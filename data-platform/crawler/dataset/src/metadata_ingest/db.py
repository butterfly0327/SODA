from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import re
from typing import Any, Dict, Iterable, Optional, Sequence

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .models import (
    CollectionRunInfo,
    HarvestStats,
    NormalizedDatasetRecord,
    SourceDefinition,
)
from .utils import (
    build_field_presence,
    build_search_text,
    clean_text,
    compact_dict,
    extract_uuid,
    first_sentence,
    infer_commercial_use_from_license,
    normalize_http_url,
    pick_localized_text,
    sha256_json,
    KST,
    unique_strings,
)


_TERM_JUNK_ROW_RE = re.compile(
    r"^(?:텍스트|동영상|기타)\s+전체\s+행\s+\d+\s+확장자\s+[A-Z0-9]+(?:\s+누적)?$"
)
_TERM_JUNK_JSON_RE = re.compile(
    r"^JSON\s+활용신청\s+\d+\s+데이터\s+한계\s+키워드(?:\s+.+)?$"
)
_TERM_SENTENCE_RE = re.compile(r"\.[ ]+")
_TERM_NOISE_TOKENS = (
    "추천데이터",
    "로그인하셔서",
    "개인정보처리방침",
    "open data portal",
    "privacy policy",
)

_PROMO_NAV_SEGMENT_RE = re.compile(
    r"(?:📑\s*)?paper\s*\|\s*(?:🌐\s*)?project\s*page\s*\|\s*(?:💾\s*)?released\s*resources\s*\|\s*(?:📦\s*)?repo",
    re.IGNORECASE,
)
_PROMO_NAV_LABELS = (
    "paper",
    "project page",
    "released resources",
    "repo",
)

_SCHEMA_STRUCTURAL_TOP_KEYS = {
    "schema",
    "features",
    "fields",
    "columns",
    "splits",
    "metadata_block_names",
    "citation_field_names",
}

_EXTRA_DROP_KEYS = {
    "describedby",
    "described_by",
    "describedbytype",
    "described_by_type",
    "bureaucode",
    "bureau_code",
    "programcode",
    "program_code",
    "updatefrequency",
    "update_frequency",
    "resource_type",
    "sections",
}

_METRICS_KEY_ALIASES = {
    "downloads": "downloads",
    "downloads_all_time": "downloads_all_time",
    "likes": "likes",
    "views": "views",
    "download_count": "download_count",
    "view_count": "view_count",
    "vote_count": "vote_count",
    "shares": "shares",
    "citations": "citations",
    "usability_rating": "usability_rating",
    "request_count": "request_count",
}


def _contains_hangul(value: str) -> bool:
    return any("가" <= ch <= "힣" for ch in value)


def _is_known_noise_term(value: str) -> bool:
    lowered = value.casefold()
    if _is_promo_nav_text(value):
        return True
    if _TERM_JUNK_ROW_RE.match(value) or _TERM_JUNK_JSON_RE.match(value):
        return True
    if any(token in lowered for token in _TERM_NOISE_TOKENS):
        return True
    if value.count("�") >= 2:
        return True
    if "http" in lowered and len(value) > 40:
        return True
    return False


def _is_sentence_like_noise(value: str) -> bool:
    if len(value) > 45 and len(value.split()) >= 6:
        return True
    if _TERM_SENTENCE_RE.search(value) and " " in value and _contains_hangul(value):
        return True
    return False


def _is_promo_nav_text(value: str) -> bool:
    lowered = value.casefold()
    if _PROMO_NAV_SEGMENT_RE.search(value):
        return True
    if "|" not in lowered:
        return False
    hits = sum(1 for label in _PROMO_NAV_LABELS if label in lowered)
    return hits >= 3


def _strip_promo_nav_text(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    stripped = _PROMO_NAV_SEGMENT_RE.sub(" ", value)
    cleaned = clean_text(stripped)
    if not cleaned:
        return None
    if _is_promo_nav_text(cleaned):
        return None
    return cleaned


def _coerce_datetime(value: Any) -> Any:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return value
    return value


_DATASET_SOURCE_LOCK_NAMESPACE = 105


_DATASET_COLUMNS: Sequence[str] = (
    "dataset_source_id",
    "last_ingest_run_id",
    "source_dataset_key",
    "record_hash",
    "canonical_url",
    "landing_url",
    "title",
    "subtitle",
    "description_short",
    "description_long",
    "search_text",
    "publisher_name",
    "domains",
    "tasks",
    "modalities",
    "tags",
    "languages",
    "license_name",
    "license_url",
    "commercial_use_allowed",
    "access_type",
    "login_required",
    "approval_required",
    "payment_required",
    "is_restricted",
    "source_created_at",
    "source_updated_at",
    "source_version",
    "row_count",
    "dataset_size_bytes",
    "field_presence_json",
    "creators_json",
    "resources_json",
    "schema_json",
    "metrics_json",
    "extra_json",
    "raw_json",
    "status",
    "last_ingested_at",
)


class SourceRunAlreadyActiveError(RuntimeError):
    pass


def _normalize_term_list(
    values: Iterable[Any],
    *,
    max_items: int = 64,
    max_len: int = 200,
    reject_sentence_like: bool = False,
) -> list[str]:
    normalized: list[str] = []
    for item in unique_strings(values):
        value = item.strip()
        if not value:
            continue
        if _is_known_noise_term(value):
            continue
        if reject_sentence_like and _is_sentence_like_noise(value):
            continue
        if len(value) > max_len:
            value = value[:max_len]
        normalized.append(value)
        if len(normalized) >= max_items:
            break
    return normalized


def _sanitize_search_text(value: Optional[str]) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    tokens = []
    for line in text.split("\n"):
        cleaned = clean_text(line)
        if not cleaned:
            continue
        if _is_known_noise_term(cleaned):
            continue
        tokens.append(cleaned)
    result = " \n".join(unique_strings(tokens))
    return result or None


def _normalize_text_field(value: Any) -> Optional[str]:
    picked = pick_localized_text(value, preferred_langs=("ko", "en", "uk"))
    return _strip_promo_nav_text(picked)


def _prune_json_like(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        text = clean_text(value)
        return text if text else None
    if isinstance(value, dict):
        pruned: Dict[str, Any] = {}
        for key, raw in value.items():
            candidate = _prune_json_like(raw)
            if candidate is None:
                continue
            pruned[str(key)] = candidate
        return pruned or None
    if isinstance(value, (list, tuple, set)):
        pruned_items = []
        for item in value:
            candidate = _prune_json_like(item)
            if candidate is None:
                continue
            pruned_items.append(candidate)
        return pruned_items or None
    return value


def _normalize_schema_json(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    pruned = _prune_json_like(value)
    if not isinstance(pruned, dict):
        return None
    filtered: Dict[str, Any] = {}

    def _drop_banned_keys(payload: Any) -> Any:
        if isinstance(payload, dict):
            result: Dict[str, Any] = {}
            for key, raw in payload.items():
                key_text = clean_text(key) if isinstance(key, str) else str(key)
                if not key_text:
                    continue
                normalized_key = key_text.casefold().replace("-", "").replace("_", "")
                if key_text in _EXTRA_DROP_KEYS or normalized_key in _EXTRA_DROP_KEYS:
                    continue
                child = _drop_banned_keys(raw)
                if child is None:
                    continue
                result[str(key)] = child
            return result or None
        if isinstance(payload, (list, tuple, set)):
            items = []
            for item in payload:
                child = _drop_banned_keys(item)
                if child is None:
                    continue
                items.append(child)
            return items or None
        return payload

    for key in _SCHEMA_STRUCTURAL_TOP_KEYS:
        candidate = _drop_banned_keys(pruned.get(key))
        candidate = _prune_json_like(candidate)
        if key in {"metadata_block_names", "citation_field_names"}:
            if not isinstance(candidate, (list, tuple, set)):
                continue
            names = unique_strings(candidate)
            if names:
                filtered[key] = names
            continue
        if isinstance(candidate, (dict, list)) and candidate:
            filtered[key] = candidate
    return filtered or None


def _normalize_extra_json(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}

    def _drop_keys(payload: Any) -> Any:
        if isinstance(payload, dict):
            result: Dict[str, Any] = {}
            for key, raw in payload.items():
                key_text = clean_text(key) if isinstance(key, str) else str(key)
                if not key_text:
                    continue
                normalized_key = key_text.casefold().replace("-", "").replace("_", "")
                if key_text in _EXTRA_DROP_KEYS or normalized_key in _EXTRA_DROP_KEYS:
                    continue
                child = _drop_keys(raw)
                if child is None:
                    continue
                result[str(key)] = child
            return result or None
        if isinstance(payload, (list, tuple, set)):
            items = []
            for item in payload:
                child = _drop_keys(item)
                if child is None:
                    continue
                items.append(child)
            return items or None
        return payload

    cleaned = _drop_keys(value)
    pruned = _prune_json_like(cleaned)
    return pruned if isinstance(pruned, dict) else {}


def _normalize_metrics_json(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    normalized: Dict[str, Any] = {}
    for key, raw in value.items():
        key_text = clean_text(key) if isinstance(key, str) else str(key)
        if not key_text:
            continue
        normalized_key = (
            key_text.casefold().replace("-", "_").replace(" ", "_").replace("__", "_")
        )
        canonical = _METRICS_KEY_ALIASES.get(normalized_key)
        if canonical is None:
            continue
        if isinstance(raw, bool) or raw is None:
            continue
        if not isinstance(raw, (int, float)):
            continue
        normalized[canonical] = raw
    return normalized


class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.conn: Optional[psycopg.Connection[Any]] = None
        self._table_names: Dict[str, str] = {
            "dataset_source": "dataset_source",
            "collection_dataset": "collection_dataset",
            "dataset": "dataset",
        }

    def __enter__(self) -> "Database":
        self.conn = psycopg.connect(self.dsn)
        self.conn.autocommit = False
        self._refresh_table_names()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.conn is None:
            return
        try:
            if exc is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            self.conn.close()
            self.conn = None

    def _cursor(self):
        if self.conn is None:
            raise RuntimeError("Database connection is not initialized")
        return self.conn.cursor(row_factory=dict_row)

    def _resolve_existing_table(self, preferred: str, fallback: str) -> str:
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = ANY(current_schemas(true))
                  AND table_name IN (%s, %s)
                ORDER BY CASE
                    WHEN table_name = %s THEN 0
                    WHEN table_name = %s THEN 1
                    ELSE 2
                END
                LIMIT 1
                """,
                (preferred, fallback, preferred, fallback),
            )
            row = cur.fetchone()
        if row and row.get("table_name"):
            return str(row["table_name"])
        return fallback

    def _refresh_table_names(self) -> None:
        self._table_names["dataset_source"] = self._resolve_existing_table(
            "dataset_sources",
            "dataset_source",
        )
        self._table_names["collection_dataset"] = self._resolve_existing_table(
            "collection_datasets",
            "collection_dataset",
        )
        self._table_names["dataset"] = self._resolve_existing_table(
            "datasets",
            "dataset",
        )

    def table_name(self, logical_name: str) -> str:
        if logical_name not in self._table_names:
            raise KeyError(f"Unknown logical table name: {logical_name}")
        return self._table_names[logical_name]

    def commit(self) -> None:
        if self.conn is not None:
            self.conn.commit()

    def rollback(self) -> None:
        if self.conn is not None:
            self.conn.rollback()

    def ensure_dataset_source(self, source: SourceDefinition) -> int:
        dataset_source_table = self.table_name("dataset_source")
        query = sql.SQL(
            """
        INSERT INTO {} (
            source_code,
            source_name,
            base_url,
            collection_type,
            is_active
        )
        VALUES (%s, %s, %s, %s, TRUE)
        ON CONFLICT (source_code)
        DO UPDATE SET
            source_name = EXCLUDED.source_name,
            base_url = EXCLUDED.base_url,
            collection_type = EXCLUDED.collection_type,
            is_active = TRUE
        RETURNING id
        """
        ).format(sql.Identifier(dataset_source_table))
        with self._cursor() as cur:
            cur.execute(
                query,
                (
                    source.source_code,
                    source.source_name,
                    source.base_url,
                    source.collection_type,
                ),
            )
            row = cur.fetchone()
        self.commit()
        assert row is not None
        return int(row["id"])

    def _try_acquire_source_lock(self, source_id: int) -> bool:
        with self._cursor() as cur:
            cur.execute(
                "SELECT pg_try_advisory_lock(%s, %s) AS locked",
                (_DATASET_SOURCE_LOCK_NAMESPACE, source_id),
            )
            row = cur.fetchone()
        assert row is not None
        return bool(row["locked"])

    def start_run(
        self, source: SourceDefinition, parser_version: str, resume: bool = True
    ) -> CollectionRunInfo:
        source_id = self.ensure_dataset_source(source)
        if not self._try_acquire_source_lock(source_id):
            raise SourceRunAlreadyActiveError(
                f"dataset source run is already active: source_id={source_id}"
            )
        checkpoint: Dict[str, Any] = {}
        collection_dataset_table = self.table_name("collection_dataset")
        with self._cursor() as cur:
            cur.execute(
                sql.SQL(
                    """
                UPDATE {}
                SET status = 'STOPPED',
                    run_finished_at = NOW(),
                    error_summary = CASE
                        WHEN error_summary IS NULL OR error_summary = ''
                            THEN '[SYSTEM] previous run was not finalized (process interrupted)'
                        ELSE error_summary || E'\n[SYSTEM] previous run was not finalized (process interrupted)'
                    END
                WHERE dataset_source_id = %s
                  AND status = 'RUNNING'
                """,
                ).format(sql.Identifier(collection_dataset_table)),
                (source_id,),
            )
        self.commit()

        if resume:
            with self._cursor() as cur:
                cur.execute(
                    sql.SQL(
                        """
                    SELECT checkpoint_json
                    FROM {}
                    WHERE dataset_source_id = %s
                      AND status IN ('RUNNING', 'FAILED', 'STOPPED', 'PARTIAL_SUCCESS', 'SUCCESS')
                    ORDER BY
                      CASE
                        WHEN checkpoint_json ? 'next_csv_index'
                          AND (checkpoint_json->>'next_csv_index') ~ '^[0-9]+$'
                        THEN (checkpoint_json->>'next_csv_index')::bigint
                        ELSE 0
                      END DESC,
                      id DESC
                    LIMIT 1
                    """,
                    ).format(sql.Identifier(collection_dataset_table)),
                    (source_id,),
                )
                row = cur.fetchone()
                if row and row.get("checkpoint_json"):
                    checkpoint = row["checkpoint_json"]

        with self._cursor() as cur:
            cur.execute(
                sql.SQL(
                    """
                INSERT INTO {} (
                    dataset_source_id,
                    parser_version,
                    status,
                    checkpoint_json
                )
                VALUES (%s, %s, 'RUNNING', %s)
                RETURNING id
                """,
                ).format(sql.Identifier(collection_dataset_table)),
                (source_id, parser_version, Jsonb(checkpoint)),
            )
            row = cur.fetchone()
        self.commit()
        assert row is not None
        return CollectionRunInfo(
            run_id=int(row["id"]), source_id=source_id, checkpoint_json=checkpoint
        )

    def update_run_progress(
        self,
        run_id: int,
        stats: HarvestStats,
        checkpoint_json: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        error_summary: Optional[str] = None,
    ) -> None:
        collection_dataset_table = self.table_name("collection_dataset")
        assignments: list[sql.Composable] = [
            sql.SQL("collected_count = %s"),
            sql.SQL("upserted_count = %s"),
            sql.SQL("failed_count = %s"),
            sql.SQL("last_saved_source_dataset_key = %s"),
        ]
        params: list[Any] = [
            stats.collected_count,
            stats.upserted_count,
            stats.failed_count,
            stats.last_saved_source_dataset_key,
        ]
        if checkpoint_json is not None:
            assignments.append(sql.SQL("checkpoint_json = %s"))
            params.append(Jsonb(checkpoint_json))
        if status is not None:
            assignments.append(sql.SQL("status = %s"))
            params.append(status)
        if error_summary is not None:
            assignments.append(sql.SQL("error_summary = %s"))
            params.append(error_summary)

        params.append(run_id)
        query = (
            sql.SQL("UPDATE {} SET ").format(sql.Identifier(collection_dataset_table))
            + sql.SQL(", ").join(assignments)
            + sql.SQL(" WHERE id = %s")
        )
        with self._cursor() as cur:
            cur.execute(query, params)
        self.commit()

    def finalize_run(
        self,
        run_id: int,
        status: str,
        stats: HarvestStats,
        checkpoint_json: Optional[Dict[str, Any]] = None,
        error_summary: Optional[str] = None,
    ) -> None:
        checkpoint_json = checkpoint_json or {}
        collection_dataset_table = self.table_name("collection_dataset")
        with self._cursor() as cur:
            cur.execute(
                sql.SQL(
                    """
                UPDATE {}
                SET status = %s,
                    run_finished_at = NOW(),
                    collected_count = %s,
                    upserted_count = %s,
                    failed_count = %s,
                    error_summary = %s,
                    last_saved_source_dataset_key = %s,
                    checkpoint_json = %s
                WHERE id = %s
                """,
                ).format(sql.Identifier(collection_dataset_table)),
                (
                    status,
                    stats.collected_count,
                    stats.upserted_count,
                    stats.failed_count,
                    error_summary,
                    stats.last_saved_source_dataset_key,
                    Jsonb(checkpoint_json),
                    run_id,
                ),
            )
        self.commit()

    def deactivate_missing_datasets(self, *, source_id: int, run_id: int) -> int:
        with self._cursor() as cur:
            cur.execute(
                """
                UPDATE datasets
                SET status = 'INACTIVE',
                    updated_at = NOW()
                WHERE dataset_source_id = %s
                  AND status = 'ACTIVE'
                  AND last_ingest_run_id IS DISTINCT FROM %s
                """,
                (source_id, run_id),
            )
            deactivated_count = cur.rowcount
        self.commit()
        return int(deactivated_count or 0)

    def upsert_dataset(
        self, source_id: int, run_id: int, record: NormalizedDatasetRecord
    ) -> None:
        dataset_table = self.table_name("dataset")
        payload = self._record_to_db_payload(
            source_id=source_id, run_id=run_id, record=record
        )
        columns_sql = sql.SQL(", ").join(
            sql.Identifier(column) for column in _DATASET_COLUMNS
        )
        placeholders_sql = sql.SQL(", ").join(
            sql.Placeholder() for _ in _DATASET_COLUMNS
        )
        updates_sql = sql.SQL(", ").join(
            sql.SQL("{} = EXCLUDED.{}").format(
                sql.Identifier(column),
                sql.Identifier(column),
            )
            for column in _DATASET_COLUMNS
            if column not in {"dataset_source_id", "source_dataset_key"}
        )

        query = sql.SQL(
            """
        INSERT INTO {} ({})
        VALUES ({})
        ON CONFLICT (dataset_source_id, source_dataset_key)
        DO UPDATE SET {}, updated_at = NOW()
        """
        ).format(
            sql.Identifier(dataset_table),
            columns_sql,
            placeholders_sql,
            updates_sql,
        )

        params = [payload[column] for column in _DATASET_COLUMNS]
        with self._cursor() as cur:
            cur.execute(query, params)

    def _record_to_db_payload(
        self, source_id: int, run_id: int, record: NormalizedDatasetRecord
    ) -> Dict[str, Any]:
        record.title = _normalize_text_field(record.title)
        record.subtitle = _normalize_text_field(record.subtitle)
        record.description_short = _normalize_text_field(record.description_short)
        record.description_long = _normalize_text_field(record.description_long)
        record.publisher_name = _normalize_text_field(record.publisher_name)
        schema_json_payload = _normalize_schema_json(record.schema_json) or {}
        extra_json_payload = _normalize_extra_json(record.extra_json)
        metrics_json_payload = _normalize_metrics_json(record.metrics_json)
        if not record.description_short and record.description_long:
            record.description_short = first_sentence(
                record.description_long, max_len=240
            )

        # 배열/검색텍스트/field presence/rhash 등 누락 보정
        record.domains = _normalize_term_list(
            record.domains,
            max_items=40,
            max_len=120,
            reject_sentence_like=True,
        )
        record.tasks = _normalize_term_list(
            record.tasks,
            max_items=64,
            max_len=160,
            reject_sentence_like=True,
        )
        record.modalities = _normalize_term_list(
            record.modalities, max_items=20, max_len=80
        )
        record.tags = _normalize_term_list(
            record.tags,
            max_items=80,
            max_len=200,
            reject_sentence_like=True,
        )
        record.languages = _normalize_term_list(
            record.languages, max_items=16, max_len=40
        )

        if record.search_text is None:
            record.search_text = build_search_text(
                record.title,
                record.subtitle,
                record.description_short,
                record.description_long,
                record.publisher_name,
                record.domains,
                record.tasks,
                record.modalities,
                record.tags,
                record.languages,
            )
        record.search_text = _sanitize_search_text(record.search_text)

        if record.commercial_use_allowed is None:
            record.commercial_use_allowed = infer_commercial_use_from_license(
                record.license_name,
                record.license_url,
            )

        record.canonical_url = normalize_http_url(record.canonical_url)
        record.landing_url = normalize_http_url(record.landing_url)
        if record.canonical_url is None and record.landing_url is not None:
            record.canonical_url = record.landing_url
        if record.landing_url is None and record.canonical_url is not None:
            record.landing_url = record.canonical_url

        if (
            record.title
            and record.source_dataset_key
            and record.title == record.source_dataset_key
            and (
                extract_uuid(record.source_dataset_key) is not None
                or record.source_dataset_key.isdigit()
            )
        ):
            record.title = None

        record_view = {
            **asdict(record),
            "field_presence_json": None,
            "schema_json": schema_json_payload,
            "metrics_json": metrics_json_payload,
            "extra_json": extra_json_payload,
        }

        compact_view = compact_dict(record_view)

        if not record.record_hash:
            record.record_hash = sha256_json(compact_view)

        if not record.field_presence_json:
            record.field_presence_json = build_field_presence(record_view)

        if not record.status:
            record.status = "ACTIVE"

        payload: Dict[str, Any] = {
            "dataset_source_id": source_id,
            "last_ingest_run_id": run_id,
            "source_dataset_key": record.source_dataset_key,
            "record_hash": record.record_hash,
            "canonical_url": record.canonical_url,
            "landing_url": record.landing_url,
            "title": record.title,
            "subtitle": record.subtitle,
            "description_short": record.description_short,
            "description_long": record.description_long,
            "search_text": record.search_text,
            "publisher_name": record.publisher_name,
            "domains": record.domains,
            "tasks": record.tasks,
            "modalities": record.modalities,
            "tags": record.tags,
            "languages": record.languages,
            "license_name": record.license_name,
            "license_url": record.license_url,
            "commercial_use_allowed": record.commercial_use_allowed,
            "access_type": record.access_type,
            "login_required": record.login_required,
            "approval_required": record.approval_required,
            "payment_required": record.payment_required,
            "is_restricted": record.is_restricted,
            "source_created_at": _coerce_datetime(record.source_created_at),
            "source_updated_at": _coerce_datetime(record.source_updated_at),
            "source_version": record.source_version,
            "row_count": record.row_count,
            "dataset_size_bytes": record.dataset_size_bytes,
            "field_presence_json": Jsonb(record.field_presence_json),
            "creators_json": Jsonb(record.creators_json),
            "resources_json": Jsonb(record.resources_json),
            "schema_json": Jsonb(schema_json_payload),
            "metrics_json": Jsonb(metrics_json_payload),
            "extra_json": Jsonb(extra_json_payload),
            "raw_json": Jsonb(record.raw_json),
            "status": record.status,
            "last_ingested_at": datetime.now(KST),
        }
        return payload

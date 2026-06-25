from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup, Tag
from psycopg import sql
from psycopg.types.json import Jsonb
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _load_local_dotenv() -> None:
    try:
        dotenv_module = importlib.import_module("dotenv")
    except ModuleNotFoundError:
        return
    load_dotenv_func = getattr(dotenv_module, "load_dotenv", None)
    if not callable(load_dotenv_func):
        return
    dotenv_path = CURRENT_DIR / ".env"
    if dotenv_path.exists():
        load_dotenv_func(dotenv_path=dotenv_path, override=False)
    else:
        load_dotenv_func(override=False)


_load_local_dotenv()

_config_module = importlib.import_module("metadata_ingest.config")
_db_module = importlib.import_module("metadata_ingest.db")

Settings = _config_module.Settings
Database = _db_module.Database


TARGET_COLUMN_KEYS = ("name_ko", "description", "data_type", "max_length", "unit")

HEADER_STRIP_RE = re.compile(r"\s+")
DATA_GOV_BASE_URL = "https://www.data.go.kr"


@dataclass(slots=True)
class TargetDataset:
    id: int
    source_dataset_key: str
    landing_url: str
    schema_json: Dict[str, Any]


@dataclass(slots=True)
class ExtractResult:
    columns: List[Dict[str, Any]]
    detail_keys: Dict[str, str]
    source: str


_EMPTY_VALUES = {"", "-", "--", "N/A", "null", "None"}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return HEADER_STRIP_RE.sub(" ", str(value)).strip()


def _normalize_header(value: str) -> str:
    text = _clean_text(value)
    text = text.replace(" ", "")
    text = text.replace("\u00a0", "")
    return text


def _map_header_to_column_key(normalized_header: str) -> Optional[str]:
    if normalized_header.startswith("항목명") and "영문" not in normalized_header:
        return "name_ko"
    if normalized_header in {"항목설명", "설명"}:
        return "description"
    if normalized_header in {"데이터타입", "자료형"}:
        return "data_type"
    if normalized_header in {"최대길이", "길이"}:
        return "max_length"
    if normalized_header in {"단위", "측정단위"}:
        return "unit"
    return None


def _pick_column_table(soup: BeautifulSoup) -> Optional[Tag]:
    for table in soup.find_all("table"):
        if not isinstance(table, Tag):
            continue
        headers = [
            _normalize_header(th.get_text(" ", strip=True))
            for th in table.select("thead th")
            if isinstance(th, Tag)
        ]
        if not headers:
            first_row = table.find("tr")
            if isinstance(first_row, Tag):
                headers = [
                    _normalize_header(cell.get_text(" ", strip=True))
                    for cell in first_row.find_all(["th", "td"])
                    if isinstance(cell, Tag)
                ]
        if not headers:
            continue
        has_name = any(header.startswith("항목명") for header in headers)
        has_type = any("데이터타입" in header for header in headers)
        if has_name and has_type:
            return table
    return None


def _extract_detail_keys(soup: BeautifulSoup) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for name in ("publicDataPk", "publicDataDetailPk"):
        node = soup.find("input", attrs={"name": name})
        if not isinstance(node, Tag):
            continue
        value = _clean_text(node.get("value"))
        if value:
            result[name] = value
    return result


def _iter_data_rows(table: Tag) -> List[Tag]:
    tbody = table.find("tbody")
    if isinstance(tbody, Tag):
        return [row for row in tbody.find_all("tr") if isinstance(row, Tag)]
    rows = [row for row in table.find_all("tr") if isinstance(row, Tag)]
    if len(rows) > 1:
        return rows[1:]
    return []


def _extract_columns_from_html(
    html: str,
    *,
    include_raw: bool,
) -> tuple[List[Dict[str, Any]], Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    table = _pick_column_table(soup)
    if table is None:
        return [], _extract_detail_keys(soup)

    headers = [
        _clean_text(th.get_text(" ", strip=True))
        for th in table.select("thead th")
        if isinstance(th, Tag)
    ]
    if not headers:
        first_row = table.find("tr")
        if isinstance(first_row, Tag):
            headers = [
                _clean_text(cell.get_text(" ", strip=True))
                for cell in first_row.find_all(["th", "td"])
                if isinstance(cell, Tag)
            ]

    columns: List[Dict[str, Any]] = []
    for row in _iter_data_rows(table):
        cells = [
            _clean_text(cell.get_text(" ", strip=True))
            for cell in row.find_all(["th", "td"])
            if isinstance(cell, Tag)
        ]
        if not cells:
            continue
        payload: Dict[str, Any] = {}
        raw_payload: Dict[str, str] = {}
        for idx, raw_value in enumerate(cells):
            if idx >= len(headers):
                break
            header = headers[idx]
            if not header:
                continue
            raw_payload[header] = raw_value
            mapped_key = _map_header_to_column_key(_normalize_header(header))
            if mapped_key:
                payload[mapped_key] = raw_value

        if not payload:
            continue
        if not payload.get("name_ko"):
            continue
        if include_raw and raw_payload:
            payload["raw"] = raw_payload
        columns.append(payload)

    return columns, _extract_detail_keys(soup)


def _build_retry_session(user_agent: str) -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.7,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "HEAD", "OPTIONS"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)

    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        }
    )
    return session


def _compact_column_items(columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    compacted: List[Dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, str]] = set()

    for item in columns:
        reduced: Dict[str, Any] = {}
        for key, value in item.items():
            if key == "raw":
                reduced[key] = value
                continue
            if key not in TARGET_COLUMN_KEYS:
                continue
            text = _clean_text(value)
            if text in _EMPTY_VALUES:
                continue
            reduced[key] = text

        name_ko = _clean_text(reduced.get("name_ko"))
        description = _clean_text(reduced.get("description"))
        data_type = _clean_text(reduced.get("data_type"))
        max_length = _clean_text(reduced.get("max_length"))
        unit = _clean_text(reduced.get("unit"))

        if not name_ko:
            continue

        dedup_key = (
            name_ko.casefold(),
            description.casefold(),
            data_type.casefold(),
            max_length.casefold(),
            unit.casefold(),
        )
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        compacted.append(reduced)

    return compacted


def _extract_columns_via_button_flow(
    session: requests.Session,
    *,
    landing_url: str,
    request_timeout: float,
    include_raw: bool,
) -> ExtractResult:
    landing_response = session.get(landing_url, timeout=request_timeout)
    landing_response.raise_for_status()

    landing_columns, detail_keys = _extract_columns_from_html(
        landing_response.text,
        include_raw=include_raw,
    )

    public_data_detail_pk = detail_keys.get("publicDataDetailPk")
    if public_data_detail_pk:
        detail_response = session.get(
            f"{DATA_GOV_BASE_URL}/tcs/dss/selectDpkDetailInfo.do",
            params={"publicDataDetailPk": public_data_detail_pk},
            timeout=request_timeout,
        )
        detail_response.raise_for_status()
        detail_columns, _ = _extract_columns_from_html(
            detail_response.text,
            include_raw=include_raw,
        )
        if detail_columns:
            return ExtractResult(
                columns=detail_columns,
                detail_keys=detail_keys,
                source="detail_button",
            )

    public_data_pk = detail_keys.get("publicDataPk")
    if public_data_pk and public_data_detail_pk:
        hist_response = session.get(
            f"{DATA_GOV_BASE_URL}/tcs/dss/selectHistAndCsvData.do",
            params={
                "publicDataPk": public_data_pk,
                "publicDataDetailPk": public_data_detail_pk,
            },
            timeout=request_timeout,
        )
        hist_response.raise_for_status()
        hist_columns, _ = _extract_columns_from_html(
            hist_response.text,
            include_raw=include_raw,
        )
        if hist_columns:
            return ExtractResult(
                columns=hist_columns,
                detail_keys=detail_keys,
                source="hist_csv_button",
            )

    if landing_columns:
        return ExtractResult(
            columns=landing_columns,
            detail_keys=detail_keys,
            source="landing_page",
        )

    return ExtractResult(columns=[], detail_keys=detail_keys, source="none")


def _columns_already_present(schema_json: Dict[str, Any]) -> bool:
    columns = schema_json.get("columns")
    return isinstance(columns, list) and len(columns) > 0


def _to_psycopg_dsn(dsn: str) -> str:
    prefix = "postgresql+asyncpg://"
    if dsn.startswith(prefix):
        return "postgresql://" + dsn[len(prefix) :]
    return dsn


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill data.go.kr column metadata into datasets.schema_json"
    )
    parser.add_argument(
        "--limit", type=int, default=100, help="Max target rows to process"
    )
    parser.add_argument(
        "--offset", type=int, default=0, help="Row offset for target query"
    )
    parser.add_argument(
        "--dataset-id",
        type=int,
        default=None,
        help="Process a single datasets.id value",
    )
    parser.add_argument(
        "--include-existing",
        action="store_true",
        help="Include rows that already have schema_json.columns",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually update DB (default is dry-run)",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=20.0,
        help="HTTP timeout seconds per dataset page",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.15,
        help="Sleep seconds between HTTP requests",
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="Keep raw header-value map per column item",
    )
    return parser


def _load_targets(
    db: Database,
    *,
    limit: int,
    offset: int,
    dataset_id: Optional[int],
) -> List[TargetDataset]:
    dataset_table = db.table_name("dataset")
    where_clauses = [
        sql.SQL("landing_url IS NOT NULL"),
        sql.SQL("landing_url LIKE %s"),
    ]
    params: List[Any] = ["https://www.data.go.kr/data/%/fileData.do"]

    if dataset_id is not None:
        where_clauses.append(sql.SQL("id = %s"))
        params.append(dataset_id)

    query = (
        sql.SQL(
            "SELECT id, source_dataset_key, landing_url, schema_json FROM {} WHERE "
        ).format(sql.Identifier(dataset_table))
        + sql.SQL(" AND ").join(where_clauses)
        + sql.SQL(" ORDER BY id ASC LIMIT %s OFFSET %s")
    )
    params.extend([limit, offset])

    results: List[TargetDataset] = []
    with db._cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall() or []

    for row in rows:
        schema_json = row.get("schema_json")
        if not isinstance(schema_json, dict):
            schema_json = {}
        results.append(
            TargetDataset(
                id=int(row["id"]),
                source_dataset_key=str(row.get("source_dataset_key") or ""),
                landing_url=str(row["landing_url"]),
                schema_json=schema_json,
            )
        )
    return results


def _update_schema_json(
    db: Database, dataset_id: int, schema_json: Dict[str, Any]
) -> None:
    dataset_table = db.table_name("dataset")
    query = sql.SQL(
        "UPDATE {} SET schema_json = %s, updated_at = NOW() WHERE id = %s"
    ).format(sql.Identifier(dataset_table))
    with db._cursor() as cur:
        cur.execute(query, (Jsonb(schema_json), dataset_id))


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    settings = Settings()
    settings.validate()
    dsn = _to_psycopg_dsn(settings.database_url)

    processed = 0
    updated = 0
    skipped_existing = 0
    skipped_no_columns = 0
    failed = 0

    session = _build_retry_session(settings.user_agent)

    with Database(dsn) as db:
        targets = _load_targets(
            db,
            limit=args.limit,
            offset=args.offset,
            dataset_id=args.dataset_id,
        )
        print(f"[INFO] target_count={len(targets)} dry_run={not args.apply}")

        for target in targets:
            processed += 1

            if not args.include_existing and _columns_already_present(
                target.schema_json
            ):
                skipped_existing += 1
                print(f"[SKIP] id={target.id} reason=existing_columns")
                continue

            try:
                extract_result = _extract_columns_via_button_flow(
                    session,
                    landing_url=target.landing_url,
                    request_timeout=args.request_timeout,
                    include_raw=args.include_raw,
                )
                columns = _compact_column_items(extract_result.columns)
                detail_keys = extract_result.detail_keys
            except Exception as exc:
                failed += 1
                print(f"[FAIL] id={target.id} url={target.landing_url} error={exc}")
                continue

            if not columns:
                skipped_no_columns += 1
                print(
                    f"[SKIP] id={target.id} reason=no_column_table source={extract_result.source}"
                )
                continue

            next_schema = dict(target.schema_json)
            next_schema["columns"] = columns
            if detail_keys:
                next_schema["public_data_detail"] = detail_keys

            if args.apply:
                _update_schema_json(db, target.id, next_schema)
                updated += 1
                print(
                    f"[UPDATE] id={target.id} columns={len(columns)} source={extract_result.source} detail_keys={json.dumps(detail_keys, ensure_ascii=False)}"
                )
            else:
                print(
                    f"[DRYRUN] id={target.id} columns={len(columns)} source={extract_result.source} detail_keys={json.dumps(detail_keys, ensure_ascii=False)}"
                )

            if args.sleep > 0:
                time.sleep(args.sleep)

        if args.apply:
            db.commit()

    print(
        f"[DONE] processed={processed} updated={updated} skipped_existing={skipped_existing} "
        f"skipped_no_columns={skipped_no_columns} failed={failed}"
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import csv
import importlib
import json
import random
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from bs4 import BeautifulSoup


CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

_config_module = importlib.import_module("metadata_ingest.config")
_db_module = importlib.import_module("metadata_ingest.db")
_models_module = importlib.import_module("metadata_ingest.models")
_portal_module = importlib.import_module("metadata_ingest.sources.public_data_portal")
_utils_module = importlib.import_module("metadata_ingest.utils")

Settings = _config_module.Settings
Database = _db_module.Database
HarvestStats = _models_module.HarvestStats
NormalizedDatasetRecord = _models_module.NormalizedDatasetRecord
PublicDataPortalCollector = _portal_module.PublicDataPortalCollector

clean_text = _utils_module.clean_text
domains_from_urls = _utils_module.domains_from_urls
guess_modalities_from_text = _utils_module.guess_modalities_from_text
parse_bool = _utils_module.parse_bool
parse_bytes = _utils_module.parse_bytes
parse_datetime = _utils_module.parse_datetime
parse_int = _utils_module.parse_int
unique_strings = _utils_module.unique_strings


_SOURCE_KEY_RE = re.compile(r"/data/(\d+)/(?:fileData|openapi)\.do", re.IGNORECASE)
_SOURCE_KEY_FALLBACK_RE = re.compile(r"\b(\d{6,})\b")
_VERSION_SUFFIX_RE = re.compile(r"(?:_|-)(\d{8}|v\d+(?:\.\d+)*)$", re.IGNORECASE)
_SPLIT_RE = re.compile(r"[,|;/\\n\\t]+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|(?<=다\.)\s+|[\r\n]+")
_TASK_JUNK_ROW_RE = re.compile(
    r"^(?:텍스트|동영상|기타)\s+전체\s+행\s+\d+\s+확장자\s+[A-Z0-9]+(?:\s+누적)?$"
)
_TASK_JUNK_JSON_RE = re.compile(
    r"^JSON\s+활용신청\s+\d+\s+데이터\s+한계\s+키워드(?:\s+.+)?$"
)

_TRUE_HINTS = ("허용", "가능", "제한 없음", "allowed", "yes")
_FALSE_HINTS = ("비영리", "변경금지", "금지", "불가", "금지됨", "prohibit", "no")

_ACCESS_TYPES = {"OPEN", "REGISTERED", "APPROVAL", "PAID", "RESTRICTED", "UNKNOWN"}

_NOISE_TOKENS = (
    "추천데이터",
    "로그인하셔서",
    "개인정보처리방침",
    "오픈데이터포털",
    "open data portal",
    "privacy policy",
    "government 24",
)

_PLACEHOLDER_TEXTS = {
    "-",
    "--",
    "없음",
    "해당없음",
    "n/a",
    "na",
    "none",
    "null",
}


def _is_noisy_term(term: str) -> bool:
    lowered = term.casefold()
    if _TASK_JUNK_ROW_RE.match(term) or _TASK_JUNK_JSON_RE.match(term):
        return True
    if any(token in lowered for token in _NOISE_TOKENS):
        return True
    if term.count("�") >= 2:
        return True
    if len(term) > 90:
        return True
    if len(term) > 45 and len(term.split()) >= 6:
        return True
    if "http" in lowered and len(term) > 40:
        return True
    return False


def _has_hangul(text: str) -> bool:
    return any("가" <= char <= "힣" for char in text)


def _is_noisy_task_term(term: str) -> bool:
    if _TASK_JUNK_ROW_RE.match(term):
        return True
    if _TASK_JUNK_JSON_RE.match(term):
        return True
    if ". " in term and " " in term and _has_hangul(term):
        return True
    return False


def _sanitize_terms(
    values: Iterable[str], *, max_len: int = 80, field_type: str = "generic"
) -> List[str]:
    sanitized: List[str] = []
    for value in values or []:
        text = clean_text(value)
        if not text:
            continue
        if len(text) > max_len:
            continue
        if _is_noisy_term(text):
            continue
        if field_type == "task" and _is_noisy_task_term(text):
            continue
        sanitized.append(text)
    return unique_strings(sanitized)


def _build_description_short(
    description: Optional[str],
    description_long: Optional[str],
) -> Optional[str]:
    base = clean_text(description) or clean_text(description_long)
    if not base:
        return None

    for chunk in _SENTENCE_SPLIT_RE.split(base):
        candidate = clean_text(chunk)
        if candidate:
            return candidate
    return base


def _norm(text: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", text.casefold())


def _pick(row: Dict[str, Any], aliases: Iterable[str]) -> Optional[str]:
    alias_keys = {_norm(alias) for alias in aliases}
    for key, value in row.items():
        if _norm(str(key)) not in alias_keys:
            continue
        cleaned = clean_text(value)
        if cleaned:
            return cleaned
    return None


def _split_terms(value: Any) -> List[str]:
    text = clean_text(value)
    if not text:
        return []
    parts = [part.strip() for part in _SPLIT_RE.split(text) if part.strip()]
    if len(parts) <= 1 and " - " in text:
        parts = [part.strip() for part in text.split(" - ") if part.strip()]
    return unique_strings(parts)


def _merge_list(left: Iterable[str], right: Iterable[str]) -> List[str]:
    return unique_strings([*(left or []), *(right or [])])


def _is_meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return False
        return text.casefold() not in _PLACEHOLDER_TEXTS
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _choose(primary: Any, secondary: Any) -> Any:
    if _is_meaningful(primary):
        return primary
    return secondary


def _merge_dict(preferred: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    if fallback:
        merged.update(fallback)
    if preferred:
        merged.update(preferred)
    return merged


def _commercial_use_from_text(text: Optional[str]) -> Optional[bool]:
    cleaned = clean_text(text)
    if not cleaned:
        return None
    lowered = cleaned.casefold()
    if any(token in lowered for token in _FALSE_HINTS):
        return False
    if any(token in lowered for token in _TRUE_HINTS):
        return True
    return None


def _extract_version_from_name(name: Optional[str]) -> Optional[str]:
    text = clean_text(name)
    if not text:
        return None
    matched = _VERSION_SUFFIX_RE.search(text)
    if matched:
        return matched.group(1)
    return None


def _infer_payment_required(
    cost_flag: Optional[str], cost_note: Optional[str]
) -> Optional[bool]:
    flag = clean_text(cost_flag)
    if flag:
        lowered = flag.casefold()
        if "무료" in lowered or lowered in {"n", "no", "false", "0", "면제"}:
            return False
        if (
            "유료" in lowered
            or "비용" in lowered
            or lowered in {"y", "yes", "true", "1"}
        ):
            return True

    note = clean_text(cost_note)
    if note:
        lowered = note.casefold()
        if "무료" in lowered or "무상" in lowered:
            return False
        if any(token in lowered for token in ["원", "유료", "과금", "비용"]):
            return True
    return None


def _infer_approval_required(
    review_text: Optional[str], provided_text: Optional[str]
) -> Optional[bool]:
    review = clean_text(review_text)
    if review:
        lowered = review.casefold()
        if lowered in {"-", "없음", "미해당", "자동"}:
            return False
        if any(
            token in lowered for token in ["심의", "승인", "검토", "신청", "approval"]
        ):
            return True

    provided = clean_text(provided_text)
    if provided:
        lowered = provided.casefold()
        if any(token in lowered for token in ["활용신청", "신청", "승인", "approval"]):
            return True
    return None


def _infer_access_type(
    access_type: Optional[str],
    *,
    login_required: Optional[bool],
    approval_required: Optional[bool],
    payment_required: Optional[bool],
    is_restricted: Optional[bool],
) -> str:
    if access_type and access_type in _ACCESS_TYPES:
        return access_type
    if payment_required is True:
        return "PAID"
    if approval_required is True:
        return "APPROVAL"
    if is_restricted is True:
        return "RESTRICTED"
    if login_required is True:
        return "REGISTERED"
    if (
        payment_required is False
        and approval_required is False
        and is_restricted is False
    ):
        return "OPEN"
    return "UNKNOWN"


def _is_noisy_detail_text(value: Any) -> bool:
    text = clean_text(value)
    if not text:
        return False
    lowered = text.casefold()
    if any(token in lowered for token in _NOISE_TOKENS):
        return True
    return len(lowered) >= 320 and ("로그인" in lowered or "portal" in lowered)


def _sanitize_crawled_record(record: NormalizedDatasetRecord) -> None:
    extra_json = dict(record.extra_json or {})
    detail_kv = extra_json.get("detail_kv")
    if isinstance(detail_kv, dict):
        cleaned_detail_kv: Dict[str, Any] = {}
        for key, value in detail_kv.items():
            if _is_noisy_detail_text(value):
                continue
            cleaned_detail_kv[key] = value
        if cleaned_detail_kv:
            extra_json["detail_kv"] = cleaned_detail_kv
        else:
            extra_json.pop("detail_kv", None)
    record.extra_json = extra_json

    raw_json = dict(record.raw_json or {})
    detail_text = raw_json.get("detail_text")
    if _is_noisy_detail_text(detail_text):
        raw_json.pop("detail_text", None)
    record.raw_json = raw_json


def _is_file_type_row(row: Dict[str, Any]) -> bool:
    list_type = _pick(row, ["목록유형", "list_type", "type"])
    if not list_type:
        return False
    return list_type.strip().upper() == "FILE"


class FastPublicDataPortalCollector(PublicDataPortalCollector):
    def __init__(
        self,
        db: Database,
        settings: Settings,
        csv_path: Path,
        *,
        enable_db_resume_fallback: bool = True,
    ):
        super().__init__(db=db, settings=settings)
        self.csv_path = csv_path
        self.enable_db_resume_fallback = enable_db_resume_fallback
        configured_delay = max(settings.public_data_portal_crawl_delay_seconds, 0.0)
        self.crawl_delay_seconds = min(configured_delay, 0.01)
        self.crawl_retry_count = settings.public_data_portal_crawl_retry_count
        configured_backoff = max(
            settings.public_data_portal_crawl_retry_backoff_seconds, 0.0
        )
        self.crawl_retry_backoff_seconds = min(configured_backoff, 0.35)
        self.crawl_retry_backoff_cap_seconds = 1.5
        self.crawl_retry_jitter_ratio = 0.2

        self.min_request_interval_seconds = 0.0
        self.request_interval_jitter_seconds = 0.0
        self.batch_pause_every = 0
        self.batch_pause_seconds = 0.0

    def _resolve_resume_checkpoint(self, checkpoint: Dict[str, Any]) -> Dict[str, Any]:
        resolved = dict(checkpoint or {})
        if not self.enable_db_resume_fallback:
            return resolved

        next_csv_index = parse_int(resolved.get("next_csv_index"))
        if next_csv_index is not None and next_csv_index >= 1:
            return resolved

        last_saved_source_key = self._find_latest_saved_source_key_in_db()
        if not last_saved_source_key:
            return resolved

        next_index = self._find_next_csv_index_after_source_key(last_saved_source_key)
        if next_index is None:
            return resolved

        resolved["last_saved_source_dataset_key"] = str(last_saved_source_key)
        resolved["next_csv_index"] = int(next_index)
        return resolved

    def _find_latest_saved_source_key_in_db(self) -> Optional[str]:
        if self.db.conn is None:
            return None

        dataset_table = self.db.table_name("dataset")
        dataset_source_table = self.db.table_name("dataset_source")

        with self.db.conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT d.source_dataset_key
                FROM {dataset_table} AS d
                JOIN {dataset_source_table} AS s
                  ON s.id = d.dataset_source_id
                WHERE s.source_code = %s
                  AND d.source_dataset_key IS NOT NULL
                ORDER BY d.last_ingested_at DESC, d.id DESC
                LIMIT 1
                """,
                (self.source.source_code,),
            )
            row = cur.fetchone()

        if not row:
            return None

        source_dataset_key = (
            row[0] if isinstance(row, tuple) else row.get("source_dataset_key")
        )
        cleaned = clean_text(source_dataset_key)
        return cleaned if cleaned else None

    def _find_next_csv_index_after_source_key(self, source_key: str) -> Optional[int]:
        for index, row in self._iter_csv_rows(start_index=1):
            row_source_key = self._extract_source_key(row)
            if row_source_key == source_key:
                return index + 1
        return None

    def _crawl_record_with_retry(
        self,
        source_key: str,
        detail_url: str,
    ) -> Tuple[Optional[NormalizedDatasetRecord], Optional[str]]:
        total_attempts = max(self.crawl_retry_count, 0) + 1
        last_error: Optional[Exception] = None

        for attempt in range(total_attempts):
            try:
                if self.crawl_delay_seconds > 0:
                    self.sleep(self.crawl_delay_seconds)

                detail_html = self.get_text(detail_url, retries=1)
                detail_soup = BeautifulSoup(detail_html, "lxml")
                schema_json = self._fetch_schema_json(source_key)
                crawled = self._normalize(
                    source_key, detail_url, detail_soup, schema_json
                )
                _sanitize_crawled_record(crawled)
                return crawled, None
            except Exception as exc:
                last_error = exc
                if attempt + 1 >= total_attempts:
                    break
                if self.crawl_retry_backoff_seconds > 0:
                    backoff = self.crawl_retry_backoff_seconds * (2**attempt)
                    capped_backoff = min(backoff, self.crawl_retry_backoff_cap_seconds)
                    if self.crawl_retry_jitter_ratio > 0:
                        jitter = capped_backoff * random.uniform(
                            0.0,
                            self.crawl_retry_jitter_ratio,
                        )
                        capped_backoff += jitter
                    self.sleep(capped_backoff)

        assert last_error is not None
        return None, f"{type(last_error).__name__}: {last_error}"

    def iter_records(
        self, checkpoint: Dict[str, Any]
    ) -> Iterator[Tuple[NormalizedDatasetRecord, Dict[str, Any]]]:
        effective_checkpoint = self._resolve_resume_checkpoint(checkpoint)
        start_index = max(parse_int(effective_checkpoint.get("next_csv_index")) or 1, 1)

        for index, row in self._iter_csv_rows(start_index=start_index):
            if not _is_file_type_row(row):
                continue

            source_key = self._extract_source_key(row)
            if not source_key:
                self.stats.failed_count += 1
                self.stats.errors.append(
                    f"[PUBLIC_DATA_PORTAL] csv-row:{index}: source key not found"
                )
                continue

            detail_url = self._extract_detail_url(row, source_key)
            csv_record = self._build_csv_record(
                source_key=source_key, detail_url=detail_url, row=row
            )

            crawl_record, crawl_error = self._crawl_record_with_retry(
                source_key,
                detail_url,
            )

            if crawl_record:
                merged = self._merge_records(crawl_record, csv_record)
            else:
                merged = csv_record

            if crawl_error:
                merged.extra_json = _merge_dict(
                    {
                        "crawl_error": crawl_error,
                        "crawl_attempted": True,
                    },
                    merged.extra_json,
                )

            next_checkpoint = {
                "next_csv_index": index + 1,
            }
            yield merged, next_checkpoint

    def _iter_csv_rows(self, start_index: int) -> Iterator[Tuple[int, Dict[str, Any]]]:
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV not found: {self.csv_path}")

        with self.csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            sample = handle.read(4096)
            handle.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
            except csv.Error:
                dialect = csv.excel

            reader = csv.DictReader(handle, dialect=dialect)
            if not reader.fieldnames:
                raise ValueError("CSV header is missing")

            for idx, row in enumerate(reader, start=1):
                if idx < start_index:
                    continue
                normalized = {
                    str(k).strip(): v for k, v in (row or {}).items() if k is not None
                }
                yield idx, normalized

    def _extract_source_key(self, row: Dict[str, Any]) -> Optional[str]:
        key_from_column = _pick(
            row,
            [
                "목록키",
                "목록번호",
                "데이터셋ID",
                "데이터셋아이디",
                "데이터ID",
                "dataset_id",
                "id",
                "식별자",
            ],
        )
        if key_from_column:
            match = _SOURCE_KEY_FALLBACK_RE.search(key_from_column)
            if match:
                return match.group(1)

        for value in row.values():
            text = clean_text(value)
            if not text:
                continue
            match = _SOURCE_KEY_RE.search(text)
            if match:
                return match.group(1)

        for value in row.values():
            text = clean_text(value)
            if not text:
                continue
            fallback = _SOURCE_KEY_FALLBACK_RE.search(text)
            if fallback:
                return fallback.group(1)
        return None

    def _extract_detail_url(self, row: Dict[str, Any], source_key: str) -> str:
        url = _pick(
            row,
            [
                "목록URL",
                "상세URL",
                "상세주소",
                "dataset_url",
                "detail_url",
                "landing_url",
                "url",
            ],
        )
        if url and url.startswith("http"):
            return url
        return f"https://www.data.go.kr/data/{source_key}/fileData.do"

    def _build_csv_record(
        self,
        *,
        source_key: str,
        detail_url: str,
        row: Dict[str, Any],
    ) -> NormalizedDatasetRecord:
        list_type = _pick(row, ["목록유형", "type"])
        file_dataset_name = _pick(row, ["파일데이터명", "파일명", "dataset_file_name"])

        title = _pick(row, ["목록명", "데이터셋명", "dataset_title", "title", "이름"])
        subtitle = None
        description = _pick(row, ["설명", "개요", "설명요약", "description", "summary"])
        data_limit = _pick(row, ["데이터한계", "데이터 한계", "data_limit"])
        notice = _pick(row, ["기타유의사항", "기타 유의사항", "notes", "other_notes"])
        publisher = _pick(
            row,
            ["제공기관", "기관명", "소유기관", "publisher", "provider", "관리기관"],
        )
        department_name = _pick(row, ["관리부서명", "관리 부서명", "department"])
        department_phone = _pick(
            row, ["관리부서전화번호", "관리부서 전화번호", "department_phone"]
        )

        description_long_items = [
            clean_text(part)
            for part in [description, data_limit, notice]
            if _is_meaningful(part)
        ]
        description_long = "\n".join(
            part for part in description_long_items if part is not None
        )
        description_long = description_long if description_long else description
        description_short = _build_description_short(description, description_long)

        keyword_terms = _split_terms(_pick(row, ["키워드", "태그", "keywords", "tags"]))
        domain_terms = _split_terms(
            _pick(row, ["분류체계", "분야", "category", "domain"])
        )
        language_terms = _split_terms(_pick(row, ["언어", "language", "languages"]))

        license_name = _pick(row, ["이용허락", "라이선스", "license", "license_name"])
        license_url = _pick(row, ["라이선스URL", "license_url", "licenseLink"])

        payment_text = _pick(
            row,
            [
                "비용부과유무",
                "비용부과",
                "비용",
                "payment",
                "fee",
            ],
        )
        payment_note = _pick(
            row,
            [
                "비용부과기준및단위",
                "비용부과기준 및 단위",
                "charge_standard",
            ],
        )
        approval_text = _pick(
            row,
            [
                "심의유형",
                "심의 유형",
                "심의단계",
                "승인",
                "approval",
                "approval_required",
            ],
        )
        login_text = _pick(row, ["로그인필요", "login_required", "인증필요"])
        provided_type = _pick(row, ["제공형태", "provided", "form_of_provision"])

        payment_required = _infer_payment_required(payment_text, payment_note)

        approval_required = _infer_approval_required(approval_text, provided_type)

        login_required = parse_bool(login_text)
        if login_required is None and approval_required is True:
            login_required = True
        if login_required is None and provided_type:
            lowered = provided_type.casefold()
            if any(
                token in lowered for token in ["활용신청", "로그인", "신청", "회원"]
            ):
                login_required = True
            elif any(token in lowered for token in ["다운로드", "바로", "기관자체"]):
                login_required = False

        commercial_use_allowed = _commercial_use_from_text(license_name)

        row_count = parse_int(
            _pick(
                row, ["전체건수", "행수", "row_count", "rows", "데이터건수", "전체행"]
            )
        )
        if row_count is not None and row_count < 0:
            row_count = None
        dataset_size_bytes = parse_bytes(
            _pick(row, ["데이터용량", "용량", "size", "dataset_size", "파일용량"])
        )
        if dataset_size_bytes is not None and dataset_size_bytes < 0:
            dataset_size_bytes = None

        created_at = parse_datetime(
            _pick(row, ["등록일", "생성일", "created_at", "등록일자"])
        )
        updated_at = parse_datetime(
            _pick(row, ["수정일", "변경일", "updated_at", "수정일자"])
        )

        source_version = _pick(row, ["버전", "버전정보", "version"])
        if not source_version:
            source_version = _extract_version_from_name(file_dataset_name)
        access_type = _pick(row, ["접근유형", "access_type"])
        if access_type:
            access_type = access_type.upper()
        is_restricted = parse_bool(
            _pick(row, ["제한여부", "restricted", "is_restricted"])
        )
        if is_restricted is None:
            restricted_hint_items = [
                clean_text(part)
                for part in [provided_type, approval_text, data_limit]
                if _is_meaningful(part)
            ]
            restricted_hint_text = " ".join(
                part for part in restricted_hint_items if part is not None
            ).casefold()
            if any(
                token in restricted_hint_text
                for token in ["제한", "restricted", "승인", "심의"]
            ):
                is_restricted = True

        download_url = _pick(
            row, ["다운로드URL", "다운로드", "download_url", "file_url"]
        )
        format_text = _pick(
            row,
            [
                "확장자데이터포맷",
                "확장자(데이터포맷)",
                "확장자",
                "포맷",
                "format",
                "file_format",
                "파일형식",
            ],
        )
        media_type = _pick(row, ["매체유형", "media_type"])
        traffic_limit = _pick(
            row, ["신청가능트래픽", "신청가능 트래픽", "traffic_limit"]
        )
        api_type = _pick(row, ["api유형", "API 유형", "api_type"])
        list_url = _pick(row, ["목록URL", "목록 URL", "list_url"])

        spatial_range = _pick(row, ["공간범위", "spatial_range"])
        time_range = _pick(row, ["시간범위", "time_range"])
        update_cycle = _pick(row, ["업데이트주기", "업데이트 주기", "update_cycle"])
        next_registration_date = parse_datetime(
            _pick(row, ["차기등록예정일", "차기 등록 예정일", "next_registration_date"])
        )
        retention_basis = _pick(row, ["보유근거", "basis_for_retention"])
        collection_method = _pick(row, ["수집방법", "collection_method"])
        national_core = _pick(row, ["국가중점여부", "국가중점", "national_core"])
        standard_data = _pick(row, ["표준데이터여부", "표준데이터", "standard_data"])

        resources_json: List[Dict[str, Any]] = [
            {
                "title": file_dataset_name or title,
                "download_url": download_url or list_url or detail_url,
                "landing_url": list_url or detail_url,
                "format": format_text,
                "media_type": media_type,
                "provided_type": provided_type,
                "api_type": api_type,
                "traffic_limit": traffic_limit,
                "content_size": _pick(row, ["데이터용량", "용량", "size", "파일용량"]),
                "source": "csv",
            }
        ]

        modalities = guess_modalities_from_text(
            title,
            subtitle,
            description,
            keyword_terms,
            domain_terms,
            format_text,
            media_type,
        )

        tags = _sanitize_terms([*keyword_terms, *domain_terms], max_len=80)
        tasks = _sanitize_terms(keyword_terms, max_len=80, field_type="task")
        domains = _sanitize_terms(domain_terms, max_len=80)
        languages = _sanitize_terms(language_terms, max_len=40)

        metrics_json = {
            "request_count": parse_int(
                _pick(
                    row,
                    ["다운로드활용신청건수", "다운로드_활용신청건수", "request_count"],
                )
            ),
            "download_count": parse_int(
                _pick(row, ["다운로드수", "download_count", "download"])
            ),
            "view_count": parse_int(_pick(row, ["조회수", "view_count", "views"])),
        }

        creators_json: List[Dict[str, Any]] = []
        if publisher:
            creators_json.append({"name": publisher, "role": "publisher"})
        if department_name:
            creators_json.append(
                {
                    "name": department_name,
                    "role": "department",
                    "phone": department_phone,
                }
            )

        schema_json = {
            "csv_fields": {
                "list_type": list_type,
                "file_dataset_name": file_dataset_name,
                "media_type": media_type,
                "format": format_text,
                "update_cycle": update_cycle,
                "next_registration_date": next_registration_date,
                "retention_basis": retention_basis,
                "collection_method": collection_method,
                "spatial_range": spatial_range,
                "time_range": time_range,
                "national_core": national_core,
                "standard_data": standard_data,
            }
        }

        extra_json = {
            "csv_row": row,
            "ingest_mode": "csv_plus_crawl",
            "data_limit": data_limit,
            "notes": notice,
            "provided_type": provided_type,
            "cost_note": payment_note,
            "traffic_limit": traffic_limit,
            "api_type": api_type,
            "department_name": department_name,
            "department_phone": department_phone,
            "spatial_range": spatial_range,
            "time_range": time_range,
            "update_cycle": update_cycle,
            "next_registration_date": next_registration_date,
            "retention_basis": retention_basis,
            "collection_method": collection_method,
            "national_core": national_core,
            "standard_data": standard_data,
        }

        raw_json = {
            "csv": row,
        }

        if is_restricted is None:
            is_restricted = bool(
                payment_required is True
                or approval_required is True
                or login_required is True
            )

        access_type = _infer_access_type(
            access_type,
            login_required=login_required,
            approval_required=approval_required,
            payment_required=payment_required,
            is_restricted=is_restricted,
        )

        return NormalizedDatasetRecord(
            source_dataset_key=source_key,
            canonical_url=detail_url,
            landing_url=detail_url,
            title=title,
            subtitle=subtitle,
            description_short=description_short,
            description_long=description_long,
            publisher_name=publisher,
            domains=domains,
            tasks=tasks,
            modalities=modalities,
            tags=tags,
            languages=languages,
            license_name=license_name,
            license_url=license_url,
            commercial_use_allowed=commercial_use_allowed,
            access_type=access_type,
            login_required=login_required,
            approval_required=approval_required,
            payment_required=payment_required,
            is_restricted=is_restricted,
            source_created_at=created_at,
            source_updated_at=updated_at,
            source_version=source_version,
            row_count=row_count,
            dataset_size_bytes=dataset_size_bytes,
            metrics_json={k: v for k, v in metrics_json.items() if v is not None},
            creators_json=creators_json,
            resources_json=resources_json,
            schema_json=schema_json,
            extra_json=extra_json,
            raw_json=raw_json,
        )

    def _merge_records(
        self,
        crawled: NormalizedDatasetRecord,
        csv_record: NormalizedDatasetRecord,
    ) -> NormalizedDatasetRecord:
        merged_resources = _merge_list(
            [
                json.dumps(item, ensure_ascii=False, sort_keys=True)
                for item in crawled.resources_json
            ],
            [
                json.dumps(item, ensure_ascii=False, sort_keys=True)
                for item in csv_record.resources_json
            ],
        )
        resources_json = [json.loads(item) for item in merged_resources]

        merged_domains = _sanitize_terms(
            _merge_list(crawled.domains, csv_record.domains),
            max_len=80,
        )
        merged_tasks = _sanitize_terms(
            _merge_list(crawled.tasks, csv_record.tasks),
            max_len=80,
            field_type="task",
        )
        merged_tags = _sanitize_terms(
            _merge_list(crawled.tags, csv_record.tags),
            max_len=80,
        )
        merged_languages = _sanitize_terms(
            _merge_list(crawled.languages, csv_record.languages),
            max_len=40,
        )

        merged_modalities = _merge_list(
            crawled.modalities,
            _merge_list(
                csv_record.modalities,
                guess_modalities_from_text(
                    crawled.title,
                    crawled.description_short,
                    merged_tags,
                    [
                        item.get("format") or item.get("encoding_format")
                        for item in resources_json
                    ],
                ),
            ),
        )

        merged_record = NormalizedDatasetRecord(
            source_dataset_key=crawled.source_dataset_key,
            record_hash=None,
            canonical_url=_choose(csv_record.canonical_url, crawled.canonical_url),
            landing_url=_choose(csv_record.landing_url, crawled.landing_url),
            title=_choose(csv_record.title, crawled.title),
            subtitle=None,
            description_short=_choose(
                csv_record.description_short, crawled.description_short
            ),
            description_long=_choose(
                csv_record.description_long, crawled.description_long
            ),
            search_text=None,
            publisher_name=_choose(csv_record.publisher_name, crawled.publisher_name),
            domains=merged_domains,
            tasks=merged_tasks,
            modalities=merged_modalities,
            tags=merged_tags,
            languages=merged_languages,
            license_name=_choose(csv_record.license_name, crawled.license_name),
            license_url=_choose(csv_record.license_url, crawled.license_url),
            commercial_use_allowed=_choose(
                csv_record.commercial_use_allowed,
                crawled.commercial_use_allowed,
            ),
            access_type=_choose(csv_record.access_type, crawled.access_type),
            login_required=_choose(csv_record.login_required, crawled.login_required),
            approval_required=_choose(
                csv_record.approval_required, crawled.approval_required
            ),
            payment_required=_choose(
                csv_record.payment_required, crawled.payment_required
            ),
            is_restricted=_choose(csv_record.is_restricted, crawled.is_restricted),
            source_created_at=_choose(
                csv_record.source_created_at, crawled.source_created_at
            ),
            source_updated_at=_choose(
                csv_record.source_updated_at, crawled.source_updated_at
            ),
            source_version=_choose(csv_record.source_version, crawled.source_version),
            row_count=_choose(csv_record.row_count, crawled.row_count),
            dataset_size_bytes=_choose(
                csv_record.dataset_size_bytes, crawled.dataset_size_bytes
            ),
            field_presence_json={},
            creators_json=[
                json.loads(item)
                for item in _merge_list(
                    [
                        json.dumps(item, ensure_ascii=False, sort_keys=True)
                        for item in (crawled.creators_json or [])
                    ],
                    [
                        json.dumps(item, ensure_ascii=False, sort_keys=True)
                        for item in (csv_record.creators_json or [])
                    ],
                )
            ],
            resources_json=resources_json,
            schema_json=_merge_dict(crawled.schema_json, csv_record.schema_json),
            metrics_json=_merge_dict(crawled.metrics_json, csv_record.metrics_json),
            extra_json=_merge_dict(crawled.extra_json, csv_record.extra_json),
            raw_json=_merge_dict(crawled.raw_json, csv_record.raw_json),
            status=_choose(crawled.status, csv_record.status) or "ACTIVE",
        )

        if not merged_record.domains:
            merged_record.domains = domains_from_urls(
                [
                    merged_record.canonical_url,
                    merged_record.landing_url,
                    *[
                        item.get("download_url")
                        for item in merged_record.resources_json
                        if isinstance(item, dict)
                    ],
                ]
            )

        merged_record.access_type = _infer_access_type(
            merged_record.access_type,
            login_required=merged_record.login_required,
            approval_required=merged_record.approval_required,
            payment_required=merged_record.payment_required,
            is_restricted=merged_record.is_restricted,
        )
        return merged_record


def _resolve_csv_path(explicit_csv_path: Optional[str]) -> Path:
    if explicit_csv_path:
        return Path(explicit_csv_path).resolve()

    candidates = sorted(CURRENT_DIR.glob("*.csv"))
    if not candidates:
        raise FileNotFoundError(
            "dataset 폴더에 CSV 파일이 없습니다. --csv 경로를 지정하거나 CSV를 dataset 폴더에 넣어주세요."
        )

    preferred = [
        path
        for path in candidates
        if "public" in path.name.casefold() or "공공" in path.name
    ]
    if preferred:
        return preferred[0].resolve()
    return candidates[0].resolve()


def _to_psycopg_dsn(dsn: str) -> str:
    prefix = "postgresql+asyncpg://"
    if dsn.startswith(prefix):
        return "postgresql://" + dsn[len(prefix) :]
    return dsn


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "공공데이터포털 dataset 메타데이터를 CSV에서 읽고, "
            "상세 페이지/스키마 크롤링으로 부족한 필드를 보강해 dataset 테이블에 upsert합니다."
        )
    )
    parser.add_argument(
        "--csv", default=None, help="CSV 경로. 생략 시 dataset 폴더 내 첫 CSV를 사용"
    )
    parser.add_argument("--limit", type=int, default=None, help="최대 upsert 건수")
    parser.add_argument(
        "--from-scratch", action="store_true", help="체크포인트 무시하고 처음부터 실행"
    )
    return parser


def run(args: argparse.Namespace) -> HarvestStats:
    settings = Settings()
    settings.validate()

    csv_path = _resolve_csv_path(args.csv)
    dsn = _to_psycopg_dsn(settings.database_url)

    with Database(dsn) as db:
        collector = FastPublicDataPortalCollector(
            db=db,
            settings=settings,
            csv_path=csv_path,
            enable_db_resume_fallback=not args.from_scratch,
        )
        stats = collector.run(
            resume=not args.from_scratch,
            limit=args.limit,
        )
        return stats


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    stats = run(args)
    print(
        json.dumps(
            {
                "status": "completed" if stats.failed_count == 0 else "partial_success",
                "collected_count": stats.collected_count,
                "upserted_count": stats.upserted_count,
                "failed_count": stats.failed_count,
                "errors_preview": stats.errors[:10],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

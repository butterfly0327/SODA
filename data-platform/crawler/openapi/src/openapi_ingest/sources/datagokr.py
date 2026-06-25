"""공공데이터포털 CSV → open_api 임포트 수집기."""
from __future__ import annotations

import asyncio
import csv
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import httpx

from ..base import BaseOpenApiCollector
from ..models import HarvestStats, NormalizedOpenApiRecord, OpenApiSourceDefinition

logger = logging.getLogger(__name__)

_SOURCE_CODE   = "DATAGOKR"
_PROVIDER_FIXED = "공공데이터포털"
_AUTH_TYPE     = "API_KEY"

_COL = {
    "목록번호": 0, "목록유형": 1, "목록명": 2, "분류체계": 4,
    "제공기관코드": 5, "제공기관": 6, "응답형식": 15, "키워드": 16,
    "설명": 22, "비용부과": 26, "비용내용": 27, "이용허락": 28,
    "API유형": 29, "트래픽": 30, "심의단계": 31, "목록URL": 33,
}

_CHECKPOINT_PATH = Path("datagokr_checkpoint.json")


def _get(row: list, col_name: str) -> str:
    idx = _COL[col_name]
    return row[idx].strip() if idx < len(row) else ""


def _parse_is_free(row: list) -> bool:
    val = _get(row, "비용부과").lower()
    return "무료" in val or val in {"", "-"}


def _parse_requires_approval(row: list) -> bool:
    return "자동" not in _get(row, "심의단계").lower()


def _parse_commercial_use(row: list) -> Optional[bool]:
    val = _get(row, "이용허락").lower()
    if "제한 없음" in val or "출처표시" in val:
        return True
    if "비영리" in val or "변경금지" in val:
        return False
    return None


def _parse_tags(row: list) -> list:
    raw = _get(row, "키워드")
    if not raw or raw == "-":
        return []
    return [t.strip() for t in re.split(r"[,，、\s]+", raw) if t.strip()][:10]


def _parse_response_format(row: list) -> Optional[str]:
    val = _get(row, "응답형식").upper()
    if not val or val == "-":
        return None
    if val in {"JSON", "XML", "JSON+XML"}:
        return val
    return None


def _parse_category(row: list) -> Optional[str]:
    val = _get(row, "분류체계")
    if not val or val == "-":
        return None
    parts = [p.strip() for p in val.split("-")]
    return parts[-1] if parts else val


def _build_detail_url(pk: str) -> str:
    return f"http://www.data.go.kr/data/{pk}/openapi.do"


def _extract_base_url(html: str) -> Optional[str]:
    matches = re.findall(r'oprtinUrl\s*=\s*["\']([^"\']+)["\']', html)
    if matches:
        parsed = urlparse(matches[0].strip())
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"

    apis_matches = re.findall(r'(https?://apis\.data\.go\.kr/[A-Za-z0-9_\-]+)', html)
    if apis_matches:
        parsed = urlparse(apis_matches[0])
        parts = parsed.path.strip("/").split("/")
        if parts:
            return f"{parsed.scheme}://{parsed.netloc}/{parts[0]}"

    openapi_matches = re.findall(
        r'(https?://openapi\.[a-zA-Z0-9\.\-]+\.(?:go|or)\.kr)', html
    )
    if openapi_matches:
        return openapi_matches[0]
    return None


async def _crawl_base_url(
    client: httpx.AsyncClient,
    pk: str,
    semaphore: asyncio.Semaphore,
    retry_count: int = 2,
    delay: float = 0.3,
) -> Optional[str]:
    url = _build_detail_url(pk)
    async with semaphore:
        for attempt in range(retry_count + 1):
            try:
                await asyncio.sleep(delay)
                r = await client.get(url, timeout=15.0)
                if r.status_code == 200:
                    return _extract_base_url(r.text)
                return None
            except Exception as exc:
                if attempt < retry_count:
                    await asyncio.sleep(1.0 * (attempt + 1))
                else:
                    logger.warning(f"[{pk}] 크롤링 실패: {type(exc).__name__}")
    return None


def _load_checkpoint() -> set:
    if _CHECKPOINT_PATH.exists():
        with open(_CHECKPOINT_PATH, encoding="utf-8") as f:
            data = json.load(f)
        keys = set(data.get("done_keys", []))
        logger.info(f"체크포인트 로드: {len(keys):,}개 기완료")
        return keys
    return set()


def _save_checkpoint(done_keys: set) -> None:
    with open(_CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump({"done_keys": list(done_keys), "saved_at": datetime.now().isoformat()}, f)


def _row_to_record(row: list, base_url: Optional[str]) -> NormalizedOpenApiRecord:
    pk = _get(row, "목록번호")
    resolved_base_url = base_url or "https://www.data.go.kr"
    return NormalizedOpenApiRecord(
        openapi_source_code=_SOURCE_CODE,
        source_openapi_key=f"DATAGOKR-{pk}",
        name=_get(row, "목록명") or None,
        description=_get(row, "설명") or None,
        provider=_get(row, "제공기관") or _PROVIDER_FIXED,
        base_url=resolved_base_url,
        docs_url=_get(row, "목록URL") or _build_detail_url(pk),
        auth_type=_AUTH_TYPE,
        category=_parse_category(row),
        tags=_parse_tags(row),
        is_free=_parse_is_free(row),
        requires_approval=_parse_requires_approval(row),
        pricing_note=_get(row, "트래픽") or _get(row, "비용내용") or None,
        commercial_use=_parse_commercial_use(row),
        response_format=_parse_response_format(row),
    )


class DatagoKRCollector(BaseOpenApiCollector):
    sources = [
        OpenApiSourceDefinition(
            source_code=_SOURCE_CODE,
            source_name="공공데이터포털",
            base_url="https://www.data.go.kr",
            collection_type="FILE",
        )
    ]

    async def collect(self) -> List[NormalizedOpenApiRecord]:
        # 단순 collect()는 사용하지 않음 — run()을 직접 오버라이드
        return []

    async def run(self, limit: Optional[int] = None, resume: bool = False, **kwargs) -> HarvestStats:
        """CSV 파일 읽기 + 상세페이지 크롤링 + DB upsert."""
        csv_path_str = self.settings.datagokr_csv_path
        if not csv_path_str:
            raise ValueError(
                "DATAGOKR_CSV_PATH 환경변수가 설정되지 않았습니다. "
                ".env 파일에 CSV 파일 경로를 지정하세요."
            )
        csv_path = Path(csv_path_str)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {csv_path}")

        logger.info(f"=== 공공데이터포털 CSV 임포트 시작: {csv_path} ===")

        # CSV 로드
        all_rows: list = []
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            next(reader)  # 헤더 스킵
            for row in reader:
                if len(row) > _COL["목록유형"] and row[_COL["목록유형"]].strip() == "API":
                    all_rows.append(row)
        logger.info(f"CSV 로드 완료: API 유형 {len(all_rows):,}개")

        if limit:
            all_rows = all_rows[:limit]
            logger.info(f"--limit {limit} 적용")

        done_keys: set = set()
        if resume:
            done_keys = _load_checkpoint()

        pending = [r for r in all_rows if f"DATAGOKR-{_get(r, '목록번호')}" not in done_keys]
        logger.info(f"처리 대상: {len(pending):,}개 (체크포인트 제외 {len(done_keys):,}개)")

        # source_id 확보
        source_id = await self.db.ensure_openapi_source(self.sources[0])

        semaphore = asyncio.Semaphore(self.settings.datagokr_concurrency)
        batch_size = self.settings.datagokr_batch_size
        total = len(pending)
        headers = {
            **self._http_headers,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(
            headers=headers, follow_redirects=True, verify=False, timeout=15.0
        ) as client:
            for batch_start in range(0, total, batch_size):
                batch = pending[batch_start: batch_start + batch_size]
                pks = [_get(r, "목록번호") for r in batch]

                try:
                    base_urls = await asyncio.gather(
                        *[_crawl_base_url(client, pk, semaphore) for pk in pks],
                        return_exceptions=True,
                    )
                    records = [
                        _row_to_record(row, None if isinstance(bu, Exception) else bu)
                        for row, bu in zip(batch, base_urls)
                    ]
                    n = await self.db.upsert_apis_batch(source_id, records)
                    self.stats.upserted_count += n
                    self.stats.collected_count += len(records)

                    for r in records:
                        done_keys.add(r.source_openapi_key)
                    _save_checkpoint(done_keys)

                    progress = min(batch_start + batch_size, total)
                    logger.info(f"진행: {progress:,}/{total:,} | 이번 배치: {n}건 upsert | 총 누계: {self.stats.upserted_count:,}건")

                except Exception as exc:
                    self.stats.failed_count += len(batch)
                    self.stats.errors.append(f"배치[{batch_start}:{batch_start+batch_size}] 실패: {exc}")
                    logger.error(f"배치 실패: {exc}")

        logger.info(f"=== 완료: {self.stats.upserted_count:,}건 upsert ===")
        return self.stats

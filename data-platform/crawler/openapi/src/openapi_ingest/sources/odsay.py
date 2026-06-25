"""ODsay 대중교통 API 수집기."""
from __future__ import annotations

import logging
from typing import List

import httpx
from bs4 import BeautifulSoup

from ..base import BaseOpenApiCollector
from ..models import NormalizedOpenApiRecord, OpenApiSourceDefinition
from ..utils import truncate

logger = logging.getLogger(__name__)

_SOURCE_CODE = "ODSAY"
_PROVIDER = "ODsay"
_BASE_URL = "https://api.odsay.com"
_DOCS_URL = "https://lab.odsay.com/guide/guide"
_AUTH_TYPE = "API_KEY"

_STATIC_APIS = [
    {"id": "ODSAY-SEARCH-PUBTRANS",   "name": "대중교통 경로탐색",       "endpoint": "/v1/api/searchPubTransPathT",    "category": "경로탐색", "tags": ["경로탐색", "대중교통", "길찾기"]},
    {"id": "ODSAY-SEARCH-PUBTRANS-S", "name": "대중교통 경로탐색(상세)", "endpoint": "/v1/api/searchPubTransPathS",    "category": "경로탐색", "tags": ["경로탐색", "대중교통"]},
    {"id": "ODSAY-BUS-LANE-INFO",     "name": "버스 노선 정보",          "endpoint": "/v1/api/busLaneDetail",          "category": "버스",     "tags": ["버스", "노선정보"]},
    {"id": "ODSAY-BUS-STATION-INFO",  "name": "버스 정류장 정보",        "endpoint": "/v1/api/stationInfo",            "category": "버스",     "tags": ["버스", "정류장"]},
    {"id": "ODSAY-BUS-LANE-LIST",     "name": "정류장 경유 노선 목록",   "endpoint": "/v1/api/stationPassInfo",        "category": "버스",     "tags": ["버스", "정류장", "노선"]},
    {"id": "ODSAY-BUS-REALTIME",      "name": "버스 실시간 도착정보",    "endpoint": "/v1/api/busRealtime",            "category": "버스",     "tags": ["버스", "실시간", "도착"]},
    {"id": "ODSAY-SUBWAY-STATION",    "name": "지하철 역 정보",          "endpoint": "/v1/api/subwayStationInfo",      "category": "지하철",   "tags": ["지하철", "역정보"]},
    {"id": "ODSAY-SUBWAY-LANE",       "name": "지하철 노선 정보",        "endpoint": "/v1/api/subwayLaneInfo",         "category": "지하철",   "tags": ["지하철", "노선"]},
    {"id": "ODSAY-SUBWAY-REALTIME",   "name": "지하철 실시간 도착정보",  "endpoint": "/v1/api/subwayRealtime",         "category": "지하철",   "tags": ["지하철", "실시간"]},
    {"id": "ODSAY-TRAIN-STATION",     "name": "기차 역 정보",            "endpoint": "/v1/api/trainStationInfo",       "category": "기차",     "tags": ["기차", "KTX", "역정보"]},
    {"id": "ODSAY-TRAIN-LANE",        "name": "기차 노선 정보",          "endpoint": "/v1/api/trainLaneInfo",          "category": "기차",     "tags": ["기차", "노선"]},
    {"id": "ODSAY-AIR-STATION",       "name": "공항 정보",               "endpoint": "/v1/api/airStationInfo",         "category": "항공",     "tags": ["항공", "공항"]},
    {"id": "ODSAY-AIR-LANE",          "name": "항공 노선 정보",          "endpoint": "/v1/api/airLaneInfo",            "category": "항공",     "tags": ["항공", "노선"]},
    {"id": "ODSAY-LOAD-LANE",         "name": "경로 노선 지도 데이터",   "endpoint": "/v1/api/loadLane",               "category": "지도",     "tags": ["지도", "경로", "폴리라인"]},
    {"id": "ODSAY-NEARBY-STATION",    "name": "주변 정류장/역 탐색",     "endpoint": "/v1/api/pointSearch",            "category": "탐색",     "tags": ["주변탐색", "정류장", "역"]},
]


def _parse_guide(raw_bytes: bytes) -> dict:
    try:
        html = raw_bytes.decode("euc-kr", errors="replace")
    except Exception:
        html = raw_bytes.decode("utf-8", errors="replace")

    soup = BeautifulSoup(html, "html.parser")
    descriptions: dict = {}
    for section in soup.select("h3, h4"):
        name = section.get_text(strip=True)
        if not name or len(name) < 3:
            continue
        desc_parts = []
        node = section.find_next_sibling()
        for _ in range(8):
            if not node:
                break
            if hasattr(node, "name") and node.name in {"h3", "h4"}:
                break
            if hasattr(node, "get_text"):
                txt = node.get_text(strip=True)
                if txt and len(txt) > 5 and not txt.startswith("http"):
                    desc_parts.append(txt[:200])
            node = node.find_next_sibling() if hasattr(node, "find_next_sibling") else None
        if desc_parts:
            descriptions[name] = " ".join(desc_parts[:2])
    return descriptions


class ODsayCollector(BaseOpenApiCollector):
    sources = [
        OpenApiSourceDefinition(
            source_code=_SOURCE_CODE,
            source_name="ODsay 대중교통",
            base_url=_BASE_URL,
            collection_type="CRAWL",
        )
    ]

    async def collect(self) -> List[NormalizedOpenApiRecord]:
        descriptions: dict = {}
        headers = {**self._http_headers, "Referer": "https://lab.odsay.com/"}
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            try:
                r = await client.get(_DOCS_URL, timeout=30.0)
                r.raise_for_status()
                descriptions = _parse_guide(r.content)
                logger.info(f"[ODsay] 가이드 파싱: {len(descriptions)}개 설명")
            except Exception as exc:
                logger.warning(f"[ODsay] 가이드 파싱 실패: {exc}")

        records: List[NormalizedOpenApiRecord] = []
        for api in _STATIC_APIS:
            desc = None
            for key, val in descriptions.items():
                if api["name"] in key or key in api["name"]:
                    desc = val
                    break
            records.append(
                NormalizedOpenApiRecord(
                    openapi_source_code=_SOURCE_CODE,
                    source_openapi_key=api["id"],
                    name=api["name"],
                    description=truncate(desc),
                    provider=_PROVIDER,
                    base_url=_BASE_URL,
                    docs_url=_DOCS_URL,
                    auth_type=_AUTH_TYPE,
                    category=api["category"],
                    tags=api.get("tags", []),
                    is_free=False,
                    requires_approval=True,
                    pricing_note="유료 플랜 기반 (무료 체험 제공)",
                    commercial_use=True,
                    response_format="JSON",
                )
            )

        logger.info(f"[ODsay] 총 {len(records)}개 수집")
        return records

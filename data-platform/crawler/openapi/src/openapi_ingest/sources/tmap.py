"""T맵 API (SKT) 수집기."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import List

import httpx
from bs4 import BeautifulSoup

from ..base import BaseOpenApiCollector
from ..models import NormalizedOpenApiRecord, OpenApiSourceDefinition
from ..utils import truncate

logger = logging.getLogger(__name__)

_SOURCE_CODE = "TMAP_SKT"
_PROVIDER = "SK텔레콤"
_BASE_URL = "https://apis.openapi.sk.com"
_DOCS_BASE = "https://developers.sktelecom.com"
_AUTH_TYPE = "API_KEY"

_STATIC_APIS = [
    {"id": "TMAP-ROUTE-PEDESTRIAN", "name": "보행자 경로탐색",     "endpoint": "/tmap/routes/pedestrian",          "category": "경로탐색",  "tags": ["경로탐색", "보행자", "도보"],       "docs_url": f"{_DOCS_BASE}/apis/detail?apiCode=tmap-route"},
    {"id": "TMAP-ROUTE-DRIVING",    "name": "자동차 경로탐색",     "endpoint": "/tmap/routes",                     "category": "경로탐색",  "tags": ["경로탐색", "자동차", "내비"],       "docs_url": f"{_DOCS_BASE}/apis/detail?apiCode=tmap-route"},
    {"id": "TMAP-ROUTE-TRANSIT",    "name": "대중교통 경로탐색",   "endpoint": "/tmap/routes/transit",             "category": "경로탐색",  "tags": ["경로탐색", "대중교통", "버스", "지하철"], "docs_url": f"{_DOCS_BASE}/apis/detail?apiCode=tmap-route"},
    {"id": "TMAP-TRAFFIC",          "name": "실시간 교통정보",     "endpoint": "/tmap/traffic",                    "category": "교통정보",  "tags": ["교통정보", "실시간", "혼잡도"],     "docs_url": f"{_DOCS_BASE}/apis/detail?apiCode=tmap-traffic"},
    {"id": "TMAP-POI-SEARCH",       "name": "POI 통합검색",        "endpoint": "/tmap/pois",                       "category": "장소/검색", "tags": ["POI", "장소검색", "키워드"],        "docs_url": f"{_DOCS_BASE}/apis/detail?apiCode=tmap-poi"},
    {"id": "TMAP-POI-DETAIL",       "name": "POI 상세정보",        "endpoint": "/tmap/pois/{poiId}",               "category": "장소/검색", "tags": ["POI", "장소", "상세정보"],          "docs_url": f"{_DOCS_BASE}/apis/detail?apiCode=tmap-poi"},
    {"id": "TMAP-REVERSE-GEOCODE",  "name": "역방향 지오코딩",     "endpoint": "/tmap/geo/reversegeocoding",       "category": "지오코딩",  "tags": ["역방향지오코딩", "좌표", "주소변환"], "docs_url": f"{_DOCS_BASE}/apis/detail?apiCode=tmap-reversegeocode"},
    {"id": "TMAP-GEOCODE",          "name": "지오코딩",            "endpoint": "/tmap/geo/fullAddrGeo",            "category": "지오코딩",  "tags": ["지오코딩", "주소", "좌표변환"],     "docs_url": f"{_DOCS_BASE}/apis/detail?apiCode=tmap-reversegeocode"},
    {"id": "TMAP-RASTER",           "name": "지도 이미지 (Raster)","endpoint": "/tmap/raster",                     "category": "지도",      "tags": ["지도", "이미지", "타일"],           "docs_url": f"{_DOCS_BASE}/apis/detail?apiCode=tmap-raster"},
    {"id": "TMAP-STATISTICS-ROUTE", "name": "통계 경로탐색",       "endpoint": "/tmap/routes/routeSequential30",   "category": "경로탐색",  "tags": ["통계", "경로", "배달"],             "docs_url": f"{_DOCS_BASE}/apis"},
]


def _parse_tmap_doc(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    result: dict = {}
    h1 = soup.select_one("h1")
    if h1:
        result["title"] = h1.get_text(strip=True)
    for p in soup.select("p"):
        txt = p.get_text(strip=True)
        if len(txt) > 20:
            result["description"] = txt[:500]
            break
    for code in soup.select("code, pre"):
        txt = code.get_text(strip=True)
        if txt.startswith("/tmap/") or "openapi.sk.com" in txt:
            result.setdefault("endpoint", txt.split("\n")[0][:100])
            break
    codes_text = [c.get_text(strip=True).upper() for c in soup.select("code")]
    if "JSON" in codes_text:
        result["response_format"] = "JSON"
    return result


class TmapCollector(BaseOpenApiCollector):
    sources = [
        OpenApiSourceDefinition(
            source_code=_SOURCE_CODE,
            source_name="T맵 API (SKT)",
            base_url=_BASE_URL,
            collection_type="CRAWL",
        )
    ]

    async def collect(self) -> List[NormalizedOpenApiRecord]:
        unique_urls = list({api["docs_url"]: None for api in _STATIC_APIS}.keys())
        headers = {**self._http_headers, "Referer": f"{_DOCS_BASE}/"}

        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            tasks = [client.get(url, timeout=30.0) for url in unique_urls]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

        url_to_detail: dict = {}
        for url, resp in zip(unique_urls, responses):
            if isinstance(resp, Exception) or resp.status_code >= 400:
                url_to_detail[url] = {}
            else:
                url_to_detail[url] = _parse_tmap_doc(resp.text)

        records: List[NormalizedOpenApiRecord] = []
        for api in _STATIC_APIS:
            detail = url_to_detail.get(api["docs_url"], {})
            records.append(
                NormalizedOpenApiRecord(
                    openapi_source_code=_SOURCE_CODE,
                    source_openapi_key=api["id"],
                    name=api["name"],
                    description=truncate(detail.get("description")),
                    provider=_PROVIDER,
                    base_url=_BASE_URL,
                    docs_url=api["docs_url"],
                    auth_type=_AUTH_TYPE,
                    category=api["category"],
                    tags=api.get("tags", []),
                    is_free=False,
                    requires_approval=True,
                    pricing_note="SKT 개발자 포털 가입 후 트래픽 기반 과금",
                    commercial_use=True,
                    response_format=detail.get("response_format", "JSON"),
                )
            )

        logger.info(f"[Tmap] 총 {len(records)}개 수집")
        return records

"""네이버 클라우드 플랫폼 Maps API 수집기."""
from __future__ import annotations

import asyncio
import logging
from typing import List

import httpx
from bs4 import BeautifulSoup

from ..base import BaseOpenApiCollector
from ..models import NormalizedOpenApiRecord, OpenApiSourceDefinition
from ..utils import normalize_response_format, truncate

logger = logging.getLogger(__name__)

_SOURCE_CODE = "NAVER_CLOUD_MAPS"
_PROVIDER = "네이버 클라우드 플랫폼"
_BASE_URL = "https://naveropenapi.apigw.ntruss.com"
_AUTH_TYPE = "API_KEY"

_API_PAGES = [
    {
        "id":       "NAVER-MAP-GEOCODING",
        "name":     "Geocoding",
        "url":      "https://api.ncloud-docs.com/docs/ai-naver-mapsgeocoding",
        "endpoint": "/map-geocode/v2/geocode",
        "method":   "GET",
        "category": "지도/위치",
        "tags":     ["geocoding", "주소변환", "좌표"],
    },
    {
        "id":       "NAVER-MAP-REVERSE-GEOCODING",
        "name":     "Reverse Geocoding",
        "url":      "https://api.ncloud-docs.com/docs/ai-naver-mapsreversegeocoding",
        "endpoint": "/map-reversegeocode/v2/gc",
        "method":   "GET",
        "category": "지도/위치",
        "tags":     ["reverse-geocoding", "좌표변환", "주소"],
    },
    {
        "id":       "NAVER-MAP-DIRECTIONS5",
        "name":     "Directions 5",
        "url":      "https://api.ncloud-docs.com/docs/ai-naver-mapsdirections",
        "endpoint": "/map-direction/v1/driving",
        "method":   "GET",
        "category": "경로탐색",
        "tags":     ["directions", "경로", "내비"],
    },
    {
        "id":       "NAVER-MAP-DIRECTIONS15",
        "name":     "Directions 15",
        "url":      "https://api.ncloud-docs.com/docs/ai-naver-mapsdirections15",
        "endpoint": "/map-direction-15/v1/driving",
        "method":   "GET",
        "category": "경로탐색",
        "tags":     ["directions", "경유지", "경로"],
    },
    {
        "id":       "NAVER-MAP-STATIC",
        "name":     "Static Map",
        "url":      "https://api.ncloud-docs.com/docs/ai-naver-mapsstaticmap",
        "endpoint": "/map-static/v2/raster",
        "method":   "GET",
        "category": "지도",
        "tags":     ["static-map", "이미지", "지도"],
    },
    {
        "id":       "NAVER-MAP-SNAPTOROADS",
        "name":     "Snap To Roads",
        "url":      "https://api.ncloud-docs.com/docs/ai-naver-mapssnaptoroads",
        "endpoint": "/map-snaptoroads/v1/snap",
        "method":   "GET",
        "category": "경로탐색",
        "tags":     ["snap-to-roads", "GPS보정", "경로"],
    },
    {
        "id":       "NAVER-MAP-DISTANCE-MATRIX",
        "name":     "Distance Matrix",
        "url":      "https://api.ncloud-docs.com/docs/ai-naver-mapsdistancematrix",
        "endpoint": "/map-matrix/v1/driving",
        "method":   "GET",
        "category": "경로탐색",
        "tags":     ["distance-matrix", "거리행렬", "시간"],
    },
]


def _parse_ncp_doc(html: str, api_info: dict) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    result = dict(api_info)

    h1 = soup.select_one("h1")
    if h1:
        result["official_name"] = h1.get_text(strip=True)

    for p in soup.select("p"):
        txt = p.get_text(strip=True)
        if len(txt) > 20:
            result["description"] = txt[:500]
            break

    codes = [c.get_text(strip=True) for c in soup.select("code")]
    for code in codes:
        if code.startswith("/map-") or "apigw.ntruss" in code:
            if not result.get("endpoint"):
                result["endpoint"] = code
            break

    fmt_tags = [c for c in codes if c.upper() in {"JSON", "XML", "PNG", "JPEG"}]
    if fmt_tags:
        result["response_format"] = fmt_tags[0].upper()

    return result


class NaverMapCollector(BaseOpenApiCollector):
    sources = [
        OpenApiSourceDefinition(
            source_code=_SOURCE_CODE,
            source_name="네이버 클라우드 플랫폼 Maps",
            base_url=_BASE_URL,
            collection_type="CRAWL",
        )
    ]

    async def collect(self) -> List[NormalizedOpenApiRecord]:
        async with httpx.AsyncClient(
            headers=self._http_headers, follow_redirects=True
        ) as client:
            tasks = [client.get(p["url"], timeout=30.0) for p in _API_PAGES]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

        records: List[NormalizedOpenApiRecord] = []
        for api_info, resp in zip(_API_PAGES, responses):
            if isinstance(resp, Exception):
                logger.warning(f"[NaverMap/{api_info['name']}] 페치 실패: {resp}")
                parsed = dict(api_info)
            else:
                try:
                    parsed = _parse_ncp_doc(resp.text, api_info)
                except Exception as exc:
                    logger.warning(f"[NaverMap/{api_info['name']}] 파싱 실패: {exc}")
                    parsed = dict(api_info)

            records.append(
                NormalizedOpenApiRecord(
                    openapi_source_code=_SOURCE_CODE,
                    source_openapi_key=api_info["id"],
                    name=parsed.get("official_name") or api_info["name"],
                    description=truncate(parsed.get("description")),
                    provider=_PROVIDER,
                    base_url=_BASE_URL,
                    docs_url=api_info["url"],
                    auth_type=_AUTH_TYPE,
                    category=api_info["category"],
                    tags=api_info.get("tags", []),
                    is_free=False,
                    requires_approval=False,
                    pricing_note="NCP 크레딧 기반 과금",
                    commercial_use=True,
                    response_format=normalize_response_format(
                        parsed.get("response_format", "JSON")
                    ),
                )
            )

        logger.info(f"[NaverMap] 총 {len(records)}개 수집")
        return records

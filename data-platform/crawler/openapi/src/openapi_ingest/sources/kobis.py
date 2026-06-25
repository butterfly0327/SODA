"""영화·공연 API 수집기 (KOBIS / KMDb / KOPIS)."""
from __future__ import annotations

import logging
from typing import List

import httpx
from bs4 import BeautifulSoup

from ..base import BaseOpenApiCollector
from ..models import NormalizedOpenApiRecord, OpenApiSourceDefinition

logger = logging.getLogger(__name__)

_KOBIS_CODE = "KOBIS"
_KMDB_CODE  = "KMDB"
_KOPIS_CODE = "KOPIS"

_KOBIS_BASE = "http://www.kobis.or.kr/kobisopenapi/webservice/rest"
_KMDB_BASE  = "http://api.koreafilm.or.kr"
_KOPIS_BASE = "http://kopis.or.kr/openApi/restful"

_KOBIS_DOCS = "https://www.kobis.or.kr/kobisopenapi/homepg/apiservice/searchServiceInfo.do"
_KMDB_DOCS  = "https://www.kmdb.or.kr/info/api/apiDetail/6"
_KOPIS_DOCS = "https://www.kopis.or.kr/por/cs/openapi/openApiInfo.do"

_KOBIS_APIS = [
    {"id": "KOBIS-BOXOFFICE-DAILY",  "name": "일별 박스오피스",      "endpoint": "/boxoffice/searchDailyBoxOfficeList.json",   "category": "박스오피스", "description": "일별 박스오피스 순위 및 관객수 정보를 조회합니다."},
    {"id": "KOBIS-BOXOFFICE-WEEKLY", "name": "주간/주말 박스오피스", "endpoint": "/boxoffice/searchWeeklyBoxOfficeList.json",  "category": "박스오피스", "description": "주간 또는 주말 박스오피스 순위 및 관객수 정보를 조회합니다."},
    {"id": "KOBIS-MOVIE-LIST",       "name": "영화 목록 조회",       "endpoint": "/movie/searchMovieList.json",                "category": "영화",       "description": "제목, 감독, 배우 등 조건으로 영화 목록을 조회합니다."},
    {"id": "KOBIS-MOVIE-DETAIL",     "name": "영화 상세 조회",       "endpoint": "/movie/searchMovieInfo.json",                "category": "영화",       "description": "영화코드로 제작사, 배급사, 감독, 배우, 등급 등 상세 정보를 조회합니다."},
    {"id": "KOBIS-COMPANY-LIST",     "name": "영화사 목록 조회",     "endpoint": "/company/searchCompanyList.json",            "category": "영화사",     "description": "영화 제작사·배급사 목록을 조회합니다."},
    {"id": "KOBIS-COMPANY-DETAIL",   "name": "영화사 상세 조회",     "endpoint": "/company/searchCompanyInfo.json",            "category": "영화사",     "description": "영화사코드로 영화사 상세 정보와 참여 영화 목록을 조회합니다."},
    {"id": "KOBIS-PEOPLE-LIST",      "name": "영화인 목록 조회",     "endpoint": "/people/searchPeopleList.json",              "category": "영화인",     "description": "이름, 직종 등 조건으로 감독·배우 등 영화인 목록을 조회합니다."},
    {"id": "KOBIS-PEOPLE-DETAIL",    "name": "영화인 상세 조회",     "endpoint": "/people/searchPeopleInfo.json",              "category": "영화인",     "description": "영화인코드로 필모그래피 등 영화인 상세 정보를 조회합니다."},
    {"id": "KOBIS-THEATER-LIST",     "name": "상영관 목록 조회",     "endpoint": "/theater/searchTheaterList.json",            "category": "상영관",     "description": "상영관 목록을 지역 등 조건으로 조회합니다."},
    {"id": "KOBIS-THEATER-DETAIL",   "name": "상영관 상세 조회",     "endpoint": "/theater/searchTheaterInfo.json",            "category": "상영관",     "description": "상영관코드로 상영관 상세 정보 및 스크린 정보를 조회합니다."},
]

_KMDB_APIS = [
    {"id": "KMDB-MOVIE-SEARCH",  "name": "영화 정보 검색 (다건)", "endpoint": "/openapi-data2/wisenut/search_api/search_json2.jsp", "category": "영화정보", "description": "제목, 감독, 배우, 장르 등 조건으로 한국영화 상세 정보를 검색합니다."},
    {"id": "KMDB-MOVIE-DETAIL",  "name": "영화 상세 조회 (단건)", "endpoint": "/openapi-data2/wisenut/search_api/search_json2.jsp", "category": "영화정보", "description": "movieId로 영화 단건의 전체 메타데이터를 조회합니다."},
    {"id": "KMDB-VEGA-SEARCH",   "name": "통합 검색 (VEGA)",      "endpoint": "/openapi-data2/wisenut/search_api/search_json.jsp",  "category": "통합검색", "description": "영화 제목 및 인물 통합 검색 API입니다."},
    {"id": "KMDB-PEOPLE-SEARCH", "name": "영화인 검색",           "endpoint": "/openapi-data2/wisenut/search_api/search_json2.jsp", "category": "영화인",   "description": "감독, 배우 등 영화인 정보를 검색합니다."},
]

_KOPIS_APIS = [
    {"id": "KOPIS-PERF-LIST",       "name": "공연 목록 조회",     "endpoint": "/pblprfr",          "category": "공연",     "description": "공연 기간, 장르, 지역 등 조건으로 공연 목록을 조회합니다."},
    {"id": "KOPIS-PERF-DETAIL",     "name": "공연 상세 조회",     "endpoint": "/pblprfr/{mt20id}", "category": "공연",     "description": "공연 ID로 출연진, 런타임, 가격 등 공연 상세 정보를 조회합니다."},
    {"id": "KOPIS-FACILITY-LIST",   "name": "공연시설 목록 조회", "endpoint": "/prfplc",           "category": "공연시설", "description": "공연장·시설 목록을 지역, 시설명 등으로 조회합니다."},
    {"id": "KOPIS-FACILITY-DETAIL", "name": "공연시설 상세 조회", "endpoint": "/prfplc/{mt10id}",  "category": "공연시설", "description": "시설 ID로 공연장 상세 정보 및 좌석 구성을 조회합니다."},
    {"id": "KOPIS-BOXOFFICE-PERF",  "name": "공연 박스오피스",    "endpoint": "/boxoffice",        "category": "박스오피스","description": "기간별 공연 예매 순위 및 예매율 정보를 조회합니다."},
    {"id": "KOPIS-STATS-PERF",      "name": "공연 통계",          "endpoint": "/prfsts",           "category": "통계",     "description": "기간별 공연 건수, 공연 회차, 매출액 등 통계 정보를 조회합니다."},
    {"id": "KOPIS-STATS-FACILITY",  "name": "공연시설 통계",      "endpoint": "/prfplcsts",        "category": "통계",     "description": "공연시설별 통계 정보를 조회합니다."},
    {"id": "KOPIS-GENRE-LIST",      "name": "장르 코드 조회",     "endpoint": "/genre",            "category": "코드",     "description": "공연 장르 분류 코드 목록을 조회합니다."},
]


class KobisCollector(BaseOpenApiCollector):
    sources = [
        OpenApiSourceDefinition(source_code=_KOBIS_CODE, source_name="영화진흥위원회 오픈API",  base_url=_KOBIS_BASE, collection_type="CRAWL"),
        OpenApiSourceDefinition(source_code=_KMDB_CODE,  source_name="한국영화데이터베이스",    base_url=_KMDB_BASE,  collection_type="CRAWL"),
        OpenApiSourceDefinition(source_code=_KOPIS_CODE, source_name="공연예술통합전산망",       base_url=_KOPIS_BASE, collection_type="CRAWL"),
    ]

    async def collect(self) -> List[NormalizedOpenApiRecord]:
        # 문서 페이지 파싱으로 description 보강 시도
        kobis_apis = [dict(a) for a in _KOBIS_APIS]
        kopis_apis = [dict(a) for a in _KOPIS_APIS]

        async with httpx.AsyncClient(headers=self._http_headers, follow_redirects=True) as client:
            # KOBIS
            try:
                r = await client.get(_KOBIS_DOCS, timeout=15.0)
                soup = BeautifulSoup(r.text, "html.parser")
                for row in soup.select("table tr"):
                    cells = row.select("td")
                    if len(cells) >= 2:
                        api_name = cells[0].get_text(strip=True)
                        desc = cells[1].get_text(strip=True)[:300]
                        for api in kobis_apis:
                            if api_name and api_name in api["name"]:
                                api["description"] = desc
                logger.info("[KOBIS] 문서 파싱 완료")
            except Exception as exc:
                logger.warning(f"[KOBIS] 문서 파싱 실패: {exc}")

            # KOPIS
            try:
                r = await client.get(_KOPIS_DOCS, timeout=15.0)
                soup = BeautifulSoup(r.text, "html.parser")
                for table in soup.select("table"):
                    for row in table.select("tr"):
                        tds = row.select("td")
                        if len(tds) >= 3:
                            ep = tds[0].get_text(strip=True)
                            desc = tds[2].get_text(strip=True)[:300]
                            for api in kopis_apis:
                                if api["endpoint"].split("/")[-1] in ep:
                                    api["description"] = desc
                logger.info("[KOPIS] 문서 파싱 완료")
            except Exception as exc:
                logger.warning(f"[KOPIS] 문서 파싱 실패: {exc}")

        records: List[NormalizedOpenApiRecord] = []

        for api in kobis_apis:
            records.append(NormalizedOpenApiRecord(
                openapi_source_code=_KOBIS_CODE,
                source_openapi_key=api["id"],
                name=api["name"],
                description=api.get("description"),
                provider="영화진흥위원회",
                base_url=_KOBIS_BASE,
                docs_url=_KOBIS_DOCS,
                auth_type="API_KEY",
                category=api["category"],
                tags=["영화", "박스오피스", "KOBIS"],
                is_free=True,
                requires_approval=False,
                pricing_note="공공 API 무료",
                commercial_use=True,
                response_format="JSON",
            ))

        for api in _KMDB_APIS:
            records.append(NormalizedOpenApiRecord(
                openapi_source_code=_KMDB_CODE,
                source_openapi_key=api["id"],
                name=api["name"],
                description=api.get("description"),
                provider="한국영화진흥원",
                base_url=_KMDB_BASE,
                docs_url=_KMDB_DOCS,
                auth_type="API_KEY",
                category=api["category"],
                tags=["영화", "KMDb", "한국영화"],
                is_free=True,
                requires_approval=False,
                pricing_note="공공 API 무료",
                commercial_use=True,
                response_format="JSON",
            ))

        for api in kopis_apis:
            records.append(NormalizedOpenApiRecord(
                openapi_source_code=_KOPIS_CODE,
                source_openapi_key=api["id"],
                name=api["name"],
                description=api.get("description"),
                provider="예술경영지원센터",
                base_url=_KOPIS_BASE,
                docs_url=_KOPIS_DOCS,
                auth_type="API_KEY",
                category=api["category"],
                tags=["공연", "KOPIS", "문화예술"],
                is_free=True,
                requires_approval=False,
                pricing_note="공공 API 무료",
                commercial_use=True,
                response_format="JSON",
            ))

        logger.info(f"[Kobis] 총 {len(records)}개 수집 (KOBIS:{len(kobis_apis)}, KMDb:{len(_KMDB_APIS)}, KOPIS:{len(kopis_apis)})")
        return records

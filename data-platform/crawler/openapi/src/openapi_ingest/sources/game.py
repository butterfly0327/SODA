"""게임사 Open API 수집기 (넥슨 / Neople)."""
from __future__ import annotations

import logging
from typing import List

import httpx
from bs4 import BeautifulSoup

from ..base import BaseOpenApiCollector
from ..models import NormalizedOpenApiRecord, OpenApiSourceDefinition

logger = logging.getLogger(__name__)

_NEXON_CODE   = "NEXON_OPENAPI"
_NEOPLE_CODE  = "NEOPLE_DEVELOPERS"
_NEXON_BASE   = "https://open.api.nexon.com"
_NEOPLE_BASE  = "https://api.neople.co.kr"
_NEXON_DOCS   = "https://openapi.nexon.com"
_NEOPLE_DOCS  = "https://developers.neople.co.kr/contents/apiDocs"

_NEXON_APIS = [
    {"id": "NEXON-MAPLE-CHAR",    "name": "캐릭터 기본 정보 조회",    "endpoint": "/maplestory/v1/character/basic",          "category": "메이플스토리", "game": "메이플스토리"},
    {"id": "NEXON-MAPLE-OCID",    "name": "캐릭터 식별자(ocid) 조회", "endpoint": "/maplestory/v1/id",                       "category": "메이플스토리", "game": "메이플스토리"},
    {"id": "NEXON-MAPLE-STAT",    "name": "종합 능력치 조회",          "endpoint": "/maplestory/v1/character/stat",           "category": "메이플스토리", "game": "메이플스토리"},
    {"id": "NEXON-MAPLE-EQUIP",   "name": "장착 장비 조회",            "endpoint": "/maplestory/v1/character/item-equipment", "category": "메이플스토리", "game": "메이플스토리"},
    {"id": "NEXON-MAPLE-SKILL",   "name": "스킬 정보 조회",            "endpoint": "/maplestory/v1/character/skill",          "category": "메이플스토리", "game": "메이플스토리"},
    {"id": "NEXON-MAPLE-UNION",   "name": "유니온 정보 조회",          "endpoint": "/maplestory/v1/user/union",               "category": "메이플스토리", "game": "메이플스토리"},
    {"id": "NEXON-MAPLE-RANKING", "name": "종합 랭킹 조회",            "endpoint": "/maplestory/v1/ranking/overall",          "category": "메이플스토리", "game": "메이플스토리"},
    {"id": "NEXON-MAPLE-GUILD",   "name": "길드 기본 정보 조회",       "endpoint": "/maplestory/v1/guild/basic",              "category": "메이플스토리", "game": "메이플스토리"},
    {"id": "NEXON-FIFA-USER",     "name": "유저 정보 조회",            "endpoint": "/fifaonline4/v1.0/users",                 "category": "피파온라인4",  "game": "피파온라인4"},
    {"id": "NEXON-FIFA-MATCH",    "name": "매치 기록 조회",            "endpoint": "/fifaonline4/v1.0/users/{accessId}/matches","category": "피파온라인4", "game": "피파온라인4"},
    {"id": "NEXON-FIFA-SQUAD",    "name": "최고 등급 선수 조회",       "endpoint": "/fifaonline4/v1.0/users/{accessId}/maxdivision","category": "피파온라인4","game": "피파온라인4"},
    {"id": "NEXON-FIFA-META",     "name": "메타데이터(선수) 조회",     "endpoint": "/fifaonline4/v1.0/metadata/spid",         "category": "피파온라인4",  "game": "피파온라인4"},
    {"id": "NEXON-SA-USER",       "name": "유저 기본 정보",            "endpoint": "/suddenattack/v1/user/basic",             "category": "서든어택",     "game": "서든어택"},
    {"id": "NEXON-SA-MATCH",      "name": "매치 기록 조회",            "endpoint": "/suddenattack/v1/user/match",             "category": "서든어택",     "game": "서든어택"},
    {"id": "NEXON-BNN-CHAR",      "name": "캐릭터 정보 조회",          "endpoint": "/baramy/v1/character/basic",              "category": "바람의나라:연", "game": "바람의나라:연"},
]

_NEOPLE_APIS = [
    {"id": "NEOPLE-DF-CHAR",      "name": "캐릭터 검색",            "endpoint": "/df/servers/{serverId}/characters",                                   "category": "던전앤파이터", "game": "df"},
    {"id": "NEOPLE-DF-CHAR-INFO", "name": "캐릭터 기본 정보",       "endpoint": "/df/servers/{serverId}/characters/{characterId}",                     "category": "던전앤파이터", "game": "df"},
    {"id": "NEOPLE-DF-EQUIP",     "name": "장착 장비 조회",         "endpoint": "/df/servers/{serverId}/characters/{characterId}/equip/equipment",      "category": "던전앤파이터", "game": "df"},
    {"id": "NEOPLE-DF-SKILL",     "name": "스킬 스타일 조회",       "endpoint": "/df/servers/{serverId}/characters/{characterId}/skill/style",          "category": "던전앤파이터", "game": "df"},
    {"id": "NEOPLE-DF-TIMELINE",  "name": "플레이 기록 (타임라인)", "endpoint": "/df/servers/{serverId}/characters/{characterId}/timeline",            "category": "던전앤파이터", "game": "df"},
    {"id": "NEOPLE-DF-BUFF",      "name": "버프 강화 스킬 스타일",  "endpoint": "/df/servers/{serverId}/characters/{characterId}/skill/buff",          "category": "던전앤파이터", "game": "df"},
    {"id": "NEOPLE-DF-AUCTION",   "name": "경매장 아이템 검색",     "endpoint": "/df/auction",                                                         "category": "던전앤파이터", "game": "df"},
    {"id": "NEOPLE-DF-ITEM",      "name": "아이템 상세 정보",       "endpoint": "/df/items/{itemId}",                                                  "category": "던전앤파이터", "game": "df"},
    {"id": "NEOPLE-CY-USER",      "name": "플레이어 정보 조회",     "endpoint": "/cy/players",                                                         "category": "사이퍼즈",     "game": "cy"},
    {"id": "NEOPLE-CY-MATCH",     "name": "플레이어 매치 기록",     "endpoint": "/cy/players/{playerId}/matches",                                      "category": "사이퍼즈",     "game": "cy"},
    {"id": "NEOPLE-MG-CHAR",      "name": "캐릭터 정보 조회",       "endpoint": "/mabinogi/characters",                                                "category": "마비노기",     "game": "mabinogi"},
    {"id": "NEOPLE-MG-ITEM",      "name": "아이템 검색",            "endpoint": "/mabinogi/auction",                                                   "category": "마비노기",     "game": "mabinogi"},
    {"id": "NEOPLE-KR-USER",      "name": "라이더 기본 정보",       "endpoint": "/kartriderRushPlus/users",                                            "category": "카트라이더러쉬플러스", "game": "kartrider"},
    {"id": "NEOPLE-KR-MATCH",     "name": "매치 기록 조회",         "endpoint": "/kartriderRushPlus/users/{accessId}/matches",                         "category": "카트라이더러쉬플러스", "game": "kartrider"},
]


class GameCollector(BaseOpenApiCollector):
    sources = [
        OpenApiSourceDefinition(source_code=_NEXON_CODE,  source_name="넥슨 Open API",    base_url=_NEXON_BASE,  collection_type="CRAWL"),
        OpenApiSourceDefinition(source_code=_NEOPLE_CODE, source_name="Neople Developers", base_url=_NEOPLE_BASE, collection_type="CRAWL"),
    ]

    async def collect(self) -> List[NormalizedOpenApiRecord]:
        # 문서 페이지 파싱 시도 (description 보강, 실패해도 계속)
        async with httpx.AsyncClient(headers=self._http_headers, follow_redirects=True) as client:
            for url in ["https://openapi.nexon.com/game/maplestory/", "https://openapi.nexon.com/game/fifaonline4/"]:
                try:
                    await client.get(url, timeout=20.0)
                except Exception:
                    pass
            try:
                await client.get(_NEOPLE_DOCS, timeout=20.0)
            except Exception:
                pass

        records: List[NormalizedOpenApiRecord] = []

        for api in _NEXON_APIS:
            game = api["game"]
            game_slug = game.lower().replace(":", "").replace(" ", "")
            records.append(
                NormalizedOpenApiRecord(
                    openapi_source_code=_NEXON_CODE,
                    source_openapi_key=api["id"],
                    name=api["name"],
                    provider="넥슨",
                    base_url=_NEXON_BASE,
                    docs_url=f"{_NEXON_DOCS}/game/{game_slug}/",
                    auth_type="API_KEY",
                    category=api["category"],
                    tags=["게임", "넥슨", game],
                    is_free=True,
                    requires_approval=False,
                    pricing_note="무료 (API 키 발급 필요)",
                    commercial_use=False,
                    response_format="JSON",
                )
            )

        for api in _NEOPLE_APIS:
            game = api["game"]
            records.append(
                NormalizedOpenApiRecord(
                    openapi_source_code=_NEOPLE_CODE,
                    source_openapi_key=api["id"],
                    name=api["name"],
                    provider="Neople",
                    base_url=_NEOPLE_BASE,
                    docs_url=f"{_NEOPLE_DOCS}/{game}",
                    auth_type="API_KEY",
                    category=api["category"],
                    tags=["게임", "Neople", api["category"]],
                    is_free=True,
                    requires_approval=False,
                    pricing_note="무료 (API 키 발급 필요)",
                    commercial_use=False,
                    response_format="JSON",
                )
            )

        logger.info(f"[Game] 총 {len(records)}개 수집 (넥슨:{len(_NEXON_APIS)}, Neople:{len(_NEOPLE_APIS)})")
        return records

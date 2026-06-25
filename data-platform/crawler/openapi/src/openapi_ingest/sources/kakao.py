"""카카오 Developers REST API 수집기."""
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

_SOURCE_CODE = "KAKAO_DEVELOPERS"
_PROVIDER = "카카오"
_AUTH_TYPE = "API_KEY"

_REST_API_PAGES = [
    ("로그인",       "kakaologin",        "https://developers.kakao.com/docs/latest/ko/kakaologin/rest-api"),
    ("로그인",       "kakaosync",         "https://developers.kakao.com/docs/latest/ko/kakaosync/rest-api"),
    ("커뮤니케이션", "kakaotalk-social",  "https://developers.kakao.com/docs/latest/ko/kakaotalk-social/rest-api"),
    ("커뮤니케이션", "message",           "https://developers.kakao.com/docs/latest/ko/message/rest-api"),
    ("커뮤니케이션", "kakaotalk-channel", "https://developers.kakao.com/docs/latest/ko/kakaotalk-channel/rest-api"),
    ("커뮤니케이션", "push-notification", "https://developers.kakao.com/docs/latest/ko/push-notification/rest-api"),
    ("커뮤니케이션", "talkCalendar",      "https://developers.kakao.com/docs/latest/ko/talk-calendar/rest-api"),
    ("카카오맵",     "maps",              "https://developers.kakao.com/docs/latest/ko/maps/rest-api"),
    ("카카오맵",     "local",             "https://developers.kakao.com/docs/latest/ko/local/rest-api"),
    ("검색",         "daum-search",       "https://developers.kakao.com/docs/latest/ko/daum-search/dev-guide"),
    ("사용자",       "kakaologin-user",   "https://developers.kakao.com/docs/latest/ko/kakaologin/rest-api"),
    ("비즈니스",     "moment",            "https://developers.kakao.com/docs/latest/ko/moment/rest-api"),
    ("비즈니스",     "business",          "https://developers.kakao.com/docs/latest/ko/business/rest-api"),
]


def _build_key(name: str, category: str, endpoint: str | None) -> str:
    slug = re.sub(r"[^a-zA-Z0-9가-힣]", "_", name).strip("_")[:40]
    cat = re.sub(r"[^a-zA-Z0-9가-힣]", "_", category).strip("_")[:15]
    ep = ""
    if endpoint:
        ep = re.sub(r"[^a-zA-Z0-9]", "_", endpoint)[-20:]
    return f"KAKAO-{cat}-{slug}-{ep}".rstrip("-_")


def _parse_rest_api_page(html: str, category: str, docs_url: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("article, main, div.content, div.docs-content") or soup
    headings = main.select("h2")
    skip_kw = {"main menu", "메뉴", "소개", "개요", "시작하기", "준비하기", "샘플", "sdk"}
    apis = []

    for h in headings:
        name = h.get_text(strip=True)
        if not name or len(name) < 2:
            continue
        if any(kw in name.lower() for kw in skip_kw):
            continue

        method = None
        endpoint = None
        desc_parts = []
        node = h.find_next_sibling()
        while node and (not hasattr(node, "name") or node.name != "h2"):
            if not hasattr(node, "select"):
                node = node.find_next_sibling()
                continue
            for code in node.select("code"):
                txt = code.get_text(strip=True)
                if txt in {"GET", "POST", "PUT", "DELETE", "PATCH"}:
                    if not method:
                        method = txt
                elif txt.startswith("https://") or txt.startswith("http://"):
                    if not endpoint:
                        endpoint = txt.split("?")[0]
            for p in node.select("p"):
                txt = p.get_text(strip=True)
                if txt and len(txt) > 10:
                    desc_parts.append(txt)
            node = node.find_next_sibling()

        base_url = "https://kapi.kakao.com"
        if endpoint:
            m = re.match(r"(https?://[^/]+)", endpoint)
            if m:
                base_url = m.group(1)

        apis.append({
            "name": name,
            "description": " ".join(desc_parts[:2])[:500] or None,
            "endpoint": endpoint,
            "method": method or "GET",
            "base_url": base_url,
            "category": category,
            "docs_url": docs_url,
        })
    return apis


class KakaoCollector(BaseOpenApiCollector):
    sources = [
        OpenApiSourceDefinition(
            source_code=_SOURCE_CODE,
            source_name="카카오 Developers",
            base_url="https://developers.kakao.com",
            collection_type="CRAWL",
        )
    ]

    async def collect(self) -> List[NormalizedOpenApiRecord]:
        seen_urls: set = set()
        unique_pages = []
        for cat, slug, url in _REST_API_PAGES:
            if url not in seen_urls:
                seen_urls.add(url)
                unique_pages.append((cat, slug, url))

        async with httpx.AsyncClient(headers=self._http_headers, follow_redirects=True) as client:
            tasks = [client.get(url, timeout=30.0) for _, _, url in unique_pages]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        all_apis = []
        for (cat, slug, url), result in zip(unique_pages, results):
            if isinstance(result, Exception) or result.status_code >= 400:
                logger.warning(f"[Kakao/{slug}] 페치 실패")
                continue
            apis = _parse_rest_api_page(result.text, cat, url)
            all_apis.extend(apis)

        records: List[NormalizedOpenApiRecord] = []
        for api in all_apis:
            records.append(
                NormalizedOpenApiRecord(
                    openapi_source_code=_SOURCE_CODE,
                    source_openapi_key=_build_key(api["name"], api["category"], api.get("endpoint")),
                    name=api["name"],
                    description=truncate(api.get("description")),
                    provider=_PROVIDER,
                    base_url=api.get("base_url") or "https://kapi.kakao.com",
                    docs_url=api["docs_url"],
                    auth_type=_AUTH_TYPE,
                    category=api["category"],
                    tags=[],
                    is_free=True,
                    requires_approval=False,
                    pricing_note="무료 쿼터 초과 시 유료",
                    commercial_use=True,
                    response_format="JSON",
                )
            )

        logger.info(f"[Kakao] 총 {len(records)}개 수집")
        return records

"""토스페이먼츠 API 수집기."""
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

_SOURCE_CODE = "TOSSPAYMENTS"
_PROVIDER = "토스페이먼츠"
_BASE_URL = "https://api.tosspayments.com"
_AUTH_TYPE = "API_KEY"

_DOC_PAGES = [
    ("결제",    "https://docs.tosspayments.com/reference"),
    ("빌링",    "https://docs.tosspayments.com/reference/billing"),
    ("정산",    "https://docs.tosspayments.com/reference/payment-flow"),
    ("브랜드페이", "https://docs.tosspayments.com/reference/brandpay"),
    ("현금영수증", "https://docs.tosspayments.com/reference/cash-receipt"),
]

_STATIC_APIS = [
    {"id": "TOSS-PAYMENT-CONFIRM",     "name": "결제 승인",             "endpoint": "/v1/payments/confirm",                  "category": "결제"},
    {"id": "TOSS-PAYMENT-GET-KEY",     "name": "paymentKey로 결제 조회", "endpoint": "/v1/payments/{paymentKey}",             "category": "결제"},
    {"id": "TOSS-PAYMENT-GET-ORDER",   "name": "orderId로 결제 조회",   "endpoint": "/v1/payments/orders/{orderId}",          "category": "결제"},
    {"id": "TOSS-PAYMENT-CANCEL",      "name": "결제 취소",             "endpoint": "/v1/payments/{paymentKey}/cancel",       "category": "결제"},
    {"id": "TOSS-BILLING-AUTH-CARD",   "name": "카드 빌링키 발급",      "endpoint": "/v1/billing/authorizations/card",         "category": "빌링"},
    {"id": "TOSS-BILLING-AUTH-ISSUE",  "name": "빌링키 발급 요청",      "endpoint": "/v1/billing/authorizations/issue",        "category": "빌링"},
    {"id": "TOSS-BILLING-CHARGE",      "name": "빌링키로 결제",         "endpoint": "/v1/billing/{billingKey}",               "category": "빌링"},
    {"id": "TOSS-CARD-PROMOTE",        "name": "카드 프로모션 조회",    "endpoint": "/v1/promotions/card",                    "category": "카드"},
    {"id": "TOSS-VIRTUAL-ACCOUNT",     "name": "가상계좌 발급",         "endpoint": "/v1/virtual-accounts",                   "category": "가상계좌"},
    {"id": "TOSS-CASH-RECEIPT",        "name": "현금영수증 발행",       "endpoint": "/v1/cash-receipts",                      "category": "현금영수증"},
    {"id": "TOSS-CASH-RECEIPT-CANCEL", "name": "현금영수증 취소",       "endpoint": "/v1/cash-receipts/{receiptKey}/cancel",  "category": "현금영수증"},
    {"id": "TOSS-BRANDPAY-AUTH",       "name": "브랜드페이 인증",       "endpoint": "/v1/brandpay/authorizations",            "category": "브랜드페이"},
    {"id": "TOSS-BRANDPAY-CHARGE",     "name": "브랜드페이 결제",       "endpoint": "/v1/brandpay/payments",                  "category": "브랜드페이"},
    {"id": "TOSS-SETTLE-SUMMARY",      "name": "정산 내역 조회",        "endpoint": "/v1/settlements",                        "category": "정산"},
]


def _build_key(name: str, category: str, endpoint: str | None) -> str:
    slug = re.sub(r"[^a-zA-Z0-9가-힣]", "_", name).strip("_")[:40]
    cat = re.sub(r"[^a-zA-Z0-9가-힣]", "_", category)[:15]
    ep = ""
    if endpoint:
        ep = re.sub(r"[^a-zA-Z0-9]", "_", endpoint)[-20:]
    return f"TOSS-{cat}-{slug}-{ep}".rstrip("-_")


def _parse_toss_docs(html: str, category: str, docs_url: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    apis = []
    headings = soup.select("h1, h2, h3")
    skip_kw = {"api & sdk", "개요", "sdk", "웹훅", "에러코드", "changelog", "note"}

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
        depth = 0
        while node and depth < 20:
            if hasattr(node, "name") and node.name in {"h1", "h2", "h3"}:
                break
            if hasattr(node, "select"):
                for code in node.select("code"):
                    txt = code.get_text(strip=True)
                    if txt in {"GET", "POST", "PUT", "DELETE", "PATCH"}:
                        if not method:
                            method = txt
                    elif txt.startswith("/v"):
                        if not endpoint:
                            endpoint = txt
                    elif "tosspayments" in txt and txt.startswith("https://"):
                        if not endpoint:
                            endpoint = re.sub(r"https://api\.tosspayments\.com", "", txt)
                for p in node.select("p"):
                    txt = p.get_text(strip=True)
                    if txt and len(txt) > 10:
                        desc_parts.append(txt)
            node = node.find_next_sibling()
            depth += 1

        if name and len(name) > 2:
            apis.append({
                "name": name,
                "description": " ".join(desc_parts[:2])[:500] or None,
                "endpoint": endpoint,
                "method": method or "POST",
                "category": category,
                "docs_url": docs_url,
            })
    return apis


class TossPaymentsCollector(BaseOpenApiCollector):
    sources = [
        OpenApiSourceDefinition(
            source_code=_SOURCE_CODE,
            source_name="토스페이먼츠",
            base_url=_BASE_URL,
            collection_type="CRAWL",
        )
    ]

    async def collect(self) -> List[NormalizedOpenApiRecord]:
        parsed_apis: list = []
        async with httpx.AsyncClient(headers=self._http_headers, follow_redirects=True) as client:
            tasks = [client.get(url, timeout=30.0) for _, url in _DOC_PAGES]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for (category, url), result in zip(_DOC_PAGES, results):
            if isinstance(result, Exception) or result.status_code != 200:
                logger.warning(f"[토스페이먼츠/{category}] 페치 실패")
                continue
            apis = _parse_toss_docs(result.text, category, url)
            parsed_apis.extend(apis)

        # 파싱 결과 부족 시 고정 목록 사용
        if len(parsed_apis) < 5:
            logger.info("[토스페이먼츠] 파싱 결과 부족 → 고정 목록 사용")
            parsed_apis = [{"docs_url": "https://docs.tosspayments.com/reference", **a} for a in _STATIC_APIS]
        else:
            parsed_names = {a["name"]: a for a in parsed_apis}
            for static in _STATIC_APIS:
                if static["name"] not in parsed_names:
                    parsed_apis.append({"docs_url": "https://docs.tosspayments.com/reference", **static})

        records: List[NormalizedOpenApiRecord] = []
        for api in parsed_apis:
            key = api.get("id") or _build_key(api["name"], api.get("category", "결제"), api.get("endpoint"))
            records.append(
                NormalizedOpenApiRecord(
                    openapi_source_code=_SOURCE_CODE,
                    source_openapi_key=key,
                    name=api["name"],
                    description=truncate(api.get("description")),
                    provider=_PROVIDER,
                    base_url=_BASE_URL,
                    docs_url=api.get("docs_url", "https://docs.tosspayments.com/reference"),
                    auth_type=_AUTH_TYPE,
                    category=api.get("category", "결제"),
                    tags=["결제", "PG", "토스페이먼츠"],
                    is_free=False,
                    requires_approval=True,
                    pricing_note="가맹점 계약 필요, 결제액 기반 수수료",
                    commercial_use=True,
                    response_format="JSON",
                )
            )

        logger.info(f"[토스페이먼츠] 총 {len(records)}개 수집")
        return records

"""한국투자증권 KIS Developers Open API 수집기."""
from __future__ import annotations

import logging
import re
from typing import List

import httpx
from bs4 import BeautifulSoup

from ..base import BaseOpenApiCollector
from ..models import NormalizedOpenApiRecord, OpenApiSourceDefinition
from ..utils import truncate

logger = logging.getLogger(__name__)

_SOURCE_CODE = "KIS_DEVELOPERS"
_PROVIDER = "한국투자증권"
_BASE_URL = "https://openapi.koreainvestment.com:9443"
_PORTAL = "https://apiportal.koreainvestment.com"
_AUTH_TYPE = "OAUTH"

_KIS_APIS = [
    # 국내주식 시세
    {"id": "KIS-FHKST01010100", "tr_id": "FHKST01010100", "name": "주식현재가 시세",        "endpoint": "/uapi/domestic-stock/v1/quotations/inquire-price",                  "category": "국내주식/시세"},
    {"id": "KIS-FHKST01010200", "tr_id": "FHKST01010200", "name": "주식현재가 체결",        "endpoint": "/uapi/domestic-stock/v1/quotations/inquire-ccnl",                   "category": "국내주식/시세"},
    {"id": "KIS-FHKST01010300", "tr_id": "FHKST01010300", "name": "주식현재가 일자별",      "endpoint": "/uapi/domestic-stock/v1/quotations/inquire-daily-price",            "category": "국내주식/시세"},
    {"id": "KIS-FHKST01010400", "tr_id": "FHKST01010400", "name": "주식현재가 호가잔량",    "endpoint": "/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn",   "category": "국내주식/시세"},
    {"id": "KIS-FHKST03010100", "tr_id": "FHKST03010100", "name": "주식 일봉/주봉/월봉",   "endpoint": "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",    "category": "국내주식/시세"},
    {"id": "KIS-FHKUP03500100", "tr_id": "FHKUP03500100", "name": "국내주식 업종 시세",     "endpoint": "/uapi/domestic-stock/v1/quotations/inquire-index-price",            "category": "국내주식/시세"},
    # 국내주식 주문
    {"id": "KIS-TTTC0802U",     "tr_id": "TTTC0802U",     "name": "주식 매수 주문",         "endpoint": "/uapi/domestic-stock/v1/trading/order-cash",                       "category": "국내주식/주문"},
    {"id": "KIS-TTTC0801U",     "tr_id": "TTTC0801U",     "name": "주식 매도 주문",         "endpoint": "/uapi/domestic-stock/v1/trading/order-cash",                       "category": "국내주식/주문"},
    {"id": "KIS-TTTC0803U",     "tr_id": "TTTC0803U",     "name": "주식 정정취소 주문",     "endpoint": "/uapi/domestic-stock/v1/trading/order-rvsecncl",                   "category": "국내주식/주문"},
    {"id": "KIS-TTTC8036R",     "tr_id": "TTTC8036R",     "name": "주식 잔고 조회",         "endpoint": "/uapi/domestic-stock/v1/trading/inquire-balance",                  "category": "국내주식/계좌"},
    {"id": "KIS-TTTC8001R",     "tr_id": "TTTC8001R",     "name": "주식 일별 주문체결 조회", "endpoint": "/uapi/domestic-stock/v1/trading/inquire-daily-ccld",               "category": "국내주식/계좌"},
    {"id": "KIS-TTTC8434R",     "tr_id": "TTTC8434R",     "name": "매수가능금액 조회",      "endpoint": "/uapi/domestic-stock/v1/trading/inquire-psbl-order",               "category": "국내주식/계좌"},
    # 해외주식 시세
    {"id": "KIS-HHDFS76200200", "tr_id": "HHDFS76200200", "name": "해외주식 현재가 상세",   "endpoint": "/uapi/overseas-stock/v1/quotations/price-detail",                  "category": "해외주식/시세"},
    {"id": "KIS-HHDFS76240000", "tr_id": "HHDFS76240000", "name": "해외주식 기간별 시세",   "endpoint": "/uapi/overseas-stock/v1/quotations/dailyprice",                    "category": "해외주식/시세"},
    {"id": "KIS-HHDFS00000300", "tr_id": "HHDFS00000300", "name": "해외주식 체결기준 현재가","endpoint": "/uapi/overseas-stock/v1/quotations/inquire-ccnl",                  "category": "해외주식/시세"},
    # 해외주식 주문
    {"id": "KIS-TTTT1002U",     "tr_id": "TTTT1002U",     "name": "해외주식 매수 주문",     "endpoint": "/uapi/overseas-stock/v1/trading/order",                            "category": "해외주식/주문"},
    {"id": "KIS-TTTT1006U",     "tr_id": "TTTT1006U",     "name": "해외주식 매도 주문",     "endpoint": "/uapi/overseas-stock/v1/trading/order",                            "category": "해외주식/주문"},
    {"id": "KIS-TTTS1003U",     "tr_id": "TTTS1003U",     "name": "해외주식 정정취소 주문", "endpoint": "/uapi/overseas-stock/v1/trading/order-rvsecncl",                   "category": "해외주식/주문"},
    {"id": "KIS-TTTS3012R",     "tr_id": "TTTS3012R",     "name": "해외주식 잔고 조회",     "endpoint": "/uapi/overseas-stock/v1/trading/inquire-balance",                  "category": "해외주식/계좌"},
    # OAuth / 토큰
    {"id": "KIS-OAUTH-TOKEN",   "tr_id": "",               "name": "접근토큰 발급",           "endpoint": "/oauth2/tokenP",                                                   "category": "인증"},
    {"id": "KIS-OAUTH-REVOKE",  "tr_id": "",               "name": "접근토큰 폐기",           "endpoint": "/oauth2/revokeP",                                                  "category": "인증"},
    {"id": "KIS-APPROVAL-KEY",  "tr_id": "",               "name": "웹소켓 접속키 발급",      "endpoint": "/oauth2/Approval",                                                 "category": "인증"},
    # 선물옵션
    {"id": "KIS-FHMIF10000000", "tr_id": "FHMIF10000000", "name": "선물옵션 현재가",         "endpoint": "/uapi/domestic-futureoption/v1/quotations/inquire-price",          "category": "선물옵션/시세"},
    {"id": "KIS-TTTO1101U",     "tr_id": "TTTO1101U",     "name": "선물옵션 매수 주문",      "endpoint": "/uapi/domestic-futureoption/v1/trading/order",                     "category": "선물옵션/주문"},
]


async def _fetch_portal_descriptions(client: httpx.AsyncClient) -> dict:
    descriptions: dict = {}
    try:
        r = await client.get(f"{_PORTAL}/apiservice", timeout=20.0)
        soup = BeautifulSoup(r.text, "html.parser")
        for code in soup.select("code, td, li"):
            txt = code.get_text(strip=True)
            if re.match(r"^[A-Z]{4}\d{8}$", txt):
                sibling = code.find_next_sibling()
                if sibling:
                    descriptions[txt] = sibling.get_text(strip=True)[:200]
        logger.info(f"[KIS] 포털 파싱: {len(descriptions)}개 설명")
    except Exception as exc:
        logger.warning(f"[KIS] 포털 파싱 실패: {exc}")
    return descriptions


class KisCollector(BaseOpenApiCollector):
    sources = [
        OpenApiSourceDefinition(
            source_code=_SOURCE_CODE,
            source_name="한국투자증권 KIS Developers",
            base_url=_BASE_URL,
            collection_type="CRAWL",
        )
    ]

    async def collect(self) -> List[NormalizedOpenApiRecord]:
        headers = {**self._http_headers, "Referer": _PORTAL}
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            descriptions = await _fetch_portal_descriptions(client)

        records: List[NormalizedOpenApiRecord] = []
        for api in _KIS_APIS:
            tr_id = api.get("tr_id", "")
            desc = descriptions.get(tr_id) if tr_id else None
            cat = api["category"]
            records.append(
                NormalizedOpenApiRecord(
                    openapi_source_code=_SOURCE_CODE,
                    source_openapi_key=api["id"],
                    name=api["name"],
                    description=truncate(desc),
                    provider=_PROVIDER,
                    base_url=_BASE_URL,
                    docs_url=f"{_PORTAL}/apiservice",
                    auth_type=_AUTH_TYPE,
                    category=cat,
                    tags=["주식", "증권", "KIS", cat.split("/")[0]],
                    is_free=True,
                    requires_approval=True,
                    pricing_note="계좌 개설 후 무료 사용 (모의투자 포함)",
                    commercial_use=True,
                    response_format="JSON",
                )
            )

        logger.info(f"[KIS] 총 {len(records)}개 수집")
        return records

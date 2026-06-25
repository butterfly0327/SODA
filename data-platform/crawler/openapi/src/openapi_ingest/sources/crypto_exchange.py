"""암호화폐 거래소 API 수집기 (업비트 / 빗썸 / 코인원)."""
from __future__ import annotations

import logging
from typing import List

import httpx

from ..base import BaseOpenApiCollector
from ..models import NormalizedOpenApiRecord, OpenApiSourceDefinition

logger = logging.getLogger(__name__)

_UPBIT_CODE   = "UPBIT"
_BITHUMB_CODE = "BITHUMB"
_COINONE_CODE = "COINONE"

_UPBIT_BASE   = "https://api.upbit.com"
_BITHUMB_BASE = "https://api.bithumb.com"
_COINONE_BASE = "https://api.coinone.co.kr"

_UPBIT_DOCS   = "https://docs.upbit.com/reference/"
_BITHUMB_DOCS = "https://apidocs.bithumb.com/"
_COINONE_DOCS = "https://docs.coinone.co.kr/"

_UPBIT_PUBLIC_APIS = [
    {"id": "UPBIT-MARKET-ALL",      "name": "마켓 코드 조회",      "endpoint": "/v1/market/all",             "method": "GET",  "category": "시세"},
    {"id": "UPBIT-TICKER",          "name": "현재가 정보 (Ticker)", "endpoint": "/v1/ticker",                 "method": "GET",  "category": "시세"},
    {"id": "UPBIT-ORDERBOOK",       "name": "호가 정보 조회",       "endpoint": "/v1/orderbook",              "method": "GET",  "category": "시세"},
    {"id": "UPBIT-TRADES-TICKS",    "name": "최근 체결 내역",       "endpoint": "/v1/trades/ticks",           "method": "GET",  "category": "시세"},
    {"id": "UPBIT-CANDLES-MINUTES", "name": "분(Minute) 캔들",     "endpoint": "/v1/candles/minutes/{unit}", "method": "GET",  "category": "시세"},
    {"id": "UPBIT-CANDLES-DAYS",    "name": "일(Day) 캔들",        "endpoint": "/v1/candles/days",           "method": "GET",  "category": "시세"},
    {"id": "UPBIT-CANDLES-WEEKS",   "name": "주(Week) 캔들",       "endpoint": "/v1/candles/weeks",          "method": "GET",  "category": "시세"},
    {"id": "UPBIT-CANDLES-MONTHS",  "name": "월(Month) 캔들",      "endpoint": "/v1/candles/months",         "method": "GET",  "category": "시세"},
]
_UPBIT_AUTH_APIS = [
    {"id": "UPBIT-ACCOUNTS",     "name": "전체 계좌 조회",    "endpoint": "/v1/accounts",          "method": "GET",    "category": "계좌"},
    {"id": "UPBIT-ORDERS",       "name": "주문 리스트 조회",  "endpoint": "/v1/orders",            "method": "GET",    "category": "주문"},
    {"id": "UPBIT-ORDER-POST",   "name": "주문하기",          "endpoint": "/v1/orders",            "method": "POST",   "category": "주문"},
    {"id": "UPBIT-ORDER-DELETE", "name": "주문 취소",         "endpoint": "/v1/order",             "method": "DELETE", "category": "주문"},
    {"id": "UPBIT-ORDER-CHANCE", "name": "주문 가능 정보",    "endpoint": "/v1/orders/chance",     "method": "GET",    "category": "주문"},
    {"id": "UPBIT-WITHDRAWS",    "name": "출금 리스트 조회",  "endpoint": "/v1/withdraws",         "method": "GET",    "category": "출금"},
    {"id": "UPBIT-DEPOSITS",     "name": "입금 리스트 조회",  "endpoint": "/v1/deposits",          "method": "GET",    "category": "입금"},
]

_BITHUMB_PUBLIC_APIS = [
    {"id": "BITHUMB-TICKER",        "name": "현재가 정보",        "endpoint": "/public/ticker/{order_currency}_{payment_currency}",                                "method": "GET", "category": "시세"},
    {"id": "BITHUMB-ORDERBOOK",     "name": "호가 정보",          "endpoint": "/public/orderbook/{order_currency}_{payment_currency}",                             "method": "GET", "category": "시세"},
    {"id": "BITHUMB-TRANSACTION",   "name": "최근 체결 내역",     "endpoint": "/public/transaction_history/{order_currency}_{payment_currency}",                    "method": "GET", "category": "시세"},
    {"id": "BITHUMB-ASSETS-STATUS", "name": "입출금 현황",        "endpoint": "/public/assetsstatus/{order_currency}",                                             "method": "GET", "category": "자산"},
    {"id": "BITHUMB-OHLCV",         "name": "OHLCV 캔들 데이터", "endpoint": "/public/candlestick/{order_currency}_{payment_currency}/{chart_intervals}",           "method": "GET", "category": "시세"},
    {"id": "BITHUMB-NETWORK-INFO",  "name": "네트워크 정보",      "endpoint": "/public/network-info",                                                              "method": "GET", "category": "정보"},
]
_BITHUMB_AUTH_APIS = [
    {"id": "BITHUMB-ACCOUNT",     "name": "회원 정보",      "endpoint": "/info/account",         "method": "POST", "category": "계좌"},
    {"id": "BITHUMB-BALANCE",     "name": "보유 자산 현황", "endpoint": "/info/balance",         "method": "POST", "category": "계좌"},
    {"id": "BITHUMB-WALLET",      "name": "입금 지갑 주소", "endpoint": "/info/wallet_address",  "method": "POST", "category": "입금"},
    {"id": "BITHUMB-ORDER-LIMIT", "name": "지정가 주문",    "endpoint": "/trade/place",          "method": "POST", "category": "주문"},
    {"id": "BITHUMB-ORDER-MARKET","name": "시장가 주문",    "endpoint": "/trade/market_buy",     "method": "POST", "category": "주문"},
    {"id": "BITHUMB-ORDER-CANCEL","name": "주문 취소",      "endpoint": "/trade/cancel",         "method": "POST", "category": "주문"},
    {"id": "BITHUMB-WITHDRAW",    "name": "출금 요청",      "endpoint": "/trade/btc_withdrawal", "method": "POST", "category": "출금"},
]

_COINONE_PUBLIC_APIS = [
    {"id": "COINONE-MARKETS",  "name": "마켓 목록 조회",      "endpoint": "/public/v2/markets/KRW",               "method": "GET", "category": "시세"},
    {"id": "COINONE-TICKER",   "name": "현재가 조회 (Ticker)", "endpoint": "/public/v2/ticker_new/KRW",            "method": "GET", "category": "시세"},
    {"id": "COINONE-ORDERBOOK","name": "호가 조회",            "endpoint": "/public/v2/orderbook/KRW",             "method": "GET", "category": "시세"},
    {"id": "COINONE-TRADES",   "name": "체결 내역 조회",       "endpoint": "/public/v2/trades/KRW",               "method": "GET", "category": "시세"},
    {"id": "COINONE-CANDLES",  "name": "캔들 차트 데이터",     "endpoint": "/public/v2/chart/KRW/{target_currency}","method": "GET", "category": "시세"},
]
_COINONE_AUTH_APIS = [
    {"id": "COINONE-ACCOUNT",      "name": "잔고 조회",      "endpoint": "/v2.0/account/balance/",      "method": "GET",  "category": "계좌"},
    {"id": "COINONE-ORDER-LIMIT",  "name": "지정가 주문",    "endpoint": "/v2.0/order/",                "method": "POST", "category": "주문"},
    {"id": "COINONE-ORDER-MARKET", "name": "시장가 주문",    "endpoint": "/v2.0/order/market_price/",   "method": "POST", "category": "주문"},
    {"id": "COINONE-ORDER-CANCEL", "name": "주문 취소",      "endpoint": "/v2.0/order/cancel/",         "method": "POST", "category": "주문"},
    {"id": "COINONE-ORDERS",       "name": "미체결 주문 조회","endpoint": "/v2.0/order/active_orders/", "method": "GET",  "category": "주문"},
    {"id": "COINONE-DEPOSIT",      "name": "입금 주소 조회", "endpoint": "/v2.0/transaction/deposit/",  "method": "GET",  "category": "입금"},
    {"id": "COINONE-WITHDRAW",     "name": "출금 요청",      "endpoint": "/v2.0/transaction/coin/",     "method": "POST", "category": "출금"},
]


def _make_records(
    apis: list,
    public_ids: set,
    source_code: str,
    provider: str,
    base_url: str,
    docs_url: str,
    tags_base: list,
) -> List[NormalizedOpenApiRecord]:
    records = []
    for api in apis:
        is_public = api["id"] in public_ids
        records.append(
            NormalizedOpenApiRecord(
                openapi_source_code=source_code,
                source_openapi_key=api["id"],
                name=api["name"],
                provider=provider,
                base_url=base_url,
                docs_url=docs_url,
                auth_type="NONE" if is_public else "API_KEY",
                category=api["category"],
                tags=tags_base,
                is_free=True,
                requires_approval=False,
                pricing_note="거래 수수료 기반 (API 호출 무료)",
                commercial_use=True,
                response_format="JSON",
            )
        )
    return records


class CryptoExchangeCollector(BaseOpenApiCollector):
    sources = [
        OpenApiSourceDefinition(source_code=_UPBIT_CODE,   source_name="업비트",  base_url=_UPBIT_BASE,   collection_type="CRAWL"),
        OpenApiSourceDefinition(source_code=_BITHUMB_CODE, source_name="빗썸",   base_url=_BITHUMB_BASE, collection_type="CRAWL"),
        OpenApiSourceDefinition(source_code=_COINONE_CODE, source_name="코인원", base_url=_COINONE_BASE, collection_type="CRAWL"),
    ]

    async def collect(self) -> List[NormalizedOpenApiRecord]:
        # 공개 API 호출로 마켓 정보 검증 (선택적)
        async with httpx.AsyncClient(
            headers={**self._http_headers, "Accept": "application/json"},
            follow_redirects=True,
        ) as client:
            try:
                r = await client.get(f"{_UPBIT_BASE}/v1/market/all", timeout=10.0)
                markets = r.json()
                logger.info(f"[업비트] 마켓 수: {len(markets)}개")
            except Exception as exc:
                logger.warning(f"[업비트] 마켓 조회 실패: {exc}")
            try:
                r = await client.get(f"{_BITHUMB_BASE}/public/ticker/ALL_KRW", timeout=10.0)
                data = r.json()
                logger.info(f"[빗썸] KRW 코인 수: {len(data.get('data', {})) - 1}개")
            except Exception as exc:
                logger.warning(f"[빗썸] 시세 조회 실패: {exc}")
            try:
                r = await client.get(f"{_COINONE_BASE}/public/v2/markets/KRW", timeout=10.0)
                data = r.json()
                logger.info(f"[코인원] 마켓 수: {len(data.get('markets', []))}개")
            except Exception as exc:
                logger.warning(f"[코인원] 마켓 조회 실패: {exc}")

        upbit_public_ids = {a["id"] for a in _UPBIT_PUBLIC_APIS}
        bithumb_public_ids = {a["id"] for a in _BITHUMB_PUBLIC_APIS}
        coinone_public_ids = {a["id"] for a in _COINONE_PUBLIC_APIS}

        records = (
            _make_records(_UPBIT_PUBLIC_APIS + _UPBIT_AUTH_APIS, upbit_public_ids,
                          _UPBIT_CODE, "업비트", _UPBIT_BASE, _UPBIT_DOCS, ["암호화폐", "거래소", "업비트"])
            + _make_records(_BITHUMB_PUBLIC_APIS + _BITHUMB_AUTH_APIS, bithumb_public_ids,
                            _BITHUMB_CODE, "빗썸", _BITHUMB_BASE, _BITHUMB_DOCS, ["암호화폐", "거래소", "빗썸"])
            + _make_records(_COINONE_PUBLIC_APIS + _COINONE_AUTH_APIS, coinone_public_ids,
                            _COINONE_CODE, "코인원", _COINONE_BASE, _COINONE_DOCS, ["암호화폐", "거래소", "코인원"])
        )

        logger.info(f"[CryptoExchange] 총 {len(records)}개 수집")
        return records

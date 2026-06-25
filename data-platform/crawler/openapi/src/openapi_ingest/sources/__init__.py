from __future__ import annotations

from typing import Dict, Type

from ..base import BaseOpenApiCollector
from .crypto_exchange import CryptoExchangeCollector
from .datagokr import DatagoKRCollector
from .game import GameCollector
from .kakao import KakaoCollector
from .kis import KisCollector
from .kobis import KobisCollector
from .naver_map import NaverMapCollector
from .odsay import ODsayCollector
from .tmap import TmapCollector
from .tosspayments import TossPaymentsCollector


COLLECTORS: Dict[str, Type[BaseOpenApiCollector]] = {
    "crypto_exchange": CryptoExchangeCollector,
    "datagokr":        DatagoKRCollector,
    "game":            GameCollector,
    "kakao":           KakaoCollector,
    "kis":             KisCollector,
    "kobis":           KobisCollector,
    "naver_map":       NaverMapCollector,
    "odsay":           ODsayCollector,
    "tmap":            TmapCollector,
    "tosspayments":    TossPaymentsCollector,
}

__all__ = [
    "COLLECTORS",
    "CryptoExchangeCollector",
    "DatagoKRCollector",
    "GameCollector",
    "KakaoCollector",
    "KisCollector",
    "KobisCollector",
    "NaverMapCollector",
    "ODsayCollector",
    "TmapCollector",
    "TossPaymentsCollector",
]

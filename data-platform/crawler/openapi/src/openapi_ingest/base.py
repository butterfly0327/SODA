from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Dict, List

from .config import Settings
from .db import Database
from .models import HarvestStats, NormalizedOpenApiRecord, OpenApiSourceDefinition

logger = logging.getLogger(__name__)


class BaseOpenApiCollector(ABC):
    """Open API 수집기 추상 기반 클래스.

    서브클래스가 구현해야 할 것:
    - 클래스 속성 ``sources``: 이 수집기가 담당하는 소스 목록
    - 메서드 ``collect()``: 실제 수집 로직, NormalizedOpenApiRecord 리스트 반환
    """

    sources: List[OpenApiSourceDefinition]  # 서브클래스에서 선언

    def __init__(self, db: Database, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.stats = HarvestStats()
        self._http_headers: Dict[str, str] = {
            "User-Agent": settings.user_agent,
            "Accept-Language": "ko-KR,ko;q=0.9",
        }

    @abstractmethod
    async def collect(self) -> List[NormalizedOpenApiRecord]:
        """API 메타데이터를 수집하여 정규화된 레코드 목록을 반환."""
        raise NotImplementedError

    async def run(self, **kwargs) -> HarvestStats:
        """수집 → DB upsert 전체 플로우 실행."""
        try:
            records = await self.collect()
            self.stats.collected_count = len(records)

            # source_code → source_id 매핑
            source_ids: Dict[str, int] = {}
            for source_def in self.sources:
                source_ids[source_def.source_code] = await self.db.ensure_openapi_source(source_def)

            # source_code 별로 레코드 분리 후 upsert
            records_by_source: Dict[int, List[NormalizedOpenApiRecord]] = {}
            for record in records:
                sid = source_ids.get(record.openapi_source_code)
                if sid is None:
                    self.stats.failed_count += 1
                    self.stats.errors.append(
                        f"{record.source_openapi_key}: "
                        f"알 수 없는 source_code={record.openapi_source_code!r}"
                    )
                    continue
                records_by_source.setdefault(sid, []).append(record)

            for sid, recs in records_by_source.items():
                try:
                    n = await self.db.upsert_apis_batch(sid, recs)
                    self.stats.upserted_count += n
                except Exception as exc:
                    self.stats.failed_count += len(recs)
                    self.stats.errors.append(f"source_id={sid} upsert 실패: {exc}")

        except Exception as exc:
            self.stats.errors.append(str(exc))
            raise

        return self.stats

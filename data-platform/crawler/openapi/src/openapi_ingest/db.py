from __future__ import annotations

import json
import importlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import NormalizedOpenApiRecord, OpenApiSourceDefinition

asyncpg = importlib.import_module("asyncpg")

_SOURCE_UPSERT_SQL = """
    INSERT INTO openapi_sources (source_code, source_name, base_url, collection_type)
    VALUES ($1, $2, $3, $4)
    ON CONFLICT (source_code) DO UPDATE SET
        source_name = EXCLUDED.source_name,
        base_url    = EXCLUDED.base_url
    RETURNING id
"""

_OPEN_API_UPSERT_SQL = """
    INSERT INTO open_apis (
        openapi_source_id, source_openapi_key, name, description, provider,
        base_url, docs_url, auth_type, category, tags,
        rate_limit, daily_limit, is_free, pricing_note, commercial_use,
        requires_approval, response_format, avg_response_time, response_schema,
        is_deleted, collected_at, created_at, updated_at
    ) VALUES (
        $1, $2, $3, $4, $5,
        $6, $7, $8, $9, $10,
        $11, $12, $13, $14, $15,
        $16, $17, $18, $19,
        $20, $21, now(), $22
    )
    ON CONFLICT (openapi_source_id, source_openapi_key) DO UPDATE SET
        name              = EXCLUDED.name,
        description       = EXCLUDED.description,
        provider          = EXCLUDED.provider,
        base_url          = EXCLUDED.base_url,
        docs_url          = EXCLUDED.docs_url,
        auth_type         = EXCLUDED.auth_type,
        category          = EXCLUDED.category,
        tags              = EXCLUDED.tags,
        is_free           = EXCLUDED.is_free,
        pricing_note      = EXCLUDED.pricing_note,
        commercial_use    = EXCLUDED.commercial_use,
        requires_approval = EXCLUDED.requires_approval,
        response_format   = EXCLUDED.response_format,
        is_deleted        = EXCLUDED.is_deleted,
        collected_at      = EXCLUDED.collected_at,
        updated_at        = EXCLUDED.updated_at
"""


def _record_to_row(
    source_id: int, record: NormalizedOpenApiRecord, now: datetime
) -> tuple[Any, ...]:
    return (
        source_id,
        record.source_openapi_key,
        record.name,
        record.description,
        record.provider,
        record.base_url,
        record.docs_url,
        record.auth_type,
        record.category,
        record.tags or [],  # asyncpg가 list[str]을 TEXT[]로 자동 변환
        record.rate_limit,
        record.daily_limit,
        record.is_free,
        record.pricing_note,
        record.commercial_use,
        record.requires_approval,
        record.response_format,
        record.avg_response_time,
        json.dumps(record.response_schema) if record.response_schema else None,
        record.is_deleted,
        now,  # collected_at
        now,  # updated_at
    )


class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._pool: Optional[Any] = None

    async def __aenter__(self) -> "Database":
        self._pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None

    def _pool_or_raise(self) -> Any:
        if self._pool is None:
            raise RuntimeError(
                "Database가 연결되지 않았습니다. `async with Database(...) as db:` 를 사용하세요."
            )
        return self._pool

    async def ensure_openapi_source(self, source: OpenApiSourceDefinition) -> int:
        """openapi_sources 테이블에 upsert 후 id 반환."""
        pool = self._pool_or_raise()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                _SOURCE_UPSERT_SQL,
                source.source_code,
                source.source_name,
                source.base_url,
                source.collection_type,
            )
        assert row is not None
        return int(row["id"])

    async def upsert_apis_batch(
        self, source_id: int, records: List[NormalizedOpenApiRecord]
    ) -> int:
        """records를 open_apis 테이블에 일괄 upsert."""
        if not records:
            return 0
        now = datetime.now(timezone.utc)
        rows = [_record_to_row(source_id, r, now) for r in records]
        pool = self._pool_or_raise()
        async with pool.acquire() as conn:
            await conn.executemany(_OPEN_API_UPSERT_SQL, rows)
        return len(records)

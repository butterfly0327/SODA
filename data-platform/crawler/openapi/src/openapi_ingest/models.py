from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class NormalizedOpenApiRecord:
    """open_api 테이블 1행에 대응하는 정규화 모델.

    openapi_source_id 는 DB 계층에서 openapi_source_code 로부터 해결한다.
    수집기는 이 모델을 채워서 반환하고 DB 계층에 위임한다.
    """

    openapi_source_code: str   # openapi_source.source_code (DB 계층에서 id로 변환)
    source_openapi_key: str    # 소스 내 고유 식별자
    name: str

    description: Optional[str] = None
    provider: Optional[str] = None
    base_url: Optional[str] = None
    docs_url: Optional[str] = None
    auth_type: str = "API_KEY"
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    is_free: bool = False
    requires_approval: bool = False
    is_deleted: bool = False

    rate_limit: Optional[int] = None
    daily_limit: Optional[int] = None
    pricing_note: Optional[str] = None
    commercial_use: bool = True

    response_format: Optional[str] = "JSON"
    avg_response_time: Optional[float] = None
    response_schema: Optional[Dict[str, Any]] = None


@dataclass(slots=True)
class OpenApiSourceDefinition:
    source_code: str
    source_name: str
    base_url: str
    collection_type: str = "CRAWL"


@dataclass(slots=True)
class HarvestStats:
    collected_count: int = 0
    upserted_count: int = 0
    failed_count: int = 0
    errors: List[str] = field(default_factory=list)

    def to_error_summary(self, limit: int = 20) -> Optional[str]:
        if not self.errors:
            return None
        head = self.errors[:limit]
        more = f"\n... and {len(self.errors) - limit} more" if len(self.errors) > limit else ""
        return "\n".join(head) + more

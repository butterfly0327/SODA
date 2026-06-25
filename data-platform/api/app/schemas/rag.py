from pydantic import BaseModel, Field


class RagQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="사용자 질문")
    top_k: int | None = Field(None, ge=1, le=20, description="검색 결과 수 (기본: RAG_TOP_K)")


class RetrievedOpenApi(BaseModel):
    id: int
    name: str
    description: str | None
    provider: str | None
    base_url: str
    docs_url: str | None
    auth_type: str
    category: str | None
    tags: list[str]
    is_free: bool | None
    score: float


class RagQueryResponse(BaseModel):
    query: str
    answer: str
    retrieved: list[RetrievedOpenApi]

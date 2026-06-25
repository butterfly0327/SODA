from functools import lru_cache
from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


GENERIC_QUERY_NOISE_CONTAINS = (
    "추천",
    "프로젝트",
    "만들",
    "원해",
    "원하는",
    "원하는데",
    "싶",
    "해줘",
    "해주세요",
    "알려",
)


class Settings(BaseSettings):
    app_name: str = "FastAPI RAG Boilerplate"
    app_env: str = "local"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = True

    cors_allow_origins: list[str] = ["*"]
    rag_top_k: int = 10

    # DB (asyncpg 형식: postgresql://user:pass@host:port/db)
    database_url: str = ""

    # 서울시 공공데이터 API 키
    seoul_api_key: str = ""

    # 공용 API 키 (Gemini/OpenAI 프록시 공통)
    api_key: str = Field(default="", validation_alias="GMS_API_KEY")
    # 임베딩 호출용 키 (GMS 공용 키 사용)
    dataset_embedding_api_key: str = Field(default="", validation_alias="GMS_API_KEY")
    gemini_api_base_url: str = (
        "https://gms.ssafy.io/gmsapi/generativelanguage.googleapis.com/v1beta"
    )
    # gemini-embedding-001: MRL 지원, output_dimensionality=1536 → VECTOR(1536) 매칭
    # text-embedding-004:  고정 768차원 → DB 컬럼 변경 필요
    embed_model: str = "gemini-embedding-001"
    embed_dimensions: int = 1536  # DB openapi_chunk.embedding VECTOR(1536) 에 맞춤
    embed_batch_size: int = 100  # batchEmbedContents 권장 최대치

    # GPT (SSAFY GMS 프록시)
    gpt_api_base_url: str = "https://gms.ssafy.io/gmsapi/api.openai.com/v1"
    gpt_model: str = "gpt-5.2"

    # 데이터셋 추천 서비스 (dataset_recommendation_service)
    recommendation_embedding_model: str = "text-embedding-3-large"
    recommendation_embedding_dimensions: int = 1536
    recommendation_embedding_url: str = (
        "https://gms.ssafy.io/gmsapi/api.openai.com/v1/embeddings"
    )
    recommendation_chat_url: str = (
        "https://gms.ssafy.io/gmsapi/api.openai.com/v1/chat/completions"
    )
    recommendation_http_timeout_seconds: float = 60.0
    recommendation_llm_model: str = "gpt-5.2"
    recommendation_llm_max_tokens: int = 2200
    recommendation_default_top_n: int = 10
    recommendation_vector_top_k: int = 50
    recommendation_llm_candidate_k: int = 20
    recommendation_card_max_chars: int = 700
    recommendation_score_threshold_enabled: bool = True
    recommendation_min_score_100: float = 60.0
    recommendation_test_user_turn_id: int | None = None

    # LLM routing (dev Codex adapter + GMS fallback)
    llm_primary_provider: str = "gms"
    codex_adapter_enabled: bool = False
    codex_adapter_base_url: str = "http://codex-adapter-dev:8091"
    codex_fallback_to_gms: bool = True
    codex_model: str = "gpt-5.4"
    codex_timeout_seconds: float = 45.0
    codex_max_concurrency: int = 1
    codex_max_queue: int = 100

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

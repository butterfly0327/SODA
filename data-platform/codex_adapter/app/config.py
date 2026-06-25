from functools import lru_cache
from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AdapterSettings(BaseSettings):
    adapter_app_env: str = "dev"
    adapter_app_host: str = "0.0.0.0"
    adapter_app_port: int = 8091

    codex_command: str = Field(default="codex", validation_alias="CODEX_COMMAND")
    codex_home_path: str = Field(
        default="/root/.codex",
        validation_alias="CODEX_HOME_PATH",
    )
    model: str = Field(default="gpt-5.4", validation_alias="CODEX_MODEL")
    timeout_seconds: float = Field(
        default=45.0,
        validation_alias="CODEX_TIMEOUT_SECONDS",
    )
    max_concurrency: int = Field(
        default=1,
        validation_alias="CODEX_MAX_CONCURRENCY",
    )
    max_queue: int = Field(default=100, validation_alias="CODEX_MAX_QUEUE")

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> AdapterSettings:
    return AdapterSettings()


settings = get_settings()

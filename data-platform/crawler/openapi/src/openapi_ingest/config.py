from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from typing import Optional


def _load_dotenv_if_available() -> None:
    try:
        m = importlib.import_module("dotenv")
    except ModuleNotFoundError:
        return
    load_fn = getattr(m, "load_dotenv", None)
    if callable(load_fn):
        load_fn()


_load_dotenv_if_available()


@dataclass(slots=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "")
    parser_version: str = os.getenv("PARSER_VERSION", "v1.0.0")
    request_timeout_seconds: float = float(
        os.getenv(
            "OPENAPI_REQUEST_TIMEOUT_SECONDS",
            os.getenv("REQUEST_TIMEOUT_SECONDS", "30"),
        )
    )
    connect_timeout_seconds: float = float(os.getenv("CONNECT_TIMEOUT_SECONDS", "10"))
    user_agent: str = os.getenv(
        "OPENAPI_USER_AGENT",
        os.getenv(
            "USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        ),
    )

    # datagokr 전용
    datagokr_csv_path: Optional[str] = os.getenv("DATAGOKR_CSV_PATH")
    datagokr_concurrency: int = int(os.getenv("DATAGOKR_CONCURRENCY", "8"))
    datagokr_batch_size: int = int(os.getenv("DATAGOKR_BATCH_SIZE", "50"))

    def validate(self) -> None:
        if not self.database_url:
            raise ValueError("DATABASE_URL 환경변수가 비어 있습니다.")

    @property
    def asyncpg_dsn(self) -> str:
        """SQLAlchemy asyncpg DSN(postgresql+asyncpg://) → asyncpg DSN(postgresql://) 변환."""
        dsn = self.database_url
        if dsn.startswith("postgresql+asyncpg://"):
            dsn = "postgresql://" + dsn[len("postgresql+asyncpg://") :]
        return dsn

from __future__ import annotations

import os
from urllib.parse import quote

from celery import Celery
from celery.schedules import crontab


_DEFAULT_DATASET_AUTO_COLLECTION_SOURCES = (
    "huggingface",
    "figshare",
    "harvard_dataverse",
    "kaggle",
    "aihub",
    "aws_odr",
    "zenodo",
    "data_gov",
    "data_europa",
)


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value


def _dataset_auto_collection_enabled() -> bool:
    return _env_flag("DATASET_AUTO_COLLECTION_ENABLED", True)


def _dataset_auto_collection_sources() -> list[str]:
    raw = os.getenv("DATASET_AUTO_COLLECTION_SOURCES")
    if not raw:
        return list(_DEFAULT_DATASET_AUTO_COLLECTION_SOURCES)

    parsed: list[str] = []
    for token in raw.split(","):
        source = token.strip()
        if source and source not in parsed:
            parsed.append(source)
    return parsed


def _dataset_auto_collection_interval_hours() -> int:
    value = _env_int("DATASET_AUTO_COLLECTION_INTERVAL_HOURS", 4)
    if value <= 0 or 24 % value != 0:
        return 4
    return value


def _dataset_auto_collection_limit() -> int:
    configured = _env_int(
        "DATASET_AUTO_COLLECTION_LIMIT",
        _env_int("DEFAULT_SAFE_LIMIT", 20),
    )
    return configured if configured > 0 else 20


def _dataset_auto_collection_max_runtime_seconds() -> int | None:
    configured = _env_int("DATASET_AUTO_COLLECTION_MAX_RUNTIME_SECONDS", 0)
    return configured if configured > 0 else None


def _dataset_auto_collection_safe() -> bool:
    return _env_flag("DATASET_AUTO_COLLECTION_SAFE", True)


def _dataset_full_reconcile_enabled() -> bool:
    return _env_flag("DATASET_FULL_RECONCILE_ENABLED", False)


def _dataset_full_reconcile_sources() -> list[str]:
    raw = os.getenv("DATASET_FULL_RECONCILE_SOURCES")
    if not raw:
        return _dataset_auto_collection_sources()

    parsed: list[str] = []
    for token in raw.split(","):
        source = token.strip()
        if source and source not in parsed:
            parsed.append(source)
    return parsed


def _dataset_full_reconcile_start_hour() -> int:
    value = _env_int("DATASET_FULL_RECONCILE_START_HOUR", 1)
    if value < 0 or value > 23:
        return 1
    return value


def _dataset_full_reconcile_start_minute() -> int:
    value = _env_int("DATASET_FULL_RECONCILE_START_MINUTE", 10)
    if value < 0 or value > 59:
        return 10
    return value


def _dataset_full_reconcile_source_interval_minutes() -> int:
    value = _env_int("DATASET_FULL_RECONCILE_SOURCE_INTERVAL_MINUTES", 30)
    if value <= 0 or value > (24 * 60):
        return 30
    return value


def _dataset_schedule(index: int, total: int, interval_hours: int):
    if total <= 0:
        raise ValueError("total must be positive")

    interval_minutes = interval_hours * 60
    offset_minutes = (interval_minutes * index) // total
    hour_offset, minute = divmod(offset_minutes, 60)
    hours = ",".join(
        str((base_hour + hour_offset) % 24)
        for base_hour in range(0, 24, interval_hours)
    )
    return crontab(minute=minute, hour=hours)


def _build_dataset_auto_collection_schedule() -> dict[str, dict[str, object]]:
    if not _dataset_auto_collection_enabled():
        return {}

    sources = _dataset_auto_collection_sources()
    interval_hours = _dataset_auto_collection_interval_hours()
    max_runtime_seconds = _dataset_auto_collection_max_runtime_seconds()
    limit = (
        None if max_runtime_seconds is not None else _dataset_auto_collection_limit()
    )
    safe = _dataset_auto_collection_safe()

    schedule: dict[str, dict[str, object]] = {}
    for index, source in enumerate(sources):
        schedule[f"dataset-auto-collect-{source}"] = {
            "task": "platform.collect_dataset_metadata",
            "schedule": _dataset_schedule(index, len(sources), interval_hours),
            "kwargs": {
                "source": source,
                "limit": limit,
                "from_scratch": False,
                "safe": safe,
                "max_runtime_seconds": max_runtime_seconds,
            },
        }
    return schedule


def _build_dataset_full_reconcile_schedule() -> dict[str, dict[str, object]]:
    if not _dataset_full_reconcile_enabled():
        return {}

    start_hour = _dataset_full_reconcile_start_hour()
    start_minute = _dataset_full_reconcile_start_minute()
    interval_minutes = _dataset_full_reconcile_source_interval_minutes()

    schedule: dict[str, dict[str, object]] = {}
    for index, source in enumerate(_dataset_full_reconcile_sources()):
        total_minutes = start_hour * 60 + start_minute + (interval_minutes * index)
        hour = (total_minutes // 60) % 24
        minute = total_minutes % 60
        schedule[f"dataset-full-reconcile-{source}"] = {
            "task": "platform.collect_dataset_metadata",
            "schedule": crontab(minute=minute, hour=hour),
            "kwargs": {
                "source": source,
                "from_scratch": True,
                "reconcile_missing": True,
                "safe": True,
            },
        }
    return schedule


def _build_default_broker_url() -> str:
    user = quote(os.getenv("RABBITMQ_USER", "soda"), safe="")
    password = quote(os.getenv("RABBITMQ_PASSWORD", "change-me"), safe="")
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port = os.getenv("RABBITMQ_PORT", "5672")
    vhost = quote(os.getenv("RABBITMQ_VHOST", "dev").lstrip("/"), safe="")
    return f"amqp://{user}:{password}@{host}:{port}/{vhost}"


celery_app = Celery(
    "soda-data-platform",
    broker=os.getenv("CELERY_BROKER_URL", _build_default_broker_url()),
    backend=os.getenv("CELERY_RESULT_BACKEND", "rpc://"),
    include=["app.tasks.platform_tasks"],
)

celery_app.conf.update(
    task_default_queue=os.getenv("CELERY_DEFAULT_QUEUE", "default"),
    task_routes={
        "platform.collect_dataset_metadata": {"queue": "collect_queue"},
        "platform.collect_openapi_metadata": {"queue": "collect_queue"},
        "platform.generate_embeddings": {"queue": "embed_queue"},
        "platform.reindex_metadata": {"queue": "reindex_queue"},
    },
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=os.getenv("TZ", "Asia/Seoul"),
    enable_utc=False,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    beat_schedule={
        "platform-heartbeat": {
            "task": "platform.ping",
            "schedule": float(os.getenv("CELERY_HEARTBEAT_INTERVAL_SECONDS", "300")),
        }
    }
    | _build_dataset_auto_collection_schedule()
    | _build_dataset_full_reconcile_schedule(),
)

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.core.celery_app import celery_app


logger = logging.getLogger(__name__)


def _platform_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _extend_pythonpath(*paths: Path) -> str:
    current = os.getenv("PYTHONPATH", "")
    extra = os.pathsep.join(str(path) for path in paths)
    return extra if not current else f"{extra}{os.pathsep}{current}"


def _run_module(
    cwd: Path,
    module_name: str,
    args: list[str],
    pythonpath: str,
    extra_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONPATH"] = pythonpath
    if extra_env:
        env.update(extra_env)

    completed = subprocess.run(
        [sys.executable, "-m", module_name, *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    payload: Any = stdout

    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            payload = stdout

    result = {
        "command": [sys.executable, "-m", module_name, *args],
        "cwd": str(cwd),
        "returncode": completed.returncode,
        "stdout": payload,
        "stderr": stderr,
    }

    if completed.returncode != 0:
        raise RuntimeError(json.dumps(result, ensure_ascii=False))

    return result


def _log_dataset_collection_event(event: str, **fields: Any) -> None:
    payload = {"event": event} | {
        key: value for key, value in fields.items() if value is not None
    }
    logger.info("dataset_collection %s", json.dumps(payload, ensure_ascii=False, sort_keys=True))


@celery_app.task(name="platform.ping")
def ping() -> dict[str, str]:
    return {"status": "ok", "service": "celery"}


@celery_app.task(name="platform.collect_dataset_metadata")
def collect_dataset_metadata(
    source: str = "all",
    limit: int | None = None,
    from_scratch: bool = False,
    safe: bool | None = None,
    exclude_sources: list[str] | None = None,
    reconcile_missing: bool = False,
    parser_version: str | None = None,
    max_runtime_seconds: int | None = None,
) -> dict[str, Any]:
    platform_root = _platform_root()
    dataset_dir = platform_root / "crawler" / "dataset"
    args = ["--source", source]
    extra_env: dict[str, str] = {}

    if limit is not None:
        args.extend(["--limit", str(limit)])
    if from_scratch:
        args.append("--from-scratch")
    if safe is True:
        args.append("--safe")
    if safe is False:
        args.append("--no-safe")
    for excluded_source in exclude_sources or []:
        args.extend(["--exclude-source", excluded_source])
    if reconcile_missing:
        args.append("--reconcile-missing")
    if parser_version:
        extra_env["PARSER_VERSION"] = parser_version
    if max_runtime_seconds is not None:
        args.extend(["--max-runtime-seconds", str(max_runtime_seconds)])

    _log_dataset_collection_event(
        "start",
        source=source,
        limit=limit,
        from_scratch=from_scratch,
        safe=safe,
        exclude_sources=exclude_sources,
        reconcile_missing=reconcile_missing,
        parser_version=parser_version,
        max_runtime_seconds=max_runtime_seconds,
    )

    try:
        result = _run_module(
            cwd=dataset_dir,
            module_name="metadata_ingest",
            args=args,
            pythonpath=_extend_pythonpath(platform_root / "api", dataset_dir / "src"),
            extra_env=extra_env or None,
        )
    except Exception as exc:
        _log_dataset_collection_event(
            "failed",
            source=source,
            limit=limit,
            from_scratch=from_scratch,
            safe=safe,
            exclude_sources=exclude_sources,
            reconcile_missing=reconcile_missing,
            parser_version=parser_version,
            max_runtime_seconds=max_runtime_seconds,
            error=str(exc),
        )
        raise

    source_summary = result.get("stdout")
    if isinstance(source_summary, dict):
        source_summary = source_summary.get(source)

    _log_dataset_collection_event(
        "completed",
        source=source,
        limit=limit,
        from_scratch=from_scratch,
        safe=safe,
        exclude_sources=exclude_sources,
        reconcile_missing=reconcile_missing,
        parser_version=parser_version,
        max_runtime_seconds=max_runtime_seconds,
        summary=source_summary,
    )
    return result


@celery_app.task(name="platform.collect_openapi_metadata")
def collect_openapi_metadata(
    source: str = "all",
    limit: int | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    platform_root = _platform_root()
    openapi_dir = platform_root / "crawler" / "openapi"
    args = ["--source", source]

    if limit is not None:
        args.extend(["--limit", str(limit)])
    if resume:
        args.append("--resume")

    return _run_module(
        cwd=openapi_dir,
        module_name="openapi_ingest",
        args=args,
        pythonpath=_extend_pythonpath(platform_root / "api", openapi_dir / "src"),
    )


@celery_app.task(name="platform.generate_embeddings")
def generate_embeddings() -> dict[str, str]:
    return {"status": "queued", "message": "Embedding pipeline placeholder"}


@celery_app.task(name="platform.reindex_metadata")
def reindex_metadata() -> dict[str, str]:
    return {"status": "queued", "message": "Reindex pipeline placeholder"}

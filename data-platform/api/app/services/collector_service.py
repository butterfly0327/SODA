from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CollectorRunRequest:
    dataset_source_id: str
    parser_version: str
    limit: int | None
    from_scratch: bool
    safe: bool | None
    exclude_source_ids: list[str]
    reconcile_missing: bool
    triggered_by: str
    max_runtime_seconds: int | None = None


@dataclass(slots=True)
class EmbeddingRunRequest:
    dataset_id: int | None
    limit: int
    reembed: bool
    triggered_by: str


@dataclass(slots=True)
class CollectorRunState:
    run_id: str
    status: str
    message: str
    request: CollectorRunRequest | EmbeddingRunRequest
    output_json: dict[str, object] | None = None
    stderr: str | None = None


class CollectorService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active_run_id: str | None = None
        self._runs: dict[str, CollectorRunState] = {}

    def start_run(self, request: CollectorRunRequest) -> CollectorRunState:
        with self._lock:
            if self._active_run_id is not None:
                active_run = self._runs[self._active_run_id]
                raise RuntimeError(f"이미 실행 중인 수집 작업이 있습니다. runId={active_run.run_id}")

            run_id = str(uuid.uuid4())
            state = CollectorRunState(
                run_id=run_id,
                status="running",
                message="데이터셋 메타데이터 수집을 비동기로 시작했습니다.",
                request=request,
            )
            self._active_run_id = run_id
            self._runs[run_id] = state

        worker = threading.Thread(target=self._execute_run, args=(run_id,), daemon=True)
        worker.start()
        return state

    def start_embedding_run(self, request: EmbeddingRunRequest) -> CollectorRunState:
        with self._lock:
            if self._active_run_id is not None:
                active_run = self._runs[self._active_run_id]
                raise RuntimeError(f"이미 실행 중인 수집 작업이 있습니다. runId={active_run.run_id}")

            run_id = str(uuid.uuid4())
            state = CollectorRunState(
                run_id=run_id,
                status="running",
                message="데이터셋 임베딩 적재를 비동기로 시작했습니다.",
                request=request,
            )
            self._active_run_id = run_id
            self._runs[run_id] = state

        worker = threading.Thread(target=self._execute_embedding_run, args=(run_id,), daemon=True)
        worker.start()
        return state

    def _execute_run(self, run_id: str) -> None:
        with self._lock:
            state = self._runs[run_id]

        request = state.request
        if not isinstance(request, CollectorRunRequest):
            with self._lock:
                state.status = "failed"
                state.message = "수집 작업 실행 실패: 잘못된 실행 요청 타입"
                self._active_run_id = None
            return

        dataset_dir = self._resolve_dataset_dir()
        command = self._build_command(request)
        env = self._build_env(dataset_dir=dataset_dir, parser_version=request.parser_version)

        try:
            completed = subprocess.run(
                command,
                cwd=str(dataset_dir),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            output_json = self._parse_summary_json(completed.stdout)

            with self._lock:
                state.output_json = output_json
                state.stderr = completed.stderr.strip() if completed.stderr else None
                if completed.returncode == 0:
                    state.status = "success"
                    state.message = "데이터셋 메타데이터 수집이 정상 종료되었습니다."
                else:
                    state.status = "failed"
                    state.message = "데이터셋 메타데이터 수집 중 오류가 발생했습니다."
        except Exception as exc:
            with self._lock:
                state.status = "failed"
                state.message = f"수집 작업 실행 실패: {exc}"
        finally:
            with self._lock:
                self._active_run_id = None

    def _execute_embedding_run(self, run_id: str) -> None:
        with self._lock:
            state = self._runs[run_id]

        request = state.request
        if not isinstance(request, EmbeddingRunRequest):
            with self._lock:
                state.status = "failed"
                state.message = "임베딩 작업 실행 실패: 잘못된 실행 요청 타입"
                self._active_run_id = None
            return

        dataset_dir = self._resolve_dataset_dir()
        command = self._build_embedding_command(request)
        env = self._build_env(dataset_dir=dataset_dir, parser_version=None)

        try:
            completed = subprocess.run(
                command,
                cwd=str(dataset_dir),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            output_json = self._parse_summary_json(completed.stdout)

            with self._lock:
                state.output_json = output_json
                state.stderr = completed.stderr.strip() if completed.stderr else None
                if completed.returncode == 0:
                    state.status = "success"
                    state.message = "데이터셋 임베딩 적재가 정상 종료되었습니다."
                else:
                    state.status = "failed"
                    state.message = "데이터셋 임베딩 적재 중 오류가 발생했습니다."
        except Exception as exc:
            with self._lock:
                state.status = "failed"
                state.message = f"임베딩 작업 실행 실패: {exc}"
        finally:
            with self._lock:
                self._active_run_id = None

    def _resolve_dataset_dir(self) -> Path:
        project_root = Path(__file__).resolve().parents[3]
        dataset_dir = project_root / "crawler" / "dataset"
        if not (dataset_dir / "src" / "metadata_ingest").exists():
            raise FileNotFoundError(f"dataset 수집 모듈 경로를 찾을 수 없습니다: {dataset_dir}")
        return dataset_dir

    def _build_command(self, request: CollectorRunRequest) -> list[str]:
        command = [
            sys.executable,
            "-m",
            "metadata_ingest",
            "--source",
            request.dataset_source_id,
        ]
        for source in request.exclude_source_ids:
            command.extend(["--exclude-source", source])
        if request.limit is not None:
            command.extend(["--limit", str(request.limit)])
        if request.from_scratch:
            command.append("--from-scratch")
        if request.safe is True:
            command.append("--safe")
        if request.safe is False:
            command.append("--no-safe")
        if request.reconcile_missing:
            command.append("--reconcile-missing")
        return command

    def _build_embedding_command(self, request: EmbeddingRunRequest) -> list[str]:
        command = [
            sys.executable,
            "embedding.py",
            "--limit",
            str(request.limit),
        ]
        if request.dataset_id is not None:
            command.extend(["--dataset-id", str(request.dataset_id)])
        if request.reembed:
            command.append("--reembed")
        return command

    def _build_env(self, dataset_dir: Path, parser_version: str | None) -> dict[str, str]:
        env = dict(os.environ)
        src_path = str(dataset_dir / "src")
        current_python_path = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = src_path if not current_python_path else f"{src_path}{os.pathsep}{current_python_path}"
        if parser_version:
            env["PARSER_VERSION"] = parser_version
        return env

    def _parse_summary_json(self, stdout_text: str) -> dict[str, object] | None:
        text = stdout_text.strip()
        if not text:
            return None
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for candidate in reversed(lines):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            return parsed
        return None


collector_service = CollectorService()

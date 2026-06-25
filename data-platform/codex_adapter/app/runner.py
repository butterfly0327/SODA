from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any

from .config import AdapterSettings
from .status import RunnerStatus, utc_now_iso


class CodexRunnerError(RuntimeError):
    pass


class CodexRunner:
    def __init__(self, settings: AdapterSettings) -> None:
        self._settings = settings
        self._status = RunnerStatus(
            enabled=True,
            reachable=True,
            auth_present=self._auth_path.exists(),
            max_concurrency=settings.max_concurrency,
            max_queue=settings.max_queue,
        )
        self._slot_semaphore = asyncio.Semaphore(settings.max_concurrency)
        self._state_lock = asyncio.Lock()
        self._active_requests = 0

    @property
    def _auth_path(self) -> Path:
        return Path(self._settings.codex_home_path) / "auth.json"

    def get_status_snapshot(self) -> dict[str, object]:
        self._status.auth_present = self._auth_path.exists()
        return self._status.to_dict()

    async def run_chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        await self._reserve_request_slot()
        try:
            async with self._slot_semaphore:
                await self._set_running_delta(1)
                try:
                    self._ensure_auth_present()
                    content_text = await self._invoke_codex(payload)
                finally:
                    await self._set_running_delta(-1)
        finally:
            await self._release_request_slot()

        self._status.last_success_at = utc_now_iso()
        self._status.last_fallback_reason = None
        return {
            "provider": "codex",
            "model": str(payload.get("model") or self._settings.model),
            "content": content_text,
            "raw": {
                "choices": [
                    {
                        "message": {
                            "content": content_text,
                        }
                    }
                ]
            },
        }

    async def _reserve_request_slot(self) -> None:
        async with self._state_lock:
            if self._active_requests >= self._settings.max_queue:
                self._mark_failure("adapter queue overflow")
                raise CodexRunnerError("codex adapter queue overflow")
            self._active_requests += 1
            self._status.queue_depth = max(
                self._active_requests - self._status.running_count,
                0,
            )

    async def _release_request_slot(self) -> None:
        async with self._state_lock:
            self._active_requests = max(self._active_requests - 1, 0)
            self._status.queue_depth = max(
                self._active_requests - self._status.running_count,
                0,
            )

    async def _set_running_delta(self, delta: int) -> None:
        async with self._state_lock:
            self._status.running_count = max(self._status.running_count + delta, 0)
            self._status.queue_depth = max(
                self._active_requests - self._status.running_count,
                0,
            )

    def _ensure_auth_present(self) -> None:
        self._status.auth_present = self._auth_path.exists()
        if not self._status.auth_present:
            self._mark_failure("missing auth.json")
            raise CodexRunnerError(
                f"Codex auth.json is missing at {self._auth_path}"
            )

    def _mark_failure(self, reason: str) -> None:
        self._status.last_failure_at = utc_now_iso()
        self._status.last_fallback_reason = reason

    async def _invoke_codex(self, payload: dict[str, Any]) -> str:
        model = str(payload.get("model") or self._settings.model)
        prompt = self._build_prompt(payload)
        env = os.environ.copy()
        env["HOME"] = str(Path(self._settings.codex_home_path).expanduser().parent)

        with TemporaryDirectory() as temp_dir:
            with NamedTemporaryFile(
                mode="w+",
                encoding="utf-8",
                suffix=".txt",
                dir=temp_dir,
                delete=False,
            ) as output_file:
                output_path = output_file.name

            command = [
                self._settings.codex_command,
                "exec",
                "--skip-git-repo-check",
                "-s",
                "read-only",
                "-m",
                model,
                "-o",
                output_path,
                "-",
            ]

            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=temp_dir,
                env=env,
            )
            try:
                _stdout, stderr = await asyncio.wait_for(
                    process.communicate(prompt.encode("utf-8")),
                    timeout=self._settings.timeout_seconds,
                )
            except TimeoutError as exc:
                process.kill()
                await process.communicate()
                self._mark_failure("codex exec timeout")
                raise CodexRunnerError("Codex exec timed out") from exc

            if process.returncode != 0:
                stderr_text = stderr.decode("utf-8", errors="replace").strip()
                self._mark_failure("codex exec failed")
                raise CodexRunnerError(
                    f"Codex exec failed with exit code {process.returncode}: {stderr_text}"
                )

            content_text = Path(output_path).read_text(encoding="utf-8").strip()
            if not content_text:
                self._mark_failure("empty codex response")
                raise CodexRunnerError("Codex exec returned empty content")
            return content_text

    @staticmethod
    def _build_prompt(payload: dict[str, Any]) -> str:
        messages = payload.get("messages") or []
        response_format = payload.get("response_format")
        sections: list[str] = [
            "You are acting as a chat completion adapter.",
            "Reply with the final assistant content only.",
        ]

        if isinstance(response_format, dict):
            sections.append(
                "The caller requires structured output. Follow the requested response_format exactly."
            )
            sections.append(json.dumps(response_format, ensure_ascii=False))

        for message in messages:
            if not isinstance(message, dict):
                continue
            role = str(message.get("role") or "user").strip().upper()
            content = str(message.get("content") or "").strip()
            if not content:
                continue
            sections.append(f"{role}: {content}")

        return "\n\n".join(sections).strip()

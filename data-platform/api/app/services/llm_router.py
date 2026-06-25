from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from ..core.config import settings
from .gms_chat_client import GmsChatClient


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CodexAdapterClientError(RuntimeError):
    pass


class CodexAdapterClient:
    _HTTP_MAX_CONNECTIONS = 100
    _HTTP_MAX_KEEPALIVE_CONNECTIONS = 20
    _HTTP_KEEPALIVE_EXPIRY_SECONDS = 30.0

    def __init__(self, *, base_url: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        limits = httpx.Limits(
            max_connections=self._HTTP_MAX_CONNECTIONS,
            max_keepalive_connections=self._HTTP_MAX_KEEPALIVE_CONNECTIONS,
            keepalive_expiry=self._HTTP_KEEPALIVE_EXPIRY_SECONDS,
        )
        self._async_client = httpx.AsyncClient(
            timeout=self._timeout_seconds,
            limits=limits,
        )
        self._sync_client = httpx.Client(
            timeout=self._timeout_seconds,
            limits=limits,
        )

    async def close(self) -> None:
        self._sync_client.close()
        await self._async_client.aclose()

    async def create_chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._async_client.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise CodexAdapterClientError(f"Codex adapter timeout: {exc}") from exc
        except httpx.RequestError as exc:
            raise CodexAdapterClientError(
                f"Codex adapter request failed: {exc}"
            ) from exc

        return self._normalize_chat_response(response)

    def create_chat_completion_sync(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._sync_client.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise CodexAdapterClientError(f"Codex adapter timeout: {exc}") from exc
        except httpx.RequestError as exc:
            raise CodexAdapterClientError(
                f"Codex adapter request failed: {exc}"
            ) from exc

        return self._normalize_chat_response(response)

    async def get_status(self) -> dict[str, Any]:
        try:
            response = await self._async_client.get(f"{self._base_url}/status")
        except httpx.TimeoutException as exc:
            raise CodexAdapterClientError(
                f"Codex adapter status timeout: {exc}"
            ) from exc
        except httpx.RequestError as exc:
            raise CodexAdapterClientError(
                f"Codex adapter status request failed: {exc}"
            ) from exc

        return self._normalize_status_response(response)

    def get_status_sync(self) -> dict[str, Any]:
        try:
            response = self._sync_client.get(f"{self._base_url}/status")
        except httpx.TimeoutException as exc:
            raise CodexAdapterClientError(
                f"Codex adapter status timeout: {exc}"
            ) from exc
        except httpx.RequestError as exc:
            raise CodexAdapterClientError(
                f"Codex adapter status request failed: {exc}"
            ) from exc

        return self._normalize_status_response(response)

    @staticmethod
    def _normalize_chat_response(response: httpx.Response) -> dict[str, Any]:
        if response.status_code >= 400:
            raise CodexAdapterClientError(
                f"Codex adapter failed(status={response.status_code}): {response.text[:300]}"
            )

        body = response.json()
        if not isinstance(body, dict):
            raise CodexAdapterClientError(
                "Codex adapter response is not a JSON object."
            )
        return body

    @staticmethod
    def _normalize_status_response(response: httpx.Response) -> dict[str, Any]:
        if response.status_code >= 400:
            raise CodexAdapterClientError(
                f"Codex adapter status failed(status={response.status_code}): {response.text[:300]}"
            )
        body = response.json()
        if not isinstance(body, dict):
            raise CodexAdapterClientError("Codex adapter status response is invalid.")
        codex_status = body.get("codex")
        if not isinstance(codex_status, dict):
            raise CodexAdapterClientError(
                "Codex adapter status response has no codex snapshot."
            )
        return body


class LlmRouter:
    def __init__(
        self,
        *,
        adapter_client: CodexAdapterClient | Any,
        gms_client: GmsChatClient | Any,
        adapter_enabled: bool,
        fallback_to_gms: bool,
        primary_provider: str | None = None,
        codex_model: str | None = None,
    ) -> None:
        self._adapter_client = adapter_client
        self._gms_client = gms_client
        self._adapter_enabled = adapter_enabled
        self._fallback_to_gms = fallback_to_gms
        self._primary_provider = (
            primary_provider or ("codex" if adapter_enabled else "gms")
        ).lower()
        self._codex_model = codex_model or settings.codex_model
        self._last_success_at: str | None = None
        self._last_failure_at: str | None = None
        self._last_fallback_reason: str | None = None

    async def create_chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._should_try_adapter():
            try:
                result = await self._adapter_client.create_chat_completion(
                    self._build_adapter_payload(payload)
                )
                self._mark_success()
                return result
            except Exception as exc:
                self._mark_failure(str(exc))
                if not self._fallback_to_gms:
                    raise

        result = await self._gms_client.create_chat_completion(payload)
        self._last_success_at = _utc_now_iso()
        return result

    def create_chat_completion_sync(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._should_try_adapter():
            try:
                result = self._adapter_client.create_chat_completion_sync(
                    self._build_adapter_payload(payload)
                )
                self._mark_success()
                return result
            except Exception as exc:
                self._mark_failure(str(exc))
                if not self._fallback_to_gms:
                    raise

        result = self._gms_client.create_chat_completion_sync(payload)
        self._last_success_at = _utc_now_iso()
        return result

    async def get_status_snapshot(self) -> dict[str, Any]:
        codex_status = self._default_codex_status()
        if self._should_try_adapter() or self._primary_provider == "codex":
            try:
                adapter_status = await self._adapter_client.get_status()
                codex_status = dict(adapter_status["codex"])
            except Exception as exc:
                codex_status["reachable"] = False
                codex_status["lastFallbackReason"] = str(exc)
                if self._last_failure_at is not None:
                    codex_status["lastFailureAt"] = self._last_failure_at

        if self._last_fallback_reason is not None:
            codex_status["lastFallbackReason"] = self._last_fallback_reason
        if self._last_success_at is not None:
            codex_status["lastSuccessAt"] = self._last_success_at
        if self._last_failure_at is not None:
            codex_status["lastFailureAt"] = self._last_failure_at

        return {
            "primaryProvider": self._primary_provider,
            "codex": codex_status,
        }

    def _should_try_adapter(self) -> bool:
        return self._adapter_enabled and self._primary_provider == "codex"

    def _build_adapter_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        adapter_payload = dict(payload)
        adapter_payload["model"] = self._codex_model
        return adapter_payload

    def _mark_success(self) -> None:
        self._last_success_at = _utc_now_iso()
        self._last_fallback_reason = None

    def _mark_failure(self, reason: str) -> None:
        self._last_failure_at = _utc_now_iso()
        self._last_fallback_reason = reason

    def _default_codex_status(self) -> dict[str, Any]:
        return {
            "enabled": self._adapter_enabled,
            "reachable": False,
            "authPresent": False,
            "maxConcurrency": settings.codex_max_concurrency,
            "maxQueue": settings.codex_max_queue,
            "queueDepth": 0,
            "runningCount": 0,
            "lastSuccessAt": self._last_success_at,
            "lastFailureAt": self._last_failure_at,
            "lastFallbackReason": self._last_fallback_reason,
        }

    async def close(self) -> None:
        await self._adapter_client.close()
        await self._gms_client.close()


codex_adapter_client = CodexAdapterClient(
    base_url=settings.codex_adapter_base_url,
    timeout_seconds=settings.codex_timeout_seconds,
)
gms_chat_client = GmsChatClient()
llm_router = LlmRouter(
    adapter_client=codex_adapter_client,
    gms_client=gms_chat_client,
    adapter_enabled=settings.codex_adapter_enabled,
    fallback_to_gms=settings.codex_fallback_to_gms,
    primary_provider=settings.llm_primary_provider,
    codex_model=settings.codex_model,
)

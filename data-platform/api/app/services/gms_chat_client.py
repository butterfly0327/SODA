from __future__ import annotations

from typing import Any

import httpx

from ..core.config import settings


class GmsChatClientError(RuntimeError):
    pass


class GmsChatClient:
    _MAX_ATTEMPTS = 2
    _RETRYABLE_ERRORS = {"GMS chat completion content is empty."}
    _HTTP_MAX_CONNECTIONS = 100
    _HTTP_MAX_KEEPALIVE_CONNECTIONS = 20
    _HTTP_KEEPALIVE_EXPIRY_SECONDS = 30.0

    def __init__(
        self,
        *,
        api_base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._api_base_url = (api_base_url or settings.gpt_api_base_url).rstrip("/")
        self._api_key = api_key or settings.api_key
        self._timeout_seconds = (
            timeout_seconds or settings.recommendation_http_timeout_seconds
        )
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
        last_error: GmsChatClientError | None = None
        for attempt in range(self._MAX_ATTEMPTS):
            try:
                response = await self._async_client.post(
                    f"{self._api_base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
            except httpx.TimeoutException as exc:
                raise GmsChatClientError(f"GMS chat completion timeout: {exc}") from exc
            except httpx.RequestError as exc:
                raise GmsChatClientError(
                    f"GMS chat completion request failed: {exc}"
                ) from exc

            try:
                return self._normalize_response(response, payload)
            except GmsChatClientError as exc:
                last_error = exc
                if not self._should_retry(exc, attempt):
                    raise

        assert last_error is not None
        raise last_error

    def create_chat_completion_sync(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: GmsChatClientError | None = None
        for attempt in range(self._MAX_ATTEMPTS):
            try:
                response = self._sync_client.post(
                    f"{self._api_base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
            except httpx.TimeoutException as exc:
                raise GmsChatClientError(f"GMS chat completion timeout: {exc}") from exc
            except httpx.RequestError as exc:
                raise GmsChatClientError(
                    f"GMS chat completion request failed: {exc}"
                ) from exc

            try:
                return self._normalize_response(response, payload)
            except GmsChatClientError as exc:
                last_error = exc
                if not self._should_retry(exc, attempt):
                    raise

        assert last_error is not None
        raise last_error

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _should_retry(self, error: GmsChatClientError, attempt: int) -> bool:
        if attempt >= self._MAX_ATTEMPTS - 1:
            return False
        return str(error) in self._RETRYABLE_ERRORS

    @staticmethod
    def _normalize_response(
        response: httpx.Response,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if response.status_code >= 400:
            raise GmsChatClientError(
                f"GMS chat completion failed(status={response.status_code}): {response.text[:300]}"
            )

        body = response.json()
        if not isinstance(body, dict):
            raise GmsChatClientError(
                "GMS chat completion response is not a JSON object."
            )

        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise GmsChatClientError("GMS chat completion response has no choices.")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise GmsChatClientError("GMS chat completion first choice is invalid.")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise GmsChatClientError("GMS chat completion message is missing.")

        content_text = GmsChatClient._extract_content_text(
            message.get("content")
        ).strip()
        if not content_text:
            raise GmsChatClientError("GMS chat completion content is empty.")

        return {
            "provider": "gms",
            "model": str(body.get("model") or payload.get("model") or ""),
            "content": content_text,
            "raw": body,
        }

    @staticmethod
    def _extract_content_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if not isinstance(content, list):
            return ""

        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
        return "".join(parts)

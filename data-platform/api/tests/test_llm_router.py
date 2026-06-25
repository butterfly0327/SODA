import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx


API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


class _FailingAdapterClient:
    async def create_chat_completion(self, payload: dict) -> dict:
        raise RuntimeError("adapter unavailable")


class _TimeoutAdapterClient:
    async def create_chat_completion(self, payload: dict) -> dict:
        raise TimeoutError("adapter timeout")


class _MalformedAdapterClient:
    async def create_chat_completion(self, payload: dict) -> dict:
        raise ValueError("malformed adapter response")


class _PassingGmsClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def create_chat_completion(self, payload: dict) -> dict:
        self.calls.append(payload)
        return {
            "provider": "gms",
            "model": "gpt-5.2",
            "content": "fallback-response",
            "raw": {"choices": [{"message": {"content": "fallback-response"}}]},
        }


class _PassingAdapterClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def create_chat_completion(self, payload: dict) -> dict:
        self.calls.append(payload)
        return {
            "provider": "codex",
            "model": "gpt-5.4",
            "content": "codex-response",
            "raw": {"choices": [{"message": {"content": "codex-response"}}]},
        }


class LlmRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_router_returns_codex_result_when_adapter_succeeds(self) -> None:
        from app.services.llm_router import LlmRouter

        adapter_client = _PassingAdapterClient()
        gms_client = _PassingGmsClient()
        router = LlmRouter(
            adapter_client=adapter_client,
            gms_client=gms_client,
            adapter_enabled=True,
            fallback_to_gms=True,
            codex_model="gpt-5.4",
        )

        result = await router.create_chat_completion(
            {
                "model": "gpt-5.2",
                "messages": [{"role": "user", "content": "recommend something"}],
            }
        )

        self.assertEqual(result["provider"], "codex")
        self.assertEqual(result["model"], "gpt-5.4")
        self.assertEqual(result["content"], "codex-response")
        self.assertEqual(adapter_client.calls[0]["model"], "gpt-5.4")
        self.assertEqual(len(gms_client.calls), 0)

    async def test_router_falls_back_to_gms_when_adapter_fails(self) -> None:
        from app.services.llm_router import LlmRouter

        gms_client = _PassingGmsClient()
        router = LlmRouter(
            adapter_client=_FailingAdapterClient(),
            gms_client=gms_client,
            adapter_enabled=True,
            fallback_to_gms=True,
        )

        result = await router.create_chat_completion(
            {
                "model": "gpt-5.4",
                "messages": [{"role": "user", "content": "recommend something"}],
            }
        )

        self.assertEqual(result["provider"], "gms")
        self.assertEqual(result["model"], "gpt-5.2")
        self.assertEqual(result["content"], "fallback-response")
        self.assertEqual(len(gms_client.calls), 1)

    async def test_router_falls_back_to_gms_when_adapter_times_out(self) -> None:
        from app.services.llm_router import LlmRouter

        gms_client = _PassingGmsClient()
        router = LlmRouter(
            adapter_client=_TimeoutAdapterClient(),
            gms_client=gms_client,
            adapter_enabled=True,
            fallback_to_gms=True,
        )

        result = await router.create_chat_completion(
            {
                "model": "gpt-5.2",
                "messages": [{"role": "user", "content": "hello"}],
            }
        )

        self.assertEqual(result["provider"], "gms")
        self.assertEqual(len(gms_client.calls), 1)

    async def test_router_falls_back_to_gms_when_adapter_response_is_malformed(self) -> None:
        from app.services.llm_router import LlmRouter

        gms_client = _PassingGmsClient()
        router = LlmRouter(
            adapter_client=_MalformedAdapterClient(),
            gms_client=gms_client,
            adapter_enabled=True,
            fallback_to_gms=True,
        )

        result = await router.create_chat_completion(
            {
                "model": "gpt-5.2",
                "messages": [{"role": "user", "content": "hello"}],
            }
        )

        self.assertEqual(result["provider"], "gms")
        self.assertEqual(len(gms_client.calls), 1)

    async def test_router_uses_gms_directly_when_adapter_disabled(self) -> None:
        from app.services.llm_router import LlmRouter

        adapter_client = _PassingAdapterClient()
        gms_client = _PassingGmsClient()
        router = LlmRouter(
            adapter_client=adapter_client,
            gms_client=gms_client,
            adapter_enabled=False,
            fallback_to_gms=True,
            primary_provider="gms",
        )

        result = await router.create_chat_completion(
            {
                "model": "gpt-5.2",
                "messages": [{"role": "user", "content": "hello"}],
            }
        )

        self.assertEqual(result["provider"], "gms")
        self.assertEqual(len(adapter_client.calls), 0)
        self.assertEqual(len(gms_client.calls), 1)


class _FakeAsyncClient:
    def __init__(self, recorder: dict[str, object], response: httpx.Response) -> None:
        self._recorder = recorder
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, headers: dict[str, str], json: dict) -> httpx.Response:
        self._recorder["url"] = url
        self._recorder["headers"] = headers
        self._recorder["json"] = json
        return self._response


class _FakeAsyncClientSequence:
    def __init__(self, recorder: dict[str, object], responses: list[httpx.Response]) -> None:
        self._recorder = recorder
        self._responses = list(responses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, headers: dict[str, str], json: dict) -> httpx.Response:
        self._recorder.setdefault("calls", []).append(
            {"url": url, "headers": headers, "json": json}
        )
        return self._responses.pop(0)


class _FakeSyncClientSequence:
    def __init__(self, recorder: dict[str, object], responses: list[httpx.Response]) -> None:
        self._recorder = recorder
        self._responses = list(responses)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url: str, headers: dict[str, str], json: dict) -> httpx.Response:
        self._recorder.setdefault("calls", []).append(
            {"url": url, "headers": headers, "json": json}
        )
        return self._responses.pop(0)


class GmsChatClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_gms_client_preserves_payload_model_and_auth_header(self) -> None:
        from app.services.gms_chat_client import GmsChatClient

        recorder: dict[str, object] = {}
        request = httpx.Request("POST", "https://gms.example.com/chat/completions")
        response = httpx.Response(
            200,
            request=request,
            json={
                "model": "gpt-5.2",
                "choices": [{"message": {"content": "ok"}}],
            },
        )

        with patch(
            "app.services.gms_chat_client.httpx.AsyncClient",
            return_value=_FakeAsyncClient(recorder, response),
        ):
            client = GmsChatClient(
                api_base_url="https://gms.example.com",
                api_key="secret-key",
                timeout_seconds=5.0,
            )
            result = await client.create_chat_completion(
                {
                    "model": "gpt-5.2",
                    "messages": [{"role": "user", "content": "hello"}],
                }
            )

        headers = recorder["headers"]
        payload = recorder["json"]
        self.assertEqual(payload["model"], "gpt-5.2")
        self.assertEqual(headers["Authorization"], "Bearer secret-key")
        self.assertEqual(result["model"], "gpt-5.2")

    async def test_gms_client_retries_once_when_first_response_content_is_empty(self) -> None:
        from app.services.gms_chat_client import GmsChatClient

        recorder: dict[str, object] = {}
        first_request = httpx.Request("POST", "https://gms.example.com/chat/completions")
        second_request = httpx.Request("POST", "https://gms.example.com/chat/completions")
        responses = [
            httpx.Response(
                200,
                request=first_request,
                json={
                    "model": "gpt-5.2",
                    "choices": [{"message": {"content": ""}}],
                },
            ),
            httpx.Response(
                200,
                request=second_request,
                json={
                    "model": "gpt-5.2",
                    "choices": [{"message": {"content": "ok"}}],
                },
            ),
        ]

        with patch(
            "app.services.gms_chat_client.httpx.AsyncClient",
            return_value=_FakeAsyncClientSequence(recorder, responses),
        ):
            client = GmsChatClient(
                api_base_url="https://gms.example.com",
                api_key="secret-key",
                timeout_seconds=5.0,
            )
            result = await client.create_chat_completion(
                {
                    "model": "gpt-5.2",
                    "messages": [{"role": "user", "content": "hello"}],
                }
            )

        self.assertEqual(result["content"], "ok")
        self.assertEqual(len(recorder["calls"]), 2)

    def test_gms_client_sync_retries_once_when_first_response_content_is_empty(self) -> None:
        from app.services.gms_chat_client import GmsChatClient

        recorder: dict[str, object] = {}
        first_request = httpx.Request("POST", "https://gms.example.com/chat/completions")
        second_request = httpx.Request("POST", "https://gms.example.com/chat/completions")
        responses = [
            httpx.Response(
                200,
                request=first_request,
                json={
                    "model": "gpt-5.2",
                    "choices": [{"message": {"content": ""}}],
                },
            ),
            httpx.Response(
                200,
                request=second_request,
                json={
                    "model": "gpt-5.2",
                    "choices": [{"message": {"content": "ok"}}],
                },
            ),
        ]

        with patch(
            "app.services.gms_chat_client.httpx.Client",
            return_value=_FakeSyncClientSequence(recorder, responses),
        ):
            client = GmsChatClient(
                api_base_url="https://gms.example.com",
                api_key="secret-key",
                timeout_seconds=5.0,
            )
            result = client.create_chat_completion_sync(
                {
                    "model": "gpt-5.2",
                    "messages": [{"role": "user", "content": "hello"}],
                }
            )

        self.assertEqual(result["content"], "ok")
        self.assertEqual(len(recorder["calls"]), 2)


if __name__ == "__main__":
    unittest.main()

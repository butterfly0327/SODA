import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


class _DummyAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeAcquireContext:
    def __init__(self, rows):
        self._rows = rows

    async def __aenter__(self):
        return SimpleNamespace(fetch=AsyncMock(return_value=self._rows))

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakePool:
    def __init__(self, rows):
        self._rows = rows

    def acquire(self):
        return _FakeAcquireContext(self._rows)


class ChatIntentServiceModelTest(unittest.IsolatedAsyncioTestCase):
    async def test_infer_recommendation_mode_uses_response_model(self) -> None:
        from app.services.chat_intent_service import ChatIntentService

        service = ChatIntentService()
        response_body = {
            "model": "gpt-5.4",
            "choices": [
                {
                    "message": {
                        "content": '{"mode":"DATASET_ONLY"}',
                    }
                }
            ],
        }

        with patch.object(
            ChatIntentService,
            "_post_chat_completion",
            new=AsyncMock(return_value=response_body),
        ):
            result = await service.infer_recommendation_mode(prompt="데이터 추천해줘")

        self.assertEqual(result.mode, "DATASET_ONLY")
        self.assertEqual(result.llm_model, "gpt-5.4")


class RagServiceModelTest(unittest.IsolatedAsyncioTestCase):
    async def test_query_returns_answer_retrieved_and_actual_model(self) -> None:
        from app.services.rag_service import RagService

        service = RagService()
        rows = [
            {
                "id": 7,
                "name": "Weather API",
                "description": "Forecast data",
                "provider": "NOAA",
                "base_url": "https://example.com",
                "docs_url": "https://example.com/docs",
                "auth_type": "API_KEY",
                "category": "weather",
                "tags": ["forecast"],
                "is_free": True,
                "score": 0.92,
            }
        ]

        with patch("app.services.rag_service.httpx.AsyncClient", _DummyAsyncClient), patch.object(
            service,
            "_get_pool",
            new=AsyncMock(return_value=_FakePool(rows)),
        ), patch.object(
            service,
            "_embed_query",
            new=AsyncMock(return_value=[0.1, 0.2, 0.3]),
        ), patch.object(
            service,
            "_extract_count_with_llm",
            new=AsyncMock(return_value=1),
        ), patch.object(
            service,
            "_call_gpt",
            new=AsyncMock(return_value=("추천 답변", "gpt-5.4")),
        ):
            answer, retrieved, llm_model = await service.query("날씨 API 추천해줘")

        self.assertEqual(answer, "추천 답변")
        self.assertEqual(llm_model, "gpt-5.4")
        self.assertEqual(len(retrieved), 1)


class DatasetRecommendationServiceModelTest(unittest.TestCase):
    def test_rank_llm_response_keeps_actual_model(self) -> None:
        from app.services.dataset_recommendation_service import DatasetRecommendationService
        from app.services import dataset_recommendation_service as dataset_module

        service = DatasetRecommendationService()
        completion = {
            "provider": "codex",
            "model": "gpt-5.4",
            "content": '{"summaryReason":"ok","recommendedItems":[]}',
            "raw": {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": '{"summaryReason":"ok","recommendedItems":[]}',
                        },
                    }
                ],
                "usage": {
                    "completion_tokens": 20,
                    "completion_tokens_details": {"reasoning_tokens": 5},
                },
            },
        }

        with patch.object(
            dataset_module.llm_router,
            "create_chat_completion_sync",
            return_value=completion,
        ):
            result = service._request_rank_with_llm(
                payload={"model": "gpt-5.2", "messages": []},
                max_completion_tokens=100,
            )

        self.assertEqual(result.llm_model, "gpt-5.4")


class MergeRecommendationServiceModelTest(unittest.TestCase):
    def test_merge_with_llm_returns_text_and_actual_model(self) -> None:
        from app.schemas.recommendation import ConversationHistoryItem
        from app.services.merge_recommendation_service import MergeRecommendationService

        service = MergeRecommendationService()
        merged_text = (
            "데이터셋 근거를 반영했습니다. "
            "Open API 근거도 반영했습니다. "
            "적용 전 확인 필요가 있습니다. "
            "전체 연계 목적에 맞춰 정리했습니다."
        )

        with patch.object(
            service,
            "_request_merge_text",
            return_value=(merged_text, "gpt-5.4"),
        ):
            final_text, llm_model = service._merge_with_llm(
                prompt="추천 결과를 합쳐줘",
                history=[ConversationHistoryItem(role="USER", content="추천해줘")],
                dataset_reason="데이터셋 후보는 활용성이 높습니다.",
                openapi_reason="Open API 후보는 연계성이 높습니다.",
            )

        self.assertEqual(final_text, merged_text)
        self.assertEqual(llm_model, "gpt-5.4")


if __name__ == "__main__":
    unittest.main()

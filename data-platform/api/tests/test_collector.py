import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.api.v1.endpoints import collector as collector_endpoint  # noqa: E402
from app.main import app  # noqa: E402


class CollectorEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_start_dataset_collection_run_enqueues_celery_task(self) -> None:
        payload = {
            "datasetSourceId": "huggingface",
            "parserVersion": "v1.0.0",
            "limit": 25,
            "fromScratch": False,
            "safe": True,
        }

        with patch.object(
            collector_endpoint,
            "enqueue_dataset_collection",
            create=True,
            return_value="task-123",
        ) as enqueue_mock:
            response = self.client.post("/v1/collector/datasets/runs", json=payload)

        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertEqual(body["status"], 202)
        self.assertEqual(body["datasetSourceId"], "huggingface")
        self.assertEqual(body["parserVersion"], "v1.0.0")
        self.assertEqual(body["taskId"], "task-123")
        enqueue_mock.assert_called_once()
        run_request = enqueue_mock.call_args.args[0]
        self.assertEqual(run_request.dataset_source_id, "huggingface")
        self.assertEqual(run_request.parser_version, "v1.0.0")
        self.assertEqual(run_request.limit, 25)
        self.assertTrue(run_request.safe)
        self.assertEqual(run_request.exclude_source_ids, [])
        self.assertFalse(run_request.reconcile_missing)
        self.assertIsNone(run_request.max_runtime_seconds)

    def test_start_dataset_collection_run_returns_500_when_enqueue_fails(self) -> None:
        payload = {
            "datasetSourceId": "huggingface",
            "parserVersion": "v1.0.0",
        }

        with patch.object(
            collector_endpoint,
            "enqueue_dataset_collection",
            create=True,
            side_effect=RuntimeError("broker down"),
        ):
            response = self.client.post("/v1/collector/datasets/runs", json=payload)

        self.assertEqual(response.status_code, 500)
        body = response.json()
        self.assertEqual(body["status"], 500)
        self.assertIn("broker down", body["message"])

    def test_enqueue_dataset_collection_includes_parser_version(self) -> None:
        run_request = collector_endpoint.CollectorRunRequest(
            dataset_source_id="huggingface",
            parser_version="v2.0.0",
            limit=11,
            from_scratch=True,
            safe=False,
            exclude_source_ids=["kaggle"],
            reconcile_missing=True,
            triggered_by="qa",
            max_runtime_seconds=1200,
        )

        with patch.object(
            collector_endpoint.collect_dataset_metadata,
            "apply_async",
            return_value=type("Result", (), {"id": "task-xyz"})(),
        ) as apply_async_mock:
            task_id = collector_endpoint.enqueue_dataset_collection(run_request)

        self.assertEqual(task_id, "task-xyz")
        self.assertEqual(
            apply_async_mock.call_args.kwargs["kwargs"],
            {
                "source": "huggingface",
                "limit": 11,
                "max_runtime_seconds": 1200,
                "from_scratch": True,
                "safe": False,
                "exclude_sources": ["kaggle"],
                "reconcile_missing": True,
                "parser_version": "v2.0.0",
            },
        )

    def test_start_dataset_collection_run_forwards_excluded_sources(self) -> None:
        payload = {
            "datasetSourceId": "all",
            "parserVersion": "v1.0.0",
            "excludeSourceIds": ["kaggle", "aihub"],
        }

        with patch.object(
            collector_endpoint,
            "enqueue_dataset_collection",
            create=True,
            return_value="task-456",
        ) as enqueue_mock:
            response = self.client.post("/v1/collector/datasets/runs", json=payload)

        self.assertEqual(response.status_code, 202)
        run_request = enqueue_mock.call_args.args[0]
        self.assertEqual(run_request.exclude_source_ids, ["kaggle", "aihub"])

if __name__ == "__main__":
    unittest.main()

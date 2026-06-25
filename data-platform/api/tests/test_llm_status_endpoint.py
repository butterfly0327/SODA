import os
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

os.environ.setdefault("LLM_PRIMARY_PROVIDER", "codex")

from app.main import app  # noqa: E402


class LlmStatusEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_llm_status_endpoint_returns_provider_snapshot(self) -> None:
        response = self.client.get("/v1/internal/llm/status")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["primaryProvider"], "codex")
        self.assertIn("codex", body)
        self.assertIn("authPresent", body["codex"])


if __name__ == "__main__":
    unittest.main()

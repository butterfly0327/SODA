import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.main import app  # noqa: E402


class MetricsEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_metrics_endpoint_is_exposed(self) -> None:
        response = self.client.get("/metrics")

        self.assertEqual(response.status_code, 200)
        self.assertIn("http_requests_total", response.text)


if __name__ == "__main__":
    unittest.main()

import sys
import unittest
from pathlib import Path


API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.observability.dataset_collection_metrics import (  # noqa: E402
    DatasetCollectionMetricsCollector,
)


def _sample_value(metric, labels: dict[str, str]) -> float | None:
    for sample in metric.samples:
        if all(sample.labels.get(key) == value for key, value in labels.items()):
            return float(sample.value)
    return None


class DatasetCollectionMetricsCollectorTests(unittest.TestCase):
    def test_collect_emits_source_metrics_from_snapshot(self) -> None:
        collector = DatasetCollectionMetricsCollector("postgresql://unused", "dev")
        collector._fetch_snapshot = lambda: {  # type: ignore[method-assign]
            "latest_runs": [
                {
                    "source_code": "huggingface",
                    "collection_type": "API",
                    "is_active": True,
                    "last_status": "SUCCESS",
                    "last_run_started_at_epoch": 100.0,
                    "last_run_finished_at_epoch": 130.0,
                    "last_duration_seconds": 30.0,
                    "last_collected_count": 20,
                    "last_upserted_count": 10,
                    "last_failed_count": 1,
                }
            ],
            "inventory": [
                {
                    "source_code": "huggingface",
                    "active_record_count": 125,
                    "error_record_count": 2,
                    "active_total_size_bytes": 4096,
                    "last_ingested_at_epoch": 200.0,
                }
            ],
            "recent_runs": [
                {
                    "source_code": "huggingface",
                    "status": "SUCCESS",
                    "run_count": 3,
                }
            ],
        }

        metrics = {metric.name: metric for metric in collector.collect()}

        self.assertEqual(
            _sample_value(
                metrics["soda_dataset_metrics_scrape_success"],
                {"env": "dev"},
            ),
            1.0,
        )
        self.assertEqual(
            _sample_value(
                metrics["soda_dataset_collection_last_status"],
                {"env": "dev", "source": "huggingface", "status": "SUCCESS"},
            ),
            1.0,
        )
        self.assertEqual(
            _sample_value(
                metrics["soda_dataset_active_records_total"],
                {"env": "dev", "source": "huggingface"},
            ),
            125.0,
        )
        self.assertEqual(
            _sample_value(
                metrics["soda_dataset_collection_runs_last_24h"],
                {"env": "dev", "source": "huggingface", "status": "SUCCESS"},
            ),
            3.0,
        )

    def test_collect_reports_scrape_failure_when_dsn_missing(self) -> None:
        collector = DatasetCollectionMetricsCollector("", "prod")
        metrics = {metric.name: metric for metric in collector.collect()}

        self.assertEqual(
            _sample_value(
                metrics["soda_dataset_metrics_scrape_success"],
                {"env": "prod"},
            ),
            0.0,
        )

    def test_collect_reuses_cached_snapshot_within_ttl(self) -> None:
        collector = DatasetCollectionMetricsCollector("postgresql://unused", "prod", cache_ttl_seconds=300)
        calls = {"count": 0}

        def fetch_snapshot():
            calls["count"] += 1
            return {
                "latest_runs": [],
                "inventory": [],
                "recent_runs": [],
            }

        collector._fetch_snapshot = fetch_snapshot  # type: ignore[method-assign]

        list(collector.collect())
        list(collector.collect())

        self.assertEqual(calls["count"], 1)

    def test_collect_skips_cache_when_ttl_disabled(self) -> None:
        collector = DatasetCollectionMetricsCollector("postgresql://unused", "prod", cache_ttl_seconds=0)
        calls = {"count": 0}

        def fetch_snapshot():
            calls["count"] += 1
            return {
                "latest_runs": [],
                "inventory": [],
                "recent_runs": [],
            }

        collector._fetch_snapshot = fetch_snapshot  # type: ignore[method-assign]

        list(collector.collect())
        list(collector.collect())

        self.assertEqual(calls["count"], 2)


if __name__ == "__main__":
    unittest.main()

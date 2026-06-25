from __future__ import annotations

import importlib
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock


PROJECT_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if PROJECT_SRC not in sys.path:
    sys.path.insert(0, PROJECT_SRC)

base_module = importlib.import_module("metadata_ingest.base")
models_module = importlib.import_module("metadata_ingest.models")

BaseDatasetCollector = base_module.BaseDatasetCollector
CollectionRunInfo = models_module.CollectionRunInfo
NormalizedDatasetRecord = models_module.NormalizedDatasetRecord
SourceDefinition = models_module.SourceDefinition


def _make_settings() -> SimpleNamespace:
    return SimpleNamespace(
        user_agent="test-agent",
        request_timeout_seconds=3,
        connect_timeout_seconds=3,
        verify_ssl=False,
        min_request_interval_seconds=0.0,
        request_interval_jitter_seconds=0.0,
        batch_pause_every=0,
        batch_pause_seconds=0.0,
        per_source_cooldown_seconds=0.0,
        runtime_safe_mode=False,
        retry_status_codes={429, 500, 502, 503, 504},
        retry_max_sleep_seconds=1.0,
        save_every=10,
        parser_version="test",
    )


class _FakeCollector(BaseDatasetCollector):
    source = SourceDefinition(
        source_code="PUBLIC_DATA_PORTAL",
        source_name="공공데이터포털",
        base_url="https://www.data.go.kr",
        collection_type="CRAWL",
    )

    def __init__(self, db, settings, records):
        super().__init__(db=db, settings=settings)
        self._records = records

    def iter_records(self, checkpoint):
        for item in self._records:
            yield item


class ReconciliationTests(unittest.TestCase):
    def test_reconcile_requires_from_scratch(self) -> None:
        db = Mock()
        collector = _FakeCollector(db=db, settings=_make_settings(), records=[])

        with self.assertRaisesRegex(ValueError, "from-scratch"):
            collector.run(resume=True, limit=None, reconcile_missing=True)

        db.start_run.assert_not_called()

    def test_reconcile_requires_unbounded_run(self) -> None:
        db = Mock()
        collector = _FakeCollector(db=db, settings=_make_settings(), records=[])

        with self.assertRaisesRegex(ValueError, "limit"):
            collector.run(resume=False, limit=10, reconcile_missing=True)

        db.start_run.assert_not_called()

    def test_full_refresh_can_mark_missing_rows_inactive(self) -> None:
        db = Mock()
        db.start_run.return_value = CollectionRunInfo(
            run_id=99,
            source_id=7,
            checkpoint_json={},
        )
        db.deactivate_missing_datasets.return_value = 5

        record = NormalizedDatasetRecord(
            source_dataset_key="15000249",
            canonical_url="https://www.data.go.kr/data/15000249/fileData.do",
            landing_url="https://www.data.go.kr/data/15000249/fileData.do",
            title="sample",
            description_short="sample description",
        )
        collector = _FakeCollector(
            db=db,
            settings=_make_settings(),
            records=[(record, {"page": 1})],
        )

        stats = collector.run(resume=False, limit=None, reconcile_missing=True)

        self.assertEqual(stats.upserted_count, 1)
        self.assertEqual(stats.deactivated_count, 5)
        db.deactivate_missing_datasets.assert_called_once_with(source_id=7, run_id=99)
        db.finalize_run.assert_called_once()
        self.assertEqual(db.finalize_run.call_args.args[1], "SUCCESS")

    def test_reconcile_is_skipped_when_run_has_failures(self) -> None:
        db = Mock()
        db.start_run.return_value = CollectionRunInfo(
            run_id=100,
            source_id=8,
            checkpoint_json={},
        )
        db.upsert_dataset.side_effect = [None, RuntimeError("bad row")]

        records = [
            (
                NormalizedDatasetRecord(
                    source_dataset_key="15000249",
                    canonical_url="https://www.data.go.kr/data/15000249/fileData.do",
                    landing_url="https://www.data.go.kr/data/15000249/fileData.do",
                    title="row-1",
                    description_short="row-1 description",
                ),
                {"page": 1},
            ),
            (
                NormalizedDatasetRecord(
                    source_dataset_key="15000250",
                    canonical_url="https://www.data.go.kr/data/15000250/fileData.do",
                    landing_url="https://www.data.go.kr/data/15000250/fileData.do",
                    title="row-2",
                    description_short="row-2 description",
                ),
                {"page": 1},
            ),
        ]
        collector = _FakeCollector(db=db, settings=_make_settings(), records=records)

        stats = collector.run(resume=False, limit=None, reconcile_missing=True)

        self.assertEqual(stats.failed_count, 1)
        self.assertEqual(stats.deactivated_count, 0)
        db.deactivate_missing_datasets.assert_not_called()
        self.assertEqual(db.finalize_run.call_args.args[1], "PARTIAL_SUCCESS")


if __name__ == "__main__":
    unittest.main()

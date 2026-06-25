from __future__ import annotations

import importlib
import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if PROJECT_SRC not in sys.path:
    sys.path.insert(0, PROJECT_SRC)

cli_module = importlib.import_module("metadata_ingest.cli")
db_module = importlib.import_module("metadata_ingest.db")
models_module = importlib.import_module("metadata_ingest.models")

Database = db_module.Database
SourceDefinition = models_module.SourceDefinition
SourceRunAlreadyActiveError = getattr(
    db_module,
    "SourceRunAlreadyActiveError",
    type("SourceRunAlreadyActiveError", (RuntimeError,), {}),
)


class StartRunLockTests(unittest.TestCase):
    def test_start_run_raises_when_source_lock_unavailable(self) -> None:
        db = Database("postgresql://unused")
        db.conn = object()
        source = SourceDefinition(
            source_code="HUGGINGFACE",
            source_name="Hugging Face",
            base_url="https://huggingface.co",
            collection_type="API",
        )

        with patch.object(db, "ensure_dataset_source", return_value=7), patch.object(
            db, "_try_acquire_source_lock", create=True, return_value=False
        ), patch.object(
            db,
            "_cursor",
            side_effect=AssertionError("cursor should not be used before lock"),
        ), patch.object(
            db, "commit"
        ):
            with self.assertRaisesRegex(RuntimeError, "active"):
                db.start_run(source, "test-parser")


class CliSkipSummaryTests(unittest.TestCase):
    def test_cli_reports_overlap_as_skipped(self) -> None:
        fake_settings = SimpleNamespace(
            database_url="postgresql://unused",
            parser_version="test-parser",
            safe_mode_default=True,
            runtime_safe_mode=True,
            max_per_source=None,
            default_safe_limit=20,
            max_safe_limit=100,
            per_source_cooldown_seconds=0.0,
            validate=lambda: None,
        )

        class FakeDatabaseContext:
            def __init__(self, _dsn: str):
                self._db = SimpleNamespace()

            def __enter__(self):
                return self._db

            def __exit__(self, exc_type, exc, tb):
                return False

        class FakeCollector:
            def __init__(self, db, settings):
                self.db = db
                self.settings = settings

            def run(
                self,
                *,
                resume: bool = True,
                limit: int | None = None,
                reconcile_missing: bool = False,
            ):
                raise SourceRunAlreadyActiveError(
                    "same source run is already active"
                )

        with patch.object(cli_module, "Settings", return_value=fake_settings), patch.object(
            cli_module, "Database", FakeDatabaseContext
        ), patch.object(
            cli_module, "COLLECTORS", {"huggingface": FakeCollector}
        ), patch.object(
            sys, "argv", ["metadata_ingest", "--source", "huggingface"]
        ), patch(
            "builtins.print"
        ) as print_mock:
            cli_module.main()

        printed = print_mock.call_args[0][0]
        summary = json.loads(printed)
        self.assertEqual(summary["huggingface"]["status"], "skipped")

    def test_cli_reconcile_missing_keeps_unbounded_limit_in_safe_mode(self) -> None:
        fake_settings = SimpleNamespace(
            database_url="postgresql://unused",
            parser_version="test-parser",
            safe_mode_default=True,
            runtime_safe_mode=True,
            max_per_source=None,
            default_safe_limit=20,
            max_safe_limit=100,
            per_source_cooldown_seconds=0.0,
            min_request_interval_seconds=1.0,
            request_interval_jitter_seconds=0.1,
            batch_pause_every=10,
            batch_pause_seconds=8.0,
            validate=lambda: None,
        )

        captured: dict[str, object] = {}

        class FakeDatabaseContext:
            def __init__(self, _dsn: str):
                self._db = SimpleNamespace()

            def __enter__(self):
                return self._db

            def __exit__(self, exc_type, exc, tb):
                return False

        class FakeCollector:
            def __init__(self, db, settings):
                self.db = db
                self.settings = settings

            def run(
                self,
                *,
                resume: bool = True,
                limit: int | None = None,
                reconcile_missing: bool = False,
            ):
                captured["resume"] = resume
                captured["limit"] = limit
                captured["reconcile_missing"] = reconcile_missing
                return SimpleNamespace(
                    collected_count=1,
                    upserted_count=1,
                    deactivated_count=2,
                    failed_count=0,
                    last_saved_source_dataset_key="key-1",
                )

        with patch.object(cli_module, "Settings", return_value=fake_settings), patch.object(
            cli_module, "Database", FakeDatabaseContext
        ), patch.object(
            cli_module, "COLLECTORS", {"public_data_portal": FakeCollector}
        ), patch.object(
            sys,
            "argv",
            [
                "metadata_ingest",
                "--source",
                "public_data_portal",
                "--from-scratch",
                "--reconcile-missing",
            ],
        ):
            cli_module.main()

        self.assertFalse(captured["resume"])
        self.assertIsNone(captured["limit"])
        self.assertTrue(captured["reconcile_missing"])


if __name__ == "__main__":
    unittest.main()

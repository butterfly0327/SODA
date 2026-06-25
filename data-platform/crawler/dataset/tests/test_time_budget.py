from __future__ import annotations

import contextlib
import importlib
import io
import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch


PROJECT_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if PROJECT_SRC not in sys.path:
    sys.path.insert(0, PROJECT_SRC)

if "httpx" not in sys.modules:
    httpx_module = types.ModuleType("httpx")

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def close(self):
            return None

        def request(self, *args, **kwargs):
            raise AssertionError("request should not be called in test_time_budget")

    class _FakeTimeout:
        def __init__(self, *args, **kwargs):
            pass

    class _FakeLimits:
        def __init__(self, *args, **kwargs):
            pass

    class _FakeRequestError(Exception):
        pass

    class _FakeHTTPStatusError(Exception):
        def __init__(self, response=None):
            super().__init__("http status error")
            self.response = response

    httpx_module.Client = _FakeClient
    httpx_module.Timeout = _FakeTimeout
    httpx_module.Limits = _FakeLimits
    httpx_module.RequestError = _FakeRequestError
    httpx_module.HTTPStatusError = _FakeHTTPStatusError
    sys.modules["httpx"] = httpx_module

if "bs4" not in sys.modules:
    bs4_module = types.ModuleType("bs4")

    class _FakeBeautifulSoup:
        def __init__(self, *args, **kwargs):
            pass

    bs4_module.BeautifulSoup = _FakeBeautifulSoup
    sys.modules["bs4"] = bs4_module

if "psycopg" not in sys.modules:
    psycopg_module = types.ModuleType("psycopg")
    psycopg_sql_module = types.ModuleType("psycopg.sql")
    psycopg_rows_module = types.ModuleType("psycopg.rows")
    psycopg_types_module = types.ModuleType("psycopg.types")
    psycopg_types_json_module = types.ModuleType("psycopg.types.json")

    class _FakeJsonb:
        def __init__(self, value):
            self.value = value

    psycopg_module.connect = lambda *args, **kwargs: None
    psycopg_module.Connection = object
    psycopg_sql_module.SQL = lambda value="": value
    psycopg_sql_module.Identifier = lambda value="": value
    psycopg_rows_module.dict_row = object()
    psycopg_types_json_module.Jsonb = _FakeJsonb
    sys.modules["psycopg"] = psycopg_module
    sys.modules["psycopg.sql"] = psycopg_sql_module
    sys.modules["psycopg.rows"] = psycopg_rows_module
    sys.modules["psycopg.types"] = psycopg_types_module
    sys.modules["psycopg.types.json"] = psycopg_types_json_module

base_module = importlib.import_module("metadata_ingest.base")
cli_module = importlib.import_module("metadata_ingest.cli")
models_module = importlib.import_module("metadata_ingest.models")

BaseDatasetCollector = base_module.BaseDatasetCollector
CollectionRunInfo = models_module.CollectionRunInfo
HarvestStats = models_module.HarvestStats
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
        runtime_safe_mode=True,
        retry_status_codes={429, 500, 502, 503, 504},
        retry_max_sleep_seconds=1.0,
        save_every=10,
        parser_version="test",
        safe_mode_default=True,
        max_per_source=None,
        default_safe_limit=60,
        max_safe_limit=400,
        database_url="postgresql://test:test@localhost:5432/test",
        validate=lambda: None,
    )


class _FakeCollector(BaseDatasetCollector):
    source = SourceDefinition(
        source_code="FIGSHARE",
        source_name="Figshare",
        base_url="https://api.figshare.com/v2",
        collection_type="API",
    )

    def __init__(self, db, settings, records):
        super().__init__(db=db, settings=settings)
        self._records = records

    def iter_records(self, checkpoint):
        for item in self._records:
            yield item


class _CliCollector:
    last_call = None

    def __init__(self, db, settings):
        self.db = db
        self.settings = settings

    def run(self, *, resume=True, limit=None, reconcile_missing=False, max_runtime_seconds=None):
        _CliCollector.last_call = {
            "resume": resume,
            "limit": limit,
            "reconcile_missing": reconcile_missing,
            "max_runtime_seconds": max_runtime_seconds,
        }
        return HarvestStats(
            collected_count=1,
            upserted_count=1,
            deactivated_count=0,
            failed_count=0,
            last_saved_source_dataset_key="row-1",
        )


class _NullDatabase:
    def __init__(self, *_args, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TimeBudgetCollectorTests(unittest.TestCase):
    def test_run_stops_after_time_budget_and_keeps_checkpoint(self) -> None:
        db = Mock()
        db.start_run.return_value = CollectionRunInfo(
            run_id=101,
            source_id=5,
            checkpoint_json={},
        )

        records = [
            (
                NormalizedDatasetRecord(
                    source_dataset_key="row-1",
                    canonical_url="https://example.com/1",
                    landing_url="https://example.com/1",
                    title="row-1",
                    description_short="first",
                ),
                {"page": 1},
            ),
            (
                NormalizedDatasetRecord(
                    source_dataset_key="row-2",
                    canonical_url="https://example.com/2",
                    landing_url="https://example.com/2",
                    title="row-2",
                    description_short="second",
                ),
                {"page": 1},
            ),
        ]
        collector = _FakeCollector(db=db, settings=_make_settings(), records=records)

        with patch.object(base_module.time, "monotonic", side_effect=[0.0, 0.0, 1.3]):
            stats = collector.run(
                resume=True,
                limit=None,
                reconcile_missing=False,
                max_runtime_seconds=1.0,
            )

        self.assertEqual(stats.upserted_count, 1)
        self.assertEqual(db.upsert_dataset.call_count, 1)
        self.assertEqual(
            db.finalize_run.call_args.kwargs["checkpoint_json"]["last_saved_source_dataset_key"],
            "row-1",
        )


class TimeBudgetCliTests(unittest.TestCase):
    def test_safe_mode_with_runtime_budget_does_not_inject_default_safe_limit(self) -> None:
        _CliCollector.last_call = None
        settings = _make_settings()

        with patch.object(cli_module, "Settings", return_value=settings), patch.object(
            cli_module,
            "Database",
            _NullDatabase,
        ), patch.dict(
            cli_module.COLLECTORS,
            {"test_source": _CliCollector},
            clear=True,
        ), patch.object(
            sys,
            "argv",
            ["metadata_ingest", "--source", "test_source", "--safe", "--max-runtime-seconds", "1200"],
        ), contextlib.redirect_stdout(io.StringIO()):
            cli_module.main()

        self.assertIsNotNone(_CliCollector.last_call)
        self.assertIsNone(_CliCollector.last_call["limit"])
        self.assertEqual(_CliCollector.last_call["max_runtime_seconds"], 1200)

    def test_safe_mode_with_runtime_budget_does_not_cap_explicit_limit(self) -> None:
        _CliCollector.last_call = None
        settings = _make_settings()

        with patch.object(cli_module, "Settings", return_value=settings), patch.object(
            cli_module,
            "Database",
            _NullDatabase,
        ), patch.dict(
            cli_module.COLLECTORS,
            {"test_source": _CliCollector},
            clear=True,
        ), patch.object(
            sys,
            "argv",
            [
                "metadata_ingest",
                "--source",
                "test_source",
                "--safe",
                "--limit",
                "10000",
                "--max-runtime-seconds",
                "1200",
            ],
        ), contextlib.redirect_stdout(io.StringIO()):
            cli_module.main()

        self.assertIsNotNone(_CliCollector.last_call)
        self.assertEqual(_CliCollector.last_call["limit"], 10000)
        self.assertEqual(_CliCollector.last_call["max_runtime_seconds"], 1200)


if __name__ == "__main__":
    unittest.main()

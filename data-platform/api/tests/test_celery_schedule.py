import importlib
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

if "celery" not in sys.modules:
    celery_module = types.ModuleType("celery")
    schedules_module = types.ModuleType("celery.schedules")

    class _FakeConf(dict):
        def update(self, *args, **kwargs):
            super().update(*args, **kwargs)
            for key, value in dict(*args, **kwargs).items():
                setattr(self, key, value)

    class _FakeTask:
        def __init__(self, func):
            self.run = func

        def __call__(self, *args, **kwargs):
            return self.run(*args, **kwargs)

    class _FakeCelery:
        def __init__(self, *args, **kwargs):
            self.conf = _FakeConf()

        def task(self, *args, **kwargs):
            def decorator(func):
                return _FakeTask(func)

            return decorator

    class _FakeCrontab:
        def __init__(self, minute=None, hour=None):
            self._orig_minute = minute
            self._orig_hour = hour

    celery_module.Celery = _FakeCelery
    schedules_module.crontab = _FakeCrontab
    sys.modules["celery"] = celery_module
    sys.modules["celery.schedules"] = schedules_module


class DatasetBeatScheduleTests(unittest.TestCase):
    def _reload_celery_module(self, env: dict[str, str]):
        with patch.dict(os.environ, env, clear=False):
            import app.core.celery_app as celery_module  # noqa: WPS433

            return importlib.reload(celery_module)

    def test_default_dataset_schedule_includes_all_sources(self) -> None:
        celery_module = self._reload_celery_module(
            {
                "DATASET_AUTO_COLLECTION_ENABLED": "true",
                "DEFAULT_SAFE_LIMIT": "33",
            }
        )

        beat_schedule = celery_module.celery_app.conf.beat_schedule
        dataset_entries = {
            name: config
            for name, config in beat_schedule.items()
            if name.startswith("dataset-auto-collect-")
        }

        self.assertEqual(len(dataset_entries), 10)
        huggingface = dataset_entries["dataset-auto-collect-huggingface"]
        self.assertEqual(huggingface["task"], "platform.collect_dataset_metadata")
        self.assertEqual(huggingface["kwargs"]["source"], "huggingface")
        self.assertEqual(huggingface["kwargs"]["limit"], 33)
        self.assertTrue(huggingface["kwargs"]["safe"])
        self.assertFalse(huggingface["kwargs"]["from_scratch"])

    def test_dataset_schedule_spreads_sources_within_four_hour_window(self) -> None:
        celery_module = self._reload_celery_module(
            {
                "DATASET_AUTO_COLLECTION_ENABLED": "true",
                "DATASET_AUTO_COLLECTION_SOURCES": "huggingface,figshare,zenodo",
                "DATASET_AUTO_COLLECTION_INTERVAL_HOURS": "4",
                "DATASET_AUTO_COLLECTION_LIMIT": "15",
            }
        )

        beat_schedule = celery_module.celery_app.conf.beat_schedule
        huggingface_schedule = beat_schedule["dataset-auto-collect-huggingface"][
            "schedule"
        ]
        figshare_schedule = beat_schedule["dataset-auto-collect-figshare"]["schedule"]
        zenodo_schedule = beat_schedule["dataset-auto-collect-zenodo"]["schedule"]

        self.assertEqual(huggingface_schedule._orig_minute, 0)
        self.assertEqual(huggingface_schedule._orig_hour, "0,4,8,12,16,20")

        self.assertEqual(figshare_schedule._orig_minute, 20)
        self.assertEqual(figshare_schedule._orig_hour, "1,5,9,13,17,21")

        self.assertEqual(zenodo_schedule._orig_minute, 40)
        self.assertEqual(zenodo_schedule._orig_hour, "2,6,10,14,18,22")

    def test_full_reconcile_schedule_is_disabled_by_default(self) -> None:
        celery_module = self._reload_celery_module({})

        beat_schedule = celery_module.celery_app.conf.beat_schedule
        reconcile_entries = {
            name: config
            for name, config in beat_schedule.items()
            if name.startswith("dataset-full-reconcile-")
        }

        self.assertEqual(reconcile_entries, {})

    def test_full_reconcile_schedule_can_be_enabled(self) -> None:
        celery_module = self._reload_celery_module(
            {
                "DATASET_AUTO_COLLECTION_ENABLED": "false",
                "DATASET_FULL_RECONCILE_ENABLED": "true",
                "DATASET_FULL_RECONCILE_SOURCES": "public_data_portal,figshare",
                "DATASET_FULL_RECONCILE_START_HOUR": "1",
                "DATASET_FULL_RECONCILE_START_MINUTE": "10",
                "DATASET_FULL_RECONCILE_SOURCE_INTERVAL_MINUTES": "30",
            }
        )

        beat_schedule = celery_module.celery_app.conf.beat_schedule
        portal = beat_schedule["dataset-full-reconcile-public_data_portal"]
        figshare = beat_schedule["dataset-full-reconcile-figshare"]

        self.assertEqual(portal["task"], "platform.collect_dataset_metadata")
        self.assertEqual(
            portal["kwargs"],
            {
                "source": "public_data_portal",
                "from_scratch": True,
                "reconcile_missing": True,
                "safe": True,
            },
        )
        self.assertEqual(portal["schedule"]._orig_hour, 1)
        self.assertEqual(portal["schedule"]._orig_minute, 10)

        self.assertEqual(figshare["schedule"]._orig_hour, 1)
        self.assertEqual(figshare["schedule"]._orig_minute, 40)

    def test_auto_collection_time_budget_removes_count_cap(self) -> None:
        celery_module = self._reload_celery_module(
            {
                "DATASET_AUTO_COLLECTION_ENABLED": "true",
                "DATASET_AUTO_COLLECTION_MAX_RUNTIME_SECONDS": "1200",
                "DATASET_AUTO_COLLECTION_SOURCES": "huggingface",
                "DATASET_AUTO_COLLECTION_LIMIT": "10000",
            }
        )

        beat_schedule = celery_module.celery_app.conf.beat_schedule
        huggingface = beat_schedule["dataset-auto-collect-huggingface"]

        self.assertIsNone(huggingface["kwargs"]["limit"])
        self.assertEqual(huggingface["kwargs"]["max_runtime_seconds"], 1200)


if __name__ == "__main__":
    unittest.main()

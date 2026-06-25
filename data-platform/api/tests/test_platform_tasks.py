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

        def apply_async(self, *args, **kwargs):
            return types.SimpleNamespace(id="fake-task-id")

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

from app.tasks import platform_tasks  # noqa: E402


class DatasetTaskDefaultsTests(unittest.TestCase):
    def test_collect_dataset_metadata_keeps_manual_defaults_when_omitted(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DATASET_AUTO_COLLECTION_LIMIT": "42",
                "DATASET_AUTO_COLLECTION_SAFE": "true",
            },
            clear=False,
        ), patch.object(
            platform_tasks,
            "_run_module",
            return_value={"status": "ok"},
        ) as run_module_mock:
            result = platform_tasks.collect_dataset_metadata.run(source="huggingface")

        self.assertEqual(result, {"status": "ok"})
        self.assertEqual(
            run_module_mock.call_args.kwargs["args"],
            ["--source", "huggingface"],
        )

    def test_collect_dataset_metadata_respects_manual_overrides(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DATASET_AUTO_COLLECTION_LIMIT": "42",
                "DATASET_AUTO_COLLECTION_SAFE": "true",
            },
            clear=False,
        ), patch.object(
            platform_tasks,
            "_run_module",
            return_value={"status": "ok"},
        ) as run_module_mock:
            result = platform_tasks.collect_dataset_metadata.run(
                source="figshare",
                limit=7,
                from_scratch=True,
                safe=False,
            )

        self.assertEqual(result, {"status": "ok"})
        self.assertEqual(
            run_module_mock.call_args.kwargs["args"],
            [
                "--source",
                "figshare",
                "--limit",
                "7",
                "--from-scratch",
                "--no-safe",
            ],
        )

    def test_collect_dataset_metadata_passes_parser_version_into_subprocess_env(self) -> None:
        with patch.object(
            platform_tasks,
            "_run_module",
            return_value={"status": "ok"},
        ) as run_module_mock:
            result = platform_tasks.collect_dataset_metadata.run(
                source="zenodo",
                parser_version="v9.9.9",
            )

        self.assertEqual(result, {"status": "ok"})
        self.assertEqual(
            run_module_mock.call_args.kwargs["extra_env"],
            {"PARSER_VERSION": "v9.9.9"},
        )

    def test_collect_dataset_metadata_forwards_reconcile_flag(self) -> None:
        with patch.object(
            platform_tasks,
            "_run_module",
            return_value={"status": "ok"},
        ) as run_module_mock:
            result = platform_tasks.collect_dataset_metadata.run(
                source="public_data_portal",
                from_scratch=True,
                reconcile_missing=True,
            )

        self.assertEqual(result, {"status": "ok"})
        self.assertEqual(
            run_module_mock.call_args.kwargs["args"],
            [
                "--source",
                "public_data_portal",
                "--from-scratch",
                "--reconcile-missing",
            ],
        )

    def test_collect_dataset_metadata_forwards_excluded_sources(self) -> None:
        with patch.object(
            platform_tasks,
            "_run_module",
            return_value={"status": "ok"},
        ) as run_module_mock:
            result = platform_tasks.collect_dataset_metadata.run(
                source="all",
                exclude_sources=["kaggle", "aihub"],
            )

        self.assertEqual(result, {"status": "ok"})
        self.assertEqual(
            run_module_mock.call_args.kwargs["args"],
            [
                "--source",
                "all",
                "--exclude-source",
                "kaggle",
                "--exclude-source",
                "aihub",
            ],
        )

    def test_collect_dataset_metadata_forwards_max_runtime_seconds(self) -> None:
        with patch.object(
            platform_tasks,
            "_run_module",
            return_value={"status": "ok"},
        ) as run_module_mock:
            result = platform_tasks.collect_dataset_metadata.run(
                source="data_europa",
                safe=True,
                max_runtime_seconds=1200,
            )

        self.assertEqual(result, {"status": "ok"})
        self.assertEqual(
            run_module_mock.call_args.kwargs["args"],
            [
                "--source",
                "data_europa",
                "--safe",
                "--max-runtime-seconds",
                "1200",
            ],
        )

if __name__ == "__main__":
    unittest.main()

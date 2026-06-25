import sys
import tempfile
import unittest
from asyncio import create_task, sleep
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch


ADAPTER_ROOT = Path(__file__).resolve().parents[1]
if str(ADAPTER_ROOT) not in sys.path:
    sys.path.insert(0, str(ADAPTER_ROOT))


class CodexRunnerTest(unittest.IsolatedAsyncioTestCase):
    def test_adapter_settings_read_shared_codex_env_aliases(self) -> None:
        from app.config import AdapterSettings

        with patch.dict(
            os.environ,
            {
                "CODEX_MODEL": "gpt-5.4",
                "CODEX_TIMEOUT_SECONDS": "12",
                "CODEX_MAX_CONCURRENCY": "2",
                "CODEX_MAX_QUEUE": "9",
            },
            clear=False,
        ):
            settings = AdapterSettings(_env_file=None)

        self.assertEqual(settings.model, "gpt-5.4")
        self.assertEqual(settings.timeout_seconds, 12.0)
        self.assertEqual(settings.max_concurrency, 2)
        self.assertEqual(settings.max_queue, 9)

    async def test_runner_reports_missing_auth_file(self) -> None:
        from app.config import AdapterSettings
        from app.runner import CodexRunner, CodexRunnerError

        with tempfile.TemporaryDirectory() as temp_dir:
            settings = AdapterSettings(
                codex_command="codex",
                codex_home_path=temp_dir,
                model="gpt-5.4",
                timeout_seconds=5.0,
                max_concurrency=1,
                max_queue=2,
            )
            runner = CodexRunner(settings)

            status = runner.get_status_snapshot()
            self.assertFalse(status["authPresent"])
            self.assertEqual(status["maxConcurrency"], 1)

            with self.assertRaises(CodexRunnerError) as ctx:
                await runner.run_chat_completion(
                    {
                        "model": "gpt-5.4",
                        "messages": [{"role": "user", "content": "hello"}],
                    }
                )

        self.assertIn("auth.json", str(ctx.exception))

    async def test_runner_rejects_requests_when_queue_is_full(self) -> None:
        from app.config import AdapterSettings
        from app.runner import CodexRunner, CodexRunnerError

        with tempfile.TemporaryDirectory() as temp_dir:
            auth_path = Path(temp_dir) / "auth.json"
            auth_path.write_text("{}", encoding="utf-8")

            settings = AdapterSettings(
                codex_command="codex",
                codex_home_path=temp_dir,
                model="gpt-5.4",
                timeout_seconds=5.0,
                max_concurrency=1,
                max_queue=1,
            )
            runner = CodexRunner(settings)

            async def delayed_completion(payload):
                await sleep(0.1)
                return "ok"

            with patch.object(
                runner,
                "_invoke_codex",
                new=AsyncMock(side_effect=delayed_completion),
            ):
                first_task = create_task(
                    runner.run_chat_completion(
                        {
                            "model": "gpt-5.4",
                            "messages": [{"role": "user", "content": "first"}],
                        }
                    )
                )
                await sleep(0.01)

                with self.assertRaises(CodexRunnerError) as ctx:
                    await runner.run_chat_completion(
                        {
                            "model": "gpt-5.4",
                            "messages": [{"role": "user", "content": "second"}],
                        }
                    )

                result = await first_task

        self.assertEqual(result["content"], "ok")
        self.assertIn("queue overflow", str(ctx.exception))

    async def test_runner_surfaces_non_zero_subprocess_exit(self) -> None:
        from app.config import AdapterSettings
        from app.runner import CodexRunner, CodexRunnerError

        class _FakeProcess:
            returncode = 17

            async def communicate(self, *_args, **_kwargs):
                return b"", b"boom"

        with tempfile.TemporaryDirectory() as temp_dir:
            auth_path = Path(temp_dir) / "auth.json"
            auth_path.write_text("{}", encoding="utf-8")

            settings = AdapterSettings(
                codex_command="codex",
                codex_home_path=temp_dir,
                model="gpt-5.4",
                timeout_seconds=5.0,
                max_concurrency=1,
                max_queue=2,
            )
            runner = CodexRunner(settings)

            with patch(
                "app.runner.asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=_FakeProcess()),
            ):
                with self.assertRaises(CodexRunnerError) as ctx:
                    await runner.run_chat_completion(
                        {
                            "model": "gpt-5.4",
                            "messages": [{"role": "user", "content": "hello"}],
                        }
                    )

        self.assertIn("exit code 17", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

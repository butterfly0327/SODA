from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime


PROJECT_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if PROJECT_SRC not in sys.path:
    sys.path.insert(0, PROJECT_SRC)

from metadata_ingest import utils


class TimezoneUtilsTests(unittest.TestCase):
    def test_parse_datetime_converts_aware_values_to_kst(self) -> None:
        parsed = utils.parse_datetime("2026-03-24T00:00:00+00:00")

        self.assertEqual(parsed, "2026-03-24T09:00:00+09:00")

    def test_parse_datetime_assumes_utc_for_naive_values_then_converts_to_kst(self) -> None:
        parsed = utils.parse_datetime("2026-03-24T00:00:00")

        self.assertEqual(parsed, "2026-03-24T09:00:00+09:00")

    def test_parse_datetime_handles_datetime_instances(self) -> None:
        parsed = utils.parse_datetime(datetime.fromisoformat("2026-03-24T15:30:00+00:00"))

        self.assertEqual(parsed, "2026-03-25T00:30:00+09:00")

    def test_utcnow_iso_now_returns_kst_offset(self) -> None:
        rendered = utils.utcnow_iso()

        self.assertTrue(rendered.endswith("+09:00"))


if __name__ == "__main__":
    unittest.main()

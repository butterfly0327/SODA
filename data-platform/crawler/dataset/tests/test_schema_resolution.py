import sys
import types
import unittest


def _install_psycopg_stub() -> None:
    psycopg = types.ModuleType("psycopg")
    psycopg.sql = types.SimpleNamespace()
    sys.modules.setdefault("psycopg", psycopg)

    rows = types.ModuleType("psycopg.rows")
    rows.dict_row = object()
    sys.modules.setdefault("psycopg.rows", rows)

    types_json = types.ModuleType("psycopg.types.json")
    types_json.Jsonb = object
    sys.modules.setdefault("psycopg.types.json", types_json)

    types_pkg = types.ModuleType("psycopg.types")
    sys.modules.setdefault("psycopg.types", types_pkg)


_install_psycopg_stub()

from metadata_ingest.db import Database


class _FakeCursor:
    def __init__(self) -> None:
        self.query = ""

    def execute(self, query, params) -> None:
        self.query = str(query)

    def fetchone(self):
        if "current_schemas(true)" in self.query:
            return {"table_name": "dataset_sources"}
        return None


class _FakeCursorContext:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def __enter__(self) -> _FakeCursor:
        return self._cursor

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class SchemaResolutionTests(unittest.TestCase):
    def test_resolve_existing_table_uses_current_schemas(self) -> None:
        db = Database("postgresql://example")
        cursor = _FakeCursor()
        db._cursor = lambda: _FakeCursorContext(cursor)  # type: ignore[method-assign]

        resolved = db._resolve_existing_table("dataset_sources", "dataset_source")

        self.assertEqual("dataset_sources", resolved)


if __name__ == "__main__":
    unittest.main()

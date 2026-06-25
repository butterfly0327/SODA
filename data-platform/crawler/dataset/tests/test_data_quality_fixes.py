from __future__ import annotations

import importlib
import os
import sys
import unittest
from types import SimpleNamespace

PROJECT_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if PROJECT_SRC not in sys.path:
    sys.path.insert(0, PROJECT_SRC)

AwsOdrCollector = importlib.import_module(
    "metadata_ingest.sources.aws_odr"
).AwsOdrCollector
AIHubCollector = importlib.import_module("metadata_ingest.sources.aihub").AIHubCollector
DataEuropaCollector = importlib.import_module(
    "metadata_ingest.sources.data_europa"
).DataEuropaCollector
DataGovCollector = importlib.import_module(
    "metadata_ingest.sources.data_gov"
).DataGovCollector
Database = importlib.import_module("metadata_ingest.db").Database
KaggleCollector = importlib.import_module(
    "metadata_ingest.sources.kaggle"
).KaggleCollector
HuggingFaceCollector = importlib.import_module(
    "metadata_ingest.sources.huggingface"
).HuggingFaceCollector
NormalizedDatasetRecord = importlib.import_module(
    "metadata_ingest.models"
).NormalizedDatasetRecord
PublicDataPortalCollector = importlib.import_module(
    "metadata_ingest.sources.public_data_portal"
).PublicDataPortalCollector
BaseDatasetCollector = importlib.import_module(
    "metadata_ingest.base"
).BaseDatasetCollector
SourceDefinition = importlib.import_module("metadata_ingest.models").SourceDefinition
infer_commercial_use_from_license = importlib.import_module(
    "metadata_ingest.utils"
).infer_commercial_use_from_license
is_bad_description_for_ingest = importlib.import_module(
    "metadata_ingest.utils"
).is_bad_description_for_ingest
is_bad_title_for_ingest = importlib.import_module(
    "metadata_ingest.utils"
).is_bad_title_for_ingest


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
        kaggle_username=None,
        kaggle_key=None,
        kaggle_config_dir=None,
        data_gov_api_key="dummy",
        huggingface_token=None,
        github_token=None,
        public_data_portal_list_url_template="https://example.com?page={page}",
    )


class DataEuropaUrlFixTests(unittest.TestCase):
    def test_landing_url_does_not_fall_back_to_uuid_id(self) -> None:
        collector = DataEuropaCollector(db=SimpleNamespace(), settings=_make_settings())
        try:
            source_key = "fe4cedf3-3df0-4656-b537-d0617cd87faa"
            search_item = {
                "id": source_key,
                "title": "Europa Dataset",
            }
            detail_payload = {
                "@id": f"http://data.europa.eu/88u/dataset/{source_key}",
                "@type": "Dataset",
                "title": "Europa Dataset",
                "description": "desc",
            }

            record = collector._normalize(
                search_item=search_item,
                detail_payload=detail_payload,
                source_key=source_key,
            )

            self.assertTrue(
                record.canonical_url.startswith("http://data.europa.eu/88u/dataset/")
            )
            self.assertEqual(record.canonical_url, record.landing_url)
        finally:
            collector.close()


class DataGovSchemaFixTests(unittest.TestCase):
    def test_schema_excludes_bureau_and_program_codes(self) -> None:
        collector = DataGovCollector(db=SimpleNamespace(), settings=_make_settings())
        try:
            raw = {
                "id": "dataset-1",
                "name": "dataset-1",
                "title": "Dataset 1",
                "notes": "desc",
                "resources": [],
                "extras": [
                    {"key": "describedBy", "value": "https://example.com/schema"},
                    {
                        "key": "describedByType",
                        "value": "application/json",
                    },
                    {"key": "bureauCode", "value": "028:00"},
                    {"key": "programCode", "value": "028:000"},
                ],
            }

            record = collector._normalize(raw)

            self.assertEqual(record.schema_json, {})
            self.assertEqual(record.metrics_json, {})
            extras = record.extra_json.get("extras") if record.extra_json else {}
            self.assertNotIn("describedBy", extras)
            self.assertNotIn("describedByType", extras)
            self.assertNotIn("bureauCode", extras)
            self.assertNotIn("programCode", extras)
        finally:
            collector.close()

    def test_distribution_node_fallback_populates_dataset_size(self) -> None:
        collector = DataEuropaCollector(db=SimpleNamespace(), settings=_make_settings())
        try:
            source_key = "123e4567-e89b-12d3-a456-426614174000"
            search_item = {"id": source_key, "title": "Dataset"}
            detail_payload = {
                "@graph": [
                    {
                        "@id": "http://example.com/dataset/1",
                        "@type": "dcat:Dataset",
                        "dct:title": "Dataset",
                    },
                    {
                        "@id": "http://example.com/dist/1",
                        "@type": "dcat:Distribution",
                        "dcat:byteSize": "2 MB",
                        "dcat:accessURL": "https://example.com/file.csv",
                    },
                ]
            }

            record = collector._normalize(
                search_item=search_item,
                detail_payload=detail_payload,
                source_key=source_key,
            )

            self.assertEqual(record.dataset_size_bytes, 2_000_000)
            self.assertEqual(len(record.resources_json), 1)
            self.assertEqual(record.metrics_json, {})
        finally:
            collector.close()

    def test_multilingual_title_description_are_extracted(self) -> None:
        collector = DataEuropaCollector(db=SimpleNamespace(), settings=_make_settings())
        try:
            source_key = "fe4cedf3-3df0-4656-b537-d0617cd87faa"
            search_item = {
                "id": source_key,
                "title": {"uk": "Українська назва", "en": "English title"},
                "description": {
                    "uk": "Перший опис. Другий опис.",
                    "en": "First description. Second description.",
                },
            }

            record = collector._normalize(
                search_item=search_item,
                detail_payload=None,
                source_key=source_key,
            )

            self.assertEqual(record.title, "English title")
            self.assertEqual(
                record.description_short, "First description. Second description."
            )
            self.assertEqual(
                record.description_long, "First description. Second description."
            )
        finally:
            collector.close()


class DatabaseGuardFixTests(unittest.TestCase):
    def test_payload_normalizes_invalid_urls_and_presence_tracks_missing(self) -> None:
        db = Database("postgresql://unused")
        source_key = "fe4cedf3-3df0-4656-b537-d0617cd87faa"
        record = NormalizedDatasetRecord(
            source_dataset_key=source_key,
            canonical_url=source_key,
            landing_url=source_key,
            title=source_key,
            description_short="test",
        )

        payload = db._record_to_db_payload(source_id=1, run_id=1, record=record)

        self.assertIsNone(payload["canonical_url"])
        self.assertIsNone(payload["landing_url"])
        self.assertIsNone(payload["title"])
        self.assertIn("canonical_url", record.field_presence_json["has"])
        self.assertFalse(record.field_presence_json["has"]["canonical_url"])

    def test_payload_derives_short_from_long_and_localized_title(self) -> None:
        db = Database("postgresql://unused")
        record = NormalizedDatasetRecord(
            source_dataset_key="localized-1",
            title={"uk": "Локалізований заголовок", "en": "Localized Title"},
            description_short=None,
            description_long="First sentence. Second sentence.",
        )

        payload = db._record_to_db_payload(source_id=1, run_id=1, record=record)

        self.assertEqual(payload["title"], "Localized Title")
        self.assertEqual(payload["description_short"], "First sentence.")
        self.assertEqual(
            payload["description_long"], "First sentence. Second sentence."
        )

    def test_payload_keeps_descriptions_none_when_missing(self) -> None:
        db = Database("postgresql://unused")
        record = NormalizedDatasetRecord(
            source_dataset_key="fallback-title-1",
            title="Only title exists",
            description_short=None,
            description_long=None,
        )

        payload = db._record_to_db_payload(source_id=1, run_id=1, record=record)

        self.assertIsNone(payload["description_long"])
        self.assertIsNone(payload["description_short"])

    def test_payload_prunes_empty_schema_json_to_empty_object(self) -> None:
        db = Database("postgresql://unused")
        record = NormalizedDatasetRecord(
            source_dataset_key="schema-empty-1",
            title="Schema Empty",
            description_short="desc",
            schema_json={
                "features": [],
                "splits": None,
                "nested": {"a": "", "b": []},
            },
        )

        payload = db._record_to_db_payload(source_id=1, run_id=1, record=record)
        schema_value = payload["schema_json"]
        self.assertIsNotNone(schema_value)
        self.assertEqual(getattr(schema_value, "obj", None), {})

    def test_payload_drops_non_structural_schema_and_banned_extra_keys(self) -> None:
        db = Database("postgresql://unused")
        record = NormalizedDatasetRecord(
            source_dataset_key="schema-structural-only-1",
            title="Schema",
            description_short="desc",
            schema_json={
                "resource_type": {"type": "dataset"},
                "update_frequency": "Not updated",
                "features": [{"name": "col_a", "dtype": "string"}],
            },
            extra_json={
                "described_by": "https://example.com/schema",
                "program_code": "028:000",
                "nested": {
                    "bureau_code": "028:00",
                    "allowed": "keep",
                },
            },
        )

        payload = db._record_to_db_payload(source_id=1, run_id=1, record=record)
        schema_value = payload["schema_json"]
        extra_value = payload["extra_json"]

        self.assertEqual(
            getattr(schema_value, "obj", None),
            {"features": [{"name": "col_a", "dtype": "string"}]},
        )
        self.assertEqual(
            getattr(extra_value, "obj", None), {"nested": {"allowed": "keep"}}
        )

    def test_payload_filters_promo_nav_noise_from_text_and_terms(self) -> None:
        db = Database("postgresql://unused")
        promo = "📑 Paper | 🌐 Project Page | 💾 Released Resources | 📦 Repo"
        record = NormalizedDatasetRecord(
            source_dataset_key="promo-noise-1",
            title="Useful Dataset",
            description_short=promo,
            description_long="A real dataset description. More context.",
            tasks=[promo, "classification"],
            tags=[promo, "vision"],
        )

        payload = db._record_to_db_payload(source_id=1, run_id=1, record=record)

        self.assertEqual(payload["description_short"], "A real dataset description.")
        self.assertEqual(payload["tasks"], ["classification"])
        self.assertEqual(payload["tags"], ["vision"])
        self.assertNotIn("project page", (payload["search_text"] or "").casefold())

    def test_payload_keeps_only_popularity_metrics(self) -> None:
        db = Database("postgresql://unused")
        record = NormalizedDatasetRecord(
            source_dataset_key="metrics-only-1",
            title="Metrics",
            description_short="desc",
            metrics_json={
                "downloads": 100,
                "likes": 7,
                "views": 250,
                "num_resources": 4,
                "distribution_count": 3,
                "resource_count": 2,
                "versions": 1,
                "performance_excerpt": "text",
            },
        )

        payload = db._record_to_db_payload(source_id=1, run_id=1, record=record)
        metrics_value = payload["metrics_json"]

        self.assertEqual(
            getattr(metrics_value, "obj", None),
            {"downloads": 100, "likes": 7, "views": 250},
        )


class PublicDataPortalSizeFixTests(unittest.TestCase):
    def test_content_size_with_units_parses_to_bytes(self) -> None:
        collector = PublicDataPortalCollector(
            db=SimpleNamespace(), settings=_make_settings()
        )
        try:
            BeautifulSoup = importlib.import_module("bs4").BeautifulSoup
            soup = BeautifulSoup(
                "<html><head><meta property='og:title' content='Sample Dataset'></head><body></body></html>",
                "lxml",
            )
            schema_json = {
                "@type": "Dataset",
                "name": "Sample Dataset",
                "contentSize": "12 MB",
            }

            record = collector._normalize(
                source_key="123",
                detail_url="https://www.data.go.kr/data/123/fileData.do",
                detail_soup=soup,
                schema_json=schema_json,
            )

            self.assertEqual(record.dataset_size_bytes, 12_000_000)
        finally:
            collector.close()

    def test_column_table_is_mapped_into_schema_columns(self) -> None:
        collector = PublicDataPortalCollector(
            db=SimpleNamespace(), settings=_make_settings()
        )
        try:
            BeautifulSoup = importlib.import_module("bs4").BeautifulSoup
            html = """
            <html>
              <head><meta property='og:title' content='Sample Dataset'></head>
              <body>
                <table>
                  <thead>
                    <tr>
                      <th>항목명</th>
                      <th>항목설명</th>
                      <th>데이터타입</th>
                      <th>최대길이</th>
                      <th>단위</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>연번</td>
                      <td>일련번호</td>
                      <td>숫자형(NUMERIC)</td>
                      <td>2</td>
                      <td>해당없음</td>
                    </tr>
                  </tbody>
                </table>
              </body>
            </html>
            """
            soup = BeautifulSoup(html, "lxml")
            schema_json = {
                "@type": "Dataset",
                "name": "Sample Dataset",
            }

            record = collector._normalize(
                source_key="125",
                detail_url="https://www.data.go.kr/data/125/fileData.do",
                detail_soup=soup,
                schema_json=schema_json,
                detail_html=html,
            )

            columns = record.schema_json.get("columns") if record.schema_json else None
            self.assertIsInstance(columns, list)
            self.assertEqual(len(columns or []), 1)
            self.assertEqual((columns or [])[0].get("name"), "연번")
            self.assertEqual((columns or [])[0].get("description"), "일련번호")
            self.assertEqual((columns or [])[0].get("data_type"), "숫자형(NUMERIC)")
            self.assertEqual((columns or [])[0].get("max_length"), "2")
            self.assertEqual((columns or [])[0].get("unit"), "해당없음")
        finally:
            collector.close()

    def test_detail_text_size_pattern_is_used_when_schema_size_missing(self) -> None:
        collector = PublicDataPortalCollector(
            db=SimpleNamespace(), settings=_make_settings()
        )
        try:
            BeautifulSoup = importlib.import_module("bs4").BeautifulSoup
            soup = BeautifulSoup(
                "<html><head><meta property='og:title' content='Sample Dataset'></head><body>데이터 용량: 1.5 GB</body></html>",
                "lxml",
            )
            schema_json = {
                "@type": "Dataset",
                "name": "Sample Dataset",
            }

            record = collector._normalize(
                source_key="124",
                detail_url="https://www.data.go.kr/data/124/fileData.do",
                detail_soup=soup,
                schema_json=schema_json,
            )

            self.assertEqual(record.dataset_size_bytes, 1_500_000_000)
        finally:
            collector.close()


class KaggleSchemaFixTests(unittest.TestCase):
    def test_schema_json_excludes_file_metadata_only_payload(self) -> None:
        collector = KaggleCollector(db=SimpleNamespace(), settings=_make_settings())
        try:
            item = {
                "ref": "owner/dataset",
                "title": "dataset",
            }
            detail = {
                "info": {
                    "title": "Pretty Dataset Title",
                    "description": "Detailed metadata description",
                }
            }
            files = [{"name": "train.csv", "size": "1024"}]

            record = collector._normalize("owner/dataset", item, detail, files=files)

            self.assertEqual(record.schema_json, {})
        finally:
            collector.close()


class AwsOdrLicenseFixTests(unittest.TestCase):
    def test_markdown_license_is_split_to_name_and_url(self) -> None:
        collector = AwsOdrCollector(db=SimpleNamespace(), settings=_make_settings())
        try:
            raw = {
                "Name": "Dataset",
                "Description": "desc",
                "License": "[CC BY](https://creativecommons.org/licenses/by/4.0/)",
                "Resources": [],
            }

            record = collector._normalize(
                raw,
                path="datasets/test.yaml",
                blob_sha="abc",
            )

            self.assertEqual(record.license_name, "CC BY")
            self.assertEqual(
                record.license_url, "https://creativecommons.org/licenses/by/4.0/"
            )
        finally:
            collector.close()

    def test_size_is_extracted_from_description_text(self) -> None:
        collector = AwsOdrCollector(db=SimpleNamespace(), settings=_make_settings())
        try:
            raw = {
                "Name": "Dataset",
                "Description": "This dataset contains 2.5 TB of imagery.",
                "License": "MIT",
                "Resources": [],
            }

            record = collector._normalize(
                raw,
                path="datasets/test3.yaml",
                blob_sha="abc",
            )

            self.assertEqual(record.dataset_size_bytes, 2_500_000_000_000)
        finally:
            collector.close()


class AIHubSizeFixTests(unittest.TestCase):
    def test_build_amount_field_is_parsed_to_dataset_size(self) -> None:
        collector = AIHubCollector(db=SimpleNamespace(), settings=_make_settings())
        try:
            BeautifulSoup = importlib.import_module("bs4").BeautifulSoup
            soup = BeautifulSoup(
                "<html><head><meta property='og:title' content='AIHub Dataset'></head><body>구축량: 12 GB</body></html>",
                "lxml",
            )

            record = collector._normalize(
                source_key="123",
                detail_url="https://www.aihub.or.kr/aihubdata/data/view.do?dataSetSn=123",
                soup=soup,
            )

            self.assertEqual(record.dataset_size_bytes, 12_000_000_000)
        finally:
            collector.close()

    def test_embedded_markdown_link_extracts_license_url(self) -> None:
        collector = AwsOdrCollector(db=SimpleNamespace(), settings=_make_settings())
        try:
            raw = {
                "Name": "Dataset",
                "Description": "desc",
                "License": "Use terms are available [here](http://example.com/license).",
                "Resources": [],
            }

            record = collector._normalize(
                raw,
                path="datasets/test2.yaml",
                blob_sha="abc",
            )

            self.assertEqual(record.license_url, "http://example.com/license")
            self.assertEqual(record.license_name, "Use terms are available here.")
        finally:
            collector.close()


class CommercialInferenceFixTests(unittest.TestCase):
    def test_non_commercial_tokens_and_false_positive_prevention(self) -> None:
        self.assertFalse(infer_commercial_use_from_license("CC-BY-NC-4.0"))
        self.assertTrue(infer_commercial_use_from_license("Apache-2.0"))
        self.assertIsNone(infer_commercial_use_from_license("Concordance License"))


class IngestQualityGateTests(unittest.TestCase):
    def test_title_quality_gate_blocks_placeholder_and_short_values(self) -> None:
        self.assertTrue(is_bad_title_for_ingest("test"))
        self.assertTrue(is_bad_title_for_ingest("111"))
        self.assertTrue(is_bad_title_for_ingest("owner/dataset"))
        self.assertFalse(is_bad_title_for_ingest("한국어 법률 지식베이스"))

    def test_description_quality_gate_blocks_low_information_values(self) -> None:
        self.assertTrue(is_bad_description_for_ingest("{{description}}"))
        self.assertTrue(is_bad_description_for_ingest("https://example.com"))
        self.assertTrue(
            is_bad_description_for_ingest("https://a.example.com https://b.example.com")
        )
        self.assertFalse(
            is_bad_description_for_ingest(
                "한국어 QA 태스크를 위한 문장 단위 라벨링 데이터셋입니다."
            )
        )


class HuggingFaceSubtitleMappingTests(unittest.TestCase):
    def test_owner_slug_is_not_stored_as_subtitle(self) -> None:
        collector = HuggingFaceCollector(
            db=SimpleNamespace(), settings=_make_settings()
        )
        try:
            raw = {
                "id": "owner/dataset-name",
                "description": "desc",
                "cardData": {
                    "pretty_name": "Pretty Dataset Title",
                },
                "tags": [],
                "siblings": [],
            }
            record = collector._normalize(raw)
            self.assertIsNone(record.subtitle)
            self.assertEqual(record.title, "Pretty Dataset Title")
        finally:
            collector.close()


class RunSkipDescriptionTests(unittest.TestCase):
    def test_run_skips_records_without_descriptions_and_continues(self) -> None:
        class _DummyDB:
            def __init__(self) -> None:
                self.conn = object()
                self.upserted_keys = []

            def start_run(self, source, parser_version, resume=True):
                return SimpleNamespace(run_id=1, source_id=1, checkpoint_json={})

            def upsert_dataset(self, source_id, run_id, record):
                self.upserted_keys.append(record.source_dataset_key)

            def update_run_progress(self, *args, **kwargs):
                return None

            def finalize_run(self, *args, **kwargs):
                return None

            def commit(self):
                return None

        class _DummyCollector(BaseDatasetCollector):
            source = SourceDefinition(
                source_code="DUMMY",
                source_name="Dummy",
                base_url="https://example.com",
                collection_type="API",
            )

            def iter_records(self, checkpoint):
                yield (
                    NormalizedDatasetRecord(
                        source_dataset_key="k1",
                        title="valid title 1",
                        description_short=None,
                        description_long=None,
                    ),
                    {"index": 0},
                )
                yield (
                    NormalizedDatasetRecord(
                        source_dataset_key="k2",
                        title="valid title 2",
                        description_short="This dataset contains sufficiently detailed metadata for validation.",
                        description_long=None,
                    ),
                    {"index": 1},
                )

        db = _DummyDB()
        collector = _DummyCollector(db=db, settings=_make_settings())
        try:
            stats = collector.run(resume=False, limit=1)
            self.assertEqual(db.upserted_keys, ["k2"])
            self.assertEqual(stats.upserted_count, 1)
            self.assertEqual(stats.collected_count, 2)
            self.assertEqual(stats.failed_count, 0)
        finally:
            collector.close()

    def test_run_skips_non_public_records_when_title_or_description_is_bad(
        self,
    ) -> None:
        class _DummyDB:
            def __init__(self) -> None:
                self.conn = object()
                self.upserted_keys = []

            def start_run(self, source, parser_version, resume=True):
                return SimpleNamespace(run_id=1, source_id=2, checkpoint_json={})

            def upsert_dataset(self, source_id, run_id, record):
                self.upserted_keys.append(record.source_dataset_key)

            def update_run_progress(self, *args, **kwargs):
                return None

            def finalize_run(self, *args, **kwargs):
                return None

            def commit(self):
                return None

        class _DummyCollector(BaseDatasetCollector):
            source = SourceDefinition(
                source_code="HUGGINGFACE",
                source_name="Dummy",
                base_url="https://example.com",
                collection_type="API",
            )

            def iter_records(self, checkpoint):
                yield (
                    NormalizedDatasetRecord(
                        source_dataset_key="k1",
                        title="test",
                        description_short="valid description text",
                    ),
                    {"index": 0},
                )
                yield (
                    NormalizedDatasetRecord(
                        source_dataset_key="k2",
                        title="정상 제목",
                        description_short="https://example.com",
                    ),
                    {"index": 1},
                )
                yield (
                    NormalizedDatasetRecord(
                        source_dataset_key="k3",
                        title="정상 제목",
                        description_short="이 데이터셋은 한국어 질문 응답 태스크 학습을 위한 라벨 데이터를 제공합니다.",
                    ),
                    {"index": 2},
                )

        db = _DummyDB()
        collector = _DummyCollector(db=db, settings=_make_settings())
        try:
            stats = collector.run(resume=False)
            self.assertEqual(db.upserted_keys, ["k3"])
            self.assertEqual(stats.upserted_count, 1)
            self.assertEqual(stats.collected_count, 3)
            self.assertEqual(stats.failed_count, 0)
        finally:
            collector.close()

    def test_dataset_server_size_fallback_populates_dataset_size(self) -> None:
        collector = HuggingFaceCollector(
            db=SimpleNamespace(), settings=_make_settings()
        )
        try:
            collector.get_json = lambda *args, **kwargs: {
                "size": {"dataset": {"num_bytes_original_files": "2048"}}
            }
            raw = {
                "id": "owner/dataset-size-test",
                "description": "desc",
                "cardData": {},
                "tags": [],
                "siblings": [],
            }
            record = collector._normalize(raw)
            self.assertEqual(record.dataset_size_bytes, 2048)
        finally:
            collector.close()


if __name__ == "__main__":
    unittest.main()

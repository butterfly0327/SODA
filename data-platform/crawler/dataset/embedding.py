from __future__ import annotations

import argparse
import importlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import httpx
import psycopg
from psycopg.rows import dict_row


def _load_dotenv_if_available() -> None:
    try:
        dotenv_module = importlib.import_module("dotenv")
    except ModuleNotFoundError:
        return
    load_dotenv_func = getattr(dotenv_module, "load_dotenv", None)
    if callable(load_dotenv_func):
        env_path = Path(__file__).resolve().with_name(".env")
        load_dotenv_func(dotenv_path=env_path, override=False)


_load_dotenv_if_available()


DEFAULT_EMBED_MODEL = "text-embedding-3-large"
DEFAULT_EMBEDDING_URL = "https://gms.ssafy.io/gmsapi/api.openai.com/v1/embeddings"
DEFAULT_DIMENSIONS = 1536


@dataclass(slots=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "")
    embedding_api_url: str = os.getenv("EMBEDDING_API_URL", DEFAULT_EMBEDDING_URL)
    embedding_model: str = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBED_MODEL)
    embedding_api_key: str = os.getenv("GMS_API_KEY", "")
    embedding_dimensions: int = int(
        os.getenv("EMBEDDING_DIMENSIONS", str(DEFAULT_DIMENSIONS))
    )
    request_timeout_seconds: float = float(
        os.getenv("EMBEDDING_REQUEST_TIMEOUT_SECONDS", "45")
    )
    max_retries: int = int(os.getenv("EMBEDDING_MAX_RETRIES", "3"))
    embedding_max_text_chars: int = int(os.getenv("EMBEDDING_MAX_TEXT_CHARS", "7000"))

    def validate(self) -> None:
        if not self.database_url:
            raise ValueError("DATABASE_URL 환경변수가 비어 있습니다.")
        if not self.embedding_api_key:
            raise ValueError(
                "임베딩 API 키가 없습니다. .env에 GMS_API_KEY 를 설정하세요."
            )
        if not self.embedding_model.strip():
            raise ValueError("EMBEDDING_MODEL 환경변수가 비어 있습니다.")
        if self.embedding_dimensions <= 0:
            raise ValueError("EMBEDDING_DIMENSIONS 는 1 이상의 정수여야 합니다.")
        if self.embedding_dimensions != DEFAULT_DIMENSIONS:
            raise ValueError(
                "dataset_chunks.embedding 이 VECTOR(1536)이므로 EMBEDDING_DIMENSIONS 는 1536 이어야 합니다."
            )
        if self.request_timeout_seconds <= 0:
            raise ValueError("EMBEDDING_REQUEST_TIMEOUT_SECONDS 는 0보다 커야 합니다.")
        if self.max_retries < 0:
            raise ValueError("EMBEDDING_MAX_RETRIES 는 0 이상의 정수여야 합니다.")
        if self.embedding_max_text_chars <= 0:
            raise ValueError("EMBEDDING_MAX_TEXT_CHARS 는 1 이상의 정수여야 합니다.")


def _join_non_empty(parts: Iterable[str | None], sep: str = "\n") -> str | None:
    values = [part.strip() for part in parts if isinstance(part, str) and part.strip()]
    if not values:
        return None
    return sep.join(values)


def _format_list(name: str, values: list[str] | None) -> str | None:
    if not values:
        return None
    cleaned = [
        item.strip() for item in values if isinstance(item, str) and item.strip()
    ]
    if not cleaned:
        return None
    return f"{name}: {', '.join(cleaned)}"


def _json_text(name: str, payload: Any) -> str | None:
    if payload in (None, {}, []):
        return None
    return f"{name}: {json.dumps(payload, ensure_ascii=False)}"


def _format_scalar(name: str, value: Any) -> str | None:
    if value is None:
        return None
    return f"{name}: {value}"


def build_chunks(dataset_row: dict[str, Any]) -> list[dict[str, Any]]:
    dataset_id = int(dataset_row["id"])
    lang_code = None
    languages = dataset_row.get("languages")
    if isinstance(languages, list) and languages:
        first = languages[0]
        if isinstance(first, str) and first.strip():
            lang_code = first.strip()[:10]

    chunks: list[dict[str, Any]] = []

    title_summary_text = _join_non_empty(
        [
            dataset_row.get("title"),
            dataset_row.get("subtitle"),
        ]
    )
    if title_summary_text:
        chunks.append(
            {
                "dataset_id": dataset_id,
                "chunk_type": "TITLE_SUMMARY",
                "chunk_order": 0,
                "chunk_text": title_summary_text,
                "lang_code": lang_code,
            }
        )

    description_text = _join_non_empty([dataset_row.get("description_long")])
    if description_text:
        chunks.append(
            {
                "dataset_id": dataset_id,
                "chunk_type": "DESCRIPTION",
                "chunk_order": 0,
                "chunk_text": description_text,
                "lang_code": lang_code,
            }
        )

    tags_text = _join_non_empty(
        [
            _format_list("domains", dataset_row.get("domains")),
            _format_list("tasks", dataset_row.get("tasks")),
            _format_list("modalities", dataset_row.get("modalities")),
            _format_list("tags", dataset_row.get("tags")),
        ]
    )
    if tags_text:
        chunks.append(
            {
                "dataset_id": dataset_id,
                "chunk_type": "TAGS",
                "chunk_order": 0,
                "chunk_text": tags_text,
                "lang_code": lang_code,
            }
        )

    schema_text = _join_non_empty(
        [
            _json_text("schema_json", dataset_row.get("schema_json")),
            _json_text("metrics_json", dataset_row.get("metrics_json")),
        ]
    )
    if schema_text:
        chunks.append(
            {
                "dataset_id": dataset_id,
                "chunk_type": "SCHEMA",
                "chunk_order": 0,
                "chunk_text": schema_text,
                "lang_code": lang_code,
            }
        )

    access_text = _join_non_empty(
        [
            _format_scalar("publisher", dataset_row.get("publisher_name")),
            _format_scalar("license_name", dataset_row.get("license_name")),
            _format_scalar("access_type", dataset_row.get("access_type")),
            _format_scalar("login_required", dataset_row.get("login_required")),
            _format_scalar("approval_required", dataset_row.get("approval_required")),
            _format_scalar("payment_required", dataset_row.get("payment_required")),
            _format_scalar("is_restricted", dataset_row.get("is_restricted")),
            _format_scalar(
                "commercial_use_allowed", dataset_row.get("commercial_use_allowed")
            ),
        ]
    )
    if access_text:
        chunks.append(
            {
                "dataset_id": dataset_id,
                "chunk_type": "ACCESS",
                "chunk_order": 0,
                "chunk_text": access_text,
                "lang_code": lang_code,
            }
        )

    return chunks


class Embedder:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.Client(timeout=settings.request_timeout_seconds)

    def close(self) -> None:
        self.client.close()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        payload = {
            "model": self.settings.embedding_model,
            "input": texts,
            "dimensions": self.settings.embedding_dimensions,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.embedding_api_key}",
            "Content-Type": "application/json",
        }

        retries = self.settings.max_retries
        for attempt in range(retries + 1):
            response = self.client.post(
                self.settings.embedding_api_url,
                headers=headers,
                json=payload,
            )
            status = response.status_code
            if status < 400:
                body = response.json()
                data = body.get("data")
                if not isinstance(data, list):
                    raise RuntimeError(
                        "임베딩 응답 형식이 올바르지 않습니다: data 필드 누락"
                    )
                vectors: list[list[float]] = []
                for item in data:
                    embedding = (
                        item.get("embedding") if isinstance(item, dict) else None
                    )
                    if not isinstance(embedding, list):
                        raise RuntimeError(
                            "임베딩 응답 형식이 올바르지 않습니다: embedding 필드 누락"
                        )
                    vector = [float(x) for x in embedding]
                    if len(vector) != self.settings.embedding_dimensions:
                        raise RuntimeError(
                            "임베딩 벡터 차원이 설정값과 다릅니다. "
                            f"expected={self.settings.embedding_dimensions} actual={len(vector)}"
                        )
                    vectors.append(vector)
                if len(vectors) != len(texts):
                    raise RuntimeError(
                        "임베딩 응답 개수와 입력 텍스트 개수가 일치하지 않습니다."
                    )
                return vectors

            if status in {408, 409, 425, 429, 500, 502, 503, 504} and attempt < retries:
                sleep_seconds = min(2**attempt, 8)
                time.sleep(sleep_seconds)
                continue

            raise RuntimeError(
                f"임베딩 API 호출 실패(status={status}): {response.text[:500]}"
            )

        raise RuntimeError("임베딩 API 호출 재시도 횟수를 초과했습니다.")


def _to_vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(format(value, ".10f") for value in vector) + "]"


def _clip_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="datasets -> dataset_chunks 임베딩 적재기"
    )
    parser.add_argument(
        "--dataset-id", type=int, default=None, help="특정 dataset.id만 처리"
    )
    parser.add_argument("--limit", type=int, default=100, help="최대 처리 dataset 개수")
    parser.add_argument(
        "--reembed",
        action="store_true",
        help="기존 chunk가 있어도 다시 임베딩하여 upsert",
    )
    return parser


def fetch_datasets(
    conn: psycopg.Connection[Any],
    *,
    dataset_id: int | None,
    limit: int,
    reembed: bool,
) -> list[dict[str, Any]]:
    sql = """
    SELECT
        d.id,
        d.title,
        d.subtitle,
        d.description_short,
        d.description_long,
        d.search_text,
        d.publisher_name,
        d.domains,
        d.tasks,
        d.modalities,
        d.tags,
        d.languages,
        d.license_name,
        d.license_url,
        d.commercial_use_allowed,
        d.access_type,
        d.login_required,
        d.approval_required,
        d.payment_required,
        d.is_restricted,
        d.field_presence_json,
        d.resources_json,
        d.schema_json,
        d.metrics_json
    FROM datasets d
    WHERE (%s::bigint IS NULL OR d.id = %s)
      AND (%s::boolean = TRUE OR NOT EXISTS (
            SELECT 1
            FROM dataset_chunks dc
            WHERE dc.dataset_id = d.id
        ))
    ORDER BY d.id
    LIMIT %s
    """

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, (dataset_id, dataset_id, reembed, limit))
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def upsert_chunks(
    conn: psycopg.Connection[Any],
    *,
    chunks: list[dict[str, Any]],
    vectors: list[list[float]],
    embed_model: str,
    dimensions: int,
) -> int:
    if len(chunks) != len(vectors):
        raise RuntimeError("청크 수와 임베딩 벡터 수가 일치하지 않습니다.")

    sql = """
    INSERT INTO dataset_chunks (
        dataset_id,
        chunk_type,
        chunk_order,
        chunk_text,
        token_count,
        lang_code,
        embed_model,
        embedding
    )
    VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s::vector
    )
    ON CONFLICT (dataset_id, chunk_type, chunk_order)
    DO UPDATE SET
        chunk_text = EXCLUDED.chunk_text,
        token_count = EXCLUDED.token_count,
        lang_code = EXCLUDED.lang_code,
        embed_model = EXCLUDED.embed_model,
        embedding = EXCLUDED.embedding,
        updated_at = NOW()
    """

    embed_model_value = f"{embed_model}:{dimensions}"
    upserted = 0
    with conn.cursor() as cur:
        for chunk, vector in zip(chunks, vectors):
            vector_literal = _to_vector_literal(vector)
            cur.execute(
                sql,
                (
                    chunk["dataset_id"],
                    chunk["chunk_type"],
                    chunk["chunk_order"],
                    chunk["chunk_text"],
                    None,
                    chunk["lang_code"],
                    embed_model_value,
                    vector_literal,
                ),
            )
            upserted += 1
    conn.commit()
    return upserted


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.limit <= 0:
        raise SystemExit("--limit 은 1 이상의 정수여야 합니다.")

    settings = Settings()
    settings.validate()

    total_dataset_count = 0
    total_chunk_count = 0

    with psycopg.connect(settings.database_url) as conn:
        conn.autocommit = False
        datasets = fetch_datasets(
            conn,
            dataset_id=args.dataset_id,
            limit=args.limit,
            reembed=bool(args.reembed),
        )

        embedder = Embedder(settings)
        try:
            for dataset_row in datasets:
                chunks = build_chunks(dataset_row)
                if not chunks:
                    continue

                clipped_chunks = [
                    {
                        **chunk,
                        "chunk_text": _clip_text(
                            chunk["chunk_text"], settings.embedding_max_text_chars
                        ),
                    }
                    for chunk in chunks
                ]

                texts = [chunk["chunk_text"] for chunk in clipped_chunks]
                vectors = embedder.embed_texts(texts)
                total_chunk_count += upsert_chunks(
                    conn,
                    chunks=clipped_chunks,
                    vectors=vectors,
                    embed_model=settings.embedding_model,
                    dimensions=settings.embedding_dimensions,
                )
                total_dataset_count += 1
                print(
                    f"[OK] dataset_id={dataset_row['id']} chunks={len(chunks)} upserted_total={total_chunk_count}"
                )
        finally:
            embedder.close()

    summary = {
        "processed_dataset_count": total_dataset_count,
        "upserted_chunk_count": total_chunk_count,
        "embedding_model": settings.embedding_model,
        "embedding_dimensions": settings.embedding_dimensions,
        "endpoint": settings.embedding_api_url,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""
OpenAPI 임베딩 독립 실행 스크립트

사용법:
    python embed_openapi.py                        # 전체 (미임베딩만)
    python embed_openapi.py --source NAVER_CLOUD_MAPS
    python embed_openapi.py --force                # 이미 임베딩된 것도 재임베딩
    python embed_openapi.py --source ODSAY --force
"""

import argparse
import asyncio
import importlib
import logging
import math
import os
import sys
from typing import Any

import httpx
from dotenv import load_dotenv

asyncpg = importlib.import_module("asyncpg")

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 설정 (환경변수)
# ──────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "").replace(
    "postgresql+asyncpg://", "postgresql://"
)
GMS_API_KEY = os.getenv("GMS_API_KEY", "")
GEMINI_BASE_URL = os.getenv(
    "GEMINI_API_BASE_URL",
    "https://gms.ssafy.io/gmsapi/generativelanguage.googleapis.com/v1beta",
)
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")
EMBED_DIMENSIONS = int(os.getenv("EMBED_DIMENSIONS", "1536"))

# Gemini batchEmbedContents 는 요청당 최대 100개 제한
MAX_CHUNKS_PER_CALL = 100
# DB에서 한 번에 가져올 open_apis 행 수
ROWS_PER_BATCH = int(os.getenv("EMBED_BATCH_SIZE", "100"))

# ──────────────────────────────────────────────
# SQL
# ──────────────────────────────────────────────

_FETCH_SQL = """
    SELECT
        oa.id,
        oa.name,
        oa.description,
        oa.provider,
        oa.category,
        oa.tags,
        oa.auth_type,
        oa.is_free,
        oa.pricing_note
    FROM open_apis oa
    {source_join}
    WHERE oa.is_deleted = FALSE
    {source_filter}
    {skip_embedded}
    ORDER BY oa.id
"""

_UPSERT_CHUNK_SQL = """
    INSERT INTO openapi_chunks
        (openapi_id, chunk_type, chunk_order, chunk_text, embed_model, embedding, lang_code)
    VALUES ($1, $2, $3, $4, $5, $6::vector, $7)
    ON CONFLICT (openapi_id, chunk_type, chunk_order) DO UPDATE SET
        chunk_text  = EXCLUDED.chunk_text,
        embed_model = EXCLUDED.embed_model,
        embedding   = EXCLUDED.embedding,
        updated_at  = NOW()
"""

# ──────────────────────────────────────────────
# 청크 빌더
# ──────────────────────────────────────────────


def _build_chunks(row: Any) -> list[tuple[str, int, str]]:
    chunks: list[tuple[str, int, str]] = []

    # TITLE_SUMMARY
    parts = [row["name"]]
    if row["provider"]:
        parts.append(f"제공자: {row['provider']}")
    if row["description"]:
        parts.append(row["description"])
    chunks.append(("TITLE_SUMMARY", 0, "\n".join(parts)))

    # TAGS
    tag_parts: list[str] = []
    if row["category"]:
        tag_parts.append(f"카테고리: {row['category']}")
    if row["tags"]:
        tag_parts.append("태그: " + ", ".join(row["tags"]))
    if tag_parts:
        chunks.append(("TAGS", 0, "\n".join(tag_parts)))

    # ACCESS
    access_parts = [f"인증방식: {row['auth_type']}"]
    if row["is_free"] is not None:
        access_parts.append("무료" if row["is_free"] else "유료")
    if row["pricing_note"]:
        access_parts.append(row["pricing_note"])
    chunks.append(("ACCESS", 0, " / ".join(access_parts)))

    return chunks


# ──────────────────────────────────────────────
# 벡터 정규화 (1536 등 non-3072 차원 필수)
# ──────────────────────────────────────────────


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


# ──────────────────────────────────────────────
# Gemini 호출 (재시도 포함)
# ──────────────────────────────────────────────


async def _call_gemini_batch(
    client: httpx.AsyncClient, texts: list[str], retries: int = 3
) -> list[list[float]]:
    """최대 100개 텍스트를 batchEmbedContents로 임베딩."""
    url = f"{GEMINI_BASE_URL.rstrip('/')}/models/{EMBED_MODEL}:batchEmbedContents"
    body = {
        "requests": [
            {
                "model": f"models/{EMBED_MODEL}",
                "content": {"parts": [{"text": t}]},
                "taskType": "RETRIEVAL_DOCUMENT",
                "outputDimensionality": EMBED_DIMENSIONS,
            }
            for t in texts
        ]
    }

    for attempt in range(retries):
        try:
            resp = await client.post(
                url,
                params={"key": GMS_API_KEY},
                json=body,
                timeout=120.0,
            )
            resp.raise_for_status()
            vecs = [item["values"] for item in resp.json()["embeddings"]]
            # 3072 외 차원은 정규화 필요
            if EMBED_DIMENSIONS != 3072:
                vecs = [_normalize(v) for v in vecs]
            return vecs
        except httpx.HTTPStatusError as e:
            wait = 2**attempt
            logger.warning(
                "Gemini API %d 오류 (시도 %d/%d), %ds 후 재시도: %s",
                e.response.status_code,
                attempt + 1,
                retries,
                wait,
                e,
            )
            if attempt < retries - 1:
                await asyncio.sleep(wait)
            else:
                raise

    raise RuntimeError("Gemini batch embedding 호출이 반복 실패했습니다.")


# ──────────────────────────────────────────────
# 메인 로직
# ──────────────────────────────────────────────


async def run(source: str | None, force: bool) -> None:
    if not DATABASE_URL:
        logger.error("DATABASE_URL 환경변수가 설정되지 않았습니다.")
        sys.exit(1)
    if not GMS_API_KEY:
        logger.error("GMS_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    try:
        source_join = source_filter = skip_embedded = ""
        params: list[Any] = []

        if source:
            source_join = "JOIN openapi_sources os ON os.id = oa.openapi_source_id"
            params.append(source)
            source_filter = "AND os.source_code = $1"

        if not force:
            skip_embedded = (
                "AND NOT EXISTS ("
                "  SELECT 1 FROM openapi_chunks oc WHERE oc.openapi_id = oa.id"
                ")"
            )

        query = _FETCH_SQL.format(
            source_join=source_join,
            source_filter=source_filter,
            skip_embedded=skip_embedded,
        )
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        total = len(rows)
        logger.info(
            "대상: %d건 (source=%s, force=%s, model=%s, dims=%d)",
            total,
            source,
            force,
            EMBED_MODEL,
            EMBED_DIMENSIONS,
        )

        if total == 0:
            logger.info("임베딩할 레코드가 없습니다.")
            return

        upserted = failed = 0

        async with httpx.AsyncClient() as http_client:
            for i in range(0, total, ROWS_PER_BATCH):
                row_batch = rows[i : i + ROWS_PER_BATCH]

                # 이 행 배치의 모든 청크 수집 (빈 텍스트 제외)
                items: list[tuple[int, str, int, str]] = []
                for row in row_batch:
                    for ctype, corder, ctext in _build_chunks(row):
                        if ctext.strip():
                            items.append((row["id"], ctype, corder, ctext))

                if not items:
                    continue

                # Gemini API는 최대 100개/call → 청크 단위로 분할 호출
                all_vecs: list[list[float]] = []
                call_failed = False
                for j in range(0, len(items), MAX_CHUNKS_PER_CALL):
                    chunk_batch = items[j : j + MAX_CHUNKS_PER_CALL]
                    texts = [item[3] for item in chunk_batch]
                    try:
                        vecs = await _call_gemini_batch(http_client, texts)
                        all_vecs.extend(vecs)
                    except Exception as exc:
                        logger.error(
                            "Gemini 호출 실패 (row %d~%d, chunk %d~%d): %s",
                            i,
                            i + len(row_batch),
                            j,
                            j + len(chunk_batch),
                            exc,
                        )
                        call_failed = True
                        break

                if call_failed:
                    failed += len(row_batch)
                    continue

                # DB upsert
                try:
                    async with pool.acquire() as conn:
                        async with conn.transaction():
                            for (openapi_id, ctype, corder, ctext), vec in zip(
                                items, all_vecs
                            ):
                                vec_str = "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
                                await conn.execute(
                                    _UPSERT_CHUNK_SQL,
                                    openapi_id,
                                    ctype,
                                    corder,
                                    ctext,
                                    EMBED_MODEL,
                                    vec_str,
                                    "ko",
                                )
                    upserted += len(row_batch)
                    logger.info("upserted %d / %d", i + len(row_batch), total)
                except Exception as exc:
                    logger.error(
                        "DB upsert 실패 (row %d~%d): %s",
                        i,
                        i + len(row_batch),
                        exc,
                    )
                    failed += len(row_batch)

        logger.info("=== 완료: %d건 성공, %d건 실패 ===", upserted, failed)

    finally:
        await pool.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="OpenAPI 임베딩 -> openapi_chunks 저장"
    )
    parser.add_argument(
        "--source",
        default=None,
        help="openapi_sources.source_code (예: NAVER_CLOUD_MAPS). 생략 시 전체.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="이미 임베딩된 레코드도 재임베딩",
    )
    args = parser.parse_args()

    asyncio.run(run(source=args.source, force=args.force))

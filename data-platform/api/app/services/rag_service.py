from __future__ import annotations

import asyncio
import importlib
import json
import logging
import math
import re
from dataclasses import dataclass
from typing import Any

import httpx

from ..core.config import GENERIC_QUERY_NOISE_CONTAINS, settings
from ..schemas.rag import RetrievedOpenApi
from .llm_router import llm_router

logger = logging.getLogger(__name__)
asyncpg = importlib.import_module("asyncpg")

_SEARCH_SQL = """
SELECT
    oa.id,
    oa.name,
    oa.description,
    oa.provider,
    oa.base_url,
    oa.docs_url,
    oa.auth_type,
    oa.category,
    oa.tags,
    oa.is_free,
    oc.chunk_type,
    oc.chunk_text,
    1 - (oc.embedding <=> $1::vector) AS similarity
FROM openapi_chunks oc
JOIN open_apis oa ON oa.id = oc.openapi_id
WHERE oa.is_deleted = FALSE
ORDER BY oc.embedding <=> $1::vector ASC
LIMIT $2
"""


_MAX_TOP_N = 20
_OPENAPI_CANDIDATE_TOP_K = 25
_COUNT_EXTRACT_TIMEOUT_SECONDS = 3.0
_OPENAPI_DESC_MAX_CHARS = 1500
_OPENAPI_ITEM_REASON_MAX_CHARS = 150
_OPENAPI_SUMMARY_REASON_MAX_CHARS = 2200
_LLM_CANDIDATE_MIN_SCORE_100 = 40.0
_UNIFIED_SIMILARITY_WEIGHT = 0.60
_UNIFIED_COVERAGE_WEIGHT = 0.12
_UNIFIED_QUALITY_WEIGHT = 0.05
_UNIFIED_LEXICAL_WEIGHT = 0.23
_UNIFIED_AUTH_REQUIRED_PENALTY = 0.035
_UNIFIED_PAID_API_PENALTY = 0.045
_RAG_DB_POOL_MIN_SIZE = 1
_RAG_DB_POOL_MAX_SIZE = 12
_RAG_HTTP_MAX_CONNECTIONS = 100
_RAG_HTTP_MAX_KEEPALIVE_CONNECTIONS = 20
_RAG_HTTP_KEEPALIVE_EXPIRY_SECONDS = 30.0
_OPENAPI_QUERY_EXCLUDE_TERMS = {
    "데이터셋",
    "dataset",
    "datasets",
    "data_set",
}


@dataclass(slots=True)
class OpenApiCandidate:
    id: int
    name: str
    description: str
    provider: str
    base_url: str
    docs_url: str
    auth_type: str
    category: str
    tags: list[str]
    is_free: bool | None
    similarity: float
    internal_score: float
    chunk_text: str


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


class RagService:
    def __init__(self) -> None:
        self._pool: Any | None = None
        limits = httpx.Limits(
            max_connections=_RAG_HTTP_MAX_CONNECTIONS,
            max_keepalive_connections=_RAG_HTTP_MAX_KEEPALIVE_CONNECTIONS,
            keepalive_expiry=_RAG_HTTP_KEEPALIVE_EXPIRY_SECONDS,
        )
        self._embed_http_client = httpx.AsyncClient(
            timeout=settings.recommendation_http_timeout_seconds,
            limits=limits,
        )

    async def _get_pool(self) -> Any:
        if self._pool is None:
            dsn = settings.database_url.replace(
                "postgresql+asyncpg://", "postgresql://"
            )
            self._pool = await asyncpg.create_pool(
                dsn,
                min_size=_RAG_DB_POOL_MIN_SIZE,
                max_size=_RAG_DB_POOL_MAX_SIZE,
            )
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
        await self._embed_http_client.aclose()

    async def _embed_query(self, client: httpx.AsyncClient, text: str) -> list[float]:
        base = settings.gemini_api_base_url.rstrip("/")
        url = f"{base}/models/{settings.embed_model}:embedContent"
        body = {
            "model": f"models/{settings.embed_model}",
            "content": {"parts": [{"text": text}]},
            "taskType": "RETRIEVAL_QUERY",
            "outputDimensionality": settings.embed_dimensions,
        }
        resp = await client.post(
            url,
            params={"key": settings.api_key},
            json=body,
            timeout=30.0,
        )
        resp.raise_for_status()
        vec = resp.json()["embedding"]["values"]
        if settings.embed_dimensions != 3072:
            vec = _normalize(vec)
        return vec

    async def _extract_count_with_llm(self, prompt: str) -> int | None:
        body = {
            "model": settings.recommendation_llm_model,
            "messages": [
                {
                    "role": "developer",
                    "content": (
                        "Extract only the requested recommendation count from the user prompt. "
                        "Return a number only; if no count is mentioned, return null. "
                        f"The maximum allowed count is {_MAX_TOP_N}."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 5,
        }
        try:
            completion = await llm_router.create_chat_completion(
                {
                    **body,
                    "max_completion_tokens": 5,
                }
            )
            content = str(completion.get("content") or "").strip()
            n = int(content)
            if 1 <= n <= _MAX_TOP_N:
                return n
        except Exception:
            pass
        return None

    async def _rank_with_llm(
        self,
        *,
        prompt: str,
        candidates: list[OpenApiCandidate],
        top_n: int,
    ) -> tuple[dict[str, object], str]:
        candidate_cards: list[str] = []
        for candidate in candidates:
            card = (
                f"openApiId={candidate.id}; "
                f"name={self._clip_text(candidate.name)}; "
                f"provider={self._clip_text(candidate.provider or '미상', 80)}; "
                f"category={self._clip_text(candidate.category or '미상', 80)}; "
                f"auth={self._clip_text(candidate.auth_type or '미상', 40)}; "
                f"isFree={candidate.is_free}; "
                f"tags={','.join(candidate.tags[:6]) or '-'}; "
                f"description={self._clip_text(candidate.description)}"
            )
            candidate_cards.append(card)

        body = {
            "model": settings.recommendation_llm_model,
            "messages": [
                {
                    "role": "developer",
                    "content": (
                        "You are an Open API ranking engine. Return exactly one JSON object only. "
                        "Use only openApiId from the candidate list. "
                        "recommendedItems length can be up to requested count. "
                        "If the user did not specify a count, prefer returning 10 items when enough evidence exists. "
                        "rank must be consecutive integers from 1. "
                        "score must be 0..1 with up to 3 decimals. "
                        "Keep scoring consistent: strong semantic/practical fit >=0.85, "
                        "good fit 0.70~0.84, partial fit 0.55~0.69, weak fit <=0.54. "
                        "Each reason must be one Korean sentence <= 150 chars with concrete candidate evidence. "
                        "Do not invent facts. If evidence is weak, briefly include '확인 필요'. "
                        "summaryReason must be concise Korean prose in 2~3 short paragraphs with clear spacing. "
                        "When there are 2 or more key points, use one short heading plus 3 to 5 concise bullet points. "
                        "Keep one blank line between sections for readability. "
                        "Allow at most two short headings and up to five bullet points. "
                        "Do not expose openApiId, internal identifiers, source codes, or identifier-like numeric tokens in any user-facing text. "
                        "Do not use HTML or code block."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"User request:\n{prompt}\n\n"
                        f"Candidates ({len(candidate_cards)}):\n"
                        + "\n".join(f"- {card}" for card in candidate_cards)
                        + "\n\n"
                        + "Return one JSON object with schema:\n"
                        + "{\n"
                        + '  "summaryReason": "overall summary in Korean",\n'
                        + '  "recommendedItems": [\n'
                        + "    {\n"
                        + '      "openApiId": 123,\n'
                        + '      "rank": 1,\n'
                        + '      "score": 0.912,\n'
                        + '      "reason": "reason in Korean"\n'
                        + "    }\n"
                        + "  ]\n"
                        + "}\n"
                        + f"Return up to {top_n} items only. Output JSON only."
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "openapi_recommendation_result",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["summaryReason", "recommendedItems"],
                        "properties": {
                            "summaryReason": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 2200,
                            },
                            "recommendedItems": {
                                "type": "array",
                                "minItems": 0,
                                "maxItems": top_n,
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": [
                                        "openApiId",
                                        "rank",
                                        "score",
                                        "reason",
                                    ],
                                    "properties": {
                                        "openApiId": {"type": "integer"},
                                        "rank": {
                                            "type": "integer",
                                            "minimum": 1,
                                        },
                                        "score": {
                                            "type": "number",
                                            "minimum": 0,
                                            "maximum": 1,
                                        },
                                        "reason": {
                                            "type": "string",
                                            "minLength": 1,
                                            "maxLength": 150,
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
            "max_completion_tokens": 2400,
        }
        if "mini" in settings.recommendation_llm_model.lower():
            body["reasoning_effort"] = "low"
        else:
            body["temperature"] = 0

        try:
            completion = await llm_router.create_chat_completion(body)
        except Exception as exc:
            raise RuntimeError(f"OpenAPI LLM 호출 실패: {exc}") from exc

        content = str(completion.get("content") or "").strip()
        if not content:
            raise RuntimeError("OpenAPI LLM 응답 본문이 비어 있습니다.")

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"OpenAPI LLM JSON 파싱 실패: {exc}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("OpenAPI LLM 응답 JSON은 객체여야 합니다.")

        resolved_model = str(
            completion.get("model") or settings.recommendation_llm_model
        ).strip()
        return payload, (resolved_model or settings.recommendation_llm_model)

    async def query(
        self,
        query_text: str,
        top_k: int | None = None,
        count_hint_text: str | None = None,
    ) -> tuple[str, list[RetrievedOpenApi], str]:
        pool = await self._get_pool()

        vec, extracted_count = await asyncio.gather(
            self._embed_query(self._embed_http_client, query_text),
            self._extract_count_with_llm(count_hint_text or query_text),
        )
        final_top_n = top_k or extracted_count or settings.recommendation_default_top_n
        final_top_n = max(1, min(final_top_n, _MAX_TOP_N))

        candidate_top_k = max(_OPENAPI_CANDIDATE_TOP_K, final_top_n)
        raw_limit = max(candidate_top_k * 8, candidate_top_k)
        vec_str = "[" + ",".join(f"{x:.8f}" for x in vec) + "]"

        async with pool.acquire() as conn:
            rows = await conn.fetch(_SEARCH_SQL, vec_str, raw_limit)

        candidates = self._build_candidates(rows, query_text)
        if not candidates:
            return (
                "관련 Open API를 찾을 수 없습니다.",
                [],
                settings.recommendation_llm_model,
            )

        llm_payload, llm_model = await self._rank_with_llm(
            prompt=query_text,
            candidates=candidates,
            top_n=final_top_n,
        )

        summary_reason, retrieved = self._normalize_llm_result(
            llm_payload=llm_payload,
            candidates=candidates,
            top_n=final_top_n,
        )
        return summary_reason, retrieved, llm_model

    def _build_candidates(self, rows: list[Any], prompt: str) -> list[OpenApiCandidate]:
        grouped: dict[int, dict[str, Any]] = {}
        for row in rows:
            openapi_id = int(row["id"])
            chunk_type = str(row.get("chunk_type") or "")
            chunk_text = str(row.get("chunk_text") or "")
            similarity = max(0.0, min(1.0, float(row.get("similarity") or 0.0)))
            tags_raw = row.get("tags")
            tags = [str(x) for x in tags_raw] if isinstance(tags_raw, list) else []
            current = grouped.get(openapi_id)
            if current is None:
                current = {
                    "id": openapi_id,
                    "name": str(row.get("name") or ""),
                    "description": str(row.get("description") or ""),
                    "provider": str(row.get("provider") or ""),
                    "base_url": str(row.get("base_url") or ""),
                    "docs_url": str(row.get("docs_url") or ""),
                    "auth_type": str(row.get("auth_type") or ""),
                    "category": str(row.get("category") or ""),
                    "tags": tags,
                    "is_free": row.get("is_free"),
                    "max_similarity": similarity,
                    "chunk_types": {chunk_type},
                    "chunk_text": chunk_text,
                    "description_chunk_text": chunk_text
                    if chunk_type == "DESCRIPTION"
                    else "",
                }
                grouped[openapi_id] = current
            else:
                chunk_types = current.get("chunk_types")
                if isinstance(chunk_types, set):
                    chunk_types.add(chunk_type)
                current_max_similarity = float(current.get("max_similarity") or 0.0)
                if similarity > current_max_similarity:
                    current["max_similarity"] = similarity
                    current["chunk_text"] = chunk_text
                if chunk_type == "DESCRIPTION" and not str(
                    current.get("description_chunk_text") or ""
                ):
                    current["description_chunk_text"] = chunk_text

        prompt_terms = self._extract_openapi_query_terms(prompt)
        candidates: list[OpenApiCandidate] = []
        for item in grouped.values():
            chunk_types = item.get("chunk_types")
            chunk_type_count = len(chunk_types) if isinstance(chunk_types, set) else 0
            coverage = min(1.0, chunk_type_count / 6.0)
            tags_field = item.get("tags")
            tags_value: list[Any] = []
            if isinstance(tags_field, list):
                tags_value = list(tags_field)
            safe_tags = [str(x) for x in tags_value]
            quality = (
                sum(
                    [
                        1 if item.get("name") else 0,
                        1 if item.get("description") else 0,
                        1 if item.get("category") else 0,
                        1 if safe_tags else 0,
                    ]
                )
                / 4.0
            )
            text_terms = self._extract_terms(
                " ".join(
                    [
                        str(item.get("name") or ""),
                        str(item.get("description") or ""),
                        " ".join(safe_tags),
                        str(item.get("category") or ""),
                        str(item.get("chunk_text") or ""),
                    ]
                )
            )
            lexical_overlap = 0.0
            if prompt_terms and text_terms:
                lexical_overlap = len(prompt_terms & text_terms) / max(
                    len(prompt_terms),
                    1,
                )

            max_similarity = float(item.get("max_similarity") or 0.0)
            auth_required = self._is_auth_required(str(item.get("auth_type") or ""))
            is_paid_api = item.get("is_free") is False
            penalty = 0.0
            if auth_required:
                penalty += _UNIFIED_AUTH_REQUIRED_PENALTY
            if is_paid_api:
                penalty += _UNIFIED_PAID_API_PENALTY
            internal_score = max(
                0.0,
                min(
                    1.0,
                    _UNIFIED_SIMILARITY_WEIGHT * max_similarity
                    + _UNIFIED_COVERAGE_WEIGHT * coverage
                    + _UNIFIED_QUALITY_WEIGHT * quality
                    + _UNIFIED_LEXICAL_WEIGHT * lexical_overlap
                    - penalty,
                ),
            )

            summary_text = str(item.get("description") or "")
            chunk_text = str(item.get("description_chunk_text") or "") or str(
                item.get("chunk_text") or ""
            )
            is_free_value = item.get("is_free")
            is_free = is_free_value if isinstance(is_free_value, bool) else None
            candidates.append(
                OpenApiCandidate(
                    id=int(item.get("id") or 0),
                    name=str(item.get("name") or ""),
                    description=summary_text,
                    provider=str(item.get("provider") or ""),
                    base_url=str(item.get("base_url") or ""),
                    docs_url=str(item.get("docs_url") or ""),
                    auth_type=str(item.get("auth_type") or ""),
                    category=str(item.get("category") or ""),
                    tags=safe_tags[:8],
                    is_free=is_free,
                    similarity=round(max_similarity, 4),
                    internal_score=round(internal_score, 4),
                    chunk_text=chunk_text,
                )
            )

        candidates.sort(
            key=lambda item: (item.internal_score, item.similarity, -item.id),
            reverse=True,
        )
        filtered_candidates = [
            item
            for item in candidates
            if self._to_score_100(item.internal_score) >= _LLM_CANDIDATE_MIN_SCORE_100
        ]
        return filtered_candidates[:_OPENAPI_CANDIDATE_TOP_K]

    def _normalize_llm_result(
        self,
        *,
        llm_payload: dict[str, object],
        candidates: list[OpenApiCandidate],
        top_n: int,
    ) -> tuple[str, list[RetrievedOpenApi]]:
        summary_reason = str(
            llm_payload.get("summaryReason")
            or "요청 의도 기반으로 Open API를 추천했습니다."
        ).strip()
        summary_reason = self._sanitize_identifier_like_tokens(summary_reason)
        summary_reason = self._clip_display_text(
            summary_reason,
            _OPENAPI_SUMMARY_REASON_MAX_CHARS,
        )
        raw_items = llm_payload.get("recommendedItems")
        if not isinstance(raw_items, list):
            raise RuntimeError("OpenAPI LLM 응답에 recommendedItems 배열이 없습니다.")

        candidate_map = {candidate.id: candidate for candidate in candidates}
        seen: set[int] = set()
        selected: list[RetrievedOpenApi] = []
        for index, raw_item in enumerate(raw_items, start=1):
            if not isinstance(raw_item, dict):
                continue
            openapi_id = self._to_int(raw_item.get("openApiId"))
            if openapi_id is None:
                continue
            if openapi_id in seen:
                continue
            candidate = candidate_map.get(openapi_id)
            if candidate is None:
                continue
            seen.add(openapi_id)

            score = self._to_float(raw_item.get("score"), default=0.0)
            if score > 1.0:
                score = score / 100.0
            score = round(max(0.0, min(1.0, score)), 4)

            selected.append(
                RetrievedOpenApi(
                    id=candidate.id,
                    name=candidate.name,
                    description=candidate.description,
                    provider=candidate.provider or None,
                    base_url=candidate.base_url,
                    docs_url=candidate.docs_url or None,
                    auth_type=candidate.auth_type,
                    category=candidate.category or None,
                    tags=candidate.tags,
                    is_free=candidate.is_free,
                    score=score,
                )
            )
            if len(selected) >= top_n:
                break

        if not selected:
            selected = [
                RetrievedOpenApi(
                    id=item.id,
                    name=item.name,
                    description=item.description,
                    provider=item.provider or None,
                    base_url=item.base_url,
                    docs_url=item.docs_url or None,
                    auth_type=item.auth_type,
                    category=item.category or None,
                    tags=item.tags,
                    is_free=item.is_free,
                    score=round(item.internal_score, 4),
                )
                for item in candidates[:top_n]
            ]

        return summary_reason, selected

    @staticmethod
    def _clip_text(value: str, max_chars: int = _OPENAPI_DESC_MAX_CHARS) -> str:
        text = value.strip().replace("\n", " ")
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3] + "..."

    @staticmethod
    def _clip_display_text(value: str, max_chars: int) -> str:
        text = value.strip().replace("\r\n", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(lines).strip()
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3].rstrip() + "..."

    @staticmethod
    def _sanitize_identifier_like_tokens(text: str) -> str:
        sanitized = re.sub(
            r"(?i)(?:^|[^0-9A-Za-z가-힣])(?:dataset|openapi)[_\s-]*id\s*[:=]?\s*\d+(?:\s*\(\s*\d{4}\s*[~-]\s*\d{4}\s*\))?(?=$|[^0-9A-Za-z가-힣])",
            "",
            text,
        )
        sanitized = re.sub(
            r"(?i)(?:^|[^0-9A-Za-z])(?:src|source|source_code)\s*[:=]\s*[^;,\n]+",
            "",
            sanitized,
        )
        sanitized = re.sub(r"\(\s*\)", "", sanitized)
        sanitized = re.sub(r"[ \t]{2,}", " ", sanitized)
        sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)
        return sanitized.strip(" -;,:\n")

    @staticmethod
    def _extract_terms(text: str) -> set[str]:
        normalized = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", text.lower())
        return {token for token in normalized.split() if len(token) >= 2}

    @staticmethod
    def _extract_openapi_query_terms(text: str) -> set[str]:
        tokens = RagService._extract_terms(text)
        filtered = {
            token
            for token in tokens
            if token not in _OPENAPI_QUERY_EXCLUDE_TERMS
            and not any(noise in token for noise in GENERIC_QUERY_NOISE_CONTAINS)
        }
        return filtered or tokens

    @staticmethod
    def _is_auth_required(auth_type: str) -> bool:
        normalized = auth_type.strip().lower()
        if not normalized:
            return False
        no_auth_markers = (
            "none",
            "noauth",
            "public",
            "anonymous",
            "없음",
            "미필요",
            "불필요",
            "free",
        )
        return not any(marker in normalized for marker in no_auth_markers)

    def _is_allowed_score(self, raw_score: float) -> bool:
        if not settings.recommendation_score_threshold_enabled:
            return True
        return self._to_score_100(raw_score) > settings.recommendation_min_score_100

    @staticmethod
    def _to_score_100(raw_score: float) -> float:
        if raw_score <= 1.0:
            normalized = max(0.0, min(raw_score, 1.0)) * 100.0
            return round(normalized, 3)
        normalized = max(0.0, min(raw_score, 100.0))
        return round(normalized, 3)

    @staticmethod
    def _to_int(value: object) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            try:
                return int(text)
            except ValueError:
                return None
        return None

    @staticmethod
    def _to_float(value: object, *, default: float) -> float:
        if isinstance(value, bool):
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return default
            try:
                return float(text)
            except ValueError:
                return default
        return default


rag_service = RagService()

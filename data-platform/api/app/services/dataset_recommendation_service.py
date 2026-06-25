from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx
import psycopg
from psycopg.rows import dict_row

from ..core.config import GENERIC_QUERY_NOISE_CONTAINS, settings
from .llm_router import llm_router
from .psycopg_connection_pool import get_recommendation_connection_pool


_MAX_TOP_N = 20
_COUNT_EXTRACT_TIMEOUT_SECONDS = 3.0
_RANK_EMPTY_RETRY_MIN_TOKENS = 1600
_RANK_EMPTY_RETRY_BONUS_TOKENS = 300
_CONTEXT_HISTORY_MAX_ITEMS = 10
_CONTEXT_HISTORY_ITEM_MAX_CHARS = 160
_DATASET_CARD_DESC_LONG_MAX_CHARS = 1500
_DATASET_ITEM_REASON_MAX_CHARS = 150
_DATASET_SUMMARY_REASON_MAX_CHARS = 2200
_LLM_CANDIDATE_MIN_SCORE_100 = 40.0
_UNIFIED_SIMILARITY_WEIGHT = 0.60
_UNIFIED_COVERAGE_WEIGHT = 0.12
_UNIFIED_QUALITY_WEIGHT = 0.05
_UNIFIED_LEXICAL_WEIGHT = 0.23
_UNIFIED_RESTRICTED_PENALTY = 0.035
_UNIFIED_APPROVAL_PENALTY = 0.02
_UNIFIED_PAYMENT_PENALTY = 0.035
_DATASET_LLM_CANDIDATE_MAX = 25
_EMBED_HTTP_MAX_CONNECTIONS = 100
_EMBED_HTTP_MAX_KEEPALIVE_CONNECTIONS = 20
_EMBED_HTTP_KEEPALIVE_EXPIRY_SECONDS = 30.0
_DATASET_QUERY_EXCLUDE_TERMS = {
    "openapi",
    "open_api",
    "api",
    "apis",
    "오픈api",
    "오픈_api",
    "오픈",
}
_ACTIVE_CHUNK_TYPES = {
    "TITLE_SUMMARY",
    "DESCRIPTION",
    "TAGS",
    "SCHEMA",
    "ACCESS",
}


class RecommendationInputError(ValueError):
    pass


class RecommendationNoCandidateError(RuntimeError):
    pass


class RecommendationUpstreamError(RuntimeError):
    pass


@dataclass(slots=True)
class Candidate:
    dataset_id: int
    source_code: str
    title: str
    description_short: str
    description_long: str
    chunk_text: str
    similarity: float
    pre_score: float
    coverage: float
    quality: float
    penalty: float
    access_type: str
    is_restricted: bool
    approval_required: bool
    payment_required: bool
    domains: list[str]
    tasks: list[str]
    languages: list[str]
    summary_text: str


@dataclass(slots=True)
class RecommendedItem:
    dataset_id: int
    rank: int
    suitability_score: float
    reason: str


@dataclass(slots=True)
class RecommendationResult:
    recommendation_id: int
    user_turn_id: int
    prompt: str
    summary_reason: str
    candidate_count: int
    llm_model: str
    recommended_items: list[RecommendedItem]


@dataclass(slots=True)
class RankLlmResponse:
    content_text: str
    finish_reason: str | None
    refusal: str | None
    completion_tokens: int | None
    reasoning_tokens: int | None
    llm_model: str


class DatasetRecommendationService:
    def __init__(self) -> None:
        limits = httpx.Limits(
            max_connections=_EMBED_HTTP_MAX_CONNECTIONS,
            max_keepalive_connections=_EMBED_HTTP_MAX_KEEPALIVE_CONNECTIONS,
            keepalive_expiry=_EMBED_HTTP_KEEPALIVE_EXPIRY_SECONDS,
        )
        self._embedding_http_client = httpx.Client(
            timeout=settings.recommendation_http_timeout_seconds,
            limits=limits,
        )

    def close(self) -> None:
        self._embedding_http_client.close()

    def generate_recommendation(
        self,
        *,
        user_turn_id: int | None,
        debug_user_turn_id: int | None,
        dataset_recommendation_id: int | None,
        prompt: str,
        top_n: int | None,
        history: list[dict[str, str]] | None = None,
    ) -> RecommendationResult:
        resolved_user_turn_id = self._resolve_user_turn_id(
            user_turn_id=user_turn_id,
            debug_user_turn_id=debug_user_turn_id,
        )
        prompt_text = prompt.strip()
        if not prompt_text:
            raise RecommendationInputError("prompt는 비어 있을 수 없습니다.")

        final_top_n = self._resolve_top_n(prompt=prompt_text, top_n=top_n)
        contextual_prompt = self._build_contextual_prompt(prompt_text, history)

        with get_recommendation_connection_pool().connection() as conn:
            conn.autocommit = False
            recommendation_id = self._insert_running_recommendation(
                conn=conn,
                user_turn_id=resolved_user_turn_id,
                recommendation_id=dataset_recommendation_id,
            )

            try:
                query_embedding = self._embed_query(contextual_prompt)
                top50_candidates = self._retrieve_top_candidates(
                    conn=conn,
                    query_embedding=query_embedding,
                    top_k=settings.recommendation_vector_top_k,
                )
                llm_candidates = self._prune_candidates(
                    candidates=top50_candidates,
                    top_n=final_top_n,
                    prompt=contextual_prompt,
                )
                if not llm_candidates:
                    raise RecommendationNoCandidateError(
                        "추천 가능한 데이터셋 후보를 찾지 못했습니다."
                    )

                llm_response = self._rank_with_llm(
                    prompt=contextual_prompt,
                    candidates=llm_candidates,
                    top_n=final_top_n,
                )
                recommended_items, summary_reason = self._normalize_llm_result(
                    llm_payload=llm_response["payload"],
                    candidates=llm_candidates,
                    top_n=final_top_n,
                )

                self._mark_success(
                    conn=conn,
                    recommendation_id=recommendation_id,
                    llm_model=llm_response["llm_model"],
                    summary_reason=summary_reason,
                    recommended_items=recommended_items,
                )
                conn.commit()

                return RecommendationResult(
                    recommendation_id=recommendation_id,
                    user_turn_id=resolved_user_turn_id,
                    prompt=prompt_text,
                    summary_reason=summary_reason,
                    candidate_count=len(llm_candidates),
                    llm_model=llm_response["llm_model"],
                    recommended_items=recommended_items,
                )
            except Exception as exc:
                self._mark_failed(
                    conn=conn,
                    recommendation_id=recommendation_id,
                    error_summary=str(exc),
                )
                conn.commit()
                raise

    def _resolve_top_n(self, *, prompt: str, top_n: int | None) -> int:
        if top_n is not None:
            return max(1, min(top_n, _MAX_TOP_N))

        extracted_top_n = self._extract_count_with_llm(prompt)
        if extracted_top_n is not None:
            return extracted_top_n

        return max(1, min(settings.recommendation_default_top_n, _MAX_TOP_N))

    def _build_contextual_prompt(
        self,
        prompt: str,
        history: list[dict[str, str]] | None,
    ) -> str:
        if not history:
            return prompt

        lines: list[str] = []
        for item in history[-_CONTEXT_HISTORY_MAX_ITEMS:]:
            role = str(item.get("role", "")).strip().upper()
            content = str(item.get("content", "")).strip()
            if not role or not content:
                continue

            if role.startswith("USER"):
                role_label = "USER"
            elif role.startswith("ASSISTANT"):
                role_label = "ASSISTANT"
            else:
                role_label = role

            clipped = self._clip_text(content, _CONTEXT_HISTORY_ITEM_MAX_CHARS)
            lines.append(f"- {role_label}: {clipped}")

        if not lines:
            return prompt

        return f"{prompt}\n\nConversation context (recent):\n" + "\n".join(lines)

    def _extract_count_with_llm(self, prompt: str) -> int | None:
        payload: dict[str, Any] = {
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
            "max_completion_tokens": 8,
        }
        if "mini" in settings.recommendation_llm_model.lower():
            payload["reasoning_effort"] = "low"
        else:
            payload["temperature"] = 0

        try:
            completion = llm_router.create_chat_completion_sync(payload)
            content_text = str(completion.get("content") or "").strip()
            if not content_text:
                return None
            value = self._to_int(content_text)
            if value is None:
                return None
            return max(1, min(value, _MAX_TOP_N))
        except Exception:
            return None

    def _resolve_user_turn_id(
        self,
        *,
        user_turn_id: int | None,
        debug_user_turn_id: int | None,
    ) -> int:
        resolved = (
            user_turn_id
            or debug_user_turn_id
            or settings.recommendation_test_user_turn_id
        )
        if resolved is None:
            raise RecommendationInputError(
                "userTurnId가 필요합니다. Spring 미구현 테스트 시 debugUserTurnId를 전달하세요."
            )
        return resolved

    def _insert_running_recommendation(
        self,
        *,
        conn: psycopg.Connection[Any],
        user_turn_id: int,
        recommendation_id: int | None,
    ) -> int:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT 1 FROM conversation_turns WHERE id = %s",
                (user_turn_id,),
            )
            exists = cur.fetchone()
            if exists is None:
                raise RecommendationInputError(
                    f"conversation_turns(id={user_turn_id})를 찾을 수 없습니다."
                )

            if recommendation_id is not None:
                cur.execute(
                    """
                    SELECT id
                    FROM dataset_recommendations
                    WHERE id = %s AND user_turn_id = %s
                    """,
                    (recommendation_id, user_turn_id),
                )
                existing = cur.fetchone()
                if existing is None:
                    raise RecommendationInputError(
                        f"dataset_recommendations(id={recommendation_id})를 찾을 수 없습니다."
                    )

                cur.execute(
                    """
                    UPDATE dataset_recommendations
                    SET
                        status = 'RUNNING',
                        error_summary = NULL,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (recommendation_id,),
                )
                return recommendation_id

            cur.execute(
                """
                INSERT INTO dataset_recommendations (
                    user_turn_id,
                    llm_model,
                    status,
                    reason_text,
                    recommended_items_json,
                    error_summary
                )
                VALUES (%s, %s, 'RUNNING', NULL, '[]'::jsonb, NULL)
                RETURNING id
                """,
                (user_turn_id, settings.recommendation_llm_model),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError(
                    "dataset_recommendations RUNNING 레코드 생성에 실패했습니다."
                )
            return int(row["id"])

    def _mark_success(
        self,
        *,
        conn: psycopg.Connection[Any],
        recommendation_id: int,
        llm_model: str,
        summary_reason: str,
        recommended_items: list[RecommendedItem],
    ) -> None:
        compact_items = [
            {
                "datasetId": item.dataset_id,
                "rank": item.rank,
                "suitabilityScore": item.suitability_score,
                "reason": item.reason,
            }
            for item in recommended_items
        ]
        normalized_summary = self._normalize_reason_markdown(summary_reason)
        reason_text = normalized_summary

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE dataset_recommendations
                SET
                    reason_text = %s,
                    recommended_items_json = %s::jsonb,
                    llm_model = %s,
                    status = 'SUCCESS',
                    error_summary = NULL,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (reason_text, json.dumps(compact_items), llm_model, recommendation_id),
            )

    def _mark_failed(
        self,
        *,
        conn: psycopg.Connection[Any],
        recommendation_id: int,
        error_summary: str,
    ) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE dataset_recommendations
                SET
                    status = 'FAILED',
                    error_summary = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (error_summary, recommendation_id),
            )

    def _embed_query(self, prompt: str) -> list[float]:
        payload = {
            "model": settings.recommendation_embedding_model,
            "input": prompt,
            "dimensions": settings.recommendation_embedding_dimensions,
        }
        headers = {
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = self._embedding_http_client.post(
                settings.recommendation_embedding_url,
                headers=headers,
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise RecommendationUpstreamError(f"임베딩 API 타임아웃: {exc}") from exc
        except httpx.RequestError as exc:
            raise RecommendationUpstreamError(f"임베딩 API 요청 실패: {exc}") from exc
        if response.status_code >= 400:
            raise RecommendationUpstreamError(
                f"임베딩 API 호출 실패(status={response.status_code}): {response.text[:300]}"
            )
        body = response.json()
        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, list) or not data:
            raise RecommendationUpstreamError("임베딩 응답에 data가 없습니다.")
        first = data[0]
        embedding = first.get("embedding") if isinstance(first, dict) else None
        if not isinstance(embedding, list):
            raise RecommendationUpstreamError("임베딩 응답에 embedding이 없습니다.")
        vector = [float(value) for value in embedding]
        if len(vector) != settings.recommendation_embedding_dimensions:
            raise RecommendationUpstreamError(
                "임베딩 차원 불일치: "
                f"expected={settings.recommendation_embedding_dimensions} actual={len(vector)}"
            )
        return vector

    def _retrieve_top_candidates(
        self,
        *,
        conn: psycopg.Connection[Any],
        query_embedding: list[float],
        top_k: int,
    ) -> list[Candidate]:
        vector_literal = self._to_vector_literal(query_embedding)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    dc.dataset_id,
                    dc.chunk_type,
                    dc.chunk_text,
                    (1 - (dc.embedding <=> %s::vector)) AS similarity,
                    ds.source_code,
                    d.title,
                    d.description_short,
                    d.description_long,
                    d.access_type,
                    COALESCE(d.is_restricted, false) AS is_restricted,
                    COALESCE(d.approval_required, false) AS approval_required,
                    COALESCE(d.payment_required, false) AS payment_required,
                    d.domains,
                    d.tasks,
                    d.languages
                FROM dataset_chunks dc
                JOIN datasets d ON d.id = dc.dataset_id
                JOIN dataset_sources ds ON ds.id = d.dataset_source_id
                WHERE dc.embedding IS NOT NULL
                  AND d.status = 'ACTIVE'
                ORDER BY dc.embedding <=> %s::vector ASC
                LIMIT %s
                """,
                (vector_literal, vector_literal, top_k),
            )
            rows = cur.fetchall()

        grouped: dict[int, dict[str, Any]] = {}
        for row in rows:
            dataset_id = int(row["dataset_id"])
            similarity = max(0.0, min(1.0, float(row["similarity"] or 0.0)))
            current = grouped.get(dataset_id)
            if current is None:
                current = {
                    "dataset_id": dataset_id,
                    "source_code": str(row["source_code"] or "UNKNOWN"),
                    "title": str(row["title"] or "(제목 없음)"),
                    "description_short": str(row["description_short"] or ""),
                    "description_long": str(row["description_long"] or ""),
                    "chunk_text": str(row["chunk_text"] or ""),
                    "max_similarity": similarity,
                    "chunk_types": {str(row["chunk_type"] or "")},
                    "access_type": str(row["access_type"] or "UNKNOWN"),
                    "is_restricted": bool(row["is_restricted"]),
                    "approval_required": bool(row["approval_required"]),
                    "payment_required": bool(row["payment_required"]),
                    "domains": [str(x) for x in (row["domains"] or [])],
                    "tasks": [str(x) for x in (row["tasks"] or [])],
                    "languages": [str(x) for x in (row["languages"] or [])],
                    "description_chunk_text": "",
                }
                grouped[dataset_id] = current
                if str(row["chunk_type"] or "") == "DESCRIPTION":
                    current["description_chunk_text"] = str(row["chunk_text"] or "")
            else:
                current["chunk_types"].add(str(row["chunk_type"] or ""))
                if similarity > float(current["max_similarity"]):
                    current["max_similarity"] = similarity
                    current["chunk_text"] = str(row["chunk_text"] or "")
                if str(row["chunk_type"] or "") == "DESCRIPTION" and not str(
                    current["description_chunk_text"] or ""
                ):
                    current["description_chunk_text"] = str(row["chunk_text"] or "")

        candidates: list[Candidate] = []
        for item in grouped.values():
            active_chunk_count = len(
                {
                    chunk_type
                    for chunk_type in item["chunk_types"]
                    if chunk_type in _ACTIVE_CHUNK_TYPES
                }
            )
            coverage = min(1.0, active_chunk_count / len(_ACTIVE_CHUNK_TYPES))
            quality_count = sum(
                [
                    1 if item["title"] else 0,
                    1 if item["description_long"] else 0,
                    1 if item["domains"] else 0,
                    1 if item["tasks"] else 0,
                ]
            )
            quality = quality_count / 4.0
            restriction_penalty = 0.0
            if item["is_restricted"]:
                restriction_penalty += _UNIFIED_RESTRICTED_PENALTY
            if item["approval_required"]:
                restriction_penalty += _UNIFIED_APPROVAL_PENALTY
            if item["payment_required"]:
                restriction_penalty += _UNIFIED_PAYMENT_PENALTY

            pre_score = max(
                0.0,
                min(
                    1.0,
                    _UNIFIED_SIMILARITY_WEIGHT * float(item["max_similarity"])
                    + _UNIFIED_COVERAGE_WEIGHT * coverage
                    + _UNIFIED_QUALITY_WEIGHT * quality
                    - restriction_penalty,
                ),
            )

            candidates.append(
                Candidate(
                    dataset_id=int(item["dataset_id"]),
                    source_code=str(item["source_code"]),
                    title=str(item["title"]),
                    description_short=str(item["description_short"]),
                    description_long=str(item["description_long"]),
                    chunk_text=str(item["chunk_text"]),
                    similarity=round(float(item["max_similarity"]), 4),
                    pre_score=round(pre_score, 4),
                    coverage=round(coverage, 4),
                    quality=round(quality, 4),
                    penalty=round(restriction_penalty, 4),
                    access_type=str(item["access_type"]),
                    is_restricted=bool(item["is_restricted"]),
                    approval_required=bool(item["approval_required"]),
                    payment_required=bool(item["payment_required"]),
                    domains=[str(x) for x in item["domains"][:3]],
                    tasks=[str(x) for x in item["tasks"][:3]],
                    languages=[str(x) for x in item["languages"][:2]],
                    summary_text=(
                        str(item["description_long"] or "")
                        or str(item["description_chunk_text"] or "")
                        or str(item["chunk_text"] or "")
                    ),
                )
            )

        candidates.sort(
            key=lambda item: (
                item.pre_score,
                item.similarity,
                -item.dataset_id,
            ),
            reverse=True,
        )
        return candidates

    def _prune_candidates(
        self,
        *,
        candidates: list[Candidate],
        top_n: int,
        prompt: str,
    ) -> list[Candidate]:
        if not candidates:
            return []

        query_terms = self._extract_dataset_query_terms(prompt)
        scored_candidates = sorted(
            [
                (
                    item,
                    self._internal_similarity_score(item=item, query_terms=query_terms),
                )
                for item in candidates
            ],
            key=lambda pair: pair[1],
            reverse=True,
        )
        filtered_candidates = [
            item
            for item, score in scored_candidates
            if self._score_to_100(score) >= _LLM_CANDIDATE_MIN_SCORE_100
        ]
        candidate_limit = min(
            len(filtered_candidates),
            settings.recommendation_vector_top_k,
            _DATASET_LLM_CANDIDATE_MAX,
        )
        return filtered_candidates[:candidate_limit]

    def _rank_with_llm(
        self,
        *,
        prompt: str,
        candidates: list[Candidate],
        top_n: int,
    ) -> dict[str, Any]:
        candidate_cards = []
        for candidate in candidates:
            card = (
                f"datasetId={candidate.dataset_id}; "
                f"title={self._clip_text(candidate.title, 80)}; "
                f"descLong={self._clip_text(candidate.description_long, _DATASET_CARD_DESC_LONG_MAX_CHARS)}; "
                f"domains={','.join(candidate.domains) or '-'}; "
                f"tasks={','.join(candidate.tasks) or '-'}; "
                f"langs={','.join(candidate.languages) or '-'}; "
                f"access={candidate.access_type}; "
                f"restricted={candidate.is_restricted}; "
                f"approval={candidate.approval_required}; "
                f"payment={candidate.payment_required}; "
                f"summary={self._clip_text(candidate.summary_text, settings.recommendation_card_max_chars)}"
            )
            candidate_cards.append(card)

        system_prompt = (
            "You are a dataset ranking engine. Return exactly one JSON object. "
            "No extra text outside JSON. "
            "Use only datasetId values from the candidate list. "
            "recommendedItems length can be up to the requested count. "
            "Default to exactly 10 items when enough evidence exists and the user did not request a specific count. "
            "rank must be consecutive integers starting at 1. "
            "suitabilityScore must be 0..1 with up to 3 decimals. "
            "Keep scoring consistent: strong semantic match with concrete evidence >=0.85, "
            "good practical fit 0.70~0.84, partial fit 0.55~0.69, weak fit <=0.54. "
            "summaryReason must be concise Korean prose with natural chat tone and clear spacing. "
            "When there are 2 or more key points, use one short heading and 3 to 5 concise bullets, plus optional short closing paragraph. "
            "Keep one blank line between sections for readability. "
            "Allow at most two short headings and up to five bullet points. "
            "Do not use code fences, HTML tags, or markdown tables. "
            "Do not expose datasetId, source codes, internal identifiers, or identifier-like numeric tokens in any user-facing text. "
            "Each item reason must be one Korean sentence <= 150 chars, include user benefit and concrete candidate-card evidence. "
            "Do not invent facts. If evidence is weak, include '확인 필요' briefly in reason. "
            "Avoid generic praise words like '최고', '완벽', '무조건'. "
            "Exclude low-confidence items under score threshold and do not fill placeholders. "
            "Prioritize user-intent relevance, then access constraints, then pre/sim scores."
        )
        user_prompt = (
            f"User request:\n{prompt}\n\n"
            f"Candidates ({len(candidate_cards)}):\n"
            + "\n".join(f"- {card}" for card in candidate_cards)
            + "\n\n"
            + "Return one JSON object matching this schema:\n"
            + "{\n"
            + '  "summaryReason": "overall summary in Korean",\n'
            + '  "recommendedItems": [\n'
            + "    {\n"
            + '      "datasetId": 123,\n'
            + '      "rank": 1,\n'
            + '      "suitabilityScore": 0.912,\n'
            + '      "reason": "reason in Korean"\n'
            + "    }\n"
            + "  ]\n"
            + "}\n"
            + f"Return up to {top_n} items only. "
            + "summaryReason should be detailed enough for final explanation merge. "
            + "Output JSON only."
        )

        schema = {
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
                            "datasetId",
                            "rank",
                            "suitabilityScore",
                            "reason",
                        ],
                        "properties": {
                            "datasetId": {"type": "integer"},
                            "rank": {"type": "integer", "minimum": 1},
                            "suitabilityScore": {
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
        }

        payload: dict[str, Any] = {
            "model": settings.recommendation_llm_model,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "dataset_recommendation_result",
                    "strict": True,
                    "schema": schema,
                },
            },
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if "mini" in settings.recommendation_llm_model.lower():
            payload["reasoning_effort"] = "low"
        else:
            payload["temperature"] = 0
        first_response = self._request_rank_with_llm(
            payload=payload,
            max_completion_tokens=settings.recommendation_llm_max_tokens,
        )

        resolved_response = first_response
        if self._is_empty_response_with_length_stop(first_response):
            retry_tokens = max(
                settings.recommendation_llm_max_tokens + _RANK_EMPTY_RETRY_BONUS_TOKENS,
                _RANK_EMPTY_RETRY_MIN_TOKENS,
            )
            resolved_response = self._request_rank_with_llm(
                payload=payload,
                max_completion_tokens=retry_tokens,
            )

        if not resolved_response.content_text.strip():
            raise RecommendationUpstreamError(
                self._build_empty_content_error(resolved_response)
            )

        parsed = self._load_json_object(resolved_response.content_text)
        return {
            "payload": parsed,
            "llm_model": resolved_response.llm_model,
        }

    def _request_rank_with_llm(
        self,
        *,
        payload: dict[str, Any],
        max_completion_tokens: int,
    ) -> RankLlmResponse:
        request_payload = dict(payload)
        request_payload["max_completion_tokens"] = max_completion_tokens

        try:
            completion = llm_router.create_chat_completion_sync(request_payload)
        except Exception as exc:
            raise RecommendationUpstreamError(f"LLM API 요청 실패: {exc}") from exc

        body = completion.get("raw") if isinstance(completion, dict) else None
        if not isinstance(body, dict):
            raise RecommendationUpstreamError("LLM 응답 형식이 유효하지 않습니다.")
        choices = body.get("choices") if isinstance(body, dict) else None
        if not isinstance(choices, list) or not choices:
            raise RecommendationUpstreamError("LLM 응답에 choices가 없습니다.")
        first_choice = choices[0]
        message = (
            first_choice.get("message") if isinstance(first_choice, dict) else None
        )
        content = message.get("content") if isinstance(message, dict) else None
        refusal = message.get("refusal") if isinstance(message, dict) else None
        refusal_text = refusal if isinstance(refusal, str) else None
        content_text = self._extract_content_text(content)

        usage = body.get("usage") if isinstance(body, dict) else None
        completion_tokens = None
        reasoning_tokens = None
        if isinstance(usage, dict):
            completion_raw = usage.get("completion_tokens")
            if isinstance(completion_raw, int):
                completion_tokens = completion_raw
            completion_detail = usage.get("completion_tokens_details")
            if isinstance(completion_detail, dict):
                reasoning_raw = completion_detail.get("reasoning_tokens")
                if isinstance(reasoning_raw, int):
                    reasoning_tokens = reasoning_raw

        finish_reason = (
            first_choice.get("finish_reason")
            if isinstance(first_choice, dict)
            else None
        )
        finish_reason_text = finish_reason if isinstance(finish_reason, str) else None

        return RankLlmResponse(
            content_text=str(completion.get("content") or content_text),
            finish_reason=finish_reason_text,
            refusal=refusal_text,
            completion_tokens=completion_tokens,
            reasoning_tokens=reasoning_tokens,
            llm_model=str(
                completion.get("model") or request_payload.get("model") or ""
            ).strip()
            or settings.recommendation_llm_model,
        )

    @staticmethod
    def _is_empty_response_with_length_stop(result: RankLlmResponse) -> bool:
        return not result.content_text.strip() and result.finish_reason == "length"

    @staticmethod
    def _build_empty_content_error(result: RankLlmResponse) -> str:
        return (
            "LLM 응답이 비어 있습니다. "
            f"finish_reason={result.finish_reason or 'unknown'}, "
            f"completion_tokens={result.completion_tokens if result.completion_tokens is not None else 'unknown'}, "
            f"reasoning_tokens={result.reasoning_tokens if result.reasoning_tokens is not None else 'unknown'}, "
            f"refusal={result.refusal or 'none'}"
        )

    def _normalize_llm_result(
        self,
        *,
        llm_payload: dict[str, Any],
        candidates: list[Candidate],
        top_n: int,
    ) -> tuple[list[RecommendedItem], str]:
        summary_reason = str(
            llm_payload.get("summaryReason") or "요청 의도 기반으로 추천했습니다."
        )
        raw_items = llm_payload.get("recommendedItems")
        if not isinstance(raw_items, list):
            raise RecommendationUpstreamError(
                "LLM 응답에 recommendedItems 배열이 없습니다."
            )

        parsed_items: list[dict[str, object]] = [
            item for item in raw_items if isinstance(item, dict)
        ]

        allowed_dataset_ids = {candidate.dataset_id for candidate in candidates}
        seen: set[int] = set()
        normalized: list[RecommendedItem] = []

        for index, raw_item in enumerate(parsed_items, start=1):
            dataset_id = self._to_int(raw_item.get("datasetId"))
            if dataset_id is None:
                continue
            if dataset_id not in allowed_dataset_ids or dataset_id in seen:
                continue
            seen.add(dataset_id)

            rank = self._to_int(raw_item.get("rank")) or index

            score = self._to_float(raw_item.get("suitabilityScore"), default=0.0)
            if score > 1.0:
                score = score / 100.0
            score = round(max(0.0, min(1.0, score)), 3)

            reason_raw = raw_item.get("reason")
            reason = (
                reason_raw
                if isinstance(reason_raw, str) and reason_raw.strip()
                else "쿼리와의 연관성이 높아 추천합니다."
            )
            reason = self._sanitize_identifier_like_tokens(reason)
            if not reason:
                reason = "쿼리와의 연관성이 높아 추천합니다."
            reason = self._clip_text(reason, _DATASET_ITEM_REASON_MAX_CHARS)

            normalized.append(
                RecommendedItem(
                    dataset_id=dataset_id,
                    rank=rank,
                    suitability_score=score,
                    reason=reason,
                )
            )

        normalized.sort(
            key=lambda item: (
                item.suitability_score,
                -item.dataset_id,
            ),
            reverse=True,
        )

        normalized = normalized[:top_n]

        if settings.recommendation_score_threshold_enabled and normalized:
            threshold_passed = [
                item
                for item in normalized
                if self._score_to_100(item.suitability_score)
                > settings.recommendation_min_score_100
            ]
            if len(threshold_passed) >= top_n:
                normalized = threshold_passed[:top_n]
        normalized.sort(
            key=lambda item: (
                item.suitability_score,
                -item.dataset_id,
            ),
            reverse=True,
        )

        for idx, item in enumerate(normalized, start=1):
            item.rank = idx

        if not normalized:
            summary_reason = "LLM 결과에서 유효한 데이터셋 추천을 찾지 못했습니다."

        summary_reason = self._sanitize_identifier_like_tokens(
            self._normalize_reason_markdown(summary_reason)
        )
        return normalized, self._clip_display_text(
            summary_reason,
            _DATASET_SUMMARY_REASON_MAX_CHARS,
        )

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
    def _score_to_100(score_0_to_1: float) -> float:
        clamped = max(0.0, min(1.0, score_0_to_1))
        return round(clamped * 100.0, 3)

    @staticmethod
    def _to_vector_literal(vector: list[float]) -> str:
        return "[" + ",".join(format(value, ".10f") for value in vector) + "]"

    @staticmethod
    def _clip_text(value: str, max_chars: int) -> str:
        text = value.strip().replace("\n", " ")
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3] + "..."

    @staticmethod
    def _normalize_reason_markdown(text: str) -> str:
        normalized = text.strip().replace("\r\n", "\n")
        normalized = re.sub(r"```[\s\S]*?```", " ", normalized)
        normalized = re.sub(r"~~~[\s\S]*?~~~", " ", normalized)
        normalized = re.sub(r"<\/?[a-zA-Z][^>]*>", " ", normalized)
        normalized = DatasetRecommendationService._normalize_light_markdown(normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        normalized = re.sub(r"[ \t]+", " ", normalized).strip()
        if not normalized:
            return ""

        if re.search(r"(?m)^(?:###\s+|-\s+)", normalized):
            return normalized

        paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]
        if len(paragraphs) >= 2:
            return "\n\n".join(paragraphs)

        sentences = [
            s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", normalized) if s.strip()
        ]
        if len(sentences) <= 2:
            return DatasetRecommendationService._force_break_for_long_text(normalized)
        chunks = [
            " ".join(sentences[i : i + 2]).strip() for i in range(0, len(sentences), 2)
        ]
        return "\n\n".join(chunk for chunk in chunks if chunk)

    @staticmethod
    def _force_break_for_long_text(text: str) -> str:
        if len(text) <= 220:
            return text
        midpoint = len(text) // 2
        split_at = text.rfind(" ", max(midpoint - 60, 0), min(midpoint + 60, len(text)))
        if split_at <= 0:
            return text
        left = text[:split_at].strip()
        right = text[split_at + 1 :].strip()
        if not left or not right:
            return text
        return f"{left}\n\n{right}"

    @staticmethod
    def _normalize_light_markdown(text: str) -> str:
        lines: list[str] = []
        heading_count = 0
        bullet_count = 0

        for raw_line in text.split("\n"):
            line = raw_line.strip()
            if not line:
                lines.append("")
                continue

            line = re.sub(r"^>\s*", "", line)

            heading_match = re.match(r"^#{1,6}\s*(.+)$", line)
            if heading_match:
                heading_text = re.sub(r"\s+", " ", heading_match.group(1)).strip()
                if heading_text:
                    if heading_count < 2:
                        lines.append(f"### {heading_text}")
                        heading_count += 1
                    else:
                        lines.append(heading_text)
                continue

            bullet_match = re.match(r"^(?:[-*+]\s+|\d+\.\s+)(.+)$", line)
            if bullet_match:
                bullet_text = re.sub(r"\s+", " ", bullet_match.group(1)).strip()
                if not bullet_text:
                    continue
                if bullet_count < 5:
                    lines.append(f"- {bullet_text}")
                    bullet_count += 1
                else:
                    lines.append(bullet_text)
                continue

            line = re.sub(r"\s+", " ", line)
            lines.append(line)

        normalized = "\n".join(lines)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        normalized = re.sub(r"[ \t]+", " ", normalized).strip()
        return normalized

    @staticmethod
    def _normalize_inline_reason(text: str) -> str:
        normalized = re.sub(r"[`*_#>|]", "", text)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    @staticmethod
    def _extract_content_text(content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "\n".join(parts)
        raise RecommendationUpstreamError("LLM content 형식을 해석할 수 없습니다.")

    @staticmethod
    def _load_json_object(raw_text: str) -> dict[str, Any]:
        text = raw_text.strip()
        if not text:
            raise RecommendationUpstreamError("LLM 응답이 비어 있습니다.")

        candidate = DatasetRecommendationService._extract_first_json_object(
            DatasetRecommendationService._strip_code_fence(text)
        )
        if candidate is None:
            candidate = DatasetRecommendationService._extract_first_json_object(text)

        if candidate is None:
            raise RecommendationUpstreamError(
                "LLM 응답에서 JSON 객체를 찾지 못했습니다."
            )
        candidate = DatasetRecommendationService._sanitize_json(candidate)
        try:
            loaded = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise RecommendationUpstreamError(f"LLM JSON 파싱 실패: {exc}") from exc
        if not isinstance(loaded, dict):
            raise RecommendationUpstreamError("LLM 응답 JSON은 객체여야 합니다.")
        return loaded

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        lines = text.splitlines()
        if (
            len(lines) >= 2
            and lines[0].strip().startswith("```")
            and lines[-1].strip() == "```"
        ):
            inner = "\n".join(lines[1:-1]).strip()
            if inner.startswith("json\n"):
                return inner[5:].strip()
            return inner
        return text

    @staticmethod
    def _extract_first_json_object(text: str) -> str | None:
        start = -1
        depth = 0
        in_string = False
        escaped = False

        for index, char in enumerate(text):
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
                continue

            if char == "{":
                if depth == 0:
                    start = index
                depth += 1
            elif char == "}" and depth > 0:
                depth -= 1
                if depth == 0 and start != -1:
                    return text[start : index + 1]

        return None

    @staticmethod
    def _sanitize_json(text: str) -> str:
        return text.replace(",}", "}").replace(",]", "]")

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

    @staticmethod
    def _extract_terms(text: str) -> set[str]:
        normalized = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", text.lower())
        tokens = [token for token in normalized.split() if len(token) >= 2]
        return set(tokens)

    @staticmethod
    def _extract_dataset_query_terms(text: str) -> set[str]:
        tokens = DatasetRecommendationService._extract_terms(text)
        filtered = {
            token
            for token in tokens
            if token not in _DATASET_QUERY_EXCLUDE_TERMS
            and not any(noise in token for noise in GENERIC_QUERY_NOISE_CONTAINS)
            and not token.endswith("api")
            and not token.startswith("openapi")
        }
        return filtered or tokens

    def _internal_similarity_score(
        self,
        *,
        item: Candidate,
        query_terms: set[str],
    ) -> float:
        corpus = " ".join(
            [
                item.title,
                item.description_long,
                " ".join(item.domains),
                " ".join(item.tasks),
                item.chunk_text,
            ]
        )
        corpus_terms = self._extract_terms(corpus)

        lexical_overlap = 0.0
        if query_terms and corpus_terms:
            overlap_count = len(query_terms & corpus_terms)
            lexical_overlap = overlap_count / max(len(query_terms), 1)

        score = (
            _UNIFIED_SIMILARITY_WEIGHT * item.similarity
            + _UNIFIED_COVERAGE_WEIGHT * item.coverage
            + _UNIFIED_QUALITY_WEIGHT * item.quality
            + _UNIFIED_LEXICAL_WEIGHT * lexical_overlap
            - item.penalty
        )
        return round(max(0.0, min(1.0, score)), 6)


dataset_recommendation_service = DatasetRecommendationService()

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row

from ..core.config import settings
from ..schemas.rag import RetrievedOpenApi
from .psycopg_connection_pool import get_recommendation_connection_pool
from .rag_service import rag_service


_CONTEXT_HISTORY_MAX_ITEMS = 10
_CONTEXT_HISTORY_ITEM_MAX_CHARS = 160


class OpenApiRecommendationInputError(ValueError):
    pass


class OpenApiRecommendationUpstreamError(RuntimeError):
    pass


@dataclass(slots=True)
class OpenApiRecommendationResult:
    recommendation_id: int
    user_turn_id: int
    prompt: str
    summary_reason: str
    llm_model: str
    recommended_items: list[RetrievedOpenApi]


class OpenApiRecommendationService:
    async def generate_recommendation(
        self,
        *,
        user_turn_id: int | None,
        debug_user_turn_id: int | None,
        openapi_recommendation_id: int | None,
        prompt: str,
        history: list[dict[str, str]] | None = None,
    ) -> OpenApiRecommendationResult:
        resolved_user_turn_id = self._resolve_user_turn_id(
            user_turn_id=user_turn_id,
            debug_user_turn_id=debug_user_turn_id,
        )
        prompt_text = prompt.strip()
        if not prompt_text:
            raise OpenApiRecommendationInputError("prompt는 비어 있을 수 없습니다.")
        contextual_prompt = self._build_contextual_prompt(prompt_text, history)

        with get_recommendation_connection_pool().connection() as conn:
            conn.autocommit = False
            recommendation_id = self._insert_running_recommendation(
                conn=conn,
                user_turn_id=resolved_user_turn_id,
                recommendation_id=openapi_recommendation_id,
            )

            try:
                summary_reason, retrieved, llm_model = await rag_service.query(
                    query_text=contextual_prompt,
                    count_hint_text=prompt_text,
                )
                normalized_summary_reason = self._normalize_reason_markdown(
                    summary_reason
                )

                self._mark_success(
                    conn=conn,
                    recommendation_id=recommendation_id,
                    summary_reason=normalized_summary_reason,
                    llm_model=llm_model,
                    recommended_items=retrieved,
                )
                conn.commit()

                return OpenApiRecommendationResult(
                    recommendation_id=recommendation_id,
                    user_turn_id=resolved_user_turn_id,
                    prompt=prompt_text,
                    summary_reason=normalized_summary_reason,
                    llm_model=llm_model,
                    recommended_items=retrieved,
                )
            except Exception as exc:
                self._mark_failed(
                    conn=conn,
                    recommendation_id=recommendation_id,
                    error_summary=str(exc),
                )
                conn.commit()
                raise

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
            raise OpenApiRecommendationInputError(
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
            if cur.fetchone() is None:
                raise OpenApiRecommendationInputError(
                    f"conversation_turns(id={user_turn_id})를 찾을 수 없습니다."
                )

            if recommendation_id is not None:
                cur.execute(
                    """
                    SELECT id
                    FROM openapi_recommendations
                    WHERE id = %s AND user_turn_id = %s
                    """,
                    (recommendation_id, user_turn_id),
                )
                existing = cur.fetchone()
                if existing is None:
                    raise OpenApiRecommendationInputError(
                        f"openapi_recommendations(id={recommendation_id})를 찾을 수 없습니다."
                    )

                cur.execute(
                    """
                    UPDATE openapi_recommendations
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
                INSERT INTO openapi_recommendations (
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
                    "openapi_recommendations RUNNING 레코드 생성에 실패했습니다."
                )
            return int(row["id"])

    def _mark_success(
        self,
        *,
        conn: psycopg.Connection[Any],
        recommendation_id: int,
        summary_reason: str,
        llm_model: str,
        recommended_items: list[RetrievedOpenApi],
    ) -> None:
        compact_items = [
            {
                "openApiId": item.id,
                "name": item.name,
                "description": item.description,
                "provider": item.provider,
                "baseUrl": item.base_url,
                "docsUrl": item.docs_url,
                "authType": item.auth_type,
                "category": item.category,
                "tags": item.tags,
                "isFree": item.is_free,
                "score": item.score,
            }
            for item in recommended_items
        ]

        reason_text = self._normalize_reason_markdown(summary_reason)

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE openapi_recommendations
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
                UPDATE openapi_recommendations
                SET
                    status = 'FAILED',
                    error_summary = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (error_summary, recommendation_id),
            )

    @staticmethod
    def _cost_label(is_free: bool | None) -> str:
        if is_free is True:
            return "무료"
        if is_free is False:
            return "유료"
        return "미상"

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

    def _build_item_reason(self, item: RetrievedOpenApi) -> str:
        category = item.category or "일반"
        auth = item.auth_type or "인증방식 미상"
        cost = self._cost_label(item.is_free)
        reason = (
            f"{item.name}는 {category} 관련 활용에 적합하며, "
            f"{auth} 인증과 {cost} 조건을 고려해 추천합니다"
        )
        return self._clip_text(reason, 120)

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
        normalized = OpenApiRecommendationService._normalize_light_markdown(normalized)
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
            return OpenApiRecommendationService._force_break_for_long_text(normalized)
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
    def _normalize_inline_text(text: str) -> str:
        normalized = re.sub(r"[`*_#>|]", "", text)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized


openapi_recommendation_service = OpenApiRecommendationService()

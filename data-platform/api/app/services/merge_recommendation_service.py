from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import httpx
import psycopg
from psycopg.rows import dict_row

from ..core.config import settings
from ..schemas.recommendation import ConversationHistoryItem
from .llm_router import llm_router
from .psycopg_connection_pool import get_recommendation_connection_pool


class MergeRecommendationInputError(ValueError):
    pass


class MergeRecommendationUpstreamError(RuntimeError):
    pass


_MERGE_MIN_SENTENCES = 4
_MERGE_TARGET_MAX_SENTENCES = 8
_MERGE_HARD_MAX_SENTENCES = 12
_MERGE_MAX_COMPLETION_TOKENS = 2200
_MERGE_HISTORY_ITEM_MAX_CHARS = 220
_MERGE_HISTORY_MAX_ITEMS = 10
_MERGE_REASON_CONTEXT_MAX_CHARS = 3600
_MERGE_MIN_KOREAN_RATIO = 0.45


@dataclass(slots=True)
class MergeRecommendationResult:
    recommendation_id: int
    user_turn_id: int
    dataset_recommendation_id: int
    openapi_recommendation_id: int
    prompt: str
    merged_reason_text: str
    llm_model: str


class MergeRecommendationService:
    def merge_recommendation_reasons(
        self,
        *,
        user_turn_id: int | None,
        debug_user_turn_id: int | None,
        recommendation_id: int | None,
        prompt: str,
        history: list[ConversationHistoryItem],
        dataset_recommendation_id: int | None,
        openapi_recommendation_id: int | None,
        dataset_reason: str | None,
        openapi_reason: str | None,
    ) -> MergeRecommendationResult:
        resolved_user_turn_id = self._resolve_user_turn_id(
            user_turn_id=user_turn_id,
            debug_user_turn_id=debug_user_turn_id,
        )

        prompt_text = prompt.strip()
        if not prompt_text:
            raise MergeRecommendationInputError("prompt는 비어 있을 수 없습니다.")

        with get_recommendation_connection_pool().connection() as conn:
            conn.autocommit = False

            self._ensure_user_turn_exists(conn=conn, user_turn_id=resolved_user_turn_id)

            resolved_dataset_id, resolved_dataset_reason = self._resolve_dataset_reason(
                conn=conn,
                user_turn_id=resolved_user_turn_id,
                dataset_recommendation_id=dataset_recommendation_id,
                dataset_reason=dataset_reason,
            )
            resolved_openapi_id, resolved_openapi_reason = self._resolve_openapi_reason(
                conn=conn,
                user_turn_id=resolved_user_turn_id,
                openapi_recommendation_id=openapi_recommendation_id,
                openapi_reason=openapi_reason,
            )

            recommendation_id = self._ensure_running_recommendation(
                conn=conn,
                recommendation_id=recommendation_id,
                user_turn_id=resolved_user_turn_id,
                dataset_recommendation_id=resolved_dataset_id,
                openapi_recommendation_id=resolved_openapi_id,
            )

            try:
                merged_reason_text, llm_model = self._merge_with_llm(
                    prompt=prompt_text,
                    history=history,
                    dataset_reason=resolved_dataset_reason,
                    openapi_reason=resolved_openapi_reason,
                )
                self._mark_success(
                    conn=conn,
                    recommendation_id=recommendation_id,
                    merged_reason_text=merged_reason_text,
                    llm_model=llm_model,
                )
                conn.commit()
            except Exception as exc:
                self._mark_failed(
                    conn=conn,
                    recommendation_id=recommendation_id,
                    error_summary=str(exc),
                )
                conn.commit()
                raise

        return MergeRecommendationResult(
            recommendation_id=recommendation_id,
            user_turn_id=resolved_user_turn_id,
            dataset_recommendation_id=resolved_dataset_id,
            openapi_recommendation_id=resolved_openapi_id,
            prompt=prompt_text,
            merged_reason_text=merged_reason_text,
            llm_model=llm_model,
        )

    @staticmethod
    def _resolve_user_turn_id(
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
            raise MergeRecommendationInputError(
                "userTurnId가 필요합니다. Spring 미구현 테스트 시 debugUserTurnId를 전달하세요."
            )
        return resolved

    @staticmethod
    def _ensure_user_turn_exists(
        *,
        conn: psycopg.Connection[Any],
        user_turn_id: int,
    ) -> None:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM conversation_turns WHERE id = %s", (user_turn_id,)
            )
            if cur.fetchone() is None:
                raise MergeRecommendationInputError(
                    f"conversation_turns(id={user_turn_id})를 찾을 수 없습니다."
                )

    @staticmethod
    def _resolve_dataset_reason(
        *,
        conn: psycopg.Connection[Any],
        user_turn_id: int,
        dataset_recommendation_id: int | None,
        dataset_reason: str | None,
    ) -> tuple[int, str]:
        with conn.cursor(row_factory=dict_row) as cur:
            if dataset_recommendation_id is not None:
                cur.execute(
                    """
                    SELECT id, reason_text
                    FROM dataset_recommendations
                    WHERE id = %s AND user_turn_id = %s
                    """,
                    (dataset_recommendation_id, user_turn_id),
                )
            else:
                cur.execute(
                    """
                    SELECT id, reason_text
                    FROM dataset_recommendations
                    WHERE user_turn_id = %s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (user_turn_id,),
                )
            row = cur.fetchone()

        if row is None:
            raise MergeRecommendationInputError(
                "dataset_recommendations 레코드를 찾을 수 없습니다."
            )

        resolved_reason = (row["reason_text"] or dataset_reason or "").strip()
        if not resolved_reason:
            raise MergeRecommendationInputError("데이터셋 추천 이유가 비어 있습니다.")

        return int(row["id"]), resolved_reason

    @staticmethod
    def _resolve_openapi_reason(
        *,
        conn: psycopg.Connection[Any],
        user_turn_id: int,
        openapi_recommendation_id: int | None,
        openapi_reason: str | None,
    ) -> tuple[int, str]:
        with conn.cursor(row_factory=dict_row) as cur:
            if openapi_recommendation_id is not None:
                cur.execute(
                    """
                    SELECT id, reason_text
                    FROM openapi_recommendations
                    WHERE id = %s AND user_turn_id = %s
                    """,
                    (openapi_recommendation_id, user_turn_id),
                )
            else:
                cur.execute(
                    """
                    SELECT id, reason_text
                    FROM openapi_recommendations
                    WHERE user_turn_id = %s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (user_turn_id,),
                )
            row = cur.fetchone()

        if row is None:
            raise MergeRecommendationInputError(
                "openapi_recommendations 레코드를 찾을 수 없습니다."
            )

        resolved_reason = (row["reason_text"] or openapi_reason or "").strip()
        if not resolved_reason:
            raise MergeRecommendationInputError("Open API 추천 이유가 비어 있습니다.")

        return int(row["id"]), resolved_reason

    @staticmethod
    def _ensure_running_recommendation(
        *,
        conn: psycopg.Connection[Any],
        recommendation_id: int | None,
        user_turn_id: int,
        dataset_recommendation_id: int,
        openapi_recommendation_id: int,
    ) -> int:
        with conn.cursor(row_factory=dict_row) as cur:
            if recommendation_id is not None:
                cur.execute(
                    """
                    SELECT id, user_turn_id, dataset_recommendation_id, openapi_recommendation_id
                    FROM recommendations
                    WHERE id = %s
                    """,
                    (recommendation_id,),
                )
                existing_by_id = cur.fetchone()
                if existing_by_id is None:
                    raise MergeRecommendationInputError(
                        f"recommendations(id={recommendation_id})를 찾을 수 없습니다."
                    )

                if (
                    int(existing_by_id["user_turn_id"]) != user_turn_id
                    or int(existing_by_id["dataset_recommendation_id"])
                    != dataset_recommendation_id
                    or int(existing_by_id["openapi_recommendation_id"])
                    != openapi_recommendation_id
                ):
                    raise MergeRecommendationInputError(
                        "recommendation 레코드와 추천 참조(dataset/openapi/user_turn)가 일치하지 않습니다."
                    )

                cur.execute(
                    """
                    UPDATE recommendations
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
                SELECT id
                FROM recommendations
                WHERE user_turn_id = %s
                  AND dataset_recommendation_id = %s
                  AND openapi_recommendation_id = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_turn_id, dataset_recommendation_id, openapi_recommendation_id),
            )
            existing = cur.fetchone()

            if existing is not None:
                recommendation_id = int(existing["id"])
                cur.execute(
                    """
                    UPDATE recommendations
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
                INSERT INTO recommendations (
                    user_turn_id,
                    assistant_turn_id,
                    dataset_recommendation_id,
                    openapi_recommendation_id,
                    merged_reason_text,
                    llm_model,
                    status,
                    error_summary
                )
                VALUES (%s, NULL, %s, %s, NULL, %s, 'RUNNING', NULL)
                RETURNING id
                """,
                (
                    user_turn_id,
                    dataset_recommendation_id,
                    openapi_recommendation_id,
                    settings.gpt_model,
                ),
            )
            row = cur.fetchone()

        if row is None:
            raise RuntimeError("recommendations RUNNING 레코드 생성에 실패했습니다.")
        return int(row["id"])

    @staticmethod
    def _mark_success(
        *,
        conn: psycopg.Connection[Any],
        recommendation_id: int,
        merged_reason_text: str,
        llm_model: str,
    ) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE recommendations
                SET
                    merged_reason_text = %s,
                    llm_model = %s,
                    status = 'SUCCESS',
                    error_summary = NULL,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (merged_reason_text, llm_model, recommendation_id),
            )

    @staticmethod
    def _mark_failed(
        *,
        conn: psycopg.Connection[Any],
        recommendation_id: int,
        error_summary: str,
    ) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE recommendations
                SET
                    status = 'FAILED',
                    error_summary = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (error_summary, recommendation_id),
            )

    def _merge_with_llm(
        self,
        *,
        prompt: str,
        history: list[ConversationHistoryItem],
        dataset_reason: str,
        openapi_reason: str,
    ) -> tuple[str, str]:
        history_text = self._build_history_text(history)
        dataset_context = self._build_reason_context(dataset_reason)
        openapi_context = self._build_reason_context(openapi_reason)

        first_raw, first_model = self._request_merge_text(
            prompt=prompt,
            history_text=history_text,
            dataset_reason=dataset_context,
            openapi_reason=openapi_context,
        )
        first_result = self._normalize_merged_text(first_raw)
        first_issue = self._validate_merged_text(
            first_result,
            first_raw,
            require_dataset=bool(dataset_context.strip()),
            require_openapi=bool(openapi_context.strip()),
        )
        if first_issue is None:
            return first_result, first_model

        if self._is_hard_failure(first_issue):
            retry_raw, retry_model = self._request_merge_text(
                prompt=prompt,
                history_text=history_text,
                dataset_reason=dataset_context,
                openapi_reason=openapi_context,
                previous_output=first_result,
                failure_reason=first_issue,
            )
            retry_result = self._normalize_merged_text(retry_raw)
            retry_issue = self._validate_merged_text(
                retry_result,
                retry_raw,
                require_dataset=bool(dataset_context.strip()),
                require_openapi=bool(openapi_context.strip()),
            )
            if retry_issue is None:
                return retry_result, retry_model

        fallback_text = self._build_fallback_merge_text(
            prompt=prompt,
            dataset_reason=dataset_context,
            openapi_reason=openapi_context,
        )
        return self._normalize_merged_text(fallback_text), first_model

    def _request_merge_text(
        self,
        *,
        prompt: str,
        history_text: str,
        dataset_reason: str,
        openapi_reason: str,
        previous_output: str | None = None,
        failure_reason: str | None = None,
    ) -> tuple[str, str]:
        if previous_output is None:
            system_prompt = (
                "Write a final user-facing recommendation explanation in Korean. "
                "Use only [USER_REQUEST], [HISTORY], [DATASET_REASON], and [OPENAPI_REASON]. "
                "Do not add new facts. "
                "Write in natural Korean prose like a chat reply. "
                "Output exactly 3 short paragraphs separated by one blank line. "
                "Each paragraph should have 1 to 2 complete sentences. "
                "Every sentence must end with a period. "
                "Use readable structure: prefer one short heading plus 3 to 5 concise bullet points when there are multiple key points. "
                "Allow at most two short headings and up to five bullet points. "
                f"Write {_MERGE_MIN_SENTENCES} to {_MERGE_TARGET_MAX_SENTENCES} complete Korean sentences. "
                "Include overall rationale, dataset-side reasons, openapi-side reasons, "
                "and one caution sentence using '확인 필요' when evidence is weak or conflicting. "
                "Mention both '데이터셋' and 'Open API' in the final explanation."
            )
            user_prompt = (
                f"[USER_REQUEST]\n{prompt}\n\n"
                f"[HISTORY]\n{history_text or 'none'}\n\n"
                f"[DATASET_REASON]\n{dataset_reason}\n\n"
                f"[OPENAPI_REASON]\n{openapi_reason}\n\n"
                "Write the final explanation now."
            )
        else:
            system_prompt = (
                "Fix an invalid Korean recommendation explanation. "
                "Rewrite only with provided sources. Do not add new facts. "
                "Rewrite in natural Korean chat prose with clean paragraph breaks. "
                "Output exactly 3 short paragraphs separated by one blank line. "
                "Every sentence must end with a period. "
                "Allow at most two short headings and up to five bullet points for readability. "
                "Avoid code blocks and HTML. "
                f"Write {_MERGE_MIN_SENTENCES} to {_MERGE_TARGET_MAX_SENTENCES} complete Korean sentences. "
                "Mention both '데이터셋' and 'Open API'."
            )
            user_prompt = (
                f"[USER_REQUEST]\n{prompt}\n\n"
                f"[HISTORY]\n{history_text or 'none'}\n\n"
                f"[DATASET_REASON]\n{dataset_reason}\n\n"
                f"[OPENAPI_REASON]\n{openapi_reason}\n\n"
                f"[PREVIOUS_OUTPUT]\n{previous_output}\n\n"
                f"[FAILURE_REASON]\n{failure_reason or 'invalid format'}\n\n"
                "Rewrite the explanation so it satisfies all constraints."
            )

        payload: dict[str, Any] = {
            "model": settings.gpt_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_completion_tokens": _MERGE_MAX_COMPLETION_TOKENS,
        }
        if "mini" in settings.gpt_model.lower():
            payload["reasoning_effort"] = "low"
        else:
            payload["temperature"] = 0

        try:
            completion = llm_router.create_chat_completion_sync(payload)
        except Exception as exc:
            raise MergeRecommendationUpstreamError(f"LLM API 요청 실패: {exc}") from exc

        body = completion.get("raw") if isinstance(completion, dict) else None
        if not isinstance(body, dict):
            raise MergeRecommendationUpstreamError("LLM 응답 형식이 유효하지 않습니다.")
        choices = body.get("choices") if isinstance(body, dict) else None
        if not isinstance(choices, list) or not choices:
            raise MergeRecommendationUpstreamError("LLM 응답에 choices가 없습니다.")
        first_choice = choices[0]
        message = (
            first_choice.get("message") if isinstance(first_choice, dict) else None
        )
        content = message.get("content") if isinstance(message, dict) else None
        merged = str(
            completion.get("content") or self._extract_content_text(content)
        ).strip()
        if not merged:
            raise MergeRecommendationUpstreamError("LLM 응답 본문이 비어 있습니다.")
        resolved_model = str(
            completion.get("model") or payload.get("model") or ""
        ).strip()
        return merged, (resolved_model or settings.gpt_model)

    @staticmethod
    def _build_history_text(history: list[ConversationHistoryItem]) -> str:
        lines: list[str] = []
        for item in history[-_MERGE_HISTORY_MAX_ITEMS:]:
            content = item.content.strip()
            if not content:
                continue
            content = MergeRecommendationService._clip_text(
                content,
                _MERGE_HISTORY_ITEM_MAX_CHARS,
            )
            lines.append(f"- {item.role}: {content}")
        return "\n".join(lines)

    @staticmethod
    def _build_reason_context(reason_text: str) -> str:
        lines = [
            MergeRecommendationService._sanitize_identifier_tokens(line.strip())
            for line in reason_text.splitlines()
            if line.strip()
        ]
        lines = [line for line in lines if line]
        if not lines:
            return "추천 근거 요약은 내부 식별자 제거 정책에 따라 정리되었습니다."
        limited = lines[:20]
        compact = "\n".join(limited)
        return MergeRecommendationService._clip_text(
            compact,
            _MERGE_REASON_CONTEXT_MAX_CHARS,
        )

    @staticmethod
    def _normalize_merged_text(text: str) -> str:
        normalized = text.strip()
        normalized = MergeRecommendationService._sanitize_identifier_tokens(normalized)
        normalized = normalized.replace("[D]", "").replace("[O]", "")
        normalized = normalized.replace("\r\n", "\n")
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        normalized = MergeRecommendationService._normalize_light_markdown(normalized)
        return MergeRecommendationService._format_chat_paragraphs(normalized)

    @staticmethod
    def _format_chat_paragraphs(text: str) -> str:
        normalized = text.strip()
        if not normalized:
            return ""

        if re.search(r"(?m)^(?:###\s+|-\s+)", normalized):
            return normalized

        paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]
        if len(paragraphs) >= 2:
            return "\n\n".join(paragraphs)

        sentences = MergeRecommendationService._split_sentences(normalized)
        if len(sentences) <= 2:
            return MergeRecommendationService._force_break_for_long_text(normalized)
        chunks = [
            " ".join(sentences[i : i + 2]).strip() for i in range(0, len(sentences), 2)
        ]
        return "\n\n".join(chunk for chunk in chunks if chunk)

    @staticmethod
    def _force_break_for_long_text(text: str) -> str:
        if len(text) <= 220:
            return text

        match = re.search(r"(?:\.|\?|!|다\.|요\.|죠\.)\s+", text)
        if match is not None:
            left = text[: match.end()].strip()
            right = text[match.end() :].strip()
            if left and right:
                return f"{left}\n\n{right}"

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
    def _validate_merged_text(
        normalized_text: str,
        raw_text: str,
        *,
        require_dataset: bool,
        require_openapi: bool,
    ) -> str | None:
        if not normalized_text:
            return "empty"

        if "```" in raw_text or "~~~" in raw_text:
            return "markdown_code_block"
        if re.search(r"<\/?[a-zA-Z][^>]*>", raw_text):
            return "html_tag"

        plain_text = MergeRecommendationService._strip_markdown_for_validation(
            normalized_text
        )

        sentences = MergeRecommendationService._split_sentences(plain_text)
        if len(sentences) < _MERGE_MIN_SENTENCES:
            return "too_short"
        if len(sentences) > _MERGE_HARD_MAX_SENTENCES:
            return "too_long"

        if not MergeRecommendationService._has_minimum_korean(plain_text):
            return "low_korean_ratio"

        if require_dataset and not re.search(r"데이터셋|데이터", plain_text):
            return "missing_dataset_perspective"

        if require_openapi and not re.search(
            r"open\s*api|오픈\s*api|api",
            plain_text,
            re.IGNORECASE,
        ):
            return "missing_openapi_perspective"

        return None

    @staticmethod
    def _is_hard_failure(failure_reason: str) -> bool:
        return failure_reason in {
            "empty",
            "markdown_code_block",
            "html_tag",
            "too_short",
            "too_long",
            "low_korean_ratio",
            "missing_dataset_perspective",
            "missing_openapi_perspective",
        }

    @staticmethod
    def _strip_markdown_for_validation(text: str) -> str:
        plain = re.sub(r"```[\s\S]*?```", " ", text)
        plain = re.sub(r"~~~[\s\S]*?~~~", " ", plain)
        plain = re.sub(r"<\/?[a-zA-Z][^>]*>", " ", plain)
        plain = re.sub(r"`([^`]*)`", r"\1", plain)
        plain = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", plain)
        plain = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", plain)
        plain = re.sub(r"(^|\n)\s{0,3}#{1,6}\s*", " ", plain)
        plain = re.sub(r"(^|\n)\s*(?:[-*+] |\d+\.\s+)", " ", plain)
        plain = re.sub(r"[*_~>]", " ", plain)
        plain = re.sub(r"\s+", " ", plain)
        return plain.strip()

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        base_parts = [
            part.strip()
            for part in re.split(r"(?<=[.!?])\s+|\n+", text)
            if part.strip()
        ]
        parts = [part for part in base_parts if len(part) >= 6]
        return parts or ([text] if text.strip() else [])

    @staticmethod
    def _has_minimum_korean(text: str) -> bool:
        hangul_count = len(re.findall(r"[가-힣]", text))
        alpha_count = len(re.findall(r"[A-Za-z가-힣]", text))
        if alpha_count == 0:
            return False
        return (hangul_count / alpha_count) >= _MERGE_MIN_KOREAN_RATIO

    @staticmethod
    def _build_fallback_merge_text(
        *,
        prompt: str,
        dataset_reason: str,
        openapi_reason: str,
    ) -> str:
        dataset_points = MergeRecommendationService._extract_reason_points(
            dataset_reason,
            max_points=2,
        )
        openapi_points = MergeRecommendationService._extract_reason_points(
            openapi_reason,
            max_points=2,
            skip_identifier_lines=True,
        )

        dataset_primary = (
            dataset_points[0]
            if dataset_points
            else "요청 의도와 유사한 데이터 속성을 우선 반영했습니다"
        )
        dataset_secondary = (
            dataset_points[1]
            if len(dataset_points) > 1
            else "접근 조건과 활용 난이도를 함께 고려해 후보를 정리했습니다"
        )
        openapi_primary = (
            openapi_points[0]
            if openapi_points
            else "Open API 후보의 제공 범위와 인증 방식을 중심으로 정리했습니다"
        )
        openapi_secondary = (
            openapi_points[1]
            if len(openapi_points) > 1
            else "실제 연계 시 필요한 제약 조건을 함께 검토했습니다"
        )
        prompt_hint = MergeRecommendationService._clip_text(prompt, 80)

        paragraphs = [
            MergeRecommendationService._ensure_sentence(
                f"요청하신 '{prompt_hint}' 목적을 기준으로 데이터셋과 Open API 추천 근거를 함께 검토했습니다"
            ),
            MergeRecommendationService._ensure_sentence(
                f"데이터셋 측면에서는 {dataset_primary} 또한 {dataset_secondary}"
            ),
            MergeRecommendationService._ensure_sentence(
                f"Open API 측면에서는 {openapi_primary} 또한 {openapi_secondary}"
            ),
            "근거가 제한된 항목은 확인 필요로 보고, 실제 적용 전 최신 문서와 접근 권한을 점검하는 것을 권장합니다.",
        ]

        return "\n\n".join(paragraphs)

    @staticmethod
    def _extract_reason_points(
        reason_text: str,
        *,
        max_points: int,
        skip_identifier_lines: bool = False,
    ) -> list[str]:
        points: list[str] = []
        for line in reason_text.splitlines():
            item = line.strip()
            if not item:
                continue
            if skip_identifier_lines and re.search(r"openapi_id=\d+", item):
                continue
            item = MergeRecommendationService._sanitize_identifier_tokens(item)
            item = re.sub(r"^\[\d+\]\s*", "", item)
            if " - " in item:
                item = item.split(" - ", 1)[1].strip()
            item = item.strip("-* ")
            item = MergeRecommendationService._clip_text(item, 140)
            if len(item) < 8 or item in points:
                continue
            points.append(item)
            if len(points) >= max_points:
                break
        return points

    @staticmethod
    def _ensure_sentence(text: str) -> str:
        normalized = text.strip()
        if not normalized:
            return ""
        if normalized[-1] in ".!?":
            return normalized
        return normalized + "."

    @staticmethod
    def _clip_text(text: str, max_chars: int) -> str:
        normalized = text.strip().replace("\n", " ")
        if len(normalized) <= max_chars:
            return normalized
        return normalized[: max_chars - 3] + "..."

    @staticmethod
    def _sanitize_identifier_tokens(text: str) -> str:
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
        sanitized = re.sub(r"\n{3,}", "\n\n", sanitized).strip()
        return sanitized

    @staticmethod
    def _extract_content_text(content: Any) -> str:
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
        raise MergeRecommendationUpstreamError("LLM content 형식을 해석할 수 없습니다.")


merge_recommendation_service = MergeRecommendationService()

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

import httpx

from ..core.config import settings
from .llm_router import llm_router


class ChatIntentInputError(ValueError):
    pass


class ChatIntentUpstreamError(RuntimeError):
    pass


_HISTORY_LIMIT = 10
_HISTORY_ITEM_MAX_CHARS = 220
_ALLOWED_MODES = {"CHAT_ONLY", "DATASET_ONLY", "OPENAPI_ONLY", "BOTH"}
_INTENT_MAX_COMPLETION_TOKENS = 240
_CHAT_ANSWER_MAX_COMPLETION_TOKENS = 2000


@dataclass(slots=True)
class RecommendationModeResult:
    mode: str
    llm_model: str


@dataclass(slots=True)
class ChatAnswerResult:
    answer: str
    llm_model: str


class ChatIntentService:
    async def infer_recommendation_mode(
        self,
        *,
        prompt: str,
        history: list[dict[str, str]] | None = None,
    ) -> RecommendationModeResult:
        prompt_text = prompt.strip()
        if not prompt_text:
            raise ChatIntentInputError("prompt는 비어 있을 수 없습니다.")

        contextual_prompt = self._build_contextual_prompt(prompt_text, history)
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["mode"],
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": sorted(_ALLOWED_MODES),
                }
            },
        }

        payload: dict[str, Any] = {
            "model": settings.gpt_model,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "chat_intent_mode",
                    "strict": True,
                    "schema": schema,
                },
            },
            "messages": [
                {
                    "role": "developer",
                    "content": (
                        "Classify the user request into one mode: CHAT_ONLY, DATASET_ONLY, OPENAPI_ONLY, BOTH. "
                        "CHAT_ONLY when user asks for explanation, conversation, advice, or generic Q&A without asking resource recommendations. "
                        "DATASET_ONLY when user explicitly asks dataset recommendations. "
                        "OPENAPI_ONLY when user explicitly asks API/OpenAPI recommendations. "
                        "BOTH when user asks both kinds or asks for integrated resource recommendations. "
                        "Return JSON only."
                    ),
                },
                {"role": "user", "content": contextual_prompt},
            ],
            "max_completion_tokens": _INTENT_MAX_COMPLETION_TOKENS,
        }
        if "mini" in settings.gpt_model.lower():
            payload["reasoning_effort"] = "low"

        body = await self._post_chat_completion(payload)
        content_text = self._extract_first_choice_content(body)
        parsed = self._load_json_object(content_text)
        mode_raw = str(parsed.get("mode") or "").strip().upper()
        if mode_raw not in _ALLOWED_MODES:
            raise ChatIntentUpstreamError("의도 분류 결과(mode)가 유효하지 않습니다.")

        return RecommendationModeResult(
            mode=mode_raw,
            llm_model=self._resolve_response_model(body, settings.gpt_model),
        )

    async def generate_chat_answer(
        self,
        *,
        prompt: str,
        history: list[dict[str, str]] | None = None,
    ) -> ChatAnswerResult:
        prompt_text = prompt.strip()
        if not prompt_text:
            raise ChatIntentInputError("prompt는 비어 있을 수 없습니다.")

        contextual_prompt = self._build_contextual_prompt(prompt_text, history)
        payload: dict[str, Any] = {
            "model": settings.gpt_model,
            "messages": [
                {
                    "role": "developer",
                    "content": (
                        "You are a Korean assistant for plain Q&A. "
                        "Answer in natural Korean prose like a real chat conversation. "
                        "Use readable structure with light formatting and clear spacing. "
                        "When the answer has 2 or more key points, use one short heading plus 3 to 5 concise bullet points. "
                        "Keep one blank line between sections or paragraphs. "
                        "You may add one short closing paragraph after bullets. "
                        "Do not use code fences, HTML tags, markdown tables, or blockquotes. "
                        "Do not recommend datasets or APIs unless user explicitly asks for recommendations. "
                        "Keep response concise and practical."
                    ),
                },
                {"role": "user", "content": contextual_prompt},
            ],
            "max_completion_tokens": _CHAT_ANSWER_MAX_COMPLETION_TOKENS,
        }
        if "mini" in settings.gpt_model.lower():
            payload["reasoning_effort"] = "low"

        body = await self._post_chat_completion(payload)
        content_text = self._extract_first_choice_content(body).strip()
        content_text = self._normalize_plain_markdown(content_text)
        if not content_text:
            raise ChatIntentUpstreamError("채팅 답변이 비어 있습니다.")

        return ChatAnswerResult(
            answer=content_text,
            llm_model=self._resolve_response_model(body, settings.gpt_model),
        )

    @staticmethod
    def _build_contextual_prompt(
        prompt: str,
        history: list[dict[str, str]] | None,
    ) -> str:
        if not history:
            return prompt

        lines: list[str] = []
        for item in history[-_HISTORY_LIMIT:]:
            role = str(item.get("role", "")).strip().upper()
            content = str(item.get("content", "")).strip()
            if not role or not content:
                continue

            clipped = content.replace("\n", " ")
            if len(clipped) > _HISTORY_ITEM_MAX_CHARS:
                clipped = clipped[: _HISTORY_ITEM_MAX_CHARS - 3] + "..."
            lines.append(f"- {role}: {clipped}")

        if not lines:
            return prompt

        return f"{prompt}\n\nConversation context (recent):\n" + "\n".join(lines)

    @staticmethod
    async def _post_chat_completion(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            completion = await llm_router.create_chat_completion(payload)
        except httpx.TimeoutException as exc:
            raise ChatIntentUpstreamError(f"LLM API 타임아웃: {exc}") from exc
        except httpx.RequestError as exc:
            raise ChatIntentUpstreamError(f"LLM API 요청 실패: {exc}") from exc
        except Exception as exc:
            raise ChatIntentUpstreamError(f"LLM API 응답 파싱 실패: {exc}") from exc

        body = completion.get("raw") if isinstance(completion, dict) else None
        if not isinstance(body, dict):
            raise ChatIntentUpstreamError("LLM API 응답 형식이 유효하지 않습니다.")
        resolved_model = completion.get("model")
        if isinstance(resolved_model, str) and resolved_model.strip():
            body["_resolved_model"] = resolved_model.strip()
        if "choices" not in body:
            body["choices"] = [
                {"message": {"content": str(completion.get("content") or "")}}
            ]
        return body

    @staticmethod
    def _resolve_response_model(body: dict[str, Any], default_model: str) -> str:
        for key in ("_resolved_model", "model"):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return default_model

    @staticmethod
    def _extract_first_choice_content(body: dict[str, Any]) -> str:
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ChatIntentUpstreamError("LLM 응답에 choices가 없습니다.")
        first = choices[0]
        if not isinstance(first, dict):
            raise ChatIntentUpstreamError("LLM 응답 choice 형식이 유효하지 않습니다.")
        message = first.get("message")
        if not isinstance(message, dict):
            raise ChatIntentUpstreamError("LLM 응답 message 형식이 유효하지 않습니다.")
        content = message.get("content")
        return ChatIntentService._extract_content_text(content)

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
        return ""

    @staticmethod
    def _normalize_plain_markdown(text: str) -> str:
        normalized = text.strip().replace("\r\n", "\n")
        if not normalized:
            return ""

        normalized = re.sub(r"```[\s\S]*?```", " ", normalized)
        normalized = re.sub(r"~~~[\s\S]*?~~~", " ", normalized)
        normalized = re.sub(r"<\/?[a-zA-Z][^>]*>", " ", normalized)

        cleaned_lines: list[str] = []
        heading_count = 0
        bullet_count = 0
        for raw_line in normalized.split("\n"):
            line = raw_line.strip()
            if not line:
                cleaned_lines.append("")
                continue

            if re.match(r"^\|.*\|$", line):
                continue

            line = re.sub(r"^>\s*", "", line)
            heading_match = re.match(r"^#{1,6}\s*(.+)$", line)
            if heading_match:
                heading_text = re.sub(r"\s+", " ", heading_match.group(1)).strip()
                if heading_text:
                    if heading_count < 2:
                        cleaned_lines.append(f"### {heading_text}")
                        heading_count += 1
                    else:
                        cleaned_lines.append(heading_text)
                continue

            bullet_match = re.match(r"^(?:[-*+]\s+|\d+\.\s+)(.+)$", line)
            if bullet_match:
                bullet_text = re.sub(r"\s+", " ", bullet_match.group(1)).strip()
                if not bullet_text:
                    continue
                if bullet_count < 5:
                    cleaned_lines.append(f"- {bullet_text}")
                    bullet_count += 1
                else:
                    cleaned_lines.append(bullet_text)
                continue

            line = re.sub(r"\s+", " ", line).strip()
            if line:
                cleaned_lines.append(line)

        if any(
            line.startswith("### ") or line.startswith("- ") for line in cleaned_lines
        ):
            structured = "\n".join(cleaned_lines)
            structured = re.sub(r"\n{3,}", "\n\n", structured)
            structured = re.sub(r"[ \t]+", " ", structured).strip()
            return ChatIntentService._format_as_chat_paragraphs(structured)

        paragraphs: list[str] = []
        buffer: list[str] = []
        for line in cleaned_lines:
            if not line:
                if buffer:
                    paragraphs.append(" ".join(buffer).strip())
                    buffer.clear()
                continue
            buffer.append(line)
        if buffer:
            paragraphs.append(" ".join(buffer).strip())

        compact = "\n\n".join(p for p in paragraphs if p)
        compact = re.sub(r"\n{3,}", "\n\n", compact)
        compact = re.sub(r"[ \t]+", " ", compact).strip()
        return ChatIntentService._format_as_chat_paragraphs(compact)

    @staticmethod
    def _format_as_chat_paragraphs(text: str) -> str:
        if not text:
            return ""

        normalized = re.sub(r"\n{3,}", "\n\n", text.strip())
        if re.search(r"(?m)^(?:###\s+|-\s+)", normalized):
            return normalized

        raw_paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]
        if len(raw_paragraphs) >= 2:
            return "\n\n".join(raw_paragraphs)

        sentences = ChatIntentService._split_sentences(normalized)
        if len(sentences) <= 2:
            return ChatIntentService._force_break_for_long_text(normalized)

        chunks: list[str] = []
        for idx in range(0, len(sentences), 2):
            chunks.append(" ".join(sentences[idx : idx + 2]).strip())
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
    def _split_sentences(text: str) -> list[str]:
        parts = [
            part.strip()
            for part in re.split(r"(?<=[.!?])\s+|\n+", text)
            if part.strip()
        ]
        return parts

    @staticmethod
    def _load_json_object(raw_text: str) -> dict[str, Any]:
        text = raw_text.strip()
        if not text:
            raise ChatIntentUpstreamError("LLM 응답(JSON)이 비어 있습니다.")

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ChatIntentUpstreamError(f"LLM 응답(JSON) 파싱 실패: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ChatIntentUpstreamError("LLM 응답(JSON) 객체가 필요합니다.")
        return parsed


chat_intent_service = ChatIntentService()

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ChatMessage(BaseModel):
    role: str
    content: str


class AdapterChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage]
    response_format: dict[str, Any] | None = None
    reasoning_effort: str | None = None
    temperature: float | None = None
    max_completion_tokens: int | None = None

    model_config = ConfigDict(extra="allow")


class AdapterChatCompletionResponse(BaseModel):
    provider: str
    model: str
    content: str
    raw: dict[str, Any]


class AdapterStatusResponse(BaseModel):
    primaryProvider: str
    codex: dict[str, Any]

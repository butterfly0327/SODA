from __future__ import annotations

import html
import re
from typing import Any, List, Optional

_WHITESPACE_RE = re.compile(r"\s+")
_TAG_RE = re.compile(r"<[^>]+>")

# open_api.response_format CHECK 제약: JSON, XML, JSON+XML 만 허용
VALID_RESPONSE_FORMATS = {"JSON", "XML", "JSON+XML"}


def clean_text(text: Any) -> Optional[str]:
    """HTML 태그 제거 + 공백 정규화."""
    if text is None:
        return None
    if not isinstance(text, str):
        text = str(text)
    text = html.unescape(text)
    text = _TAG_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text or None


def normalize_response_format(fmt: Optional[str]) -> Optional[str]:
    """DB CHECK 제약에 맞게 응답 포맷 정규화. 알 수 없는 값은 None으로."""
    if not fmt:
        return None
    upper = fmt.strip().upper()
    return upper if upper in VALID_RESPONSE_FORMATS else None


def truncate(text: Optional[str], max_len: int = 500) -> Optional[str]:
    if not text:
        return text
    return text[:max_len] if len(text) > max_len else text


def to_pg_array(lst: List[str]) -> str:
    """Python list → PostgreSQL TEXT[] 문자열 표현 (SQLAlchemy CAST용)."""
    if not lst:
        return "{}"
    escaped = []
    for s in lst:
        s = str(s)
        if any(c in s for c in [",", '"', "{", "}"]):
            escaped.append('"' + s.replace('"', '\\"') + '"')
        else:
            escaped.append(s)
    return "{" + ",".join(escaped) + "}"

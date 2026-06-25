from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class RunnerStatus:
    enabled: bool
    reachable: bool
    auth_present: bool
    max_concurrency: int
    max_queue: int
    queue_depth: int = 0
    running_count: int = 0
    last_success_at: str | None = None
    last_failure_at: str | None = None
    last_fallback_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "reachable": self.reachable,
            "authPresent": self.auth_present,
            "maxConcurrency": self.max_concurrency,
            "maxQueue": self.max_queue,
            "queueDepth": self.queue_depth,
            "runningCount": self.running_count,
            "lastSuccessAt": self.last_success_at,
            "lastFailureAt": self.last_failure_at,
            "lastFallbackReason": self.last_fallback_reason,
        }

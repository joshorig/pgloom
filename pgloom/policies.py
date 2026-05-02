from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: int = 2
    max_delay_seconds: int = 60

    def delay_for_attempt(self, attempt: int) -> int:
        return int(min(self.max_delay_seconds, self.base_delay_seconds ** max(attempt, 0)))

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


DEFAULT_RETRY_POLICY = RetryPolicy()


def resolve_retry_policy(payload: dict[str, Any] | None) -> RetryPolicy:
    raw = (payload or {}).get("retry_policy")
    if not isinstance(raw, dict):
        return DEFAULT_RETRY_POLICY
    return RetryPolicy(
        max_attempts=int(raw.get("max_attempts", DEFAULT_RETRY_POLICY.max_attempts)),
        base_delay_seconds=int(
            raw.get("base_delay_seconds", DEFAULT_RETRY_POLICY.base_delay_seconds)
        ),
        max_delay_seconds=int(raw.get("max_delay_seconds", DEFAULT_RETRY_POLICY.max_delay_seconds)),
    )

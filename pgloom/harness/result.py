from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class HandlerResult:
    status: Literal["done", "blocked", "approval", "retry"]
    result: dict[str, Any] = field(default_factory=dict)
    message: str | None = None
    blocker_code: str | None = None
    blocker_reason: str | None = None

    @classmethod
    def done(cls, result: dict[str, Any] | None = None) -> HandlerResult:
        return cls(status="done", result=result or {})

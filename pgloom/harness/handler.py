from __future__ import annotations

from typing import Any, Protocol

from pgloom.harness.result import HandlerResult


class TaskHandler(Protocol):
    def handle(self, task: dict[str, Any]) -> HandlerResult:
        """Run one task and return a structured result."""

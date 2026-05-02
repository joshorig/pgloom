from __future__ import annotations

from typing import Any

from pgloom.harness.result import HandlerResult


class FakeHandler:
    def handle(self, task: dict[str, Any]) -> HandlerResult:
        behavior = task.get("payload", {}).get("behavior", "done")
        if behavior == "blocked":
            return HandlerResult(
                status="blocked", blocker_code="fake_blocked", blocker_reason="fake"
            )
        if behavior == "approval":
            return HandlerResult(status="approval", message="fake approval")
        if behavior == "retry":
            return HandlerResult(status="retry", message="fake retry")
        return HandlerResult.done({"handled_by": "fake"})

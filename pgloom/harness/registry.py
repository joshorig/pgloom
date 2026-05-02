from __future__ import annotations

from pgloom.harness.handler import TaskHandler


class HandlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, TaskHandler] = {}

    def register(self, task_type: str, handler: TaskHandler) -> None:
        self._handlers[task_type] = handler

    def get(self, task_type: str) -> TaskHandler:
        return self._handlers[task_type]

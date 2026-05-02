from __future__ import annotations

import threading
from typing import Any, Protocol

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    workflow_id: str
    key: str
    value: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryStore(Protocol):
    def put(self, entry: MemoryEntry) -> None: ...

    def get(self, workflow_id: str, key: str) -> MemoryEntry | None: ...

    def list_for_workflow(self, workflow_id: str) -> list[MemoryEntry]: ...

    def delete(self, workflow_id: str, key: str) -> bool: ...


class NullMemoryStore:
    def put(self, entry: MemoryEntry) -> None:
        return None

    def get(self, workflow_id: str, key: str) -> MemoryEntry | None:
        return None

    def list_for_workflow(self, workflow_id: str) -> list[MemoryEntry]:
        return []

    def delete(self, workflow_id: str, key: str) -> bool:
        return False


class InMemoryMemoryStore:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], MemoryEntry] = {}
        self._lock = threading.Lock()

    def put(self, entry: MemoryEntry) -> None:
        with self._lock:
            self._entries[(entry.workflow_id, entry.key)] = entry

    def get(self, workflow_id: str, key: str) -> MemoryEntry | None:
        with self._lock:
            return self._entries.get((workflow_id, key))

    def list_for_workflow(self, workflow_id: str) -> list[MemoryEntry]:
        with self._lock:
            return sorted(
                (entry for entry in self._entries.values() if entry.workflow_id == workflow_id),
                key=lambda item: item.key,
            )

    def delete(self, workflow_id: str, key: str) -> bool:
        with self._lock:
            return self._entries.pop((workflow_id, key), None) is not None

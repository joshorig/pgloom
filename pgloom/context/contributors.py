from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ContextContributor(BaseModel):
    kind: str
    label: str
    text: str
    priority: float = 0
    artifact_id: str | None = None
    tokens: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PackedContributor(BaseModel):
    kind: str
    label: str
    artifact_id: str | None = None
    tokens_original: int = Field(ge=0)
    tokens_packed: int = Field(ge=0)
    included: bool
    truncated: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

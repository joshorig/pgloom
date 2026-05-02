from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Scenario:
    id: str
    purpose: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    assertions: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_path(cls, path: str | Path) -> Scenario:
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls(
            id=str(payload["id"]),
            purpose=str(payload.get("purpose", "")),
            steps=list(payload.get("steps", [])),
            assertions=list(payload.get("assertions", [])),
        )

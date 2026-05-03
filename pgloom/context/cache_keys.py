from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field


class PromptCacheKey(BaseModel):
    model_profile: str
    prompt_template_version: str
    artifact_hashes: list[str] = Field(default_factory=list)
    static_context_hash: str = ""
    strategy_version: str = "v1"
    metadata: dict[str, Any] = Field(default_factory=dict)

    def digest(self) -> str:
        payload = self.model_dump(mode="json")
        payload["artifact_hashes"] = sorted(self.artifact_hashes)
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

from __future__ import annotations

import hashlib

from pgloom.models.provider import ModelRequest, ModelResponse


class FakeModelProvider:
    def complete(self, request: ModelRequest) -> ModelResponse:
        digest = hashlib.sha256(request.prompt.encode("utf-8")).hexdigest()[:12]
        text = f"fake:{digest}"
        return ModelResponse(
            text=text,
            input_tokens=max(1, len(request.prompt.split())),
            output_tokens=1,
            cost_usd=0.0,
        )

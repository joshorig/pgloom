from __future__ import annotations

from pgloom.models.fake import FakeModelProvider
from pgloom.models.provider import ModelProvider, ModelRequest, ModelResponse


class ModelRouter:
    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {"fake": FakeModelProvider()}

    def register(self, name: str, provider: ModelProvider) -> None:
        self._providers[name] = provider

    def complete(self, request: ModelRequest) -> ModelResponse:
        return self._providers[request.profile].complete(request)

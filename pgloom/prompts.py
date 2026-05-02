from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PromptTemplate(BaseModel):
    name: str
    version: str = "1"
    template: str
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromptRegistry:
    """In-memory prompt registry. Downstream apps may persist by extending this class."""

    def __init__(self) -> None:
        self._templates: dict[tuple[str, str], PromptTemplate] = {}

    def register(self, template: PromptTemplate) -> None:
        self._templates[(template.name, template.version)] = template

    def get(self, name: str, version: str | None = None) -> PromptTemplate:
        if version is not None:
            try:
                return self._templates[(name, version)]
            except KeyError as exc:
                raise KeyError(f"Unknown prompt {name!r} version {version!r}") from exc
        candidates = [item for item in self._templates.values() if item.name == name]
        if not candidates:
            raise KeyError(f"Unknown prompt {name!r}")
        return sorted(candidates, key=lambda item: item.version)[-1]

    def list(self) -> list[PromptTemplate]:
        return sorted(self._templates.values(), key=lambda item: (item.name, item.version))

    def render(self, prompt_name: str, *, version: str | None = None, **values: Any) -> str:
        return self.get(prompt_name, version).template.format(**values)


_default_registry = PromptRegistry()


def register_prompt(template: PromptTemplate) -> None:
    _default_registry.register(template)


def render_prompt(prompt_name: str, *, version: str | None = None, **values: Any) -> str:
    return _default_registry.render(prompt_name, version=version, **values)


__all__ = [
    "PromptRegistry",
    "PromptTemplate",
    "register_prompt",
    "render_prompt",
]

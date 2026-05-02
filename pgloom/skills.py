from __future__ import annotations

import builtins
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class Skill(BaseModel):
    name: str
    version: str = "1"
    handler_type: str
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[tuple[str, str], Skill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[(skill.name, skill.version)] = skill

    def get(self, name: str, version: str | None = None) -> Skill:
        if version is not None:
            try:
                return self._skills[(name, version)]
            except KeyError as exc:
                raise KeyError(f"Unknown skill {name!r} version {version!r}") from exc
        candidates = [item for item in self._skills.values() if item.name == name]
        if not candidates:
            raise KeyError(f"Unknown skill {name!r}")
        return sorted(candidates, key=lambda item: item.version)[-1]

    def list(self) -> builtins.list[Skill]:
        return sorted(self._skills.values(), key=lambda item: (item.name, item.version))

    def for_handler_type(self, handler_type: str) -> builtins.list[Skill]:
        return [item for item in self.list() if item.handler_type == handler_type]

    def load_yaml(self, path: str | Path) -> int:
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("skills"), list):
            raise ValueError("skills YAML must contain a 'skills' list")
        count = 0
        for raw_skill in payload["skills"]:
            self.register(Skill.model_validate(raw_skill))
            count += 1
        return count


_default_registry = SkillRegistry()


def register_skill(skill: Skill) -> None:
    _default_registry.register(skill)


def get_skill(name: str, version: str | None = None) -> Skill:
    return _default_registry.get(name, version)


def load_skills_config(path: str | Path) -> int:
    return _default_registry.load_yaml(path)

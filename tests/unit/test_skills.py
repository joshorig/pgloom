from __future__ import annotations

from pathlib import Path

import pytest

from pgloom.skills import Skill, SkillRegistry


def test_skill_register_get_and_filter() -> None:
    registry = SkillRegistry()
    skill = Skill(name="demo", handler_type="fake.complete")
    registry.register(skill)
    assert registry.get("demo") == skill
    assert registry.for_handler_type("fake.complete") == [skill]


def test_skill_load_yaml(tmp_path: Path) -> None:
    path = tmp_path / "skills.yaml"
    path.write_text(
        """
skills:
  - name: alpha
    version: "1"
    handler_type: fake.complete
  - name: beta
    version: "1"
    handler_type: fake.block
""",
        encoding="utf-8",
    )
    registry = SkillRegistry()
    assert registry.load_yaml(path) == 2
    assert registry.get("alpha").handler_type == "fake.complete"


def test_skill_malformed_yaml_raises(tmp_path: Path) -> None:
    path = tmp_path / "skills.yaml"
    path.write_text("not_skills: []\n", encoding="utf-8")
    with pytest.raises(ValueError):
        SkillRegistry().load_yaml(path)

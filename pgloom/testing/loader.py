from __future__ import annotations

from pathlib import Path

from pgloom.testing.scenario import Scenario


def load_scenarios(path: str | Path) -> list[Scenario]:
    root = Path(path)
    files = sorted(root.rglob("*.yaml")) if root.is_dir() else [root]
    return [Scenario.from_path(file) for file in files]

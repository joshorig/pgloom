from __future__ import annotations

from typing import Any

from psycopg.types.json import Jsonb


def jsonb(value: Any) -> Jsonb:
    return Jsonb(value)

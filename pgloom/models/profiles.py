from __future__ import annotations

from typing import Any

from pgloom.db.json import jsonb
from pgloom.db.postgres import connect


def upsert_profile(
    name: str, provider: str, model: str, settings: dict[str, Any] | None = None
) -> None:
    with connect() as conn, conn.transaction():
        conn.execute(
            """
            insert into model_profiles(name, provider, model, settings)
            values (%s, %s, %s, %s)
            on conflict(name) do update set provider = excluded.provider,
              model = excluded.model, settings = excluded.settings
            """,
            (name, provider, model, jsonb(settings or {})),
        )

from __future__ import annotations

from typing import Any

from pgloom.db.json import jsonb
from pgloom.db.postgres import connect


def get_slot_concurrency(conn: Any, slot: str) -> int | None:
    row = conn.execute(
        "select concurrency from slots where name = %s and enabled",
        (slot,),
    ).fetchone()
    return int(row["concurrency"]) if row else None


def upsert_slot(
    conn: Any | None = None,
    *,
    name: str,
    enabled: bool = True,
    concurrency: int = 1,
    metadata: dict[str, Any] | None = None,
    database_url: str | None = None,
) -> None:
    def write(target: Any) -> None:
        target.execute(
            """
            insert into slots(name, enabled, concurrency, metadata)
            values (%s, %s, %s, %s)
            on conflict(name) do update set enabled = excluded.enabled,
              concurrency = excluded.concurrency, metadata = excluded.metadata
            """,
            (name, enabled, concurrency, jsonb(metadata or {})),
        )

    if conn is not None:
        write(conn)
        return
    with connect(database_url) as managed, managed.transaction():
        write(managed)

from __future__ import annotations

from pgloom.db.json import jsonb
from pgloom.db.postgres import connect


def upsert_quota(
    name: str,
    *,
    capacity: float,
    remaining: float | None = None,
    database_url: str | None = None,
) -> None:
    with connect(database_url) as conn, conn.transaction():
        conn.execute(
            """
            insert into quota_buckets(name, capacity, remaining, metadata)
            values (%s, %s, %s, %s)
            on conflict(name) do update set
              capacity = excluded.capacity,
              remaining = excluded.remaining,
              metadata = excluded.metadata
            """,
            (name, capacity, capacity if remaining is None else remaining, jsonb({})),
        )


def consume_quota(name: str, amount: float = 1, *, database_url: str | None = None) -> bool:
    with connect(database_url) as conn, conn.transaction():
        row = conn.execute(
            "select remaining from quota_buckets where name = %s for update", (name,)
        ).fetchone()
        if not row or float(row["remaining"]) < amount:
            return False
        conn.execute(
            "update quota_buckets set remaining = remaining - %s where name = %s", (amount, name)
        )
        return True

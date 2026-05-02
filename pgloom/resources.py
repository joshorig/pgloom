from __future__ import annotations

from datetime import timedelta

from pgloom.db.postgres import connect
from pgloom.time import utcnow


def acquire_lock(
    *,
    resource_key: str,
    owner_id: str,
    task_id: str | None = None,
    ttl_seconds: int = 300,
    database_url: str | None = None,
) -> bool:
    with connect(database_url) as conn, conn.transaction():
        conn.execute("delete from resource_locks where expires_at < now()")
        row = conn.execute(
            """
            insert into resource_locks(resource_key, owner_id, task_id, expires_at)
            values (%s, %s, %s, %s)
            on conflict(resource_key) do nothing
            returning resource_key
            """,
            (resource_key, owner_id, task_id, utcnow() + timedelta(seconds=ttl_seconds)),
        ).fetchone()
        return bool(row)

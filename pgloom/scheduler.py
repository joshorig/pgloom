from __future__ import annotations

from typing import Any


def due_task_ids(conn: Any, *, slot: str | None = None, limit: int = 100) -> list[str]:
    if slot is None:
        rows = conn.execute(
            """
            select id from tasks
            where state = 'queued' and run_after <= now()
            order by priority desc, run_after asc
            limit %s
            """,
            (limit,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            select id from tasks
            where state = 'queued' and run_after <= now() and slot = %s
            order by priority desc, run_after asc
            limit %s
            """,
            (slot, limit),
        ).fetchall()
    return [str(row["id"]) for row in rows]


def tick(conn: Any, *, slot: str | None = None, limit: int = 100) -> int:
    return len(due_task_ids(conn, slot=slot, limit=limit))

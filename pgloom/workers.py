from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from pgloom.db.json import jsonb


class WorkerInfo(BaseModel):
    id: str
    slot: str
    state: str
    current_task_id: str | None
    last_heartbeat_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


def _to_worker(row: dict[str, Any]) -> WorkerInfo:
    return WorkerInfo.model_validate(row)


def register_worker(
    conn: Any,
    *,
    worker_id: str,
    slot: str,
    metadata: dict[str, Any] | None = None,
) -> WorkerInfo:
    row = conn.execute(
        """
        insert into workers(id, slot, state, current_task_id, last_heartbeat_at, metadata)
        values (%s, %s, 'idle', null, now(), %s)
        on conflict(id) do update set
          slot = excluded.slot,
          state = 'idle',
          current_task_id = null,
          last_heartbeat_at = now(),
          metadata = excluded.metadata
        returning *
        """,
        (worker_id, slot, jsonb(metadata or {})),
    ).fetchone()
    assert row is not None
    return _to_worker(dict(row))


def deregister_worker(conn: Any, *, worker_id: str) -> bool:
    result = conn.execute("delete from workers where id = %s", (worker_id,))
    return bool(result.rowcount)


def set_idle(conn: Any, *, worker_id: str) -> None:
    conn.execute(
        """
        update workers
        set state = 'idle', current_task_id = null, last_heartbeat_at = now()
        where id = %s
        """,
        (worker_id,),
    )


def set_busy(conn: Any, *, worker_id: str, task_id: str) -> None:
    conn.execute(
        """
        update workers
        set state = 'busy', current_task_id = %s, last_heartbeat_at = now()
        where id = %s
        """,
        (task_id, worker_id),
    )


def list_active(
    conn: Any,
    *,
    slot: str | None = None,
    stale_after_seconds: int = 60,
) -> list[WorkerInfo]:
    if slot is None:
        rows = conn.execute(
            """
            select * from workers
            where last_heartbeat_at >= now() - (%s * interval '1 second')
            order by id
            """,
            (stale_after_seconds,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            select * from workers
            where slot = %s and last_heartbeat_at >= now() - (%s * interval '1 second')
            order by id
            """,
            (slot, stale_after_seconds),
        ).fetchall()
    return [_to_worker(dict(row)) for row in rows]


def heartbeat(conn: Any, *, worker_id: str) -> None:
    conn.execute("update workers set last_heartbeat_at = now() where id = %s", (worker_id,))


def run_once(*args: Any, **kwargs: Any) -> dict[str, object]:
    from pgloom.harness.runner import run_once as harness_run_once

    return harness_run_once(*args, **kwargs)

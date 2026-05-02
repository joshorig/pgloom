from __future__ import annotations

from datetime import timedelta

from pgloom.db.postgres import connect
from pgloom.events import append_event
from pgloom.time import utcnow


def heartbeat(
    task_id: str, worker_id: str, *, lease_seconds: int = 300, database_url: str | None = None
) -> bool:
    with connect(database_url) as conn, conn.transaction():
        row = conn.execute(
            "select * from tasks where id = %s and lease_owner = %s for update",
            (task_id, worker_id),
        ).fetchone()
        if not row:
            return False
        conn.execute(
            "update tasks set lease_expires_at = %s, updated_at = now() where id = %s",
            (utcnow() + timedelta(seconds=lease_seconds), task_id),
        )
        conn.execute(
            "update workers set last_heartbeat_at = now() where id = %s",
            (worker_id,),
        )
        append_event(
            conn, event_type="task.heartbeat", workflow_id=row["workflow_id"], task_id=task_id
        )
        return True

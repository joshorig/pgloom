from __future__ import annotations

from pgloom.approvals import expire_pending_approvals
from pgloom.db.postgres import connect
from pgloom.events import append_event
from pgloom.states import TaskState
from pgloom.workers import set_idle


def reap_expired_leases(*, database_url: str | None = None, limit: int = 100) -> int:
    count = 0
    with connect(database_url) as conn, conn.transaction():
        rows = conn.execute(
            """
            select * from tasks
            where state in (%s, %s) and lease_expires_at < now()
            order by lease_expires_at asc
            for update skip locked
            limit %s
            """,
            (TaskState.LEASED.value, TaskState.RUNNING.value, limit),
        ).fetchall()
        for row in rows:
            next_state = (
                TaskState.QUEUED if row["attempt"] < row["max_attempts"] else TaskState.FAILED
            )
            conn.execute(
                """
                update tasks
                set state = %s, lease_owner = null, lease_expires_at = null,
                    updated_at = now()
                where id = %s
                """,
                (next_state.value, row["id"]),
            )
            append_event(
                conn,
                event_type="task.lease_expired",
                workflow_id=row["workflow_id"],
                task_id=row["id"],
                from_state=row["state"],
                to_state=next_state.value,
            )
            if next_state == TaskState.FAILED:
                dependents = conn.execute(
                    """
                    select t.id, t.workflow_id from tasks t
                    join task_dependencies d on d.task_id = t.id
                    where d.depends_on_task_id = %s
                      and t.state not in (%s, %s, %s, %s)
                    for update
                    """,
                    (
                        row["id"],
                        TaskState.DONE.value,
                        TaskState.FAILED.value,
                        TaskState.CANCELLED.value,
                        TaskState.ABANDONED.value,
                    ),
                ).fetchall()
                for dependent in dependents:
                    conn.execute(
                        """
                        update tasks
                        set state = %s, blocker_code = %s, blocker_reason = %s,
                            updated_at = now()
                        where id = %s
                        """,
                        (
                            TaskState.BLOCKED.value,
                            "dependency_terminal",
                            f"Dependency {row['id']} reached failed",
                            dependent["id"],
                        ),
                    )
                    append_event(
                        conn,
                        event_type="task.dependency_blocked",
                        workflow_id=dependent["workflow_id"],
                        task_id=dependent["id"],
                        to_state=TaskState.BLOCKED.value,
                    )
            workers = conn.execute(
                "select id from workers where current_task_id = %s", (row["id"],)
            ).fetchall()
            for worker in workers:
                set_idle(conn, worker_id=worker["id"])
            count += 1
    return count


def sweep(*, database_url: str | None = None, limit: int = 100) -> dict[str, int]:
    return {
        "leases_reaped": reap_expired_leases(database_url=database_url, limit=limit),
        "approvals_expired": expire_pending_approvals(database_url=database_url, limit=limit),
    }

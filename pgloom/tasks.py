from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from pgloom.db.json import jsonb
from pgloom.db.postgres import connect
from pgloom.events import append_event
from pgloom.ids import new_id
from pgloom.notifications import Notification, emit
from pgloom.policies import resolve_retry_policy
from pgloom.slots import get_slot_concurrency
from pgloom.states import TERMINAL_TASK_STATES, TaskState, WorkflowState
from pgloom.time import utcnow
from pgloom.workers import register_worker, set_busy, set_idle


def enqueue_task(
    *,
    workflow_id: str,
    domain: str,
    task_type: str,
    slot: str,
    payload: dict[str, Any] | None = None,
    priority: int = 0,
    run_after: datetime | None = None,
    max_attempts: int = 3,
    depends_on: list[str] | None = None,
    database_url: str | None = None,
) -> dict[str, Any]:
    task_id = new_id("task")
    state = TaskState.BLOCKED if depends_on else TaskState.QUEUED
    with connect(database_url) as conn, conn.transaction():
        row = conn.execute(
            """
            insert into tasks(
              id, workflow_id, domain, task_type, slot, state, priority, payload,
              run_after, max_attempts
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            returning *
            """,
            (
                task_id,
                workflow_id,
                domain,
                task_type,
                slot,
                state.value,
                priority,
                jsonb(payload or {}),
                run_after or utcnow(),
                max_attempts,
            ),
        ).fetchone()
        assert row is not None
        for dependency_id in depends_on or []:
            conn.execute(
                "insert into task_dependencies(task_id, depends_on_task_id) values (%s, %s)",
                (task_id, dependency_id),
            )
        append_event(
            conn,
            event_type="task.enqueued",
            workflow_id=workflow_id,
            task_id=task_id,
            to_state=state.value,
        )
        conn.execute(
            "update workflows set state = %s, updated_at = now() where id = %s and state = %s",
            (WorkflowState.RUNNING.value, workflow_id, WorkflowState.OPEN.value),
        )
        return dict(row)


def claim_next(
    *,
    slot: str,
    worker_id: str,
    lease_seconds: int = 300,
    database_url: str | None = None,
) -> dict[str, Any] | None:
    with connect(database_url) as conn, conn.transaction():
        blocked = conn.execute(
            """
            select 1 from health_checks
            where blocks_dispatch is true and status != 'ok'
            order by created_at desc limit 1
            """
        ).fetchone()
        if blocked:
            return None
        concurrency = get_slot_concurrency(conn, slot)
        if concurrency is not None:
            in_flight = conn.execute(
                """
                select count(*) as count from tasks
                where slot = %s and state in (%s, %s)
                """,
                (slot, TaskState.LEASED.value, TaskState.RUNNING.value),
            ).fetchone()
            if in_flight and int(in_flight["count"]) >= concurrency:
                return None
        row = conn.execute(
            """
            select * from tasks
            where slot = %s and state = %s and run_after <= now()
            order by priority desc, run_after asc, created_at asc
            for update skip locked
            limit 1
            """,
            (slot, TaskState.QUEUED.value),
        ).fetchone()
        if not row:
            return None
        if not _reserve_dispatch_constraints(conn, row, worker_id):
            return None
        lease_expires = utcnow() + timedelta(seconds=lease_seconds)
        updated = conn.execute(
            """
            update tasks
            set state = %s, lease_owner = %s, lease_expires_at = %s,
                attempt = attempt + 1, updated_at = now()
            where id = %s
            returning *
            """,
            (TaskState.LEASED.value, worker_id, lease_expires, row["id"]),
        ).fetchone()
        assert updated is not None
        register_worker(conn, worker_id=worker_id, slot=slot)
        set_busy(conn, worker_id=worker_id, task_id=row["id"])
        append_event(
            conn,
            event_type="task.claimed",
            workflow_id=row["workflow_id"],
            task_id=row["id"],
            from_state=row["state"],
            to_state=TaskState.LEASED.value,
            metadata={"worker_id": worker_id},
        )
        return dict(updated)


def _reserve_dispatch_constraints(conn: Any, row: dict[str, Any], worker_id: str) -> bool:
    payload = row.get("payload") or {}
    for resource_key in payload.get("resources", []):
        conn.execute("delete from resource_locks where expires_at < now()")
        reserved = conn.execute(
            """
            insert into resource_locks(resource_key, owner_id, task_id, expires_at)
            values (%s, %s, %s, now() + interval '5 minutes')
            on conflict(resource_key) do nothing
            returning resource_key
            """,
            (str(resource_key), worker_id, row["id"]),
        ).fetchone()
        if not reserved:
            append_event(
                conn,
                event_type="task.resource_unavailable",
                workflow_id=row["workflow_id"],
                task_id=row["id"],
                metadata={"resource_key": str(resource_key)},
            )
            return False

    for quota in payload.get("quotas", []):
        quota_name = str(quota["name"])
        amount = float(quota.get("amount", 1))
        bucket = conn.execute(
            "select remaining from quota_buckets where name = %s for update", (quota_name,)
        ).fetchone()
        if not bucket or float(bucket["remaining"]) < amount:
            conn.execute(
                """
                update tasks
                set state = %s, blocker_code = %s, blocker_reason = %s, updated_at = now()
                where id = %s
                """,
                (
                    TaskState.BLOCKED.value,
                    "quota_exhausted",
                    f"Quota {quota_name} has insufficient remaining capacity",
                    row["id"],
                ),
            )
            append_event(
                conn,
                event_type="task.quota_exhausted",
                workflow_id=row["workflow_id"],
                task_id=row["id"],
                from_state=row["state"],
                to_state=TaskState.BLOCKED.value,
                metadata={"quota": quota_name, "amount": amount},
            )
            _refresh_workflow_state(conn, row["workflow_id"])
            return False
        conn.execute(
            "update quota_buckets set remaining = remaining - %s where name = %s",
            (amount, quota_name),
        )
    return True


def transition_task(
    task_id: str,
    to_state: TaskState,
    *,
    result: dict[str, Any] | None = None,
    blocker_code: str | None = None,
    blocker_reason: str | None = None,
    message: str | None = None,
    database_url: str | None = None,
) -> dict[str, Any] | None:
    with connect(database_url) as conn, conn.transaction():
        row = conn.execute("select * from tasks where id = %s for update", (task_id,)).fetchone()
        if not row:
            return None
        updated = conn.execute(
            """
            update tasks
            set state = %s,
                result = case when %s::jsonb = '{}'::jsonb then result else %s::jsonb end,
                blocker_code = %s,
                blocker_reason = %s,
                updated_at = now()
            where id = %s
            returning *
            """,
            (
                to_state.value,
                jsonb(result or {}),
                jsonb(result or {}),
                blocker_code,
                blocker_reason,
                task_id,
            ),
        ).fetchone()
        assert updated is not None
        append_event(
            conn,
            event_type="task.transitioned",
            workflow_id=row["workflow_id"],
            task_id=task_id,
            from_state=row["state"],
            to_state=to_state.value,
            message=message,
        )
        if to_state == TaskState.DONE:
            _unblock_dependents(conn, task_id)
        elif to_state in {TaskState.FAILED, TaskState.CANCELLED, TaskState.ABANDONED}:
            _block_dependents(conn, task_id, to_state)
        if to_state in TERMINAL_TASK_STATES or to_state in {
            TaskState.BLOCKED,
            TaskState.AWAITING_APPROVAL,
            TaskState.AWAITING_QA,
            TaskState.AWAITING_REVIEW,
        }:
            _clear_workers_for_task(conn, task_id)
        if to_state in {TaskState.DONE, TaskState.FAILED}:
            emit(
                Notification(
                    kind=f"task.{to_state.value}",
                    workflow_id=row["workflow_id"],
                    task_id=task_id,
                    message=f"Task {task_id} transitioned to {to_state.value}",
                )
            )
        _refresh_workflow_state(conn, row["workflow_id"])
        return dict(updated)


def retry_or_fail_task(task_id: str, *, reason: str, database_url: str | None = None) -> None:
    with connect(database_url) as conn, conn.transaction():
        row = conn.execute("select * from tasks where id = %s for update", (task_id,)).fetchone()
        if not row:
            return
        policy = resolve_retry_policy(dict(row["payload"] or {}))
        max_attempts = min(int(row["max_attempts"]), policy.max_attempts)
        if int(row["attempt"]) >= max_attempts:
            state = TaskState.FAILED
            run_after = row["run_after"]
        else:
            state = TaskState.QUEUED
            run_after = utcnow() + timedelta(seconds=policy.delay_for_attempt(int(row["attempt"])))
        conn.execute(
            """
            update tasks
            set state = %s, run_after = %s, lease_owner = null,
              lease_expires_at = null, blocker_reason = %s, updated_at = now()
            where id = %s
            """,
            (state.value, run_after, reason, task_id),
        )
        append_event(
            conn,
            event_type="task.retry_policy_applied",
            workflow_id=row["workflow_id"],
            task_id=task_id,
            from_state=row["state"],
            to_state=state.value,
            message=reason,
            metadata={"policy": policy.as_dict()},
        )
        if state == TaskState.FAILED:
            _block_dependents(conn, task_id, state)
            emit(
                Notification(
                    kind="task.failed",
                    workflow_id=row["workflow_id"],
                    task_id=task_id,
                    message=f"Task {task_id} failed after retry policy",
                )
            )
        _clear_workers_for_task(conn, task_id)
        _refresh_workflow_state(conn, row["workflow_id"])


def list_tasks(
    *, workflow_id: str | None = None, database_url: str | None = None
) -> list[dict[str, Any]]:
    with connect(database_url) as conn:
        if workflow_id:
            rows = conn.execute(
                "select * from tasks where workflow_id = %s order by created_at", (workflow_id,)
            ).fetchall()
        else:
            rows = conn.execute("select * from tasks order by created_at").fetchall()
        return [dict(row) for row in rows]


def get_task(task_id: str, *, database_url: str | None = None) -> dict[str, Any] | None:
    with connect(database_url) as conn:
        task = conn.execute("select * from tasks where id = %s", (task_id,)).fetchone()
        if not task:
            return None
        events = conn.execute(
            "select * from task_events where task_id = %s order by created_at desc limit 20",
            (task_id,),
        ).fetchall()
        dependencies = conn.execute(
            "select * from task_dependencies where task_id = %s order by created_at",
            (task_id,),
        ).fetchall()
        return {
            "task": dict(task),
            "events": [dict(row) for row in events],
            "dependencies": [dict(row) for row in dependencies],
        }


def _clear_workers_for_task(conn: Any, task_id: str) -> None:
    rows = conn.execute("select id from workers where current_task_id = %s", (task_id,)).fetchall()
    for row in rows:
        set_idle(conn, worker_id=row["id"])


def _unblock_dependents(conn: Any, dependency_id: str) -> None:
    rows = conn.execute(
        """
        select t.id, t.workflow_id from tasks t
        where t.state = %s
          and exists (
            select 1 from task_dependencies d
            where d.task_id = t.id and d.depends_on_task_id = %s
          )
          and not exists (
            select 1 from task_dependencies d
            join tasks dep on dep.id = d.depends_on_task_id
            where d.task_id = t.id and dep.state != %s
          )
        for update
        """,
        (TaskState.BLOCKED.value, dependency_id, TaskState.DONE.value),
    ).fetchall()
    for row in rows:
        conn.execute(
            "update tasks set state = %s, blocker_code = null, blocker_reason = null where id = %s",
            (TaskState.QUEUED.value, row["id"]),
        )
        append_event(
            conn,
            event_type="task.dependency_unblocked",
            workflow_id=row["workflow_id"],
            task_id=row["id"],
            from_state=TaskState.BLOCKED.value,
            to_state=TaskState.QUEUED.value,
        )


def _block_dependents(conn: Any, dependency_id: str, dependency_state: TaskState) -> None:
    rows = conn.execute(
        """
        select t.id, t.workflow_id from tasks t
        join task_dependencies d on d.task_id = t.id
        where d.depends_on_task_id = %s
          and t.state not in (%s, %s, %s, %s)
        for update
        """,
        (
            dependency_id,
            TaskState.DONE.value,
            TaskState.FAILED.value,
            TaskState.CANCELLED.value,
            TaskState.ABANDONED.value,
        ),
    ).fetchall()
    for row in rows:
        conn.execute(
            """
            update tasks
            set state = %s, blocker_code = %s, blocker_reason = %s, updated_at = now()
            where id = %s
            """,
            (
                TaskState.BLOCKED.value,
                "dependency_terminal",
                f"Dependency {dependency_id} reached {dependency_state.value}",
                row["id"],
            ),
        )
        append_event(
            conn,
            event_type="task.dependency_blocked",
            workflow_id=row["workflow_id"],
            task_id=row["id"],
            to_state=TaskState.BLOCKED.value,
            metadata={"dependency_id": dependency_id, "dependency_state": dependency_state.value},
        )


def _refresh_workflow_state(conn: Any, workflow_id: str) -> None:
    rows = conn.execute("select state from tasks where workflow_id = %s", (workflow_id,)).fetchall()
    if not rows:
        return
    states = {TaskState(row["state"]) for row in rows}
    if states == {TaskState.DONE}:
        next_state = WorkflowState.DONE
    elif TaskState.FAILED in states:
        next_state = WorkflowState.FAILED
    elif TaskState.BLOCKED in states:
        next_state = WorkflowState.BLOCKED
    elif TaskState.AWAITING_APPROVAL in states:
        next_state = WorkflowState.AWAITING_APPROVAL
    elif all(state in TERMINAL_TASK_STATES for state in states):
        next_state = WorkflowState.DONE
    else:
        next_state = WorkflowState.RUNNING
    workflow = conn.execute(
        "select state from workflows where id = %s for update", (workflow_id,)
    ).fetchone()
    if workflow and workflow["state"] != next_state.value:
        conn.execute(
            "update workflows set state = %s, updated_at = now() where id = %s",
            (next_state.value, workflow_id),
        )
        append_event(
            conn,
            event_type="workflow.transitioned",
            workflow_id=workflow_id,
            from_state=workflow["state"],
            to_state=next_state.value,
        )
        if next_state in {
            WorkflowState.DONE,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
            WorkflowState.ABANDONED,
        }:
            emit(
                Notification(
                    kind=f"workflow.{next_state.value}",
                    workflow_id=workflow_id,
                    message=f"Workflow {workflow_id} transitioned to {next_state.value}",
                )
            )

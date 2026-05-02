from __future__ import annotations

from typing import Any

from pgloom.db.json import jsonb
from pgloom.db.postgres import connect
from pgloom.events import append_event
from pgloom.ids import new_id
from pgloom.notifications import Notification, emit
from pgloom.states import ApprovalState, TaskState


def request_approval(
    *,
    workflow_id: str,
    task_id: str | None,
    domain: str,
    prompt: str,
    expires_at: Any | None = None,
    database_url: str | None = None,
) -> dict[str, Any]:
    approval_id = new_id("approval")
    with connect(database_url) as conn, conn.transaction():
        row = conn.execute(
            """
            insert into approvals(id, workflow_id, task_id, domain, state, prompt, expires_at)
            values (%s, %s, %s, %s, %s, %s, %s)
            returning *
            """,
            (
                approval_id,
                workflow_id,
                task_id,
                domain,
                ApprovalState.PENDING.value,
                prompt,
                expires_at,
            ),
        ).fetchone()
        assert row is not None
        append_event(
            conn, event_type="approval.requested", workflow_id=workflow_id, task_id=task_id
        )
        emit(
            Notification(
                kind="approval.requested",
                workflow_id=workflow_id,
                task_id=task_id,
                approval_id=approval_id,
                message=prompt,
            )
        )
        return dict(row)


def decide_approval(
    approval_id: str,
    *,
    approved: bool,
    response: dict[str, Any] | None = None,
    database_url: str | None = None,
) -> None:
    state = ApprovalState.APPROVED if approved else ApprovalState.REJECTED
    with connect(database_url) as conn, conn.transaction():
        approval = conn.execute(
            "select * from approvals where id = %s for update", (approval_id,)
        ).fetchone()
        if not approval:
            return
        conn.execute(
            "update approvals set state = %s, response = %s, updated_at = now() where id = %s",
            (state.value, jsonb(response or {}), approval_id),
        )
        if approval["task_id"] and approved:
            conn.execute(
                "update tasks set state = %s, updated_at = now() where id = %s",
                (TaskState.QUEUED.value, approval["task_id"]),
            )
        elif approval["task_id"]:
            conn.execute(
                "update tasks set state = %s, blocker_code = %s, updated_at = now() where id = %s",
                (TaskState.BLOCKED.value, "approval_rejected", approval["task_id"]),
            )
        append_event(
            conn,
            event_type="approval.decided",
            workflow_id=approval["workflow_id"],
            task_id=approval["task_id"],
            to_state=state.value,
        )
        emit(
            Notification(
                kind=f"approval.{state.value}",
                workflow_id=approval["workflow_id"],
                task_id=approval["task_id"],
                approval_id=approval_id,
                message=f"Approval {approval_id} {state.value}",
            )
        )


def expire_pending_approvals(*, database_url: str | None = None, limit: int = 100) -> int:
    count = 0
    with connect(database_url) as conn, conn.transaction():
        rows = conn.execute(
            """
            select * from approvals
            where state = %s and expires_at is not null and expires_at < now()
            order by expires_at asc
            for update skip locked
            limit %s
            """,
            (ApprovalState.PENDING.value, limit),
        ).fetchall()
        for approval in rows:
            conn.execute(
                "update approvals set state = %s, updated_at = now() where id = %s",
                (ApprovalState.EXPIRED.value, approval["id"]),
            )
            if approval["task_id"]:
                conn.execute(
                    """
                    update tasks
                    set state = %s, blocker_code = %s, blocker_reason = %s, updated_at = now()
                    where id = %s
                    """,
                    (
                        TaskState.BLOCKED.value,
                        "approval_expired",
                        f"Approval {approval['id']} expired",
                        approval["task_id"],
                    ),
                )
            append_event(
                conn,
                event_type="approval.expired",
                workflow_id=approval["workflow_id"],
                task_id=approval["task_id"],
                to_state=ApprovalState.EXPIRED.value,
            )
            emit(
                Notification(
                    kind="approval.expired",
                    workflow_id=approval["workflow_id"],
                    task_id=approval["task_id"],
                    approval_id=approval["id"],
                    message=f"Approval {approval['id']} expired",
                )
            )
            count += 1
    return count

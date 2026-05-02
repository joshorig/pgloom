from __future__ import annotations

from typing import Any

from pgloom.db.json import jsonb
from pgloom.db.postgres import connect
from pgloom.events import append_event
from pgloom.ids import new_id
from pgloom.notifications import Notification, emit
from pgloom.states import WorkflowState


def create_workflow(
    *,
    domain: str,
    name: str,
    metadata: dict[str, Any] | None = None,
    database_url: str | None = None,
) -> dict[str, Any]:
    workflow_id = new_id("wf")
    with connect(database_url) as conn, conn.transaction():
        row = conn.execute(
            """
            insert into workflows(id, domain, name, state, metadata)
            values (%s, %s, %s, %s, %s)
            returning *
            """,
            (workflow_id, domain, name, WorkflowState.OPEN.value, jsonb(metadata or {})),
        ).fetchone()
        assert row is not None
        append_event(conn, event_type="workflow.created", workflow_id=workflow_id)
        return dict(row)


def get_workflow(workflow_id: str, *, database_url: str | None = None) -> dict[str, Any] | None:
    with connect(database_url) as conn:
        row = conn.execute("select * from workflows where id = %s", (workflow_id,)).fetchone()
        return dict(row) if row else None


def update_workflow_state(
    workflow_id: str, state: WorkflowState, *, database_url: str | None = None
) -> None:
    with connect(database_url) as conn, conn.transaction():
        row = conn.execute(
            "select state from workflows where id = %s for update", (workflow_id,)
        ).fetchone()
        if not row:
            return
        conn.execute(
            "update workflows set state = %s, updated_at = now() where id = %s",
            (state.value, workflow_id),
        )
        append_event(
            conn,
            event_type="workflow.transitioned",
            workflow_id=workflow_id,
            from_state=row["state"],
            to_state=state.value,
        )
        if state in {
            WorkflowState.DONE,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
            WorkflowState.ABANDONED,
        }:
            emit(
                Notification(
                    kind=f"workflow.{state.value}",
                    workflow_id=workflow_id,
                    message=f"Workflow {workflow_id} transitioned to {state.value}",
                )
            )

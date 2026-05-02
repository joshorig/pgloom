from __future__ import annotations

from typing import Any

import psycopg

from pgloom.db.json import jsonb


def append_event(
    conn: psycopg.Connection[Any],
    *,
    event_type: str,
    workflow_id: str | None = None,
    task_id: str | None = None,
    from_state: str | None = None,
    to_state: str | None = None,
    message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        """
        insert into task_events(
          task_id, workflow_id, event_type, from_state, to_state, message, metadata
        ) values (%s, %s, %s, %s, %s, %s, %s)
        """,
        (task_id, workflow_id, event_type, from_state, to_state, message, jsonb(metadata or {})),
    )

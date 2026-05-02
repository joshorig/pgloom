from __future__ import annotations

from typing import Any

import psycopg

from pgloom.db.json import jsonb
from pgloom.db.postgres import connect
from pgloom.exceptions import DuplicateExternalActionError
from pgloom.ids import new_id


def record_external_action(
    *,
    idempotency_key: str,
    action_type: str,
    result: dict[str, Any] | None = None,
    database_url: str | None = None,
) -> dict[str, Any]:
    with connect(database_url) as conn, conn.transaction():
        try:
            row = conn.execute(
                """
                insert into external_actions(id, idempotency_key, action_type, status, result)
                values (%s, %s, %s, %s, %s)
                returning *
                """,
                (new_id("action"), idempotency_key, action_type, "recorded", jsonb(result or {})),
            ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise DuplicateExternalActionError(idempotency_key) from exc
        assert row is not None
        return dict(row)

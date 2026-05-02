from __future__ import annotations

from typing import Any

from pgloom.db.json import jsonb
from pgloom.db.postgres import connect


def record_health_check(
    *,
    name: str,
    status: str,
    blocks_dispatch: bool = False,
    message: str | None = None,
    metadata: dict[str, Any] | None = None,
    database_url: str | None = None,
) -> dict[str, Any]:
    with connect(database_url) as conn, conn.transaction():
        row = conn.execute(
            """
            insert into health_checks(name, status, blocks_dispatch, message, metadata)
            values (%s, %s, %s, %s, %s)
            returning *
            """,
            (name, status, blocks_dispatch, message, jsonb(metadata or {})),
        ).fetchone()
        assert row is not None
        return dict(row)


def dispatch_blocked(*, database_url: str | None = None) -> bool:
    with connect(database_url) as conn:
        row = conn.execute(
            "select 1 from health_checks where blocks_dispatch and status != 'ok' limit 1"
        ).fetchone()
        return bool(row)

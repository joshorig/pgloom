from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from pgloom.db.json import jsonb

CORE_BLOCKERS = {
    "handler_blocked": "Task handler cannot continue.",
    "approval_rejected": "Operator rejected the approval request.",
    "attempts_exhausted": "Retry attempts were exhausted.",
    "health_check_blocked": "A blocking health check failed.",
    "quota_exhausted": "A quota bucket has no remaining capacity.",
    "budget_exhausted": "A model budget has been exhausted.",
}


class BlockerCode(BaseModel):
    code: str
    name: str
    severity: int = Field(ge=0, le=5)
    retryable: bool = True
    category: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def register_blocker(conn: Any, blocker: BlockerCode) -> None:
    conn.execute(
        """
        insert into blocker_codes(code, name, severity, retryable, category, metadata)
        values (%s, %s, %s, %s, %s, %s)
        on conflict (code) do update set
          name = excluded.name,
          severity = excluded.severity,
          retryable = excluded.retryable,
          category = excluded.category,
          metadata = excluded.metadata
        """,
        (
            blocker.code,
            blocker.name,
            blocker.severity,
            blocker.retryable,
            blocker.category,
            jsonb(blocker.metadata),
        ),
    )


def get_blocker(conn: Any, code: str) -> BlockerCode | None:
    row = conn.execute(
        """
        select code, name, severity, retryable, category, metadata
        from blocker_codes
        where code = %s
        """,
        (code,),
    ).fetchone()
    return BlockerCode(**row) if row is not None else None


def list_blockers(conn: Any, *, category: str | None = None) -> list[BlockerCode]:
    if category is None:
        rows = conn.execute(
            """
            select code, name, severity, retryable, category, metadata
            from blocker_codes
            order by code
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            select code, name, severity, retryable, category, metadata
            from blocker_codes
            where category = %s
            order by code
            """,
            (category,),
        ).fetchall()
    return [BlockerCode(**row) for row in rows]

from __future__ import annotations

from pgloom.db.postgres import connect
from pgloom.models.provider import ModelResponse


def record_usage(
    *,
    response: ModelResponse,
    profile_name: str,
    workflow_id: str | None = None,
    task_id: str | None = None,
    database_url: str | None = None,
) -> None:
    with connect(database_url) as conn, conn.transaction():
        conn.execute(
            """
            insert into model_usage(
              workflow_id, task_id, profile_name, input_tokens, output_tokens, cost_usd
            )
            values (%s, %s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                task_id,
                profile_name,
                response.input_tokens,
                response.output_tokens,
                response.cost_usd,
            ),
        )


def total_cost(*, database_url: str | None = None) -> float:
    with connect(database_url) as conn:
        row = conn.execute("select coalesce(sum(cost_usd), 0) as total from model_usage").fetchone()
        return float(row["total"] if row else 0)

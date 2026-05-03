from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from pgloom.db.json import jsonb
from pgloom.db.postgres import connect


class TokenSavingsRecord(BaseModel):
    scope_id: str
    workflow_id: str | None = None
    task_id: str | None = None
    model_usage_id: int | None = None
    profile_name: str | None = None
    input_tokens_original: int = Field(ge=0)
    input_tokens_after: int = Field(ge=0)
    tokens_saved: int = Field(ge=0)
    reduction_ratio: float = Field(ge=0, le=1)
    estimated_cost_saved_usd: float = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_accounting(self) -> TokenSavingsRecord:
        expected_saved = max(0, self.input_tokens_original - self.input_tokens_after)
        if self.tokens_saved != expected_saved:
            raise ValueError("tokens_saved must equal input_tokens_original - input_tokens_after")
        expected_ratio = (
            expected_saved / self.input_tokens_original if self.input_tokens_original else 0.0
        )
        if abs(self.reduction_ratio - expected_ratio) > 0.000001:
            raise ValueError("reduction_ratio must match tokens_saved / input_tokens_original")
        return self


def record_token_savings(
    record: TokenSavingsRecord,
    *,
    database_url: str | None = None,
) -> dict[str, Any]:
    with connect(database_url) as conn, conn.transaction():
        row = conn.execute(
            """
            insert into token_savings(
              scope_id, workflow_id, task_id, model_usage_id, profile_name,
              input_tokens_original, input_tokens_after, tokens_saved,
              reduction_ratio, estimated_cost_saved_usd, metadata
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            returning *
            """,
            (
                record.scope_id,
                record.workflow_id,
                record.task_id,
                record.model_usage_id,
                record.profile_name,
                record.input_tokens_original,
                record.input_tokens_after,
                record.tokens_saved,
                record.reduction_ratio,
                record.estimated_cost_saved_usd,
                jsonb(record.metadata),
            ),
        ).fetchone()
    if row is None:
        raise RuntimeError("token savings insert did not return a row")
    return dict(row)


def list_token_savings(
    scope_id: str,
    *,
    database_url: str | None = None,
) -> list[dict[str, Any]]:
    with connect(database_url) as conn:
        rows = conn.execute(
            """
            select *
            from token_savings
            where scope_id = %s
            order by created_at, id
            """,
            (scope_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def summarize_token_savings(
    scope_id: str,
    *,
    database_url: str | None = None,
) -> dict[str, Any]:
    with connect(database_url) as conn:
        row = conn.execute(
            """
            select
              coalesce(sum(input_tokens_original), 0) as input_tokens_original,
              coalesce(sum(input_tokens_after), 0) as input_tokens_after,
              coalesce(sum(tokens_saved), 0) as tokens_saved,
              coalesce(sum(estimated_cost_saved_usd), 0) as estimated_cost_saved_usd
            from token_savings
            where scope_id = %s
            """,
            (scope_id,),
        ).fetchone()
    original = int(row["input_tokens_original"]) if row else 0
    saved = int(row["tokens_saved"]) if row else 0
    return {
        "input_tokens_original": original,
        "input_tokens_after": int(row["input_tokens_after"]) if row else 0,
        "tokens_saved": saved,
        "reduction_ratio": saved / original if original else 0.0,
        "estimated_cost_saved_usd": float(row["estimated_cost_saved_usd"]) if row else 0.0,
    }

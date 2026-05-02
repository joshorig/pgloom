from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from pgloom.db.json import jsonb
from pgloom.db.postgres import connect
from pgloom.harness.subprocess import SubprocessResult, run_bounded


class CLIModelProfile(BaseModel):
    name: str
    command: list[str]
    timeout_seconds: float = 300
    cost_per_input_token_usd: float = 0
    cost_per_output_token_usd: float = 0
    parse_response: Literal["json", "text"] = "text"
    response_schema: dict[str, Any] | None = None


class ModelInvocationResult(BaseModel):
    text: str
    parsed: Any = None
    input_tokens: int
    output_tokens: int
    cost_usd: float
    subprocess: SubprocessResult
    metadata: dict[str, Any] = Field(default_factory=dict)


class CLIModelProvider:
    """Runs a configurable CLI as a model process and records usage."""

    def __init__(self, *, database_url: str | None = None) -> None:
        self._database_url = database_url

    def invoke(
        self,
        *,
        profile: CLIModelProfile,
        prompt: str,
        input_tokens_hint: int | None = None,
        workflow_id: str | None = None,
        task_id: str | None = None,
    ) -> ModelInvocationResult:
        completed = run_bounded(
            profile.command,
            timeout_seconds=profile.timeout_seconds,
            stdin=prompt.encode("utf-8"),
        )
        parsed: Any = None
        text = completed.stdout
        metadata: dict[str, Any] = {
            "argv": completed.argv,
            "exit_code": completed.exit_code,
            "timed_out": completed.timed_out,
            "killed": completed.killed,
            "stderr": completed.stderr,
            "token_count_source": "approximate",
        }
        if profile.parse_response == "json" and completed.stdout.strip():
            parsed = json.loads(completed.stdout)
            if isinstance(parsed, dict):
                text = str(parsed.get("text", completed.stdout))
                usage = parsed.get("usage")
                if isinstance(usage, dict):
                    metadata["token_count_source"] = "json_usage"
                    input_tokens_hint = _int_or_none(usage.get("input_tokens"))
                    output_tokens = _int_or_none(usage.get("output_tokens"))
                else:
                    output_tokens = None
            else:
                output_tokens = None
        else:
            output_tokens = None

        input_tokens = input_tokens_hint or _approx_tokens(prompt)
        final_output_tokens = output_tokens or _approx_tokens(text)
        cost = (
            input_tokens * profile.cost_per_input_token_usd
            + final_output_tokens * profile.cost_per_output_token_usd
        )
        result = ModelInvocationResult(
            text=text,
            parsed=parsed,
            input_tokens=input_tokens,
            output_tokens=final_output_tokens,
            cost_usd=cost,
            subprocess=completed,
            metadata=metadata,
        )
        self._record_usage(
            result=result,
            profile_name=profile.name,
            workflow_id=workflow_id,
            task_id=task_id,
        )
        return result

    def _record_usage(
        self,
        *,
        result: ModelInvocationResult,
        profile_name: str,
        workflow_id: str | None,
        task_id: str | None,
    ) -> None:
        with connect(self._database_url) as conn, conn.transaction():
            conn.execute(
                """
                insert into model_usage(
                  workflow_id, task_id, profile_name, input_tokens, output_tokens,
                  cost_usd, metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    workflow_id,
                    task_id,
                    profile_name,
                    result.input_tokens,
                    result.output_tokens,
                    result.cost_usd,
                    jsonb(result.metadata),
                ),
            )


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return None

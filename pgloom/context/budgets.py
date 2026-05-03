from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TokenBudget(BaseModel):
    max_input_tokens: int = Field(gt=0)
    max_output_tokens: int = Field(default=0, ge=0)
    reserve_output_tokens: int = Field(default=0, ge=0)
    strategy: str = "priority_truncate"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def usable_input_tokens(self) -> int:
        return max(1, self.max_input_tokens - self.reserve_output_tokens)


def resolve_token_budget(
    *,
    task_type: str | None = None,
    slot: str | None = None,
    model_profile: str | None = None,
    budgets: dict[str, TokenBudget | dict[str, Any]],
    default: TokenBudget | None = None,
) -> TokenBudget:
    for key in (task_type, model_profile, slot):
        if key and key in budgets:
            return _coerce_budget(budgets[key])
    if default is not None:
        return default
    raise KeyError("no token budget matched task_type, model_profile, or slot")


def _coerce_budget(value: TokenBudget | dict[str, Any]) -> TokenBudget:
    if isinstance(value, TokenBudget):
        return value
    return TokenBudget.model_validate(value)

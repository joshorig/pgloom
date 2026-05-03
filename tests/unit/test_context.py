from __future__ import annotations

import pytest

from pgloom.context import (
    ContextBuilder,
    ContextContributor,
    PromptCacheKey,
    TokenBudget,
    TokenSavingsRecord,
    count_tokens,
    resolve_token_budget,
)


def test_count_tokens_has_fallback_safe_result() -> None:
    assert count_tokens("hello world") >= 1
    assert count_tokens("") == 0


def test_context_builder_packs_by_priority_and_truncates() -> None:
    budget = TokenBudget(max_input_tokens=8)
    pack = ContextBuilder(budget=budget).pack(
        [
            ContextContributor(kind="artifact", label="low", text="low " * 20, priority=1),
            ContextContributor(kind="artifact", label="high", text="high value", priority=10),
        ]
    )

    assert "high value" in pack.packed_context
    assert count_tokens(pack.packed_context) <= budget.usable_input_tokens
    assert pack.input_tokens_original >= pack.input_tokens_packed
    assert pack.tokens_saved >= 0
    assert any(item.label == "low" and item.truncated for item in pack.contributors)


def test_prompt_cache_key_is_stable() -> None:
    key = PromptCacheKey(
        model_profile="youtube_reasoning",
        prompt_template_version="v1",
        artifact_hashes=["b", "a"],
        static_context_hash="style",
    )

    assert key.digest() == key.model_copy().digest()
    assert key.digest() == key.model_copy(update={"artifact_hashes": ["a", "b"]}).digest()


def test_resolve_token_budget_prefers_task_type() -> None:
    budget = resolve_token_budget(
        task_type="youtube.generate_channel_diagnosis",
        model_profile="youtube_reasoning",
        budgets={
            "youtube.generate_channel_diagnosis": {"max_input_tokens": 100},
            "youtube_reasoning": {"max_input_tokens": 200},
        },
    )

    assert budget.max_input_tokens == 100


def test_token_savings_record_rejects_inconsistent_accounting() -> None:
    with pytest.raises(ValueError, match="tokens_saved"):
        TokenSavingsRecord(
            scope_id="feature-1",
            input_tokens_original=100,
            input_tokens_after=90,
            tokens_saved=60,
            reduction_ratio=0.6,
        )


def test_token_savings_record_rejects_inconsistent_ratio() -> None:
    with pytest.raises(ValueError, match="reduction_ratio"):
        TokenSavingsRecord(
            scope_id="feature-1",
            input_tokens_original=100,
            input_tokens_after=40,
            tokens_saved=60,
            reduction_ratio=0.5,
        )

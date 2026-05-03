from __future__ import annotations

from collections.abc import Callable, Iterable

from pydantic import BaseModel, Field

from pgloom.context.budgets import TokenBudget
from pgloom.context.contributors import ContextContributor, PackedContributor
from pgloom.context.token_count import count_tokens

Summariser = Callable[[ContextContributor, int], str]


class ContextPack(BaseModel):
    packed_context: str
    input_tokens_original: int = Field(ge=0)
    input_tokens_packed: int = Field(ge=0)
    tokens_saved: int = Field(ge=0)
    reduction_ratio: float = Field(ge=0, le=1)
    method: str
    contributors: list[PackedContributor] = Field(default_factory=list)


class ContextBuilder:
    def __init__(
        self,
        *,
        budget: TokenBudget,
        encoder_name: str = "cl100k_base",
        summariser: Summariser | None = None,
    ) -> None:
        self.budget = budget
        self.encoder_name = encoder_name
        self.summariser = summariser

    def pack(self, contributors: Iterable[ContextContributor]) -> ContextPack:
        ordered = sorted(
            contributors,
            key=lambda item: (item.priority, item.kind, item.label),
            reverse=True,
        )
        remaining = self.budget.usable_input_tokens
        parts: list[str] = []
        packed_contributors: list[PackedContributor] = []
        original_tokens = 0
        packed_tokens = 0
        for contributor in ordered:
            tokens_original = contributor.tokens
            if tokens_original is None:
                tokens_original = count_tokens(contributor.text, encoder_name=self.encoder_name)
            original_tokens += tokens_original
            if remaining <= 0:
                packed_contributors.append(
                    _packed_contributor(contributor, tokens_original, 0, included=False)
                )
                continue
            text = contributor.text
            text_tokens = tokens_original
            truncated = False
            if text_tokens > remaining:
                text = self._fit_to_budget(contributor, remaining)
                text_tokens = count_tokens(text, encoder_name=self.encoder_name)
                truncated = text_tokens < tokens_original
            if text_tokens <= 0:
                packed_contributors.append(
                    _packed_contributor(contributor, tokens_original, 0, included=False)
                )
                continue
            fragment = f"# {contributor.label}\n{text}"
            fragment_tokens = count_tokens(fragment, encoder_name=self.encoder_name)
            if fragment_tokens > remaining:
                header = f"# {contributor.label}\n"
                header_tokens = count_tokens(header, encoder_name=self.encoder_name)
                text_budget = remaining - header_tokens
                if text_budget <= 0:
                    packed_contributors.append(
                        _packed_contributor(contributor, tokens_original, 0, included=False)
                    )
                    continue
                text = self._fit_to_budget(contributor, text_budget)
                fragment = f"{header}{text}"
                fragment_tokens = count_tokens(fragment, encoder_name=self.encoder_name)
                truncated = True
            if fragment_tokens > remaining:
                packed_contributors.append(
                    _packed_contributor(contributor, tokens_original, 0, included=False)
                )
                continue
            parts.append(fragment)
            packed_tokens += fragment_tokens
            remaining -= fragment_tokens
            packed_contributors.append(
                _packed_contributor(
                    contributor,
                    tokens_original,
                    fragment_tokens,
                    included=True,
                    truncated=truncated,
                )
            )
        tokens_saved = max(0, original_tokens - packed_tokens)
        return ContextPack(
            packed_context="\n\n".join(parts),
            input_tokens_original=original_tokens,
            input_tokens_packed=packed_tokens,
            tokens_saved=tokens_saved,
            reduction_ratio=tokens_saved / original_tokens if original_tokens else 0.0,
            method=f"context_builder:{self.budget.strategy}",
            contributors=packed_contributors,
        )

    def _fit_to_budget(self, contributor: ContextContributor, token_budget: int) -> str:
        if token_budget <= 0:
            return ""
        if self.summariser is not None:
            summary = self.summariser(contributor, token_budget)
            if count_tokens(summary, encoder_name=self.encoder_name) <= token_budget:
                return summary
        approx_chars = max(1, token_budget * 4)
        text = contributor.text[:approx_chars]
        while text and count_tokens(text, encoder_name=self.encoder_name) > token_budget:
            text = text[: max(0, len(text) - 128)]
        return text


def _packed_contributor(
    contributor: ContextContributor,
    tokens_original: int,
    tokens_packed: int,
    *,
    included: bool,
    truncated: bool = False,
) -> PackedContributor:
    return PackedContributor(
        kind=contributor.kind,
        label=contributor.label,
        artifact_id=contributor.artifact_id,
        tokens_original=tokens_original,
        tokens_packed=tokens_packed,
        included=included,
        truncated=truncated,
        metadata=contributor.metadata,
    )

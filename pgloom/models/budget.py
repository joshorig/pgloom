from __future__ import annotations


def budget_allows(*, spent: float, limit: float | None) -> bool:
    return limit is None or spent <= limit

from __future__ import annotations

from pgloom.policies import resolve_retry_policy


def test_default_retry_policy_formula() -> None:
    policy = resolve_retry_policy(None)
    assert policy.delay_for_attempt(1) == 2
    assert policy.delay_for_attempt(3) == 8
    assert policy.delay_for_attempt(10) == 60


def test_retry_policy_payload_override_preserves_defaults() -> None:
    policy = resolve_retry_policy({"retry_policy": {"base_delay_seconds": 5}})
    assert policy.base_delay_seconds == 5
    assert policy.max_attempts == 3
    assert policy.max_delay_seconds == 60

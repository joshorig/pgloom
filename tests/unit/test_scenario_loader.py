from pgloom.testing.loader import load_scenarios


def test_load_scenarios() -> None:
    scenarios = load_scenarios("scenarios/core/smoke")
    assert {scenario.id for scenario in scenarios} >= {"task_claim_once", "approval_pause_resume"}

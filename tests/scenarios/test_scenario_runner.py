from __future__ import annotations

from pgloom.db.postgres import connect
from pgloom.testing.loader import load_scenarios
from pgloom.testing.runner import run_scenario


def test_scenario_runner_persists_report(database_url: str) -> None:
    scenario = next(
        item for item in load_scenarios("scenarios/core/smoke") if item.id == "task_claim_once"
    )
    report = run_scenario(scenario, database_url=database_url)
    assert report["passed"] is True
    with connect(database_url) as conn:
        run = conn.execute(
            "select status from scenario_runs where id = %s",
            (report["scenario_run_id"],),
        ).fetchone()
        assertion_count = conn.execute(
            "select count(*) as count from scenario_assertions where scenario_run_id = %s",
            (report["scenario_run_id"],),
        ).fetchone()
    assert run == {"status": "passed"}
    assert assertion_count == {"count": 1}

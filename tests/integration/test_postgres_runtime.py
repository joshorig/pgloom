from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest

from pgloom.approvals import decide_approval, expire_pending_approvals, request_approval
from pgloom.artifacts import register_artifact
from pgloom.cli import db_check, health_run, reaper_run
from pgloom.context import TokenSavingsRecord, record_token_savings, summarize_token_savings
from pgloom.dashboard import snapshot
from pgloom.db.postgres import connect
from pgloom.exceptions import DuplicateExternalActionError
from pgloom.harness import HandlerRegistry, run_once
from pgloom.harness.result import HandlerResult
from pgloom.health import record_health_check
from pgloom.idempotency import record_external_action
from pgloom.leases import heartbeat
from pgloom.models.provider import ModelResponse
from pgloom.models.usage import record_usage, total_cost
from pgloom.notifications import Notification, set_default_sink
from pgloom.quotas import consume_quota, upsert_quota
from pgloom.reaper import reap_expired_leases, sweep
from pgloom.resources import acquire_lock
from pgloom.scheduler import due_task_ids, tick
from pgloom.slots import upsert_slot
from pgloom.states import TaskState
from pgloom.tasks import (
    claim_next,
    enqueue_task,
    list_tasks,
    retry_or_fail_task,
    transition_task,
)
from pgloom.testing.fakes import FakeHandler
from pgloom.time import utcnow
from pgloom.workers import (
    deregister_worker,
    list_active,
    register_worker,
    set_busy,
    set_idle,
)
from pgloom.workers import (
    heartbeat as worker_heartbeat,
)
from pgloom.workflows import create_workflow, get_workflow

pytestmark = pytest.mark.skipif(
    not os.environ.get("PGLOOM_TEST_DATABASE_URL"),
    reason="PGLOOM_TEST_DATABASE_URL not set",
)


def test_fake_task_completes(database_url: str) -> None:
    workflow = create_workflow(domain="test", name="runtime", database_url=database_url)
    enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="fake",
        database_url=database_url,
    )
    registry = HandlerRegistry()
    registry.register("fake.complete", FakeHandler())
    result = run_once(
        slot="fake", worker_id="test-worker", registry=registry, database_url=database_url
    )
    assert result["status"] == "done"
    assert [
        task["state"] for task in list_tasks(workflow_id=workflow["id"], database_url=database_url)
    ] == ["done"]


def test_two_workers_cannot_claim_same_task(database_url: str) -> None:
    workflow = create_workflow(domain="test", name="claim", database_url=database_url)
    task = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="concurrent",
        database_url=database_url,
    )

    def claim(worker_id: str) -> str | None:
        claimed = claim_next(slot="concurrent", worker_id=worker_id, database_url=database_url)
        return claimed["id"] if claimed else None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, ["worker-a", "worker-b"]))

    assert results.count(task["id"]) == 1
    assert results.count(None) == 1


def test_slot_concurrency_caps_in_flight(database_url: str) -> None:
    workflow = create_workflow(domain="test", name="slot-cap", database_url=database_url)
    upsert_slot(name="cap1", concurrency=1, database_url=database_url)
    first = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="cap1",
        database_url=database_url,
    )
    second = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="cap1",
        database_url=database_url,
    )
    first_claim = claim_next(slot="cap1", worker_id="worker-a", database_url=database_url)
    assert first_claim is not None
    assert first_claim["id"] == first["id"]
    assert claim_next(slot="cap1", worker_id="worker-b", database_url=database_url) is None
    transition_task(first["id"], TaskState.DONE, database_url=database_url)
    second_claim = claim_next(slot="cap1", worker_id="worker-b", database_url=database_url)
    assert second_claim is not None
    assert second_claim["id"] == second["id"]


def test_heartbeat_extends_and_reaper_requeues_expired_lease(database_url: str) -> None:
    workflow = create_workflow(domain="test", name="lease", database_url=database_url)
    task = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="lease",
        database_url=database_url,
    )
    claimed = claim_next(
        slot="lease",
        worker_id="worker-lease",
        lease_seconds=1,
        database_url=database_url,
    )
    assert claimed and claimed["id"] == task["id"]
    assert heartbeat(task["id"], "worker-lease", lease_seconds=20, database_url=database_url)
    assert reap_expired_leases(database_url=database_url) == 0
    with connect(database_url) as conn, conn.transaction():
        conn.execute("update tasks set lease_expires_at = now() - interval '1 second'")
    assert reap_expired_leases(database_url=database_url) == 1
    [row] = list_tasks(workflow_id=workflow["id"], database_url=database_url)
    assert row["state"] == "queued"


def test_transitions_emit_events_and_clear_worker(database_url: str) -> None:
    workflow = create_workflow(domain="test", name="events", database_url=database_url)
    task = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="events",
        database_url=database_url,
    )
    assert claim_next(slot="events", worker_id="worker-events", database_url=database_url)
    transition_task(task["id"], TaskState.RUNNING, database_url=database_url)
    transition_task(task["id"], TaskState.DONE, database_url=database_url)
    with connect(database_url) as conn:
        event_types = [
            row["event_type"]
            for row in conn.execute(
                "select event_type from task_events where task_id = %s order by id", (task["id"],)
            )
        ]
        worker = conn.execute(
            "select state, current_task_id from workers where id = 'worker-events'"
        ).fetchone()
    assert event_types == [
        "task.enqueued",
        "task.claimed",
        "task.transitioned",
        "task.transitioned",
    ]
    assert worker == {"state": "idle", "current_task_id": None}


def test_dependency_done_unblocks_and_failed_blocks_child(database_url: str) -> None:
    workflow = create_workflow(domain="test", name="deps", database_url=database_url)
    parent = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="deps",
        database_url=database_url,
    )
    child = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="deps",
        depends_on=[parent["id"]],
        database_url=database_url,
    )
    assert child["state"] == "blocked"
    transition_task(parent["id"], TaskState.DONE, database_url=database_url)
    states = {
        task["id"]: task["state"]
        for task in list_tasks(workflow_id=workflow["id"], database_url=database_url)
    }
    assert states[child["id"]] == "queued"

    workflow2 = create_workflow(domain="test", name="deps-fail", database_url=database_url)
    parent2 = enqueue_task(
        workflow_id=workflow2["id"],
        domain="test",
        task_type="fake.complete",
        slot="deps",
        database_url=database_url,
    )
    child2 = enqueue_task(
        workflow_id=workflow2["id"],
        domain="test",
        task_type="fake.complete",
        slot="deps",
        depends_on=[parent2["id"]],
        database_url=database_url,
    )
    transition_task(parent2["id"], TaskState.FAILED, database_url=database_url)
    states = {
        task["id"]: task
        for task in list_tasks(workflow_id=workflow2["id"], database_url=database_url)
    }
    assert states[child2["id"]]["state"] == "blocked"
    assert states[child2["id"]]["blocker_code"] == "dependency_terminal"


def test_approvals_artifacts_idempotency_resources_quotas_and_dashboard(database_url: str) -> None:
    workflow = create_workflow(domain="test", name="ops", database_url=database_url)
    task = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="ops",
        database_url=database_url,
    )
    registry = HandlerRegistry()
    registry.register("fake.complete", FakeHandler())
    run_once(slot="ops", worker_id="worker-ops", registry=registry, database_url=database_url)
    artifact = register_artifact(
        workflow_id=workflow["id"],
        task_id=task["id"],
        artifact_type="log",
        content=b"hello",
        database_url=database_url,
    )
    assert artifact["sha256"]

    approval_workflow = create_workflow(domain="test", name="approval", database_url=database_url)
    approval_task = enqueue_task(
        workflow_id=approval_workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="approval",
        payload={"behavior": "approval"},
        database_url=database_url,
    )
    run_once(
        slot="approval",
        worker_id="worker-approval",
        registry=registry,
        database_url=database_url,
    )
    with connect(database_url) as conn:
        approval = conn.execute(
            "select id from approvals where task_id = %s", (approval_task["id"],)
        ).fetchone()
    assert approval is not None
    decide_approval(approval["id"], approved=True, database_url=database_url)
    [approved_task] = list_tasks(workflow_id=approval_workflow["id"], database_url=database_url)
    assert approved_task["state"] == "queued"

    record_external_action(idempotency_key="k1", action_type="demo", database_url=database_url)
    with pytest.raises(DuplicateExternalActionError):
        record_external_action(idempotency_key="k1", action_type="demo", database_url=database_url)

    assert acquire_lock(resource_key="repo:one", owner_id="a", database_url=database_url)
    assert not acquire_lock(resource_key="repo:one", owner_id="b", database_url=database_url)
    with connect(database_url) as conn, conn.transaction():
        conn.execute("update resource_locks set expires_at = now() - interval '1 second'")
    assert acquire_lock(resource_key="repo:one", owner_id="b", database_url=database_url)

    upsert_quota("tokens", capacity=2, database_url=database_url)
    assert consume_quota("tokens", 1, database_url=database_url)
    assert consume_quota("tokens", 1, database_url=database_url)
    assert not consume_quota("tokens", 1, database_url=database_url)

    record_usage(
        response=ModelResponse(text="ok", input_tokens=10, output_tokens=2, cost_usd=0.5),
        profile_name="fake",
        workflow_id=workflow["id"],
        task_id=task["id"],
        database_url=database_url,
    )
    assert total_cost(database_url=database_url) == 0.5
    shot = snapshot(database_url=database_url)
    assert shot["tasks"]
    assert shot["workers"]


def test_health_check_blocks_dispatch(database_url: str) -> None:
    workflow = create_workflow(domain="test", name="health", database_url=database_url)
    enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="health",
        database_url=database_url,
    )
    record_health_check(
        name="db",
        status="failed",
        blocks_dispatch=True,
        database_url=database_url,
    )
    assert claim_next(slot="health", worker_id="worker-health", database_url=database_url) is None


def test_resource_and_quota_payloads_gate_dispatch(database_url: str) -> None:
    workflow = create_workflow(domain="test", name="dispatch-guards", database_url=database_url)
    first = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="guarded",
        payload={"resources": ["repo:shared"]},
        database_url=database_url,
    )
    second = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="guarded",
        payload={"resources": ["repo:shared"]},
        database_url=database_url,
    )
    assert claim_next(slot="guarded", worker_id="worker-a", database_url=database_url)
    assert claim_next(slot="guarded", worker_id="worker-b", database_url=database_url) is None

    upsert_quota("dispatch", capacity=1, remaining=0, database_url=database_url)
    quota_task = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="quota",
        payload={"quotas": [{"name": "dispatch", "amount": 1}]},
        database_url=database_url,
    )
    assert claim_next(slot="quota", worker_id="worker-quota", database_url=database_url) is None
    states = {
        task["id"]: task
        for task in list_tasks(workflow_id=workflow["id"], database_url=database_url)
    }
    assert states[first["id"]]["state"] == "leased"
    assert states[second["id"]]["state"] == "queued"
    assert states[quota_task["id"]]["state"] == "blocked"
    assert states[quota_task["id"]]["blocker_code"] == "quota_exhausted"


def test_worker_timeout_requeues_task(database_url: str) -> None:
    class SlowHandler:
        def handle(self, task: dict[str, object]) -> HandlerResult:
            time.sleep(0.2)
            return HandlerResult.done()

    workflow = create_workflow(domain="test", name="timeout", database_url=database_url)
    enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="slow",
        slot="slow",
        database_url=database_url,
    )
    registry = HandlerRegistry()
    registry.register("slow", SlowHandler())
    result = run_once(
        slot="slow",
        worker_id="worker-slow",
        registry=registry,
        handler_timeout_seconds=0.01,
        database_url=database_url,
    )
    assert result["status"] == "timeout"
    [task] = list_tasks(workflow_id=workflow["id"], database_url=database_url)
    assert task["state"] == "queued"


def test_cli_helpers_db_health_and_reaper(database_url: str) -> None:
    db_check(database_url=database_url)
    health_run(name="integration", status="ok", blocks_dispatch=False)
    reaper_run(limit=5)


def test_retry_uses_policy_delay(database_url: str) -> None:
    workflow = create_workflow(domain="test", name="retry-policy", database_url=database_url)
    task = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="retry-policy",
        payload={"retry_policy": {"base_delay_seconds": 7, "max_delay_seconds": 7}},
        max_attempts=5,
        database_url=database_url,
    )
    assert claim_next(slot="retry-policy", worker_id="worker-retry", database_url=database_url)
    retry_or_fail_task(task["id"], reason="x", database_url=database_url)
    with connect(database_url) as conn:
        row = conn.execute(
            "select run_after, updated_at from tasks where id = %s", (task["id"],)
        ).fetchone()
        event = conn.execute(
            """
            select event_type, metadata from task_events
            where task_id = %s and event_type = 'task.retry_policy_applied'
            order by id desc limit 1
            """,
            (task["id"],),
        ).fetchone()
    assert row is not None
    delta = (row["run_after"] - row["updated_at"]).total_seconds()
    assert 5 <= delta <= 9
    assert event is not None
    assert event["metadata"]["policy"]["base_delay_seconds"] == 7


def test_reaper_fails_task_when_attempts_exhausted(database_url: str) -> None:
    workflow = create_workflow(domain="test", name="reaper-fail", database_url=database_url)
    parent = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="reaper-fail",
        max_attempts=1,
        database_url=database_url,
    )
    child = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="reaper-fail",
        depends_on=[parent["id"]],
        database_url=database_url,
    )
    assert claim_next(slot="reaper-fail", worker_id="worker-reaper", database_url=database_url)
    with connect(database_url) as conn, conn.transaction():
        conn.execute(
            "update tasks set lease_expires_at = now() - interval '10 seconds' where id = %s",
            (parent["id"],),
        )
    assert sweep(database_url=database_url)["leases_reaped"] == 1
    tasks = {
        task["id"]: task
        for task in list_tasks(workflow_id=workflow["id"], database_url=database_url)
    }
    assert tasks[parent["id"]]["state"] == "failed"
    assert tasks[child["id"]]["state"] == "blocked"
    with connect(database_url) as conn:
        event = conn.execute(
            """
            select to_state from task_events
            where task_id = %s and event_type = 'task.lease_expired'
            """,
            (parent["id"],),
        ).fetchone()
    assert event == {"to_state": "failed"}


def test_approval_expires_and_blocks_task(database_url: str) -> None:
    workflow = create_workflow(domain="test", name="approval-expiry", database_url=database_url)
    task = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="approval-expiry",
        database_url=database_url,
    )
    transition_task(task["id"], TaskState.AWAITING_APPROVAL, database_url=database_url)
    approval = request_approval(
        workflow_id=workflow["id"],
        task_id=task["id"],
        domain="test",
        prompt="approve",
        expires_at=utcnow() - timedelta(minutes=1),
        database_url=database_url,
    )
    assert expire_pending_approvals(database_url=database_url) == 1
    with connect(database_url) as conn:
        approval_row = conn.execute(
            "select state from approvals where id = %s", (approval["id"],)
        ).fetchone()
        event = conn.execute(
            """
            select event_type from task_events
            where task_id = %s and event_type = 'approval.expired'
            """,
            (task["id"],),
        ).fetchone()
    [task_row] = list_tasks(workflow_id=workflow["id"], database_url=database_url)
    assert approval_row == {"state": "expired"}
    assert task_row["state"] == "blocked"
    assert task_row["blocker_code"] == "approval_expired"
    assert event == {"event_type": "approval.expired"}


def test_workflow_done_when_all_tasks_done(database_url: str) -> None:
    workflow = create_workflow(domain="test", name="done", database_url=database_url)
    tasks = [
        enqueue_task(
            workflow_id=workflow["id"],
            domain="test",
            task_type="fake.complete",
            slot="aggregate",
            database_url=database_url,
        )
        for _ in range(3)
    ]
    for task in tasks:
        transition_task(task["id"], TaskState.DONE, database_url=database_url)
    workflow_row = get_workflow(workflow["id"], database_url=database_url)
    assert workflow_row is not None
    assert workflow_row["state"] == "done"
    with connect(database_url) as conn:
        event = conn.execute(
            """
            select event_type from task_events
            where workflow_id = %s and event_type = 'workflow.transitioned' and to_state = 'done'
            """,
            (workflow["id"],),
        ).fetchone()
    assert event is not None


def test_workflow_failed_when_any_task_failed(database_url: str) -> None:
    workflow = create_workflow(domain="test", name="failed", database_url=database_url)
    failed_task = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="aggregate",
        database_url=database_url,
    )
    enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="aggregate",
        database_url=database_url,
    )
    transition_task(failed_task["id"], TaskState.FAILED, database_url=database_url)
    workflow_row = get_workflow(workflow["id"], database_url=database_url)
    assert workflow_row is not None
    assert workflow_row["state"] == "failed"


def test_workflow_blocked_aggregates_when_no_failure(database_url: str) -> None:
    workflow = create_workflow(domain="test", name="blocked", database_url=database_url)
    blocked_task = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="aggregate",
        database_url=database_url,
    )
    transition_task(blocked_task["id"], TaskState.BLOCKED, database_url=database_url)
    workflow_row = get_workflow(workflow["id"], database_url=database_url)
    assert workflow_row is not None
    assert workflow_row["state"] == "blocked"


def test_workflow_awaiting_approval_aggregates(database_url: str) -> None:
    workflow = create_workflow(domain="test", name="awaiting", database_url=database_url)
    approval_task = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="aggregate",
        database_url=database_url,
    )
    transition_task(approval_task["id"], TaskState.AWAITING_APPROVAL, database_url=database_url)
    workflow_row = get_workflow(workflow["id"], database_url=database_url)
    assert workflow_row is not None
    assert workflow_row["state"] == "awaiting_approval"


def test_workflow_done_emits_notification(database_url: str) -> None:
    class RecordingSink:
        def __init__(self) -> None:
            self.notifications: list[Notification] = []

        def emit(self, notification: Notification) -> None:
            self.notifications.append(notification)

    sink = RecordingSink()
    set_default_sink(sink)
    workflow = create_workflow(domain="test", name="notify", database_url=database_url)
    task = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="notify",
        database_url=database_url,
    )
    transition_task(task["id"], TaskState.DONE, database_url=database_url)
    assert any(
        item.kind == "workflow.done" and item.workflow_id == workflow["id"]
        for item in sink.notifications
    )


def test_scheduler_due_task_promotion(database_url: str) -> None:
    workflow = create_workflow(domain="test", name="scheduler", database_url=database_url)
    future = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="scheduler",
        run_after=utcnow() + timedelta(days=1),
        database_url=database_url,
    )
    due = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="scheduler",
        run_after=utcnow() - timedelta(minutes=1),
        database_url=database_url,
    )
    with connect(database_url) as conn:
        assert due_task_ids(conn, slot="scheduler") == [due["id"]]
        assert tick(conn, slot="scheduler") == 1
    assert future["id"] != due["id"]


def test_worker_lifecycle(database_url: str) -> None:
    with connect(database_url) as conn, conn.transaction():
        info = register_worker(conn, worker_id="worker-life", slot="life")
        assert info.state == "idle"
        set_busy(conn, worker_id="worker-life", task_id="task_demo")
        worker_heartbeat(conn, worker_id="worker-life")
        busy = conn.execute(
            "select state, current_task_id from workers where id = 'worker-life'"
        ).fetchone()
        assert busy == {"state": "busy", "current_task_id": "task_demo"}
        set_idle(conn, worker_id="worker-life")
        active = list_active(conn, slot="life", stale_after_seconds=1)
        assert [item.id for item in active] == ["worker-life"]
        conn.execute("update workers set last_heartbeat_at = now() - interval '10 seconds'")
        assert list_active(conn, slot="life", stale_after_seconds=1) == []
        assert deregister_worker(conn, worker_id="worker-life")


def test_token_savings_ledger_round_trip(database_url: str) -> None:
    workflow = create_workflow(domain="test", name="token-savings", database_url=database_url)
    task = enqueue_task(
        workflow_id=workflow["id"],
        domain="test",
        task_type="fake.complete",
        slot="tokens",
        database_url=database_url,
    )
    row = record_token_savings(
        TokenSavingsRecord(
            scope_id="feature-1",
            workflow_id=workflow["id"],
            task_id=task["id"],
            profile_name="fake",
            input_tokens_original=100,
            input_tokens_after=40,
            tokens_saved=60,
            reduction_ratio=0.6,
            estimated_cost_saved_usd=0.001,
            metadata={"method": "unit", "role": "test"},
        ),
        database_url=database_url,
    )

    assert row["scope_id"] == "feature-1"
    summary = summarize_token_savings("feature-1", database_url=database_url)
    assert summary["tokens_saved"] == 60
    assert summary["reduction_ratio"] == 0.6

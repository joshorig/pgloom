from __future__ import annotations

from typing import Any

from pgloom.approvals import decide_approval, expire_pending_approvals
from pgloom.artifacts import register_artifact
from pgloom.db.json import jsonb
from pgloom.db.postgres import connect
from pgloom.harness.registry import HandlerRegistry
from pgloom.harness.runner import run_once
from pgloom.health import record_health_check
from pgloom.idempotency import record_external_action
from pgloom.ids import new_id
from pgloom.leases import heartbeat
from pgloom.models.provider import ModelResponse
from pgloom.models.usage import record_usage
from pgloom.quotas import consume_quota, upsert_quota
from pgloom.reaper import reap_expired_leases
from pgloom.resources import acquire_lock
from pgloom.scheduler import tick
from pgloom.slots import upsert_slot
from pgloom.states import TaskState
from pgloom.tasks import claim_next, enqueue_task, list_tasks, transition_task
from pgloom.testing.fakes import FakeHandler
from pgloom.testing.scenario import Scenario
from pgloom.workflows import create_workflow


def run_scenario(scenario: Scenario, *, database_url: str | None = None) -> dict[str, Any]:
    scenario_run_id = new_id("scenario_run")
    with connect(database_url) as conn, conn.transaction():
        conn.execute("delete from health_checks")
        conn.execute(
            """
            insert into scenario_runs(id, scenario_id, status)
            values (%s, %s, %s)
            """,
            (scenario_run_id, scenario.id, "running"),
        )
    workflow = create_workflow(domain="scenario", name=scenario.id, database_url=database_url)
    default_slot = f"scenario-{scenario.id}-{workflow['id']}"
    refs: dict[str, str] = {}
    slot_aliases: dict[str, str] = {}
    flags: dict[str, bool] = {}
    registry = HandlerRegistry()
    registry.register("fake.complete", FakeHandler())
    for step in scenario.steps:
        action = step.get("action")
        raw_slot = str(step.get("slot", "fake"))
        slot = default_slot if raw_slot == "fake" else slot_aliases.get(raw_slot, raw_slot)
        if action == "enqueue_task":
            task = enqueue_task(
                workflow_id=workflow["id"],
                domain="scenario",
                task_type=step.get("task_type", "fake.complete"),
                slot=slot,
                payload=step.get("payload", {}),
                depends_on=[refs[item] for item in step.get("depends_on", [])],
                database_url=database_url,
            )
            if step.get("as"):
                refs[str(step["as"])] = task["id"]
        elif action == "run_once":
            run_once(
                slot=slot,
                worker_id="scenario-worker",
                registry=registry,
                database_url=database_url,
            )
        elif action == "claim":
            claimed_task = claim_next(
                slot=slot,
                worker_id=str(step.get("worker_id", "scenario-worker")),
                lease_seconds=int(step.get("lease_seconds", 300)),
                database_url=database_url,
            )
            if claimed_task and step.get("as"):
                refs[str(step["as"])] = claimed_task["id"]
            elif step.get("as"):
                flags[f"{step['as']}_blocked"] = True
        elif action == "heartbeat":
            heartbeat(
                refs[str(step["task"])],
                str(step.get("worker_id", "scenario-worker")),
                lease_seconds=int(step.get("lease_seconds", 300)),
                database_url=database_url,
            )
        elif action == "expire_task_lease":
            with connect(database_url) as conn, conn.transaction():
                conn.execute(
                    "update tasks set lease_expires_at = now() - interval '1 second' where id = %s",
                    (refs[str(step["task"])],),
                )
        elif action == "reap_expired_leases":
            reap_expired_leases(database_url=database_url)
        elif action == "transition_task":
            transition_task(
                refs[str(step["task"])],
                TaskState(str(step["state"])),
                database_url=database_url,
            )
        elif action == "decide_pending_approval":
            with connect(database_url) as conn:
                approval = conn.execute(
                    """
                    select id from approvals
                    where workflow_id = %s and state = 'pending'
                    order by created_at desc
                    limit 1
                    """,
                    (workflow["id"],),
                ).fetchone()
            if approval:
                decide_approval(
                    approval["id"],
                    approved=bool(step.get("approved", True)),
                    database_url=database_url,
                )
        elif action == "register_artifact":
            register_artifact(
                workflow_id=workflow["id"],
                task_id=refs.get(str(step.get("task"))),
                artifact_type=str(step.get("artifact_type", "log")),
                content=str(step.get("content", "")).encode("utf-8"),
                database_url=database_url,
            )
        elif action == "record_health_check":
            record_health_check(
                name=str(step.get("name", "scenario")),
                status=str(step.get("status", "ok")),
                blocks_dispatch=bool(step.get("blocks_dispatch", False)),
                database_url=database_url,
            )
        elif action == "clear_health_checks":
            with connect(database_url) as conn, conn.transaction():
                conn.execute("delete from health_checks")
        elif action == "upsert_slot":
            raw_name = str(step["name"])
            slot_name = default_slot if raw_name == "fake" else f"{raw_name}-{workflow['id']}"
            slot_aliases[raw_name] = slot_name
            upsert_slot(
                name=slot_name,
                concurrency=int(step["concurrency"]),
                enabled=bool(step.get("enabled", True)),
                metadata=dict(step.get("metadata", {})),
                database_url=database_url,
            )
        elif action == "set_task_run_after":
            with connect(database_url) as conn, conn.transaction():
                conn.execute(
                    """
                    update tasks
                    set run_after = now() + (%s * interval '1 second'), updated_at = now()
                    where id = %s
                    """,
                    (int(step["seconds_offset"]), refs[str(step["task_ref"])]),
                )
        elif action == "scheduler_tick":
            scheduler_slot = step.get("slot")
            if scheduler_slot == "fake":
                scheduler_slot = default_slot
            with connect(database_url) as conn:
                flags["scheduler_due_count"] = (
                    tick(
                        conn,
                        slot=str(scheduler_slot) if scheduler_slot else None,
                    )
                    > 0
                )
        elif action == "expire_pending_approvals":
            flags["approvals_expired"] = expire_pending_approvals(database_url=database_url) > 0
        elif action == "record_external_action":
            idempotency_key = f"{step['idempotency_key']}:{workflow['id']}"
            try:
                record_external_action(
                    idempotency_key=idempotency_key,
                    action_type=str(step.get("action_type", "scenario")),
                    database_url=database_url,
                )
            except Exception:
                if step.get("expect_duplicate"):
                    flags["duplicate_prevented"] = True
                else:
                    raise
        elif action == "acquire_resource_lock":
            flags[str(step.get("flag", "resource_lock_acquired"))] = acquire_lock(
                resource_key=str(step["resource_key"]),
                owner_id=str(step.get("owner_id", "scenario")),
                database_url=database_url,
            )
        elif action == "upsert_quota":
            upsert_quota(
                str(step["name"]),
                capacity=float(step["capacity"]),
                remaining=float(step.get("remaining", step["capacity"])),
                database_url=database_url,
            )
        elif action == "consume_quota":
            flags[str(step.get("flag", "quota_consumed"))] = consume_quota(
                str(step["name"]),
                float(step.get("amount", 1)),
                database_url=database_url,
            )
        elif action == "record_model_usage":
            record_usage(
                response=ModelResponse(
                    text=str(step.get("text", "ok")),
                    input_tokens=int(step.get("input_tokens", 1)),
                    output_tokens=int(step.get("output_tokens", 1)),
                    cost_usd=float(step.get("cost_usd", 0)),
                ),
                profile_name=str(step.get("profile_name", "fake")),
                workflow_id=workflow["id"],
                task_id=refs.get(str(step.get("task"))),
                database_url=database_url,
            )
    tasks = list_tasks(workflow_id=workflow["id"], database_url=database_url)
    passed = True
    messages: list[str] = []
    for assertion in scenario.assertions:
        assertion_passed = True
        assertion_message: str | None = None
        if assertion.get("type") == "task_state_count":
            count = sum(1 for task in tasks if task["state"] == assertion["state"])
            if count != int(assertion["count"]):
                passed = False
                assertion_passed = False
                assertion_message = (
                    f"expected {assertion['count']} {assertion['state']} tasks, got {count}"
                )
        elif assertion.get("type") == "artifact_count":
            with connect(database_url) as conn:
                row = conn.execute(
                    "select count(*) as count from artifacts where workflow_id = %s",
                    (workflow["id"],),
                ).fetchone()
            count = int(row["count"] if row else 0)
            if count != int(assertion["count"]):
                passed = False
                assertion_passed = False
                assertion_message = f"expected {assertion['count']} artifacts, got {count}"
        elif assertion.get("type") == "approval_state_count":
            with connect(database_url) as conn:
                row = conn.execute(
                    """
                    select count(*) as count from approvals
                    where workflow_id = %s and state = %s
                    """,
                    (workflow["id"], assertion["state"]),
                ).fetchone()
            count = int(row["count"] if row else 0)
            if count != int(assertion["count"]):
                passed = False
                assertion_passed = False
                assertion_message = (
                    f"expected {assertion['count']} {assertion['state']} approvals, got {count}"
                )
        elif assertion.get("type") == "event_type_count":
            with connect(database_url) as conn:
                row = conn.execute(
                    """
                    select count(*) as count from task_events
                    where workflow_id = %s and event_type = %s
                    """,
                    (workflow["id"], assertion["event_type"]),
                ).fetchone()
            count = int(row["count"] if row else 0)
            if count != int(assertion["count"]):
                passed = False
                assertion_passed = False
                assertion_message = (
                    f"expected {assertion['count']} {assertion['event_type']} events, got {count}"
                )
        elif assertion.get("type") == "flag":
            value = bool(flags.get(str(assertion["name"])))
            if value != bool(assertion["value"]):
                passed = False
                assertion_passed = False
                assertion_message = f"expected flag {assertion['name']} to be {assertion['value']}"
        elif assertion.get("type") == "model_usage_count":
            with connect(database_url) as conn:
                row = conn.execute(
                    "select count(*) as count from model_usage where workflow_id = %s",
                    (workflow["id"],),
                ).fetchone()
            count = int(row["count"] if row else 0)
            if count != int(assertion["count"]):
                passed = False
                assertion_passed = False
                assertion_message = f"expected {assertion['count']} model usage rows, got {count}"
        if assertion_message:
            messages.append(assertion_message)
        with connect(database_url) as conn, conn.transaction():
            conn.execute(
                """
                insert into scenario_assertions(
                  scenario_run_id, assertion_key, passed, message
                ) values (%s, %s, %s, %s)
                """,
                (
                    scenario_run_id,
                    str(assertion.get("type", "unknown")),
                    assertion_passed,
                    assertion_message,
                ),
            )
    report = {"scenario_id": scenario.id, "passed": passed, "messages": messages}
    with connect(database_url) as conn, conn.transaction():
        conn.execute(
            """
            update scenario_runs
            set status = %s, report = %s, finished_at = now()
            where id = %s
            """,
            ("passed" if passed else "failed", jsonb(report), scenario_run_id),
        )
    return {**report, "scenario_run_id": scenario_run_id, "tasks": tasks}

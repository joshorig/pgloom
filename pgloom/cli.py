from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich import print

from pgloom.config import get_settings
from pgloom.dashboard import snapshot
from pgloom.db.migrations import check, migrate, reset
from pgloom.harness.registry import HandlerRegistry
from pgloom.harness.runner import run_once
from pgloom.health import record_health_check
from pgloom.reaper import sweep
from pgloom.tasks import enqueue_task, get_task, list_tasks
from pgloom.testing.fakes import FakeHandler
from pgloom.testing.loader import load_scenarios
from pgloom.testing.runner import run_scenario
from pgloom.workflows import create_workflow

app = typer.Typer(help="Postgres-backed reusable orchestration runtime.")
db_app = typer.Typer()
workflow_app = typer.Typer()
task_app = typer.Typer()
worker_app = typer.Typer()
scenario_app = typer.Typer()
dashboard_app = typer.Typer()
app.add_typer(db_app, name="db")
app.add_typer(workflow_app, name="workflow")
app.add_typer(task_app, name="task")
app.add_typer(worker_app, name="worker")
app.add_typer(scenario_app, name="scenario")
app.add_typer(dashboard_app, name="dashboard")


@db_app.command("migrate")
def db_migrate(database_url: Annotated[str | None, typer.Option()] = None) -> None:
    applied = migrate(database_url)
    print({"applied": applied})


@db_app.command("check")
def db_check(database_url: Annotated[str | None, typer.Option()] = None) -> None:
    result = check(database_url)
    print(result)
    if not result["ok"]:
        raise typer.Exit(1)


@db_app.command("reset")
def db_reset(
    yes: Annotated[bool, typer.Option("--yes", help="Confirm destructive reset")] = False,
    database_url: Annotated[str | None, typer.Option()] = None,
) -> None:
    if not yes:
        print({"ok": False, "error": "refusing destructive reset without --yes"})
        raise typer.Exit(1)
    print({"applied": reset(database_url)})


@workflow_app.command("create")
def workflow_create(domain: str, name: str) -> None:
    print(create_workflow(domain=domain, name=name))


@task_app.command("enqueue")
def task_enqueue(
    workflow_id: str,
    slot: str,
    task_type: str,
    domain: str = "default",
    payload: str = "{}",
) -> None:
    data: dict[str, Any] = json.loads(payload)
    print(
        enqueue_task(
            workflow_id=workflow_id, domain=domain, task_type=task_type, slot=slot, payload=data
        )
    )


@task_app.command("list")
def task_list(workflow_id: str | None = None) -> None:
    print(list_tasks(workflow_id=workflow_id))


@task_app.command("show")
def task_show(task_id: str) -> None:
    task = get_task(task_id)
    if task is None:
        print({"ok": False, "error": "task not found", "task_id": task_id})
        raise typer.Exit(1)
    print(task)


@worker_app.command("run-once")
def worker_run_once(slot: str, worker_id: str | None = None) -> None:
    settings = get_settings()
    registry = HandlerRegistry()
    registry.register("fake.complete", FakeHandler())
    print(run_once(slot=slot, worker_id=worker_id or settings.worker_id, registry=registry))


@dashboard_app.command("snapshot")
def dashboard_snapshot() -> None:
    print(snapshot())


@app.command("reaper")
def reaper_run(limit: int = 100) -> None:
    print(sweep(limit=limit))


@app.command("health")
def health_run(name: str, status: str = "ok", blocks_dispatch: bool = False) -> None:
    row = record_health_check(name=name, status=status, blocks_dispatch=blocks_dispatch)
    print(row)
    if status != "ok" and blocks_dispatch:
        raise typer.Exit(1)


@scenario_app.command("run")
def scenario_run(path: Path) -> None:
    reports = [run_scenario(scenario) for scenario in load_scenarios(path)]
    print(reports)
    if not all(report["passed"] for report in reports):
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

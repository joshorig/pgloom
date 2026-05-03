from __future__ import annotations

from importlib import resources
from typing import Any

from pgloom.db.postgres import connect

REQUIRED_TABLES = {
    "workflows",
    "tasks",
    "task_dependencies",
    "task_events",
    "artifacts",
    "approvals",
    "workers",
    "slots",
    "health_checks",
    "model_profiles",
    "model_usage",
    "external_actions",
    "resource_locks",
    "quota_buckets",
    "scenario_runs",
    "scenario_assertions",
    "memory_entries",
    "blocker_codes",
    "token_savings",
}


def _schema_files() -> list[Any]:
    schema = resources.files("pgloom.db.schema")
    return sorted(path for path in schema.iterdir() if path.name.endswith(".sql"))


def migrate(database_url: str | None = None) -> list[str]:
    applied: list[str] = []
    with connect(database_url) as conn:
        with conn.transaction():
            conn.execute(
                """
                create table if not exists schema_migrations (
                  version text primary key,
                  applied_at timestamptz not null default now()
                )
                """
            )
            existing = {
                row["version"] for row in conn.execute("select version from schema_migrations")
            }
            for path in _schema_files():
                if path.name in existing:
                    continue
                sql = path.read_text(encoding="utf-8")
                conn.execute(sql)
                conn.execute("insert into schema_migrations(version) values (%s)", (path.name,))
                applied.append(path.name)
    return applied


def check(database_url: str | None = None) -> dict[str, Any]:
    with connect(database_url) as conn:
        conn.execute("select 1")
        rows = conn.execute(
            """
            select table_name
            from information_schema.tables
            where table_schema = 'public'
            """
        ).fetchall()
    present = {str(row["table_name"]) for row in rows}
    missing = sorted(REQUIRED_TABLES - present)
    return {"ok": not missing, "tables": len(REQUIRED_TABLES - set(missing)), "missing": missing}


def reset(database_url: str | None = None) -> list[str]:
    with connect(database_url) as conn, conn.transaction():
        conn.execute("drop schema public cascade")
        conn.execute("create schema public")
    return migrate(database_url)

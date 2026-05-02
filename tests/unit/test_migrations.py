from __future__ import annotations

from importlib import resources

from pgloom.blockers import BlockerCode, get_blocker, list_blockers, register_blocker
from pgloom.db.postgres import connect


def test_hot_path_index_migration_exists() -> None:
    sql = resources.files("pgloom.db.schema").joinpath("003_indexes.sql").read_text()
    assert "idx_task_dependencies_depends_on" in sql
    assert "idx_resource_locks_expires_at" in sql


def test_memory_and_blocker_migrations_exist() -> None:
    memory_sql = resources.files("pgloom.db.schema").joinpath("005_memory.sql").read_text()
    blocker_sql = (
        resources.files("pgloom.db.schema").joinpath("006_blocker_registry.sql").read_text()
    )
    assert "memory_entries" in memory_sql
    assert "blocker_codes" in blocker_sql


def test_blocker_registry_round_trip(database_url: str) -> None:
    blocker = BlockerCode(
        code="tier0.operator",
        name="Operator escalation",
        severity=0,
        retryable=False,
        category="operator",
        metadata={"owner": "ops"},
    )
    with connect(database_url) as conn, conn.transaction():
        register_blocker(conn, blocker)
        assert get_blocker(conn, "tier0.operator") == blocker
        assert list_blockers(conn, category="operator") == [blocker]

from __future__ import annotations

from typing import Any

import psycopg

from pgloom.dashboard import DashboardSection, register_collector, snapshot


def test_dashboard_snapshot_includes_registered_collectors(database_url: str) -> None:
    class FakeCollector:
        def collect(self, conn: psycopg.Connection[dict[str, Any]]) -> DashboardSection:
            conn.execute("select 1")
            return DashboardSection(key="fake", title="Fake", data={"ok": True})

    register_collector(FakeCollector())
    data = snapshot(database_url=database_url)
    assert data["fake"] == {"ok": True}
    assert any(section["key"] == "fake" for section in data["sections"])

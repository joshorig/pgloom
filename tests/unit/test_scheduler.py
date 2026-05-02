from __future__ import annotations

from pgloom.scheduler import due_task_ids, tick


class FakeRows:
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self._rows = rows

    def fetchall(self) -> list[dict[str, str]]:
        return self._rows


class FakeConn:
    def __init__(self) -> None:
        self.queries: list[tuple[str, tuple[object, ...]]] = []

    def execute(self, query: str, params: tuple[object, ...]) -> FakeRows:
        self.queries.append((query, params))
        return FakeRows([{"id": "task_1"}])


def test_scheduler_queries_due_tasks() -> None:
    conn = FakeConn()
    assert due_task_ids(conn, slot="fake", limit=5) == ["task_1"]
    assert "run_after <= now()" in conn.queries[0][0]
    assert conn.queries[0][1] == ("fake", 5)
    assert tick(conn, slot="fake") == 1

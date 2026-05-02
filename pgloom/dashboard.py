from __future__ import annotations

from typing import Any, Protocol

import psycopg
from pydantic import BaseModel

from pgloom.db.postgres import connect


class DashboardSection(BaseModel):
    key: str
    title: str
    data: Any


class DashboardCollector(Protocol):
    def collect(self, conn: psycopg.Connection[dict[str, Any]]) -> DashboardSection: ...


_collectors: list[DashboardCollector] = []


def register_collector(collector: DashboardCollector) -> None:
    _collectors.append(collector)


def snapshot(*, database_url: str | None = None) -> dict[str, Any]:
    with connect(database_url) as conn:

        def counts(table: str) -> list[dict[str, Any]]:
            return [
                dict(row)
                for row in conn.execute(f"select state, count(*) from {table} group by state")
            ]

        recent_events = [
            dict(row)
            for row in conn.execute(
                """
                select id, workflow_id, task_id, event_type, from_state, to_state,
                       message, created_at
                from task_events
                order by created_at desc, id desc
                limit 50
                """
            )
        ]
        blockers = [
            dict(row)
            for row in conn.execute(
                """
                select id, workflow_id, task_type, blocker_code, blocker_reason
                from tasks where state = 'blocked'
                order by updated_at desc
                limit 50
                """
            )
        ]
        task_counts = counts("tasks")
        workflow_counts = counts("workflows")
        approval_counts = counts("approvals")
        data = {
            "tasks": task_counts,
            "tasks_by_state": task_counts,
            "workflows": workflow_counts,
            "workflows_by_state": workflow_counts,
            "workers": [
                dict(row) for row in conn.execute("select * from workers order by id limit 50")
            ],
            "approvals": approval_counts,
            "approvals_by_state": approval_counts,
            "blockers": blockers,
            "recent_events": recent_events,
            "model_usage_24h": [
                dict(row)
                for row in conn.execute(
                    """
                    select profile_name, sum(input_tokens) as input_tokens,
                           sum(output_tokens) as output_tokens, sum(cost_usd) as cost_usd
                    from model_usage
                    where created_at >= now() - interval '24 hours'
                    group by profile_name
                    order by profile_name
                    """
                )
            ],
        }
        sections = []
        for collector in _collectors:
            section = collector.collect(conn)
            sections.append(section.model_dump())
            data[section.key] = section.data
        data["sections"] = sections
        return data

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

from pgloom.db.migrations import migrate
from pgloom.db.postgres import connect
from pgloom.notifications import NullNotificationSink, set_default_sink


@pytest.fixture(autouse=True)
def reset_notifications() -> Iterator[None]:
    set_default_sink(NullNotificationSink())
    yield
    set_default_sink(NullNotificationSink())


@pytest.fixture()
def database_url() -> Iterator[str]:
    url = os.environ.get("PGLOOM_TEST_DATABASE_URL")
    if not url:
        pytest.skip("PGLOOM_TEST_DATABASE_URL not set")
    migrate(url)
    with connect(url) as conn, conn.transaction():
        conn.execute(
            """
            truncate table
              scenario_assertions,
              scenario_runs,
              memory_entries,
              blocker_codes,
              token_savings,
              resource_locks,
              quota_buckets,
              external_actions,
              model_usage,
              model_profiles,
              health_checks,
              slots,
              workers,
              approvals,
              artifacts,
              task_events,
              task_dependencies,
              tasks,
              workflows
            restart identity cascade
            """
        )
    yield url

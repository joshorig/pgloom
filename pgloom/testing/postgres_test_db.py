from __future__ import annotations

import os


def test_database_url() -> str | None:
    return os.environ.get("PGLOOM_TEST_DATABASE_URL")

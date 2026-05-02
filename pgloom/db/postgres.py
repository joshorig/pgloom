from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row

from pgloom.config import get_settings


@contextmanager
def connect(database_url: str | None = None) -> Iterator[psycopg.Connection[dict[str, Any]]]:
    conn = psycopg.connect(database_url or get_settings().database_url, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()

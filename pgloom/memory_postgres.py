from __future__ import annotations

from pgloom.db.json import jsonb
from pgloom.db.postgres import connect
from pgloom.memory import MemoryEntry


class PostgresMemoryStore:
    """Persistent memory store using Postgres full-text search."""

    def __init__(self, *, database_url: str | None = None) -> None:
        self._database_url = database_url

    def put(self, entry: MemoryEntry) -> None:
        with connect(self._database_url) as conn, conn.transaction():
            conn.execute(
                """
                insert into memory_entries(workflow_id, key, value, metadata)
                values (%s, %s, %s, %s)
                on conflict (workflow_id, key) do update set
                  value = excluded.value,
                  metadata = excluded.metadata,
                  updated_at = now()
                """,
                (entry.workflow_id, entry.key, entry.value, jsonb(entry.metadata)),
            )

    def get(self, workflow_id: str, key: str) -> MemoryEntry | None:
        with connect(self._database_url) as conn:
            row = conn.execute(
                """
                select workflow_id, key, value, metadata
                from memory_entries
                where workflow_id = %s and key = %s
                """,
                (workflow_id, key),
            ).fetchone()
        return MemoryEntry(**row) if row is not None else None

    def list_for_workflow(self, workflow_id: str) -> list[MemoryEntry]:
        with connect(self._database_url) as conn:
            rows = conn.execute(
                """
                select workflow_id, key, value, metadata
                from memory_entries
                where workflow_id = %s
                order by key
                """,
                (workflow_id,),
            ).fetchall()
        return [MemoryEntry(**row) for row in rows]

    def delete(self, workflow_id: str, key: str) -> bool:
        with connect(self._database_url) as conn, conn.transaction():
            result = conn.execute(
                "delete from memory_entries where workflow_id = %s and key = %s",
                (workflow_id, key),
            )
            return result.rowcount == 1

    def search(
        self,
        workflow_id: str | None,
        query: str,
        *,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        workflow_filter = "and workflow_id = %s" if workflow_id is not None else ""
        params: tuple[object, ...]
        if workflow_id is not None:
            params = (query, workflow_id, query, limit)
        else:
            params = (query, query, limit)
        with connect(self._database_url) as conn:
            rows = conn.execute(
                f"""
                select workflow_id, key, value, metadata
                from memory_entries
                where search_vector @@ websearch_to_tsquery('english', %s)
                {workflow_filter}
                order by ts_rank_cd(search_vector, websearch_to_tsquery('english', %s)) desc, key
                limit %s
                """,
                params,
            ).fetchall()
        return [MemoryEntry(**row) for row in rows]

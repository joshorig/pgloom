from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from pgloom.config import get_settings
from pgloom.db.json import jsonb
from pgloom.db.postgres import connect
from pgloom.ids import new_id


def register_artifact(
    *,
    workflow_id: str,
    artifact_type: str,
    uri: str | None = None,
    content: bytes | None = None,
    task_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    database_url: str | None = None,
) -> dict[str, Any]:
    artifact_id = new_id("artifact")
    sha256: str | None = None
    size_bytes: int | None = None
    final_uri = uri
    if content is not None:
        sha256 = hashlib.sha256(content).hexdigest()
        size_bytes = len(content)
        root = get_settings().artifact_root
        path = Path(root) / workflow_id / f"{artifact_id}.bin"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        final_uri = str(path)
    with connect(database_url) as conn, conn.transaction():
        row = conn.execute(
            """
            insert into artifacts(
              id, workflow_id, task_id, artifact_type, uri, sha256, size_bytes, metadata
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            returning *
            """,
            (
                artifact_id,
                workflow_id,
                task_id,
                artifact_type,
                final_uri or "",
                sha256,
                size_bytes,
                jsonb(metadata or {}),
            ),
        ).fetchone()
        assert row is not None
        return dict(row)

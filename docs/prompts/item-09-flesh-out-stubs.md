# Implementor Prompt — orchestrator-core item 9: flesh out stub modules

```yaml
task_id: orchestrator-core/next-steps/item-09
title: Flesh out stub modules into real interfaces (prompts, memory, skills, scheduler, workers)
repo_path: /Volumes/devssd/repos/oss/orchestrator-core
reference_only_repo: /Volumes/devssd/orchestrator   # READ-ONLY. Do not import from. Inspect for ideas only.
python_min: "3.11"
postgres_required: true

constraints:
  - All new code must have type hints. mypy strict must pass.
  - ruff check must pass (config in pyproject.toml / .ruff.toml).
  - All Pydantic models v2 only.
  - Use `from __future__ import annotations` at the top of every new/edited .py file.
  - Use absolute imports (`from orchestrator_core...`), never relative.
  - No domain-specific names: do not introduce github / pr / worktree / braid / ffmpeg / youtube / travel / household terms.
  - Postgres remains the source of truth. New persistence goes in migrations under orchestrator_core/db/schema/.
  - Never use live external services from tests. Default to fakes / null implementations.
  - Idempotent SQL: every new schema file must be safe to re-run.
  - Do not break existing public APIs in tasks.py, harness/runner.py, reaper.py, approvals.py, workflows.py.
  - Do not delete any module listed in the spec.

verification_commands:
  lint: ".venv/bin/ruff check orchestrator_core tests"
  type: ".venv/bin/mypy orchestrator_core"
  unit: ".venv/bin/pytest tests/unit -q"
  integration: ".venv/bin/pytest tests/integration -q"   # requires ORCHESTRATOR_TEST_DATABASE_URL
  scenarios: ".venv/bin/pytest tests/scenarios -q"

definition_of_done:
  - Every module below has a real implementation, not a re-export or one-liner.
  - Every module below has a unit test covering its public surface.
  - workers.py and scheduler.py have one integration test each that uses a real Postgres DB.
  - One regression scenario YAML exercises scheduler.tick() promoting a due task.
  - lint, type, unit, integration, scenarios commands all pass.
  - No new domain-specific names. Grep `git diff --stat` shows files only under orchestrator_core/, tests/, scenarios/, and docs/.
```

## Module work items

### 1. `orchestrator_core/prompts.py` — flesh out into a registry

**Replace the entire file.** Implement an in-memory `PromptRegistry` class.

```python
# Required public surface:

class PromptTemplate(pydantic.BaseModel):
    name: str
    version: str = "1"
    template: str                       # python str.format style
    description: str | None = None
    metadata: dict[str, Any] = {}

class PromptRegistry:
    def register(self, template: PromptTemplate) -> None: ...
    def get(self, name: str, version: str | None = None) -> PromptTemplate: ...   # latest if version is None
    def list(self) -> list[PromptTemplate]: ...
    def render(self, name: str, *, version: str | None = None, **values: Any) -> str: ...

# Module-level convenience helpers that operate on a default registry:
def register_prompt(template: PromptTemplate) -> None: ...
def render_prompt(name: str, *, version: str | None = None, **values: Any) -> str: ...
```

Behavior:
- `register` overwrites identical (name, version); registering a new version of the same name keeps both.
- `get(name)` with no version returns the latest version by lexicographic compare on `version`.
- `render` looks up the template, then `template.format(**values)`. Raise `KeyError` (subclass `OrchestratorCoreError` from exceptions.py if a sensible parent exists; otherwise plain `KeyError`) on unknown name.
- No DB persistence in this iteration. Document in module docstring that downstream orchestrators may persist by extending the registry.

**Tests** (`tests/unit/test_prompts.py`, new file):
- register + get returns the registered template
- register two versions, `get(name)` returns latest
- render formats with kwargs
- render with unknown name raises
- `__all__` exports match the documented surface

---

### 2. `orchestrator_core/memory.py` — convert to a Protocol + null impl

**Replace the entire file.** Define the *interface* the spec describes; provide a no-op default.

```python
# Required public surface:

class MemoryEntry(pydantic.BaseModel):
    workflow_id: str
    key: str
    value: str
    metadata: dict[str, Any] = {}

class MemoryStore(typing.Protocol):
    def put(self, entry: MemoryEntry) -> None: ...
    def get(self, workflow_id: str, key: str) -> MemoryEntry | None: ...
    def list_for_workflow(self, workflow_id: str) -> list[MemoryEntry]: ...
    def delete(self, workflow_id: str, key: str) -> bool: ...

class NullMemoryStore:                  # implements MemoryStore
    """Default no-op store. Returns None / empty / False. Safe for tests and minimal deployments."""
    ...

class InMemoryMemoryStore:              # implements MemoryStore
    """Process-local dict-backed store. Useful for tests and single-process orchestrators."""
    ...
```

Behavior:
- `NullMemoryStore`: methods always succeed but persist nothing.
- `InMemoryMemoryStore`: dict keyed by `(workflow_id, key)`. Thread-safe with a `threading.Lock`.
- Keep the existing `MemoryRef` dataclass as a deprecated alias for `MemoryEntry` only if doing so does not break ruff; otherwise remove it (it has no callers — verified via grep).

**Tests** (`tests/unit/test_memory.py`, new file):
- NullMemoryStore returns None / empty / False for every operation
- InMemoryMemoryStore put/get/list/delete round-trip
- list_for_workflow scopes by workflow_id (entries for other workflows excluded)
- concurrent put on InMemoryMemoryStore from two threads does not lose data (use `ThreadPoolExecutor`)

---

### 3. `orchestrator_core/skills.py` — flesh out into a registry

**Replace the entire file.** Build a real registry; keep YAML loading as a populator.

```python
# Required public surface:

class Skill(pydantic.BaseModel):
    name: str
    version: str = "1"
    handler_type: str                   # the harness handler key this skill maps to
    description: str | None = None
    metadata: dict[str, Any] = {}

class SkillRegistry:
    def register(self, skill: Skill) -> None: ...
    def get(self, name: str, version: str | None = None) -> Skill: ...
    def list(self) -> list[Skill]: ...
    def for_handler_type(self, handler_type: str) -> list[Skill]: ...
    def load_yaml(self, path: str | pathlib.Path) -> int: ...   # returns count loaded

# Default module-level registry + convenience wrappers:
def register_skill(skill: Skill) -> None: ...
def get_skill(name: str, version: str | None = None) -> Skill: ...
def load_skills_config(path: str | pathlib.Path) -> int: ...   # delegates to default registry
```

YAML format:
```yaml
skills:
  - name: example
    version: "1"
    handler_type: fake
    description: Example skill
    metadata: {tags: [demo]}
```

Behavior:
- `load_yaml` raises if the file is malformed or any entry fails Pydantic validation.
- Latest-version semantics same as PromptRegistry.

**Tests** (`tests/unit/test_skills.py`, new file):
- register + get
- load_yaml from a tmp_path file with two skills loads both and registers them
- for_handler_type filters correctly
- malformed YAML raises a clear exception

---

### 4. `orchestrator_core/scheduler.py` — flesh out promotion of `run_after`

**Replace the entire file.** Implement helpers that exploit the existing `tasks.run_after` column.

```python
# Required public surface:

def due_task_ids(conn: psycopg.Connection, *, slot: str | None = None, limit: int = 100) -> list[str]:
    """Return queued task IDs whose run_after has elapsed."""

def tick(conn: psycopg.Connection, *, slot: str | None = None, limit: int = 100) -> int:
    """No-op promotion: return the count of due tasks. Tasks already become claimable
    once run_after <= now() because claim_next filters on it. This function exists to
    expose visibility ('how many tasks are ready right now?') and to provide a hook
    for future side effects like notifications. Returns the count of due tasks."""
```

Behavior:
- `due_task_ids` query: `select id from tasks where state = 'queued' and run_after <= now() [and slot = %s] order by priority desc, run_after asc limit %s`.
- `tick` calls `due_task_ids` and returns `len(...)`. Future iterations may emit events; this iteration must not.
- No new schema. No locking. Read-only query.

**Tests:**
- Unit test (`tests/unit/test_scheduler.py`) for the SQL composition (use a stub connection or a real one in conftest if simpler).
- Integration test added to `tests/integration/test_postgres_runtime.py`:
  - Enqueue task A with `run_after = now() + 1 day`
  - Enqueue task B with `run_after = now() - 1 minute`
  - `due_task_ids()` returns `[B]` only
  - `tick()` returns 1

---

### 5. `orchestrator_core/workers.py` — flesh out worker lifecycle

**Replace the entire file.** Centralize the upserts currently scattered through `tasks.py`.

```python
# Required public surface:

class WorkerInfo(pydantic.BaseModel):
    id: str
    slot: str
    state: str                    # 'idle' | 'busy' | 'offline'
    current_task_id: str | None
    last_heartbeat_at: datetime
    metadata: dict[str, Any] = {}

def register_worker(conn: psycopg.Connection, *, worker_id: str, slot: str,
                    metadata: dict[str, Any] | None = None) -> WorkerInfo: ...
def deregister_worker(conn: psycopg.Connection, *, worker_id: str) -> bool: ...
def set_idle(conn: psycopg.Connection, *, worker_id: str) -> None: ...
def set_busy(conn: psycopg.Connection, *, worker_id: str, task_id: str) -> None: ...
def list_active(conn: psycopg.Connection, *, slot: str | None = None,
                stale_after_seconds: int = 60) -> list[WorkerInfo]: ...
def heartbeat(conn: psycopg.Connection, *, worker_id: str) -> None: ...
```

Behavior:
- `register_worker` upserts on (id) and sets state='idle', last_heartbeat_at=now().
- `deregister_worker` deletes the row; returns True if a row was removed.
- `set_busy` sets state='busy', current_task_id, last_heartbeat_at=now().
- `set_idle` sets state='idle', current_task_id=NULL, last_heartbeat_at=now().
- `list_active` returns rows where last_heartbeat_at >= now() - stale_after_seconds. Optional slot filter.
- `heartbeat` updates last_heartbeat_at only.

**Refactor `tasks.py`:** the existing inline `insert into workers ...` upserts in `claim_next` and the `update workers ...` calls in transition functions must call into `workers.py`. Same SQL, just centralized. Re-export `from orchestrator_core.harness.runner import run_once` is allowed for backward compatibility but must be in addition to the lifecycle functions, not in place of them.

**Tests:**
- Unit (`tests/unit/test_workers.py`): use psycopg-mock or skip if no DB; basic round-trip is fine if DB available.
- Integration (`tests/integration/test_postgres_runtime.py` new test): register → set_busy → heartbeat → set_idle → deregister. Verify each row state via direct SQL.
- Add an integration assertion that `list_active(stale_after_seconds=1)` excludes a worker whose heartbeat is older than the threshold (use `freezegun` or a manual `update workers set last_heartbeat_at = now() - interval '10 seconds'`).

---

## Schema changes

No new tables required. If integration tests need fixtures (e.g. preloaded slots), use the existing `slots` table.

If you want to add the missing index on `task_dependencies(depends_on_task_id)` while you're in here, do it in a new migration `orchestrator_core/db/schema/003_indexes.sql` — but that's out of scope for item 9 unless trivial.

## Scenario harness changes

Add **one** new YAML scenario to exercise the scheduler:

`scenarios/core/regression/scheduler_promotes_due_task.yaml`:
- Enqueue task with `run_after` 1 hour in the future
- Call new harness action `set_task_run_after` to move it to 1 second ago
- Assert `flag.scheduler_due_count == 1` after a `scheduler_tick` action

This requires two new actions in `orchestrator_core/testing/runner.py`:
- `set_task_run_after`: takes `task_ref` and `seconds_offset`, updates the row directly
- `scheduler_tick`: calls `scheduler.tick()` and stores the count in `flags`

## Out of scope (do not do)

- DB-backed prompt persistence
- DB-backed memory persistence
- Cron / recurring schedule expressions in scheduler
- Any GitHub / PR / worktree / BRAID / FFmpeg / YouTube / travel / household integrations
- Changes to `tasks.claim_next` other than the workers.py refactor above
- Changes to the existing 9 required scenarios

## Reporting

When complete, write a short report to `docs/reports/item-09-completion.md`:
- Summary of changes per module
- Test commands run with their outputs
- Any deviations from this prompt and why
- A `git diff --stat` summary

```bash
# Final acceptance gate (must all pass):
.venv/bin/ruff check orchestrator_core tests
.venv/bin/mypy orchestrator_core
.venv/bin/pytest tests/unit -q
.venv/bin/pytest tests/integration -q
.venv/bin/pytest tests/scenarios -q
```

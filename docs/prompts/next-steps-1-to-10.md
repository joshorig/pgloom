# Implementor Prompt — orchestrator-core next steps (items 1–10)

This prompt is consumed by an implementor agent. It is self-contained: do not assume context from prior conversation. Work items are ordered; respect ordering unless explicitly told otherwise. Each work item has a rationale, exact file targets, required public surface, behavior contract, tests to add, and out-of-scope notes.

```yaml
batch_id: orchestrator-core/next-steps/1-to-10
title: Close definition-of-done gaps and harden the runtime
repo_path: /Volumes/devssd/repos/oss/orchestrator-core
reference_only_repo: /Volumes/devssd/orchestrator   # READ-ONLY. Do not import. Inspect for ideas only.
python_min: "3.11"
postgres_required: true

global_constraints:
  - All new code must have type hints. mypy strict (existing config) must continue to pass.
  - ruff check must continue to pass.
  - Pydantic v2 only.
  - `from __future__ import annotations` at the top of every new/edited .py file.
  - Absolute imports only (`from orchestrator_core...`).
  - No domain-specific names: do not introduce github / pr / worktree / braid / ffmpeg / youtube / travel / household terms anywhere in core.
  - Postgres remains the source of truth. Schema changes go in new files under orchestrator_core/db/schema/ and must be idempotent.
  - Default tests must not call live external services. Use fakes/null impls.
  - Do not break the existing public APIs of: tasks.claim_next, tasks.transition_task, tasks.retry_or_fail_task, tasks.enqueue_task, harness.runner.run_once, reaper.reap_expired_leases, approvals.request_approval, approvals.decide_approval, workflows.create_workflow.
  - Do not modify any of the 9 existing required scenarios under scenarios/core/.
  - Do not delete any module the spec lists by name.

verification_commands:
  lint: ".venv/bin/ruff check orchestrator_core tests"
  type: ".venv/bin/mypy orchestrator_core"
  unit: ".venv/bin/pytest tests/unit -q"
  integration: ".venv/bin/pytest tests/integration -q"        # requires ORCHESTRATOR_TEST_DATABASE_URL
  scenarios: ".venv/bin/pytest tests/scenarios -q"
  cli_smoke: ".venv/bin/orchestrator-core --help"

batch_definition_of_done:
  - All 10 work items below are implemented per their contracts.
  - All five verification_commands pass locally.
  - A completion report exists at docs/reports/next-steps-1-to-10-completion.md with: per-item summary, test outputs, deviations + rationale, and a `git diff --stat` summary.
  - No new mypy or ruff errors anywhere in the repo.
  - No new files outside orchestrator_core/, tests/, scenarios/, scripts/, .github/, docs/.
  - No introduction of domain-specific names (verify with: `git diff | grep -iE "github|worktree|braid|ffmpeg|youtube|travel|household"` returning no relevant matches).

ordering: |
  Implement in this order. Several items depend on earlier items.
   3 → 2 → 1 → 4 → 5 → 6 → 7 → 8 → 9 → 10
  Rationale:
  - 3 (index) is trivial and unblocks anything touching dependencies.
  - 2 (slot concurrency) modifies claim_next; do it before 1 wires the CLI surfaces that lean on it.
  - 1 (CLI verbs) lands the operator surface that 5/6/7 can then use in tests.
  - 4 (RetryPolicy wiring) and 5 (reaper terminal-fail + approval expiry) are tightly related.
  - 6 (NotificationSink) gets emitted from terminal transitions added in 4/5/7.
  - 7 (workflow aggregation tests) verifies code that already exists; do after 5 so reaper-driven failures are observable.
  - 8 (setup-report path) is trivial cleanup.
  - 9 (flesh out stub modules) is mechanical and isolated.
  - 10 (CI) wraps everything and proves the green state.
```

---

## Item 1 — Add missing CLI verbs

**Rationale.** The spec lists CLI commands `orchestrator-core db check`, `db reset --yes`, `task list`, `task show`, `reaper run`, and `health run`. None of these are wired in `orchestrator_core/cli.py`. Without `reaper run` the runtime is not operationally complete; the others are debugging essentials.

**Files to edit.**
- `orchestrator_core/cli.py` (add commands)
- `orchestrator_core/tasks.py` (already has `list_tasks`; add `get_task` if missing)
- `orchestrator_core/db/migrations.py` (add `check()` helper if missing)

**Required surface (cli.py additions).**

```python
@db_app.command("check")
def db_check(database_url: Annotated[str | None, typer.Option()] = None) -> None:
    """Verify connectivity and that all expected tables exist. Exits 1 on failure."""

@db_app.command("reset")
def db_reset(
    yes: Annotated[bool, typer.Option("--yes", help="Confirm destructive reset")] = False,
    database_url: Annotated[str | None, typer.Option()] = None,
) -> None:
    """Drop and recreate all orchestrator_core tables. Refuses without --yes."""

@task_app.command("list")
def task_list(workflow_id: str | None = None) -> None: ...

@task_app.command("show")
def task_show(task_id: str) -> None: ...

@app.command("reaper")
def reaper_run(limit: int = 100) -> None:
    """Run one reaper sweep over expired leases."""
    # Use a top-level command (not a subgroup) because `reaper run` is a single verb.
    # Acceptable alternative: a `reaper_app` subgroup with a single `run` command.

@app.command("health")
def health_run(name: str, status: str = "ok", blocks_dispatch: bool = False) -> None:
    """Record a health check row. Exits 1 if status != 'ok' and blocks_dispatch is true."""
```

**Behavior contract.**
- `db check`: try `select 1`, then assert the 16 required tables exist (`workflows`, `tasks`, `task_dependencies`, `task_events`, `artifacts`, `approvals`, `workers`, `slots`, `health_checks`, `model_profiles`, `model_usage`, `external_actions`, `resource_locks`, `quota_buckets`, `scenario_runs`, `scenario_assertions`). Print `{"ok": true, "tables": N}` on success. Exit 1 with `{"ok": false, "missing": [...]}` on failure.
- `db reset --yes`: drop all tables in dependency order (or `drop schema public cascade; create schema public;` if simpler), then run `migrate()`. Refuse without `--yes`.
- `task list`: pretty-print rows from `tasks.list_tasks(workflow_id=...)`.
- `task show <id>`: query `tasks` + last 20 `task_events` + dependencies. Print as a single dict.
- `reaper run`: call `reaper.reap_expired_leases(limit=limit)`. Print `{"reaped": N}`.
- `health run`: insert one row via `health.record_health_check(...)`. Print the inserted row.

**Tests.**
- `tests/unit/test_cli_smoke.py` (new): use `typer.testing.CliRunner` to assert `--help` text contains all the new verbs and they exit 0 on `--help`.
- Extend `tests/integration/test_postgres_runtime.py`: invoke `db_check`, `reaper_run`, `health_run` programmatically (call the underlying functions, not via subprocess) and assert side effects.

**Out of scope.** Any kind of daemon/service mode. `reaper run` runs once and exits.

---

## Item 2 — Enforce slot concurrency in `claim_next`

**Rationale.** `slots.concurrency` exists in the schema but is never read. The spec requires slot capacity be honored. Without this, a slot configured for concurrency=1 still allows N concurrent leases.

**Files to edit.**
- `orchestrator_core/tasks.py` (`claim_next`, add a check before the `update tasks set state = 'leased'` step)
- `orchestrator_core/slots.py` (add `get_slot_concurrency` helper)
- `orchestrator_core/db/schema/004_slot_defaults.sql` (new; ensure default slot rows exist if you require them — optional)
- `scenarios/core/regression/slot_concurrency_limit.yaml` (new)
- `orchestrator_core/testing/runner.py` (add `upsert_slot` action if not already supported)

**Required surface.**

```python
# slots.py
def get_slot_concurrency(conn: Any, slot: str) -> int | None:
    """Return concurrency for the given slot, or None if the slot row does not exist
    (interpreted as unlimited). Read-only query."""

def upsert_slot(conn: Any, *, name: str, concurrency: int, enabled: bool = True,
                metadata: dict[str, Any] | None = None) -> None: ...
```

**Behavior contract.** Inside `tasks.claim_next`, after the health-check guard and before `select ... for update skip locked`:

```sql
-- Pseudocode logic inside claim_next:
limit := slots.concurrency for this slot, or NULL (unlimited)
in_flight := count of tasks where slot = ? and state in ('leased','running')
if limit is not NULL and in_flight >= limit:
    return None
```

Use a single SQL statement to read both, e.g.:

```sql
select s.concurrency, (
  select count(*) from tasks t
  where t.slot = s.name and t.state in ('leased','running')
) as in_flight
from slots s where s.name = %s
```

If no `slots` row exists for the slot name, treat it as unlimited (preserves backward compatibility with all existing scenarios that don't pre-create slot rows).

**Tests.**
- Integration test in `tests/integration/test_postgres_runtime.py`:
  - `test_slot_concurrency_caps_in_flight`:
    - Upsert slot `cap1` with `concurrency=1`.
    - Enqueue two tasks on slot `cap1`.
    - First `claim_next` returns task A.
    - Second `claim_next` returns `None` (capacity reached).
    - Transition task A to `done`.
    - Third `claim_next` returns task B.
- New scenario YAML `scenarios/core/regression/slot_concurrency_limit.yaml`:
  - actions: `upsert_slot(name=cap1, concurrency=1)` → enqueue two tasks → claim → claim again → assert `flag.second_claim_blocked == true`.

**Out of scope.** Per-worker-id concurrency. Slot quotas across multiple machines (the in_flight count already covers this since it queries the DB).

---

## Item 3 — Add missing index on `task_dependencies(depends_on_task_id)`

**Rationale.** `tasks._unblock_dependents` and `tasks._block_dependents` query `task_dependencies` by `depends_on_task_id` on every parent transition. No index exists; full scan at scale.

**Files to edit.**
- `orchestrator_core/db/schema/003_indexes.sql` (new file)

**Content (idempotent SQL).**

```sql
-- 003_indexes.sql — secondary indexes for hot-path queries
create index if not exists idx_task_dependencies_depends_on
  on task_dependencies(depends_on_task_id);

-- Cleanup helper for resource_locks expiry sweeps.
create index if not exists idx_resource_locks_expires_at
  on resource_locks(expires_at);
```

**Behavior contract.** `migrate()` already iterates `orchestrator_core/db/schema/*.sql` in lexical order. Verify the new file is picked up (existing migrations machinery should handle this).

**Tests.** Extend `tests/unit/` with a tiny test that loads the SQL file and confirms it parses (read the file, assert it contains `idx_task_dependencies_depends_on`). No need for a behavioral test.

**Out of scope.** Other secondary indexes. Stick to the two listed.

---

## Item 4 — Wire `RetryPolicy` into `retry_or_fail_task`

**Rationale.** `policies.RetryPolicy` exists with `delay_for_attempt(attempt)`, but `tasks.retry_or_fail_task` (line ~265 of `tasks.py`) computes its own delay inline: `min(60, 2 ** max(int(row["attempt"]), 0))`. The policy class is dead code.

**Files to edit.**
- `orchestrator_core/policies.py` (export a default and a registry function)
- `orchestrator_core/tasks.py` (`retry_or_fail_task` reads policy)
- Add policy resolution: per task `payload.retry_policy` overrides default; otherwise use `DEFAULT_RETRY_POLICY`.

**Required surface (policies.py).**

```python
DEFAULT_RETRY_POLICY: RetryPolicy = RetryPolicy()  # max_attempts=3, base=2, max_delay=60

def resolve_retry_policy(payload: dict[str, Any] | None) -> RetryPolicy:
    """Read payload.retry_policy if present (dict with optional max_attempts,
    base_delay_seconds, max_delay_seconds) and merge over DEFAULT_RETRY_POLICY."""
```

**Behavior contract (tasks.retry_or_fail_task).**
- Read `row["payload"]`, call `resolve_retry_policy(payload)`.
- Cap attempts using `policy.max_attempts` (currently the code reads `row["max_attempts"]`; honor whichever is **smaller** to avoid widening bounds set at enqueue time).
- Compute next `run_after` as `now() + policy.delay_for_attempt(attempt)`.
- Append a `task.retry_policy_applied` event with `metadata={"policy": policy.dict_or_asdict()}` so the policy is auditable.

**Tests.**
- Unit test `tests/unit/test_policies.py` (extend):
  - Default policy formula matches `delay_for_attempt(1)=2, delay_for_attempt(3)=8, delay_for_attempt(10)=60`.
  - `resolve_retry_policy({"retry_policy": {"base_delay_seconds": 5}})` returns a policy with base=5 and other defaults preserved.
- Integration test `test_retry_uses_policy_delay`:
  - Enqueue task with `payload={"retry_policy": {"base_delay_seconds": 7, "max_delay_seconds": 7}}` and `max_attempts=5`.
  - Force a retry by calling `retry_or_fail_task(task_id, reason="x")` after one attempt.
  - Read the row and assert `run_after - updated_at` is approximately 7 seconds (use `freezegun` or compare with a tolerance window).
  - Read latest `task_events` row and assert `event_type='task.retry_policy_applied'` and `metadata.policy.base_delay_seconds == 7`.

**Out of scope.** Backoff jitter. Per-error-class policies.

---

## Item 5 — Cover the reaper terminal-fail branch and approval expiry

**Rationale.** `reaper.reap_expired_leases` already supports the terminal-fail branch (`if row["attempt"] < row["max_attempts"] else FAILED`). It is untested. The approval expiry path is missing entirely: `approvals.expires_at` exists in the schema, `ApprovalState.EXPIRED` exists in the enum, but no code transitions an approval to expired.

**Files to edit.**
- `orchestrator_core/approvals.py` (add `expire_pending_approvals`)
- `orchestrator_core/reaper.py` (extend reaper sweep to also expire approvals)
- `orchestrator_core/cli.py` (no change required if `reaper run` from item 1 already covers it)
- `tests/integration/test_postgres_runtime.py` (two new tests)

**Required surface (approvals.py addition).**

```python
def expire_pending_approvals(*, database_url: str | None = None, limit: int = 100) -> int:
    """Transition any approval rows where state='pending' AND expires_at < now()
    to state='expired'. If the approval is linked to a task, mark that task as
    blocked with blocker_code='approval_expired'. Append 'approval.expired' event.
    Return count expired."""
```

**Behavior contract (reaper).**
- Either keep `reap_expired_leases` focused on tasks and add a sibling `expire_pending_approvals` call inside `cli.reaper_run`, or have the reaper module export a `sweep()` function that does both. Pick the second option for cleaner ergonomics:

```python
# reaper.py addition
def sweep(*, database_url: str | None = None, limit: int = 100) -> dict[str, int]:
    return {
        "leases_reaped": reap_expired_leases(database_url=database_url, limit=limit),
        "approvals_expired": expire_pending_approvals(database_url=database_url, limit=limit),
    }
```

Update `cli.reaper_run` (item 1) to call `sweep` and print the dict.

**Tests.**
- `test_reaper_fails_task_when_attempts_exhausted`:
  - Enqueue task with `max_attempts=1`.
  - Claim it (attempt becomes 1).
  - Force lease expiry by `update tasks set lease_expires_at = now() - interval '10 seconds' where id = ...`.
  - Run reaper.
  - Assert task state is `failed`, not `queued`.
  - Assert event `task.lease_expired` with `to_state='failed'` exists.
  - Assert dependent tasks (if any) are blocked.

- `test_approval_expires_and_blocks_task`:
  - Create workflow + task in `awaiting_approval` state.
  - Insert approval with `expires_at = now() - interval '1 minute'`, state `pending`.
  - Call `approvals.expire_pending_approvals()`.
  - Assert approval state is `expired`.
  - Assert task state is `blocked` with `blocker_code='approval_expired'`.
  - Assert event `approval.expired` exists.

**Out of scope.** Auto-extending approval expiries. Notifications (those land in item 6).

---

## Item 6 — Implement a logging `NotificationSink`

**Rationale.** `notifications.py` defines a Protocol but no concrete implementation. Operator visibility into terminal events is required.

**Files to edit.**
- `orchestrator_core/notifications.py` (add `Notification` model, `LoggingNotificationSink`, `NullNotificationSink`, default singleton)
- `orchestrator_core/workflows.py` (emit on `update_workflow_state` reaching DONE/FAILED/CANCELLED/ABANDONED)
- `orchestrator_core/approvals.py` (emit on `request_approval` and on `decide_approval`)
- `orchestrator_core/tasks.py` (emit on terminal task states `failed`, `done` — keep volume manageable, only on transitions, not every attempt)

**Required surface.**

```python
class Notification(pydantic.BaseModel):
    kind: str                                  # e.g. "workflow.done", "approval.requested"
    workflow_id: str | None = None
    task_id: str | None = None
    approval_id: str | None = None
    message: str
    metadata: dict[str, Any] = {}
    occurred_at: datetime

class NotificationSink(typing.Protocol):
    def emit(self, notification: Notification) -> None: ...

class LoggingNotificationSink:                  # implements NotificationSink
    """Logs notifications via structlog at INFO level. Default in dev."""

class NullNotificationSink:                     # implements NotificationSink
    """Drops notifications. Used in tests by default."""

# Module-level default sink, settable for tests:
def get_default_sink() -> NotificationSink: ...
def set_default_sink(sink: NotificationSink) -> None: ...
def emit(notification: Notification) -> None: ...   # convenience: emits via default sink
```

**Behavior contract.**
- All emit calls must be wrapped in `try/except` so a sink failure never breaks a transition.
- Default sink: `LoggingNotificationSink` in dev, `NullNotificationSink` in tests. Test fixture must reset the default sink between tests (use a `pytest` fixture in `tests/conftest.py` that calls `set_default_sink(NullNotificationSink())`).
- Notifications are best-effort, not durable. Do not write to DB.

**Tests.**
- Unit test `tests/unit/test_notifications.py`:
  - `LoggingNotificationSink.emit` logs at INFO with the kind in the log line (use `caplog`).
  - `NullNotificationSink.emit` is a no-op.
  - Default sink swap works.
- Integration test `test_workflow_done_emits_notification`:
  - Use a `RecordingNotificationSink` (define inline in the test) that captures emits.
  - Set as default. Drive a workflow to DONE. Assert the recorder saw a `workflow.done` notification with the right workflow_id.

**Out of scope.** Webhook delivery. Email. Slack. Persistent queue.

---

## Item 7 — Workflow-state-aggregation tests

**Rationale.** `tasks._refresh_workflow_state` (line ~394 of `tasks.py`) already aggregates child task states into a workflow state. It is called from transition paths, but no integration test asserts the aggregation is correct.

**Files to edit.**
- `tests/integration/test_postgres_runtime.py` (add aggregation tests)

**Tests to add.**
- `test_workflow_done_when_all_tasks_done`:
  - Workflow with three tasks. Transition all three to DONE.
  - Assert workflow state is `done`.
  - Assert event `workflow.transitioned` to `done` exists.
- `test_workflow_failed_when_any_task_failed`:
  - Workflow with three tasks. Transition one to FAILED, one to DONE, leave one queued.
  - Assert workflow state is `failed`.
- `test_workflow_blocked_aggregates_when_no_failure`:
  - Workflow with two tasks. Transition one to BLOCKED, leave one queued.
  - Assert workflow state is `blocked`.
- `test_workflow_awaiting_approval_aggregates`:
  - Workflow with one task in `awaiting_approval`.
  - Assert workflow state is `awaiting_approval`.

If any test fails, **investigate `_refresh_workflow_state` carefully** before adjusting the test — the aggregation order in the function (DONE → FAILED → BLOCKED → AWAITING_APPROVAL → all-terminal → RUNNING) is explicit; tests should encode that order.

**Out of scope.** Changes to aggregation logic unless a test reveals a bug. Document any bug found in the completion report.

---

## Item 8 — Setup-report path cleanup

**Rationale.** `scripts/bootstrap_dev_env.sh` currently writes to `$ROOT/.local/setup-report.md` (correct per spec) **and** copies to `$ROOT/docs/setup-report.md` (not in spec; pollutes docs). Spec is `.local/setup-report.md`.

**Files to edit.**
- `scripts/bootstrap_dev_env.sh` (remove the `cp ... docs/setup-report.md` line)
- Delete `docs/setup-report.md` if present (it's a generated artifact).
- `.gitignore`: ensure `.local/` is ignored (verify; add if missing).

**Tests.** None required; this is a script cleanup. Run `bash scripts/bootstrap_dev_env.sh` once locally to confirm `.local/setup-report.md` is written.

**Out of scope.** Other bootstrap script changes.

---

## Item 9 — Flesh out stub modules into real interfaces

**Rationale.** `prompts.py`, `memory.py`, `skills.py`, `scheduler.py`, `workers.py` are 5–9 line files. The spec lists each by name and assigns a role. Each must be a real interface/registry.

**Files to edit (replace contents).**
- `orchestrator_core/prompts.py`
- `orchestrator_core/memory.py`
- `orchestrator_core/skills.py`
- `orchestrator_core/scheduler.py`
- `orchestrator_core/workers.py`

**9a — prompts.py (in-memory `PromptRegistry`).**

```python
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

def register_prompt(template: PromptTemplate) -> None: ...
def render_prompt(name: str, *, version: str | None = None, **values: Any) -> str: ...
```

- `register` overwrites identical (name, version); registering a new version of the same name keeps both.
- `get(name)` with no version returns the latest by lexicographic compare on `version`.
- Unknown name raises `KeyError`.

**9b — memory.py (Protocol + null + in-memory).**

```python
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

class NullMemoryStore: ...                  # all methods no-op / return None / False / []
class InMemoryMemoryStore: ...              # dict-backed, threading.Lock, scoped by (workflow_id, key)
```

- The existing `MemoryRef` dataclass has no callers; remove it.

**9c — skills.py (registry; YAML loader becomes one populator).**

```python
class Skill(pydantic.BaseModel):
    name: str
    version: str = "1"
    handler_type: str                    # the harness handler key this skill maps to
    description: str | None = None
    metadata: dict[str, Any] = {}

class SkillRegistry:
    def register(self, skill: Skill) -> None: ...
    def get(self, name: str, version: str | None = None) -> Skill: ...
    def list(self) -> list[Skill]: ...
    def for_handler_type(self, handler_type: str) -> list[Skill]: ...
    def load_yaml(self, path: str | pathlib.Path) -> int: ...

def register_skill(skill: Skill) -> None: ...
def get_skill(name: str, version: str | None = None) -> Skill: ...
def load_skills_config(path: str | pathlib.Path) -> int: ...
```

YAML format:

```yaml
skills:
  - name: example
    version: "1"
    handler_type: fake.complete
    description: Example skill
    metadata: {tags: [demo]}
```

**9d — scheduler.py (`due_task_ids`, `tick`).**

```python
def due_task_ids(conn: psycopg.Connection, *, slot: str | None = None, limit: int = 100) -> list[str]:
    """Return queued task IDs whose run_after has elapsed."""

def tick(conn: psycopg.Connection, *, slot: str | None = None, limit: int = 100) -> int:
    """Return count of due tasks. No side effects in this iteration."""
```

- SQL: `select id from tasks where state='queued' and run_after <= now() [and slot=%s] order by priority desc, run_after asc limit %s`.
- No new schema. Read-only.

**9e — workers.py (lifecycle).**

```python
class WorkerInfo(pydantic.BaseModel):
    id: str
    slot: str
    state: str                    # 'idle' | 'busy' | 'offline'
    current_task_id: str | None
    last_heartbeat_at: datetime
    metadata: dict[str, Any] = {}

def register_worker(conn, *, worker_id: str, slot: str,
                    metadata: dict[str, Any] | None = None) -> WorkerInfo: ...
def deregister_worker(conn, *, worker_id: str) -> bool: ...
def set_idle(conn, *, worker_id: str) -> None: ...
def set_busy(conn, *, worker_id: str, task_id: str) -> None: ...
def list_active(conn, *, slot: str | None = None,
                stale_after_seconds: int = 60) -> list[WorkerInfo]: ...
def heartbeat(conn, *, worker_id: str) -> None: ...
```

- Refactor inline `insert into workers ...` upsert in `tasks.claim_next` (line ~116) and `update workers ...` calls in transition functions (~lines 255, 298) to call into `workers.py`. Same SQL, centralized.
- Keep `from orchestrator_core.harness.runner import run_once` re-export in `workers.py` for backward compatibility.

**Tests for item 9.**
- `tests/unit/test_prompts.py`: register, latest-version semantics, render, unknown-name raises.
- `tests/unit/test_memory.py`: NullMemoryStore is no-op; InMemoryMemoryStore round-trip; list scopes by workflow_id; concurrent put from two threads doesn't lose data.
- `tests/unit/test_skills.py`: register + get; load_yaml from tmp_path file; for_handler_type filter; malformed YAML raises.
- `tests/unit/test_scheduler.py`: with stub conn (or real if conftest fixture available) verify SQL correctness.
- Integration test `test_scheduler_due_task_promotion`:
  - Enqueue task A with `run_after = now() + interval '1 day'`.
  - Enqueue task B with `run_after = now() - interval '1 minute'`.
  - `due_task_ids()` returns `[B.id]`.
  - `tick()` returns 1.
- Integration test `test_worker_lifecycle`:
  - register_worker → set_busy → heartbeat → set_idle → deregister_worker.
  - Verify each state via direct SQL.
  - `list_active(stale_after_seconds=1)` excludes a worker whose `last_heartbeat_at` is manually backdated 10 seconds.
- New scenario `scenarios/core/regression/scheduler_promotes_due_task.yaml`: enqueue task with future `run_after`, harness action `set_task_run_after(seconds_offset=-1)`, harness action `scheduler_tick`, assert `flag.scheduler_due_count == 1`.
- `orchestrator_core/testing/runner.py`: add the two new actions `set_task_run_after` and `scheduler_tick`.

**Out of scope.** DB-backed prompt or memory persistence. Cron/recurring expressions in scheduler.

---

## Item 10 — CI workflow

**Rationale.** Code currently passes lint/type/unit locally but there is no enforcement in CI. The other items add tests; CI prevents regression.

**Files to edit.**
- `.github/workflows/ci.yml` (new)

**Required workflow (GitHub Actions).**

```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:

jobs:
  lint-type-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install --upgrade pip
      - run: pip install -e ".[dev]"
      - run: ruff check orchestrator_core tests
      - run: mypy orchestrator_core
      - run: pytest tests/unit -q

  integration-and-scenarios:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: orchestrator_core_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      ORCHESTRATOR_TEST_DATABASE_URL: postgresql://postgres:postgres@localhost:5432/orchestrator_core_test
      ORCHESTRATOR_DATABASE_URL: postgresql://postgres:postgres@localhost:5432/orchestrator_core_test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install --upgrade pip
      - run: pip install -e ".[dev]"
      - run: orchestrator-core db migrate
      - run: pytest tests/integration -q
      - run: pytest tests/scenarios -q
```

**Tests.** None — CI is a meta-deliverable. Verify by pushing a branch and confirming both jobs go green.

**Out of scope.** Coverage thresholds, deploy pipelines, release automation, container builds.

---

## Cross-cutting requirements

### Scenario harness extensions (touched by items 2 and 9)

Add the following actions to `orchestrator_core/testing/runner.py`:
- `upsert_slot` — args: `name`, `concurrency`, optional `enabled`, `metadata`. Calls `slots.upsert_slot`.
- `set_task_run_after` — args: `task_ref`, `seconds_offset`. Resolves task_ref via the existing refs map; updates the row.
- `scheduler_tick` — args: optional `slot`. Calls `scheduler.tick`; stores `count` in `flags['scheduler_due_count']`.
- `expire_pending_approvals` — calls `approvals.expire_pending_approvals`; stores count in `flags['approvals_expired']`.

Each new action: keep argument shape consistent with existing actions. Each must be referenced from at least one new or existing scenario YAML.

### Schema migration list (final state)

By batch end, `orchestrator_core/db/schema/` should contain:
- `001_initial.sql` (existing)
- `002_indexes.sql` (existing)
- `003_indexes.sql` (item 3)
- `004_slot_defaults.sql` (item 2 — only if you choose to seed default slot rows; optional)

### Reporting

Write `docs/reports/next-steps-1-to-10-completion.md`:

```markdown
# Next Steps 1–10 Completion Report

## Summary
- Item 1 (CLI verbs): <status> — files changed: ...
- Item 2 (slot concurrency): ...
- ...
- Item 10 (CI): ...

## Verification
- ruff: <output>
- mypy: <output>
- unit: <output>
- integration: <output>
- scenarios: <output>

## Deviations from prompt
<list any with rationale; "none" if none>

## git diff --stat
<paste output>
```

### Final acceptance gate

Run all of these and confirm green before reporting complete:

```bash
.venv/bin/ruff check orchestrator_core tests
.venv/bin/mypy orchestrator_core
.venv/bin/pytest tests/unit -q
.venv/bin/pytest tests/integration -q
.venv/bin/pytest tests/scenarios -q
.venv/bin/orchestrator-core --help
.venv/bin/orchestrator-core db check
.venv/bin/orchestrator-core reaper --limit 10
```

The last three must exit 0 against a migrated test database.

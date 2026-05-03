# Plan — Convert `/Volumes/devssd/orchestrator` to `pgloom-engineering` on top of `pgloom`

> **Naming.** The runtime previously named `orchestrator-core` is being renamed to **`pgloom`** before its first public release. The dist name on PyPI, the import name, the CLI verb, and the GitHub repo all rename together. Phase 0a below covers the mechanical rename step. Throughout this plan, `pgloom` refers to what was previously `orchestrator_core` / `orchestrator-core`.
>
> The downstream consumer was originally drafted as `engineering-orchestrator` and was later renamed to **`pgloom-engineering`** (dist name + repo + Python package `pgloom_engineering`). This plan was rewritten in‑place on 2026‑05‑02 to use the new names; sibling docs under `docs/prompts/` and `docs/reports/` retain the old names as historical record.

> **Plan status (2026‑05‑02).**
> - **Phase 0a (rename to pgloom)** — DONE.
> - **Phase 0 (packaging + release.yml + Trusted Publishing)** — DONE. `pgloom 0.2.0` published to PyPI on 2026‑05‑02 (https://pypi.org/project/pgloom/0.2.0/), wheel + sdist, MIT, owner `joshorig`. Tag `v0.2.0` present.
> - **Phase 0.5 (gap‑fill enhancements)** — DONE in 0.2.0. All five blockers (0.5.1 bounded subprocess, 0.5.2 CLIModelProvider, 0.5.3 PostgresMemoryStore, 0.5.4 pluggable dashboard, 0.5.5 blocker registry) plus the QoL multiplexer (0.5.6) landed with tests. 0.5.7 storage backend deferred to 0.3.x as planned. 0.5.8 approval panels deferred as planned.
> - **Phase 1 (pgloom-engineering scaffolding)** — DONE. Repo at `/Volumes/devssd/repos/oss/pgloom-engineering`, depends on `pgloom>=0.2,<0.3`, CI green (ruff/mypy/unit pass), 6 migrations in place.
> - **Phase 2 (domain port)** — IN PROGRESS. The autonomy/contract foundation is **committed**: Track G typed contract layer + worker pre/post gates are DONE in pgloom-engineering commits `5bdb5c1` (`add typed contract layer with worker pre/post gates`) and `e2d9027` (`wire planner implementer reviewer to contract layer`). Track H projects registry + CLI (register / list / show / import / enable / disable / archive) are DONE; the worker consults project active/disabled state on every dispatch. Track C BRAID runtime is **parked indefinitely**; bounded rubric runners replace it as the multi-panel review primitive. **QA reframed (2026‑05)**: QA becomes a test‑authoring engineer with two task types — `engineering.qa.author` runs **before** Implementer (writes one failing test per `acceptance_test_matrix` row, test‑first), and `engineering.qa.verify` runs **after** Reviewer to run the full app + sign off via `engineering_qa_signoffs`. Add‑or‑strengthen post‑gate enforces non‑weakening of tests. Brief stubbed at `docs/prompts/qa-engineer-impl.md`; deferred until the planner ships. Slot `qa-engineer` (concurrency 1) is the dispatch target; initially colocated, eventual move to a dedicated Mac mini is operational only. Remaining high-priority work is real role *execution*: planner council + rubric critic (in flight, brief at `docs/prompts/planner-impl-and-review.md`), Implementer task-result producer, Reviewer rubric verdict producer, QA Engineer (both phases), worktree + GitHub integration (Track D), and self-repair orchestration. Tracks E mostly stubs; Track F dashboard collector wired (server stub); Track A features partial.
> - **Phase 3 (harness port)** and **Phase 4 (hard cutover)** — not started.
>
> The plan was extended in 2026‑05 with a typed contract layer (Track G below) that wraps every handoff in a hashed Pydantic contract with worker pre/post gating. The original Phase 2 sketch did not include this; the plan was updated to make it first‑class.

## Targets

| Repo | Path | Role |
|---|---|---|
| **pgloom** | `/Volumes/devssd/repos/oss/pgloom` (renamed from `orchestrator-core`) | Domain-neutral runtime. Already exists. Needs renaming + packaging + a small set of enhancements before downstream consumers can build on it cleanly. PyPI: `pgloom`. GitHub: `github.com/joshorig/pgloom`. |
| **pgloom-engineering** | `/Volumes/devssd/repos/oss/pgloom-engineering` | New. Engineering-specific orchestrator (planner / implementer / reviewer / QA / historian, rubric councils, worktrees, GH PRs, Telegram). Consumes `pgloom` as a pinned dependency. GitHub: `github.com/joshorig/pgloom-engineering`. |
| **reference orchestrator** | `/Volumes/devssd/orchestrator` | Read-only. Source of domain logic to port. Eventually retired. Roughly 27.5k LOC of Python, 60+ harness scenarios, 14k-line `bin/orchestrator.py`, 9.8k-line `bin/worker.py`. |

## Plan shape

Six steps. Phase 0a renames the repo. Phase 0 and 0.5 happen on the renamed `pgloom` repo *first*; nothing in pgloom-engineering can land until `pgloom` is published as a real, installable package and the gap-fill enhancements are merged. After that, the port runs through scaffolding → domain port → harness port → cutover.

```
Phase 0a   Phase 0      Phase 0.5             Phase 1       Phase 2          Phase 3        Phase 4
Rename     Packaging    Core enhancements     Scaffolding   Domain port      Harness port   Hard
to pgloom  & release    (gap-fill)            new repo      (roles, rubrics, (scenarios,    cutover
                                                             worktrees,       fixtures)
                                                             PRs, Telegram)
↓ pgloom repo work ↓                          ↓ pgloom-engineering repo work ↓
```

---

# PHASE 0a — Rename `orchestrator-core` to `pgloom`

> **Status: DONE.** Rename landed cleanly; the package now ships as `pgloom`. Section retained for historical traceability of the rename surface.

**Goal:** mechanical rename, fully tested, before any release artifact is built. This is a discrete step to keep the rename diff readable.

## 0a.1 — Rename surface

| Layer | Before | After |
|---|---|---|
| Python package directory | `orchestrator_core/` | `pgloom/` |
| Distribution name (`pyproject.toml > [project] name`) | `orchestrator-core` | `pgloom` |
| Import statements | `from orchestrator_core...` | `from pgloom...` |
| CLI script entry point | `orchestrator-core = "orchestrator_core.cli:app"` | `pgloom = "pgloom.cli:app"` |
| CLI command name | `orchestrator-core db migrate` | `pgloom db migrate` |
| Default DB name in env vars | `ORCHESTRATOR_DATABASE_URL` | `PGLOOM_DATABASE_URL` (and `PGLOOM_TEST_DATABASE_URL`) |
| Docs / README references | `orchestrator-core` / `orchestrator_core` | `pgloom` |
| GitHub repo (manual rename in GitHub UI) | `joshorig/orchestrator-core` (if it exists) | `joshorig/pgloom` |
| Local repo directory (optional, recommended) | `/Volumes/devssd/repos/oss/orchestrator-core` | `/Volumes/devssd/repos/oss/pgloom` |

## 0a.2 — Mechanical steps

```bash
cd /Volumes/devssd/repos/oss/orchestrator-core

# 1. Rename the package directory.
git mv orchestrator_core pgloom

# 2. Sweep imports and string references.
git ls-files -z | xargs -0 sed -i '' \
  -e 's/orchestrator_core/pgloom/g' \
  -e 's/orchestrator-core/pgloom/g'
# On macOS use `-i ''`. On Linux use `-i`.

# 3. Rename env var prefix (do this in a second pass, narrower scope).
git ls-files -z | xargs -0 sed -i '' \
  -e 's/ORCHESTRATOR_DATABASE_URL/PGLOOM_DATABASE_URL/g' \
  -e 's/ORCHESTRATOR_TEST_DATABASE_URL/PGLOOM_TEST_DATABASE_URL/g'

# 4. Verify nothing references the old names.
git grep -i orchestrator_core   # should be empty
git grep -i orchestrator-core   # should be empty (except possibly historical changelog entries)

# 5. Run the full test suite to confirm nothing broke.
ruff check pgloom tests
mypy pgloom
pytest tests/unit -q
pytest tests/integration -q       # against a fresh DB created with the new env var name
pytest tests/scenarios -q

# 6. Optional but recommended: rename the directory itself.
cd /Volumes/devssd/repos/oss
mv orchestrator-core pgloom
```

## 0a.3 — Acceptance for Phase 0a

- `git grep -i orchestrator` returns zero relevant matches in code (a few historical mentions in `docs/` and `CHANGELOG.md` are fine).
- All five verification commands (ruff, mypy, unit, integration, scenarios) pass against the renamed package.
- The CLI is invokable as `pgloom --help` from an editable install.
- A single rename commit is on the branch, with a clean message: `rename: orchestrator-core → pgloom`.

---

# PHASE 0 — pgloom packaging & release

> **Status: DONE.** `pgloom 0.2.0` is on PyPI (https://pypi.org/project/pgloom/0.2.0/), wheel + sdist, MIT, owner `joshorig`. Tag‑driven release via `.github/workflows/release.yml` with Trusted Publishing (OIDC). Schema files bundled. README badges, LICENSE, CHANGELOG, MANIFEST, `py.typed` all present.

**Goal:** `pip install pgloom` works against a real PyPI release. Tag-driven publishing via GitHub Actions with PyPI Trusted Publishing (OIDC, no long-lived tokens). Semver. Changelog. Sdist + wheel artifacts. Reproducible builds.

## 0.1 — Package metadata polish

Edit `pyproject.toml` to satisfy PyPI's metadata requirements:

```toml
[project]
name = "pgloom"
version = "0.1.0"            # bump per release; consider hatch-vcs / setuptools-scm later
description = "Postgres-backed reusable workflow and task orchestration runtime."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "Josh Cassidy", email = "cassidy.joshua@googlemail.com" }]
keywords = ["orchestration", "workflow", "postgres", "task-queue", "agents"]
classifiers = [
  "Development Status :: 4 - Beta",
  "Intended Audience :: Developers",
  "License :: OSI Approved :: MIT License",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Programming Language :: Python :: 3.13",
  "Topic :: Software Development :: Libraries",
  "Topic :: System :: Distributed Computing",
  "Operating System :: OS Independent",
]

[project.urls]
Homepage = "https://github.com/joshorig/pgloom"
Repository = "https://github.com/joshorig/pgloom"
Issues = "https://github.com/joshorig/pgloom/issues"
Changelog = "https://github.com/joshorig/pgloom/blob/main/CHANGELOG.md"

[project.scripts]
pgloom = "pgloom.cli:app"

[tool.setuptools.packages.find]
include = ["pgloom*"]

[tool.setuptools.package-data]
pgloom = ["db/schema/*.sql", "py.typed"]
```

New top-level files:
- `LICENSE` — MIT. Standard text with `Copyright (c) 2026 Josh Cassidy`.
- `CHANGELOG.md` — "Keep a Changelog" format. Seed with `## [0.1.0] - YYYY-MM-DD - Initial release (renamed from orchestrator-core, never published under that name)`.
- `MANIFEST.in` — explicitly include `pgloom/db/schema/*.sql`, `LICENSE`, `CHANGELOG.md`, `README.md`.
- `py.typed` — empty marker file at `pgloom/py.typed` so downstream consumers get type hints. Add to `[tool.setuptools.package-data]` (already shown above).

## 0.2 — Build hygiene

Add `tools/` workflow:

```bash
# scripts/build_dist.sh
.venv/bin/python -m pip install --upgrade build twine
.venv/bin/python -m build              # produces dist/*.tar.gz and dist/*.whl
.venv/bin/python -m twine check dist/* # validates metadata renders on PyPI
```

Validate locally before any tag push:
```bash
pip install dist/pgloom-0.1.0-py3-none-any.whl
pgloom --help
pgloom db migrate                  # against a throwaway DB
```

## 0.3 — Versioning policy

- Use **manual semver** in `pyproject.toml` for now; defer setuptools-scm until you need branch-based dev versions.
- `0.x` while pre-stable. Breaking changes allowed at any minor bump. Document each break in the changelog under a "Breaking" subsection.
- pgloom-engineering pins to a specific minor: `pgloom>=0.2,<0.3`.

## 0.4 — Release workflow

New file: `.github/workflows/release.yml`. Triggered on tag push matching `v*.*.*`.

```yaml
name: release
on:
  push:
    tags: ["v*.*.*"]

permissions:
  contents: write     # for GitHub Release creation
  id-token: write     # required for PyPI Trusted Publishing (OIDC)

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install --upgrade build twine
      - run: python -m build
      - run: python -m twine check dist/*
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  test-on-built-wheel:
    needs: build
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_USER: postgres, POSTGRES_PASSWORD: postgres, POSTGRES_DB: pgloom_test }
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U postgres" --health-interval 10s
          --health-timeout 5s --health-retries 5
    env:
      PGLOOM_TEST_DATABASE_URL: postgresql://postgres:postgres@localhost:5432/pgloom_test
      PGLOOM_DATABASE_URL: postgresql://postgres:postgres@localhost:5432/pgloom_test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - uses: actions/download-artifact@v4
        with: { name: dist, path: dist/ }
      - run: pip install dist/*.whl
      - run: pip install pytest pytest-timeout freezegun "psycopg[binary]"
      # Smoke: install the wheel and run the tests against it (not against editable source)
      - run: pgloom db migrate
      - run: pytest tests/integration -q
      - run: pytest tests/scenarios -q

  publish-testpypi:
    needs: test-on-built-wheel
    runs-on: ubuntu-latest
    environment: testpypi              # Configure environment in repo settings; protects with required reviewers
    steps:
      - uses: actions/download-artifact@v4
        with: { name: dist, path: dist/ }
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/

  publish-pypi:
    needs: publish-testpypi
    runs-on: ubuntu-latest
    environment: pypi                  # Required reviewers for prod publish
    steps:
      - uses: actions/download-artifact@v4
        with: { name: dist, path: dist/ }
      - uses: pypa/gh-action-pypi-publish@release/v1

  github-release:
    needs: publish-pypi
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with: { name: dist, path: dist/ }
      - uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: dist/*
```

**Trusted Publishing setup (one-time, manual):**
1. **PyPI pending publisher** (no need to upload a placeholder release first):
   - Log in at `pypi.org` as `joshorig`. Account → "Publishing" → "Add a pending publisher".
   - Project name: `pgloom`
   - Owner: `joshorig`
   - Repository name: `pgloom`
   - Workflow filename: `release.yml`
   - Environment name: `pypi`
2. **TestPyPI pending publisher** (separate site, separate account):
   - Log in at `test.pypi.org` as `joshorig`. Same form, identical fields except environment name `testpypi`.
3. In the GitHub repo `joshorig/pgloom` → Settings → Environments → create `pypi` and `testpypi`. Add required reviewers (yourself) on `pypi` so a human approves before public release.
4. No PyPI API tokens stored anywhere — OIDC handles auth per workflow run.

## 0.5 — Release process (operator-facing)

Document in `docs/release-process.md`:

```
1. Update CHANGELOG.md: move "Unreleased" entries under a new "## [0.2.0] - YYYY-MM-DD" heading.
2. Bump pyproject.toml version to match.
3. Commit: "release: 0.2.0"
4. Tag: git tag v0.2.0 && git push origin v0.2.0
5. Watch the release workflow:
   - build → test-on-built-wheel → publish-testpypi (auto)
   - publish-pypi blocks on environment reviewer approval
   - github-release runs after pypi publish
6. Verify: pip install --upgrade pgloom; pgloom --help.
```

## 0.6 — README hardening

Replace the current `README.md` with a release-quality version:
- Badges: PyPI version, Python versions, MIT license, CI status. Concrete URLs:
  - `https://img.shields.io/pypi/v/pgloom.svg`
  - `https://img.shields.io/pypi/pyversions/pgloom.svg`
  - `https://img.shields.io/github/license/joshorig/pgloom.svg`
  - `https://github.com/joshorig/pgloom/actions/workflows/ci.yml/badge.svg`
- 30-second install + quickstart (`pip install pgloom; createdb foo; PGLOOM_DATABASE_URL=postgresql://localhost/foo pgloom db migrate`).
- Concept primer: workflows / tasks / slots / handlers. One diagram.
- "Embedding pgloom in your service" — pointer to `pgloom-engineering` once it lands as a reference consumer.
- Link to `docs/architecture.md`, `docs/postgres-schema.md`, `docs/scenario-harness.md`.

## 0.7 — Acceptance for Phase 0

- `pip install pgloom==0.1.0` works on a fresh Python 3.12.
- `pgloom --help` exits 0 from an installed (non-editable) wheel.
- `LICENSE`, `CHANGELOG.md`, `py.typed`, README badges all present.
- Release workflow has run end-to-end at least once (cut a `v0.1.0` tag against a TestPyPI dry run; promote to PyPI when satisfied).
- Schema files (`pgloom/db/schema/*.sql`) are bundled in the wheel — verified with `unzip -l dist/*.whl | grep schema`.

---

# PHASE 0.5 — pgloom enhancements (gap fill)

> **Status: DONE in pgloom 0.2.0.** All five blocker items (0.5.1–0.5.5) and the QoL multiplexer (0.5.6) shipped. Verified surface, tests, and migrations as of 2026‑05‑02 — no `NotImplementedError` / `TODO` / `FIXME` in any of the six modules. 0.5.7 (storage backend) and 0.5.8 (approval panels) intentionally deferred. Per‑item evidence below; section retained for traceability.

**Goal:** close the gaps that the reference orchestrator exposes, so pgloom-engineering can be a thin domain layer rather than a parallel runtime. Nothing here is huge; each is a targeted addition.

The reference orchestrator does several things that `pgloom` today either stubs or omits. Five of them are real blockers for a clean port; one is quality-of-life. Land them all in 0.2.0 so the port consumes a stable surface.

## 0.5.1 — Bounded subprocess runner *(blocker)*

**Why.** pgloom-engineering constantly shells out: `git`, `gh`, `claude`, `codex`, `bash`. The reference's `_run_bounded()` does timeout, SIGTERM→SIGKILL escalation, stdout/stderr capture, exit code, and structured result. `pgloom`'s `harness/subprocess.py` is currently 9 lines.

**What.** Flesh out `pgloom/harness/subprocess.py`:

```python
class SubprocessResult(pydantic.BaseModel):
    argv: list[str]
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool
    killed: bool

def run_bounded(
    argv: list[str],
    *,
    timeout_seconds: float,
    cwd: str | os.PathLike[str] | None = None,
    env: dict[str, str] | None = None,
    stdin: bytes | None = None,
    grace_seconds: float = 5.0,
) -> SubprocessResult: ...
```

Behavior: launch via `subprocess.Popen`, poll until completion or timeout, on timeout send SIGTERM, wait `grace_seconds`, then SIGKILL. Capture both streams without deadlocking (use `communicate()` with timeout, then thread-based draining on escalation). Always return a result; raising is not the contract.

Tests: timeout → `timed_out=True`, `killed=True`, exit_code != 0; quick success → `exit_code=0`, `duration_seconds < timeout`; large output (~5MB stderr) does not deadlock.

## 0.5.2 — CLI-backed model provider *(blocker)*

**Why.** Reference invokes Claude and Codex as **CLI processes** (`claude`, `codex`), not HTTP APIs. `pgloom` has only `FakeModelProvider`. A `CLIModelProvider` is the missing primitive.

**What.** New module `pgloom/models/cli.py`:

```python
class CLIModelProfile(pydantic.BaseModel):
    name: str
    command: list[str]                # e.g. ["claude", "--profile", "default"]
    timeout_seconds: float = 300
    cost_per_input_token_usd: float = 0
    cost_per_output_token_usd: float = 0
    parse_response: typing.Literal["json", "text"] = "text"
    response_schema: dict[str, Any] | None = None    # JSON schema if parse_response=json

class CLIModelProvider:
    """Runs a configurable CLI as a model. Captures stdout, parses, records usage."""
    def invoke(self, *, profile: CLIModelProfile, prompt: str,
               input_tokens_hint: int | None = None,
               workflow_id: str | None = None,
               task_id: str | None = None) -> ModelInvocationResult: ...
```

Internally builds on 0.5.1's `run_bounded`. Records to `model_usage` exactly as `FakeModelProvider` does. If the CLI surfaces token counts (e.g. via stderr or a JSON envelope), parse them; otherwise approximate from input/output character lengths.

Tests: stub a fake CLI shell script in tests/fixtures/, run it with `CLIModelProvider`, assert usage row written and result parsed.

## 0.5.3 — Postgres-backed memory store *(blocker)*

**Why.** Reference's `memory_observations` table is the durable knowledge base across sessions. It uses SQLite FTS5 + optional sqlite-vec for hybrid search. The Postgres equivalent is `tsvector` + optional pgvector. `pgloom` today provides only `NullMemoryStore` and `InMemoryMemoryStore`.

**What.** New module `pgloom/memory_postgres.py` (kept separate so the import doesn't load psycopg into Null users):

```python
class PostgresMemoryStore:
    """Persistent memory store. Implements MemoryStore Protocol from memory.py.

    Uses tsvector on `value` for full-text search.
    Optional pgvector column for semantic search (lazy-imported)."""

    def put(self, entry: MemoryEntry) -> None: ...
    def get(self, workflow_id: str, key: str) -> MemoryEntry | None: ...
    def list_for_workflow(self, workflow_id: str) -> list[MemoryEntry]: ...
    def delete(self, workflow_id: str, key: str) -> bool: ...
    def search(self, workflow_id: str | None, query: str, *, limit: int = 20) -> list[MemoryEntry]: ...
```

New schema migration `005_memory.sql`:
```sql
create table if not exists memory_entries (
  workflow_id text not null,
  key text not null,
  value text not null,
  metadata jsonb not null default '{}'::jsonb,
  search_vector tsvector generated always as (to_tsvector('english', coalesce(value,''))) stored,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (workflow_id, key)
);
create index if not exists idx_memory_entries_search on memory_entries using gin (search_vector);
create index if not exists idx_memory_entries_workflow on memory_entries (workflow_id);
```

Reference's RRF (reciprocal rank fusion) hybrid logic stays in **pgloom-engineering**; core only ships FTS. Vector support deferred to 0.3.x.

Tests: round-trip put/get/list/delete, search by phrase ranks expected entries first, scoping by workflow_id excludes other workflows.

## 0.5.4 — Pluggable dashboard snapshot *(blocker)*

**Why.** Reference's `dashboard_feed.py` (1,018 LOC) is much richer than `pgloom`'s `dashboard.snapshot()`: per-project task buckets, transition timelines, slot health, rubric/council stats, cost rollups. Downstream orchestrators need a way to extend the snapshot without forking pgloom.

**What.** Refactor `pgloom/dashboard.py` to a plugin model:

```python
class DashboardSection(pydantic.BaseModel):
    key: str
    title: str
    data: Any

class DashboardCollector(typing.Protocol):
    def collect(self, conn: psycopg.Connection) -> DashboardSection: ...

_collectors: list[DashboardCollector] = []

def register_collector(collector: DashboardCollector) -> None: ...
def snapshot(*, database_url: str | None = None) -> dict[str, Any]:
    # Built-in sections: tasks_by_state, workers, blockers, recent_events, model_usage_24h
    # Plus everything from registered collectors.
    ...
```

pgloom ships a small set of built-in collectors. pgloom-engineering registers its own (per-project breakdown, rubric/council stats, council vote distribution).

Tests: register a fake collector, call `snapshot()`, assert its section is present.

## 0.5.5 — Blocker registry table *(blocker)*

**Why.** Reference treats blockers as data: `blocker_codes` table with `severity` (tier 0–5), `retryable` boolean, `category`, `metadata`. Severity drives recovery strategy (tier 0 = immediate escalation, tier 3–4 = autonomy reduction, tier 5 = session terminate). `pgloom`'s `blockers.py` is currently a constants dict — useful but not data-backed and not enforced.

**What.**

New schema `006_blocker_registry.sql`:
```sql
create table if not exists blocker_codes (
  code text primary key,
  name text not null,
  severity smallint not null check (severity between 0 and 5),
  retryable boolean not null default true,
  category text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

New module surface in `pgloom/blockers.py`:
```python
class BlockerCode(pydantic.BaseModel):
    code: str
    name: str
    severity: int                 # 0-5
    retryable: bool = True
    category: str
    metadata: dict[str, Any] = {}

def register_blocker(conn, blocker: BlockerCode) -> None: ...
def get_blocker(conn, code: str) -> BlockerCode | None: ...
def list_blockers(conn, *, category: str | None = None) -> list[BlockerCode]: ...
```

Optionally add a foreign-key check on `tasks.blocker_code` once downstream consumers have populated their codes. **Don't** make it FK-enforced in core — pgloom-engineering may want to declare codes lazily.

Tests: register, get, list-by-category. Migration is idempotent.

## 0.5.6 — Notification sink multiplexer *(QoL)*

**Why.** Reference pushes to Telegram + writes to events.jsonl + emits structlog. `pgloom` today has a single default sink. Real consumers want `LoggingSink + WebhookSink + DBSink` stacked.

**What.** Extend `pgloom/notifications.py`:

```python
class MultiplexNotificationSink:
    """Fan-out sink. Emits to all child sinks, swallows per-sink failures."""
    def __init__(self, sinks: list[NotificationSink]) -> None: ...
    def emit(self, notification: Notification) -> None: ...
```

No schema change. Tests: register a multiplex of two recording sinks, emit once, assert both received.

## 0.5.7 — Artifact storage backend protocol — *deferred to 0.3.x*

For pgloom-engineering running on a single host, the existing local-filesystem write in `artifacts.py` is sufficient. Defer the `StorageBackend` Protocol (S3 / URI-only / etc.) until a downstream consumer actually needs object storage. Saves ~half a day in this phase. The decision is documented here so we don't lose track.

## 0.5.8 — Approval panels (deferred) — *do NOT do in 0.2.0*

The reference's "council voting" (multi-stage approvals across panels) is engineering-specific. Keep `pgloom`'s approvals primitive single-decision. pgloom-engineering stacks N approvals against the same task and aggregates the verdict in its own logic. Revisit after the port; if multiple downstream orchestrators need it, lift to `pgloom` in 0.3.x.

## 0.5 — Acceptance

- `0.2.0` cut and published with all five blocker items (0.5.1 – 0.5.5) and the notification multiplexer (0.5.6).
- Artifact storage backend (0.5.7) deferred to 0.3.x.
- Mypy/ruff stay clean.
- New schema migrations are idempotent.
- Existing 21 integration tests + 1 scenario test still pass; new tests added for each enhancement.
- Changelog clearly lists the new public surface.

---

# PHASE 1 — `pgloom-engineering` repo scaffolding

> **Status: DONE.** Repo present at `/Volumes/devssd/repos/oss/pgloom-engineering` (GitHub: `joshorig/pgloom-engineering`). `pyproject.toml` declares `pgloom>=0.2,<0.3`. CI (`.github/workflows/ci.yml`) runs ruff, mypy, unit tests, and integration tests with a Postgres service container. CLI entry point `pgloom-engineering` wired to `pgloom_engineering.cli:app`. Six engineering migrations in `pgloom_engineering/db/schema/` (see Phase 2 Track G for the contract migrations 005/006 added later). Layout matches the spec below with two additions surfaced in Phase 2 Track G: `worker.py`, `contracts.py`, `contract_store.py`, `token_savior.py`.

**Goal:** stand up `/Volumes/devssd/repos/oss/pgloom-engineering` as a real Python project that depends on `pgloom>=0.2,<0.3`. No domain logic yet — just the skeleton, CI, and a runnable CLI that proves the pgloom dependency works end-to-end.

## 1.1 — Repo layout

```
pgloom-engineering/
├── pyproject.toml                  # name=pgloom-engineering
├── README.md
├── LICENSE
├── CHANGELOG.md
├── .gitignore
├── .env.example
├── justfile
├── scripts/
│   └── bootstrap_dev_env.sh        # similar pattern to pgloom's
├── docs/
│   ├── architecture.md             # how this layers on pgloom
│   ├── roles.md                    # planner/implementer/reviewer/qa/historian
│   ├── rubrics.md                  # bounded rubric pattern
│   ├── migration-from-reference.md # what we ported, what we dropped, gotchas
│   └── operations.md               # launchd, telegram, dashboard
├── pgloom_engineering/
│   ├── __init__.py
│   ├── cli.py                      # extends pgloom CLI
│   ├── config.py                   # extends pgloom Settings
│   ├── exceptions.py
│   ├── db/
│   │   └── schema/                 # engineering-specific tables
│   │       ├── 001_features.sql
│   │       ├── 002_self_repair.sql
│   │       └── 003_blocker_seed.sql
│   ├── features.py                 # feature aggregate (groups tasks by branch/PR)
│   ├── self_repair.py              # multi-stage recovery workflow
│   ├── council.py                  # multi-panel approval
│   ├── braid/
│   │   ├── __init__.py
│   │   ├── registry.py             # template registry
│   │   ├── runner.py               # graph traversal
│   │   └── templates/              # .mmd templates copied from reference
│   ├── roles/
│   │   ├── __init__.py
│   │   ├── planner.py
│   │   ├── implementer.py
│   │   ├── reviewer.py
│   │   ├── qa.py
│   │   └── historian.py
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── git.py                  # worktree, branch, push helpers
│   │   ├── github.py               # gh pr create, issue create
│   │   └── telegram.py             # long-polling bot
│   ├── handlers/
│   │   ├── __init__.py
│   │   └── registry.py             # registers handlers with pgloom's HandlerRegistry
│   ├── dashboard/
│   │   ├── feed.py                 # registers dashboard collectors with pgloom
│   │   └── server.py               # tiny HTTP server, optional
│   ├── reports/
│   │   └── ppd.py                  # daily PPD reports
│   └── projects.py                 # project registration + validation
├── scenarios/                      # engineering-specific scenarios
│   └── ...                         # ported from reference harness/scenarios
└── tests/
    ├── conftest.py
    ├── unit/
    ├── integration/
    └── scenarios/
```

## 1.2 — pyproject.toml

```toml
[project]
name = "pgloom-engineering"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "pgloom>=0.2,<0.3",
  # plus anything not in pgloom; e.g. nothing right now since pgloom ships httpx, pydantic, etc.
]
[project.scripts]
pgloom-engineering = "pgloom_engineering.cli:app"

[project.urls]
Homepage = "https://github.com/joshorig/pgloom-engineering"
Repository = "https://github.com/joshorig/pgloom-engineering"
```

## 1.3 — CLI bootstrap

`pgloom_engineering/cli.py` imports pgloom's typer app and adds engineering-specific verbs:

```python
from pgloom.cli import app as pgloom_app
import typer

app = typer.Typer(help="Engineering orchestrator built on pgloom")
app.add_typer(pgloom_app, name="pgloom")    # all pgloom verbs available under `pgloom-engineering pgloom ...`

# Engineering-specific top-level verbs:
@app.command("plan")
def plan(...): ...
@app.command("implement")
def implement(...): ...
@app.command("review")
def review(...): ...
@app.command("feature-status")
def feature_status(...): ...
```

## 1.4 — CI

Mirror pgloom's CI: lint/type/unit job + integration-and-scenarios job with Postgres service container. Add a step that pins `pgloom` to the latest published release in CI to catch packaging regressions: `pip install pgloom` (no `-e`, no path).

## 1.5 — Acceptance

- `pgloom-engineering pgloom db migrate` works (delegates to `pgloom`).
- `pgloom-engineering pgloom scenario run scenarios/core/smoke` passes (running pgloom scenarios via the wrapper proves the dependency is wired).
- `pyproject.toml` declares `pgloom>=0.2,<0.3`.
- CI is green on a stub repo with one trivial test.

---

# PHASE 2 — Domain port

**Goal:** port the engineering-specific runtime onto `pgloom`'s primitives. Eight tracks (A–H, after the 2026‑05 addition of Track G); can be parallelized by sub‑area but each track has internal ordering.

## Autonomy Contract

`pgloom-engineering` is **autonomous‑first.** A human is required only at feature finalization (PR merge). Every other transition — plan acceptance, implementer dispatch, review verdict, QA pass, blocker recovery — runs without human input under the rules below. These rules are not aspirational; they are encoded in Track G's contract validation and worker gates and are enforceable today.

1. **Planning is always multi‑agent.** Every Planner task invokes ≥ 2 agents and consolidates their proposals into a single `PlanContract`. Single‑agent planning is not a supported mode.
2. **Review is always multi‑agent.** Every Reviewer task invokes ≥ 2 panels (e.g. correctness, security, ops) and aggregates them into one `ReviewVerdictContract`. Council decisions live inside the contract, not in pgloom approvals.
3. **Implementation multi‑agent is configurable per project.** `engineering_projects.config` declares whether implement uses single‑specialist, split‑specialists, parallel‑candidates, or council‑decides topology (`ImplementationTopology` enum in `contracts.py`). The Planner emits the topology choice into the `PlanContract`.
4. **The plan must satisfy `PlanContract` validation.** No task in the feature is dispatchable until `validate_plan_contract()` returns no errors — non‑empty allowed/forbidden paths, verification commands, expected outputs, acceptance test matrix, no forward dependencies, edge‑case tests for stateful lifecycle.
5. **Every task handoff is typed, persisted, and hash‑linked.** `engineering_handoffs` rows carry the contract JSON; downstream handlers read upstream contracts via `list_task_handoffs(task_id, handoff_type)` rather than inspecting raw task payloads.
6. **Stale or drifting plans require explicit supersession.** A new `PlanContract` that diverges from a prior `DesignContract` must set `supersedes_plan_contract_id` and `design_drift_acknowledged`; otherwise `validate_plan_contract` rejects it. Tasks created under the prior plan are blocked by the pre‑gate hash check.
7. **Recovery attempts are recorded as structured data.** Every gate failure, every uncaught handler exception, every retry decision is a `RecoveryDecisionContract` row in `engineering_recovery_actions` — with blocker code, attempt count, max attempts, decision JSON, and outcome. Self‑repair acts on these rows, not on log scraping.
8. **Workers must self‑heal before asking a human.** The escalation path is replan → retry → topology change → escalate. Asking for human input is the last resort and only at attempt exhaustion (`attempt >= max_attempts` in the recovery contract). Feature finalization (PR merge) is the one place human input is *expected*, not exceptional.
9. **QA owns the test surface and gates the merge.** QA runs in two phases: `qa.author` runs *before* Implementer and writes one failing test per row of `acceptance_test_matrix` (test‑first), and `qa.verify` runs *after* Reviewer to run the full app + suite, close any residual gaps, and sign off. **No feature finalizes without an `approved` row in `engineering_qa_signoffs` for that feature.** QA's `allowed_paths` is restricted to `tests/**` and `qa/fixtures/**`; QA may **add** new tests and **strengthen** existing assertions but may never **delete tests, remove assertions, or relax bounds** (numerically widening any tolerance, timeout, epsilon, or assertion threshold). The post‑gate enforces add‑or‑strengthen via diff inspection; violations transition the task to `blocked` with `blocker_code="engineering.qa_test_weakening"`.

## Legacy Failure Modes Reviewed

The autonomy rules above are derived from the failure classes observed in the reference orchestrator at `/Volumes/devssd/orchestrator`. Each class is a documented historical bug or recurring blocker; the corresponding mitigation in `pgloom-engineering` is shown alongside.

| # | Legacy failure | Mitigation in `pgloom-engineering` |
|---|---|---|
| 1 | Invalid planner JSON (Claude returned malformed plan, runtime crashed) | `PlanContract` is Pydantic; validation rejects malformed input before persistence. Planner re‑prompts on validation failure rather than crashing the task. |
| 2 | Ambiguous lifecycle requirements (slice said "implement X" with no I/O contract; Implementer guessed wrong) | `TaskSliceContract` requires `expected_outputs`, `verification_commands`, `allowed_paths`, `forbidden_paths`. Empty fields fail `validate_plan_contract`. |
| 3 | Stale design contract / contract drift (later phase work contradicted earlier design; nothing flagged it) | Pre‑gate refuses tasks whose `input_contract_hash` ≠ active `PlanContract` hash. Drift requires explicit supersession with `design_drift_acknowledged=true`. |
| 4 | Missing lifecycle edge‑case tests (stateful work merged with no Store/restore coverage; production bugs followed) | `validate_plan_contract` detects stateful keywords and requires an edge‑case acceptance test in `acceptance_test_matrix`. |
| 5 | Runtime precondition failures (worker dispatched against disabled project / unavailable env) | Pre‑gate consults `engineering_projects.enabled`; refuses dispatch and records a recovery action. |
| 6 | QA target missing (review claimed done, no QA artifacts existed) | QA pre‑gate requires upstream `task_result` + `review_verdict` handoffs to exist before claim is valid. |
| 7 | False blocker claims (handlers raised "blocker: X" without Y registered code) | Blocker registry from Phase 0.5.5 is data‑backed; recovery contract carries the registered code, not free text. |
| 8 | Attempt exhaustion without useful recovery (retried the same broken plan five times then bricked the feature) | `RecoveryDecisionContract` carries `attempt` and `max_attempts`; orchestration must escalate to replan / topology change once exhausted, recorded as a fresh recovery row. |
| 9 | Worker crashes not captured as structured recovery (segfault / OOM / uncaught exception left task in `running` forever) | Worker post‑gate wraps `Handler.handle()` in a try/except; uncaught exceptions write a `RecoveryDecisionContract` and transition the task to `blocked`, never leaving it in `running`. |

These mitigations are why Track G is the **execution safety layer** rather than just a data layer: every legacy failure has a corresponding gate, contract, or validator that prevents its recurrence.

## Track A — Features and self-repair (engineering-only schema)

Reference has `features` + `feature_children` + `self_repair_issues` + `self_repair_deliberations`. `pgloom` has none of these and shouldn't (they're engineering-specific).

| From | To |
|---|---|
| `bin/orchestrator.py` lines ~10000–11000 (feature finalization) | `pgloom_engineering/features.py` |
| `bin/orchestrator.py` lines ~8000–10000 (self-repair) | `pgloom_engineering/self_repair.py` |
| Reference's tables `features`, `feature_children`, `self_repair_issues`, `self_repair_deliberations` | `pgloom_engineering/db/schema/001_features.sql` and `002_self_repair.sql` |

A **feature** wraps N **tasks** (a `pgloom.workflow` is the right abstraction; the engineering layer adds a `feature_id` foreign key into a `features` table that holds PR metadata + status).

Concretely: each engineering feature = one `pgloom.workflows` row + one `pgloom_engineering.features` row sharing the same id (or the workflow's metadata holds the feature_id; pick one and document).

Self-repair issues stay engineering-local. They reference `tasks.id` from `pgloom` but track council deliberations in their own tables.

## Track B — Roles as task handlers (rewritten 2026‑05 around contract outputs)

Each role becomes a `pgloom.harness.handler.Handler` registered against a task type. The runtime calls `tasks.claim_next` and dispatches; the worker pre‑gate (Track G) validates the inbound contract and handoffs; the handler performs the role‑specific work and **must return the role's required output contract**; the worker post‑gate validates that contract before recording the next handoff.

| Role | Handler module | Task type | Required output contract | Status |
|---|---|---|---|---|
| Planner | `roles/planner.py` | `engineering.plan` | `PlanContract` (persisted via `create_plan_contract`) + one `TaskContract` per child task | **partial — produces contracts, but model invocation + decomposition heuristics still simplistic** |
| QA Engineer (test author) | `roles/qa_engineer.py` | `engineering.qa.author` | `QAAuthorContract` — `tests_added`, `matrix_coverage` (acceptance criterion → tests covering it), `red_proof` (each new test demonstrably failing on the as‑read worktree). Runs **before Implementer**. | **not started — see `docs/prompts/qa-engineer-impl.md` (deferred until planner ships)** |
| Implementer | `roles/implementer.py` | `engineering.implement` | `TaskResultContract` (artifacts list, coverage summary, edge cases addressed, implementation choices, paths touched, verification command exit codes) | **stub — not yet emitting a real contract; gate correctly refuses** |
| Reviewer | `roles/reviewer.py` | `engineering.review` | `ReviewVerdictContract` (per‑panel verdict + rationale + council decision) — must read upstream `task_result` handoff | **stub** |
| QA Engineer (verify + sign‑off) | `roles/qa_engineer.py` | `engineering.qa.verify` | Extended `QAResultContract` (verdict, full‑suite evidence, additional tests added to close residual gaps, full‑app run logs) **plus** a row in `engineering_qa_signoffs` with `verdict ∈ {approved, rejected, needs_implementer_fix, needs_planner_replan}`. Runs **after Reviewer**. | **not started** |
| Historian | `roles/historian.py` | `engineering.historian` | One or more `MemoryEntry` rows linked to `feature_id` / `task_id` / `contract_hash`, plus a `historian_note` handoff | **stub** |

**Contract output requirements (the non‑negotiable interface).** A handler whose return value fails the post‑gate is treated as having produced no result. The handler can therefore not "fake done" by returning an empty payload — the gate either has the structured contract or it has a structured recovery row.

- **Planner**: invokes Claude (via 0.5.2 `CLIModelProvider`), produces a `PlanContract` (feature goal, design contract, task slice DAG, acceptance test matrix, autonomy policy), persists it, decomposes into child tasks each with an attached `TaskContract`. The child tasks have `depends_on` set so the worker pre‑gate sees the upstream handoff before they are claimable. Plans **must include both `engineering.qa.author` and `engineering.qa.verify` slices** (the planner critic enforces this).
- **QA Engineer (author)**: reads `PlanContract.acceptance_test_matrix`, writes one failing test per row (or per logical group), proves each is red on the as‑read worktree, and **returns a `QAAuthorContract`**. `allowed_paths` is restricted to `tests/**` and `qa/fixtures/**`; `forbidden_paths` includes `src/**` and any production module owned by Implementer. The post‑gate enforces the **add‑or‑strengthen** policy described in the Autonomy Contract (only addition or strict tightening of assertions; weakening or deletion is a `RecoveryDecisionContract(blocker_code="engineering.qa_test_weakening")`).
- **Implementer**: creates a worktree (Track D), invokes Claude/Codex via `CLIModelProvider`, runs the slice's `verification_commands` via 0.5.1 `run_bounded` (which now include the red tests authored by QA in the previous step), registers artifacts via `pgloom.artifacts.register_artifact`, commits + pushes (Track D), and **returns a `TaskResultContract`** declaring artifacts, coverage, edge cases, implementation choices, paths touched, verification command exit codes. May also call `record_token_savior_usage` if compression was applied.
- **Reviewer**: reads the upstream `task_result` handoff via `list_task_handoffs(task_id, "task_result")`, invokes bounded rubric panels per review domain, and **returns a `ReviewVerdictContract`** capturing per-panel verdicts, rationales, and the council decision. Pushes back to the Implementer by enqueuing a new `engineering.implement` slice (with `depends_on` on the rejected reviewer task) rather than re-opening pgloom approvals.
- **QA Engineer (verify + sign‑off)**: reads the upstream `task_result` + `review_verdict` + `qa_author_contract` handoffs. Runs the full suite (smoke + integration + targeted regression + **full‑app run** under per‑project resource lock). Identifies any residual gaps versus `acceptance_test_matrix` and closes them (same add‑or‑strengthen policy). Writes the extended `QAResultContract` and a row in `engineering_qa_signoffs`. The future `engineering.feature_finalize` task pre‑gate refuses dispatch unless an `approved` row exists for the feature.
- **Historian**: writes to `PostgresMemoryStore` (0.5.3) keyed by feature/task/contract id, then records a `historian_note` handoff so downstream readers can find it. No DB schema changes.

Slot mapping: reference has `{claude, codex, qa}`. In pgloom, slots become rows in `slots` table with `concurrency` set per the reference's per‑slot config. **Both QA task types (`engineering.qa.author` and `engineering.qa.verify`) dispatch to a dedicated slot `qa-engineer` with `concurrency=1`** — sign‑off serializes per host. Initially the worker process for that slot is colocated with other engineering workers (single host); when the dedicated Mac mini is provisioned, the operator simply moves the `--slot qa-engineer` worker process to the new host with no schema or code change. This is the "single dedicated slot, accept SPOF" decision: if the worker host is offline, QA queues and feature finalization waits.

## Track C — Bounded rubrics, not BRAID runtime

> **Decision 2026-05: BRAID is parked indefinitely.** The legacy Mermaid DSL, graph runner, template registry, and R1-R7 lint engine are not being ported unless a concrete future need appears: human-authored reusable templates, lint-time workflow topology guarantees, or a measured cost/accuracy regression that typed rubrics cannot address.

The useful idea from BRAID is retained: bounded, explicit checks with stable IDs, short prompts, mechanically computed verdicts, per-check audit, retry, and optional parallel execution. That becomes a Python-native rubric pattern rather than a runtime DSL.

| Legacy BRAID concept | New home |
|---|---|
| `Check:` node | `CheckDefinition(check_id, name, severity_if_failed, rubric)` |
| Mermaid graph | Python `RubricDefinition` + tested control flow |
| Graph runner | `RubricRunner.run(target, context, rubric)` |
| R1-R7 lint | Unit tests: every check has a prompt subsection, all check IDs are present exactly once, verdict computed mechanically |
| Template audit trail | `per_check_results` persisted in `PlanContract.council_reports` and later `ReviewVerdictContract` |
| Per-check retry / parallelism | `revise_until_clean(...)` and optional parallel execution over checks or panels |

Initial implementation surface:

- `pgloom_engineering/planner/critic.py` defines the first rubric: `PLANNER_CRITIC_RUBRIC` with the 11 planner checks.
- A later shared `pgloom_engineering/rubrics.py` can extract `CheckDefinition`, `RubricDefinition`, `RubricRunner`, and `revise_until_clean` once Reviewer/QA need the same pattern.
- Mermaid diagrams may still be generated for docs, but they are not runtime inputs and are not a second source of truth.

## Track D — Git / GitHub / worktree integration

Lifted mostly verbatim from `bin/worker.py`:

| From | To |
|---|---|
| worker.py `make_worktree`, `remove_worktree`, `_autocommit_worktree`, `push_worktree_branch`, `_detect_secrets_hook_findings` | `pgloom_engineering/integrations/git.py` |
| worker.py `create_pr` and surrounding | `pgloom_engineering/integrations/github.py` |

Each function moves to a stateless module with a clear signature; no global state. Subprocess calls go through 0.5.1 `run_bounded`.

Idempotency: PR creation must use `pgloom.idempotency.record_external_action` keyed by `(feature_id, "pr_create")` so a re-run of an implementer task doesn't double-open PRs.

## Track E — Telegram + PPD reports

| From | To |
|---|---|
| `bin/telegram_bot.py` | `pgloom_engineering/integrations/telegram.py` (library) + `cli.py` `telegram run` (daemon entry point) |
| `bin/ppd_report.py` | `pgloom_engineering/reports/ppd.py` |

Telegram becomes a `NotificationSink` registered with pgloom via 0.5.6 `MultiplexNotificationSink`. The long-polling daemon listens for commands and dispatches to engineering CLI verbs.

PPD report queries pgloom's `model_usage`, `task_events`, `tasks` tables plus the engineering `features` table. Output stays markdown.

## Track F — Dashboard

| From | To |
|---|---|
| `bin/dashboard_feed.py` (1,018 LOC) | `pgloom_engineering/dashboard/feed.py` (~300 LOC after dropping FS-specific code) |
| `bin/dashboard_server.py` | `pgloom_engineering/dashboard/server.py` |
| `orchestrator-dashboard.html` | `pgloom_engineering/dashboard/static/index.html` |

The feed registers as a `DashboardCollector` plugin (0.5.4) so the snapshot is composed of pgloom's built-in sections + engineering's per-project / per-feature sections.

## Track G — Typed contract layer + execution safety (added 2026‑05; structural DONE)

> **Status: structural pieces DONE; consumer handlers still stubs.** This track was not in the original plan. It was added in May 2026 after the Planner work surfaced a need for explicit, hashed, validated handoffs between roles. The infrastructure (contracts, contract_store, worker pre/post gates, token_savior instrumentation, projects gate) landed in:
>
> - `5bdb5c1 add typed contract layer with worker pre/post gates`
> - `e2d9027 wire planner implementer reviewer to contract layer`
>
> The Implementer/Reviewer/QA/Historian handlers that consume these contracts are still stubs (Track B).

**Why this exists.** Track G is not just a data layer — it is the **execution safety layer**. The worker refuses to run when contracts, handoffs, project state, or handler outputs are invalid. The original plan had handlers communicating implicitly via task payloads + pgloom approvals. In practice that was too loose: drift between Planner intent and Implementer output went undetected, recovery decisions had no audit trail, and disabled projects could still receive dispatch. The contract layer makes every Plan → Implement → Review → QA boundary a typed Pydantic object that is hashed, persisted, and validated by the worker on dispatch and on completion.

**Autonomy hardening (what the gates actually enforce).**

- **Disabled / unregistered project pre‑gate.** A claim against a task whose project is not in `engineering_projects` (or has `enabled=false`) is refused, the task transitions to `blocked`, and a `RecoveryDecisionContract` row is written.
- **Missing task contract pre‑gate.** Any non‑Planner task arriving without an attached `TaskContract` is refused. Planner is exempt because it is the contract producer.
- **Stale plan / task contract pre‑gate.** A `TaskContract` whose `input_contract_hash` no longer matches the current active `PlanContract` is refused — a new plan must explicitly supersede the old one before its tasks can run.
- **Missing upstream task‑result handoff pre‑gate (review / QA).** A `engineering.review` or `engineering.qa` task whose upstream Implementer/Reviewer has not yet recorded a `task_result` handoff is refused. This prevents reviewers from running against absent outputs.
- **Invalid implementer / reviewer / QA output post‑gate.** The handler's returned contract is validated against the slice's `expected_outputs` and against the contract type's own validators. Failures transition the task to `blocked` with a structured recovery row, not silent success.
- **Structured `RecoveryDecisionContract` rows for gate failures and crashes.** Every refusal *and* every uncaught handler exception writes a `RecoveryDecisionContract` to `engineering_recovery_actions` with blocker code, attempt count, max attempts, decision JSON, and outcome — so self‑repair can act on data, not log scraping.

**Modules.**

| Module | LOC | Surface | Status |
|---|---|---|---|
| `pgloom_engineering/contracts.py` | 311 | `FeatureGoalContract`, `DesignContract`, `TaskSliceContract`, `PlanContract`, `TaskContract`, `TaskResultContract`, `ReviewVerdictContract`, `QAResultContract`, `RecoveryDecisionContract`, `ImplementationTopology` enum, `validate_plan_contract()`, `contract_hash()`, `contract_payload()` | DONE; 7 unit tests in `tests/unit/test_contracts.py` |
| `pgloom_engineering/contract_store.py` | 307 | Plan: `create_plan_contract`, `get_active_plan_contract`, `list_plan_contracts`. Tasks: `upsert_task_contract`, `get_task_contract`, `list_task_contracts`. Handoffs: `record_handoff`, `list_handoffs`, `list_task_handoffs`. Recovery: `record_recovery_action`, `list_recovery_actions`. | DONE; integration coverage via `tests/integration/test_migrations.py` |
| `pgloom_engineering/worker.py` | 303 | `run_once(slot, worker_id, registry)` — claim → pre‑gate (project enabled, contract present, contract hash fresh) → handler dispatch → post‑gate (output contract, handoff recorded, drift checked) → state transition; records a `RecoveryDecisionContract` on crash. | DONE; covered by 12 integration tests including `test_worker_blocks_*` cases |
| `pgloom_engineering/token_savior.py` | 103 | `TokenSaviorUsage` model, `record_token_savior_usage`, `list_token_savior_usage`, `summarize_token_savior_usage` | DONE schema + recording surface; no upstream producer yet (Implementer/Reviewer will call once they're real) |
| `pgloom_engineering/projects.py` | 218 | Project registration, config load/validate, topology lookup, enable/disable flag the worker pre‑gate consults | DONE for the gate's needs; environment.py (Track H) still pending |

**Schema.**

- `004_token_savior.sql` — `engineering_token_savior_usage` (feature_id FK, workflow_id, task_id, model_usage_id, profile_name, input_tokens_original, input_tokens_after_savior, tokens_saved, reduction_ratio, estimated_cost_saved_usd, metadata JSONB).
- `005_contracts.sql` — `engineering_plan_contracts` (with unique partial index on `feature_id WHERE active=true` enforcing single‑active plan), `engineering_task_contracts` (PK on task_id), `engineering_handoffs`, `engineering_recovery_actions`. All FK‑cascading from `engineering_features`.
- `006_projects.sql` — `engineering_projects` (registry of valid projects + enabled flag).

**Validation rules in `validate_plan_contract()`.**

- Every `TaskSliceContract` must have non‑empty `allowed_paths`, `forbidden_paths`, `verification_commands`, `expected_outputs`.
- The plan's `acceptance_test_matrix` must be non‑empty.
- No forward dependencies in the slice DAG.
- If a slice mentions stateful lifecycle (text matches `store|restore|persist|resume`), it must declare an edge‑case acceptance test.
- A new plan that diverges from a prior plan's `DesignContract` must set `supersedes_plan_contract_id` and `design_drift_acknowledged`; otherwise validation rejects it.

**Worker gate semantics.**

- **Pre‑gate** runs after `pgloom.tasks.claim_next` and before handler dispatch. Refuses to dispatch if: the project is unregistered or disabled (`projects.py`), the task type is non‑Planner and no `TaskContract` is attached, the attached contract's hash doesn't match the current active `PlanContract`, or a downstream review/QA task has no upstream task‑result handoff yet. A refusal transitions the task to `blocked` with a `RecoveryDecisionContract` recorded.
- **Post‑gate** runs after `Handler.handle()` returns. Validates the handler's returned contract against the slice's `expected_outputs` and against the contract type's own Pydantic validators. On success it updates the task contract via `upsert_task_contract` (output_contract + status) and records a handoff to the next role via `record_handoff`. On failure it transitions the task to `blocked` and records a `RecoveryDecisionContract`.

> **Implementation note.** Because the post‑gate validates the returned contract, the **current Implementer handler is intentionally still blocked**: it does not yet emit a real `TaskResultContract` (artifacts, coverage summary, edge cases addressed, implementation choices), so the post‑gate refuses any tasks dispatched to it once a non‑trivial slice is present. This is the desired failure mode — the gate is correctly preventing fake "implementer done" signals — and unblocks only when Track B's Implementer is wired to produce a real result contract.

**How this changes Track B.**

The original Track B sketch had each handler "do its thing and return". With the contract layer, each handler now has a fixed signature for what it must read and produce:

- **Planner** (real): builds `PlanContract`, persists via `create_plan_contract`, decomposes into child tasks each with an attached `TaskContract`, records handoffs.
- **Implementer** (stubbed): must read its `TaskContract`, perform the work, return a `TaskResultContract` declaring artifacts/coverage/edge cases. Cannot just return `done`.
- **Reviewer** (stubbed): must read the upstream `TaskResultContract`, run bounded rubric panels, return a `ReviewVerdictContract` (per-panel verdicts + council decision).
- **QA** (stubbed): must run verification commands from the slice contract, return a `QAResultContract`.
- **Historian** (stubbed): writes `MemoryEntry` rows referencing the feature/task IDs.

**What this track does *not* do.**

- It does not implement the handlers themselves — those remain Track B.
- It does not implement self‑repair *orchestration* — only the recording surface (`record_recovery_action`). Retry/escalation/replan logic is still pending.
- It does not implement Reviewer rubrics — only provides the `ReviewVerdictContract` shape that the future bounded review panels will fill in.

## Track H — Projects + environment health (project layer DONE; environment health pending)

| From | To | Status |
|---|---|---|
| reference `projects` config + validation | `pgloom_engineering/projects.py` + `006_projects.sql` (`engineering_projects` table) | **DONE.** DB‑backed registry, JSON config import/validate, topology lookup. |
| `pgloom-engineering project register / list / show / import / enable / disable / archive` CLI verbs | `pgloom_engineering/cli.py` | **DONE.** Full lifecycle CLI surface. |
| Worker consults project active/disabled state on every dispatch | Track G pre‑gate | **DONE.** Disabled or unregistered projects refused at claim time. |
| `project_environment_ok()` check helpers | `pgloom_engineering/environment.py` | **NOT YET.** Per‑project smoke/regression scripts not yet registered with `pgloom.health`. |

Each project's smoke script + regression script + base branch lives in DB‑backed config. `environment.py` will register per‑project checks with pgloom's `health` module so blocking checks pause dispatch.

## What we drop in Phase 2

These exist in the reference and **do not** port:
- Filesystem queue (`queue/queued/`, `queue/claimed/`, etc.) — replaced by pgloom's `tasks` table.
- `state/runtime/transitions.log` — replaced by pgloom's `task_events`.
- `state/runtime/claims/`, `state/runtime/locks/` — replaced by pgloom's `FOR UPDATE SKIP LOCKED` and `resource_locks`.
- `state/runtime/events.jsonl` and `metrics.jsonl` — replaced by pgloom's `task_events` and `model_usage`.
- `bin/migrate_fs_to_engine.py` — N/A; we don't migrate FS state into the new repo.
- The dual-write FS↔SQLite mode in reference's `state_engine.py`.

## Track ordering and parallelism

**Updated order (2026-05):** G → A → B → D → rubric extraction → E → F → H. Track G (typed contract layer) is foundational — Planner, Worker, and the role contracts depend on it; it landed first. Tracks A and B run in parallel on top of G. D unblocks the Implementer handler in B. The rubric pattern starts inside the Planner critic and is extracted only when Reviewer/QA panels need it. E/F/H are independent and can be parallelized.

## Phase 2 acceptance

The acceptance bar is a superset of the original sketch and the Track G non‑negotiables. Items 1–4 are autonomy gates; items 5–11 are end‑to‑end and surface coverage; items 9–11 are the QA Engineer additions from 2026‑05.

1. **Worker blocks disabled projects.** A claim against a project with `enabled=false` (or unregistered) transitions the task to `blocked` and writes a `RecoveryDecisionContract`. (Covered today by `tests/integration/test_worker_blocks_disabled_project_before_handler` — DONE.)
2. **Worker blocks missing or stale contracts.** Non‑Planner tasks without an attached `TaskContract`, and tasks whose `input_contract_hash` ≠ active `PlanContract` hash, are refused with a recovery row. (Covered by `test_worker_blocks_non_planner_without_task_contract` and `test_worker_blocks_stale_task_contract` — DONE.)
3. **Worker blocks review/QA without upstream handoff.** A `engineering.review` claim with no upstream `task_result` handoff is refused; same for `engineering.qa.verify`. (Covered by `test_worker_blocks_review_without_result_handoff` — DONE for review; QA.verify equivalent pending.)
4. **Invalid handler output becomes structured recovery.** Implementer (or any role) returning a contract that fails post‑gate validation transitions the task to `blocked` with a `RecoveryDecisionContract` carrying the validation errors. Never silent success. (Covered by `test_worker_blocks_invalid_implementer_output` — DONE.)
5. **All role handlers exist and pass a unit test with a fake worktree + fake `CLIModelProvider`.** Six handlers now: planner, qa_engineer (`qa.author`), implementer, reviewer, qa_engineer (`qa.verify`), historian.
6. **Full happy‑path contract chain.** Integration test: enqueue `engineering.plan` → Planner emits `PlanContract` (with both `qa.author` and `qa.verify` slices) + child `TaskContract`s → `engineering.qa.author` writes red tests and emits `QAAuthorContract` → Implementer returns `TaskResultContract` (turning the red tests green) → Reviewer reads the result handoff and returns `ReviewVerdictContract` → `engineering.qa.verify` runs full app + signs off → `engineering_qa_signoffs` row with `verdict='approved'` → feature closed. The contract chain is queryable via `get_feature_aggregate`.
7. **`pgloom-engineering feature show FEATURE_ID` surfaces token‑savior usage.** Aggregate output includes `summarize_token_savior_usage(feature_id)` rows so cost reductions are visible per feature.
8. **Telegram bot can list active features.** Dashboard snapshot shows engineering‑specific sections.
9. **QA test‑first runs before Implementer.** A plan whose acceptance matrix has N rows produces an `engineering.qa.author` task that, when claimed, commits ≥ N test additions (or fewer if grouped, with grouping declared in `QAAuthorContract.matrix_coverage`) and proves each is red on the as‑read worktree before the Implementer slice becomes claimable.
10. **Add‑or‑strengthen post‑gate.** A QA task whose returned diff weakens or deletes any existing assertion (or relaxes any numeric tolerance/timeout/epsilon/threshold) is refused with `blocker_code="engineering.qa_test_weakening"`; integration test asserts this against a deliberately‑weakening fixture diff.
11. **Sign‑off gates finalization.** Future `engineering.feature_finalize` task pre‑gate refuses dispatch unless `select 1 from engineering_qa_signoffs where feature_id = $1 and verdict = 'approved'` returns a row. Integration test seeds a feature with no signoff and asserts the gate refuses; flips to a seeded approved signoff and asserts the gate accepts.

---

# PHASE 3 — Harness port

**Goal:** port the 60+ scenarios under `harness/scenarios/` to pgloom-engineering's harness, on top of pgloom's scenario runner.

## 3.1 — Categorize the reference scenarios

From the reference review:

| Category | Count | Disposition |
|---|---|---|
| Self-repair (19, 22, 26, 28, 29, 32, 33, 34, 43) | ~12 | Port. Engineering-specific, valuable regression coverage. |
| State engine (35–39, 49–62) | ~20 | Mostly drop. These tested SQLite migrations; we use pgloom's Postgres migrations which are tested at the pgloom level. Keep 1–2 representative cases as smoke tests. |
| Memory (41, 41a) | 2 | Port to pgloom-engineering harness once 0.5.3 PostgresMemoryStore exists. |
| Notifications (44, 45) | 2 | Port; depends on Telegram + cost capture. |
| Security (46, 47, 48) | 3 | Port. Security-review scenario, untrusted-skill scenario, supply-chain audit. |
| Runner/fixture (r1–r3) | 3 | Mostly absorbed by pgloom's harness. Keep as sanity checks. |
| Lifecycle / QA / council / etc. (20, 23–25, 27, 30–31, 40, 57–63) | ~15 | Port the ones that exercise engineering primitives (council, QA contracts, environment checks); drop those that re-test what pgloom already tests. |

Net: ~25 ported scenarios + ~5 retained as smoke/regression. Rest are dropped as redundant with pgloom's harness.

## 3.2 — Harness compatibility

Reference scenarios use `harness/run_scenario.py` (~120 LOC) with YAML + optional `mock_reviewer.py`. pgloom's harness in `pgloom/testing/runner.py` uses YAML actions + assertions registered against a `FakeHandler`.

Bridge:
- Engineering harness (`tests/scenarios/engineering_runner.py`) wraps pgloom's `run_scenario` and adds:
  - `mock_council_decision` action (deterministic verdict injection)
  - `mock_braid_template` action (preload a template into the registry)
  - `simulate_pr_create` action (records to `external_actions` without calling `gh`)
  - `simulate_worktree_state` action

- All reference `mock_reviewer.py` files become `mock_council_decision` actions in the corresponding YAML, so no Python-per-scenario.

## 3.3 — Phase 3 acceptance

- 25 ported scenarios pass.
- Mock CLI surface lets every scenario run hermetically — no `gh`, no `claude`, no `git push` to anything real.
- Engineering CI runs scenarios on every PR.

---

# PHASE 4 — Hard cutover

Risk tolerance is high, so this phase is compact. No dual-run hold-down.

## 4.1 — Cutover

1. Bring up `pgloom-engineering` against a fresh Postgres database. No state migration from the reference repo.
2. Run one happy-path feature end-to-end on `pgloom-engineering` to confirm: plan → implement → review → QA → PR open → merge.
3. Drain the reference: stop accepting new tasks, wait for `queue/{queued,claimed,running}` to empty (or hand-resolve the stragglers).
4. Flip launchd plists / systemd units from the reference's `worker.py <slot>` to `pgloom-engineering <slot>`.
5. Repoint the Telegram bot config and start `pgloom-engineering telegram run`. Stop the reference's `dashboard_server.py`, start engineering's.

## 4.2 — Sunset (same day or next)

- Reference repo (`/Volumes/devssd/orchestrator`) goes read-only with a top-level `RETIRED.md` pointing to pgloom-engineering.
- Old reports under `reports/` archive to a snapshot folder.
- Reference repo archived in place. No grace period.

## 4.3 — Phase 4 acceptance

- Reference orchestrator's launchd plists are unloaded.
- Engineering-orchestrator has executed at least one full feature end-to-end in production.
- Telegram bot, dashboard, PPD reports all sourced from pgloom-engineering.
- Reference repo marked retired.

---

# Risk and dependency summary

| Risk | Likelihood | Mitigation |
|---|---|---|
| `CLIModelProvider` (0.5.2) doesn't capture token counts from `claude` CLI | Medium | Fall back to char-length approximation; document the discrepancy in `model_usage.metadata`. Cost numbers stay best-effort. |
| Reintroducing BRAID runtime out of inertia | Medium | BRAID is parked. Keep bounded checks as typed Python rubrics; resurrect Mermaid runtime only with a concrete measured need. |
| Self-repair workflow has subtle state machine bugs that surface only after migration | High | Port self-repair scenarios *first* in Phase 3, before declaring Phase 2 done. They are the strongest regression net. |
| PyPI Trusted Publishing setup forgotten until tag day | Low | Do a `v0.0.1` dry-run release into TestPyPI early in Phase 0 to flush out config issues. |
| pgloom-engineering pin on `pgloom>=0.2,<0.3` blocks pgloom 0.3 release | Expected, by design | When pgloom 0.3 lands, bump pgloom-engineering dep range and test. Standard semver upgrade. |
| Reference orchestrator's filesystem queue contains in-flight tasks at cutover | Medium | Drain by halting enqueue + waiting for queue/{queued,claimed,running} to empty before flipping launchd. Manual rerun any survivors via engineering CLI. |
| Hard cutover hits an undiscovered bug after launchd flip | Accepted (high risk tolerance) | pgloom-engineering CLI keeps `pgloom db reset --yes` available; reference launchd plists are stashed not deleted, so a same-day rollback is possible if needed. |

---

# Effort summary

| Phase | Scope | Estimate |
|---|---|---|
| 0a — rename to pgloom | mechanical sed sweep + dir rename + green test run | ~30 minutes |
| 0 — packaging & release | metadata, MIT license, changelog, release workflow, README | 1–2 days |
| 0.5 — pgloom enhancements | 5 blocker items + 1 QoL item (multiplexer); 0.5.7 deferred | 3–5 days |
| 1 — repo scaffolding | pyproject, layout, CI, smoke | 1 day |
| 2 — domain port | 8 tracks (A–H); A/B/D are the bulk. Track G (typed contract layer) added 2026‑05 and already DONE. | 2–3 weeks |
| 3 — harness port | ~25 scenarios + harness bridge | 4–6 days |
| 4 — hard cutover | drain, launchd flip, archive | ~1 day |
| **Total** | | **~4–5 weeks of focused work** |

---

# Mapping crib sheet

For the implementor doing the port, this is the one-page summary of where each reference concept lands.

```
REFERENCE  →  NEW HOME
================================================================
bin/orchestrator.py task lifecycle       →  pgloom.tasks (already exists)
bin/orchestrator.py blocker registry     →  pgloom.blockers + 006 migration (Phase 0.5.5)
bin/orchestrator.py self-repair          →  pgloom_engineering.self_repair (Phase 2 Track A)
bin/orchestrator.py council voting       →  pgloom_engineering.council (Phase 2 Track B)
bin/orchestrator.py feature finalization →  pgloom_engineering.features (Phase 2 Track A)
bin/orchestrator.py role handoff state   →  pgloom_engineering.contracts + contract_store (Phase 2 Track G — NEW)
bin/orchestrator.py recovery decisions   →  pgloom_engineering.contract_store.record_recovery_action (Phase 2 Track G — NEW)
bin/orchestrator.py token cost tracking  →  pgloom_engineering.token_savior (Phase 2 Track G — NEW)
bin/orchestrator.py QA invocation        →  pgloom_engineering.roles.qa_engineer (Phase 2 Track B; replaces qa.py stub) + 007_qa_signoffs.sql + qa.diff_policy (NEW 2026‑05; brief at docs/prompts/qa-engineer-impl.md)
bin/worker.py engineering dispatch loop  →  pgloom_engineering.worker.run_once (Phase 2 Track G — NEW; wraps pgloom.tasks.claim_next with pre/post gates)
bin/worker.py project gating             →  pgloom_engineering.projects (Phase 2 Track H)
bin/worker.py worker loop                →  pgloom.harness.runner (already exists)
bin/worker.py worktree mgmt              →  pgloom_engineering.integrations.git (Phase 2 Track D)
bin/worker.py PR create                  →  pgloom_engineering.integrations.github (Phase 2 Track D)
bin/worker.py code execution (Claude)    →  pgloom.models.cli (Phase 0.5.2)
bin/worker.py timeout/SIGTERM/SIGKILL    →  pgloom.harness.subprocess (Phase 0.5.1)
bin/state_engine.py                      →  drop entirely (replaced by pgloom's Postgres)
bin/dashboard_feed.py                    →  pgloom_engineering.dashboard.feed (Phase 2 Track F)
bin/dashboard_server.py                  →  pgloom_engineering.dashboard.server (Phase 2 Track F)
bin/telegram_bot.py                      →  pgloom_engineering.integrations.telegram (Phase 2 Track E)
bin/ppd_report.py                        →  pgloom_engineering.reports.ppd (Phase 2 Track E)
bin/migrate_fs_to_engine.py              →  drop entirely
queue/* directories                      →  drop entirely (Postgres replaces FS queue)
state/runtime/transitions.log            →  pgloom.task_events (already exists)
state/runtime/claims/, locks/            →  pgloom lease + resource_locks (already exists)
state/runtime/metrics.jsonl              →  pgloom.model_usage (already exists)
state/migrations/                        →  drop (pgloom handles its own; engineering adds 001-003 of its own)
roles/{planner,implementer,...}/README   →  pgloom_engineering/roles/{role}.py (Phase 2 Track B)
braid/templates/*.mmd                    →  parked; use docs-only diagrams if useful, not runtime inputs
braid/generators/*.prompt.md             →  selected rubric wording may be reused in Python prompt templates
braid/contract_schema.json               →  parked; Pydantic contracts are the runtime schema
.claude/skills/*                         →  copy verbatim; pgloom_engineering.skills validates trust
config/orchestrator.example.json         →  pgloom_engineering/config.py + .env.example
harness/run_scenario.py                  →  pgloom_engineering harness wrapper around pgloom's runner
harness/scenarios/* (60+)                →  ~25 ported scenarios; rest dropped (Phase 3.1)
memory_observations table (FTS5)         →  pgloom.memory_postgres (Phase 0.5.3)
task_costs                               →  pgloom.model_usage (already exists)
artifacts                                →  pgloom.artifacts (already exists)
events                                   →  pgloom.task_events (already exists)
environment_check_log                    →  pgloom.health (already exists)
```

---

# Decisions captured

1. **Project name:** `pgloom` (renamed from `orchestrator-core`; never published under the old name). PyPI: `pgloom`. Import: `pgloom`. CLI: `pgloom`. Repo: `github.com/joshorig/pgloom`.
2. **License:** MIT. `Copyright (c) 2026 Josh Cassidy`.
3. **PyPI account:** personal, username `joshorig`. TestPyPI account: same, `joshorig`.
4. **GitHub account:** personal, `https://github.com/joshorig`.
5. **PyPI name availability:** confirmed `pgloom` is unclaimed on PyPI as of plan-write time (`https://pypi.org/pypi/pgloom/json` → 404). **Update 2026‑05‑02:** `pgloom 0.2.0` now published; URL returns full release metadata.
6. **Cutover:** hard flip after Phase 3 acceptance. No dual-run.
7. **Artifact storage backend (0.5.7):** deferred to 0.3.x; local filesystem write is sufficient for pgloom-engineering.
8. **Approval panels:** stay in pgloom-engineering; not lifted to pgloom for 0.2.0.
9. **Consumer name (added 2026‑05):** the downstream consumer was originally drafted as `engineering-orchestrator` and is now `pgloom-engineering` (dist + repo + Python package `pgloom_engineering`). Reason: brand consistency with `pgloom`, cleaner namespace for future siblings (e.g. `pgloom-research`, `pgloom-ops`). The rename is reflected throughout this plan; sibling docs in `docs/prompts/` and `docs/reports/` retain the old name as historical record.
10. **Typed contract layer (added 2026‑05):** every Plan → Implement → Review → QA handoff is a hashed Pydantic contract persisted in dedicated tables, with worker pre/post gating. See Phase 2 Track G. The original sketch had handlers communicate via task payloads; the new layer makes drift detectable and recovery decisions auditable. This is engineering‑local; not lifted to `pgloom` for 0.2.x.
11. **Worker loop in pgloom-engineering (added 2026‑05):** a thin `pgloom_engineering.worker.run_once()` wraps `pgloom.tasks.claim_next` with project + contract pre/post gates. pgloom's own `harness.runner` remains the underlying primitive; the engineering wrapper adds the gates rather than forking the runner.
12. **BRAID runtime parked (added 2026-05):** the legacy Mermaid DSL + runner are deferred indefinitely. The retained pattern is bounded, explicit rubric checks with stable IDs, typed results, mechanically computed verdicts, and optional parallel execution. Runtime source of truth stays in Python + Pydantic contracts.
13. **QA Engineer architecture (added 2026‑05):** QA becomes a code‑producing role split into two task types. `engineering.qa.author` runs after the Planner and before the Implementer, writing one failing test per `acceptance_test_matrix` row (test‑first). `engineering.qa.verify` runs after the Reviewer, runs the full suite + the full app under per‑project resource lock, closes residual gaps, and writes a row to `engineering_qa_signoffs`. The future `engineering.feature_finalize` task pre‑gate refuses dispatch unless an `approved` signoff row exists for the feature. QA's `allowed_paths` is restricted to `tests/**` and `qa/fixtures/**`; the post‑gate enforces an **add‑or‑strengthen** rule via diff inspection — QA may add tests or strengthen assertions, never delete tests, remove assertions, or relax numeric tolerances/timeouts/thresholds. Both QA task types dispatch to a dedicated `qa-engineer` slot with concurrency 1; initially the worker for that slot is colocated with other engineering workers, with a planned operational move to a dedicated Mac mini when provisioned (no schema or code change). SPOF accepted as a hardware‑reliability forcing function. Brief at `docs/prompts/qa-engineer-impl.md`, deferred until planner ships.

# Historical: one‑time setup that was required before Phase 0a (all DONE 2026‑05‑02)

> Retained as a checklist of what was accomplished, not as outstanding work. Every item below is complete; the section is preserved so a future contributor can see what the bootstrap surface looked like.

1. ~~TestPyPI account.~~ DONE — `joshorig` registered on TestPyPI; Trusted Publishing pending‑publisher created for `pgloom`.
2. ~~PyPI 2FA.~~ DONE — 2FA enabled on PyPI and TestPyPI accounts.
3. ~~GitHub repo `joshorig/pgloom`.~~ DONE — repo exists, tag `v0.2.0` published, release workflow has run end‑to‑end (the live PyPI 0.2.0 release proves it).
4. ~~GitHub repo `joshorig/pgloom-engineering`.~~ DONE — repo exists, CI green on `main`.

Once items 1 and 3 are done, Phase 0a (rename) can run in roughly thirty minutes, after which Phase 0 (packaging + release) can proceed.

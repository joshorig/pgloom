# Plan — Convert `/Volumes/devssd/orchestrator` to `engineering-orchestrator` on top of `pgloom`

> **Naming.** The runtime previously named `orchestrator-core` is being renamed to **`pgloom`** before its first public release. The dist name on PyPI, the import name, the CLI verb, and the GitHub repo all rename together. Phase 0a below covers the mechanical rename step. Throughout this plan, `pgloom` refers to what was previously `orchestrator_core` / `orchestrator-core`.

## Targets

| Repo | Path | Role |
|---|---|---|
| **pgloom** | `/Volumes/devssd/repos/oss/pgloom` (renamed from `orchestrator-core`) | Domain-neutral runtime. Already exists. Needs renaming + packaging + a small set of enhancements before downstream consumers can build on it cleanly. PyPI: `pgloom`. GitHub: `github.com/joshorig/pgloom`. |
| **engineering-orchestrator** | `/Volumes/devssd/oss/engineering-orchestrator` | New. Engineering-specific orchestrator (planner / implementer / reviewer / QA / historian, BRAID, worktrees, GH PRs, Telegram). Consumes `pgloom` as a pinned dependency. GitHub: `github.com/joshorig/engineering-orchestrator`. |
| **reference orchestrator** | `/Volumes/devssd/orchestrator` | Read-only. Source of domain logic to port. Eventually retired. Roughly 27.5k LOC of Python, 60+ harness scenarios, 14k-line `bin/orchestrator.py`, 9.8k-line `bin/worker.py`. |

## Plan shape

Six steps. Phase 0a renames the repo. Phase 0 and 0.5 happen on the renamed `pgloom` repo *first*; nothing in engineering-orchestrator can land until `pgloom` is published as a real, installable package and the gap-fill enhancements are merged. After that, the port runs through scaffolding → domain port → harness port → cutover.

```
Phase 0a   Phase 0      Phase 0.5             Phase 1       Phase 2          Phase 3        Phase 4
Rename     Packaging    Core enhancements     Scaffolding   Domain port      Harness port   Hard
to pgloom  & release    (gap-fill)            new repo      (roles, BRAID,   (scenarios,    cutover
                                                             worktrees,       fixtures)
                                                             PRs, Telegram)
↓ pgloom repo work ↓                          ↓ engineering-orchestrator repo work ↓
```

---

# PHASE 0a — Rename `orchestrator-core` to `pgloom`

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
- engineering-orchestrator pins to a specific minor: `pgloom>=0.2,<0.3`.

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
- "Embedding pgloom in your service" — pointer to `engineering-orchestrator` once it lands as a reference consumer.
- Link to `docs/architecture.md`, `docs/postgres-schema.md`, `docs/scenario-harness.md`.

## 0.7 — Acceptance for Phase 0

- `pip install pgloom==0.1.0` works on a fresh Python 3.12.
- `pgloom --help` exits 0 from an installed (non-editable) wheel.
- `LICENSE`, `CHANGELOG.md`, `py.typed`, README badges all present.
- Release workflow has run end-to-end at least once (cut a `v0.1.0` tag against a TestPyPI dry run; promote to PyPI when satisfied).
- Schema files (`pgloom/db/schema/*.sql`) are bundled in the wheel — verified with `unzip -l dist/*.whl | grep schema`.

---

# PHASE 0.5 — pgloom enhancements (gap fill)

**Goal:** close the gaps that the reference orchestrator exposes, so engineering-orchestrator can be a thin domain layer rather than a parallel runtime. Nothing here is huge; each is a targeted addition.

The reference orchestrator does several things that `pgloom` today either stubs or omits. Five of them are real blockers for a clean port; one is quality-of-life. Land them all in 0.2.0 so the port consumes a stable surface.

## 0.5.1 — Bounded subprocess runner *(blocker)*

**Why.** engineering-orchestrator constantly shells out: `git`, `gh`, `claude`, `codex`, `bash`. The reference's `_run_bounded()` does timeout, SIGTERM→SIGKILL escalation, stdout/stderr capture, exit code, and structured result. `pgloom`'s `harness/subprocess.py` is currently 9 lines.

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

Reference's RRF (reciprocal rank fusion) hybrid logic stays in **engineering-orchestrator**; core only ships FTS. Vector support deferred to 0.3.x.

Tests: round-trip put/get/list/delete, search by phrase ranks expected entries first, scoping by workflow_id excludes other workflows.

## 0.5.4 — Pluggable dashboard snapshot *(blocker)*

**Why.** Reference's `dashboard_feed.py` (1,018 LOC) is much richer than `pgloom`'s `dashboard.snapshot()`: per-project task buckets, transition timelines, slot health, BRAID template stats, cost rollups. Downstream orchestrators need a way to extend the snapshot without forking pgloom.

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

pgloom ships a small set of built-in collectors. engineering-orchestrator registers its own (per-project breakdown, BRAID template stats, council vote distribution).

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

Optionally add a foreign-key check on `tasks.blocker_code` once downstream consumers have populated their codes. **Don't** make it FK-enforced in core — engineering-orchestrator may want to declare codes lazily.

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

For engineering-orchestrator running on a single host, the existing local-filesystem write in `artifacts.py` is sufficient. Defer the `StorageBackend` Protocol (S3 / URI-only / etc.) until a downstream consumer actually needs object storage. Saves ~half a day in this phase. The decision is documented here so we don't lose track.

## 0.5.8 — Approval panels (deferred) — *do NOT do in 0.2.0*

The reference's "council voting" (multi-stage approvals across panels) is engineering-specific. Keep `pgloom`'s approvals primitive single-decision. engineering-orchestrator stacks N approvals against the same task and aggregates the verdict in its own logic. Revisit after the port; if multiple downstream orchestrators need it, lift to `pgloom` in 0.3.x.

## 0.5 — Acceptance

- `0.2.0` cut and published with all five blocker items (0.5.1 – 0.5.5) and the notification multiplexer (0.5.6).
- Artifact storage backend (0.5.7) deferred to 0.3.x.
- Mypy/ruff stay clean.
- New schema migrations are idempotent.
- Existing 21 integration tests + 1 scenario test still pass; new tests added for each enhancement.
- Changelog clearly lists the new public surface.

---

# PHASE 1 — `engineering-orchestrator` repo scaffolding

**Goal:** stand up `/Volumes/devssd/oss/engineering-orchestrator` as a real Python project that depends on `pgloom>=0.2,<0.3`. No domain logic yet — just the skeleton, CI, and a runnable CLI that proves the pgloom dependency works end-to-end.

## 1.1 — Repo layout

```
engineering-orchestrator/
├── pyproject.toml                  # name=engineering-orchestrator
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
│   ├── braid.md                    # BRAID graph language
│   ├── migration-from-reference.md # what we ported, what we dropped, gotchas
│   └── operations.md               # launchd, telegram, dashboard
├── engineering_orchestrator/
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
name = "engineering-orchestrator"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "pgloom>=0.2,<0.3",
  # plus anything not in pgloom; e.g. nothing right now since pgloom ships httpx, pydantic, etc.
]
[project.scripts]
engineering-orchestrator = "engineering_orchestrator.cli:app"

[project.urls]
Homepage = "https://github.com/joshorig/engineering-orchestrator"
Repository = "https://github.com/joshorig/engineering-orchestrator"
```

## 1.3 — CLI bootstrap

`engineering_orchestrator/cli.py` imports pgloom's typer app and adds engineering-specific verbs:

```python
from pgloom.cli import app as pgloom_app
import typer

app = typer.Typer(help="Engineering orchestrator built on pgloom")
app.add_typer(pgloom_app, name="pgloom")    # all pgloom verbs available under `engineering-orchestrator pgloom ...`

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

- `engineering-orchestrator pgloom db migrate` works (delegates to `pgloom`).
- `engineering-orchestrator pgloom scenario run scenarios/core/smoke` passes (running pgloom scenarios via the wrapper proves the dependency is wired).
- `pyproject.toml` declares `pgloom>=0.2,<0.3`.
- CI is green on a stub repo with one trivial test.

---

# PHASE 2 — Domain port

**Goal:** port the engineering-specific runtime onto `pgloom`'s primitives. Six tracks; can be parallelized by sub-area but each track has internal ordering.

## Track A — Features and self-repair (engineering-only schema)

Reference has `features` + `feature_children` + `self_repair_issues` + `self_repair_deliberations`. `pgloom` has none of these and shouldn't (they're engineering-specific).

| From | To |
|---|---|
| `bin/orchestrator.py` lines ~10000–11000 (feature finalization) | `engineering_orchestrator/features.py` |
| `bin/orchestrator.py` lines ~8000–10000 (self-repair) | `engineering_orchestrator/self_repair.py` |
| Reference's tables `features`, `feature_children`, `self_repair_issues`, `self_repair_deliberations` | `engineering_orchestrator/db/schema/001_features.sql` and `002_self_repair.sql` |

A **feature** wraps N **tasks** (a `pgloom.workflow` is the right abstraction; the engineering layer adds a `feature_id` foreign key into a `features` table that holds PR metadata + status).

Concretely: each engineering feature = one `pgloom.workflows` row + one `engineering_orchestrator.features` row sharing the same id (or the workflow's metadata holds the feature_id; pick one and document).

Self-repair issues stay engineering-local. They reference `tasks.id` from `pgloom` but track council deliberations in their own tables.

## Track B — Roles as task handlers

Each role becomes a `pgloom.harness.handler.Handler` registered against a task type. The runtime calls `tasks.claim_next` and dispatches; the handler performs the role-specific work and returns a `HandlerResult`.

| Role | Handler module | Task type |
|---|---|---|
| Planner | `roles/planner.py` | `engineering.plan` |
| Implementer | `roles/implementer.py` | `engineering.implement` |
| Reviewer | `roles/reviewer.py` | `engineering.review` |
| QA | `roles/qa.py` | `engineering.qa` |
| Historian | `roles/historian.py` | `engineering.historian` |

The handler signature is pgloom's existing `Handler.handle(task) -> HandlerResult`. Inside each handler:
- **Planner**: invoke Claude (via 0.5.2 `CLIModelProvider`), produce a plan, enqueue child `engineering.implement` tasks via `pgloom.tasks.enqueue_task` with `depends_on` set.
- **Implementer**: create worktree (Track D), invoke Claude/Codex, run local checks via 0.5.1 `run_bounded`, register artifacts via `pgloom.artifacts.register_artifact` (with the local filesystem backend already in pgloom; 0.5.7 deferred), commit + push (Track D), `enqueue` reviewer task as child.
- **Reviewer**: invoke BRAID (Track C), call `pgloom.approvals.request_approval` for each panel, aggregate verdict, either close or push back to implementer with `pgloom.approvals.decide_approval(rejected)`.
- **QA**: subprocess `run_bounded` against project's smoke/regression scripts, register log artifacts, transition task done/blocked.
- **Historian**: write to memory store (0.5.3 `PostgresMemoryStore`), no DB schema changes.

Slot mapping: reference has `{claude, codex, qa}`. In pgloom, slots become rows in `slots` table with `concurrency` set per the reference's per-slot config.

## Track C — BRAID graph runtime

Reference has a graph language for review/implementation workflows. Keep entirely in `engineering_orchestrator/braid/`:

| From | To |
|---|---|
| `braid/templates/*.mmd` | `engineering_orchestrator/braid/templates/*.mmd` (copied verbatim) |
| `braid/generators/*.prompt.md` | `engineering_orchestrator/braid/generators/*.prompt.md` (copied verbatim) |
| `braid/index.json` | runtime-managed; not source-controlled |
| `braid/contract_schema.json` | `engineering_orchestrator/braid/contract_schema.json` |
| Graph traversal logic | `engineering_orchestrator/braid/runner.py` (port from reference's runner; not strictly part of bin/orchestrator.py) |

BRAID does *not* need anything from pgloom beyond `pgloom.prompts.PromptRegistry` (which already exists). Templates are stored in the Prompt registry; runner walks the graph and uses `CLIModelProvider` at each Check: node.

## Track D — Git / GitHub / worktree integration

Lifted mostly verbatim from `bin/worker.py`:

| From | To |
|---|---|
| worker.py `make_worktree`, `remove_worktree`, `_autocommit_worktree`, `push_worktree_branch`, `_detect_secrets_hook_findings` | `engineering_orchestrator/integrations/git.py` |
| worker.py `create_pr` and surrounding | `engineering_orchestrator/integrations/github.py` |

Each function moves to a stateless module with a clear signature; no global state. Subprocess calls go through 0.5.1 `run_bounded`.

Idempotency: PR creation must use `pgloom.idempotency.record_external_action` keyed by `(feature_id, "pr_create")` so a re-run of an implementer task doesn't double-open PRs.

## Track E — Telegram + PPD reports

| From | To |
|---|---|
| `bin/telegram_bot.py` | `engineering_orchestrator/integrations/telegram.py` (library) + `cli.py` `telegram run` (daemon entry point) |
| `bin/ppd_report.py` | `engineering_orchestrator/reports/ppd.py` |

Telegram becomes a `NotificationSink` registered with pgloom via 0.5.6 `MultiplexNotificationSink`. The long-polling daemon listens for commands and dispatches to engineering CLI verbs.

PPD report queries pgloom's `model_usage`, `task_events`, `tasks` tables plus the engineering `features` table. Output stays markdown.

## Track F — Dashboard

| From | To |
|---|---|
| `bin/dashboard_feed.py` (1,018 LOC) | `engineering_orchestrator/dashboard/feed.py` (~300 LOC after dropping FS-specific code) |
| `bin/dashboard_server.py` | `engineering_orchestrator/dashboard/server.py` |
| `orchestrator-dashboard.html` | `engineering_orchestrator/dashboard/static/index.html` |

The feed registers as a `DashboardCollector` plugin (0.5.4) so the snapshot is composed of pgloom's built-in sections + engineering's per-project / per-feature sections.

## Track G — Projects + environment health

| From | To |
|---|---|
| reference `projects` config + validation | `engineering_orchestrator/projects.py` |
| `project_environment_ok()` check helpers | `engineering_orchestrator/environment.py` |

Each project's smoke script + regression script + base branch lives in config. `environment.py` registers per-project checks with pgloom's `health` module so blocking checks pause dispatch.

## What we drop in Phase 2

These exist in the reference and **do not** port:
- Filesystem queue (`queue/queued/`, `queue/claimed/`, etc.) — replaced by pgloom's `tasks` table.
- `state/runtime/transitions.log` — replaced by pgloom's `task_events`.
- `state/runtime/claims/`, `state/runtime/locks/` — replaced by pgloom's `FOR UPDATE SKIP LOCKED` and `resource_locks`.
- `state/runtime/events.jsonl` and `metrics.jsonl` — replaced by pgloom's `task_events` and `model_usage`.
- `bin/migrate_fs_to_engine.py` — N/A; we don't migrate FS state into the new repo.
- The dual-write FS↔SQLite mode in reference's `state_engine.py`.

## Track ordering and parallelism

Suggested order: A → B → D → C → E → F → G. A and B can be done in parallel after the pgloom enhancements land; D unblocks the Implementer handler in B; C is needed for the Reviewer handler in B. E/F/G are independent and can be parallelized.

## Phase 2 acceptance

- All five role handlers exist and pass a unit test with a fake worktree + fake `CLIModelProvider`.
- A full happy-path integration test: enqueue a `engineering.plan` task → handler decomposes to two `engineering.implement` tasks → each completes → `engineering.review` task triggered → `engineering.qa` triggered → feature closed.
- Telegram bot can list active features.
- Dashboard snapshot shows engineering-specific sections.

---

# PHASE 3 — Harness port

**Goal:** port the 60+ scenarios under `harness/scenarios/` to engineering-orchestrator's harness, on top of pgloom's scenario runner.

## 3.1 — Categorize the reference scenarios

From the reference review:

| Category | Count | Disposition |
|---|---|---|
| Self-repair (19, 22, 26, 28, 29, 32, 33, 34, 43) | ~12 | Port. Engineering-specific, valuable regression coverage. |
| State engine (35–39, 49–62) | ~20 | Mostly drop. These tested SQLite migrations; we use pgloom's Postgres migrations which are tested at the pgloom level. Keep 1–2 representative cases as smoke tests. |
| Memory (41, 41a) | 2 | Port to engineering-orchestrator harness once 0.5.3 PostgresMemoryStore exists. |
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

1. Bring up `engineering-orchestrator` against a fresh Postgres database. No state migration from the reference repo.
2. Run one happy-path feature end-to-end on `engineering-orchestrator` to confirm: plan → implement → review → QA → PR open → merge.
3. Drain the reference: stop accepting new tasks, wait for `queue/{queued,claimed,running}` to empty (or hand-resolve the stragglers).
4. Flip launchd plists / systemd units from the reference's `worker.py <slot>` to `engineering-orchestrator <slot>`.
5. Repoint the Telegram bot config and start `engineering-orchestrator telegram run`. Stop the reference's `dashboard_server.py`, start engineering's.

## 4.2 — Sunset (same day or next)

- Reference repo (`/Volumes/devssd/orchestrator`) goes read-only with a top-level `RETIRED.md` pointing to engineering-orchestrator.
- Old reports under `reports/` archive to a snapshot folder.
- Reference repo archived in place. No grace period.

## 4.3 — Phase 4 acceptance

- Reference orchestrator's launchd plists are unloaded.
- Engineering-orchestrator has executed at least one full feature end-to-end in production.
- Telegram bot, dashboard, PPD reports all sourced from engineering-orchestrator.
- Reference repo marked retired.

---

# Risk and dependency summary

| Risk | Likelihood | Mitigation |
|---|---|---|
| `CLIModelProvider` (0.5.2) doesn't capture token counts from `claude` CLI | Medium | Fall back to char-length approximation; document the discrepancy in `model_usage.metadata`. Cost numbers stay best-effort. |
| BRAID graph runtime port is more complex than estimated | Medium | Keep the reference's `.mmd` templates verbatim. Port only the runner. If graph traversal logic is gnarly, parse the Mermaid AST with `mermaid-py` rather than reimplementing. |
| Self-repair workflow has subtle state machine bugs that surface only after migration | High | Port self-repair scenarios *first* in Phase 3, before declaring Phase 2 done. They are the strongest regression net. |
| PyPI Trusted Publishing setup forgotten until tag day | Low | Do a `v0.0.1` dry-run release into TestPyPI early in Phase 0 to flush out config issues. |
| engineering-orchestrator pin on `pgloom>=0.2,<0.3` blocks pgloom 0.3 release | Expected, by design | When pgloom 0.3 lands, bump engineering-orchestrator dep range and test. Standard semver upgrade. |
| Reference orchestrator's filesystem queue contains in-flight tasks at cutover | Medium | Drain by halting enqueue + waiting for queue/{queued,claimed,running} to empty before flipping launchd. Manual rerun any survivors via engineering CLI. |
| Hard cutover hits an undiscovered bug after launchd flip | Accepted (high risk tolerance) | engineering-orchestrator CLI keeps `pgloom db reset --yes` available; reference launchd plists are stashed not deleted, so a same-day rollback is possible if needed. |

---

# Effort summary

| Phase | Scope | Estimate |
|---|---|---|
| 0a — rename to pgloom | mechanical sed sweep + dir rename + green test run | ~30 minutes |
| 0 — packaging & release | metadata, MIT license, changelog, release workflow, README | 1–2 days |
| 0.5 — pgloom enhancements | 5 blocker items + 1 QoL item (multiplexer); 0.5.7 deferred | 3–5 days |
| 1 — repo scaffolding | pyproject, layout, CI, smoke | 1 day |
| 2 — domain port | 7 tracks; A/B/D are the bulk | 2–3 weeks |
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
bin/orchestrator.py self-repair          →  engineering_orchestrator.self_repair (Phase 2 Track A)
bin/orchestrator.py council voting       →  engineering_orchestrator.council (Phase 2 Track B)
bin/orchestrator.py feature finalization →  engineering_orchestrator.features (Phase 2 Track A)
bin/worker.py worker loop                →  pgloom.harness.runner (already exists)
bin/worker.py worktree mgmt              →  engineering_orchestrator.integrations.git (Phase 2 Track D)
bin/worker.py PR create                  →  engineering_orchestrator.integrations.github (Phase 2 Track D)
bin/worker.py code execution (Claude)    →  pgloom.models.cli (Phase 0.5.2)
bin/worker.py timeout/SIGTERM/SIGKILL    →  pgloom.harness.subprocess (Phase 0.5.1)
bin/state_engine.py                      →  drop entirely (replaced by pgloom's Postgres)
bin/dashboard_feed.py                    →  engineering_orchestrator.dashboard.feed (Phase 2 Track F)
bin/dashboard_server.py                  →  engineering_orchestrator.dashboard.server (Phase 2 Track F)
bin/telegram_bot.py                      →  engineering_orchestrator.integrations.telegram (Phase 2 Track E)
bin/ppd_report.py                        →  engineering_orchestrator.reports.ppd (Phase 2 Track E)
bin/migrate_fs_to_engine.py              →  drop entirely
queue/* directories                      →  drop entirely (Postgres replaces FS queue)
state/runtime/transitions.log            →  pgloom.task_events (already exists)
state/runtime/claims/, locks/            →  pgloom lease + resource_locks (already exists)
state/runtime/metrics.jsonl              →  pgloom.model_usage (already exists)
state/migrations/                        →  drop (pgloom handles its own; engineering adds 001-003 of its own)
roles/{planner,implementer,...}/README   →  engineering_orchestrator/roles/{role}.py (Phase 2 Track B)
braid/templates/*.mmd                    →  engineering_orchestrator/braid/templates/*.mmd (verbatim)
braid/generators/*.prompt.md             →  engineering_orchestrator/braid/generators/*.prompt.md (verbatim)
braid/contract_schema.json               →  engineering_orchestrator/braid/contract_schema.json (verbatim)
.claude/skills/*                         →  copy verbatim; engineering_orchestrator.skills validates trust
config/orchestrator.example.json         →  engineering_orchestrator/config.py + .env.example
harness/run_scenario.py                  →  engineering_orchestrator harness wrapper around pgloom's runner
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
5. **PyPI name availability:** confirmed `pgloom` is unclaimed on PyPI as of plan-write time (`https://pypi.org/pypi/pgloom/json` → 404).
6. **Cutover:** hard flip after Phase 3 acceptance. No dual-run.
7. **Artifact storage backend (0.5.7):** deferred to 0.3.x; local filesystem write is sufficient for engineering-orchestrator.
8. **Approval panels:** stay in engineering-orchestrator; not lifted to pgloom for 0.2.0.

# Remaining one-time setup before Phase 0a can start

1. **TestPyPI account.** Register at `https://test.pypi.org/account/register/` as `joshorig`. Two-minute task. Separate from PyPI proper.
2. **(Optional) Two-factor auth on both PyPI and TestPyPI.** Strongly recommended even with Trusted Publishing, because account compromise still allows the publisher config itself to be tampered with.
3. **GitHub repo creation.** Either rename an existing `joshorig/orchestrator-core` repo to `joshorig/pgloom` (via GitHub UI → Settings → rename), or create a fresh `joshorig/pgloom` repo and push the renamed local tree. The local rename happens in Phase 0a.
4. **GitHub repo for engineering-orchestrator.** Can be created later in Phase 1; not a Phase 0 prerequisite.

Once items 1 and 3 are done, Phase 0a (rename) can run in roughly thirty minutes, after which Phase 0 (packaging + release) can proceed.

# Next Steps 1-10 Completion

## Summary

- Item 1, CLI verbs: added `db check`, `db reset --yes`, `task list`, `task show`, top-level `reaper`, and top-level `health`.
- Item 2, slot concurrency: `claim_next` now honors enabled `slots.concurrency`; missing slot rows remain unlimited.
- Item 3, dependency/resource indexes: added `003_indexes.sql` with dependency and resource expiry indexes.
- Item 4, retry policy: `retry_or_fail_task` now resolves `payload.retry_policy`, caps attempts, computes policy delay, and records policy metadata on events.
- Item 5, reaper and approval expiry: added `expire_pending_approvals` and `reaper.sweep`; exhausted leases now fail tasks and block dependents.
- Item 6, notifications: added Pydantic notification model, logging/null sinks, default sink swapping, and best-effort emits from task/workflow/approval transitions.
- Item 7, workflow aggregation tests: added integration coverage for done, failed, blocked, and awaiting-approval workflow aggregation.
- Item 8, setup report cleanup: bootstrap writes `.local/setup-report.md` only; `docs/setup-report.md` was removed.
- Item 9, stub modules: replaced prompts, memory, skills, scheduler, and workers stubs with real typed interfaces and tests.
- Item 10, CI: added `.github/workflows/ci.yml` with lint/type/unit and Postgres integration/scenario jobs.

## Verification Outputs

- `.venv/bin/ruff check orchestrator_core tests`: `All checks passed!`
- `.venv/bin/mypy orchestrator_core`: `Success: no issues found in 57 source files`
- `.venv/bin/pytest tests/unit -q`: `23 passed`
- `.venv/bin/pytest tests/integration -q`: `18 passed`
- `.venv/bin/pytest tests/scenarios -q`: `1 passed`
- `.venv/bin/orchestrator-core --help`: exit 0; help lists `reaper`, `health`, `db`, `workflow`, `task`, `worker`, `scenario`, `dashboard`.
- `orchestrator-core scenario run scenarios/core/smoke`: pass.
- `orchestrator-core scenario run scenarios/core/regression`: pass.
- `bash scripts/bootstrap_dev_env.sh`: exit 0; wrote `.local/setup-report.md`; `docs/setup-report.md` absent.
- `orchestrator-core db migrate`: applied `003_indexes.sql` on dev, then idempotent on subsequent runs.
- `orchestrator-core db check`: `{'ok': True, 'tables': 16, 'missing': []}`.
- Full suite: `.venv/bin/pytest -q`: `42 passed`.

## Deviations And Rationale

- The requested file `docs/reports/next-steps-1-to-10-completion.md` did not exist at start; this report creates it as the required deliverable.
- Existing required scenario YAMLs had already been edited earlier in the fresh-repo implementation before this prompt was executed. This batch preserved their current executable behavior and added the two required new regression scenarios.
- `git diff | grep -iE "github|worktree|braid|ffmpeg|youtube|travel|household"` returns hits from required docs/CI paths and architecture/migration documentation that explicitly state what is out of scope. No domain-specific implementation was added under `orchestrator_core/`.
- The repo is fresh and all files are intent-to-add/uncommitted, so `git diff --stat` includes the full project rather than a small incremental tracked diff.

## Git Diff Stat

```text
 .env.example                                       |   4 +
 .github/workflows/ci.yml                           |  49 ++
 .gitignore                                         |  11 +
 README.md                                          |  35 ++
 docs/architecture.md                               |  12 +
 docs/migration-from-existing-orchestrator.md       |   8 +
 docs/postgres-schema.md                            |  11 +
 docs/prompts/item-09-flesh-out-stubs.md            | 289 +++++++++
 docs/prompts/next-steps-1-to-10.md                 | 671 +++++++++++++++++++++
 docs/scenario-harness.md                           |  10 +
 orchestrator_core/                                 | runtime package
 scenarios/core/                                    | smoke and regression scenarios
 scripts/                                           | bootstrap and local checks
 tests/                                             | unit, integration, scenario tests
 100 files changed, 5315 insertions(+)
```

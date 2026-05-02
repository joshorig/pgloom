# Migration From Existing Orchestrator

The existing `/Volumes/devssd/orchestrator` repo may be used to understand lifecycle ideas,
worker behavior, slot configuration, blockers, health checks, dashboards, and scenario testing.

Do not import code from it. Do not move Git worktree logic, GitHub PR automation, PR sweep,
BRAID-specific behavior, repo-memory mutation policy, or file-backed queue behavior into this
core package. Those belong in future domain packages.

# Architecture

`pgloom` is a reusable orchestration library. Postgres is authoritative for
workflow, task, lease, approval, artifact metadata, model usage, quota, health, and scenario
state. Filesystem storage is allowed only for artifact bytes and logs.

The worker model is one task per process invocation: claim a task with `FOR UPDATE SKIP LOCKED`,
run the registered handler, write a result or blocker, then exit. Supervisors can respawn workers
without embedding orchestration state in process memory.

The old `/Volumes/devssd/orchestrator` checkout is reference-only. Future domain orchestrators can
depend on this package, but this package must not depend on domain apps.

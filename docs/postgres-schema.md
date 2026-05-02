# Postgres Schema

Core tables:

- `workflows`, `tasks`, `task_dependencies`, `task_events`
- `artifacts`, `approvals`, `workers`, `slots`, `health_checks`
- `model_profiles`, `model_usage`, `external_actions`
- `resource_locks`, `quota_buckets`, `scenario_runs`, `scenario_assertions`

Important dispatch behavior is centered on `idx_tasks_claim` and `FOR UPDATE SKIP LOCKED`.
Every state transition records a `task_events` row.

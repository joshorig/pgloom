create index if not exists idx_tasks_claim on tasks(slot, state, priority desc, run_after, created_at);
create index if not exists idx_tasks_workflow on tasks(workflow_id);
create index if not exists idx_tasks_domain_state on tasks(domain, state);
create index if not exists idx_tasks_leases on tasks(state, lease_expires_at);
create index if not exists idx_task_events_task on task_events(task_id, created_at);
create index if not exists idx_artifacts_workflow on artifacts(workflow_id, artifact_type);
create index if not exists idx_approvals_pending on approvals(domain, state, created_at);

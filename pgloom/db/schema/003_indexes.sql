create index if not exists idx_task_dependencies_depends_on
  on task_dependencies(depends_on_task_id);

create index if not exists idx_resource_locks_expires_at
  on resource_locks(expires_at);

create table if not exists workflows (
  id text primary key,
  domain text not null,
  name text not null,
  state text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists tasks (
  id text primary key,
  workflow_id text not null references workflows(id) on delete cascade,
  domain text not null,
  task_type text not null,
  slot text not null,
  state text not null,
  priority integer not null default 0,
  payload jsonb not null default '{}'::jsonb,
  result jsonb not null default '{}'::jsonb,
  attempt integer not null default 0,
  max_attempts integer not null default 3,
  run_after timestamptz not null default now(),
  lease_owner text,
  lease_expires_at timestamptz,
  blocker_code text,
  blocker_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists task_dependencies (
  task_id text not null references tasks(id) on delete cascade,
  depends_on_task_id text not null references tasks(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key(task_id, depends_on_task_id)
);

create table if not exists task_events (
  id bigserial primary key,
  task_id text references tasks(id) on delete cascade,
  workflow_id text references workflows(id) on delete cascade,
  event_type text not null,
  from_state text,
  to_state text,
  message text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists artifacts (
  id text primary key,
  workflow_id text not null references workflows(id) on delete cascade,
  task_id text references tasks(id) on delete set null,
  artifact_type text not null,
  uri text not null,
  sha256 text,
  size_bytes bigint,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists approvals (
  id text primary key,
  workflow_id text not null references workflows(id) on delete cascade,
  task_id text references tasks(id) on delete cascade,
  domain text not null,
  state text not null,
  prompt text not null,
  response jsonb not null default '{}'::jsonb,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists workers (
  id text primary key,
  slot text not null,
  state text not null,
  current_task_id text,
  last_heartbeat_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists slots (
  name text primary key,
  enabled boolean not null default true,
  concurrency integer not null default 1,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists health_checks (
  id bigserial primary key,
  name text not null,
  status text not null,
  blocks_dispatch boolean not null default false,
  message text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists model_profiles (
  name text primary key,
  provider text not null,
  model text not null,
  settings jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists model_usage (
  id bigserial primary key,
  workflow_id text references workflows(id) on delete set null,
  task_id text references tasks(id) on delete set null,
  profile_name text,
  input_tokens integer not null default 0,
  output_tokens integer not null default 0,
  cost_usd numeric(12,6) not null default 0,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists external_actions (
  id text primary key,
  idempotency_key text not null unique,
  action_type text not null,
  status text not null,
  result jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists resource_locks (
  resource_key text primary key,
  owner_id text not null,
  task_id text references tasks(id) on delete set null,
  expires_at timestamptz not null,
  created_at timestamptz not null default now()
);

create table if not exists quota_buckets (
  name text primary key,
  capacity numeric not null,
  remaining numeric not null,
  reset_at timestamptz,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists scenario_runs (
  id text primary key,
  scenario_id text not null,
  status text not null,
  report jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  finished_at timestamptz
);

create table if not exists scenario_assertions (
  id bigserial primary key,
  scenario_run_id text not null references scenario_runs(id) on delete cascade,
  assertion_key text not null,
  passed boolean not null,
  message text,
  created_at timestamptz not null default now()
);

create table if not exists token_savings (
  id bigserial primary key,
  scope_id text not null,
  workflow_id text references workflows(id) on delete set null,
  task_id text references tasks(id) on delete set null,
  model_usage_id bigint references model_usage(id) on delete set null,
  profile_name text,
  input_tokens_original integer not null,
  input_tokens_after integer not null,
  tokens_saved integer not null,
  reduction_ratio numeric not null,
  estimated_cost_saved_usd numeric(12,6) not null default 0,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint token_savings_non_negative check (
    input_tokens_original >= 0
    and input_tokens_after >= 0
    and tokens_saved >= 0
    and estimated_cost_saved_usd >= 0
  ),
  constraint token_savings_consistent_counts check (
    tokens_saved = greatest(0, input_tokens_original - input_tokens_after)
  ),
  constraint token_savings_ratio_range check (
    reduction_ratio >= 0 and reduction_ratio <= 1
  )
);

create index if not exists idx_token_savings_scope
  on token_savings(scope_id);

create index if not exists idx_token_savings_task
  on token_savings(task_id);

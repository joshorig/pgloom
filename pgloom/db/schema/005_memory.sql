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

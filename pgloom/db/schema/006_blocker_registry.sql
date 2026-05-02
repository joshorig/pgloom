create table if not exists blocker_codes (
  code text primary key,
  name text not null,
  severity smallint not null check (severity between 0 and 5),
  retryable boolean not null default true,
  category text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

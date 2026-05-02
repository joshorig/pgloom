#!/usr/bin/env bash
set -euo pipefail

DEV_DB="${PGLOOM_DEV_DB:-pgloom_dev}"
TEST_DB="${PGLOOM_TEST_DB:-pgloom_test}"

command -v psql >/dev/null 2>&1 || { echo "psql: missing"; exit 1; }
psql --version

if command -v pg_isready >/dev/null 2>&1; then
  pg_isready || true
else
  echo "pg_isready: missing"
fi

psql -d postgres -c "select version();" >/dev/null
for db in "$DEV_DB" "$TEST_DB"; do
  if psql -lqt | cut -d '|' -f 1 | grep -qw "$db"; then
    echo "$db: present"
  else
    echo "$db: missing"
  fi
done

#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/Volumes/devssd/repos/oss/pgloom}"
REF_ORCH="${REF_ORCH:-/Volumes/devssd/orchestrator}"
REPORT="$ROOT/.local/setup-report.md"
DEV_DB="${PGLOOM_DEV_DB:-pgloom_dev}"
TEST_DB="${PGLOOM_TEST_DB:-pgloom_test}"

mkdir -p "$ROOT/.local"
cd "$ROOT"

if command -v brew >/dev/null 2>&1 && [ -d "$(brew --prefix postgresql@16 2>/dev/null)/bin" ]; then
  PATH="$(brew --prefix postgresql@16)/bin:$PATH"
  export PATH
fi

timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

{
  echo "# Setup Report"
  echo
  echo "- date: $(timestamp)"
  echo "- root: $ROOT"
  echo "- os: $(uname -a)"
  if command -v sw_vers >/dev/null 2>&1; then echo "- macos: $(sw_vers -productVersion)"; fi
} > "$REPORT"

if [ -d "$REF_ORCH" ]; then
  echo "- reference_orchestrator_status: present" >> "$REPORT"
else
  echo "- reference_orchestrator_status: missing" >> "$REPORT"
fi

if command -v brew >/dev/null 2>&1; then
  HAVE_BREW=1
  echo "- homebrew: $(brew --version | head -1)" >> "$REPORT"
else
  HAVE_BREW=0
  echo "- homebrew: missing" >> "$REPORT"
fi

if PYTHON_BIN="$(scripts/select_python.sh 2>/dev/null)"; then
  echo "- python_selected: $PYTHON_BIN ($($PYTHON_BIN --version))" >> "$REPORT"
else
  if [ "$HAVE_BREW" -eq 1 ]; then
    brew install python@3.12
    PYTHON_BIN="python3.12"
    echo "- python_installed: python@3.12" >> "$REPORT"
  else
    echo "- setup_status: manual_python_required" >> "$REPORT"
    echo "Python >= 3.11 missing and Homebrew unavailable. Install Python manually."
    exit 1
  fi
fi

if command -v psql >/dev/null 2>&1; then
  echo "- postgres_client: $(psql --version)" >> "$REPORT"
else
  if [ "$HAVE_BREW" -eq 1 ]; then
    brew install postgresql@16
    echo "- postgres_client_installed: postgresql@16" >> "$REPORT"
  else
    echo "- setup_status: manual_postgres_required" >> "$REPORT"
    echo "Postgres client missing and Homebrew unavailable. Install Postgres manually."
    exit 1
  fi
fi

if command -v pg_isready >/dev/null 2>&1 && pg_isready >/dev/null 2>&1; then
  echo "- postgres_server: ready" >> "$REPORT"
else
  echo "- postgres_server: not_ready_initially" >> "$REPORT"
  if [ "$HAVE_BREW" -eq 1 ]; then
    brew services start postgresql@16 || true
    sleep 2
  fi
fi

if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
  echo "- venv: created" >> "$REPORT"
else
  echo "- venv: existing" >> "$REPORT"
fi

source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"

if command -v createdb >/dev/null 2>&1 && psql -d postgres -c "select 1" >/dev/null 2>&1; then
  createdb "$DEV_DB" 2>/dev/null || true
  createdb "$TEST_DB" 2>/dev/null || true
  echo "- databases: checked_or_created" >> "$REPORT"
else
  echo "- databases: skipped_postgres_unavailable" >> "$REPORT"
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "- env_file: created_from_example" >> "$REPORT"
else
  echo "- env_file: existing_not_overwritten" >> "$REPORT"
fi

echo "- setup_status: complete" >> "$REPORT"
echo "Wrote $REPORT"

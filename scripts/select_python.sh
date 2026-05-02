#!/usr/bin/env bash
set -euo pipefail

for py in python3.12 python3.11 python3; do
  if command -v "$py" >/dev/null 2>&1; then
    version="$("$py" - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
    major="${version%%.*}"
    minor="${version#*.}"
    if [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; then
      echo "$py"
      exit 0
    fi
  fi
done

echo "Python >= 3.11 not found" >&2
exit 1

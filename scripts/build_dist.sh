#!/usr/bin/env bash
set -euo pipefail

.venv/bin/python -m pip install --upgrade build twine
.venv/bin/python -m build
.venv/bin/python -m twine check dist/*

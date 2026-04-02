#!/usr/bin/env bash
# Gate 2-Python: Python linting (ruff)
echo "Gate 2-Python: Lint (ruff)"
if [ -f "athena/pyproject.toml" ]; then
  if [ -f "athena/.venv/bin/python" ]; then
    cd athena && .venv/bin/python -m ruff check src/ 2>&1
    exit $?
  elif command -v ruff &>/dev/null; then
    cd athena && ruff check src/ 2>&1
    exit $?
  else
    echo "[WARN] ruff not found — install: pip install ruff"
    exit 0
  fi
else
  echo "[SKIP] No athena/pyproject.toml found"
  exit 0
fi

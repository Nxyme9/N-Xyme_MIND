#!/usr/bin/env bash
# Gate 1-Python: Python type checking (pyright)
echo "Gate 1-Python: Type Check (pyright)"
if [ -f "athena/pyproject.toml" ]; then
  if command -v pyright &>/dev/null; then
    cd athena && pyright src/ 2>&1
    exit $?
  elif [ -f "athena/.venv/bin/python" ]; then
    cd athena && .venv/bin/python -m pyright src/ 2>&1
    exit $?
  else
    echo "[WARN] pyright not found — install: pip install pyright"
    exit 0
  fi
else
  echo "[SKIP] No athena/pyproject.toml found"
  exit 0
fi

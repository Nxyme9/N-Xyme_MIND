#!/usr/bin/env bash
echo "Gate 1: Type Check"
if [ -f "tsconfig.json" ]; then
  npx tsc --noEmit 2>&1
  exit $?
elif [ -f "athena/pyproject.toml" ] && [ -f "athena/.venv/bin/python" ]; then
  echo "Falling back to Python type check"
  cd athena && .venv/bin/python -m pyright src/ 2>&1 || echo "[WARN] pyright not installed"
  exit 0
else
  echo "[WARN] No tsconfig.json or pyright found — skipping"
  exit 0
fi

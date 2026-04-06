#!/usr/bin/env bash
# Gate 1-Python: Python type checking (pyright)
echo "Gate 1-Python: Type Check (pyright)"
if [ -f "athena/pyproject.toml" ]; then
  if command -v pyright &>/dev/null; then
    cd athena && pyright src/ 2>&1 | grep -E "error:|Error" | grep -v "warning:" | grep -v "warnings"
    PYRIGHT_EXIT=${PIPESTATUS[0]}
    # Only block on actual errors, not warnings
    ERROR_COUNT=$(cd athena && pyright src/ 2>&1 | grep -c "error:" || true)
    if [ "$ERROR_COUNT" -gt 0 ]; then
      echo "❌ $ERROR_COUNT type error(s) found"
      exit 1
    fi
    echo "✓ No type errors (warnings OK)"
    exit 0
  elif [ -f "athena/.venv/bin/python" ]; then
    cd athena && .venv/bin/python -m pyright src/ 2>&1 | grep -E "error:|Error" | grep -v "warning:"
    PYRIGHT_EXIT=${PIPESTATUS[0]}
    ERROR_COUNT=$(cd athena && .venv/bin/python -m pyright src/ 2>&1 | grep -c "error:" || true)
    if [ "$ERROR_COUNT" -gt 0 ]; then
      echo "❌ $ERROR_COUNT type error(s) found"
      exit 1
    fi
    echo "✓ No type errors (warnings OK)"
    exit 0
  else
    echo "[WARN] pyright not found — install: pip install pyright"
    exit 0
  fi
else
  echo "[SKIP] No athena/pyproject.toml found"
  exit 0
fi

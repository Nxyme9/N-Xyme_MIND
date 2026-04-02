#!/usr/bin/env bash
# L0 Health Check (<1s) — Pre-flight blink
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ERRORS=0

# Workspace readable
[ -r "$ROOT" ] || { echo "FAIL: Workspace not readable"; ERRORS=$((ERRORS+1)); }

# Configs exist
[ -f "$ROOT/opencode.json" ] || { echo "FAIL: opencode.json missing"; ERRORS=$((ERRORS+1)); }
[ -f "$ROOT/AGENTS.md" ] || { echo "FAIL: AGENTS.md missing"; ERRORS=$((ERRORS+1)); }

# No hardcoded paths (fast: only check src/, not venvs/)
HARDCODED=$(grep -r "/home/nxyme/nx_openmore" "$ROOT/src/" "$ROOT/athena/src/" --include="*.py" 2>/dev/null | wc -l || true)
[ "$HARDCODED" -eq 0 ] || { echo "FAIL: $HARDCODED hardcoded paths"; ERRORS=$((ERRORS+1)); }

# Venv exists
[ -f "$ROOT/venvs/athena/bin/python" ] || { echo "FAIL: Python venv missing"; ERRORS=$((ERRORS+1)); }

if [ $ERRORS -eq 0 ]; then
    echo "L0: PASS"
    exit 0
else
    echo "L0: FAIL ($ERRORS errors)"
    exit 1
fi

#!/usr/bin/env bash
# L2 Health Check (<60s) — Deep vitals
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ERRORS=0

echo "=== L2 Deep Vitals ==="

# Config drift
echo "Config files valid..."
python3 -m json.tool "$ROOT/opencode.json" > /dev/null 2>&1 || { echo "FAIL: opencode.json invalid JSON"; ERRORS=$((ERRORS+1)); }

# Broken symlinks
BROKEN=$(find "$ROOT" -not -path "*/venvs/*" -not -path "*/.git/*" -not -path "*/node_modules/*" -not -path "*/.cache/*" -xtype l 2>/dev/null | wc -l)
[ "$BROKEN" -eq 0 ] || { echo "WARN: $BROKEN broken symlinks"; }

# Python deps intact
echo "Python deps..."
"$ROOT/.venv/bin/python3" -c "import dotenv,requests,pydantic,diskcache,rich" 2>/dev/null || { echo "FAIL: Core Python deps broken"; ERRORS=$((ERRORS+1)); }

# Disk space
AVAILABLE=$(df -h "$ROOT" | awk 'NR==2{print $4}' | sed 's/G//')
[ "${AVAILABLE:-0}" -gt 5 ] || { echo "WARN: Low disk space (${AVAILABLE}G)"; }

# AGENTS.md has task rules
grep -q "load_skills" "$ROOT/AGENTSold.md" 2>/dev/null || { echo "WARN: AGENTS.md missing task() rules"; }

if [ $ERRORS -eq 0 ]; then
    echo "L2: PASS"
    exit 0
else
    echo "L2: FAIL ($ERRORS errors)"
    exit 1
fi

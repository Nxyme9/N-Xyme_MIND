#!/usr/bin/env bash
# L1 Health Check (<10s) — Service pulse
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ERRORS=0

# Ollama alive
curl -sf --max-time 3 http://localhost:11434/api/tags > /dev/null 2>&1 || { echo "WARN: Ollama not running"; }

# MCP binaries exist
[ -f /usr/bin/mcp-server-sequential-thinking ] || { echo "FAIL: sequential-thinking MCP missing"; ERRORS=$((ERRORS+1)); }
[ -f /usr/bin/mcp-server-memory ] || { echo "FAIL: memory MCP missing"; ERRORS=$((ERRORS+1)); }
[ -f /usr/bin/context7-mcp ] || { echo "FAIL: context7 MCP missing"; ERRORS=$((ERRORS+1)); }
[ -f /usr/bin/mcp-server-filesystem ] || { echo "FAIL: filesystem MCP missing"; ERRORS=$((ERRORS+1)); }

# Python venv works
"$ROOT/venvs/athena/bin/python" -c "import dotenv" 2>/dev/null || { echo "FAIL: Python venv broken"; ERRORS=$((ERRORS+1)); }

# OpenCode binary exists
[ -f ~/.opencode/bin/opencode ] || { echo "FAIL: OpenCode binary missing"; ERRORS=$((ERRORS+1)); }

if [ $ERRORS -eq 0 ]; then
    echo "L1: PASS"
    exit 0
else
    echo "L1: FAIL ($ERRORS errors)"
    exit 1
fi

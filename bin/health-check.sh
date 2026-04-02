#!/usr/bin/env bash
# Health check for self-contained workspace
set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; ERRORS=$((ERRORS+1)); }
warn() { echo -e "${YELLOW}!${NC} $1"; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ERRORS=0
echo "=== Workspace Health Check ==="
echo "Root: $ROOT"
echo ""

# 1. OpenCode binary
echo "--- OpenCode ---"
if [ -f ~/.opencode/bin/opencode ]; then
  pass "Binary exists: $(~/.opencode/bin/opencode --version 2>/dev/null || echo 'version unknown')"
else
  warn "OpenCode binary not found at ~/.opencode/bin/opencode"
fi

# 2. Config files (self-contained)
echo ""
echo "--- Config ---"
[ -f "$ROOT/.opencode/opencode.json" ] && pass ".opencode/opencode.json exists" || fail ".opencode/opencode.json missing"
[ -f "$ROOT/config/opencode.json" ] && pass "config/opencode.json exists" || fail "config/opencode.json missing"
[ -f "$ROOT/config/oh-my-opencode.json" ] && pass "oh-my-opencode.json exists" || fail "oh-my-opencode.json missing"

# Check for hardcoded paths
HARDCODED=$(grep -rn "/home/nxyme" "$ROOT/config/" "$ROOT/bin/" "$ROOT/.opencode/opencode.json" 2>/dev/null | grep -v "repair-paths" | grep -v "stays LOCAL" || true)
if [ -z "$HARDCODED" ]; then
  pass "No hardcoded paths in configs"
else
  fail "Hardcoded paths found — run ./bin/repair-paths.sh"
fi

# Check for symlinks
SYMLINKS=$(find "$ROOT" -type l 2>/dev/null | grep -v node_modules | grep -v ".venv" | wc -l)
[ "$SYMLINKS" -eq 0 ] && pass "No symlinks (self-contained)" || warn "$SYMLINKS symlinks found"

# 3. MCP packages
echo ""
echo "--- MCP Packages ---"
if [ -d "$ROOT/athena/.venv/bin" ]; then
  for mod in mcp_server_git sequential_thinking mcp_memory_service mcp; do
    if "$ROOT/athena/.venv/bin/python3" -c "import $mod" 2>/dev/null; then
      pass "$mod installed"
    else
      fail "$mod not installed"
    fi
  done
else
  fail "Athena venv not found"
fi

# 4. Athena MCP server
echo ""
echo "--- Athena ---"
ATHENA_VENV="$ROOT/athena/.venv/bin/python3"
if [ -f "$ATHENA_VENV" ]; then
  pass "Athena venv exists"
else
  fail "Athena venv not found at $ATHENA_VENV"
fi

# 5. Quality gates
echo ""
echo "--- Quality Gates ---"
for gate in gate-5-secrets.sh gate-6-placeholders.sh gate-all.sh; do
  [ -x "$ROOT/bin/quality-gates/$gate" ] && pass "$gate executable" || fail "$gate missing/not executable"
done

# 6. Git hooks
echo ""
echo "--- Git Hooks ---"
[ -x "$ROOT/.git/hooks/pre-commit" ] && pass "pre-commit hook" || fail "pre-commit hook missing"
[ -x "$ROOT/.git/hooks/pre-push" ] && pass "pre-push hook" || fail "pre-push hook missing"

# 7. Git tracking
echo ""
echo "--- Git Tracking ---"
CONTEXT_TRACKED=$(git -C "$ROOT" ls-files context/ 2>/dev/null | wc -l)
[ "$CONTEXT_TRACKED" -eq 0 ] && pass "No context/ files tracked" || fail "$CONTEXT_TRACKED context/ files still tracked"

# 8. Ollama (optional)
echo ""
echo "--- Ollama (optional) ---"
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
  pass "Ollama running"
else
  warn "Ollama not responding at localhost:11434"
fi

# Summary
echo ""
echo "==================================="
if [ $ERRORS -eq 0 ]; then
  echo -e "${GREEN}All checks passed!${NC}"
else
  echo -e "${RED}$ERRORS check(s) failed — run ./bin/repair-paths.sh to fix path issues${NC}"
fi
exit $ERRORS

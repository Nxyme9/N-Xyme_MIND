#!/usr/bin/env bash
# bin/ensure-services.sh — Pre-flight for all services (Ollama + MCPs)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ERRORS=0
WARNINGS=0
PASSES=0

# ── Colors ──
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

pass()  { echo -e "${GREEN}  ✓${NC} $*"; PASSES=$((PASSES+1)); }
warn()  { echo -e "${YELLOW}  ⚠${NC} $*"; WARNINGS=$((WARNINGS+1)); }
fail()  { echo -e "${RED}  ✗${NC} $*"; ERRORS=$((ERRORS+1)); }
header() { echo -e "\n${CYAN}── $* ──${NC}"; }

# ── 1. Workspace ──
header "Workspace"
[ -d "$ROOT" ] && pass "Workspace root: $ROOT" || fail "Workspace root missing"
[ -f "$ROOT/opencode.json" ] && pass "opencode.json present" || fail "opencode.json missing"
[ -f "$ROOT/AGENTS.md" ] && pass "AGENTS.md present" || fail "AGENTS.md missing"
[ -f "$ROOT/n-xyme-mind.sh" ] && pass "n-xyme-mind.sh present" || fail "n-xyme-mind.sh missing"

# ── 2. Python venvs ──
header "Python Venvs"
ATHENA_VENV="$ROOT/venvs/athena"
if [ -f "$ATHENA_VENV/bin/python" ]; then
    pass "Athena venv exists"
    if "$ATHENA_VENV/bin/python" -c "import dotenv" 2>/dev/null; then
        pass "Athena venv: dotenv imports OK"
    else
        fail "Athena venv: dotenv import failed"
    fi
else
    fail "Athena venv missing at $ATHENA_VENV"
fi

for pkg in athena-context-mcp nx-mind-mcp trigger-guardian-mcp; do
    PKG_DIR="$ROOT/packages/$pkg"
    if [ -d "$PKG_DIR" ]; then
        # Check for venv in package
        VENV="$PKG_DIR/venv"
        [ -d "$VENV" ] || VENV="$PKG_DIR/.venv"
        if [ -f "$VENV/bin/python" ]; then
            pass "$pkg: venv OK"
        else
            warn "$pkg: no venv found (expected venv or .venv)"
        fi
    else
        fail "$pkg: package directory missing"
    fi
done

# ── 3. Ollama ──
header "Ollama"
if command -v ollama &>/dev/null; then
    pass "ollama binary in PATH"
    if curl -sf --max-time 3 http://localhost:11434/api/tags &>/dev/null; then
        pass "Ollama server responding"
        # Check embedding model
        EMBED_MODEL="${OLLAMA_EMBED_MODEL:-nomic-embed-text}"
        if ollama list 2>/dev/null | grep -q "$EMBED_MODEL"; then
            pass "Embedding model '$EMBED_MODEL' present"
        else
            warn "Embedding model '$EMBED_MODEL' not pulled (run: bin/ensure-ollama.sh)"
        fi
    else
        warn "Ollama server not responding (run: bin/ensure-ollama.sh)"
    fi
else
    warn "ollama binary not in PATH"
fi

# ── 4. MCP Import Verification ──
header "MCP Import Checks"

# athena
if "$ATHENA_VENV/bin/python" -c "from athena import mcp_server" 2>/dev/null; then
    pass "athena: import OK"
else
    fail "athena: import failed"
fi

# athena-context
AC_MCP="$ROOT/packages/athena-context-mcp"
if [ -d "$AC_MCP/venv" ]; then
    AC_PY="$AC_MCP/venv/bin/python"
elif [ -d "$AC_MCP/.venv" ]; then
    AC_PY="$AC_MCP/.venv/bin/python"
else
    AC_PY="python3"
fi
if PYTHONPATH="$AC_MCP" "$AC_PY" -m athena_context_mcp --help &>/dev/null; then
    pass "athena-context: module OK"
else
    fail "athena-context: module failed"
fi

# nx-mind
NM_MCP="$ROOT/packages/nx-mind-mcp"
if [ -d "$NM_MCP/venv" ]; then
    NM_PY="$NM_MCP/venv/bin/python"
elif [ -d "$NM_MCP/.venv" ]; then
    NM_PY="$NM_MCP/.venv/bin/python"
else
    NM_PY="python3"
fi
if PYTHONPATH="$NM_MCP" "$NM_PY" -m nx_mind_mcp --help &>/dev/null; then
    pass "nx-mind: module OK"
else
    fail "nx-mind: module failed"
fi

# trigger-guardian
TG_MCP="$ROOT/packages/trigger-guardian-mcp"
if [ -d "$TG_MCP/venv" ]; then
    TG_PY="$TG_MCP/venv/bin/python"
elif [ -d "$TG_MCP/.venv" ]; then
    TG_PY="$TG_MCP/.venv/bin/python"
else
    TG_PY="python3"
fi
if PYTHONPATH="$TG_MCP" "$TG_PY" -m trigger_guardian_mcp --help &>/dev/null; then
    pass "trigger-guardian: module OK"
else
    fail "trigger-guardian: module failed"
fi

# unified-memory (uses athena venv)
if PYTHONPATH="$ROOT" "$ATHENA_VENV/bin/python" -c "import src.memory.mcp_server" 2>/dev/null; then
    pass "unified-memory: import OK"
else
    fail "unified-memory: import failed"
fi

# ── 5. Global MCPs ──
header "Global MCPs (npx)"
for mcp in "@modelcontextprotocol/server-sequential-thinking" "@modelcontextprotocol/server-memory" "@upstash/context7-mcp" "mcp-server-filesystem"; do
    if command -v npx &>/dev/null; then
        pass "npx available (for $mcp)"
    else
        warn "npx not available (needed for $mcp)"
    fi
done

# ── 6. OpenCode ──
header "OpenCode"
OPENCODE_PATH="${OPENCODE_PATH:-$HOME/.opencode/bin/opencode}"
if [ -x "$OPENCODE_PATH" ]; then
    pass "OpenCode binary: $OPENCODE_PATH"
else
    fail "OpenCode binary not found at $OPENCODE_PATH"
fi

# ── Summary ──
echo ""
echo "═══════════════════════════════════════════"
echo -e "  ${GREEN}PASS: $PASSES${NC}  ${YELLOW}WARN: $WARNINGS${NC}  ${RED}FAIL: $ERRORS${NC}"
echo "═══════════════════════════════════════════"

if [ $ERRORS -gt 0 ]; then
    echo -e "\n${RED}Run 'bash bin/mcp-doctor.sh' to diagnose and attempt fixes${NC}"
    exit 1
fi

if [ $WARNINGS -gt 0 ]; then
    echo -e "\n${YELLOW}Warnings present — system may work but check above${NC}"
fi

echo -e "\n${GREEN}All services ready${NC}"
exit 0

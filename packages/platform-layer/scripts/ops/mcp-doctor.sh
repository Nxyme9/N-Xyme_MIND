#!/usr/bin/env bash
# bin/mcp-doctor.sh — Diagnose MCP issues and attempt automatic fixes
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXES_APPLIED=0
ISSUES_FOUND=0

# ── Colors ──
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

pass()  { echo -e "${GREEN}  ✓${NC} $*"; }
warn()  { echo -e "${YELLOW}  ⚠${NC} $*"; }
fail()  { echo -e "${RED}  ✗${NC} $*"; ISSUES_FOUND=$((ISSUES_FOUND+1)); }
fix()   { echo -e "${BLUE}  →${NC} $*"; FIXES_APPLIED=$((FIXES_APPLIED+1)); }
header() { echo -e "\n${CYAN}── $* ──${NC}"; }

# ── Helper: resolve python for a package ──
resolve_python() {
    local pkg_dir="$1"
    local venv="$pkg_dir/venv"
    [ -d "$venv" ] || venv="$pkg_dir/.venv"
    if [ -f "$venv/bin/python" ]; then
        echo "$venv/bin/python"
    else
        echo "python3"
    fi
}

# ── Helper: attempt pip install -e . ──
attempt_install() {
    local pkg_dir="$1"
    local pkg_name="$2"
    local py
    py="$(resolve_python "$pkg_dir")"
    warn "$pkg_name: import failed — attempting 'pip install -e .'"
    if (cd "$pkg_dir" && "$py" -m pip install -e . --quiet 2>&1); then
        fix "$pkg_name: pip install succeeded"
        return 0
    else
        fail "$pkg_name: pip install failed"
        return 1
    fi
}

header "MCP Doctor — Diagnosing & Attempting Fixes"
echo "Workspace: $ROOT"
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"

# ── 1. Environment ──
header "Environment"

# Check if env.sh sources cleanly
if source "$ROOT/env.sh" 2>/dev/null; then
    pass "env.sh sources cleanly"
else
    warn "env.sh had issues — attempting to continue"
fi

# PYTHONPATH
if [ -n "${PYTHONPATH:-}" ]; then
    pass "PYTHONPATH set: $PYTHONPATH"
else
    warn "PYTHONPATH not set — doctor will validate per-MCP"
fi

# ── 2. Athena MCP ──
header "athena"
ATHENA_VENV="$ROOT/venvs/athena"
if [ ! -f "$ATHENA_VENV/bin/python" ]; then
    fail "athena venv missing at $ATHENA_VENV"
    warn "Cannot diagnose athena without venv"
else
    if "$ATHENA_VENV/bin/python" -c "from athena import mcp_server" 2>/dev/null; then
        pass "athena: import OK"
    else
        fail "athena: import failed"
        fix "Attempting pip install -e athena/"
        if (cd "$ROOT/athena" && "$ATHENA_VENV/bin/python" -m pip install -e . --quiet 2>&1); then
            fix "athena: reinstall succeeded"
        else
            fail "athena: reinstall failed — check athena/pyproject.toml"
        fi
    fi
fi

# ── 3. nx-context MCP ──
header "nx-context"
AC_MCP="$ROOT/packages/nx-context-mcp"
AC_PY="$(resolve_python "$AC_MCP")"
if [ ! -d "$AC_MCP" ]; then
    fail "nx-context: package directory missing"
else
    if PYTHONPATH="$AC_MCP" "$AC_PY" -m nx_context_mcp --help &>/dev/null; then
        pass "nx-context: module OK"
    else
        fail "nx-context: module failed"
        attempt_install "$AC_MCP" "nx-context"
    fi
fi

# ── 4. nx-mind MCP ──
header "nx-mind"
NM_MCP="$ROOT/packages/nx-mind-mcp"
NM_PY="$(resolve_python "$NM_MCP")"
if [ ! -d "$NM_MCP" ]; then
    fail "nx-mind: package directory missing"
else
    if PYTHONPATH="$NM_MCP" "$NM_PY" -m nx_mind_mcp --help &>/dev/null; then
        pass "nx-mind: module OK"
    else
        fail "nx-mind: module failed"
        attempt_install "$NM_MCP" "nx-mind"
    fi
fi

# ── 5. trigger-guardian MCP ──
header "trigger-guardian"
TG_MCP="$ROOT/packages/trigger-guardian-mcp"
TG_PY="$(resolve_python "$TG_MCP")"
if [ ! -d "$TG_MCP" ]; then
    fail "trigger-guardian: package directory missing"
else
    if PYTHONPATH="$TG_MCP" "$TG_PY" -m trigger_guardian_mcp --help &>/dev/null; then
        pass "trigger-guardian: module OK"
    else
        fail "trigger-guardian: module failed"
        attempt_install "$TG_MCP" "trigger-guardian"
    fi
fi

# ── 6. unified-memory MCP ──
header "unified-memory"
if [ -f "$ATHENA_VENV/bin/python" ]; then
    if PYTHONPATH="$ROOT" "$ATHENA_VENV/bin/python" -c "import src.memory.mcp_server" 2>/dev/null; then
        pass "unified-memory: import OK"
    else
        fail "unified-memory: import failed"
        # Check if src/memory/mcp_server.py exists
        if [ -f "$ROOT/src/memory/mcp_server.py" ]; then
            pass "unified-memory: source file exists (PYTHONPATH issue)"
            fix "Ensure PYTHONPATH includes $ROOT"
        else
            fail "unified-memory: source file missing at src/memory/mcp_server.py"
        fi
    fi
else
    fail "unified-memory: athena venv missing (shared dependency)"
fi

# ── 7. Ollama ──
header "Ollama"
if command -v ollama &>/dev/null; then
    pass "ollama binary in PATH"
    if curl -sf --max-time 3 http://localhost:11434/api/tags &>/dev/null; then
        pass "Ollama server responding"
        EMBED_MODEL="${OLLAMA_EMBED_MODEL:-nomic-embed-text}"
        if ollama list 2>/dev/null | grep -q "$EMBED_MODEL"; then
            pass "Embedding model '$EMBED_MODEL' present"
        else
            warn "Embedding model '$EMBED_MODEL' not pulled"
            fix "Run: bash bin/ensure-ollama.sh"
        fi
    else
        warn "Ollama server not responding"
        fix "Run: bash bin/ensure-ollama.sh"
    fi
else
    fail "ollama binary not in PATH"
    fix "Install: curl -fsSL https://ollama.com/install.sh | sh"
fi

# ── 8. Config Integrity ──
header "Config Integrity"
if [ -f "$ROOT/opencode.json" ]; then
    if python3 -m json.tool "$ROOT/opencode.json" &>/dev/null; then
        pass "opencode.json: valid JSON"
    else
        fail "opencode.json: invalid JSON"
        fix "Run: python3 -m json.tool opencode.json"
    fi
else
    fail "opencode.json: missing"
fi

# Check for hardcoded paths in opencode.json
if grep -q '/home/nxyme/' "$ROOT/opencode.json" 2>/dev/null; then
    warn "opencode.json contains hardcoded /home/nxyme/ paths"
    fix "Consider using relative paths (./venvs/..., ./packages/...)"
else
    pass "opencode.json: no hardcoded paths"
fi

# ── Summary ──
echo ""
echo "═══════════════════════════════════════════"
echo -e "  ${RED}Issues: $ISSUES_FOUND${NC}  ${BLUE}Fixes Applied: $FIXES_APPLIED${NC}"
echo "═══════════════════════════════════════════"

if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "\n${GREEN}All MCPs healthy${NC}"
    exit 0
else
    echo -e "\n${YELLOW}$ISSUES_FOUND issue(s) found, $FIXES_APPLIED fix(es) attempted${NC}"
    if [ $ISSUES_FOUND -gt $FIXES_APPLIED ]; then
        echo -e "${RED}$((ISSUES_FOUND - FIXES_APPLIED)) issue(s) require manual attention${NC}"
    fi
    exit 1
fi

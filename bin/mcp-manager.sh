#!/usr/bin/env bash
# bin/mcp-manager.sh — Start, stop, and check status of all N-Xyme brain MCPs
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="$ROOT/.venv/bin/python"
JQ="${JQ:-command -v jq >/dev/null && echo jq || echo $VENV_PY -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]])'}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass()  { echo -e "${GREEN}✓${NC} $*"; }
fail()  { echo -e "${RED}✗${NC} $*"; }
info()  { echo -e "${CYAN}→${NC} $*"; }
warn()  { echo -e "${YELLOW}!${NC} $*"; }
header() { echo -e "\n${CYAN}═══ $* ═══${NC}"; }

BRAIN_MCPS=(
    "brain_mcp"
    "session-pool"
    "nx-context"
    "trigger-guardian"
    "catalyst"
    "orchestration"
    "nx-mind"
    "unified-memory"
    "learning-engine"
    "intelligence"
)

# ── External MCPs ──
EXTERNAL_MCPS=(
    "sequential-thinking"
    "quality-gates"
    "telegram"
    "notion"
    "github"
)

# ── Read MCP config ──
get_mcp_command() {
    local name="$1"
    local root="$ROOT"
    $VENV_PY -c "
import json, sys
with open('$root/opencode.json') as f:
    config = json.load(f)
mcp_servers = config.get('mcp', {})
key = '$name'
if key in mcp_servers:
    cfg = mcp_servers[key]
    cmd = cfg.get('command', [])
    args = cfg.get('args', [])
    if isinstance(cmd, list):
        cmd_str = ' '.join(cmd)
    else:
        cmd_str = str(cmd) if cmd else ''
    args = [a.replace('./', '$root/') if isinstance(a, str) and a.startswith('./') else str(a) for a in args]
    print(cmd_str + ' ' + ' '.join(args))
" 2>/dev/null || echo "NOT CONFIGURED"
}

# ── Commands ──

cmd_status() {
    header "MCP Server Status"
    echo "Config: $ROOT/opencode.json"
    echo ""

    echo "━━━ Brain MCPs (N-Xyme integration) ━━━"
    for name in "${BRAIN_MCPS[@]}"; do
        cmd=$(get_mcp_command "$name")
        if [ "$cmd" != "NOT CONFIGURED" ] && [ -n "$cmd" ]; then
            pass "$name: $cmd"
        else
            fail "$name: NOT IN CONFIG"
        fi
    done

    echo ""
    echo "━━━ External MCPs ━━━"
    for name in "${EXTERNAL_MCPS[@]}"; do
        cmd=$(get_mcp_command "$name")
        if [ "$cmd" != "NOT CONFIGURED" ] && [ -n "$cmd" ]; then
            pass "$name: $cmd"
        else
            fail "$name: NOT IN CONFIG"
        fi
    done
}

cmd_import_check() {
    header "MCP Module Import Check"
    ERRORS=0

    # Brain MCPs
    test_import() {
        local module="$1"
        local desc="$2"
        if PYTHONPATH="$ROOT" "$VENV_PY" -c "import $module" 2>/dev/null; then
            pass "$desc"
        else
            fail "$desc"
            ERRORS=$((ERRORS+1))
        fi
    }

    test_import "packages.brain_mcp" "brain_mcp (central)"
    test_import "packages.session_pool_mcp" "session-pool"
    test_import "packages.nx_context_mcp" "nx-context"
    test_import "packages.trigger_guardian_mcp.trigger_guardian_mcp" "trigger-guardian"
    test_import "packages.catalyst_orchestrator" "catalyst"
    test_import "packages.orchestration" "orchestration"
    test_import "packages.nx_mind_mcp" "nx-mind"
    test_import "packages.memory_core" "unified-memory"
    test_import "packages.learning_engine" "learning-engine"
    test_import "packages.intelligence" "intelligence"

    echo ""
    if [ $ERRORS -eq 0 ]; then
        pass "All brain MCP modules import cleanly"
    else
        fail "$ERRORS module(s) failed to import"
    fi
}

cmd_bridge_test() {
    header "Brain Bridge Functionality Test"
    BRIDGE="$ROOT/packages/nx-brain-hook/bridge.py"
    if [ ! -f "$BRIDGE" ]; then
        fail "bridge.py not found at $BRIDGE"
        return
    fi

    bridge_call() {
        local func="$1"
        local args="$2"
        echo "{\"tool\": \"$func\", \"args\": $args}" | PYTHONPATH="$ROOT" $VENV_PY "$BRIDGE" 2>/dev/null
    }

    check_json() {
        echo "$1" | $VENV_PY -c "import json,sys; json.load(sys.stdin); print('OK')" 2>/dev/null
    }

    result=$(bridge_call "memory.search" '{"query": "health check", "limit": 2}')
    if [ -n "$result" ] && [ "$(check_json "$result")" = "OK" ]; then
        pass "memory.search: OK"
    else
        fail "memory.search: FAILED"
    fi

    result=$(bridge_call "learning.route_task" '{"task_description": "fix auth bug"}')
    if echo "$result" | grep -q '"status"'; then
        pass "learning.route_task: OK"
    else
        fail "learning.route_task: FAILED"
    fi

    result=$(bridge_call "intelligence.score_complexity" '{"task_description": "add JWT auth"}')
    if [ -n "$result" ] && [ "$(check_json "$result")" = "OK" ]; then
        pass "intelligence.score_complexity: OK"
    else
        fail "intelligence.score_complexity: FAILED"
    fi
}

cmd_full() {
    cmd_status
    echo ""
    cmd_import_check
    echo ""
    cmd_bridge_test
    echo ""
    header "Run Health Checks"
    info "bash $ROOT/bin/health-brain.sh   # brain component health"
    info "bash $ROOT/bin/health-l0-blink.sh  # <1s pre-flight"
    info "bash $ROOT/bin/health-l1-pulse.sh  # <10s service check"
    info "bash $ROOT/bin/health-l2-vitals.sh # <60s deep check"
}

# ── CLI ──
ACTION="${1:-full}"

case "$ACTION" in
    status)  cmd_status ;;
    import)  cmd_import_check ;;
    bridge)  cmd_bridge_test ;;
    full)   cmd_full ;;
    *)
        echo "Usage: $0 {status|import|bridge|full}"
        echo ""
        echo "  status  — Show configured MCP server commands"
        echo "  import  — Test all MCP module imports"
        echo "  bridge  — Test the Python brain bridge (6 functions)"
        echo "  full    — All checks (default)"
        exit 1
        ;;
esac

#!/usr/bin/env bash
# Alert Script for N-Xyme MIND - Critical Failure Detection
# Outputs structured JSON results for cron job integration
# Usage: ./scripts/alert.sh [--json]

set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

JSON_OUTPUT=false
if [[ "${1:-}" == "--json" ]]; then
    JSON_OUTPUT=true
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ERRORS=0
WARNINGS=0
CHECKS=""

# Helper functions for JSON output
json_add_check() {
    local name="$1"
    local status="$2"
    local message="$3"
    CHECKS="${CHECKS}{\"name\":\"$name\",\"status\":\"$status\",\"message\":\"$message\"},"
}

pass_msg() { echo -e "${GREEN}✓${NC} $1"; }
fail_msg() { echo -e "${RED}✗${NC} $1"; ERRORS=$((ERRORS+1)); }
warn_msg() { echo -e "${YELLOW}!${NC} $1"; WARNINGS=$((WARNINGS+1)); }

# ============================================================
# CHECK 1: MCP Servers
# ============================================================
check_mcp_servers() {
    local check_name="mcp_servers"
    
    if [ -d "$ROOT/athena/.venv/bin" ]; then
        local venv_python="$ROOT/athena/.venv/bin/python3"
        local mcp_modules=("mcp_server_git" "sequential_thinking" "mcp_memory_service" "mcp")
        local all_ok=true
        
        for mod in "${mcp_modules[@]}"; do
            if ! "$venv_python" -c "import $mod" 2>/dev/null; then
                all_ok=false
                break
            fi
        done
        
        if $all_ok; then
            pass_msg "MCP servers responding"
            json_add_check "$check_name" "ok" "All MCP modules available"
        else
            fail_msg "MCP servers - some modules missing"
            json_add_check "$check_name" "critical" "One or more MCP modules not available"
        fi
    else
        fail_msg "MCP servers - venv not found"
        json_add_check "$check_name" "critical" "Athena venv not found"
    fi
}

# ============================================================
# CHECK 2: Ollama
# ============================================================
check_ollama() {
    local check_name="ollama"
    
    if curl -sf --max-time 5 http://localhost:11434/api/tags >/dev/null 2>&1; then
        pass_msg "Ollama running"
        json_add_check "$check_name" "ok" "Ollama responding on localhost:11434"
    else
        fail_msg "Ollama not responding"
        json_add_check "$check_name" "critical" "Ollama not responding on localhost:11434"
    fi
}

# ============================================================
# CHECK 3: Proxy Health
# ============================================================
check_proxy() {
    local check_name="proxy"
    local proxy_ports=(1080 1081 1082 1083 1084 1085 1086 1087)
    local failed=0
    
    for port in "${proxy_ports[@]}"; do
        if ! ss -tlnp 2>/dev/null | grep -q ":${port} "; then
            ((failed++))
        fi
    done
    
    if [ $failed -eq 0 ]; then
        pass_msg "All proxies healthy (8/8)"
        json_add_check "$check_name" "ok" "All 8 SOCKS5 proxies running"
    elif [ $failed -lt 5 ]; then
        warn_msg "Some proxies down ($((8-failed))/8)"
        json_add_check "$check_name" "warning" "$failed of 8 proxies down"
    else
        fail_msg "Most proxies down ($((8-failed))/8)"
        json_add_check "$check_name" "critical" "$failed of 8 proxies down"
    fi
}

# ============================================================
# CHECK 4: Disk Space
# ============================================================
check_disk_space() {
    local check_name="disk_space"
    local threshold=90
    local usage=$(df -h "$ROOT" | tail -1 | awk '{print $5}' | tr -d '%')
    
    if [ "$usage" -lt "$threshold" ]; then
        pass_msg "Disk space: ${usage}% used"
        json_add_check "$check_name" "ok" "Disk usage at ${usage}%"
    elif [ "$usage" -lt 95 ]; then
        warn_msg "Disk space: ${usage}% used"
        json_add_check "$check_name" "warning" "Disk usage at ${usage}%"
    else
        fail_msg "Disk space critical: ${usage}% used"
        json_add_check "$check_name" "critical" "Disk usage at ${usage}%"
    fi
}

# ============================================================
# CHECK 5: Crashed Processes
# ============================================================
check_crashed_processes() {
    local check_name="crashed_processes"
    # Check for critical processes - be lenient, only check if they should be running
    # Use more flexible matching
    local crashed=()
    
    # Check Ollama
    if ! pgrep -x ollama >/dev/null 2>&1; then
        crashed+=("ollama")
    fi
    
    # Check if model-router service exists and is supposed to be running
    if ! systemctl --user is-active --quiet model-router.service 2>/dev/null; then
        if ! pgrep -f "model-router" >/dev/null 2>&1; then
            crashed+=("model-router")
        fi
    fi
    
    if [ ${#crashed[@]} -eq 0 ]; then
        pass_msg "No crashed critical processes"
        json_add_check "$check_name" "ok" "All critical processes running"
    else
        warn_msg "Potentially crashed: ${crashed[*]}"
        json_add_check "$check_name" "warning" "Potentially crashed: ${crashed[*]}"
    fi
}

# ============================================================
# CHECK 6: Model Router
# ============================================================
check_model_router() {
    local check_name="model_router"
    
    if curl -sf --max-time 5 http://127.0.0.1:8080/health > /dev/null 2>&1; then
        pass_msg "Model Router healthy"
        json_add_check "$check_name" "ok" "Model Router responding"
    else
        fail_msg "Model Router unhealthy"
        json_add_check "$check_name" "critical" "Model Router not responding"
    fi
}

# ============================================================
# Main Execution
# ============================================================
main() {
    if $JSON_OUTPUT; then
        # Run checks and collect JSON
        check_mcp_servers
        check_ollama
        check_proxy
        check_disk_space
        check_crashed_processes
        check_model_router
        
        # Build final JSON
        local timestamp=$(date -Iseconds)
        local severity="ok"
        if [ $ERRORS -gt 0 ]; then
            severity="critical"
        elif [ $WARNINGS -gt 0 ]; then
            severity="warning"
        fi
        
        # Remove trailing comma and build array
        local checks_array="${CHECKS%,}"
        
        cat <<EOF
{
  "timestamp": "$timestamp",
  "severity": "$severity",
  "errors": $ERRORS,
  "warnings": $WARNINGS,
  "checks": [$checks_array]
}
EOF
    else
        # Human-readable output
        echo "=== N-Xyme MIND Alert System ==="
        echo "Timestamp: $(date)"
        echo ""
        
        check_mcp_servers
        check_ollama
        check_proxy
        check_disk_space
        check_crashed_processes
        check_model_router
        
        echo ""
        echo "==================================="
        if [ $ERRORS -eq 0 ]; then
            if [ $WARNINGS -eq 0 ]; then
                echo -e "${GREEN}All systems operational${NC}"
            else
                echo -e "${YELLOW}$WARNINGS warning(s)${NC}"
            fi
        else
            echo -e "${RED}$ERRORS critical failure(s) detected${NC}"
        fi
    fi
    
    # Exit code: 0=ok, 1=warning, 2=critical
    if [ $ERRORS -gt 0 ]; then
        exit 2
    elif [ $WARNINGS -gt 0 ]; then
        exit 1
    fi
    exit 0
}

main "$@"

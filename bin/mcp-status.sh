#!/usr/bin/env bash
# =============================================================================
# mcp-status.sh — Health check all running MCP servers
# =============================================================================
# Checks each PID file, reports running/stopped/healthy status
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_DIR="$PROJECT_ROOT/.sisyphus/mcp_pids"

echo "=== MCP Server Status ==="
echo ""

# Check if PID directory exists
if [[ ! -d "$PID_DIR" ]]; then
    echo "No PID directory found at $PID_DIR"
    echo "No MCP servers started yet."
    exit 0
fi

# Define MCP servers
declare -A MCP_SERVERS=(
    ["unified-memory"]="Unified Memory"
    ["learning-engine"]="Learning Engine"
    ["orchestration"]="Orchestration"
    ["intelligence"]="Intelligence"
)

running=0
stopped=0

for server_name in "${!MCP_SERVERS[@]}"; do
    server_desc="${MCP_SERVERS[$server_name]}"
    pid_file="$PID_DIR/${server_name}.pid"
    log_file="$PID_DIR/${server_name}.log"
    
    printf "%-20s " "$server_desc:"
    
    if [[ ! -f "$pid_file" ]]; then
        echo "STOPPED (no PID file)"
        ((stopped++)) || true
        continue
    fi
    
    pid=$(cat "$pid_file" 2>/dev/null)
    
    if [[ -z "$pid" ]]; then
        echo "STOPPED (empty PID)"
        ((stopped++)) || true
        continue
    fi
    
    # Check if process is running
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "STOPPED (stale PID: $pid)"
        rm -f "$pid_file"
        ((stopped++)) || true
        continue
    fi
    
    # Process is running - check log for errors
    if [[ -f "$log_file" ]]; then
        # Check for recent errors in log (last 10 lines)
        if tail -10 "$log_file" 2>/dev/null | grep -qi "error\|exception\|traceback\|failed"; then
            echo "RUNNING (has errors in log)"
        else
            echo "RUNNING (PID: $pid)"
        fi
    else
        echo "RUNNING (PID: $pid)"
    fi
    
    ((running++)) || true
done

echo ""
echo "Summary: $running running, $stopped stopped"
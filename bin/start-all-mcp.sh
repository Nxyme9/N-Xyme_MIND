#!/usr/bin/env bash
# =============================================================================
# start-all-mcp.sh — Start all MCP server processes in background
# =============================================================================
# Creates PID files in .sisyphus/mcp_pids/ for each server
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_DIR="$PROJECT_ROOT/.sisyphus/mcp_pids"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

# Ensure PID directory exists
mkdir -p "$PID_DIR"

# MCP servers configuration
declare -A MCP_SERVERS=(
    ["unified-memory"]="packages/memory_core/mcp_server.py"
    ["learning-engine"]="packages/learning_engine/mcp_server.py"
    ["orchestration"]="packages/orchestration/mcp_server.py"
    ["intelligence"]="packages/intelligence/mcp_server.py"
)

echo "Starting MCP servers..."

# Check if venv Python exists, fallback to system python
if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "Warning: .venv not found, using system python3"
    PYTHON_CMD="python3"
else
    PYTHON_CMD="$VENV_PYTHON"
fi

# Start each MCP server
for server_name in "${!MCP_SERVERS[@]}"; do
    server_path="${MCP_SERVERS[$server_name]}"
    pid_file="$PID_DIR/${server_name}.pid"
    log_file="$PID_DIR/${server_name}.log"
    
    # Kill any existing process with same PID file
    if [[ -f "$pid_file" ]]; then
        old_pid=$(cat "$pid_file")
        if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
            echo "Stopping existing $server_name (PID: $old_pid)"
            kill "$old_pid" 2>/dev/null || true
            sleep 1
        fi
    fi
    
    # Start server in background by running the script directly
    echo "Starting $server_name..."
    cd "$PROJECT_ROOT"
    PYTHONPATH="$PROJECT_ROOT" $PYTHON_CMD "$PROJECT_ROOT/$server_path" > "$log_file" 2>&1 &
    pid=$!
    
    # Save PID
    echo "$pid" > "$pid_file"
    echo "  -> PID $pid (log: $log_file)"
    
    # Brief pause between starts
    sleep 0.5
done

echo ""
echo "All MCP servers started."
echo "PIDs saved to: $PID_DIR"
echo ""
echo "To check status: bash bin/mcp-status.sh"
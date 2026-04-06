#!/usr/bin/env bash
# =============================================================================
# stop-all-mcp.sh — Graceful shutdown of all MCP servers
# =============================================================================
# Reads PIDs from .sisyphus/mcp_pids/, sends SIGTERM, waits, SIGKILL if needed
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_DIR="$PROJECT_ROOT/.sisyphus/mcp_pids"

TIMEOUT=10  # seconds to wait before SIGKILL

echo "Stopping MCP servers..."

# Check if PID directory exists
if [[ ! -d "$PID_DIR" ]]; then
    echo "No PID directory found at $PID_DIR"
    exit 0
fi

# Get list of PID files
pid_files=("$PID_DIR"/*.pid)

if [[ ! -f "${pid_files[0]}" ]] && [[ ! -f "$PID_DIR/unified-memory.pid" ]]; then
    echo "No MCP server PIDs found."
    exit 0
fi

# Track what we stopped
stopped=0
failed=0

for pid_file in "$PID_DIR"/*.pid; do
    [[ -e "$pid_file" ]] || continue
    
    server_name=$(basename "$pid_file" .pid)
    pid=$(cat "$pid_file" 2>/dev/null)
    
    if [[ -z "$pid" ]]; then
        echo "  $server_name: No PID recorded, skipping"
        continue
    fi
    
    # Check if process is actually running
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "  $server_name: Process not running (stale PID)"
        rm -f "$pid_file"
        continue
    fi
    
    echo "  Stopping $server_name (PID: $pid)..."
    
    # Send SIGTERM
    kill -TERM "$pid" 2>/dev/null || true
    
    # Wait for graceful shutdown
    waited=0
    while kill -0 "$pid" 2>/dev/null; do
        sleep 1
        ((waited++)) || true
        if [[ $waited -ge $TIMEOUT ]]; then
            echo "  -> SIGKILL required for $server_name"
            kill -KILL "$pid" 2>/dev/null || true
            break
        fi
    done
    
    # Verify it's stopped
    if kill -0 "$pid" 2>/dev/null; then
        echo "  -> FAILED to stop $server_name"
        ((failed++)) || true
    else
        echo "  -> Stopped"
        rm -f "$pid_file"
        ((stopped++)) || true
    fi
done

echo ""
if [[ $failed -gt 0 ]]; then
    echo "Stopped: $stopped, Failed: $failed"
    exit 1
else
    echo "All MCP servers stopped ($stopped)"
    exit 0
fi
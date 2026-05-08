#!/bin/bash
# Auto-start Hook & Trigger Guardian System
# This ensures the system is always running when OpenCode starts
# Runs as background daemon, self-healing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="/tmp/hook-trigger"
PID_FILE="$LOG_DIR/daemon.pid"
STATE_FILE="$LOG_DIR/state.json"

mkdir -p "$LOG_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[HOOK-TRIGGER]${NC} $1"; }
warn() { echo -e "${YELLOW}[HOOK-TRIGGER]${NC} WARNING: $1"; }
error() { echo -e "${RED}[HOOK-TRIGGER]${NC} ERROR: $1"; }

# Check if already running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# Start MCP server for trigger-guardian
start_mcp() {
    log "Starting Trigger Guardian MCP..."
    
    # Check if trigger-guardian-mcp exists
    if [ -d "$SCRIPT_DIR/packages/trigger-guardian-mcp" ]; then
        cd "$SCRIPT_DIR/packages/trigger-guardian-mcp"
        if [ -f ".venv/bin/python" ]; then
            nohup .venv/bin/python -m trigger_guardian_mcp > "$LOG_DIR/mcp.log" 2>&1 &
            echo $! > "$PID_FILE"
            sleep 2
            if kill -0 $(cat "$PID_FILE") 2>/dev/null; then
                log "✅ Trigger Guardian MCP started (PID: $(cat "$PID_FILE"))"
            else
                error "MCP failed to start"
                cat "$LOG_DIR/mcp.log" | tail -5
                return 1
            fi
        else
            warn "Trigger Guardian MCP venv not found, skipping"
        fi
    else
        warn "Trigger Guardian MCP not found at $SCRIPT_DIR/packages/trigger-guardian-mcp"
    fi
    
    # Register default triggers
    register_default_triggers
}

# Register default system triggers
register_default_triggers() {
    log "Registering default triggers..."
    
    # Use the trigger-guardian MCP if available
    if command -v curl &> /dev/null; then
        # Core system health triggers
        curl -s -X POST http://localhost:8090/triggers/register \
            -H "Content-Type: application/json" \
            -d '{"phrase": "/health", "handler": "function", "handler_target": "system.health_check"}' 2>/dev/null || true
            
        # Benchmark triggers
        curl -s -X POST http://localhost:8090/triggers/register \
            -H "Content-Type: application/json" \
            -d '{"phrase": "/benchmark", "handler": "function", "handler_target": "system.run_benchmark"}' 2>/dev/null || true
            
        # Status triggers
        curl -s -X POST http://localhost:8090/triggers/register \
            -H "Content-Type: application/json" \
            -d '{"phrase": "/status", "handler": "function", "handler_target": "system.status"}' 2>/dev/null || true
            
        log "Default triggers registered"
    fi
}

# Main daemon loop
daemon() {
    log "Starting Hook & Trigger Guardian daemon..."
    
    # Start MCP
    start_mcp
    
    # Save state
    echo '{"status": "running", "started": "'$(date -Iseconds)'"}' > "$STATE_FILE"
    
    log "✅ Hook & Trigger system active"
    
    # Keep alive - restart if dies
    while true; do
        if ! is_running; then
            warn "Process died, restarting..."
            start_mcp
        fi
        sleep 30
    done
}

# Stop daemon
stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill "$PID" 2>/dev/null; then
            log "Stopped daemon (PID: $PID)"
            rm -f "$PID_FILE"
        fi
    fi
    rm -f "$STATE_FILE"
}

# Status check
status() {
    if is_running; then
        log "✅ Running (PID: $(cat "$PID_FILE"))"
        cat "$STATE_FILE" 2>/dev/null || echo '{"status": "running"}'
    else
        error "Not running"
        exit 1
    fi
}

# Parse command
case "${1:-start}" in
    start)
        if is_running; then
            warn "Already running"
            exit 0
        fi
        daemon &
        disown
        log "Daemon started in background"
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 1
        daemon &
        disown
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
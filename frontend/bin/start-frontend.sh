#!/usr/bin/env bash
set -euo pipefail

FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORTS=(3000 3001 3002)
MAX_RETRIES_PER_MINUTE=10
RESTART_LOG="/tmp/frontend-restarts.log"
PID_FILE="/tmp/frontend.pid"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

find_available_port() {
    for port in "${PORTS[@]}"; do
        if ! lsof -i ":$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo "$port"
            return 0
        fi
        log "Port $port is in use, trying next..."
    done
    log "ERROR: No available ports found"
    return 1
}

start_frontend() {
    local port="$1"
    local log_file="/tmp/frontend-${port}.log"
    
    log "Starting frontend on port $port..."
    log "Log file: $log_file"
    
    cd "$FRONTEND_DIR"
    
    nohup npm run dev -- --port "$port" > "$log_file" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"
    
    log "Frontend started with PID $pid on port $port"
    
    sleep 3
    
    if ! kill -0 "$pid" 2>/dev/null; then
        log "ERROR: Frontend failed to start. Check $log_file"
        cat "$log_file"
        return 1
    fi
    
    local health_url="http://localhost:$port/api/health"
    local retries=0
    while [ $retries -lt 10 ]; do
        if curl -sf "$health_url" > /dev/null 2>&1; then
            log "Health check passed for port $port"
            return 0
        fi
        sleep 2
        ((retries++))
    done
    
    log "WARNING: Health check not responding yet, but process is running"
    return 0
}

cleanup() {
    log "Shutting down gracefully..."
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid" 2>/dev/null || true
            sleep 2
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
    fi
    log "Cleanup complete"
    exit 0
}

trap cleanup SIGINT SIGTERM

main() {
    log "=== Frontend Start Script ==="
    log "Frontend directory: $FRONTEND_DIR"
    
    if [ -f "$PID_FILE" ]; then
        local existing_pid=$(cat "$PID_FILE")
        if kill -0 "$existing_pid" 2>/dev/null; then
            log "Frontend already running with PID $existing_pid"
            log "Stopping existing instance..."
            kill -TERM "$existing_pid" 2>/dev/null || true
            sleep 2
        fi
        rm -f "$PID_FILE"
    fi
    
    while true; do
        local port
        port=$(find_available_port) || { log "Failed to find port, exiting"; exit 1; }
        
        local log_file="/tmp/frontend-${port}.log"
        > "$log_file"
        
        start_frontend "$port"
        
        local frontend_pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
        
        log "Monitoring frontend PID $frontend_pid..."
        
        while kill -0 "$frontend_pid" 2>/dev/null; do
            sleep 5
        done
        
        local exit_code=$?
        log "Frontend crashed with code $exit_code"
        
        echo "$(date '+%Y-%m-%d %H:%M:%S') Port $port crashed, restarting..." >> "$RESTART_LOG"
        
        local restart_count=$(grep -c "$(date '+%Y-%m-%d %H')" "$RESTART_LOG" 2>/dev/null || echo 0)
        if [ "$restart_count" -ge "$MAX_RETRIES_PER_MINUTE" ]; then
            log "ERROR: Too many restarts ($restart_count) in the last minute"
            log "Exiting to prevent crash loop"
            exit 1
        fi
        
        log "Restarting frontend in 2 seconds..."
        sleep 2
    done
}

main "$@"

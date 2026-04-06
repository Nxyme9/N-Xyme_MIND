#!/usr/bin/env bash
# Stop the Model Router Proxy Server
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT/logs/model-router.pid"

# Cleanup function for stale PID files and orphaned processes
cleanup() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ! kill -0 "$PID" 2>/dev/null; then
            echo "Removing stale PID file (PID: $PID)"
            rm -f "$PID_FILE"
        fi
    fi

    # Kill orphaned uvicorn processes on the model router port
    PORT=${MODEL_ROUTER_PORT:-8080}
    ORPHANS=$(lsof -ti :"$PORT" 2>/dev/null || ss -tlnp "sport = :$PORT" 2>/dev/null | grep -oP 'pid=\K[0-9]+' || true)
    if [ -n "$ORPHANS" ]; then
        echo "Found orphaned processes on port $PORT: $ORPHANS"
        for ORPHAN_PID in $ORPHANS; do
            if [ -f "$PID_FILE" ] && [ "$(cat "$PID_FILE")" != "$ORPHAN_PID" ]; then
                echo "Killing orphaned process $ORPHAN_PID"
                kill "$ORPHAN_PID" 2>/dev/null || true
                sleep 1
                kill -0 "$ORPHAN_PID" 2>/dev/null && kill -9 "$ORPHAN_PID" 2>/dev/null || true
            fi
        done
    fi
}

if [ ! -f "$PID_FILE" ]; then
    echo "Model router not running (no PID file)"
    cleanup
    exit 0
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
    echo "Stopping model router (PID: $PID)..."
    kill "$PID"
    sleep 2
    if kill -0 "$PID" 2>/dev/null; then
        echo "Force stopping..."
        kill -9 "$PID"
    fi
    echo "Model router stopped"
else
    echo "Model router not running (stale PID: $PID)"
fi

rm -f "$PID_FILE"
cleanup

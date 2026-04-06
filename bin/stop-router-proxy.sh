#!/bin/bash
# Stop N-Xyme Intelligent Router Proxy Server
set -e

PID_FILE="/tmp/router-proxy.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Router proxy not running (no PID file)"
    exit 0
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    echo "Router proxy stopped (PID: $PID)"
else
    echo "Router proxy not running (stale PID: $PID)"
fi

rm -f "$PID_FILE"

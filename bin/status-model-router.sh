#!/usr/bin/env bash
# Check Model Router Proxy Server status
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT=${MODEL_ROUTER_PORT:-8080}
HOST=${MODEL_ROUTER_HOST:-127.0.0.1}

echo "=== Model Router Status ==="

# Check process
PID_FILE="$ROOT/logs/model-router.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Process: Running (PID: $PID)"
    else
        echo "Process: Not running (stale PID: $PID)"
    fi
else
    echo "Process: Not running"
fi

# Check health
echo -n "Health: "
if curl -sf "http://$HOST:$PORT/health" > /dev/null 2>&1; then
    echo "✅ Healthy"
    curl -sf "http://$HOST:$PORT/health" | python3 -m json.tool 2>/dev/null || true
else
    echo "❌ Unreachable"
fi

# Check VRAM
echo -n "VRAM: "
if curl -sf "http://$HOST:$PORT/vram" > /dev/null 2>&1; then
    curl -sf "http://$HOST:$PORT/vram" | python3 -m json.tool 2>/dev/null || true
else
    echo "❌ Unreachable"
fi

# Check models
echo -n "Loaded Models: "
if curl -sf "http://$HOST:$PORT/models/loaded" > /dev/null 2>&1; then
    curl -sf "http://$HOST:$PORT/models/loaded" | python3 -m json.tool 2>/dev/null || true
else
    echo "❌ Unreachable"
fi

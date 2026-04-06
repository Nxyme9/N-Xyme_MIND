#!/usr/bin/env bash
# Start the Model Router Proxy Server
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
source env.sh 2>/dev/null || true

PORT=${MODEL_ROUTER_PORT:-8080}
HOST=${MODEL_ROUTER_HOST:-127.0.0.1}
LOG_FILE="$ROOT/logs/model-router.log"
PID_FILE="$ROOT/logs/model-router.pid"

mkdir -p "$ROOT/logs"

# Log rotation: max 10MB, keep 5 backups
MAX_LOG_SIZE=10485760  # 10MB in bytes
MAX_LOG_BACKUPS=5

if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
    if [ "$LOG_SIZE" -ge "$MAX_LOG_SIZE" ]; then
        echo "Rotating log file (size: $((LOG_SIZE / 1024))KB)"
        for i in $(seq $((MAX_LOG_BACKUPS - 1)) -1 1); do
            if [ -f "${LOG_FILE}.$i" ]; then
                mv "${LOG_FILE}.$i" "${LOG_FILE}.$((i + 1))"
            fi
        done
        mv "$LOG_FILE" "${LOG_FILE}.1"
        # Remove oldest backup if it exceeds limit
        if [ -f "${LOG_FILE}.$((MAX_LOG_BACKUPS + 1))" ]; then
            rm -f "${LOG_FILE}.$((MAX_LOG_BACKUPS + 1))"
        fi
    fi
fi

# Start proxy server
echo "Starting model router on $HOST:$PORT..."
nohup ./venv/bin/python -m uvicorn src.proxy.model_router:app \
    --host "$HOST" \
    --port "$PORT" \
    --log-level info \
    >> "$LOG_FILE" 2>&1 &

echo $! > "$PID_FILE"
echo "Model router started (PID: $(cat $PID_FILE))"
echo "Log file: $LOG_FILE"

# Wait for health check
for i in $(seq 1 30); do
    if curl -sf "http://$HOST:$PORT/health" > /dev/null 2>&1; then
        echo "Health check passed"
        break
    fi
    sleep 1
done

# VPN health check
if [ "${VPN_ENABLED:-true}" = "true" ]; then
    echo "Checking VPN backends..."
    VPN_STATUS=$(curl -sf http://127.0.0.1:8080/vpn/health 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "VPN backends: $VPN_STATUS"
    else
        echo "WARNING: VPN health check failed"
    fi
fi

# Verify health check passed
if ! curl -sf "http://$HOST:$PORT/health" > /dev/null 2>&1; then
    echo "ERROR: Health check timed out — cleaning up"
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        kill "$PID" 2>/dev/null || true
        rm -f "$PID_FILE"
    fi
    exit 1
fi

exit 0

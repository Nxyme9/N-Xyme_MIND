#!/bin/bash
# Start N-Xyme Intelligent Router Proxy Server (OpenAI-compatible on port 8080)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="/tmp/router-proxy.pid"
LOG_FILE="/tmp/router-proxy.log"

cd "$PROJECT_DIR"

# Check if already running
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Router proxy already running (PID: $(cat "$PID_FILE"))"
    exit 0
fi

# Activate virtual environment
if [ -d "venvs/athena" ]; then
    source venvs/athena/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

export PYTHONPATH="$PROJECT_DIR"

# Start the proxy server
nohup python -m src.infrastructure.proxy.openai_proxy > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

echo "Router proxy started on port 8080 (PID: $(cat "$PID_FILE"))"
echo "Logs: $LOG_FILE"
sleep 2
curl -s http://localhost:8080/health | python3 -m json.tool 2>/dev/null || echo "Server starting... check $LOG_FILE"

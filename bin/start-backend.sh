#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_DIR="$PROJECT_ROOT/.sisyphus/mcp_pids"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

mkdir -p "$PID_DIR"

echo "=== Starting N-Xyme Backend Services ==="

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "Warning: .venv not found, using system python3"
    PYTHON_CMD="python3"
else
    PYTHON_CMD="$VENV_PYTHON"
fi

pkill -f "brain_mcp" 2>/dev/null || true
pkill -f "http_gateway" 2>/dev/null || true
sleep 1

cd "$PROJECT_ROOT"
PYTHONPATH="$PROJECT_ROOT" nohup $PYTHON_CMD -m packages.brain_mcp --http --port 8765 > "$PID_DIR/brain_mcp.log" 2>&1 &
BRAIN_PID=$!
echo "$BRAIN_PID" > "$PID_DIR/brain_mcp.pid"
echo "  -> brain_mcp PID: $BRAIN_PID"

for i in {1..15}; do
    if curl -s http://localhost:8765/health > /dev/null 2>&1; then
        echo "  -> brain_mcp ready!"
        break
    fi
    sleep 1
done

PYTHONPATH="$PROJECT_ROOT" nohup $PYTHON_CMD -m packages.http_gateway > "$PID_DIR/http_gateway.log" 2>&1 &
GATEWAY_PID=$!
echo "$GATEWAY_PID" > "$PID_DIR/http_gateway.pid"
echo "  -> http_gateway PID: $GATEWAY_PID"

for i in {1..15}; do
    if curl -s http://localhost:8766/ > /dev/null 2>&1; then
        echo "  -> http_gateway ready!"
        break
    fi
    sleep 1
done

echo ""
echo "=== Backend Services Status ==="
echo ""
echo "Testing brain_mcp:"
echo "  GET /health        -> $(curl -s http://localhost:8765/health | head -c 100)"
echo ""
echo "Testing http_gateway:"
echo "  GET /              -> $(curl -s http://localhost:8766/ | head -c 100)"
echo "  GET /system_health_check -> $(curl -s http://localhost:8766/system_health_check | head -c 100)"
echo ""

if curl -s http://localhost:8765/health > /dev/null 2>&1 && curl -s http://localhost:8766/ > /dev/null 2>&1; then
    echo "=== All services started successfully ==="
    exit 0
else
    echo "=== Warning: Some services may not be ready ==="
    exit 1
fi

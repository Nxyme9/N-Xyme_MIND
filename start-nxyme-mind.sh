#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "=== Starting N-Xyme MIND ==="
echo ""

# Start backend
echo "→ Starting backend services..."
"$SCRIPT_DIR/bin/start-backend.sh"
echo ""

# Start frontend
echo "→ Starting frontend..."
cd "$FRONTEND_DIR"
nohup npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

# Wait for frontend
echo "Waiting for frontend..."
for i in {1..30}; do
    if curl -sf http://localhost:3000/api/health > /dev/null 2>&1; then
        echo "Frontend ready!"
        break
    fi
    sleep 1
done

echo ""
echo "=== All services ready ==="
echo ""
echo "Frontend:  http://localhost:3000"
echo "Backend:   http://localhost:8765"
echo "Proxy:     http://localhost:8766"
echo ""
echo "PIDs saved to: .sisyphus/mcp_pids/"
echo ""
echo "Press Ctrl+C to stop all services"

# Handle cleanup
cleanup() {
    echo ""
    echo "Stopping services..."
    pkill -f "brain_mcp" 2>/dev/null || true
    pkill -f "http_gateway" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    echo "Done!"
}
trap cleanup SIGINT SIGTERM

# Keep running
wait
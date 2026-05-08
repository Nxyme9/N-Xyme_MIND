#!/bin/bash
# GGUF Server Pool - Port 8081 (Qwen 0.5B for fast lightweight tasks)
# Usage: ./start_gguf_8081.sh

PORT=8081
MODEL="qwen2.5-0.5b-instruct-q4_k_m"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if already running
if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
    echo "GGUF server already running on port $PORT (model: $MODEL)"
    exit 0
fi

# Kill any existing on this port
fuser -k $PORT/tcp 2>/dev/null || true

# Start server with port
echo "Starting GGUF server on port $PORT..."
nohup .venv/bin/python packages/local_llm/gguf_mcp_server.py --port $PORT > /tmp/gguf_8081.log 2>&1 &

# Wait for server to be ready
for i in {1..15}; do
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo "GGUF server started on port $PORT (model: $MODEL)"
        exit 0
    fi
    sleep 1
done

echo "Failed to start GGUF server on port $PORT"
cat /tmp/gguf_8081.log
exit 1

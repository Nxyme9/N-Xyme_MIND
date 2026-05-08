#!/bin/bash
# GGUF Server Pool - Port 8083 (Nomic Embed for embeddings)
# Usage: ./start_gguf_8083.sh

PORT=8083
MODEL="nomic-embed-text-v1.5-Q4_K_M"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if already running
if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
    echo "GGUF server already running on port $PORT (model: $MODEL)"
    exit 0
fi

# Kill any existing on this port
fuser -k $PORT/tcp 2>/dev/null || true

# Start server with specific model
echo "Starting GGUF server on port $PORT (model: $MODEL)..."
GGUF_MODEL=$MODEL nohup .venv/bin/python packages/local_llm/gguf_mcp_server.py --port $PORT > /tmp/gguf_8083.log 2>&1 &

# Wait for server to be ready
for i in {1..15}; do
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo "GGUF server started on port $PORT (model: $MODEL)"
        exit 0
    fi
    sleep 1
done

echo "Failed to start GGUF server on port $PORT"
cat /tmp/gguf_8083.log
exit 1

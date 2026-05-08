#!/bin/bash
# GGUF Server startup script
# Usage: ./start_gguf_server.sh [--port 8081]

PORT=8081

while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if already running
if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
    echo "GGUF server already running on port $PORT"
    exit 0
fi

# Start server
echo "Starting GGUF server on port $PORT..."
nohup .venv/bin/python packages/local_llm/gguf_mcp_server.py --port $PORT > /tmp/gguf_server.log 2>&1 &

# Wait for server to be ready
for i in {1..10}; do
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo "GGUF server started successfully on port $PORT"
        exit 0
    fi
    sleep 1
done

echo "Failed to start GGUF server"
cat /tmp/gguf_server.log
exit 1

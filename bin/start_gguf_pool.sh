#!/bin/bash
# GGUF Server Pool - Start All Servers
# Usage: ./start_gguf_pool.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== GGUF Server Pool ==="
echo "Starting all GGUF server instances..."
echo ""

# Start each server
for port in 8081 8082 8083; do
    script="./start_gguf_${port}.sh"
    if [ -f "$script" ]; then
        echo "Starting port $port..."
        bash "$script"
    else
        echo "Warning: $script not found"
    fi
done

echo ""
echo "=== Checking all servers ==="
for port in 8081 8082 8083; do
    if curl -s http://localhost:$port/health > /dev/null 2>&1; then
        echo "✅ Port $port: UP"
    else
        echo "❌ Port $port: DOWN"
    fi
done

echo ""
echo "=== Available Models ==="
curl -s http://localhost:8081/v1/models 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    for m in data.get('data', []):
        print(f\"  - {m['id']}\")
except:
    print('  (error reading models)')
"

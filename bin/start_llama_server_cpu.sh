#!/bin/bash
# N-XYME CPU-Optimized GGUF Server
# For when GPU is unavailable or as fallback

set -e

PORT=${PORT:-8081}
MODEL_DIR="${MODEL_DIR:-/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models}"
SERVER_BIN="${SERVER_BIN:-/home/nxyme/llama.cpp/build/bin/llama-server}"
MODEL="${MODEL:-qwen2.5-0.5b-instruct-q4_k_m.gguf}"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🚀 Starting CPU-optimized llama-server...${NC}"

# CPU OPTIMIZATION FOR RYZEN 7800X3D
# 7800X3D has 8 cores, 16 threads - optimize for this
CPU_THREADS=16
UBATCH=512
BATCH=2048

# Kill existing on this port
fuser -k $PORT/tcp 2>/dev/null || true
sleep 1

cd /home/nxyme
nohup $SERVER_BIN \
  -m "$MODEL_DIR/$MODEL" \
  -c 4096 \
  -np 16 \
  -cb \
  -t $CPU_THREADS \
  -b $BATCH \
  -ub $UBATCH \
  --no-mmap \
  --jinja \
  --pooling mean \
  --slots \
  --flash-attn off \
  --port $PORT \
  --host 0.0.0.0 \
  > /tmp/llama-cpu.log 2>&1 &

echo "Starting CPU server on port $PORT..."

for i in {1..20}; do
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ CPU Server ready on http://localhost:$PORT${NC}"
        exit 0
    fi
    sleep 1
done

echo "❌ Failed to start"
tail -10 /tmp/llama-cpu.log

#!/bin/bash
# N-XYME GGUF RTX 3080 Ti MAXIMUM PERFORMANCE STARTUP
# Optimized specifically for 12.5GB VRAM with all bleeding-edge flags

set -e

PORT=${PORT:-8080}
MODEL_DIR="${MODEL_DIR:-/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models}"
SERVER_BIN="${SERVER_BIN:-/home/nxyme/llama.cpp/build/bin/llama-server}"
MODEL="${MODEL:-qwen2.5-0.5b-instruct-q4_k_m.gguf}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "═══════════════════════════════════════════════════════════"
echo "  N-XYME GGUF - RTX 3080 Ti MAX PERFORMANCE"
echo "  Target: <50ms latency, 8-16 concurrent slots"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Hardware validation
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${YELLOW}⚠️  No NVIDIA GPU detected - running in fallback mode${NC}"
    GPU_MODE="cpu"
else
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    VRAM_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -1 | sed 's/ MiB//')
    echo -e "${GREEN}✅ GPU: $GPU_NAME${NC}"
    echo "   VRAM: $((VRAM_MB / 1024))GB"
    
    if [ "$VRAM_MB" -lt 10000 ]; then
        echo -e "${YELLOW}⚠️  VRAM < 10GB - using balanced config${NC}"
        GPU_MODE="balanced"
    else
        GPU_MODE="max"
    fi
fi

# Kill existing server on port
fuser -k $PORT/tcp 2>/dev/null || true
sleep 1

# Build optimized flags based on GPU mode
NGL_FLAG="-ngl 99"
FLASH_ATTN="--flash-attn on --flash-attn-type 2"
KV_CACHE="-ctk q4_0 -ctv q4_0"
NO_MMAP="--no-mmap"

if [ "$GPU_MODE" = "cpu" ]; then
    # CPU fallback - reduced parallelism
    PARAMS=(
        -m "$MODEL_DIR/$MODEL"
        -c 4096
        -np 4
        -cb
        -t 16
        -b 512
        -ub 256
    )
    echo "   Mode: CPU fallback"
else
    # RTX 3080 Ti MAXIMUM PERFORMANCE
    PARAMS=(
        -m "$MODEL_DIR/$MODEL"
        -ngl 99
        -c 8192
        -np 16
        -cb
        -t 16
        -tb 16
        -b 4096
        -ub 2048
        --flash-attn on
        --flash-attn-type 2
        -ctk q4_0
        -ctv q4_0
        --no-mmap
        --jinja
        --tools all
        --metrics
    )
    echo "   Mode: GPU MAX (16 slots, 8192 ctx, KV quant)"
fi

echo ""
echo "🚀 Starting llama-server with RTX 3080 Ti optimizations..."

nohup $SERVER_BIN \
    "${PARAMS[@]}" \
    --port $PORT \
    --host 0.0.0.0 \
    > /tmp/llama-server.log 2>&1 &

# Wait for server ready
echo "⏳ Waiting for server..."
for i in {1..20}; do
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}✅ SERVER READY${NC}"
        echo "   URL: http://localhost:$PORT"
        echo "   Docs: http://localhost:$PORT/docs"
        
        # Show slot info
        curl -s http://localhost:$PORT/slots 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    slots = data.get('slots', [])
    print(f'   Concurrent slots: {len(slots)}')
except: pass
" 2>/dev/null || true
        
        echo ""
        echo "📝 Startup flags used:"
        echo "   -ngl 99              (all layers GPU)"
        echo "   -c 8192              (context size)"
        echo "   -np 16               (parallel slots)"
        echo "   -b 4096 -ub 2048     (batch sizes)"
        echo "   --flash-attn on      (Flash Attention)"
        echo "   --flash-attn-type 2  (2025+ kernel)"
        echo "   -ctk q4_0 -ctv q4_0  (KV cache quant)"
        echo "   --no-mmap            (memory efficiency)"
        echo "   -t 16                (CPU threads)"
        exit 0
    fi
    sleep 1
done

echo -e "${RED}❌ Failed to start server${NC}"
echo ""
echo "Log output:"
tail -20 /tmp/llama-server.log
exit 1
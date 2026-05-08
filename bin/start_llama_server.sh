#!/bin/bash
# N-XYME GGUF Inference Server - BLEEDING EDGE OPTIMIZED
# Optimized for: RTX 3080 Ti + AMD Ryzen 7 7800X3D

set -e

# === COLORS ===
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════╗"
echo -e "${BLUE}║  N-XYME GGUF ENGINE v2.1 (BLEEDING EDGE) ║"
echo -e "${BLUE}║  RTX 3080 Ti + AMD Ryzen 7 7800X3D   ║"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"

# === CONFIG ===
PORT=${PORT:-9000}
MODEL_DIR="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models"
SERVER_BIN="/home/nxyme/llama.cpp/build/bin/llama-server"

# Default model (can override with MODEL=...)
MODEL=${MODEL:-rosetta-v5-q8_0.gguf}
CONTEXT=${CONTEXT:-4096}

# === HARDWARE DETECTION ===
echo -e "${YELLOW}Detecting hardware...${NC}"

# GPU detection
N_GPUS=0
GPU_NAME=""
GPU_VRAM=0
if command -v nvidia-smi &> /dev/null; then
    N_GPUS=$(nvidia-smi --query-gpu=gpu_name --format=csv,noheader 2>/dev/null | wc -l)
    if [ "$N_GPUS" -gt 0 ]; then
        GPU_NAME=$(nvidia-smi --query-gpu=gpu_name --format=csv,noheader 2>/dev/null | head -1)
        GPU_VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -1 | tr -d 'MiB')
        echo -e "${GREEN}GPU: $GPU_NAME (${GPU_VRAM} MiB)${NC}"
    fi
fi

# CPU detection
CPU_MODEL=$(lscpu | grep "Model name" | cut -d: -f2 | xargs)
CPU_CORES=$(nproc)
echo -e "${GREEN}CPU: $CPU_MODEL ($CPU_CORES cores)${NC}"

RAM_TOTAL=$(free -h | grep Mem | awk '{print $2}')
RAM_FREE=$(free -h | grep Mem | awk '{print $7}')
echo -e "${GREEN}RAM: ${RAM_TOTAL} total, ${RAM_FREE} free${NC}"

# === ENVIRONMENT OPTIMIZATIONS ===
# CUDA Graph for reduced kernel launch overhead
export GGML_CUDA_GRAPH_OPT=1
export GGML_CUDA_ALLOCATOR=1
export CUDA_LAUNCH_BLOCKING=0

export OMP_PROC_BIND=close
export OMP_PLACES=cores

# === OPTIMIZATION FLAGS ===
NGL_FLAG=""
FLASH_ATTN=""
KV_CACHE_QUANT=""
EXTRA_FLAGS=""
BATCH_SIZE=""
N_THREADS=""

if [ "$N_GPUS" -gt 0 ]; then
    echo -e "${YELLOW}>>> GPU MODE (RTX 3080 Ti)${NC}"
    
    # All layers on GPU - CRITICAL for performance
    NGL_FLAG="-ngl 99 --main-gpu 0"
    
    # Flash Attention - 1.5x speedup
    FLASH_ATTN="--flash-attn on"
    
    # KV Cache Quantization - 2x context, lower VRAM
    KV_CACHE_QUANT="-ctk q8_0 -ctv q8_0"
    
    # Unified KV cache + RAM cache for performance
    EXTRA_FLAGS="--kv-unified --cache-ram 2048 --cache-type-k q8_0 --cache-type-v q8_0"
    
    # Batch tuning - verified optimal for 3080 Ti
    BATCH_SIZE="-b 512 -ub 512"
    
    # Thread tuning - verified optimal for 7800X3D (benchmark: t6 > t8 > t4)
    N_THREADS="-t 6 -tb 6"
    
    echo -e "${GREEN}Optimizations:${NC}"
    echo "  - GPU layers: 99 (ALL)"
    echo "  - Flash Attention: ON"
    echo "  - KV Cache: Q8_0"
    echo "  - Batch: 512"
    echo "  - Threads: 6 (7800X3D tuned)"
    echo "  - RAM Cache: 2048MB"
else
    echo -e "${YELLOW}>>> CPU MODE${NC}"
    
    FLASH_ATTN=""
    KV_CACHE_QUANT="-ctk q4_0 -ctv q4_0"
    EXTRA_FLAGS="--cache-ram 4096 --cache-type-k q4_0 --cache-type-v q4_0"
    BATCH_SIZE="-b 256 -ub 256"
    N_THREADS="-t $CPU_CORES -tb $((CPU_CORES/2))"
    
    echo -e "${GREEN}Optimizations:${NC}"
    echo "  - KV Cache: Q4_0"
    echo "  - Batch: 256"
    echo "  - Threads: $CPU_CORES"
    echo "  - RAM Cache: 4096MB"
fi

# === STOP EXISTING SERVER ===
echo -e "${YELLOW}Stopping existing server on port $PORT...${NC}"
fuser -k $PORT/tcp 2>/dev/null || true
sleep 1

# === VERIFY MODEL ===
MODEL_PATH="$MODEL_DIR/$MODEL"
if [ ! -f "$MODEL_PATH" ]; then
    echo -e "${RED}ERROR: Model not found: $MODEL_PATH${NC}"
    echo "Available models:"
    ls -lh "$MODEL_DIR"/*.gguf 2>/dev/null | head -10
    exit 1
fi
MODEL_SIZE=$(du -h "$MODEL_PATH" | cut -f1)
echo -e "${GREEN}Model: $MODEL ($MODEL_SIZE)${NC}"

# === START SERVER ===
echo -e "${YELLOW}Starting llama-server...${NC}"

cd /home/nxyme
nohup $SERVER_BIN \
  -m "$MODEL_PATH" \
  $NGL_FLAG \
  -c $CONTEXT \
  -np 4 \
  $N_THREADS \
  $BATCH_SIZE \
  $FLASH_ATTN \
  $KV_CACHE_QUANT \
  $EXTRA_FLAGS \
  --no-mmap \
  --jinja \
  --port $PORT \
  --host 0.0.0.0 \
  > /tmp/llama-server-$PORT.log 2>&1 &

SERVER_PID=$!
echo "PID: $SERVER_PID"

# === WAIT FOR HEALTH ===
echo -e "${YELLOW}Waiting for server...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Server READY on port $PORT${NC}"
        
        # Get token limit
        TOKENS=$(curl -s http://localhost:$PORT/v1/models | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0].get('meta',{}).get('n_params','N/A'))" 2>/dev/null || echo "N/A")
        
        echo -e "${GREEN}=== ENGINE STATUS ===${NC}"
        echo "Model: $MODEL"
        echo "Parameters: $TOKENS"
        echo "Context: $CONTEXT"
        echo "Port: $PORT"
        echo "PID: $SERVER_PID"
        echo "Log: /tmp/llama-server-$PORT.log"
        
        # Quick benchmark
        echo -e "${YELLOW}Quick benchmark...${NC}"
        START=$(date +%s%3N)
        curl -s http://localhost:$PORT/v1/chat/completions \
          -H "Content-Type: application/json" \
          -d '{"messages":[{"role":"user","content":"Count to 3","max_tokens":20}]}' > /dev/null
        END=$(date +%s%3N)
        LATENCY=$((END - START))
        echo -e "${GREEN}Latency: ${LATENCY}ms${NC}"
        
        exit 0
    fi
    sleep 1
done

echo -e "${RED}✗ Server FAILED to start${NC}"
echo "Log:"
tail -20 /tmp/llama-server-$PORT.log
exit 1
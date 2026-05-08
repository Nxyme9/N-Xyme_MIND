#!/bin/bash
# N-XYME GGUF Inference Server
# High-performance local LLM inference with GPU acceleration
# Homepage: https://github.com/Nxyme9/gguf-inference

set -e

# Configuration
PORT=${PORT:-8080}
MODEL_DIR="${MODEL_DIR:-/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models}"
SERVER_BIN="${SERVER_BIN:-/home/nxyme/llama.cpp/build/bin/llama-server}"
MODEL=${1:-"qwen2.5-0.5b-instruct-q4_k_m.gguf"}
MODE=${2:-"balanced"}  # balanced | max-throughput | low-latency | auto

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================
# HARDWARE DETECTION
# ============================================

detect_hardware() {
    echo "🔍 Detecting hardware..."
    
    # Detect GPU
    N_GPUS=0
    GPU_NAME=""
    TOTAL_VRAM=0
    
    if command -v nvidia-smi &> /dev/null; then
        N_GPUS=$(nvidia-smi --query-gpu=gpu_name --format=csv,noheader 2>/dev/null | wc -l)
        if [ "$N_GPUS" -gt 0 ]; then
            GPU_NAME=$(nvidia-smi --query-gpu=gpu_name --format=csv,noheader 2>/dev/null | head -1)
            TOTAL_VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -1 | sed 's/ MiB//')
            echo -e "${GREEN}✅ Found NVIDIA GPU: $GPU_NAME${NC}"
            echo "   VRAM: ${TOTAL_VRAM} MiB"
        fi
    fi
    
    # Detect CPU
    if [ -f /proc/cpuinfo ]; then
        CPU_CORES=$(grep -c processor /proc/cpuinfo)
        CPU_NAME=$(grep "model name" /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)
        echo "   CPU: $CPU_NAME ($CPU_CORES cores)"
    fi
    
    # Detect RAM
    if [ -f /proc/meminfo ]; then
        TOTAL_RAM=$(grep MemTotal /proc/meminfo | awk '{print $2}')
        TOTAL_RAM_GB=$((TOTAL_RAM / 1024 / 1024))
        echo "   RAM: ${TOTAL_RAM_GB} GiB"
    fi
    
    # Return values
    echo "$N_GPUS" > /tmp/nxyme_n_gpus
    echo "$TOTAL_VRAM" > /tmp/nxyme_vram
    echo "$CPU_CORES" > /tmp/nxyme_cores
}

# ============================================
# AUTO MODE: Select optimal configuration
# ============================================

auto_select_mode() {
    local n_gpus=$(cat /tmp/nxyme_n_gpus 2>/dev/null || echo "0")
    local vram=$(cat /tmp/nxyme_vram 2>/dev/null || echo "0")
    local cores=$(cat /tmp/nxyme_cores 2>/dev/null || echo "4")
    
    if [ "$n_gpus" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  No GPU detected - running in CPU mode${NC}"
        echo "   Tip: For better performance, install CUDA-enabled llama.cpp"
        MODE="cpu"
    elif [ "$vram" -lt 6000 ]; then
        echo "   VRAM < 6GB - using low-latency mode"
        MODE="low-latency"
    elif [ "$vram" -lt 10000 ]; then
        echo "   VRAM < 10GB - using balanced mode"
        MODE="balanced"
    else
        echo "   VRAM >= 10GB - using max-throughput mode"
        MODE="max-throughput"
    fi
}

# ============================================
# CONFIGURATION BY MODE
# ============================================

get_params() {
    local mode=$1
    local model=$2
    
    case $mode in
        balanced)
            # Sweet spot - RTX 3080 Ti (12.5GB) OPTIMIZED
            PARAMS=(
                -m "$MODEL_DIR/$model"
                -ngl 99
                -c 8192
                -np 12
                -cb
                -t 16
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
            ;;
        max-throughput)
            # Maximum throughput for large models - RTX 3080 Ti (12.5GB) OPTIMIZED
            PARAMS=(
                -m "$MODEL_DIR/$model"
                -ngl 99
                -c 8192
                -np 16
                -cb
                -t 16
                -b 4096
                -ub 2048
                -tb 16
                --flash-attn on
                --flash-attn-type 2
                -ctk q4_0
                -ctv q4_0
                --no-mmap
                --jinja
                --tools all
                --metrics
            )
            ;;
        low-latency)
            # Low latency for single requests
            PARAMS=(
                -m "$MODEL_DIR/$model"
                -ngl 99
                -c 2048
                -np 4
                -cb
                -t 2
                -b 512
                -ub 256
                --flash-attn on
                --flash-attn-type 2
                -ctk q4_0
                -ctv q4_0
                --no-mmap
                --jinja
                --tools all
                --metrics
            )
            ;;
        cpu)
            # CPU-only mode (no GPU)
            PARAMS=(
                -m "$MODEL_DIR/$model"
                -c 2048
                -np 4
                -cb
                -t "$(nproc)"
                -b 512
                -ub 256
                --jinja
                --tools all
                --metrics
            )
            ;;
    esac
}

# ============================================
# MAIN
# ============================================

main() {
    echo "═══════════════════════════════════════════════════════════"
    echo "  N-XYME GGUF Inference Server v1.0"
    echo "  High-performance local LLM inference"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    
    # Hardware detection
    detect_hardware
    
    # Auto-select mode if needed
    if [ "$MODE" = "auto" ]; then
        auto_select_mode
    fi
    
    echo ""
    echo "📦 Model: $MODEL"
    echo "⚙️  Mode: $MODE"
    echo ""
    
    # Check model exists
    if [ ! -f "$MODEL_DIR/$MODEL" ]; then
        echo -e "${RED}❌ Model not found: $MODEL_DIR/$MODEL${NC}"
        echo ""
        echo "Available models:"
        ls -lh "$MODEL_DIR"/*.gguf 2>/dev/null || echo "   (no models found)"
        exit 1
    fi
    
    # Check server binary exists
    if [ ! -f "$SERVER_BIN" ]; then
        echo -e "${RED}❌ llama-server not found: $SERVER_BIN${NC}"
        echo "   Build llama.cpp first: see docs/BUILD.md"
        exit 1
    fi
    
    # Kill existing server
    fuser -k $PORT/tcp 2>/dev/null || true
    sleep 1
    
    # Get parameters
    get_params "$MODE" "$MODEL"
    
    echo "🚀 Starting server..."
    echo "   Parameters: ${PARAMS[@]}"
    echo ""
    
    # Start server
    nohup $SERVER_BIN \
        "${PARAMS[@]}" \
        --port $PORT \
        --host 0.0.0.0 \
        > /tmp/llama-server.log 2>&1 &
    
    # Wait for server to be ready
    echo "⏳ Waiting for server..."
    for i in {1..30}; do
        if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
            echo ""
            echo -e "${GREEN}✅ Server ready!${NC}"
            echo "   URL: http://localhost:$PORT"
            echo "   Docs: http://localhost:$PORT/docs"
            echo ""
            
            # Show slot info
            curl -s http://localhost:$PORT/slots | python3 -c "
import sys, json
data = json.load(sys.stdin)
slots = data.get('slots', [])
print(f'   Slots: {len(slots)} parallel')
for s in slots[:3]:
    print(f'      - {s.get(\"id\", \"?\")}: {s.get(\"state\", \"?\")}')
" 2>/dev/null || true
            
            exit 0
        fi
        sleep 1
    done
    
    echo -e "${RED}❌ Failed to start server${NC}"
    echo ""
    echo "Log output:"
    tail -20 /tmp/llama-server.log
    exit 1
}

main "$@"

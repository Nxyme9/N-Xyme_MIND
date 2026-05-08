#!/bin/bash
# GGUF Model Server Manager - Auto-startup with model hot-swap
# Features: Automatic startup, model switching, health monitoring

PORT=8080
MODEL_DIR="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models"
SERVER_BIN="/home/nxyme/llama.cpp/build/bin/llama-server"
LOG_FILE="/tmp/llama-server.log"
PID_FILE="/tmp/llama-server.pid"

# Default model
DEFAULT_MODEL="qwen2.5-0.5b-instruct-q4_k_m.gguf"

# Thread configuration (default: 16 for 7800X3D, can be overridden with -t flag)
THREADS=16

# Parse arguments
ACTION=${1:-start}
MODEL=${2:-$DEFAULT_MODEL}
CONTEXT_PRESET=${3:-medium}

# Parse optional flags
shift 3
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--threads)
            THREADS=$2
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Context presets with KV cache memory calculation
case $CONTEXT_PRESET in
    short)
        CONTEXT_SIZE=2048
        KV_CACHE_MB=32
        YARN_FLAG=""
        ;;
    medium)
        CONTEXT_SIZE=4096
        KV_CACHE_MB=64
        YARN_FLAG=""
        ;;
    long)
        CONTEXT_SIZE=8192
        KV_CACHE_MB=128
        YARN_FLAG=""
        ;;
    xlong)
        CONTEXT_SIZE=16384
        KV_CACHE_MB=256
        YARN_FLAG="--rope-scaling yarn --rope-scale 4"
        ;;
    xxl)
        CONTEXT_SIZE=32768
        KV_CACHE_MB=512
        YARN_FLAG="--rope-scaling yarn --rope-scale 8"
        ;;
    huge)
        CONTEXT_SIZE=65536
        KV_CACHE_MB=1024
        YARN_FLAG="--rope-scaling yarn --rope-scale 16 --yarn-ext-factor 0.75 --yarn-attn-factor 1.0"
        ;;
    *)
        echo "❌ Unknown preset: $CONTEXT_PRESET"
        echo "Valid presets: short, medium, long, xlong, xxl, huge"
        exit 1
        ;;
esac

# Conditional flash-attn: helps when context >1K, hurts when <256
FLASH_ATTN_FLAG=""
if [ "$CONTEXT_SIZE" -gt 1024 ]; then
    FLASH_ATTN_FLAG="--flash-attn on"
fi

get_pid() {
    cat "$PID_FILE" 2>/dev/null
}

is_running() {
    local pid=$(get_pid)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    fi
    return 1
}

start_server() {
    local model=$1
    
    if is_running; then
        echo "⚠️  Server already running (PID: $(get_pid))"
        return 0
    fi
    
    # Kill any existing on port
    fuser -k $PORT/tcp 2>/dev/null || true
    sleep 1
    
    local model_path="$MODEL_DIR/$model"
    if [ ! -f "$model_path" ]; then
        echo "❌ Model not found: $model_path"
        return 1
    fi
    
    echo "🚀 Starting GPU-accelerated llama-server with $model..."
    
    # GPU-optimized parameters:
    #   -ngl 99: Offload all layers to GPU
    #   -t 4: Thread count (reduced for GPU focus)
    #   --flash-attn on: Flash Attention
    #   -ctk q4_0 -ctv q4_0: KV cache quantization
    #   --no-mmap: Faster loading
    nohup $SERVER_BIN \
        -m "$model_path" \
        -ngl 99 \
        -c $CONTEXT_SIZE \
        -np 8 \
        -cb \
        -t $THREADS \
        $FLASH_ATTN_FLAG \
        $YARN_FLAG \
        -ctk q4_0 \
        -ctv q4_0 \
        --no-mmap \
        --jinja \
        --tools all \
        --metrics \
        --port $PORT \
        --host 127.0.0.1 \
        > "$LOG_FILE" 2>&1 &
    
    echo $! > "$PID_FILE"
    
    # Wait for server to be ready
    for i in {1..20}; do
        if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
            echo "✅ GPU-accelerated server started on port $PORT with model: $model"
            echo "   PID: $(get_pid)"
            echo "   Context: $CONTEXT_SIZE tokens (${CONTEXT_PRESET} preset, ~${KV_CACHE_MB}MB KV cache)"
            echo "   GPU: -ngl 99, -t $THREADS, $FLASH_ATTN_FLAG"
            echo "   Memory: -ctk q4_0 -ctv q4_0"
            [ -n "$YARN_FLAG" ] && echo "   YaRN: $YARN_FLAG"
            echo "   Features: 8 parallel slots, tool calling, continuous batching"
            return 0
        fi
        sleep 1
    done
    
    echo "❌ Failed to start server"
    cat "$LOG_FILE" | tail -10
    return 1
}

stop_server() {
    if is_running; then
        echo "🛑 Stopping server..."
        kill $(get_pid) 2>/dev/null
        rm -f "$PID_FILE"
        sleep 2
        echo "✅ Server stopped"
    else
        echo "⚠️  Server not running"
    fi
    
    # Also kill any on port
    fuser -k $PORT/tcp 2>/dev/null || true
}

restart_server() {
    stop_server
    sleep 1
    start_server "$MODEL"
}

status_server() {
    if is_running; then
        echo "✅ Server running"
        echo "   PID: $(get_pid)"
        curl -s http://localhost:$PORT/models | python3 -c "
import sys, json
d = json.load(sys.stdin)
m = d.get('data', [{}])[0]
print(f'   Model: {m.get(\"id\", \"unknown\")}')" 2>/dev/null || true
    else
        echo "❌ Server not running"
    fi
}

switch_model() {
    local new_model=$1
    
    echo "🔄 Switching to model: $new_model"
    restart_server
}

list_models() {
    echo "📦 Available models:"
    ls -lh "$MODEL_DIR"/*.gguf 2>/dev/null | awk '{print "   " $9 " (" $5 ")"}'
}

health_check() {
    if is_running; then
        local health=$(curl -s http://localhost:$PORT/health)
        if [ "$health" = '{"status":"ok"}' ]; then
            echo "✅ Health check passed"
            return 0
        fi
    fi
    echo "❌ Health check failed"
    return 1
}

# Main
case $ACTION in
    start)
        start_server "$MODEL"
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        status_server
        ;;
    switch)
        switch_model "$MODEL"
        ;;
    list)
        list_models
        ;;
    health)
        health_check
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|switch|list|health} [model] [context_preset] [-t threads]"
        echo ""
        echo "Commands:"
        echo "  start [model] [preset] [-t threads] - Start server with model"
        echo "                                        Presets: short(2048), medium(4096), long(8192), xlong(16384)"
        echo "                                        Threads: 1, 8, 16 (default: 8)"
        echo "  stop            - Stop server"
        echo "  restart         - Restart server"
        echo "  status          - Show server status"
        echo "  switch <model> - Switch to different model"
        echo "  list            - List available models"
        echo "  health          - Check server health"
        ;;
esac

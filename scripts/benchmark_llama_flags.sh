#!/usr/bin/env bash
#===============================================================================
# LLaMA Flags Benchmark Script
# Tests various llama-server optimization flags on THIS hardware
#===============================================================================
# Tests:
#   1. Thread configs: -t 1 vs -t 8 vs --cpu-strict
#   2. Flash Attention: with/without --flash-attn
#   3. Context fitting: with/without --fit
#   4. Context sizes: 2048, 4096, 8192
#===============================================================================

set -e

# Config
SERVER_BIN="${SERVER_BIN:-/home/nxyme/llama.cpp/build/bin/llama-server}"
MODEL_DIR="${MODEL_DIR:-/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models}"
MODEL="${MODEL:-qwen2.5-0.5b-instruct-q4_k_m.gguf}"
PORT="${PORT:-8089}"  # Use different port to avoid conflicts
TEST_PROMPT="Explain what a recursive function is in Python. Write a detailed response with code examples."
MAX_TOKENS=256
WARMUP_RUNS=2
BENCH_RUNS=3

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

#-------------------------------------------------------------------------------
# Helper functions
#-------------------------------------------------------------------------------

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_success() { echo -e "${GREEN}[OK]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

cleanup() {
    log_info "Cleaning up..."
    fuser -k $PORT/tcp 2>/dev/null || true
    pkill -f "llama-server.*--port $PORT" 2>/dev/null || true
}

wait_for_server() {
    local max_attempts=30
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:$PORT/health >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
        ((attempt++))
    done
    return 1
}

get_tokens_per_sec() {
    local result="$1"
    # Check timings.predicted_per_second (generation speed)
    local pred_tps=$(echo "$result" | grep -oP '"predicted_per_second":\s*\K[0-9.]+' | head -1)
    # Fallback to tokens_per_second (overall)
    local tokens=$(echo "$result" | grep -oP '"tokens_per_second":\s*\K[0-9.]+' | head -1)
    
    if [ -n "$pred_tps" ]; then
        echo "$pred_tps"
    elif [ -n "$tokens" ]; then
        echo "$tokens"
    else
        echo "0"
    fi
}

run_benchmark() {
    local extra_args="$1"
    local description="$2"
    
    # Kill any existing server on our port
    fuser -k $PORT/tcp 2>/dev/null || true
    sleep 1
    
    log_info "Testing: $description"
    log_info "  Args: $extra_args"
    
    # Start server
    cd /home/nxyme
    local server_cmd="$SERVER_BIN -m $MODEL_DIR/$MODEL --port $PORT -np 1 -ngl 99 $extra_args"
    
    # Check if flash-attn is in args
    if echo "$extra_args" | grep -q "flash-attn"; then
        server_cmd="$server_cmd --flash-attn on"
    fi
    
    $server_cmd > /tmp/llama_server_$PORT.log 2>&1 &
    SERVER_PID=$!
    
    # Wait for server
    if ! wait_for_server; then
        log_error "Server failed to start"
        cat /tmp/llama_server_$PORT.log
        kill $SERVER_PID 2>/dev/null || true
        return 1
    fi
    
    log_success "Server running (PID: $SERVER_PID)"
    
    # Warmup
    for i in $(seq 1 $WARMUP_RUNS); do
        curl -s http://localhost:$PORT/v1/chat/completions \
            -H "Content-Type: application/json" \
            -d "{\"model\": \"$(basename $MODEL)\", \"messages\": [{\"role\": \"user\", \"content\": \"Hi\"}], \"max_tokens\": 10}" \
            > /dev/null 2>&1
    done
    
    # Benchmark runs
    local total_tps=0
    local successful_runs=0
    
    for i in $(seq 1 $BENCH_RUNS); do
        local result=$(curl -s http://localhost:$PORT/v1/chat/completions \
            -H "Content-Type: application/json" \
            -d "{
                \"model\": \"$(basename $MODEL)\",
                \"messages\": [{\"role\": \"user\", \"content\": \"$TEST_PROMPT\"}],
                \"max_tokens\": $MAX_TOKENS,
                \"temperature\": 0.3
            }")
        
        if echo "$result" | grep -q "content"; then
            local tps=$(get_tokens_per_sec "$result")
            total_tps=$(python3 -c "print($total_tps + $tps)")
            ((successful_runs++))
            echo "    Run $i: ${tps} tok/s"
        else
            log_warn "Run $i failed, result: $result"
        fi
    done
    
    # Cleanup
    kill $SERVER_PID 2>/dev/null || true
    fuser -k $PORT/tcp 2>/dev/null || true
    sleep 1
    
    if [ "$successful_runs" -gt 0 ]; then
        local avg_tps=$(python3 -c "print(round($total_tps / $successful_runs, 2))")
        echo "    ${GREEN}AVG: $avg_tps tok/s${NC}"
        echo "$avg_tps"
        return 0
    else
        log_error "All runs failed"
        return 1
    fi
}

print_header() {
    echo ""
    echo "==============================================================================="
    echo " $1"
    echo "==============================================================================="
}

#-------------------------------------------------------------------------------
# Main benchmark execution
#----------------------------------------------------------------------------===

trap cleanup EXIT

# Check prerequisites
if [ ! -f "$SERVER_BIN" ]; then
    log_error "llama-server not found at $SERVER_BIN"
    exit 1
fi

if [ ! -f "$MODEL_DIR/$MODEL" ]; then
    log_error "Model not found at $MODEL_DIR/$MODEL"
    exit 1
fi

log_info "Starting LLaMA Flags Benchmark"
log_info "  Model: $MODEL"
log_info "  Server: $SERVER_BIN"
log_info "  Port: $PORT"

# Detect hardware
log_info "Hardware detection:"
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null || true
else
    echo "  No NVIDIA GPU detected - CPU mode"
fi

# Detect CPU
if [ -f /proc/cpuinfo ]; then
    cpu_model=$(grep "model name" /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)
    cpu_cores=$(nproc)
    echo "  CPU: $cpu_model ($cpu_cores cores)"
fi

# Store results
declare -A RESULTS

#-------------------------------------------------------------------------------
# Test 1: Thread configurations
#-------------------------------------------------------------------------------
print_header "THREAD CONFIGURATIONS"

RESULTS["t1"]=$(run_benchmark "-t 1" "Single thread (-t 1)")
RESULTS["t8"]=$(run_benchmark "-t 8" "8 threads (-t 8)")
RESULTS["t16"]=$(run_benchmark "-t 16" "16 threads (-t 16)")
RESULTS["t8-no-ht"]=$(run_benchmark "-t 8 --cpu-strict 1" "8 threads + cpu-strict")

#-------------------------------------------------------------------------------
# Test 2: Flash Attention
#-------------------------------------------------------------------------------
print_header "FLASH ATTENTION"

RESULTS["no-flash"]=$(run_benchmark "" "No flash attention (baseline)")
RESULTS["flash"]=$(run_benchmark "--flash-attn on" "With flash attention")

#-------------------------------------------------------------------------------
# Test 3: --fit flag
#-------------------------------------------------------------------------------
print_header "CONTEXT FITTING"

RESULTS["no-fit"]=$(run_benchmark "-c 4096 --fit off" "Without --fit (baseline)")
RESULTS["fit"]=$(run_benchmark "-c 4096 --fit on" "With --fit")

#-------------------------------------------------------------------------------
# Test 4: Context sizes
#-------------------------------------------------------------------------------
print_header "CONTEXT SIZES"

for ctx in 2048 4096 8192; do
    RESULTS["ctx-$ctx"]=$(run_benchmark "-c $ctx" "Context size $ctx")
done

#-------------------------------------------------------------------------------
# Summary
#-------------------------------------------------------------------------------
print_header "BENCHMARK RESULTS SUMMARY"

echo ""
printf " %-25s | %s\n" "Test Configuration" "Tokens/sec"
echo "--------------------------- | ------------"

printf " %-25s | %s\n" "Thread: -t 1" "${RESULTS[t1]:-N/A}"
printf " %-25s | %s\n" "Thread: -t 8" "${RESULTS[t8]:-N/A}"
printf " %-25s | %s\n" "Thread: -t 16" "${RESULTS[t16]:-N/A}"
printf " %-25s | %s\n" "Thread: -t 8 no-HT" "${RESULTS[t8-no-ht]:-N/A}"
echo "--------------------------- | ------------"
printf " %-25s | %s\n" "No Flash Attention" "${RESULTS[no-flash]:-N/A}"
printf " %-25s | %s\n" "With Flash Attention" "${RESULTS[flash]:-N/A}"
echo "--------------------------- | ------------"
printf " %-25s | %s\n" "Without --fit" "${RESULTS[no-fit]:-N/A}"
printf " %-25s | %s\n" "With --fit" "${RESULTS[fit]:-N/A}"
echo "--------------------------- | ------------"
printf " %-25s | %s\n" "Context: 2048" "${RESULTS[ctx-2048]:-N/A}"
printf " %-25s | %s\n" "Context: 4096" "${RESULTS[ctx-4096]:-N/A}"
printf " %-25s | %s\n" "Context: 8192" "${RESULTS[ctx-8192]:-N/A}"

# Find best configs
echo ""
log_success "RECOMMENDATIONS FOR THIS HARDWARE:"

# Best thread config
best_thread="t1"
best_tps="${RESULTS[t1]:-0}"
for config in t8 t16 t8-no-ht; do
    if python3 -c "print(${RESULTS[$config]:-0} > $best_tps)"; then
        best_tps="${RESULTS[$config]:-0}"
        best_thread="$config"
    fi
done
echo "  Best thread config: $best_thread (${best_tps} tok/s)"

# Flash attention
if python3 -c "print(${RESULTS[flash]:-0} > ${RESULTS[no-flash]:-0})"; then
    echo "  Flash Attention: RECOMMENDED (+$(python3 -c "print(round(${RESULTS[flash]:-0} - ${RESULTS[no-flash]:-0}, 2))") tok/s)"
else
    echo "  Flash Attention: Not beneficial on this hardware"
fi

# --fit flag
if python3 -c "print(${RESULTS[fit]:-0} > ${RESULTS[no-fit]:-0})"; then
    echo "  --fit flag: RECOMMENDED (+$(python3 -c "print(round(${RESULTS[fit]:-0} - ${RESULTS[no-fit]:-0}, 2))") tok/s)"
else
    echo "  --fit flag: Not beneficial on this hardware"
fi

# Best context size
best_ctx="ctx-2048"
best_ctx_tps="${RESULTS[ctx-2048]:-0}"
for ctx in 4096 8192; do
    if python3 -c "print(${RESULTS[ctx-$ctx]:-0} > $best_ctx_tps)"; then
        best_ctx_tps="${RESULTS[ctx-$ctx]:-0}"
        best_ctx="$ctx"
    fi
done
echo "  Best context size: $best_ctx (${best_ctx_tps} tok/s)"

echo ""
log_info "Benchmark complete!"

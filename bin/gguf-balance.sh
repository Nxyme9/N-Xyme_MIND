#!/bin/bash
# N-XYME GGUF Load Balancer - Auto-route to best model

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

MODELS=(
    "qwen2.5-0.5b-instruct-q4_k_m|8088|256|fastest"
    "qwen2.5-coder-7b-q4_k_m|8089|2048|balanced"  
    "rosetta-v5-q8_0|9000|4096|toolcalling"
)

get_port_for_task() {
    local prompt="$1"
    local len=${#prompt}
    
    if [ $len -lt 50 ]; then
        echo "8088"
    elif [ $len -lt 200 ]; then
        echo "8089"  
    else
        echo "9000"
    fi
}

get_model_info() {
    local port="$1"
    curl -s "http://localhost:$port/v1/models" 2>/dev/null | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print(d['data'][0]['id'])
except: print('N/A')
" 2>/dev/null || echo "offline"
}

check_all_models() {
    echo -e "${BLUE}=== GGUF MODEL STATUS ===${NC}"
    
    for entry in "${MODELS[@]}"; do
        IFS='|' read -r name port limit flags <<< "$entry"
        
        if curl -s -w "%{http_code}" -o /dev/null "http://localhost:$port/health" 2>/dev/null | grep -q "200"; then
            model=$(get_model_info $port)
            echo -e "${GREEN}●${NC} Port $port: $model ($flags)"
        else
            echo -e "${RED}●${NC} Port $port: OFFLINE"
        fi
    done
}

benchmark_port() {
    local port=$1
    local warmup=3
    local runs=5
    
    for i in $(seq 1 $warmup); do
        curl -s "http://localhost:$port/v1/chat/completions" \
            -H "Content-Type: application/json" \
            -d '{"messages":[{"role":"user","content":"Hi","max_tokens":5}]}' > /dev/null 2>&1
    done
    
    total=0
    for i in $(seq 1 $runs); do
        start=$(date +%s%3N)
        curl -s "http://localhost:$port/v1/chat/completions" \
            -H "Content-Type: application/json" \
            -d '{"messages":[{"role":"user","content":"Count","max_tokens":20}]}' > /dev/null 2>&1
        end=$(date +%s%3N)
        latency=$((end - start))
        total=$((total + latency))
    done
    
    avg=$((total / runs))
    echo "$avg"
}

route() {
    local prompt="$1"
    local port=$(get_port_for_task "$prompt")
    
    echo "Routing to port $port (prompt length: ${#prompt})"
    curl -s "http://localhost:$port/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d "{\"messages\":[{\"role\":\"user\",\"content\":\"$prompt\",\"max_tokens\":1024}]}"
}

case "${1:-status}" in
    status)
        check_all_models
        ;;
    bench)
        echo -e "${BLUE}=== BENCHMARK ===${NC}"
        for entry in "${MODELS[@]}"; do
            IFS='|' read -r name port limit flags <<< "$entry"
            if curl -s -w "%{http_code}" -o /dev/null "http://localhost:$port/health" 2>/dev/null | grep -q "200"; then
                avg=$(benchmark_port $port)
                echo "$port: ${avg}ms avg"
            fi
        done
        ;;
    route)
        shift
        route "$@"
        ;;
    start)
        echo "Starting all models..."
        for entry in "${MODELS[@]}"; do
            IFS='|' read -r name port limit flags <<< "$entry"
            PORT=$port MODEL=$name bash /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/bin/start_llama_server.sh &
        done
        sleep 5
        check_all_models
        ;;
    *)
        echo "Usage: $0 {status|bench|route <prompt>|start}"
        exit 1
        ;;
esac
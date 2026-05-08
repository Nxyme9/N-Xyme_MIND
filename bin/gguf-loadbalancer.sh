#!/bin/bash
PORT=${1:-9000}
MODEL_DIR="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models"

AVAILABLE_MODELS=(
    "rosetta-v5-q8_0.gguf:Rosetta-v5:410:toolcall"
    "qwen2.5-0.5b-instruct-q4_k_m.gguf:Qwen-0.5B:250:fast"
    "qwen2.5-coder-7b-q4_k_m.gguf:Qwen-7B:131:coder"
)

get_load() {
    curl -s http://localhost:$PORT/v1/chat/completions \
        -H "Content-Type: application/json" \
        -d '{"messages":[{"role":"user","content":"Hi"}],"max_tokens":5}' 2>/dev/null | grep -o "tok" | wc -l
}

choose_model() {
    BEST=""
    BEST_SPEED=0
    for m in "${AVAILABLE_MODELS[@]}"; do
        IFS=':' read -r file name speed flags <<< "$m"
        if [ "$speed" -gt "$BEST_SPEED" ]; then
            BEST="$file"
            BEST_SPEED=$speed
        fi
    done
    echo "$BEST"
}

case "$1" in
    start)
        MODEL=$(choose_model)
        echo "Starting $MODEL on port $PORT..."
        fuser -k $PORT/tcp 2>/dev/null
        cd /home/nxyme
        /home/nxyme/llama.cpp/build/bin/llama-server \
            -m "$MODEL_DIR/$MODEL" \
            -ngl 99 --main-gpu 0 \
            --flash-attn on \
            -c 4096 -np 4 -t 8 -b 256 \
            --port $PORT --host 0.0.0.0 &
        sleep 3
        curl -s http://localhost:$PORT/v1/models | python3 -c "import sys,json; print(json.load(sys.stdin)['models'][0]['model'])"
        ;;
    status)
        curl -s http://localhost:$PORT/v1/models | python3 -c "import sys,json; d=json.load(sys.stdin); print('Model:', d['models'][0]['model'])"
        ;;
    bench)
        for i in 1 2 3; do
            t1=$(date +%s%3N)
            curl -s http://localhost:$PORT/v1/chat/completions \
                -H "Content-Type: application/json" \
                -d '{"messages":[{"role":"user","content":"Count: 1"}],"max_tokens":10}' >/dev/null
            t2=$(date +%s%3N)
            echo "$i: $((t2-t1))ms"
        done
        ;;
    switch)
        fuser -k $PORT/tcp 2>/dev/null
        sleep 1
        $0 start
        ;;
    *)
        echo "Usage: $0 {start|status|bench|switch}"
        ;;
esac
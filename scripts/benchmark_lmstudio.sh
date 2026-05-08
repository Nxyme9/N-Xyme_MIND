#!/bin/bash
# Fair Benchmark: llama-server vs LM Studio API
# Run with identical settings for apples-to-apples comparison

PORT_LLAMA=8095
PORT_LMSTUDIO=${1:-8090}  # LM Studio default

echo "=========================================="
echo "Fair Benchmark: llama-server vs LM Studio"
echo "=========================================="
echo ""
echo "Ensure LM Studio is running with:"
echo "  - GPU: Full"
echo "  - Context: 4096"
echo "  - Threads: 16"
echo "  - Flash Attention: ON"
echo ""

MODEL="qwen2.5-0.5b-instruct-q4_k_m.gguf"
MODEL_PATH="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models/$MODEL"
PROMPT="Write a short story about a robot"
MAX_TOKENS=100

# Start llama-server with optimized config
echo "[1] Starting llama-server with -t 16..."
cd /home/nxyme
/home/nxyme/llama.cpp/build/bin/llama-server \
  -m "$MODEL_PATH" \
  --port $PORT_LLAMA \
  -np 1 \
  -ngl 99 \
  -t 16 \
  -c 4096 \
  --flash-attn on \
  --jinja \
  > /tmp/llama_bench.log 2>&1 &

sleep 4

# Test llama-server
echo ""
echo "[2] Testing llama-server..."
for i in 1 2 3; do
  result=$(curl -s http://localhost:$PORT_LLAMA/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"$PROMPT\"}],\"max_tokens\":$MAX_TOKENS}")
  
  pred=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['timings']['predicted_per_second'])" 2>/dev/null)
  echo "  Run $i: ${pred:-ERR} tok/s"
  sleep 0.5
done

# Kill llama-server
fuser -k $PORT_LLAMA/tcp 2>/dev/null

echo ""
echo "=========================================="
echo "Now test LM Studio manually:"
echo "  1. Configure LM Studio with same settings"
echo "  2. Ensure API is enabled (localhost:8090)"
echo "  3. Run same test:"
echo ""
echo "  for i in 1 2 3; do"
echo "    curl -s http://localhost:$PORT_LMSTUDIO/v1/chat/completions \\"
echo "      -H 'Content-Type: application/json' \\"
echo "      -d '{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"$PROMPT\"}],\"max_tokens\":$MAX_TOKENS}' \\"
echo "      | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d[timings][predicted_per_second])'"
echo "  done"
echo "=========================================="

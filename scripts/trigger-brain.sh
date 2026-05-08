#!/bin/bash
# Test/Trigger the N-Xyme Brain
# Usage: bash scripts/trigger-brain.sh [embedding|rosetta|reasoner|status]

ACTION="${1:-status}"

LOG="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/logs/brain-trigger.log"

echo "$(date '+%H:%M:%S') - Trigger: $ACTION" >> "$LOG"

case "$ACTION" in
    embedding)
        cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
        PYTHONPATH=/home/nxyme/N-Xyme_CODE/N-Xyme_MIND python3 -c "
from frankenstein_engine.compatibility import get_embedding
import time
start = time.time()
emb = get_embedding('test')
print(f'Embed: {len(emb)}D in {(time.time()-start)*1000:.1f}ms')
" >> "$LOG" 2>&1
        ;;
    rosetta)
        cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
        PYTHONPATH=/home/nxyme/N-Xyme_CODE/N-Xyme_MIND python3 -c "
from frankenstein_engine.compatibility import translate_to_tool_call
result = translate_to_tool_call('search memory for test')
print(f'Rosetta: {result}')
" >> "$LOG" 2>&1
        ;;
    reasoner)
        cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
        PYTHONPATH=/home/nxyme/N-Xyme_CODE/N-Xyme_MIND python3 -c "
from frankenstein_engine.compatibility import run_reasoning
result = run_reasoning('What is 2+2?')
print(f'Reasoner: {result[:50]}')
" >> "$LOG" 2>&1
        ;;
    status)
        echo "Brain service running: $(systemctl --user is-active nxyme-brain.service)"
        echo "Models: lazy-load on first trigger"
        ;;
esac

cat "$LOG" | tail -5
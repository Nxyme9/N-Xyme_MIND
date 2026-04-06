#!/usr/bin/env bash
# n-xyme-mind.sh — Session lifecycle wrapper with memory integration

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"
if [ -f "env.sh" ]; then
    source env.sh 2>/dev/null || true
fi

echo "========================================"
echo "🧠 N-Xyme MIND — AI Coding Workspace"
echo "========================================"
echo ""

# Step 1: Load memory context
echo "📖 Loading memory context..."
"$PROJECT_ROOT/venvs/athena/bin/python3" -c "
import sys
sys.path.insert(0, '.')
try:
    from packages.memory_core.mcp_server import get_memory_stats
    stats = get_memory_stats()
    keys = list(stats.keys())
    keys_str = ", ".join(keys) if keys else "none"
    print(f'  Memory modules: {len(keys)} ({keys_str})')
    for k, v in stats.items():
        if isinstance(v, dict):
            count = v.get('count', v.get('total', '?'))
            print(f'    ✅ {k}: {count} entries')
        elif isinstance(v, int):
            print(f'    ✅ {k}: {v}')
except Exception as e:
    print(f'  ⚠️  Memory error: {e}')
" 2>&1 || echo "  ⚠️  Memory context load failed (continuing anyway)"

echo ""

# Step 2: Check Ollama
echo "🤖 Checking Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "  ✅ Ollama running"
else
    echo "  ⚠️  Ollama not running"
fi

echo ""

# Step 3: Start OpenCode (use system python which has opencode installed)
echo "🚀 Starting OpenCode..."
if command -v opencode &> /dev/null; then
    opencode "$@" || true
else
    echo "  ⚠️  opencode not found in PATH"
    echo "  Trying: pip install opencode"
fi

# Step 4: Save session summary
echo ""
echo "💾 Saving session summary..."
"$PROJECT_ROOT/venvs/athena/bin/python3" -c "
import sys, json
from datetime import datetime, timezone
sys.path.insert(0, '.')

state_path = '.sisyphus/session-state.json'
try:
    with open(state_path) as f:
        state = json.load(f)
except:
    state = {}

state['last_updated'] = datetime.now(timezone.utc).isoformat()
state['last_action'] = 'Session completed'

with open(state_path, 'w') as f:
    json.dump(state, f, indent=2)
print('  ✅ Session state updated')
" 2>&1 || echo "  ⚠️  Session save failed"

echo ""
echo "========================================"
echo "✅ Session ended"
echo "========================================"

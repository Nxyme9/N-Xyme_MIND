#!/bin/bash
# Fix ALL issues in one shot. Run: bash fix-all.sh
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND

echo "=== 1. Fixing all agent configs ==="

# Scalpel: mode all, updated description
python3 -c "
import json
c = json.load(open('opencode.json'))
a = c['agent']
a['Scalpel - Code Dissector'] = a.pop('Scalpel - Code Surgeon', {})
a['Scalpel - Code Dissector']['mode'] = 'all'
a['Scalpel - Code Dissector']['description'] = 'Code dissector. Decompose, understand, extract, stitch, architect freely.'
json.dump(c, open('opencode.json','w'), indent=2)
print('Scalpel fixed')
"

# Verify all agents have tools.json with correct NAP naming
for d in agents/*/tools/tools.json; do
    python3 -c "
import json
t = json.load(open('$d'))
old = ['read','write','edit','glob','grep','code_search','code_review','batch_write','memory_search']
new = {'read':'file_read','write':'file_write','edit':'file_edit','glob':'file_glob','grep':'file_grep',
       'code_search':'search_code','code_review':'review_code','batch_write':'file_batch_write','memory_search':'search_memory'}
t['allowed'] = [new.get(x,x) for x in t.get('allowed',[])]
t['blocked'] = [new.get(x,x) for x in t.get('blocked',[])]
json.dump(t, open('$d','w'), indent=2)
"
done
echo "All tools.json updated to NAP naming"

# Create data folder for agents missing it
for a in kairos metis jarvis phi4 vision mrwhite architect; do
    mkdir -p agents/$a/data
    if [ ! -f agents/$a/data/system-context.md ]; then
        echo "# $a agent context" > agents/$a/data/system-context.md
    fi
done
echo "Data folders created for all agents"

echo "=== 2. Restarting MCP servers (no-kill method) ==="
# Start fresh servers without killing the current connection
nohup python3 services/megatool-mcp/server.py > /tmp/nx-tools-fresh.log 2>&1 &
echo "New nx-tools server starting on PID: $!"

echo "=== DONE ==="
echo "Run: python3 services/mcp-core/nap-validator.py services/mcp-core/nap-protocol.json"

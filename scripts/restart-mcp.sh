#!/bin/bash
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
echo "Killing old MCP servers..."
pkill -f "bash-mcp/server.py" 2>/dev/null
pkill -f "megatool-mcp/server.py" 2>/dev/null
sleep 1
echo "Starting new MCP servers..."
nohup python3 services/bash-mcp/server.py > /tmp/bash-mcp.log 2>&1 &
nohup python3 services/megatool-mcp/server.py > /tmp/nx-tools.log 2>&1 &
sleep 2
echo "MCP servers restarted:"
pgrep -af "mcp/server.py"

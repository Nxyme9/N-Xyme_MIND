# MCP Server Down Runbook

## Symptoms
- Agent reports "MCP server not responding"
- Tool calls fail with connection errors
- Health check shows MCP server offline

## Diagnosis Steps

### 1. Check which MCP server is down
```bash
bash bin/mcp-doctor.sh
```

### 2. Check individual MCP servers
```bash
# Check if MCP processes are running
ps aux | grep mcp | grep -v grep
```

### 3. Check MCP configuration
```bash
python3 -m json.tool opencode.json > /dev/null && echo "Valid" || echo "Invalid"
```

## Resolution

### Restart a specific MCP server:
```bash
# Find the MCP command in opencode.json
python3 -c "
import json
config = json.load(open('opencode.json'))
for name, cfg in config.get('mcp', {}).items():
    print(f'{name}: {cfg.get(\"command\", \"N/A\")}')
"
```

### Restart all MCP servers:
```bash
# Kill existing processes
pkill -f mcp-server || true
pkill -f mcp_server || true

# Restart via OpenCode (agents will auto-reconnect)
```

### If athena-context MCP is down:
```bash
cd packages/athena-context-mcp && ./venv/bin/python -m athena_context_mcp &
```

### If trigger-guardian MCP is down:
```bash
cd packages/trigger-guardian-mcp && ./.venv/bin/python -m trigger_guardian_mcp &
```

### If nx-mind MCP is down:
```bash
cd packages/nx-mind-mcp && ./venv/bin/python -m nx_mind_mcp &
```

## Prevention
- Monitor MCP health: `bash bin/health-l1-pulse.sh`
- Check logs: `ls logs/` for MCP-related errors
- Ensure venvs are active: `ls packages/*/venv/bin/python`

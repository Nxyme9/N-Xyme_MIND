# MCP Server Registry

## Global MCPs (configured in opencode.json)

| Server | Command | Tools | Purpose |
|--------|---------|-------|---------|
| sequential-thinking | npx @modelcontextprotocol/server-sequential-thinking | 1 | Chain-of-thought reasoning |
| memory | npx @modelcontextprotocol/server-memory | 9 | Knowledge graph (entities, relations) |
| context7 | npx @upstash/context7-mcp | 2 | Real-time library documentation |
| filesystem | npx mcp-server-filesystem /home/nxyme | 10 | Scoped file read/write |
| fetch | npx mcp-fetch-server | 4 | HTTP requests |
| git | npx mcp-git | 6 | Git operations |

## Installation

All MCPs are configured in `~/.config/opencode/opencode.json` and loaded via npx:

```bash
# Already configured - loaded via npx from opencode.json
npm install -g @modelcontextprotocol/server-sequential-thinking
npm install -g @modelcontextprotocol/server-memory  
npm install -g @upstash/context7-mcp
npm install -g mcp-server-filesystem
npm install -g mcp-fetch-server
npm install -g mcp-git
```

## Health Check

```bash
# Test each MCP
timeout 3 npx -y @modelcontextprotocol/server-sequential-thinking <<< "" && echo "OK"
timeout 3 npx -y @modelcontextprotocol/server-memory <<< "" && echo "OK"
timeout 3 npx -y @upstash/context7-mcp <<< "" && echo "OK"
timeout 3 npx -y mcp-server-filesystem /home/nxyme <<< "" && echo "OK"
timeout 3 npx -y mcp-fetch-server <<< "" && echo "OK"
timeout 3 npx -y mcp-git <<< "" && echo "OK"
```

## Future MCPs to Add

| Server | Purpose | Priority |
|--------|---------|----------|
| mcp-server-git (full) | Enhanced git operations | High |
| mcp-github | GitHub API integration | High |
| mcp-code-executor | Sandboxed code execution | Medium |
| mcp-sqlite | Database operations | Medium |

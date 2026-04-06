# Athena MCP API Contract

## Overview
The Athena MCP server provides context-aware memory and knowledge retrieval for AI agents.

## Connection
```json
{
  "command": ["./venvs/athena/bin/python", "-m", "athena.mcp_server"],
  "environment": {
    "PYTHONPATH": "./athena/src:."
  }
}
```

## Tools

### `smart_search`
Search Athena's knowledge base using hybrid RAG.

**Input:**
```json
{
  "query": "string - The search query",
  "limit": "number (optional, default 10)",
  "strict": "boolean (optional, default false)",
  "rerank": "boolean (optional, default false)"
}
```

**Output:**
```json
{
  "results": [{"path": "string", "score": "number", "content": "string"}],
  "meta": {"query": "string", "total": "number"}
}
```

### `agentic_search`
Multi-step query decomposition with parallel search.

**Input:**
```json
{
  "query": "string - Complex search query",
  "limit": "number (optional, default 10)",
  "validate": "boolean (optional, default true)"
}
```

### `quicksave`
Save a checkpoint to the current session log.

**Input:**
```json
{
  "summary": "string - Brief description",
  "bullets": "string[] (optional)"
}
```

### `health_check`
Run health audit of Athena's core services.

**Input:** `{}`

**Output:**
```json
{
  "vector_api": "string - status",
  "database": "string - status"
}
```

# Unified Memory MCP API Contract

## Overview
Provides unified memory operations across all memory sources with semantic search, CRUD, and learning capabilities.

## Connection
```json
{
  "command": ["./venvs/athena/bin/python", "-m", "src.memory.mcp_server"],
  "environment": {
    "PYTHONPATH": ".",
    "ROOT": "."
  }
}
```

## Tools

### `search_memories`
Search across all memory sources using unified memory router.

**Input:**
```json
{
  "query": "string - The search query",
  "limit": "number (optional, default 10)",
  "sources": "string[] (optional)"
}
```

### `create_memory`
Create a new memory entry.

**Input:**
```json
{
  "content": "string - Memory content text",
  "kind": "string - note|task|project|doc|summary|preference",
  "scope": "string - global|project|session",
  "tags": "string[] (optional)",
  "metadata": "object (optional)"
}
```

### `update_memory`
Update an existing memory entry.

**Input:**
```json
{
  "memory_id": "string - ID of memory to update",
  "content": "string (optional)",
  "tags": "string[] (optional)",
  "metadata": "object (optional)"
}
```

### `delete_memory`
Delete or archive a memory entry.

**Input:**
```json
{
  "memory_id": "string",
  "hard_delete": "boolean (optional, default false)"
}
```

### `get_memory_stats`
Get statistics about all memory sources.

**Input:** `{}`

### `semantic_search`
Semantic search using embeddings via Ollama.

**Input:**
```json
{
  "query": "string",
  "top_k": "number (optional, default 5)"
}
```

### `route_task`
Get optimal routing decision for a task.

**Input:**
```json
{
  "task_description": "string"
}
```

**Output:**
```json
{
  "level": "number (1-5)",
  "agent": "string",
  "confidence": "number (0-1)",
  "strategy": "string",
  "reason": "string"
}
```

### `record_delegation_outcome`
Log delegation outcome for learning.

**Input:**
```json
{
  "task_id": "string",
  "task_description": "string",
  "level": "number",
  "agent": "string",
  "success": "boolean",
  "latency_ms": "number",
  "tokens_used": "number"
}
```

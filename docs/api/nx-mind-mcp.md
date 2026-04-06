# NX-Mind MCP API Contract

## Overview
Manages project state, session tracking, and MIND (Memory, Intelligence, Navigation, Delegation) context.

## Connection
```json
{
  "command": ["./packages/nx-mind-mcp/venv/bin/python", "-m", "nx_mind_mcp"]
}
```

## Tools

### `get_mind_state`
Returns current MIND state including project, phase, and active tasks.

**Input:** `{}`

**Output:**
```json
{
  "project": "string",
  "phase": "string",
  "active_tasks": "string[]",
  "context": "object",
  "last_updated": "string (ISO 8601)",
  "session_start": "string (ISO 8601)"
}
```

### `update_mind_state`
Updates MIND state with new information.

**Input:**
```json
{
  "project": "string (optional)",
  "phase": "string (optional)",
  "active_tasks": "string[] (optional)",
  "context": "object (optional)",
  "clear_context": "boolean (optional, default false)"
}
```

### `get_session_history`
Returns history of past sessions with summaries.

**Input:**
```json
{
  "limit": "number (optional, default 10)"
}
```

**Output:**
```json
{
  "sessions": [{"id": "string", "summary": "string", "timestamp": "string"}]
}
```

### `set_context`
Sets project context for current session.

**Input:**
```json
{
  "key": "string - Context key (e.g., 'task', 'goal')",
  "value": "string - Context value"
}
```

### `sync_memory`
Sync current MIND state to unified memory system.

**Input:** `{}`

### `get_memory_stats`
Get memory system statistics.

**Input:** `{}`

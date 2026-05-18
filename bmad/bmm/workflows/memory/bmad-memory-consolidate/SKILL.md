---
name: bmad-memory-consolidate
description: Consolidate current session to unified memory for future recall. Use when the user says "save session", "consolidate to memory", "remember this", or "store context".
argument-hint: "[session summary or key points to store] [--target memory|graphiti|both]"
---

# Memory Consolidate Skill

## Overview

This skill consolidates the current session's context into the unified memory system, making it available for future recall. It creates persistent knowledge that survives across sessions.

## On Activation

1. **Identify what to consolidate:**
   - Extract key decisions, learnings, and context from current session
   - Determine target memory systems (memory MCP, Graphiti, or both)
   
2. **Route** — proceed to Stage 1.

## Stages

| # | Stage | Purpose |
|---|-------|---------|
| 1 | Extract | Pull key context from current session |
| 2 | Transform | Format for target memory systems |
| 3 | Persist | Write to memory MCP and/or Graphiti |
| 4 | Confirm | Report consolidation status |

### Stage 1: Extract

Gather context from current session:

```python
# Read current session state
import json
with open('.sisyphus/session-state.json', 'r') as f:
    session = json.load(f)

# Extract: current_task, completed_actions, decisions_made
```

Key elements to capture:
- Current task and its status
- Decisions made during this session
- Any relevant code changes or findings
- User preferences discovered
- Any blockers or pending items

### Stage 2: Transform

Format the extracted context for each target system:

**For Memory MCP (entities + relations):**
```python
entities = [
    {"name": f"session-{timestamp}", "type": "session", "observations": [...]},
    {"name": task_name, "type": "task", "observations": [...]},
]

relations = [
    {"from": "session-{}", "relationType": "worked_on", "to": task_name},
]
```

**For Graphiti (episodes):**
```python
episode = {
    "text": f"Session: {summary}",
    "entity_names": [task_name, user_name],
    "created": timestamp
}
```

### Stage 3: Persist

Write to the target memory systems:

```python
# Write to holographic memory (structured JSON store)
write_memory(content="key decision or context to save", category="architecture")

# Read back to verify
read_memory(memoryId="mem_1234567890")
```

### Stage 4: Confirm

Report consolidation status:

```json
{
  "status": "success",
  "session_id": "{session ID}",
  "entities_created": {count},
  "relations_created": {count},
  "graphiti_episodes": {count},
  "timestamp": "{ISO timestamp}"
}
```

## Output Format

Always return structured result:

```json
{
  "status": "success",
  "consolidated": {
    "entities": {count},
    "relations": {count},
    "episodes": {count}
  },
  "session_summary": "{1-2 sentence summary}",
  "ready_for_recall": true
}
```

## Best Practices

- Consolidate at natural breakpoints (task completion, significant decisions)
- Keep summaries concise — memory MCP works best with focused observations
- Include enough context for future recall but avoid raw transcript storage
- Tag sessions with project/task names for targeted recall
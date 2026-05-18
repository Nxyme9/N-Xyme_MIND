---
name: recall-agent-history
description: Get agent work history from memory. Use when user asks what has been done, what work has been completed, or what did we work on last time.
argument-hint: "[agent-name or omit for all agents]"
---

# Recall Agent History Workflow

## Purpose

Retrieve work history from past sessions across all agents, including:
- Completed tasks and actions
- Code changes and implementations
- Decisions and their rationale
- Issues encountered and resolved

## Workflow Steps

### Step 1: Determine Scope

- If agent name provided: filter to that agent's work
- If no name: retrieve all agent history

### Step 2: Query Memory

Search for agent activity:

```python
# Query memory MCP for agent entity history
from src.memory_mcp import search_agent_history

# Query Graphiti for agent episodes
from src.graphiti_memory import get_agent_episodes

# Query opencode.db for agent messages
from src.unified_memory_mcp import search_opencode
```

### Step 3: Timeline

Organize results into chronological timeline:

```markdown
## Agent History: {agent or "All Agents"}

### Recent Sessions
- **2026-04-02**: {task completed}
- **2026-04-01**: {task completed}

### Key Implementations
- {file}: {what changed}

### Decisions Made
- {decision}: {rationale}
```

## Output

```json
{
  "status": "success",
  "agent": "{name or all}",
  "history": [
    {
      "date": "2026-04-02",
      "task": "...",
      "outcome": "success",
      "artifacts": [...]
    }
  ]
}
```
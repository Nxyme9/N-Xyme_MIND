---
name: consolidate-session
description: Save current session to unified memory. Use at session end or natural breakpoints to persist context for future recall.
argument-hint: "[optional summary focus]"
---

# Consolidate Session Workflow

## Purpose

Save the current session's work to unified memory so it can be recalled in future sessions. This is the primary mechanism for session-to-session continuity.

## Workflow Steps

### Step 1: Gather Session State

Read current session information:

```python
import json
from datetime import datetime

# Read session state
with open('.sisyphus/session-state.json', 'r') as f:
    session = json.load(f)

# Read project context
with open('.context/project-manifest.json', 'r') as f:
    project = json.load(f)

# Read MIND state
from src.nx_mind import get_mind_state
mind = get_mind_state()
```

### Step 2: Extract Key Elements

Pull the important parts:

```python
key_elements = {
    "session_id": session.get("session_id"),
    "current_task": session.get("current_task"),
    "completed_actions": session.get("completed_actions", []),
    "decisions": session.get("decisions_made", []),
    "project": project.get("name"),
    "phase": mind.get("phase"),
    "active_tasks": mind.get("active_tasks", [])
}
```

### Step 3: Persist to Memory

Write to all memory systems:

```python
# To Memory MCP - create entities and relations
from src.memory_mcp import create_entities, create_relations

entities = [
    {"name": f"session-{key_elements['session_id']}", "type": "session", 
     "observations": [f"Task: {key_elements['current_task']}", 
                     f"Project: {key_elements['project']}"]},
    {"name": key_elements['project'], "type": "project",
     "observations": [f"Phase: {key_elements['phase']}"]}
]

relations = [
    {"from": f"session-{key_elements['session_id']}", 
     "relationType": "belongs_to", 
     "to": key_elements['project']},
    {"from": f"session-{key_elements['session_id']}",
     "relationType": "worked_on",
     "to": key_elements['current_task']}
]

create_entities(entities)
create_relations(relations)

# To Graphiti - create episode
from src.graphiti_memory import add_episode

episode = {
    "text": f"Session {key_elements['session_id']}: {key_elements['current_task']}. "
            f"Completed: {key_elements['completed_actions']}. "
            f"Project: {key_elements['project']}, Phase: {key_elements['phase']}",
    "entity_names": [key_elements['project'], key_elements['current_task']],
    "created": datetime.utcnow().isoformat()
}
add_episode(episode)

# To opencode.db - session is already stored automatically
```

### Step 4: Confirm

```json
{
  "status": "success",
  "session_id": "{session_id}",
  "consolidated": {
    "entities": 2,
    "relations": 2,
    "graphiti_episode": 1
  },
  "ready_for_recall": true
}
```

## When to Consolidate

- End of session (explicit "save session" or natural end)
- Before long context switches
- After completing significant milestones
- When switching between major tasks

## Integration

This workflow is called automatically by the session manager at appropriate points, but can also be invoked explicitly by the user.
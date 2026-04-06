---
name: recall-project-context
description: Get project context from unified memory. Use when user asks what is the current project state, what are we building, or what is the project about.
argument-hint: "[project-name or omit for current]"
---

# Recall Project Context Workflow

## Purpose

Retrieve the current project context from memory, including:
- Project description and goals
- Current phase/milestone
- Key stakeholders and preferences
- Recent decisions and direction

## Workflow Steps

### Step 1: Identify Project

Determine which project context to retrieve:
- If project name provided: use that
- If no name: read from `.context/project-manifest.json` for current project

### Step 2: Query Memory

Search for project context:

```python
# Search memory MCP for project entities
from src.memory_search import search_project_context

# Also check Graphiti for project episodes
from src.graphiti_memory import get_project_episodes

# Check opencode.db for recent project discussions
from src.unified_memory_mcp import search_opencode
```

### Step 3: Synthesize

Combine into project context summary:

```markdown
## Project: {name}

**Description**: {from memory MCP}
**Phase**: {from project-manifest}
**Current Focus**: {from recent sessions}

### Key Decisions
- {decision 1}
- {decision 2}

### Stakeholders
- {stakeholder info}

### Next Steps
- {from session state}
```

## Output

Returns project context ready for injection into new session.

```json
{
  "status": "success",
  "project": "{name}",
  "context": {
    "description": "...",
    "phase": "...",
    "decisions": [...],
    "stakeholders": {...},
    "next_steps": [...]
  }
}
```
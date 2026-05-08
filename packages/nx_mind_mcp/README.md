# nx-mind-mcp

MCP Tool Server for MIND state management and session continuity in N-Xyme_MIND.

## Overview

Manages project progress, active workflows, session history, and cross-session continuity. Acts as the persistent "brain" layer for N-Xyme_MIND.

## Tools

| Tool | Description |
|------|-------------|
| `get_mind_state` | Returns current MIND state (project, phase, active tasks) |
| `update_mind_state` | Updates MIND state with new information |
| `get_session_history` | Returns history of past sessions with summaries |
| `get_active_workflow` | Returns currently active BMAD workflow and step |
| `set_context` | Sets project context for current session |
| `sync_to_memory` | Syncs MIND state to memory MCP (entities/relations) |
| `get_project_manifest` | Returns project metadata and progress |

## Installation

```bash
cd packages/nx-mind-mcp
pip install -e .
```

## Usage

### CLI

```bash
# Run with stdio transport (default)
nx-mind-mcp

# Run with SSE transport
nx-mind-mcp --sse --port 8767
```

### Python

```python
from nx_mind_mcp import mcp

# Run the server
mcp.run(transport="stdio")
```

## Configuration

Environment variables:
- `NX_MIND_ROOT`: Project root path (default: `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND`)

## Data Storage

State files stored in `.context/`:
- `mind-state.json` - Current MIND state
- `project-manifest.json` - Project metadata
- `session-history.json` - Session history

## Architecture

```
nx-mind-mcp/
├── nx_mind_mcp/
│   ├── __init__.py    # MCP server with 7 tools
│   └── __main__.py    # Entry point
└── pyproject.toml
```

## Integration

- Uses filesystem for state persistence
- Compatible with memory MCP for entity sync
- References `_bmad/catalyst/` for workflow detection

# Agent Framework & Permissions

This package provides the core agent framework and permission system for N-Xyme CATALYST.

## Features

- Agent configuration management (YAML)
- Granular permission system with roles and rules
- BMAD hybrid workflow for task routing
- Agent communication patterns (direct, blackboard, pub/sub)
- Skill definitions for all agents

## Configuration

Agent configurations are stored in `configs/opencode/agents/`. Each agent has a YAML file defining its capabilities, permissions, and skills.

## Permission System

The permission system is defined in `configs/opencode/permissions.json`. It includes:

- **Roles**: user, developer, admin
- **Rules**: Pattern-based allow/deny rules
- **Defaults**: Default role and action

## BMAD Workflow

The BMAD (Bounded Model-Agentic Design) hybrid workflow selects agents based on task type and capability matching.

## Communication Patterns

- **Direct Messaging**: Agent-to-agent communication
- **Blackboard**: Shared memory via Graphiti (Agent 2)
- **Event Pub/Sub**: Event bus for asynchronous communication

## Usage

The framework is used by OpenCode to route tasks, enforce permissions, and coordinate agents.

## API

### Agent Configuration

```python
from agent_framework import AgentConfig

config = AgentConfig.load("configs/opencode/agents/planner.yaml")
```

### Permission Check

```python
from agent_framework import PermissionManager

pm = PermissionManager("configs/opencode/permissions.json")
allowed = pm.check_permission("user", "file:write")
```

### Task Routing

```python
from agent_framework import Router

router = Router()
agent = router.route_task("write a test")
```

### HTTP API

Run the agent framework service:

```bash
poetry run uvicorn src.service:app --host 0.0.0.0 --port 8002
```

Endpoints:
- `GET /health` - Health check
- `GET /agents` - List all agents
- `GET /agents/{name}` - Get specific agent
- `POST /route` - Route a task to an agent
- `POST /permissions/check` - Check permission for a role
- `POST /permissions/evaluate` - Evaluate command against rules

See `interfaces/agent-framework-api.yaml` for full OpenAPI spec.

## Development

1. Install dependencies: `poetry install`
2. Run tests: `poetry run pytest`
3. Build package: `poetry build`

## License

MIT
# Core Infrastructure & The Catalyst Engine

The core infrastructure package provides The Catalyst - the central orchestration engine for N-Xyme Catalyst.

## Overview

The Catalyst is the single entry point for all system operations, managing the lifecycle and coordination of all subsystems:

- **Agent Framework**: Task routing and agent coordination
- **MCP Servers**: Tool registry and server lifecycle
- **Memory System**: Graphiti/Neo4j integration
- **Security Layer**: Command validation and permissions
- **Auto-Capture**: Voice, screen, and clipboard monitoring
- **Performance**: GPU optimization and resource management
- **Monitoring**: Health checks and system metrics

## Directory Structure

```
core-infrastructure/
├── src/
│   ├── __init__.py           # Package exports
│   ├── catalyst.py           # Main Catalyst engine
│   ├── config_manager.py     # Configuration loading
│   └── service_registry.py   # Service discovery
├── pyproject.toml            # Package configuration
└── README.md                 # This file
```

## Installation

```bash
cd packages/core-infrastructure
poetry install
```

## Quick Start

### Python API

```python
from src.catalyst import Catalyst, create_catalyst

# Create and initialize
catalyst = await create_catalyst("configs")

# Check health
health = await catalyst.health_check()
print(f"State: {health.state.value}")

# Route a task
result = await catalyst.route_task("Write a Python function")
print(f"Routed to: {result['agent']}")

# Shutdown
await catalyst.shutdown()
```

### CLI

```bash
# Interactive mode
python scripts/the-catalyst.py

# Health check
python scripts/the-catalyst.py --health

# List agents
python scripts/the-catalyst.py --agents

# Verbose mode
python scripts/the-catalyst.py --verbose
```

## Features

### System Lifecycle Management

The Catalyst manages the complete system lifecycle:

1. **Initialization**: Loads configuration, starts components in order
2. **Running**: Coordinates tasks, monitors health
3. **Shutdown**: Graceful cleanup in reverse order

### Task Routing

Routes tasks to the most appropriate agent based on:
- Task description keywords
- Agent capabilities and skills
- Context-aware matching

### Health Monitoring

Continuous health monitoring of all components:
- Component status tracking
- Automatic degradation detection
- Event-driven notifications

### Event System

Extensible event system for:
- System state changes
- Component status updates
- Custom event handlers

## API Reference

### Catalyst Class

```python
class Catalyst:
    # Properties
    state: SystemState          # Current system state
    is_running: bool            # Whether system is running
    uptime: float               # Uptime in seconds

    # Methods
    async initialize()          # Initialize all components
    async shutdown()            # Graceful shutdown
    async health_check()        # Get system health
    async route_task(task)      # Route task to agent
    async get_agents()          # List all agents
    async check_permission()    # Check permissions
    get_component(name)         # Get component by name
    list_components()           # List all components
    on(event, handler)          # Register event handler
    off(event, handler)         # Unregister event handler
```

### System States

| State | Description |
|-------|-------------|
| `UNINITIALIZED` | Initial state |
| `INITIALIZING` | Starting up |
| `RUNNING` | Operational |
| `DEGRADED` | Partially functional |
| `SHUTTING_DOWN` | Shutting down |
| `STOPPED` | Fully stopped |
| `ERROR` | Critical error |

### Component Health

| Status | Description |
|--------|-------------|
| `HEALTHY` | Fully operational |
| `DEGRADED` | Partially functional |
| `UNHEALTHY` | Not working |
| `OFFLINE` | Not running |
| `UNKNOWN` | Status unknown |

## Configuration

The Catalyst loads configuration from `configs/`:

```
configs/
├── opencode/
│   ├── agents/          # Agent YAML definitions
│   ├── opencode.json    # Main configuration
│   └── permissions.json # Permission rules
```

## Examples

See `examples/` directory for usage examples:

- `quick_start.py` - Minimal usage example
- `catalyst_usage.py` - Comprehensive examples
- `integration_example.py` - Integration patterns

## Documentation

Full documentation: `docs/THE_CATALYST.md`

## Dependencies

- Python 3.10+
- pyyaml
- pydantic

## License

MIT License

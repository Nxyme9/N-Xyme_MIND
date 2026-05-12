# Orchestration Layer

## Overview

The Orchestration Layer is the nerve center of N-Xyme MIND. It coordinates agent lifecycle, task execution, session management, tool registry, triggers, and BMAD workflows. It implements adaptive agent orchestration with FLOW/FRICTION state detection.

## Public API

```python
# Spawn agent tasks
task_id = spawn(agent="hephaestus", task="Fix the bug", context={})

# Get task status
status = task_status(task_id)

# List available tools
tools = tools_list()
```

## Architecture

### Core Modules

| Module | Purpose | Key Classes | Key Functions |
|--------|---------|-------------|---------------|
| agent_loop.py | Core execution engine | AgentLoop, ExitReason, LoopStep | run(), execute_tools() |
| catalyst.py | Master orchestration | CatalystOrchestrator, UserStateDetector, BMADWorkflowExecutor | orchestrate(), detect_state() |
| triggers/engine.py | Event trigger system | TriggerEngine, Trigger | add(), evaluate(), get_stats() |
| bmad/ | BMAD workflow execution | BMADWorkflowExecutor, PhaseGate | execute(), validate() |
| tasks/ | Task dispatch and lifecycle | TaskDispatcher, TaskRouter | dispatch(), route() |
| sessions/ | Session management | SessionManager | create(), resume(), archive() |
| tools/ | Tool registry and search | ToolRegistry | register(), search(), get_tools() |
| governance/ | Permission and policy | PermissionManager, PolicyEngine | check_permission(), enforce() |

### Agent Framework

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| agent-framework/src/service.py | Agent service | AgentService |
| agent-framework/src/router.py | Agent routing | AgentRouter |
| agent-framework/src/tool_registry.py | Tool registry | ToolRegistry |
| agent-framework/src/permission_manager.py | Permission management | PermissionManager |
| agent-framework/src/agent_config.py | Agent configuration | AgentConfig |
| agent-framework/src/cancellation.py | Task cancellation | CancellationToken |

## Components

### Agent Loop (agent_loop.py)

- **Purpose**: Core execution engine implementing 10-step iteration pattern from Claude Code
- **Key Methods**:
  - `run()`: Execute agent loop with user message, system prompt, tools
  - `execute_tools()`: Execute detected tool calls during streaming
  - `compact_context()`: Reactive context compaction
- **States**: EXIT_REASON (normal_completion, token_budget_exceeded, max_iterations, error, tool_limit)
- **Dependencies**: frankenstein_engine, agent_context_middleware

### Catalyst Orchestrator (catalyst.py)

- **Purpose**: Adaptive agent orchestration with BMAD workflow execution
- **Key Classes**:
  - `UserStateDetector`: Detects FLOW vs FRICTION from user signals
    - FLOW: reaction_time < 3000ms, message_length < 500, no error markers
    - FRICTION: reaction_time > 8000ms, message_length > 1000
  - `BMADWorkflowExecutor`: Executes BMAD workflows from _bmad/ registry
  - `FractalDelegation`: Recursive agent spawning with depth tracking
- **States**: FLOW, FRICTION, ADAPT
- **Dependencies**: pathlib, asyncio, BMAD workflows

### Trigger Engine (triggers/engine.py)

- **Purpose**: Event trigger system for automated responses
- **Key Functions**:
  - `clean_stale_sessions()`: Remove stale session files older than max_age_days
  - `clear_db_lock()`: Release database locks
- **Configuration**: triggers.json defines all trigger rules
- **Categories**: gpu, pm2, service, database, sessions, rate_limit, config, graphiti, ollama, system, velocity, consciousness, memory

### Self-Healer (self_healer.py)

- **Purpose**: Automatic service recovery and fallback switching
- **Key Methods**:
  - `_restart_service()`: Restart PM2-managed service
  - `_notify_failure()`: Send notification to event bus
  - `_switch_fallback()`: Disable service and move to quarantine

## Relationships

- **Depends on**: local_llm (for inference), memory_core (for context), learning_engine (for routing)
- **Used by**: OpenCode frontend, MCP servers, catalyst orchestrator

## Notes

- Agent loop implements 10-step iteration pattern (Context → Budget → API → Stream → Error → Hooks → Budget → Tools → Attach → Loop)
- Circuit breakers track: hasAttemptedReactiveCompact, token budget
- Tool calls detected during streaming (not just stop_reason)
- BMAD workflows located in _bmad/ directory
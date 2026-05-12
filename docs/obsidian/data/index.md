# Data Layer

## Overview

The Data Layer contains data models, schemas, and configurations used across the N-Xyme MIND system. While the main `__init__.py` is currently empty, the system defines data models throughout other packages.

## Data Models by Layer

### Orchestration Models (packages/orchestration/models/)

| Model | Purpose | Key Classes |
|-------|---------|-------------|
| fallback.py | Fallback configuration | FallbackConfig, FallbackChain |

### Intelligence Schemas (packages/intelligence/schemas.py)

| Schema | Purpose |
|--------|---------|
| RoutingDecision | Task routing result with agent, confidence, strategy |
| CircuitBreakerConfig | Circuit breaker configuration |
| TaskContext | Task execution context |
| AgentWeights | Per-agent routing weights |

### Memory Core Schemas (packages/memory_core/schemas.py)

| Schema | Purpose |
|--------|---------|
| MemoryRecord | Core memory storage format |
| SessionContext | Per-session memory context |
| RetrievalResult | Search result format |

### Learning Engine Models (packages/learning_engine/models/)

| Model | Purpose | Key Classes |
|-------|---------|-------------|
| QLearningTable | Q-value storage | - |
| BanditArm | Bandit selection state | - |
| RoutingWeights | Agent performance weights | - |
| ABTestConfig | A/B test configuration | ABTest, TestVariant |

### Infrastructure Data

| Model | Purpose | Classes |
|-------|---------|---------|
| ModelProvider | Provider definition | CostTracker, MODEL_PRICING |
| UsageRecord | API usage tracking | UsageRecord |
| MetricsData | Metrics storage | MetricsStore |

## Configuration Files

### Root Configuration

| File | Purpose |
|------|---------|
| opencode.json | OpenCode configuration (agents, MCPs, providers) |
| oh-my-openagent.json | Agent definitions, categories, experimental features |
| triggers.json | Trigger action registry and trigger definitions |
| AGENTS.md | Workspace rules and agent instructions |

### Provider Configuration (in opencode.json)

```json
{
  "provider": {
    "openrouter": { "models": {...} },
    "xai": { "models": {...} },
    "deepseek": { "models": {...} },
    "ollama": { "models": {...} },
    "lmstudio": { "models": {...} },
    "gguf": { "models": {...} },
    "opencode": { "models": {...} }
  }
}
```

### MCP Servers Configuration

| MCP | Module | Purpose |
|-----|--------|---------|
| nx-mind | nx_mind_mcp | Project state management |
| unified-memory | memory_core.mcp_server | Memory operations |
| learning-engine | learning_engine.mcp_server | Learning system |
| intelligence | intelligence.mcp_server | Routing intelligence |
| session-pool | session-pool-mcp | Session management |
| quality-gates | quality-gates-mcp | Code quality |
| nx-context | nx_context_mcp | Context management |
| trigger-guardian | trigger_guardian_mcp | Trigger management |
| orchestration | orchestration.mcp_server | Orchestration |
| catalyst | catalyst_mcp | BMAD workflows |
| notion | @notionhq/notion-mcp-server | Notion integration |
| obsidian | obsidian_mcp_fixed | Obsidian integration |
| github | @beautyfree/modelcontextprotocol-server-github | GitHub integration |

## Agent Definitions (from oh-my-openagent.json)

| Agent | Model | Variant | Mode | Description |
|-------|-------|---------|------|-------------|
| sisyphus | minimax-m2.5-free | high | primary | Primary orchestrator |
| catalyst | minimax-m2.5-free | high | all | Master orchestrator (FLOW/FRICTION) |
| prometheus | minimax-m2.5-free | high | all | Strategic planning |
| oracle | minimax-m2.5-free | high | all | Architecture review |
| metis | minimax-m2.5-free | high | all | Gap analysis |
| momus | minimax-m2.5-free | high | all | Adversarial review |
| hephaestus | minimax-m2.5-free | medium | all | Implementation |
| atlas | minimax-m2.5-free | medium | all | Plan executor |
| explore | minimax-m2.5-free | - | subagent | Codebase search |
| librarian | minimax-m2.5-free | - | subagent | External research |
| sisyphus-junior | minimax-m2.5-free | - | subagent | Light tasks |
| multimodal-looker | minimax-m2.5-free | medium | all | Vision agent |

## Category Definitions

| Category | Model | Variant | Purpose |
|----------|-------|---------|---------|
| visual-engineering | minimax-m2.5-free | medium | UI/UX work |
| ultrabrain | minimax-m2.5-free | high | Complex logic |
| deep | minimax-m2.5-free | medium | Autonomous research |
| artistry | minimax-m2.5-free | high | Creative problem-solving |
| quick | minimax-m2.5-free | - | Trivial tasks |
| unspecified-low | minimax-m2.5-free | - | Low-effort tasks |
| unspecified-high | minimax-m2.5-free | medium | High-effort tasks |
| routing | minimax-m2.5-free | - | Delegation only |
| writing | minimax-m2.5-free | high | Documentation |

## Notes

- The data layer is distributed across packages
- Core models defined in intelligence (routing, circuit breakers)
- Memory models in memory_core
- Learning models in learning_engine
- Configuration centralized in opencode.json and oh-my-openagent.json
- Triggers defined in triggers.json
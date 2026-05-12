# Intelligence Layer

## Overview

The Intelligence Layer provides task routing and delegation intelligence. It orchestrates multiple routing strategies with fallback chains, implements circuit breaker patterns, and provides adaptive routing with self-learning capabilities.

## Public API

```python
# Route task to optimal agent
decision = await route(task_description="Fix the bug")

# Score task complexity
score = score_complexity(task_description)

# Get available agents
agents = available_agents()
```

## Architecture

### Core Modules

| Module | Purpose | Key Classes | Key Functions |
|--------|---------|-------------|---------------|
| router/unified.py | Unified routing orchestration | UnifiedDelegationRouter, RoutingDecision | route_task(), _route_with_fallback() |
| circuit_breaker.py | Fault tolerance pattern | CircuitBreaker, CircuitState, CircuitBreakerConfig | record_success(), record_failure(), allow_request() |
| fallback.py | Fallback chain management | FallbackChain, get_fallback_chain | get_alternatives() |
| router/keyword.py | Keyword-based routing | score_complexity() | - |
| router/memory.py | Memory-augmented routing | get_memory_router() | - |
| router/trigger.py | Trigger-based routing | get_trigger_router() | - |
| router/ml.py | ML-based predictions | get_ml_router() | - |
| router/semantic_classifier.py | Semantic task classifier | SemanticClassifier | classify() |

### Advanced Components

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| scoring/dynamic.py | Dynamic scoring | DynamicScorer |
| scoring/token_estimator.py | Token estimation | TokenEstimator |
| review/triage.py | Review triage | ReviewTriage |
| review/security_gate.py | Security gate | SecurityGate |
| delegation/decomposer.py | Task decomposition | TaskDecomposer |
| middleware/sandbox.py | Sandbox execution | SandboxMiddleware |

## Components

### Unified Delegation Router (router/unified.py)

- **Purpose**: Orchestrates all routing strategies with proper fallback chains
- **Routing Strategies** (in order):
  1. Trigger-based routing (explicit command patterns)
  2. Memory-augmented routing (past similar tasks)
  3. ML-based predictions (learned patterns)
  4. Skill-based agent matching
  5. Learning-based optimization (Q-learning + Bandits)
  6. Keyword fallback (L1-L5 complexity scoring)
- **Key Methods**:
  - `route_task()`: Main routing entry point
  - `_route_with_fallback()`: Try strategies in order with fallback
- **Dependencies**: router components, learning_engine

### Circuit Breaker (circuit_breaker.py)

- **Purpose**: Fault tolerance pattern for model failure detection
- **State Machine**: CLOSED → OPEN → HALF_OPEN → CLOSED
- **Key Methods**:
  - `record_success()`: Reset failure counter, transition to CLOSED
  - `record_failure()`: Increment failure counter, transition to OPEN
  - `allow_request()`: Check if request allowed in current state
- **Configuration**:
  - `failure_threshold`: 3 (default)
  - `recovery_timeout_seconds`: 120 (default)
  - `half_open_max_requests`: 1 (default)

### Fallback Chain (fallback.py)

- **Purpose**: Manage fallback chains when primary agent fails
- **Key Methods**:
  - `get_alternatives()`: Get fallback agents for a failed agent

### Complexity Scoring (router/keyword.py)

- **Purpose**: L1-L5 complexity scoring for task routing
- **Levels**:
  - L1: Trivial (typo, version bump)
  - L2: Simple (single-file fix)
  - L3: Moderate (multi-file change)
  - L4: Complex (new feature)
  - L5: Architect (system design)

## Relationships

- **Depends on**: learning_engine (routing optimization), memory_core (memory routing)
- **Used by**: orchestration layer (for agent selection), MCP servers

## Notes

- RoutingDecision includes: task_description, level, agent, confidence, strategy_used, reason, alternatives, latency_ms, subtasks
- Integrated with Q-Learning + Bandits from learning_engine
- Semantic classifier provides Strategy 2.5 for nuanced task understanding
- Health-aware routing prevents routing to unhealthy agents
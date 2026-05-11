# Router Precedence Architecture

> How routing decisions flow through the N-Xyme_MIND system — which router runs first, which runs last, and who wins when they disagree.

**Last updated:** Sprint 3  
**Status:** Implemented  

---

## Overview

The system has **three distinct routing layers** that serve different purposes. They are **not** competing — they operate at different levels of the stack. This document maps how they compose.

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Tool Routing  (orchestration/two_stage_router)│
│  "Which tool executes this task?"                        │
└──────────────────────────┬──────────────────────────────┘
                           │ RouteResult.route_path
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Agent Routing  (nx_routing.py)                 │
│  "Which agent handles this task?"                       │
└──────────────────────────┬──────────────────────────────┘
                           │ RoutingResult.agent
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Model Routing  (intelligent_router_mcp)        │
│  "Which model does the agent use?"                      │
└─────────────────────────────────────────────────────────┘
```

---

## Layer 1: TwoStageRouter — Tool Routing

**File:** `packages/orchestration/two_stage_router.py`  
**Purpose:** Classify task complexity and select execution path for tool calling.  
**Entry point:** `router.route(user_message)` → `RouteResult`

### Decision Logic

```
score_complexity(task_description)
  │
  ├─── L1 (simple) + clear tool match ──► route_path = "direct"
  │                                      (fast path, local)
  │
  ├─── L2-L3 (moderate) + ambiguous ────► route_path = "rosetta_only"
  │                                      (proxy through Rosetta)
  │
  └─── L4-L5 (complex) ─────────────────► route_path = "full"
                                       (big model → Rosetta → Tool)
```

### Route Path Meanings

| Path | When Used | Latency Target | Example |
|------|-----------|---------------|---------|
| `direct` | Simple task, clear tool match | <500ms | "Read file config.json" |
| `rosetta_only` | Moderate task, ambiguous intent | <2s | "Update the UI layout" |
| `full` | Complex task, multi-step reasoning | <10s | "Implement auth middleware" |

### L1 Cache

TwoStageRouter uses an **L1 cache** (in-memory dict, max 200 entries) keyed on:
- `hash(task_description + str(complexity))`

Cache hit rate is tracked via `_cache_hits` / `_cache_misses`. No TTL — cache is cleared on process restart.

### Who calls TwoStageRouter?

- `packages/intelligence/middleware/interceptor.py`
- `packages/intelligence/router/unified.py`
- `packages/platform_layer/scripts/model/model-router.py`
- `packages/orchestration/spawn.py` (handoff pipeline)
- `packages/orchestration/context_loader.py`

---

## Layer 2: nx_routing — Agent Routing

**File:** `packages/nx_routing.py`  
**Purpose:** Select which AI agent handles the task (Sisyphus, Oracle, Explore, Librarian, etc.).  
**Entry point:** `route_task(task_description, session_id=None)` → `RoutingResult`

### Decision Logic

```
route_task(task_description, session_id)
  │
  ├─── Session pinned? ──────────────────► return pinned agent (confidence=1.0)
  │                                      (session pin via pin_routing())
  │
  └─── No pin ───────────────────────────► score_complexity(task_description)
                                          │
                                          ▼
                                     _route_with_qlearning()
                                          │
                                          ├─── Q-Learning weights → agent selection
                                          │    (Q-values per (task_type, agent))
                                          │
                                          └─── Fallback: heuristic rules if <50 decisions
                                               (cold start guard)
```

### Complexity Levels (L1-L5)

| Level | Description | Typical Tasks |
|-------|-------------|---------------|
| L1 | Trivial, single step | "Read file X", "Show git status" |
| L2 | Simple with context | "What does this function do?" |
| L3 | Moderate complexity | "Refactor this module", "Add tests" |
| L4 | High complexity | "Implement auth system", "Rebase feature branch" |
| L5 | Expert only | "Redesign architecture", "Security audit" |

### Q-Learning Integration

- Uses `QLearningEngine` from `packages/learning_engine/`
- Weights persisted to `data/qlearning/weights.json` on module load
- Cold start: first 50 decisions use heuristic fallback
- Outcome logging via `OutcomeLogger` feeds back into Q-values
- Confidence scores reflect Q-value certainty

### Session Pinning

Once an agent is pinned to a session via `pin_routing()`, **all** subsequent calls to `route_task()` for that session return the pinned agent with `confidence=1.0`. Unpin via `unpin_routing()`.

### Who calls nx_routing?

- `packages/nx_delegate/nx_delegate.py` — task delegation
- `packages/session-pool-mcp/mcp_server.py` — pool routing
- `packages/learning_engine/mcp_server.py` — learning engine
- `packages/brain_mcp/` — via `learning.*` namespace tools

---

## Layer 3: AdaptiveRouter — Learning-Enhanced Agent Routing

**File:** `packages/learning_engine/routing/adaptive_router.py`  
**Purpose:** Wrap MemoryRouter with Q-Learning feedback loop for real learning.  
**Entry point:** `router.route(task_description)` → `dict[str, Any]`

### Decision Logic

```
AdaptiveRouter.route(task_description)
  │
  ├─── MemoryRouter.search() ────────────► baseline similarity search
  │                                      (finds relevant past routing decisions)
  │
  ├─── Q-Learning selection ─────────────► agent + level + confidence
  │                                      (learns from past outcomes)
  │
  └─── log_outcome() ───────────────────► records decision for feedback
                                          (OutcomeLogger → Q-Learning update)
```

### Relationship to nx_routing

AdaptiveRouter is the **backend engine** that nx_routing's `_route_with_qlearning()` delegates to. The `QLearningEngine` is shared:

```
nx_routing._route_with_qlearning()
  └── AdaptiveRouter.route()
        ├── MemoryRouter (similarity)
        ├── QLearningEngine (Q-values)
        └── OutcomeLogger (feedback)
```

### Who calls AdaptiveRouter?

- Primarily nx_routing internally
- `packages/learning_engine/memory_bridge.py` — bridge between memory and learning

---

## Precedence Rules (When Layers Disagree)

Since each layer operates at a different level, **conflict is rare**. But when it occurs:

| Conflict | Resolution |
|----------|------------|
| TwoStageRouter says "direct", AdaptiveRouter says "full" | TwoStageRouter wins (tool path selection is faster/cheaper) |
| Session pin overrides AdaptiveRouter | Session pin wins (explicit user preference) |
| TwoStageRouter L1 cache hit, AdaptiveRouter disagrees | L1 cache wins (performance) |

The system does **not** reconcile disagreements — each layer trusts the layer above it has already made the right decision.

---

## Configuration

### Environment Variables

| Variable | Default | Effect |
|----------|---------|--------|
| `LOCAL_ROUTING_ENABLED` | `true` | Enable local routing (vs cloud-only) |
| `LOCAL_QUALITY_THRESHOLD` | `0.7` | Minimum quality for local execution |
| `LOCAL_TIMEOUT_SECONDS` | `30` | Timeout for local routing decisions |
| `CLOUD_ESCALATION_MODE` | `auto` | When to escalate to cloud (`auto`, `never`, `always`) |
| `ROUTING_METRICS_ENABLED` | `true` | Emit routing metrics |
| `LOCAL_MODEL_POOL` | `llama3.2:3b,qwen2.5-coder:7b` | Available local models |

### Cache Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| TwoStageRouter L1 cache max | 200 entries | In-memory, process-scoped |
| TwoStageRouter cache key | `hash(task + complexity)` | No TTL, cleared on restart |
| nx_routing Q-Learning | Persistent to `data/qlearning/weights.json` | Loaded on module init |

---

## File Inventory

| File | Role | Exports |
|------|------|---------|
| `packages/orchestration/two_stage_router.py` | Tool routing | `TwoStageRouter`, `RouteResult`, `route()` |
| `packages/nx_routing.py` | Agent routing (consolidation layer) | `route_task()`, `score_complexity()`, `pin_routing()` |
| `packages/learning_engine/routing/adaptive_router.py` | Learning-enhanced routing | `AdaptiveRouter` |
| `packages/learning_engine/routing/q_learning.py` | Q-Learning engine | `QLearningEngine` |
| `packages/intelligence/mcp_server.py` | Intelligence MCP | `score_complexity()` as MCP tool |
| `packages/intelligence/router/unified.py` | Unified routing facade | Calls TwoStageRouter + nx_routing |
| `packages/orchestration/spawn.py` | Handoff pipeline | Calls routing, spawns agents |
| `packages/nx_delegate/nx_delegate.py` | Task delegation | Calls nx_routing |
| `packages/session-pool-mcp/mcp_server.py` | Session pool | Calls routing for warm pool |
| `packages/learning_engine/mcp_server.py` | Learning MCP | `route_task()` as MCP tool |
| `packages/brain_mcp/` | Central MCP | Exposes routing via `learning.*` tools |

---

## Known Limitations

1. **Cold start bias**: Until Q-Learning has 50+ decisions, routing falls back to heuristics that may not be optimal for niche task types.
2. **No cross-layer conflict resolution**: If TwoStageRouter and AdaptiveRouter disagree, no reconciliation happens — last-mile trust is assumed.
3. **Session pinning is sticky**: Once pinned, a session never changes agents until explicitly unpinned, even if task complexity changes significantly.
4. **L1 cache invalidation**: TwoStageRouter L1 cache has no TTL — stale decisions can persist until process restart.
5. **intelligent_router_mcp not wired**: `packages/intelligent_router_mcp/` exists but is not connected to the routing stack. Model-level routing decision is TODO (S-304).

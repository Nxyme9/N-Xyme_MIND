# Phase 18: Intelligence Component Integration — Masterplan

> **Date:** 2026-04-07
> **Effort:** ~14 hours across 4 waves
> **Priority:** Critical — highest impact remaining work

---

## Current State Assessment

### What's Already Built (Code Exists)

The `packages/intelligence/` directory contains **36 files/subdirectories** with a sophisticated architecture:

| Component | File | Status |
|-----------|------|--------|
| Unified Router | `router/unified.py` | ✅ Built, lazy-loads all 8 advanced components |
| Delegation Interceptor | `middleware/interceptor.py` | ✅ Built with retry, memory bridge, advanced learning |
| ML Router | `router/ml.py` | ✅ Code exists |
| Skill Registry | `skill_registry.py` | ✅ Code exists |
| Health Monitor | `health_monitor.py` | ✅ Code exists |
| Context Sharing | `delegation/context_sharing.py` | ✅ Code exists |
| Task Decomposer | `delegation/decomposer.py` | ✅ Code exists |
| Prompt Templates | `templates/prompts.py` | ✅ Code exists |
| A/B Testing | `packages/learning_engine/routing/ab_testing.py` | ✅ Code exists |
| Agent Communication | `delegation/communication.py` | ✅ Code exists |

### The Real Problem

The components ARE wired into `UnifiedDelegationRouter` and `DelegationInterceptor` — but **neither is connected to the live MCP pipeline**. The intelligence MCP server (`packages/intelligence/mcp_server.py`) exposes `route`, `score_complexity`, and `available_agents` — but these call the old simple functions, NOT the unified router pipeline.

**Additionally:** 16 orphaned files exist that are never imported anywhere.

### Orphaned Files (16 total)

| File | Likely Purpose | Action |
|------|---------------|--------|
| `agent_optimizer.py` | Agent performance optimization | Archive → integrate if useful |
| `benchmark.py` | Routing benchmark | Archive |
| `budget_tracker.py` | Token cost tracking | Archive → integrate into infrastructure |
| `code_quality_tracker.py` | Code quality metrics | Archive → integrate into review/ |
| `context_compact.py` | Context compression | Archive |
| `delegation_logger.py` | Old delegation logger (dup of delegation/logger.py) | DELETE — duplicate |
| `load_balancer.py` | Load balancing | Archive |
| `permission_engine.py` | Permission checks (dup of orchestration/permissions.py) | DELETE — duplicate |
| `request_recorder.py` | Request recording | Archive |
| `result_checker.py` | Result validation | Archive → integrate into review/ |
| `review/security_gate.py` | Security gate | KEEP — used by platform_layer |
| `review/quality.py` | Code quality | KEEP — used by platform_layer |
| `scoring/token_estimator.py` | Token estimation | Archive → integrate into scoring/ |
| `tool_contract.py` | Tool contracts | Archive |
| `context_manager.py` | Context management | Archive |
| `delegation_learner.py` | Delegation learning | Archive → merge with delegation_learner |

### Duplicate Functionality

| Duplication | Files | Action |
|-------------|-------|--------|
| Complexity scoring | `scoring/dynamic.py` vs `router/keyword.py` vs `scoring/token_estimator.py` | Consolidate to single `scoring/complexity.py` |
| Delegation logging | `delegation_logger.py` vs `delegation/logger.py` | Delete `delegation_logger.py` |
| Permission engine | `permission_engine.py` vs `orchestration/governance/permissions.py` | Delete `permission_engine.py` |

---

## Architecture: Target Pipeline

```
User Request (via OpenCode)
    │
    ▼
┌─────────────────────────────────────────────┐
│  DelegationInterceptor (FastMCP Middleware) │
│  - Auto-intercepts task() calls             │
│  - Pre-reads memory context                 │
│  - Routes via UnifiedDelegationRouter       │
│  - Retries on failure with fallback agent   │
│  - Post-writes outcome to memory            │
└────────────────────────┬────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────┐
│  UnifiedDelegationRouter (11 strategies)    │
│  1. Health Check (skip unhealthy agents)    │
│  2. Trigger Match (instant, 24 patterns)    │
│  3. ML Prediction (trained model)           │
│  4. Memory Augmentation (past similar tasks)│
│  5. Skill Matching (agent capabilities)     │
│  6. Context Loading (shared session state)  │
│  7. Task Decomposition (complex → subtasks) │
│  8. A/B Test Selection (strategy variant)   │
│  9. Q-Learning (reinforcement weights)      │
│  10. Bandit Selection (explore/exploit)     │
│  11. Keyword Fallback (L1-L5 scoring)       │
│                                             │
│  → Prompt Templates (render delegation)     │
│  → Agent Communication (multi-agent tasks)  │
└────────────────────────┬────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────┐
│  MCP Server (exposes to OpenCode agents)    │
│  - route_task(task) → RoutingDecision       │
│  - score_complexity(task) → ScoreResult     │
│  - available_agents() → list                │
│  - get_routing_recommendations(task) → list │
│  - retrain() → status                      │
│  - get_learning_stats() → dict             │
│  - record_delegation_outcome(...) → status  │
│  - get_skill_status(skill) → dict           │
│  - evolve_prompt(prompt, context) → str     │
│  - get_learning_patterns(query) → list      │
└─────────────────────────────────────────────┘
```

---

## Sub-Tasks with Optimal Delegation

### Wave 1: Audit + Classification (Sequential, 2hr)

| # | Task | Effort | Delegation | Agent | Why |
|---|------|--------|------------|-------|-----|
| 18.1 | Audit all 16 orphaned files — classify each as KEEP/DELETE/ARCHIVE | 1hr | `subagent_type="explore"` | explore | Read-only codebase analysis |
| 18.1b | Audit all import chains — verify which components actually load | 1hr | `subagent_type="explore"` | explore | Cross-file dependency tracing |

**Prompt for 18.1:**
```
TASK: Audit 16 orphaned files in packages/intelligence/ and classify each as KEEP, DELETE, or ARCHIVE.

Files to audit:
agent_optimizer.py, benchmark.py, budget_tracker.py, code_quality_tracker.py,
context_compact.py, delegation_logger.py, load_balancer.py, permission_engine.py,
request_recorder.py, result_checker.py, scoring/token_estimator.py, tool_contract.py,
context_manager.py, delegation_learner.py

For EACH file:
1. Read the file fully
2. Search for any imports of it across the entire codebase (grep -r "from.*<module>" and "import.*<module>")
3. Check if it has duplicate functionality elsewhere
4. Classify: KEEP (actively used), DELETE (duplicate/dead code), ARCHIVE (useful but not wired)
5. If ARCHIVE: note what it does and where it could be integrated later

Return a table: File | Classification | Reason | Referenced By | Duplicates
```

**Prompt for 18.1b:**
```
TASK: Trace import chains for all 8 "advanced" intelligence components to verify they actually load.

Components to trace:
1. router/ml.py (ML Router)
2. skill_registry.py (Skill Registry)
3. health_monitor.py (Health Monitor)
4. delegation/context_sharing.py (Context Sharing)
5. delegation/decomposer.py (Task Decomposer)
6. templates/prompts.py (Prompt Templates)
7. packages/learning_engine/routing/ab_testing.py (A/B Testing)
8. delegation/communication.py (Agent Communication)

For EACH component:
1. Read the file — does it have valid code or is it a stub?
2. Check if its get_*() factory function works (trace all imports)
3. Check if UnifiedDelegationRouter actually calls it (read router/unified.py lines 130-200)
4. Check if any test exists for it
5. Rate: WORKING (loads clean), BROKEN (import errors), STUB (empty/placeholder)

Return: Component | Status | Import Chain | Used By | Tests Exist
```

### Wave 2: Critical Wiring (Parallel x4, 6hr)

| # | Task | Effort | Delegation | Agent | Depends On |
|---|------|--------|------------|-------|------------|
| 18.2 | Wire ML Router into unified_router.py pipeline | 1.5hr | `subagent_type="hephaestus"` | hephaestus | 18.1 |
| 18.3 | Wire Skill Registry + Health Monitor into routing decisions | 1.5hr | `subagent_type="hephaestus"` | hephaestus | 18.1 |
| 18.4 | Wire Context Sharing into session start flow | 1.5hr | `subagent_type="hephaestus"` | hephaestus | 18.1 |
| 18.5 | Wire Task Decomposer into delegation flow | 1.5hr | `subagent_type="hephaestus"` | hephaestus | 18.1 |

**Prompt for 18.2 (ML Router):**
```
TASK: Wire ML Router (packages/intelligence/router/ml.py) into the UnifiedDelegationRouter pipeline.

CONTEXT: The unified router at packages/intelligence/router/unified.py already has lazy-init for _ml_router (line 133-139) and uses it in Strategy 2 (line 258-272). However, the ML router only adds to alternatives — it never becomes the primary routing decision.

WHAT TO DO:
1. Read packages/intelligence/router/ml.py fully — understand its predict() API
2. Read packages/intelligence/router/unified.py lines 258-272 — see current ML usage
3. Modify the ML routing strategy so that when ML confidence > 0.75, it becomes the PRIMARY decision (not just an alternative)
4. Add ML prediction metadata to the RoutingDecision (model version, features used, prediction confidence breakdown)
5. Ensure graceful fallback if ML model is unavailable (current behavior is correct — just log warning)

MUST DO:
- Read router/ml.py first to understand the API
- Read router/unified.py fully before editing
- Run `uv run python3 -c "from packages.intelligence.router.unified import UnifiedDelegationRouter; print('OK')"` after changes
- Keep all existing fallback behavior intact

MUST NOT DO:
- Do NOT change the RoutingDecision dataclass structure
- Do NOT modify any other strategy (trigger, memory, keyword)
- Do NOT add new dependencies
- Do NOT commit changes

EXPECTED OUTCOME: ML router can become primary decision when confidence > 0.75, with full metadata attached to the decision.
```

**Prompt for 18.3 (Skill Registry + Health Monitor):**
```
TASK: Wire Skill Registry and Health Monitor into routing decisions in UnifiedDelegationRouter.

CONTEXT: The unified router has lazy-init for _skill_registry (line 141-147) and _health_monitor (line 149-155) but neither is used in the routing pipeline. These should filter out unhealthy agents and boost agents with matching skills.

WHAT TO DO:
1. Read packages/intelligence/skill_registry.py — understand get_skill_registry() and its API
2. Read packages/intelligence/health_monitor.py — understand get_health_monitor() and its API
3. Read packages/intelligence/router/unified.py — find where routing decisions are made
4. Add a health check step BEFORE final agent selection: if the recommended agent is unhealthy, try the next best alternative
5. Add a skill matching step: if multiple agents have similar routing scores, prefer the one whose skills match the task description
6. Add health and skill metadata to RoutingDecision alternatives

MUST DO:
- Read both component files fully before editing
- Use lazy-init pattern (agent may be unavailable — log warning and skip)
- Health check: skip agents with status "unhealthy" or "degraded" for >5min
- Skill matching: use keyword overlap between task and agent skill descriptions
- Run `uv run python3 -c "from packages.intelligence.router.unified import UnifiedDelegationRouter; print('OK')"` after changes

MUST NOT DO:
- Do NOT change RoutingDecision dataclass
- Do NOT modify trigger/memory/ML/keyword strategies
- Do NOT add new dependencies
- Do NOT commit

EXPECTED OUTCOME: Routing decisions respect agent health (skip unhealthy) and skill matching (prefer best-skilled agent among tied candidates).
```

**Prompt for 18.4 (Context Sharing):**
```
TASK: Wire Context Sharing into the session start flow and UnifiedDelegationRouter.

CONTEXT: packages/intelligence/delegation/context_sharing.py exists with get_context_sharing(). The unified router already calls get_shared_context() (line 224-232) but the result is never used to influence routing. Context sharing should inject relevant past session context into the routing decision.

WHAT TO DO:
1. Read packages/intelligence/delegation/context_sharing.py fully
2. Read packages/intelligence/router/unified.py lines 223-232 (current context loading)
3. Modify the context sharing step to:
   a. Load shared context from previous sessions
   b. If similar tasks were completed successfully by a specific agent, boost that agent's score
   c. If similar tasks failed with a specific agent, penalize that agent
   d. Add context-derived insights to the RoutingDecision.reason field
4. Ensure the context sharing works cross-session (reads from .sisyphus/session-state.json and routing.db)

MUST DO:
- Read context_sharing.py fully first
- Use lazy-init pattern
- Cross-session data sources: .sisyphus/session-state.json, .sisyphus/routing.db
- Run `uv run python3 -c "from packages.intelligence.router.unified import UnifiedDelegationRouter; print('OK')"` after changes

MUST NOT DO:
- Do NOT change RoutingDecision dataclass
- Do NOT modify other strategies
- Do NOT add new dependencies
- Do NOT commit

EXPECTED OUTCOME: Routing decisions incorporate cross-session context — agents that succeeded on similar tasks in past sessions get boosted.
```

**Prompt for 18.5 (Task Decomposer):**
```
TASK: Wire Task Decomposer into the delegation flow in UnifiedDelegationRouter.

CONTEXT: packages/intelligence/delegation/decomposer.py exists with get_task_decomposer(). The unified router has lazy-init (line 165-171) and sets `subtasks` on RoutingDecision (line 43) but never actually calls the decomposer. Complex tasks (L4-L5) should be decomposed into subtasks.

WHAT TO DO:
1. Read packages/intelligence/delegation/decomposer.py fully — understand its decompose() API
2. Read packages/intelligence/router/unified.py — find where subtasks could be set
3. Add task decomposition step AFTER routing decision but BEFORE returning:
   - If level >= 4 (complex task), call decomposer to break into subtasks
   - Attach subtasks to RoutingDecision.subtasks field
   - Each subtask should have its own recommended agent and level
4. For L5 tasks (architecture), also add a planning subtask that runs first

MUST DO:
- Read decomposer.py fully first
- Only decompose for L4+ tasks (don't over-decompose simple tasks)
- Each subtask: {description, recommended_agent, level, depends_on}
- Run `uv run python3 -c "from packages.intelligence.router.unified import UnifiedDelegationRouter; print('OK')"` after changes

MUST NOT DO:
- Do NOT change RoutingDecision dataclass
- Do NOT decompose L1-L3 tasks
- Do NOT add new dependencies
- Do NOT commit

EXPECTED OUTCOME: L4-L5 routing decisions include a subtasks list with per-subtask agent recommendations and dependency ordering.
```

### Wave 3: Pipeline Enhancement (Parallel x3, 4hr)

| # | Task | Effort | Delegation | Agent | Depends On |
|---|------|--------|------------|-------|------------|
| 18.6 | Wire Prompt Templates into delegation prompts | 1hr | `subagent_type="hephaestus"` | hephaestus | 18.2-18.5 |
| 18.7 | Wire A/B Testing into routing strategy selection | 1.5hr | `subagent_type="hephaestus"` | hephaestus | 18.2-18.5 |
| 18.8 | Wire Agent Communication into multi-agent tasks | 1.5hr | `subagent_type="hephaestus"` | hephaestus | 18.2-18.5 |

### Wave 4: Cleanup + Integration Tests (Sequential, 2hr)

| # | Task | Effort | Delegation | Agent | Depends On |
|---|------|--------|------------|-------|------------|
| 18.9 | Delete duplicate files, archive orphaned components | 0.5hr | `subagent_type="hephaestus"` | hephaestus | 18.1 |
| 18.10 | Consolidate duplicate scoring (3 → 1 complexity scorer) | 0.5hr | `subagent_type="hephaestus"` | hephaestus | 18.9 |
| 18.11 | Integration tests for full delegation pipeline | 1hr | `subagent_type="hephaestus"` | hephaestus | 18.2-18.10 |

---

## Delegation Summary

| Wave | Tasks | Agent(s) | Parallel | Duration |
|------|-------|----------|----------|----------|
| 1 | 18.1, 18.1b | explore × 2 | Yes | 1hr |
| 2 | 18.2, 18.3, 18.4, 18.5 | hephaestus × 4 | Yes | 1.5hr |
| 3 | 18.6, 18.7, 18.8 | hephaestus × 3 | Yes | 1.5hr |
| 4 | 18.9, 18.10, 18.11 | hephaestus (sequential) | No | 2hr |

**Total: ~6 hours wall time with parallel delegation**

---

## Success Criteria

- [ ] All 8 advanced components actively used in routing pipeline (not just lazy-init)
- [ ] ML router can become primary decision when confidence > 0.75
- [ ] Health monitor filters out unhealthy agents
- [ ] Skill registry boosts agents with matching capabilities
- [ ] Context sharing influences routing based on past session outcomes
- [ ] Task decomposer breaks L4-L5 tasks into subtasks
- [ ] 0 orphaned imports in `packages/intelligence/`
- [ ] Integration tests pass for full pipeline (trigger → ML → memory → skill → health → decompose → template → agent)
- [ ] `uv run python3 -c "from packages.intelligence import route; print('OK')"` succeeds

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Component import fails | All components use lazy-init with try/except — pipeline survives |
| Breaking change to RoutingDecision | Forbidden by MUST NOT DO in all delegation prompts |
| Circular dependency | Already resolved by uv workspace — no new deps added |
| Regression in existing routing | Each wave runs import verification after changes |

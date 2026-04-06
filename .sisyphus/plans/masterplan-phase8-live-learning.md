# N-Xyme_MIND Masterplan — Wire Learning Into Live Routing

> Created: 2026-04-06 | Priority: P0 (Highest ROI)
> Goal: Replace hardcoded routing with AdaptiveRouter learning loop

---

## Current State

- ✅ All components built and tested (98 tests passing)
- ✅ AdaptiveRouter works in isolation
- ❌ **Intelligent router still uses hardcoded rules** — never calls AdaptiveRouter
- ❌ **No real-world learning** — Q-Learning only updated in tests

## The Gap

`bin/intelligent_router_mcp.py` routes tasks using static rules:
```python
# Current: hardcoded keyword matching
if "fix typo" in task: return L1
if "add feature" in task: return L3
```

Should be:
```python
# Target: AdaptiveRouter learns from every decision
result = adaptive_router.route(task)
# Logs outcome, updates Q-Learning, improves over time
```

---

## Phase 8: Wire Live Learning (P0)

### T8.1: Replace Hardcoded Router with AdaptiveRouter
**Priority**: P0 | **Complexity**: L4 | **Agent**: `hephaestus`
**Files**: `bin/intelligent_router_mcp.py` (modify), `packages/learning_engine/routing/adaptive_router.py` (extend if needed)

**Requirements**:
- Read current `bin/intelligent_router_mcp.py` to understand routing interface
- Replace hardcoded keyword rules with AdaptiveRouter
- Keep fallback to hardcoded rules for first N decisions (cold start)
- After N decisions, Q-Learning takes over
- Log every routing decision as outcome (success = task completed without errors)
- Must be backward compatible — existing MCP tools still work

**Success Criteria**:
- `route_task()` calls AdaptiveRouter, not hardcoded rules
- First 50 decisions use fallback (cold start)
- After 50 decisions, Q-Learning influences routing
- All existing MCP tools still respond correctly

### T8.2: Auto-Log Outcomes from Task Completion
**Priority**: P0 | **Complexity**: L4 | **Agent**: `hephaestus`
**Files**: `bin/intelligent_router_mcp.py` (extend), task execution hooks

**Requirements**:
- Hook into task completion to auto-log outcomes
- Success = task completed without errors
- Failure = task errored or user rejected
- Latency = task execution time
- Tokens = tokens used (from session)
- Call `OutcomeLogger.log()` automatically after every task

**Success Criteria**:
- Every routed task automatically logs outcome
- Q-Learning receives real rewards from real tasks
- No manual intervention needed

### T8.3: Learning Dashboard / Stats Endpoint
**Priority**: P1 | **Complexity**: L3 | **Agent**: `hephaestus`
**Files**: `bin/intelligent_router_mcp.py` (add tool), `packages/learning_engine/routing/adaptive_router.py` (extend)

**Requirements**:
- Add MCP tool `get_learning_progress()` — returns:
  - Total decisions made
  - Success rate over time
  - Top performing agent per task type
  - Q-Learning convergence status
  - Exploration vs exploitation ratio

**Success Criteria**:
- Tool returns real data from real usage
- Shows improvement trend over time

---

## Optimal Delegation Chain

```
Sisyphus (Orchestrator)
    ↓
┌─────────────────────────────────────────────────────────────┐
│ WAVE 1 (P0 — Critical, Sequential — T8.2 depends on T8.1) │
├─────────────────────────────────────────────────────────────┤
│ T8.1: Replace hardcoded router → AdaptiveRouter (hephaestus)│
│   ↓ (verify it works)                                       │
│ T8.2: Auto-log outcomes from task completion (hephaestus)   │
└─────────────────────────────────────────────────────────────┘
    ↓ (verify Wave 1)
┌─────────────────────────────────────────────────────────────┐
│ WAVE 2 (P1 — Nice to have, Parallel)                       │
├─────────────────────────────────────────────────────────────┤
│ T8.3: Learning dashboard/stats (hephaestus)                 │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ FINAL: Test with real tasks → Commit → Push                │
└─────────────────────────────────────────────────────────────┘
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Q-Learning makes bad decisions early | High | Medium | Cold start fallback (first 50 decisions use hardcoded rules) |
| Outcome logging slows down tasks | Low | Low | Async logging, fire-and-forget |
| Breaking existing MCP tools | Medium | High | Keep backward compat, test all tools after change |

---

## Success Criteria

- [ ] `route_task()` uses AdaptiveRouter, not hardcoded rules
- [ ] Every real task logs outcome automatically
- [ ] Q-Learning improves routing after ~50 decisions
- [ ] All existing MCP tools still work
- [ ] Learning stats show improvement over time
- [ ] Committed and pushed

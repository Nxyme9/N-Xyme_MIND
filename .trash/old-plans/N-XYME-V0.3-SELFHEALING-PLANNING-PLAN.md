# N-Xyme MIND v0.3 — Self-Healing + Planning Plan

> **Philosophy**: "Add autonomous resilience — the agent can detect failures and recover."
> **Status**: DEPENDS ON v0.2
> **Timeline**: 5-7 sessions
> **Inspired by**: openclaw (circuit breaker), GTPyhop (HTN planning)

---

## 1. EXECUTIVE SUMMARY

v0.3 introduces autonomous resilience — the agent can detect failures and recover, plus perform basic task decomposition. This phase transforms the system from a fragile execution engine to a resilient agent.

**What v0.3 Adds**:
- Self-healing (health monitor, circuit breaker, auto-recovery)
- MCP health monitoring
- Basic HTN planning (rule-based)
- Checkpoint/resume
- Regression detection

**What v0.3 Excludes**:
- No self-learning
- No security sandboxing
- No runtime containerization
- No tool synthesis

---

## 2. LAYERS INCLUDED (NEW + ENHANCED)

### L4: Self-Healing (Core)
| File | Status | Description |
|------|--------|-------------|
| `src/healing/health_monitor.py` | ENHANCE | Move from src/health_monitor.py + composite scoring |
| `src/healing/self_healer.py` | ENHANCE | Move from src/self_healer.py + circuit breaker |
| `src/healing/auto_recovery.py` | NEW | 4-tier graceful degradation |
| `src/healing/checkpoint_resume.py` | NEW | LangGraph-style state persistence |
| `src/healing/mcp_health.py` | NEW | MCP server health monitoring |

### L10: Planning (Basic)
| File | Status | Description |
|------|--------|-------------|
| `src/planning/htn_planner.py` | NEW | Hierarchical task networks (GTPyhop) |
| `src/planning/goal_reasoning.py` | NEW | SELFGOAL patterns |
| `src/planning/temporal_planner.py` | DEFERRED | v0.5 |

### L8: Testing (Enhanced)
| File | Status | Description |
|------|--------|-------------|
| `src/testing/regression_detector.py` | NEW | agent-vcr time-travel patterns |

### L5: Orchestration (Enhanced)
| File | Status | Description |
|------|--------|-------------|
| `src/orchestration/sisyphus.py` | ENHANCE | Add checkpoint calls |
| `src/orchestration/a2a_protocol.py` | ENHANCE | Full A2A implementation |
| `src/orchestration/network_orchestrator.py` | ENHANCE | Full orchestration |

---

## 3. IMPLEMENTATION TASKS

### W1: Self-Healing Core (2 sessions)
| Task | File | Agent | Category | QA |
|------|------|-------|----------|-----|
| W1-T1 | Move+enhance `health_monitor.py` | Hephaestus | deep | Composite scoring 0-100 |
| W1-T2 | Move+enhance `self_healer.py` | Hephaestus | deep | Circuit breaker transitions |
| W1-T3 | `src/healing/auto_recovery.py` | Hephaestus | deep | 4-tier degradation works |
| W1-T4 | `src/healing/checkpoint_resume.py` | Hephaestus | deep | State persistence works |
| W1-T5 | `src/healing/mcp_health.py` | Hephaestus | deep | MCP health monitoring works |

### W2: Planning (1-2 sessions)
| Task | File | Agent | Category | QA |
|------|------|-------|----------|-----|
| W2-T1 | `src/planning/htn_planner.py` | Hephaestus | ultrabrain | HTN planning works |
| W2-T2 | `src/planning/goal_reasoning.py` | Hephaestus | deep | Goal reasoning works |

### W3: Testing Enhancement (1 session)
| Task | File | Agent | Category | QA |
|------|------|-------|----------|-----|
| W3-T1 | `src/testing/regression_detector.py` | Hephaestus | deep | Regression detection works |

### W4: Orchestration Enhancement (1 session)
| Task | File | Agent | Category | QA |
|------|------|-------|----------|-----|
| W4-T1 | Enhance `sisyphus.py` | Hephaestus | deep | Checkpoint calls added |
| W4-T2 | Enhance `a2a_protocol.py` | Hephaestus | deep | Full A2A implementation |
| W4-T3 | Enhance `network_orchestrator.py` | Hephaestus | ultrabrain | Full orchestration |

---

## 4. TESTING STRATEGY

### Unit Tests (30 tests)
| Layer | Test Count | Description |
|-------|------------|-------------|
| L4 Self-Healing | 15 | Health scoring, circuit breaker, recovery |
| L10 Planning | 10 | HTN planning, goal reasoning |
| L8 Testing | 5 | Regression detection |

### Integration Tests (10 tests — NEW)
| Test | Description |
|------|-------------|
| Failure injection | Simulate MCP timeout, verify recovery |
| Checkpoint restore | Verify state restoration after failure |
| Planning validation | Verify task decomposition produces valid sub-tasks |
| A2A delegation | Verify agent-to-agent task delegation |
| MCP health | Verify MCP health monitoring detects failures |

### Success Criteria
- [ ] Agent recovers from MCP failure without human intervention
- [ ] Task decomposition produces executable sub-plans
- [ ] State restoration works after checkpoint
- [ ] 119 tests passing (69 v0.2 + 30 unit + 10 integration + 10 existing)

---

## 5. DEPENDENCIES

```
v0.2 Complete ──► W1 (Self-Healing) ──► W2 (Planning) ──► W3 (Testing) ──► W4 (Orchestration)
```

---

## 6. QUALITY GATES

| Gate | v0.3 |
|------|------|
| Gate 1: Type Check | ✓ |
| Gate 2: Lint | ✓ |
| Gate 3: Tests | ✓ (119 tests) |
| Gate 4: Coverage | 75% |
| Gate 5: Secrets | ✓ |
| Gate 6: Placeholders | ✓ |

---

## 7. ATOMIC COMMIT STRATEGY

| Commit | Message | Files |
|--------|---------|-------|
| 0 | `feat(healing): implement self-healing system (v0.3)` | 5 L4 files |
| 1 | `feat(planning): implement HTN planner + goal reasoning (v0.3)` | 2 L10 files |
| 2 | `feat(testing): add regression detector (v0.3)` | 1 L8 file |
| 3 | `feat(orchestration): enhance orchestration (v0.3)` | 3 L5 files |
| 4 | `test: add tests for v0.3` | 40 tests |
| 5 | `chore: run quality gates, tag v0.3.0` | Various |

---

## 8. RISK MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| HTN planning too complex | HIGH | HIGH | Use rule-based, not learned |
| Circuit breaker loops | Medium | Medium | Add max retry limit + backoff |
| Session limit hit | HIGH | Medium | Checkpoint after each wave |

---

*v0.3 Self-Healing + Planning Plan — Autonomous resilience*
*5-7 sessions | 11 tasks | ~11 new files | 40 new tests*

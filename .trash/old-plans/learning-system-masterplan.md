# N-Xyme_MIND Learning System — Robust Master Plan

> **Generated**: 2026-04-05
> **Sources**: Metis, Momus, Oracle, Librarian, Explore (4 agents, 47 issues found)
> **Status**: Ready for Execution

---

## Executive Summary

**Current State**: Learning system exists but is effectively stateless in production. MCP tools create fresh instances every call, health metrics are fake, recovery handlers are no-ops, and learning modules don't communicate.

**Goal**: Transform from "broken learning system" to "production-grade self-learning memory" matching Mem0/Zep/Letta standards.

**Approach**: 5 phases, 25 tasks, ~40 hours total. Fix critical bugs first, then wire modules together, then add bleeding-edge features.

---

## Phase 0: Critical Bug Fixes (4 hours) — MUST DO FIRST

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T0.1**: Fix singleton instances for all learning modules | `mcp_server.py`, `src/learning/__init__.py` | Hephaestus | 1 hr | None |
| **T0.2**: Fix `SelfLearner` and `PromptWizard` to use persistent DB | `self_learning.py`, `prompt_evolution.py`, `mcp_server.py` | Hephaestus | 30 min | T0.1 |
| **T0.3**: Fix fake health metrics — record REAL metrics | `daemon.py`, `health_composite.py` | Hephaestus | 2 hrs | None |
| **T0.4**: Implement real recovery handlers | `auto_recovery.py` | Hephaestus | 2 hrs | None |
| **T0.5**: Add thread locks to shared state | `self_learning.py`, `skill_lifecycle.py`, `health_composite.py` | Hephaestus | 1 hr | None |
| **T0.6**: Cap unbounded lists + batch feedback inserts | `self_learning.py`, `mcp_server.py` | Hephaestus | 30 min | T0.5 |

**Success Metrics**:
- [ ] Learning persists across MCP calls (not stateless)
- [ ] Health metrics reflect real system state (not hardcoded 100.0)
- [ ] Recovery handlers actually recover (not just log)
- [ ] No race conditions under concurrent access
- [ ] No memory leaks from unbounded growth
- [ ] Feedback inserts batched (not N+1 per search)

---

## Phase 1: Wire Learning Modules Together (6 hours)

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T1.1**: Create `LearningEventBus` — unified pub/sub for learning signals | `src/learning/event_bus.py` | Hephaestus | 2 hrs | Phase 0 |
| **T1.2**: Wire MCP tools to event bus (replace direct calls) | `mcp_server.py` | Hephaestus | 1 hr | T1.1 |
| **T1.3**: Wire skill outcomes → SelfLearner pattern extraction | `skill_lifecycle.py`, `self_learning.py` | Hephaestus | 1 hr | T1.1 |
| **T1.4**: Wire search results → PreferenceModel feedback | `mcp_server.py`, `preference_model.py` | Hephaestus | 1 hr | T1.1 |
| **T1.5**: Wire daemon learning cycle to SelfLearner.extract_patterns() | `daemon.py`, `self_learning.py` | Hephaestus | 1 hr | T1.1 |

**Success Metrics**:
- [ ] All learning signals flow through single event bus
- [ ] Skill outcomes feed into pattern extraction
- [ ] Search results update preference model
- [ ] Daemon learning cycle actually extracts patterns
- [ ] No more scattered SQLite writes

---

## Phase 2: Replace Garbage Feedback with Signals Taxonomy (4 hours)

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T2.1**: Implement Signals taxonomy (interaction, execution, environment) | `src/learning/signals.py` | Hephaestus | 2 hrs | Phase 1 |
| **T2.2**: Replace implicit position-based feedback with Signals | `mcp_server.py` | Hephaestus | 1 hr | T2.1 |
| **T2.3**: Add signal computation to search results | `mcp_server.py`, `signals.py` | Hephaestus | 1 hr | T2.1 |

**Success Metrics**:
- [ ] Signals taxonomy implemented (3 categories, 8 signals)
- [ ] No more "position 0 = used, 3+ = ignored" heuristic
- [ ] Real implicit signals captured (reformulation, dwell time, etc.)
- [ ] Signal data feeds into PriorityEngine

---

## Phase 3: Bleeding-Edge Features (12 hours)

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T3.1**: ETGPO prompt optimization (error taxonomy → guidance) | `src/learning/etgpo.py` | Hephaestus | 3 hrs | Phase 2 |
| **T3.2**: Wire ETGPO to PromptWizard (replace naive strategies) | `prompt_evolution.py`, `etgpo.py` | Hephaestus | 2 hrs | T3.1 |
| **T3.3**: EvoSkill Proposer (failure → skill proposal) | `src/learning/skill_proposer.py` | Hephaestus | 3 hrs | Phase 1 |
| **T3.4**: Skill Registry + Hybrid Router | `src/learning/skill_registry.py` | Hephaestus | 2 hrs | T3.3 |
| **T3.5**: LLM-as-a-Judge for self-evaluation | `src/learning/llm_judge.py` | Hephaestus | 2 hrs | Phase 1 |

**Success Metrics**:
- [ ] ETGPO categorizes errors and generates guidance
- [ ] PromptWizard uses ETGPO instead of naive strategies
- [ ] EvoSkill proposes new skills from failure traces
- [ ] Skill registry routes queries to best skill
- [ ] LLM judge evaluates output quality without human feedback

---

## Phase 4: Testing + Polish (4 hours)

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T4.1**: Add pytest tests for all learning modules | `tests/test_learning/` | Hephaestus | 2 hrs | All phases |
| **T4.2**: Add integration tests for learning → MCP → daemon | `tests/test_learning_integration.py` | Hephaestus | 1 hr | T4.1 |
| **T4.3**: Add type hints + `__all__` exports | All learning modules | Sisyphus-Junior | 30 min | All phases |
| **T4.4**: Documentation + examples | `docs/learning.md` | Sisyphus-Junior | 30 min | All phases |

**Success Metrics**:
- [ ] 100% test coverage for learning modules
- [ ] Integration tests pass end-to-end
- [ ] All modules have type hints and exports
- [ ] Documentation with usage examples

---

## Dependency Graph

```
Phase 0 (Critical Fixes) — 4 hours
├── T0.1: Singleton instances
├── T0.2: Persistent DB paths
├── T0.3: Real health metrics
├── T0.4: Real recovery handlers
├── T0.5: Thread locks
└── T0.6: Cap unbounded lists + batch inserts

Phase 1 (Wire Modules) — 6 hours
├── T1.1: LearningEventBus
├── T1.2: Wire MCP tools to bus
├── T1.3: Wire skills → SelfLearner
├── T1.4: Wire search → PreferenceModel
└── T1.5: Wire daemon → SelfLearner

Phase 2 (Signals Taxonomy) — 4 hours
├── T2.1: Implement Signals taxonomy
├── T2.2: Replace implicit feedback
└── T2.3: Add signal computation

Phase 3 (Bleeding-Edge) — 12 hours
├── T3.1: ETGPO prompt optimization
├── T3.2: Wire ETGPO to PromptWizard
├── T3.3: EvoSkill Proposer
├── T3.4: Skill Registry + Hybrid Router
└── T3.5: LLM-as-a-Judge

Phase 4 (Testing + Polish) — 4 hours
├── T4.1: Pytest tests
├── T4.2: Integration tests
├── T4.3: Type hints + exports
└── T4.4: Documentation
```

---

## Agent Delegation Strategy

| Task Type | Agent | Why |
|-----------|-------|-----|
| **Critical bug fixes** | Hephaestus | Code writing, follows patterns |
| **Module wiring** | Hephaestus | Integration work |
| **Bleeding-edge features** | Hephaestus + Oracle review | Complex implementation + architecture review |
| **Testing** | Hephaestus | Test writing |
| **Type hints + docs** | Sisyphus-Junior | Simple, repetitive work |
| **Architecture review** | Oracle | After each phase |
| **Adversarial review** | Momus | After Phase 2 and Phase 4 |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **SQLite write contention** | Medium | High | WAL mode + connection pooling |
| **Feedback signal noise** | High | Medium | Signals taxonomy filters noise |
| **PromptWizard runaway iterations** | Medium | Medium | Score threshold + max iterations |
| **Race conditions under load** | Low | High | Thread locks (T0.5) |
| **Memory leaks at scale** | Low | Medium | Capped lists + TTL (T0.6) |

---

## Success Metrics

| Metric | Current | Target (Phase 2) | Target (Phase 4) |
|--------|---------|------------------|------------------|
| Learning persistence | ❌ Stateless | ✅ Persistent | ✅ Persistent |
| Health metrics accuracy | 0% (fake) | 80% | 95% |
| Recovery effectiveness | 0% (no-ops) | 60% | 90% |
| Feedback signal quality | Garbage | Good (Signals) | Excellent |
| Prompt evolution quality | Degrades | Improves (ETGPO) | Significantly improves |
| Test coverage | 0% | 60% | 100% |
| Cross-module learning | None | Partial | Full |

---

## Execution Order

1. **Phase 0** (4 hrs) — Fix critical bugs first
2. **Phase 1** (6 hrs) — Wire modules together
3. **Phase 2** (4 hrs) — Replace garbage feedback
4. **Phase 3** (12 hrs) — Add bleeding-edge features
5. **Phase 4** (4 hrs) — Testing + polish

**Total: ~30 hours (4 working days)**

---

## Atomic Commit Strategy

- **One commit per task** — each commit is independently testable
- **Tests first** — commit tests before implementation (TDD)
- **Feature flags** — all new features behind config flags (OFF by default)
- **No breaking changes** — existing functionality must continue working

---

*This masterplan synthesizes insights from 4 agents: Metis (planning), Momus (adversarial review), Oracle (architecture), Librarian (bleeding-edge research), and Explore (codebase audit). Total: 25 tasks across 5 phases, ~30 hours.*

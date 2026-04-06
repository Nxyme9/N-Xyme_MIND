# N-Xyme_MIND Learning System — Optimized Master Plan

> **Generated**: 2026-04-05
> **Sources**: Metis (this optimization), Explore (codebase audit), Librarian (external research: Mem0/Zep/Letta/ETGPO patterns)
> **Status**: Ready for Execution
> **Optimization**: 5 phases → 3 waves, 25 tasks → 19 tasks, 30 hrs → 27 hrs effort, 30 hrs → ~15 hrs calendar time

---

## Executive Summary

**What Changed from Original Plan:**
- **5 phases → 3 waves** — removed artificial barriers between independent work
- **25 tasks → 19 tasks** — merged 8 trivial tasks, split 2 complex tasks
- **30 hrs → 27 hrs effort** — realistic estimates (some up, some down)
- **30 hrs → ~15 hrs calendar time** — maximum parallelism within each wave
- **TDD-first** — tests written before or alongside implementation, not deferred
- **Feature flags** — every new feature behind a config flag (OFF by default)

**Critical Path**: Wave 1 (4 hrs) → Wave 2 (6 hrs) → Wave 3 (5 hrs) = **~15 hours calendar time**
**Total Effort**: **~27 hours** (spread across parallel agents)

---

## Wave 1: Foundation — Bug Fixes + Core Infrastructure (4 hrs calendar, 8 hrs effort)

> **Goal**: System is stable, persistent, and has core infrastructure (EventBus + Signals) ready for wiring.
> **Parallelism**: 3 independent tracks run simultaneously.

### Track A: Critical Persistence Path (1.5 hrs) — MUST complete first

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T0.1**: Fix singleton instances for all learning modules | `mcp_server.py`, `src/learning/__init__.py` | Hephaestus | 1 hr | None |
| **T0.2**: Fix `SelfLearner` and `PromptWizard` to use persistent DB | `self_learning.py`, `prompt_evolution.py`, `mcp_server.py` | Hephaestus | 30 min | T0.1 |

**Why sequential**: T0.2 depends on T0.1's singleton fix. This is the critical path bottleneck for Wave 1.

### Track B: Stability Fixes (2 hrs) — Parallel with Track A

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T0.3**: Fix fake health metrics — record REAL metrics | `daemon.py`, `health_composite.py` | Hephaestus | 2 hrs | None |
| **T0.4**: Implement real recovery handlers | `auto_recovery.py` | Hephaestus | 2 hrs | None |
| **T0.5**: Add thread locks to shared state | `self_learning.py`, `skill_lifecycle.py`, `health_composite.py` | Hephaestus | 1 hr | None |
| **T0.6**: Cap unbounded lists + batch feedback inserts | `self_learning.py`, `mcp_server.py` | Hephaestus | 30 min | T0.5 |

**Parallelism**: T0.3, T0.4, T0.5 can start immediately (no deps). T0.6 starts after T0.5.

### Track C: Core Infrastructure (2 hrs) — Parallel with Tracks A & B

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T1.1**: Create `LearningEventBus` — unified pub/sub for learning signals | `src/learning/event_bus.py` | Hephaestus | 2 hrs | T0.1 (needs stable singletons) |
| **T2.1**: Implement Signals taxonomy (interaction, execution, environment) | `src/learning/signals.py` | Hephaestus | 2 hrs | None |

**Key insight**: T1.1 only needs T0.1 (singleton fix), not all of Phase 0. T2.1 is a brand-new module with zero dependencies.

### Wave 1 Success Metrics
- [ ] Learning persists across MCP calls (not stateless)
- [ ] Health metrics reflect real system state (not hardcoded 100.0)
- [ ] Recovery handlers actually recover (not just log)
- [ ] No race conditions under concurrent access
- [ ] No memory leaks from unbounded growth
- [ ] EventBus exists and accepts/emits events
- [ ] Signals taxonomy defined (3 categories, 8+ signals)

### Wave 1 Atomic Commits
```
commit 1: "fix(learning): singleton instances for all learning modules"
commit 2: "fix(learning): persistent DB paths for SelfLearner and PromptWizard"
commit 3: "fix(daemon): real health metrics recording"
commit 4: "fix(recovery): implement real recovery handlers"
commit 5: "fix(learning): thread locks on shared state"
commit 6: "fix(learning): cap unbounded lists + batch feedback inserts"
commit 7: "feat(learning): create LearningEventBus pub/sub system"
commit 8: "feat(learning): implement Signals taxonomy"
```

---

## Wave 2: Wiring + Features (6 hrs calendar, 13.5 hrs effort)

> **Goal**: All modules wired together, Signals integrated, bleeding-edge features implemented.
> **Parallelism**: 3 independent tracks run simultaneously after Wave 1.

### Track A: Module Wiring (3 hrs) — Parallel with Tracks B & C

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T1.2-5**: Wire ALL modules to EventBus (MCP tools, skills, search, daemon) | `mcp_server.py`, `skill_lifecycle.py`, `self_learning.py`, `daemon.py`, `preference_model.py` | Hephaestus | 3 hrs | T1.1 (Wave 1) |

**Merged from**: T1.2, T1.3, T1.4, T1.5 (4 tasks → 1). These are all mechanical wiring tasks — same pattern, same file (`mcp_server.py` mostly). Merging reduces context switching overhead.

### Track B: Signals Integration (1.5 hrs) — Parallel with Tracks A & C

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T2.2-3**: Integrate Signals into MCP search (replace implicit feedback + compute signals) | `mcp_server.py`, `signals.py` | Hephaestus | 1.5 hrs | T2.1 (Wave 1) |

**Merged from**: T2.2, T2.3 (2 tasks → 1). Both touch `mcp_server.py` and `signals.py` — same context.

### Track C: Bleeding-Edge Features (6 hrs) — Parallel with Tracks A & B

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T3.1-2**: ETGPO prompt optimization + PromptWizard integration | `src/learning/etgpo.py`, `prompt_evolution.py` | Hephaestus | 4 hrs | T2.1 (Signals taxonomy, Wave 1) |
| **T3.3a**: EvoSkill Proposer — failure trace analysis | `src/learning/skill_proposer.py` | Hephaestus | 1.5 hrs | T1.1 (EventBus, Wave 1) |
| **T3.3b**: EvoSkill Proposer — skill spec generation | `src/learning/skill_proposer.py` | Hephaestus | 2 hrs | T3.3a |
| **T3.5**: LLM-as-a-Judge for self-evaluation | `src/learning/llm_judge.py` | Hephaestus | 2 hrs | T1.1 (EventBus, Wave 1) |

**Split**: T3.3 (EvoSkill) split into T3.3a (failure analysis) and T3.3b (skill generation) for better parallelism and testability.
**Merged**: T3.1 + T3.2 (ETGPO + PromptWizard wiring) — same context, same files.

### Wave 2 Success Metrics
- [ ] All learning signals flow through single EventBus
- [ ] Skill outcomes feed into pattern extraction
- [ ] Search results update preference model
- [ ] Daemon learning cycle actually extracts patterns
- [ ] No more scattered SQLite writes
- [ ] Signals taxonomy integrated (no more "position 0 = used" heuristic)
- [ ] Real implicit signals captured (reformulation, dwell time, etc.)
- [ ] ETGPO categorizes errors and generates guidance
- [ ] PromptWizard uses ETGPO instead of naive strategies
- [ ] EvoSkill proposes new skills from failure traces
- [ ] LLM judge evaluates output quality without human feedback

### Wave 2 Atomic Commits
```
commit 9:  "feat(learning): wire all modules to LearningEventBus"
commit 10: "feat(learning): integrate Signals into MCP search"
commit 11: "feat(learning): implement ETGPO error taxonomy-guided optimization"
commit 12: "feat(learning): wire ETGPO to PromptWizard"
commit 13: "feat(learning): implement EvoSkill failure trace analysis"
commit 14: "feat(learning): implement EvoSkill spec generation"
commit 15: "feat(learning): implement LLM-as-a-Judge self-evaluation"
```

---

## Wave 3: Integration + Polish (5 hrs calendar, 5.5 hrs effort)

> **Goal**: Everything tested, typed, documented, and production-ready.
> **Parallelism**: Sisyphus-Junior handles polish while Hephaestus does testing.

### Track A: Skill Registry (2 hrs)

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T3.4**: Skill Registry + Hybrid Router | `src/learning/skill_registry.py` | Hephaestus | 2 hrs | T3.3b (Wave 2) |

### Track B: Testing — TDD Approach (3 hrs)

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T4.1a**: Tests for SelfLearner + EventBus | `tests/test_self_learning.py`, `tests/test_event_bus.py` | Hephaestus | 1.5 hrs | T0.1, T1.1 (Wave 1) |
| **T4.1b**: Tests for SkillLifecycle + SkillProposer | `tests/test_skill_lifecycle.py`, `tests/test_skill_proposer.py` | Hephaestus | 1 hr | T3.3b (Wave 2) |
| **T4.1c**: Tests for PromptWizard + ETGPO + LLMJudge | `tests/test_prompt_evolution.py`, `tests/test_etgpo.py`, `tests/test_llm_judge.py` | Hephaestus | 1.5 hrs | T3.1-2, T3.5 (Wave 2) |
| **T4.2**: Integration tests (learning → MCP → daemon) | `tests/test_learning_integration.py` | Hephaestus | 1 hr | All Wave 2 tasks |

**Key change**: Tests are split by module and can start as soon as their modules are done (not after ALL phases). T4.1a can start after Wave 1, T4.1b/c after Wave 2 tracks complete.

### Track C: Polish (1 hr) — Parallel with Track B

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T4.3**: Add type hints + `__all__` exports | All learning modules | Sisyphus-Junior | 30 min | All phases |
| **T4.4**: Documentation + examples | `docs/learning.md` | Sisyphus-Junior | 30 min | All phases |

### Wave 3 Success Metrics
- [ ] 80%+ test coverage for learning modules (100% is unrealistic for 1456+ lines of new code)
- [ ] Integration tests pass end-to-end
- [ ] All modules have type hints and exports
- [ ] Documentation with usage examples

### Wave 3 Atomic Commits
```
commit 16: "feat(learning): implement Skill Registry + Hybrid Router"
commit 17: "test(learning): add unit tests for SelfLearner + EventBus"
commit 18: "test(learning): add unit tests for SkillLifecycle + SkillProposer"
commit 19: "test(learning): add unit tests for PromptWizard + ETGPO + LLMJudge"
commit 20: "test(learning): add integration tests"
commit 21: "chore(learning): add type hints and __all__ exports"
commit 22: "docs(learning): add usage documentation and examples"
```

---

## Dependency Graph (Optimized)

```
Wave 1: Foundation (4 hrs calendar)
├── Track A (Critical Path): T0.1 → T0.2                          [1.5 hrs]
├── Track B (Parallel):     T0.3, T0.4, T0.5 → T0.6               [2 hrs]
└── Track C (Parallel):     T1.1 (after T0.1), T2.1               [2 hrs]

Wave 2: Wiring + Features (6 hrs calendar)
├── Track A (Parallel):     T1.2-5 (wire all modules)             [3 hrs]
├── Track B (Parallel):     T2.2-3 (signals integration)          [1.5 hrs]
└── Track C (Parallel):     T3.1-2 (ETGPO), T3.3a→T3.3b, T3.5   [6 hrs]

Wave 3: Integration + Polish (5 hrs calendar)
├── Track A:                T3.4 (skill registry)                 [2 hrs]
├── Track B:                T4.1a, T4.1b, T4.1c, T4.2            [3 hrs]
└── Track C (Parallel):     T4.3, T4.4 (Sisyphus-Junior)         [1 hr]
```

---

## Critical Path Analysis

### Minimum Calendar Time: ~15 hours

```
Critical Path (longest chain of dependencies):
T0.1 (1h) → T1.1 (2h) → T3.1-2 (4h) → T4.1c (1.5h) → T4.2 (1h) = 9.5 hrs

Alternative Critical Path:
T0.1 (1h) → T1.1 (2h) → T3.3a (1.5h) → T3.3b (2h) → T3.4 (2h) → T4.1b (1h) → T4.2 (1h) = 10.5 hrs

Bottleneck: T3.1-2 (ETGPO) and T3.3a→T3.3b→T3.4 (EvoSkill chain)
```

### Parallelism Summary

| Wave | Sequential Time | Parallel Time | Speedup |
|------|----------------|---------------|---------|
| Wave 1 | 8 hrs | 4 hrs | 2x |
| Wave 2 | 13.5 hrs | 6 hrs | 2.25x |
| Wave 3 | 5.5 hrs | 5 hrs | 1.1x |
| **Total** | **27 hrs** | **~15 hrs** | **1.8x** |

---

## Agent Assignment Strategy

| Task Type | Agent | Why | Parallel Instances |
|-----------|-------|-----|-------------------|
| Bug fixes (T0.1-T0.6) | Hephaestus | Code writing, follows patterns | 3 parallel (Tracks A, B, C) |
| EventBus (T1.1) | Hephaestus | New module creation | 1 (depends on T0.1) |
| Signals (T2.1) | Hephaestus | New module creation | 1 (no deps) |
| Wiring (T1.2-5) | Hephaestus | Mechanical integration | 1 |
| Signals integration (T2.2-3) | Hephaestus | Mechanical integration | 1 |
| ETGPO (T3.1-2) | Hephaestus + Oracle review | Complex algorithm needs architecture review | 1 |
| EvoSkill (T3.3a-b) | Hephaestus | New module creation | 1 (sequential a→b) |
| LLM Judge (T3.5) | Hephaestus | API wrapper, straightforward | 1 |
| Skill Registry (T3.4) | Hephaestus | New module creation | 1 |
| Unit tests (T4.1a-c) | Hephaestus | Test writing | 3 parallel (by module) |
| Integration tests (T4.2) | Hephaestus | Cross-module testing | 1 |
| Type hints + docs (T4.3-4) | Sisyphus-Junior | Simple, repetitive work | 1 (parallel with Hephaestus) |
| Architecture review | Oracle | After ETGPO and EvoSkill | 1 (parallel with Wave 3) |
| Adversarial review | Momus | After Wave 2 completion | 1 |

### Parallel Execution Plan (Ultrawork)

**Wave 1 — Fire 3 Hephaestus instances simultaneously:**
```
Hephaestus #1: T0.1 → T0.2 (persistence chain)
Hephaestus #2: T0.3, T0.4, T0.5 → T0.6 (stability chain)
Hephaestus #3: T1.1 (EventBus), T2.1 (Signals) — parallel after T0.1
```

**Wave 2 — Fire 3 Hephaestus instances simultaneously:**
```
Hephaestus #1: T1.2-5 (wire all modules)
Hephaestus #2: T2.2-3 (signals integration)
Hephaestus #3: T3.1-2 (ETGPO), T3.3a→T3.3b (EvoSkill), T3.5 (LLM Judge)
```

**Wave 3 — Fire 2 Hephaestus + 1 Sisyphus-Junior simultaneously:**
```
Hephaestus #1: T3.4 (Skill Registry)
Hephaestus #2: T4.1a, T4.1b, T4.1c, T4.2 (testing)
Sisyphus-Junior: T4.3, T4.4 (polish)
Oracle (parallel): Review ETGPO + EvoSkill architecture
```

---

## TDD Strategy

### Rule: Tests Before or Alongside Implementation

For each task, the agent MUST:
1. Write the test file FIRST (or in the same commit)
2. Run tests — they should FAIL
3. Implement the feature
4. Run tests — they should PASS
5. Commit with both test + implementation

### Test File Structure
```
tests/
├── test_learning/
│   ├── __init__.py
│   ├── test_self_learning.py      # T4.1a — SelfLearner + EventBus
│   ├── test_event_bus.py          # T4.1a — EventBus
│   ├── test_skill_lifecycle.py    # T4.1b — SkillLifecycleManager
│   ├── test_skill_proposer.py     # T4.1b — EvoSkill Proposer
│   ├── test_prompt_evolution.py   # T4.1c — PromptWizard
│   ├── test_etgpo.py              # T4.1c — ETGPO
│   ├── test_llm_judge.py          # T4.1c — LLM-as-a-Judge
│   └── test_signals.py            # T4.1a — Signals taxonomy
└── test_learning_integration.py   # T4.2 — End-to-end
```

### Acceptance Criteria (Agent-Executable)

| Deliverable | Verification Command | Expected Output |
|-------------|---------------------|-----------------|
| Singleton fix | `python3 -c "from src.learning import SelfLearner; a=SelfLearner(); b=SelfLearner(); assert a is b"` | Exit 0 |
| Persistent DB | `python3 -c "import sqlite3; conn=sqlite3.connect('data/learning.db'); tables=[r[0] for r in conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')]; assert 'patterns' in tables"` | Exit 0 |
| Health metrics | `python3 src/memory/daemon.py --health-check` | JSON with real metrics (not 100.0) |
| EventBus | `python3 -c "from src.learning.event_bus import EventBus; bus=EventBus(); bus.subscribe('test', lambda x: print(x)); bus.publish('test', 'hello')"` | Prints "hello" |
| Signals | `python3 -c "from src.learning.signals import Signal; s=Signal('reformulation', 0.7); assert s.weight == 0.7"` | Exit 0 |
| ETGPO | `python3 -c "from src.learning.etgpo import ETGPO; e=ETGPO(); result=e.optimize('test prompt', [{'input':'x','output':'y','error':'wrong'}]); assert 'guidance' in result"` | Exit 0 |
| LLM Judge | `python3 -c "from src.learning.llm_judge import LLMJudge; j=LLMJudge(); result=j.evaluate('question', 'answer', 'rubric'); assert 'score' in result"` | Exit 0 |
| All tests | `cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND && python3 -m pytest tests/test_learning/ -v --tb=short` | All pass, 80%+ coverage |
| Integration | `cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND && python3 -m pytest tests/test_learning_integration.py -v --tb=short` | All pass |

---

## Feature Flag Strategy

All new features are behind config flags in `config/learning.json` (create if doesn't exist):

```json
{
  "learning": {
    "event_bus": { "enabled": false },
    "signals": { "enabled": false },
    "etgpo": { "enabled": false, "max_iterations": 3 },
    "evoskill": { "enabled": false, "min_confidence": 0.7 },
    "llm_judge": { "enabled": false, "model": "default" },
    "skill_registry": { "enabled": false }
  }
}
```

**Rule**: All flags default to `false`. Features are enabled incrementally after testing.

---

## Risk Assessment (Updated)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **SQLite write contention** | Medium | High | WAL mode + connection pooling (T0.1) |
| **ETGPO complexity underestimated** | High | Medium | Oracle review before implementation; fallback to simpler error categorization |
| **EvoSkill proposal quality** | Medium | Medium | Start with rule-based proposals, add LLM later |
| **LLM Judge cost** | Medium | Low | Cache evaluations, use deterministic checks first |
| **Test coverage unrealistic** | High | Low | Target 80% not 100%; focus on critical paths |
| **Parallel Hephaestus conflicts** | Low | High | Each instance works on separate files; coordinate via commits |

---

## Execution Order (Ultrawork)

### Day 1: Wave 1 (Foundation)
1. **Morning**: Fire 3 Hephaestus instances for Tracks A, B, C
2. **Afternoon**: Verify all Wave 1 commits, run acceptance criteria
3. **Evening**: Oracle review of EventBus + Signals design

### Day 2: Wave 2 (Wiring + Features)
1. **Morning**: Fire 3 Hephaestus instances for Tracks A, B, C
2. **Afternoon**: Verify all Wave 2 commits, run acceptance criteria
3. **Evening**: Momus adversarial review of ETGPO + EvoSkill

### Day 3: Wave 3 (Integration + Polish)
1. **Morning**: Fire Hephaestus for Skill Registry + Testing, Sisyphus-Junior for polish
2. **Afternoon**: Run full test suite, integration tests, quality gates
3. **Evening**: Final verification, documentation review

---

## Quality Gates (MANDATORY before each wave completion)

```bash
# After Wave 1
python3 -m pytest tests/test_learning/ -v --tb=short  # Tests for bug fixes
bash bin/quality-gates/gate-1-py-typecheck.sh || echo "FIX TYPES"
bash bin/quality-gates/gate-2-py-lint.sh || echo "FIX LINT"

# After Wave 2
python3 -m pytest tests/test_learning/ -v --tb=short  # Tests for features
bash bin/quality-gates/gate-1-py-typecheck.sh || echo "FIX TYPES"
bash bin/quality-gates/gate-2-py-lint.sh || echo "FIX LINT"

# After Wave 3 (Final)
python3 -m pytest tests/test_learning/ tests/test_learning_integration.py -v --tb=short --cov=src/learning --cov-report=term-missing
bash bin/quality-gates/gate-1-py-typecheck.sh
bash bin/quality-gates/gate-2-py-lint.sh
bash bin/quality-gates/gate-5-secrets.sh
```

---

## Comparison: Original vs Optimized

| Metric | Original | Optimized | Improvement |
|--------|----------|-----------|-------------|
| Phases | 5 | 3 | -40% |
| Tasks | 25 | 19 | -24% |
| Total effort | 30 hrs | 27 hrs | -10% |
| Calendar time | 30 hrs | ~15 hrs | -50% |
| Parallelism | Sequential | 3 tracks/wave | 1.8x speedup |
| Test approach | Deferred (Phase 4) | TDD (per module) | Earlier bug detection |
| Agent diversity | Hephaestus-only | Hephaestus + Sisyphus-Junior + Oracle + Momus | Better resource use |
| Feature safety | Not specified | Feature flags | Safe incremental rollout |
| Acceptance criteria | Vague | Agent-executable commands | Zero manual verification |

---

*This optimized plan synthesizes insights from: Metis (plan optimization), Explore (codebase audit — 1456 lines of learning code, 0 tests), Librarian (external research — Mem0/Zep/Letta/ETGPO patterns). Total: 19 tasks across 3 waves, ~27 hours effort, ~15 hours calendar time with parallelism.*

# Masterplan: N-Xyme MIND ML Synthesis

> **Created:** 2026-05-17
> **Status:** Phase 0 — NOT STARTED
> **Total Scope:** 24 stories, 4 phases, 190 hours
> **Critical Path:** Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 (fully sequential)

---

## Dependency Graph

```
Phase 0: Foundation (7h)
    │
    ├── P0-1: Delete meta-observer.js
    ├── P0-2: Map archive structure
    ├── P0-3: Verify ChromaDB connectivity
    ├── P0-4: Verify nx_agents health
    └── P0-5: Create ml/ directory
    │
    ▼
Phase 1: Core Learning Engine (42h) ← BLOCKED on Phase 0
    │
    ├── P1-1: Port circuit_breaker.py → Rust
    ├── P1-2: Port intent_predictor.py → Rust
    ├── P1-3: Port delegation_learner.py → Rust
    ├── P1-4: Port agent_optimizer.py → Rust
    ├── P1-5: Port Q-Learning → Rust
    └── P1-6: Integrate with nx_agents MCP
    │
    ▼
Phase 2: Memory & Cognitive (46h) ← BLOCKED on Phase 1
    │
    ├── P2-1: Port tier_manager.py → Rust
    ├── P2-2: Port cognitive/forgetting.py → Rust
    ├── P2-3: Port cognitive/trust.py → Rust
    ├── P2-4: Port cognitive/priority.py → Rust
    ├── P2-5: Port sleep_engine.py → Rust
    ├── P2-6: Connect ChromaDB → Rust
    └── P2-7: Build session resume
    │
    ▼
Phase 3: Intelligence & Routing (42h) ← BLOCKED on Phase 2
    │
    ├── P3-1: Port predictive_router.py → Rust
    ├── P3-2: Port context_manager.py → Rust
    ├── P3-3: Port load_balancer.py → Rust
    ├── P3-4: Port ab_testing.py → Rust
    ├── P3-5: Build training trigger
    └── P3-6: Auto-inject memories
    │
    ▼
Phase 4: Advanced ML (60h) ← BLOCKED on Phase 3
    │
    ├── P4-1: Port Double DQN → Rust+PyTorch
    ├── P4-2: Port PromptWizard → Python
    ├── P4-3: Port Thompson Sampling → Rust
    ├── P4-4: Build A/B testing framework
    ├── P4-5: Build health monitoring
    └── P4-6: VRAM management
```

---

## Phase 0: Foundation (Week 1) — 7 hours

| ID | Story | Hours | Status | Blocker | Next Action |
|----|-------|-------|--------|---------|-------------|
| P0-1 | Verify `meta-observer.js` is dead — file is `.jsbroken`, confirm no opencode.json reference | 1h | 🔴 NOT STARTED | None | `grep meta-observer opencode.json`, verify agents can call tools |
| P0-2 | Map `archive/data_chaos/data_chaos/packages/` — 1,494 Python files across intelligence/, memory_core/, learning_engine/ | 2h | 🔴 NOT STARTED | None | Catalog by category, identify golden copies vs duplicates |
| P0-3 | Verify ChromaDB connectivity — 26GB store at `context/memory/file_chroma/`, use archive `.venv` (Python 3.14) | 2h | 🔴 NOT STARTED | Archive venv path | `archive/.../.venv/bin/python3 -c "import chromadb; ..."` |
| P0-4 | Verify nx_agents health — confirm all 32 MCP tools responding, MiniLM embeddings working | 1h | 🔴 NOT STARTED | None | Test MCP tool list, run embedding query |
| P0-5 | Create `ml/` directory — Rust crate structure for ported code | 1h | 🔴 NOT STARTED | None | `cargo new ml --lib`, add to workspace Cargo.toml |

**Phase 0 Gate:** All 5 stories complete → Phase 1 unlocked

---

## Phase 1: Core Learning Engine (Week 2-3) — 42 hours

| ID | Story | Source | Hours | Status | Blocker | Next Action |
|----|-------|--------|-------|--------|---------|-------------|
| P1-1 | Port `circuit_breaker.py` (364 lines) → Rust — failure isolation, trip/reset logic | `archive/.../circuit_breaker.py` | 4h | 🔴 NOT STARTED | Phase 0 complete | Read source, design Rust struct, implement state machine |
| P1-2 | Port `intent_predictor.py` (298 lines) → Rust — predict user intent from context | `archive/.../intent_predictor.py` | 6h | 🔴 NOT STARTED | Phase 0 complete | Read source, map features to Rust, implement prediction |
| P1-3 | Port `delegation_learner.py` (357 lines) → Rust — learn which agent handles what | `archive/.../delegation_learner.py` | 6h | 🔴 NOT STARTED | Phase 0 complete | Read source, extract learning logic, port to Rust |
| P1-4 | Port `agent_optimizer.py` (423 lines) → Rust — optimize agent performance over time | `archive/.../agent_optimizer.py` | 6h | 🔴 NOT STARTED | Phase 0 complete | Read source, port optimization algorithms |
| P1-5 | Port Q-Learning suite → Rust — `q_learning.py` (665), `double_dqn.py` (805), `bandits.py` (129) | `archive/.../q_learning.py` + 2 more | 12h | 🔴 NOT STARTED | Phase 0 complete | Read all 3 sources, design RL trait, implement Q-table + DQN |
| P1-6 | Integrate learning engine with nx_agents MCP — wire Rust crate as MCP extension | `services/nx-agents-mcp/` | 8h | 🔴 NOT STARTED | P1-1 through P1-5 complete | Add ml crate dependency, expose MCP tools, test end-to-end |

**Phase 1 Gate:** All 6 stories complete, learning engine responding to MCP calls → Phase 2 unlocked

---

## Phase 2: Memory & Cognitive (Week 4-5) — 46 hours

| ID | Story | Source | Hours | Status | Blocker | Next Action |
|----|-------|--------|-------|--------|---------|-------------|
| P2-1 | Port `tier_manager.py` → Rust — memory tier management (hot/warm/cold) | `archive/.../tier_manager.py` | 6h | 🔴 NOT STARTED | Phase 1 complete | Read source, port tier logic |
| P2-2 | Port `cognitive/forgetting.py` (371 lines) → Rust — decay, prune, consolidate | `archive/.../forgetting.py` | 6h | 🔴 NOT STARTED | Phase 1 complete | Read source, port decay algorithms |
| P2-3 | Port `cognitive/trust.py` (258 lines) → Rust — memory trust scoring | `archive/.../trust.py` | 4h | 🔴 NOT STARTED | Phase 1 complete | Read source, port trust model |
| P2-4 | Port `cognitive/priority.py` (611 lines) → Rust — memory priority ranking | `archive/.../priority.py` | 6h | 🔴 NOT STARTED | Phase 1 complete | Read source, port priority algorithms |
| P2-5 | Port `sleep_engine.py` (388 lines) → Rust — offline consolidation | `archive/.../sleep_engine.py` | 8h | 🔴 NOT STARTED | Phase 1 complete | Read source, port sleep/consolidation logic |
| P2-6 | Connect ChromaDB → Rust — Rust bindings to 27GB ChromaDB store | ChromaDB 19.69GB + 2.55GB | 8h | 🔴 NOT STARTED | Phase 1 complete, ChromaDB verified (P0-3) | Choose Rust ChromaDB client or FFI, test read/write |
| P2-7 | Build session resume — restore past context on new session | Multiple memory stores | 8h | 🔴 NOT STARTED | P2-1 through P2-6 complete | Design resume protocol, implement restore flow |

**Phase 2 Gate:** Memory system operational, session resume working → Phase 3 unlocked

---

## Phase 3: Intelligence & Routing (Week 6-7) — 42 hours

| ID | Story | Source | Hours | Status | Blocker | Next Action |
|----|-------|--------|-------|--------|---------|-------------|
| P3-1 | Port `predictive_router.py` (177 lines) → Rust — predict where requests should go | `archive/.../predictive_router.py` | 6h | 🔴 NOT STARTED | Phase 2 complete | Read source, port routing logic |
| P3-2 | Port `context_manager.py` (409 lines) → Rust — context window management | `archive/.../context_manager.py` | 6h | 🔴 NOT STARTED | Phase 2 complete | Read source, port context compaction |
| P3-3 | Port `load_balancer.py` (418 lines) → Rust — distribute load across agents | `archive/.../load_balancer.py` | 6h | 🔴 NOT STARTED | Phase 2 complete | Read source, port balancing algorithms |
| P3-4 | Port `ab_testing.py` (598 lines) → Rust — A/B test routing strategies | `archive/.../ab_testing.py` | 8h | 🔴 NOT STARTED | Phase 2 complete | Read source, port testing framework |
| P3-5 | Build training trigger — auto-trigger training at 100 corrections | New | 10h | 🔴 NOT STARTED | Phase 2 complete | Design trigger mechanism, wire to correction counter |
| P3-6 | Auto-inject memories — inject relevant memories before tool calls | New | 6h | 🔴 NOT STARTED | P3-1, P3-2 complete | Design injection protocol, implement pre-call hook |

**Phase 3 Gate:** Routing intelligent, training auto-triggering, memories auto-injecting → Phase 4 unlocked

---

## Phase 4: Advanced ML (Week 8-10) — 60 hours

| ID | Story | Source | Hours | Status | Blocker | Next Action |
|----|-------|--------|-------|--------|---------|-------------|
| P4-1 | Port Double DQN → Rust+PyTorch — advanced RL with PyTorch bindings | `archive/.../double_dqn.py` (805 lines) | 20h | 🔴 NOT STARTED | Phase 3 complete | Read source, design Rust+PyO3 bridge, implement DQN |
| P4-2 | Port PromptWizard → Python — `prompt_evolution.py` (677 lines), evolve prompts | `archive/.../prompt_evolution.py` | 12h | 🔴 NOT STARTED | Phase 3 complete | Read source, port PromptWizard class, test evolution |
| P4-3 | Port Thompson Sampling → Rust — `thompson_sampling.py` (737 lines) | `archive/.../thompson_sampling.py` | 8h | 🔴 NOT STARTED | Phase 3 complete | Read source, port Bayesian sampling |
| P4-4 | Build A/B testing framework — test routing strategies in production | New | 8h | 🔴 NOT STARTED | P3-4 complete | Design framework, implement traffic splitting |
| P4-5 | Build health monitoring — monitor ML system health, alert on degradation | `archive/.../health_monitor.py` (232 lines) | 6h | 🔴 NOT STARTED | Phase 3 complete | Read source, port monitoring, add alerting |
| P4-6 | VRAM management — manage GPU memory for inference engine | `archive/.../engine.cpp` (502 lines) | 6h | 🔴 NOT STARTED | Phase 3 complete | Review C++ engine, design VRAM management |

**Phase 4 Gate:** Full ML system operational, advanced ML running → PROJECT COMPLETE

---

## Critical Path Analysis

```
P0-1 → P0-2 → P0-3 → P0-4 → P0-5
                                    ↓
P1-1 → P1-2 → P1-3 → P1-4 → P1-5 → P1-6
                                        ↓
P2-1 → P2-2 → P2-3 → P2-4 → P2-5 → P2-6 → P2-7
                                                ↓
P3-1 → P3-2 → P3-3 → P3-4 → P3-5 → P3-6
                                        ↓
P4-1 → P4-2 → P4-3 → P4-4 → P4-5 → P4-6
```

**Critical path is FULLY SEQUENTIAL.** No phase can start until the previous phase is complete.

**Within phases, some parallelism exists:**
- Phase 1: P1-1 through P1-5 can run in parallel (all depend only on Phase 0). P1-6 waits for all 5.
- Phase 2: P2-1 through P2-5 can run in parallel. P2-6 depends on P0-3 (ChromaDB verified). P2-7 waits for all.
- Phase 3: P3-1 through P3-4 can run in parallel. P3-5 is independent. P3-6 waits for P3-1, P3-2.
- Phase 4: P4-1, P4-2, P4-3 can run in parallel. P4-4 waits for P3-4. P4-5, P4-6 are independent.

**Minimum wall-clock time with full parallelism within phases:**
- Phase 0: 7h (sequential — must verify system state first)
- Phase 1: 20h (P1-1..P1-5 parallel = max 12h, then P1-6 = 8h)
- Phase 2: 22h (P2-1..P2-6 parallel = max 8h, then P2-7 = 8h, but P2-6 needs P0-3)
- Phase 3: 20h (P3-1..P3-4 parallel = max 8h, P3-5 = 10h, P3-6 = 6h after P3-1/P3-2)
- Phase 4: 26h (P4-1..P4-3 parallel = max 20h, P4-4..P4-6 parallel = max 8h)
- **Total wall-clock: ~95 hours** (vs 190 hours fully sequential)

---

## Top 3 Blockers (Must Address NOW)

### 🔴 BLOCKER 1: meta-observer.js — STATUS: Already neutralized
- **Impact:** Was blocking ALL tool calls for ALL agents.
- **Current state:** File is `.opencode/plugins/meta-observer.jsbroken` (renamed, inactive).
- **Action:** Verify no reference remains in `opencode.json`. If clean, mark P0-1 as 🟢.
- **Risk if ignored:** Could be reactivated if renamed back.

### 🔴 BLOCKER 2: ChromaDB 26GB — needs verification with correct Python env
- **Impact:** If ChromaDB is unreadable, entire memory system (Phase 2) is blocked.
- **Current state:** 26GB store at `archive/data_chaos/data_chaos/context/memory/file_chroma/`. ChromaDB is in archive's `.venv` (Python 3.14), NOT system Python.
- **Fix:** Run connectivity test using archive venv (P0-3) before committing to any memory work.
- **Risk if ignored:** 46 hours of Phase 2 work wasted if store is corrupt.

### 🟡 BLOCKER 3: No `ml/` Rust crate exists yet
- **Impact:** Cannot start any Rust porting work (Phase 1-4). Workspace has only `nx-agents-mcp` and `minilm`.
- **Fix:** Create crate structure (P0-5). Add to workspace Cargo.toml. Set up CI.
- **Risk if ignored:** All 150+ hours of porting work has nowhere to go.

---

## Progress Tracking System

### Status Legend
| Symbol | Meaning |
|--------|---------|
| 🔴 | NOT STARTED |
| 🟡 | IN PROGRESS |
| 🟢 | COMPLETE |
| ⚫ | BLOCKED |
| ⏭️ | SKIPPED |

### Completion Criteria per Story
Each story is **COMPLETE** only when:
1. Code is written and compiles (`cargo build` or `python -m py_compile`)
2. Tests pass (unit tests for the ported module)
3. Integration test passes (works with nx_agents MCP or relevant system)
4. Code is committed to the `ml/` crate or appropriate location

### Progress Metrics
| Metric | Target | Current |
|--------|--------|---------|
| Stories complete | 24 | 0 |
| Phases complete | 4 | 0 |
| Hours invested | 190 | 0 |
| Routing accuracy improvement | +20-30% | N/A |
| Session context restore | Working | N/A |
| Memory auto-injection | Working | N/A |
| Circuit breaker isolation | Working | N/A |
| Training auto-trigger | Working | N/A |

---

## First 5 Actions (Do RIGHT NOW)

### Action 1: Verify meta-observer.js status (P0-1)
```bash
# Already found: .opencode/plugins/meta-observer.jsbroken (renamed, not active)
# Verify no active meta-observer is loaded
ls -la .opencode/plugins/meta-observer*  # .jsbroken = inactive
# Check opencode.json for plugin references
grep -i "meta-observer" opencode.json
```

### Action 2: Archive inventory (P0-2 start)
```bash
# Verified: 1,494 Python files in packages/
# Key source path: archive/data_chaos/data_chaos/packages/
# Categories: intelligence/, memory_core/, learning_engine/, infrastructure/
find archive/data_chaos/data_chaos/packages -name "*.py" | wc -l  # 1,494
```

### Action 3: ChromaDB smoke test (P0-3 start)
```bash
# Verified: 26GB store at archive/data_chaos/data_chaos/context/memory/file_chroma/
# ChromaDB is in the archive's .venv (Python 3.14), NOT system Python
# Use the archive venv:
archive/data_chaos/data_chaos/.venv/bin/python3 -c "
import chromadb
client = chromadb.PersistentClient(path='archive/data_chaos/data_chaos/context/memory/file_chroma/')
print('Collections:', client.list_collections())
"
```

### Action 4: nx_agents health check (P0-4)
```bash
# Workspace members: services/nx-agents-mcp, services/minilm
# Check if they build:
cargo check -p nx-agents-mcp -p minilm
# Check MCP tools:
ls services/nx-agents-mcp/src/tools/
```

### Action 5: Create ml/ crate (P0-5)
```bash
# Create the Rust crate
cargo new ml --lib
# Add to workspace in Cargo.toml:
# Change: members = ["services/nx-agents-mcp", "services/minilm"]
# To:     members = ["services/nx-agents-mcp", "services/minilm", "ml"]
# Set up initial structure:
# ml/src/lib.rs
# ml/src/circuit_breaker.rs
# ml/src/intent_predictor.rs
# ml/Cargo.toml (with dependencies)
```

---

## Sprint Status Tracking

| Phase | Stories | Complete | In Progress | Blocked | Not Started | % Done |
|-------|---------|----------|-------------|---------|-------------|--------|
| Phase 0: Foundation | 5 | 0 | 0 | 0 | 5 | 0% |
| Phase 1: Core Learning | 6 | 0 | 0 | 0 | 6 | 0% |
| Phase 2: Memory & Cognitive | 7 | 0 | 0 | 0 | 7 | 0% |
| Phase 3: Intelligence & Routing | 6 | 0 | 0 | 0 | 6 | 0% |
| Phase 4: Advanced ML | 6 | 0 | 0 | 0 | 6 | 0% |
| **TOTAL** | **30** | **0** | **0** | **0** | **30** | **0%** |

> Note: 30 stories (not 24) — the plan description said 24 but the detailed breakdown has 30. This is the accurate count from the detailed story list.

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| ChromaDB 27GB corrupted | Medium | Critical | P0-3 verification before Phase 2. Backup before testing. |
| Free model rate limits halt progress | High | High | Cache embeddings. Batch operations. Use local MiniLM. |
| Context window exhaustion | Medium | Medium | Use compact context manager (P3-2). Summarize aggressively. |
| Archive data loss during consolidation | Low | Critical | NEVER delete archive until ported and verified. Copy, don't move. |
| Plugin isolation requires forking OpenCode | Medium | High | Test circuit breaker in isolation first (P1-1). Fork only if needed. |
| Rust+PyTorch bridge complexity (P4-1) | High | High | Start with pure Rust DQN. Add PyTorch only if needed. |
| Scope creep from "while we're here" fixes | High | Medium | Strict gate enforcement. No story starts until phase gate passed. |

---

## Next Session Checklist

- [ ] Run Action 1: Delete meta-observer.js
- [ ] Run Action 2: Archive inventory
- [ ] Run Action 3: ChromaDB smoke test
- [ ] Run Action 4: nx_agents health check
- [ ] Run Action 5: Create ml/ crate
- [ ] Update this file with Phase 0 results
- [ ] Mark P0-* stories as 🟢 or ⚫ based on results

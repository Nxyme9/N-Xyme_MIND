# N-Xyme_MIND Masterplan — Phase 5-7 (Revised)

> Created: 2026-04-06 | Revised: 2026-04-06 | Oracle: CONDITIONAL PASS | Momus: REJECT
> Status: Phases 0-4 Complete | Next: Wave 1 Implementation

---

## Current State

### ✅ Completed (Phases 0-4)
- **Phase 0**: Critical bug fixes (stdlib shadowing, broken imports, persistence bugs)
- **Phase 1**: Core integration (typed ABCs, migrations, hybrid search + RRF fusion)
- **Phase 2**: Learning-memory bridge (MemoryManager, OutcomeLogger, SessionHooks, EWC+Q-Learning)
- **Phase 3**: Advanced features (adaptive priority, Neo4j driver, MMR, reranker stubs)
- **Phase 4**: Validation (18/18 modules import, MCPs compile, outcome_logger bug fixed)

### 🔴 Critical Issues (Oracle + Momus Consensus)
1. **MemoryRouter is a stub** — Zero routing logic, returns empty results
2. **Q-Learning never receives rewards** — "Learning" is fictional, OutcomeLogger never connected
3. **No end-to-end pipeline** — Components exist but don't communicate
4. **CrossEncoderReranker is a stub** — Falls back to score sorting
5. **Race conditions in MemoryManager** — Multiple SQLite connections, no locking
6. **SQLite no resilience** — No backup, no integrity checks, no WAL checkpoint

### 🟠 Moderate Issues
7. Type inconsistencies: `rrf_fusion()` expects `List[List[dict]]` but pipeline passes `MemoryRecord`
8. EWC integration superficial — Fisher info trivial, optimal params don't persist
9. Conflict detection is O(n) full table scan — won't scale
10. Hardcoded paths, no validation, no graceful degradation

---

## Revised Phase 5: Critical Integration (P0 — Must Fix)

### T5.1: Implement MemoryRouter (REPLACES stub)
**Priority**: P0 | **Complexity**: L4 | **Agent**: `hephaestus`
**Files**: `packages/memory_core/router.py`
**Dependencies**: All retrievers, Q-Learning engine

**Requirements**:
- Read existing `TEMPRRetriever`, `KeywordRetriever`, `VectorStore` interfaces
- Implement `search(query)` that routes to optimal retriever based on query analysis
- Use query characteristics (length, keywords, filters) to select retriever
- Integrate with Q-Learning: call `select_action()` for routing decisions
- Return `SearchResults` with actual data, not stub empty results
- Must handle: semantic queries, keyword queries, filtered queries, hybrid queries

**Success Criteria**:
- `MemoryRouter.search()` returns non-empty results for real queries
- Routes to at least 2 different retrievers based on query type
- Q-Learning `select_action()` is called during routing

---

### T5.2: Wire OutcomeLogger → Q-Learning (CRITICAL FIX)
**Priority**: P0 | **Complexity**: L4 | **Agent**: `hephaestus`
**Files**: `packages/learning_engine/routing/adaptive_router.py` (new)
**Dependencies**: OutcomeLogger, QLearningEngine, MemoryRouter

**Requirements**:
- Create `AdaptiveRouter` that wraps `MemoryRouter`
- After each routing decision, log outcome via `OutcomeLogger`
- Convert outcome to reward signal: success=True → +1, success=False → -1
- Call `QLearningEngine.update(state, action, reward)` with actual rewards
- Implement reward computation: latency-based, success-based, quality-based
- Store routing history for analysis

**Success Criteria**:
- `AdaptiveRouter.route(query)` calls MemoryRouter, logs outcome, updates Q-Learning
- Q-Learning engine receives real rewards from real routing decisions
- `get_all_agent_stats()` shows learning improvement over time

---

### T5.3: Create End-to-End Retrieval Pipeline
**Priority**: P0 | **Complexity**: L4 | **Agent**: `hephaestus`
**Files**: `packages/memory_core/retrievers/pipeline.py` (new)
**Dependencies**: TEMPRRetriever, MMR, CrossEncoderReranker (or fallback)

**Requirements**:
- Implement `RetrievalPipeline` class with stages:
  1. **Query Analysis**: Determine query type (semantic, keyword, hybrid)
  2. **Retrieve**: Call appropriate retriever(s) via TEMPRRetriever
  3. **RRF Fusion**: Combine results from multiple sources
  4. **MMR Rerank**: Apply diversity scoring
  5. **Cross-Encoder Rerank**: If available, otherwise skip gracefully
  6. **Return**: Top-k results with scores
- Handle errors gracefully at each stage (no single point of failure)
- Log pipeline metrics (latency per stage, result counts)

**Success Criteria**:
- `RetrievalPipeline.execute(query)` returns ranked results
- Each stage can fail independently without crashing pipeline
- Pipeline logs metrics for each stage

---

### T5.4: Fix Race Conditions + SQLite Resilience
**Priority**: P1 | **Complexity**: L3 | **Agent**: `hephaestus`
**Files**: `packages/memory_core/memory_manager.py`, `packages/memory_core/stores/relational_store.py`

**Requirements**:
- Add `threading.Lock()` to MemoryManager for concurrent access
- Use single SQLite connection per MemoryManager instance (not multiple)
- Add `PRAGMA integrity_check` on init
- Add `PRAGMA wal_checkpoint(TRUNCATE)` on shutdown
- Wrap multi-operation sequences in transactions
- Add backup mechanism for critical DBs

**Success Criteria**:
- No race conditions under concurrent access
- SQLite integrity check passes on init
- Graceful degradation if DB corrupts

---

### T5.5: Expose MCP Tools
**Priority**: P1 | **Complexity**: L3 | **Agent**: `hephaestus`
**Files**: `packages/memory_core/mcp_server.py`, `packages/learning_engine/mcp_server.py`

**Requirements**:
- Add MCP tools: `memory_search`, `memory_write`, `memory_stats`, `learning_stats`, `log_outcome`
- Each tool must call the underlying Python API
- Return structured JSON responses
- Handle errors gracefully

**Success Criteria**:
- All 5 MCP tools respond correctly
- Tools return real data, not stubs

---

## Phase 6: Testing & Quality (P2)

### T6.1: Integration Tests
**Priority**: P2 | **Complexity**: L3 | **Agent**: `hephaestus`
**Files**: `tests/integration/test_memory_pipeline.py`

### T6.2: Unit Tests
**Priority**: P2 | **Complexity**: L2 | **Agent**: `sisyphus-junior`
**Files**: `tests/unit/test_router.py`, `tests/unit/test_pipeline.py`

### T6.3: Performance Benchmarks
**Priority**: P2 | **Complexity**: L3 | **Agent**: `hephaestus`
**Files**: `scripts/benchmark_retrieval.py`

---

## Phase 7: Production Readiness (P3)

### T7.1: Configuration Management
**Priority**: P3 | **Complexity**: L3 | **Agent**: `hephaestus`

### T7.2: Health Monitoring
**Priority**: P3 | **Complexity**: L3 | **Agent**: `hephaestus`

### T7.3: Documentation
**Priority**: P3 | **Complexity**: L2 | **Agent**: `writing` category

---

## Optimal Delegation Chain (Revised)

```
Sisyphus (Orchestrator)
    ↓
┌─────────────────────────────────────────────────────────────┐
│ WAVE 1 (P0 — CRITICAL, Parallel)                           │
├─────────────────────────────────────────────────────────────┤
│ T5.1: MemoryRouter (hephaestus) ← Independent              │
│ T5.2: Adaptive Router (hephaestus) ← Independent           │
│ T5.3: Retrieval Pipeline (hephaestus) ← Independent        │
└─────────────────────────────────────────────────────────────┘
    ↓ (Verify Wave 1)
┌─────────────────────────────────────────────────────────────┐
│ WAVE 2 (P1 — Important, Parallel)                          │
├─────────────────────────────────────────────────────────────┤
│ T5.4: Race Conditions + SQLite (hephaestus) ← Needs Wave 1 │
│ T5.5: MCP Tools (hephaestus) ← Needs T5.1, T5.3            │
└─────────────────────────────────────────────────────────────┘
    ↓ (Verify Wave 2)
┌─────────────────────────────────────────────────────────────┐
│ WAVE 3 (P2 — Testing, Parallel)                            │
├─────────────────────────────────────────────────────────────┤
│ T6.1: Integration Tests (hephaestus) ← Needs Wave 2        │
│ T6.2: Unit Tests (sisyphus-junior) ← Needs T5.1, T5.2      │
│ T6.3: Benchmarks (hephaestus) ← Needs Wave 2               │
└─────────────────────────────────────────────────────────────┘
    ↓ (Verify Wave 3)
┌─────────────────────────────────────────────────────────────┐
│ WAVE 4 (P3 — Production, Parallel)                         │
├─────────────────────────────────────────────────────────────┤
│ T7.1: Config (hephaestus) ← Independent                    │
│ T7.2: Health (hephaestus) ← Independent                    │
│ T7.3: Documentation (writing) ← Needs everything           │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ FINAL: Oracle Review → Momus Review → Commit               │
└─────────────────────────────────────────────────────────────┘
```

---

## Execution Strategy

### Wave 1 Delegation Prompts (Ready to Fire)

Each delegation includes the 6 required sections: TASK, EXPECTED OUTCOME, REQUIRED TOOLS, MUST DO, MUST NOT DO, CONTEXT.

### Risk Assessment (Updated)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Q-Learning doesn't converge | High | High | Start with simple +1/-1 rewards |
| Race conditions hard to reproduce | Medium | High | Use threading.Lock, test with concurrent writes |
| Integration complexity | High | High | Delegate with crystal-clear specs |
| SQLite corruption | Low | Critical | Add integrity checks, backup mechanism |

---

## Success Criteria (Revised)

- [ ] MemoryRouter routes queries to optimal retriever (NOT stub)
- [ ] Q-Learning receives real rewards from OutcomeLogger
- [ ] End-to-end pipeline: query → retrieve → rerank → learn
- [ ] No race conditions under concurrent access
- [ ] SQLite integrity check passes
- [ ] MCP tools expose all operations
- [ ] Integration tests pass
- [ ] Benchmarks show <100ms retrieval latency
- [ ] Oracle + Momus review pass (both must pass this time)

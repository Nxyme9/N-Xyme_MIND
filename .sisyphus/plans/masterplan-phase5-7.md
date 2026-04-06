# N-Xyme_MIND Masterplan — Remaining Work & Optimal Delegation Chain

> Created: 2026-04-06 | Status: Phases 0-4 Complete | Next: Integration & Production

---

## Current State

### ✅ Completed (Phases 0-4)
- **Phase 0**: Critical bug fixes (stdlib shadowing, broken imports, persistence bugs)
- **Phase 1**: Core integration (typed ABCs, migrations, hybrid search + RRF fusion)
- **Phase 2**: Learning-memory bridge (MemoryManager, OutcomeLogger, SessionHooks, EWC+Q-Learning)
- **Phase 3**: Advanced features (adaptive priority, Neo4j driver, MMR, reranker stubs)
- **Phase 4**: Validation (18/18 modules import, MCPs compile, outcome_logger bug fixed)

### ⚠️ Known Issues
1. `MemoryRouter` is a stub — no actual routing logic
2. `CrossEncoderReranker` is a stub — no implementation
3. No integration tests (only import checks)
4. No end-to-end pipeline: query → retrieve → rerank → learn
5. Learning engine not connected to routing decisions in real-time
6. No MCP tools exposed for memory/learning operations
7. No configuration management for all the new components

---

## Phase 5: Integration Pipeline (L4 Complexity)

### T5.1: Wire End-to-End Retrieval Pipeline
**Goal**: Query → Retrieve (hybrid) → Rerank (MMR) → Return results
**Files**: `memory_core/retrievers/pipeline.py` (new)
**Dependencies**: TEMPRRetriever, MMR, CrossEncoderReranker
**Agent**: `hephaestus` (L4 — multi-file, requires architecture)

### T5.2: Implement MemoryRouter
**Goal**: Route queries to optimal retriever based on query type
**Files**: `memory_core/router.py` (replace stub)
**Dependencies**: All retrievers, learning engine for routing decisions
**Agent**: `hephaestus` (L4 — requires Q-Learning integration)

### T5.3: Connect Learning Engine to Routing
**Goal**: Use Q-Learning outcomes to improve routing decisions
**Files**: `learning_engine/routing/adaptive_router.py` (new)
**Dependencies**: Q-Learning engine, OutcomeLogger, MemoryRouter
**Agent**: `hephaestus` (L4 — RL integration)

### T5.4: Expose MCP Tools
**Goal**: Create MCP tools for memory search, learning stats, outcome logging
**Files**: `memory_core/mcp_server.py` (extend), `learning_engine/mcp_server.py` (extend)
**Dependencies**: MemoryManager, OutcomeLogger, MemoryRouter
**Agent**: `hephaestus` (L3 — tool exposure)

---

## Phase 6: Testing & Quality (L3 Complexity)

### T6.1: Integration Tests
**Goal**: Test full pipeline: write memory → search → retrieve → learn
**Files**: `tests/integration/test_memory_pipeline.py` (new)
**Agent**: `hephaestus` (L3 — test writing)

### T6.2: Unit Tests for New Components
**Goal**: Test MemoryRouter, adaptive router, pipeline
**Files**: `tests/unit/test_router.py`, `tests/unit/test_pipeline.py` (new)
**Agent**: `sisyphus-junior` (L2 — straightforward test generation)

### T6.3: Performance Benchmarks
**Goal**: Benchmark retrieval latency, memory usage, learning convergence
**Files**: `scripts/benchmark_retrieval.py` (extend)
**Agent**: `hephaestus` (L3 — benchmarking)

---

## Phase 7: Production Readiness (L4 Complexity)

### T7.1: Configuration Management
**Goal**: Centralized config for all components (thresholds, weights, paths)
**Files**: `memory_core/config.py` (extend), `learning_engine/config.py` (new)
**Agent**: `hephaestus` (L3 — config management)

### T7.2: Health Monitoring
**Goal**: Health checks for memory stores, learning engine, MCP servers
**Files**: `memory_core/health.py` (new)
**Agent**: `hephaestus` (L3 — monitoring)

### T7.3: Documentation
**Goal**: API docs, architecture diagrams, usage examples
**Files**: `docs/memory-learning-architecture.md` (new)
**Agent**: `writing` category (L2 — documentation)

---

## Optimal Delegation Chain

```
User Request: "Finish the learning system"
    ↓
Sisyphus (Orchestrator)
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Wave 1 (Parallel - Independent)                            │
├─────────────────────────────────────────────────────────────┤
│ T5.1: Pipeline (hephaestus) ← Can start immediately        │
│ T5.2: MemoryRouter (hephaestus) ← Can start immediately    │
│ T5.4: MCP Tools (hephaestus) ← Can start immediately       │
└─────────────────────────────────────────────────────────────┘
    ↓ (wait for Wave 1)
┌─────────────────────────────────────────────────────────────┐
│ Wave 2 (Parallel - Depends on Wave 1)                      │
├─────────────────────────────────────────────────────────────┤
│ T5.3: Adaptive Router (hephaestus) ← Needs T5.1 + T5.2     │
│ T6.1: Integration Tests (hephaestus) ← Needs T5.1-T5.4     │
└─────────────────────────────────────────────────────────────┘
    ↓ (wait for Wave 2)
┌─────────────────────────────────────────────────────────────┐
│ Wave 3 (Parallel)                                          │
├─────────────────────────────────────────────────────────────┤
│ T6.2: Unit Tests (sisyphus-junior) ← Needs T5.2, T5.3      │
│ T6.3: Benchmarks (hephaestus) ← Needs T5.1-T5.4            │
│ T7.1: Config (hephaestus) ← Independent                    │
│ T7.2: Health (hephaestus) ← Independent                    │
└─────────────────────────────────────────────────────────────┘
    ↓ (wait for Wave 3)
┌─────────────────────────────────────────────────────────────┐
│ Wave 4 (Final)                                             │
├─────────────────────────────────────────────────────────────┤
│ T7.3: Documentation (writing category) ← Needs everything  │
│ Oracle Review → Momus Review → Commit                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Execution Strategy

### Immediate Next Steps (This Session)
1. **Commit current changes** — Save all Phase 0-4 work
2. **Start Wave 1** — Delegate T5.1, T5.2, T5.4 in parallel
3. **Wait for completion** → Verify → Wave 2

### Key Constraints
- **No type suppression** — All code must type-check
- **Match existing patterns** — Follow codebase conventions
- **Quality gates** — Run before marking any phase complete
- **No commits** — Until explicitly requested

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Q-Learning doesn't converge | Medium | High | Start with simple reward signals |
| MCP tool conflicts | Low | Medium | Test each tool independently |
| Performance degradation | Medium | Medium | Benchmark before/after each change |
| Integration complexity | High | High | Delegate to hephaestus with clear specs |

---

## Success Criteria

- [ ] End-to-end pipeline: query → retrieve → rerank → learn
- [ ] MemoryRouter routes queries to optimal retriever
- [ ] Learning engine improves routing over time
- [ ] MCP tools expose all memory/learning operations
- [ ] Integration tests pass
- [ ] Benchmarks show <100ms retrieval latency
- [ ] Documentation complete
- [ ] Oracle + Momus review pass

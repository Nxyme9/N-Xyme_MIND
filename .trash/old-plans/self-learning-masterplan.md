# Master Plan: Self-Learning Memory System

## Mission
Transform the N-Xyme memory system from a passive storage/retrieval system into a truly self-learning system that:
- Learns from user behavior (implicit feedback, query patterns)
- Consolidates and prunes knowledge automatically
- Adapts retrieval strategies based on what works
- Detects topic drift and reprioritizes indexing
- Forgets stale information to prevent bloat

## Current State
| Module | Learning Capability | Limitation |
|--------|-------------------|------------|
| `priority_engine.py` | Weight adaptation (+/- 0.05 per cycle) | Only adjusts file type weights, no query learning |
| `procedural.py` | Production rules with success/failure tracking | No integration with memory system |
| `enhancements.py` | Static importance scoring | No learning, hardcoded weights |

## Architecture: Self-Learning Loop

```
┌─────────────────────────────────────────────────────────────┐
│                    SELF-LEARNING LOOP                       │
│                                                             │
│  ┌──────────┐    ┌───────────┐    ┌──────────────────┐    │
│  │ OBSERVE  │───▶│  LEARN    │───▶│     ADAPT        │    │
│  │          │    │           │    │                  │    │
│  │ • Queries│    │ • Patterns│    │ • Re-rank        │    │
│  │ • Clicks │    │ • Feedback│    │ • Consolidate    │    │
│  │ • Usage  │    │ • Models  │    │ • Forget         │    │
│  │ • Errors │    │ • Rules   │    │ • Pre-compute    │    │
│  └──────────┘    └───────────┘    └──────────────────┘    │
│        ▲                                     │              │
│        └─────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Waves

### Wave 1: Foundation (2 tasks, parallel)
**Goal**: Core infrastructure for tracking and learning

| Task | File | Description | Agent | Dependencies |
|------|------|-------------|-------|--------------|
| T1.1 | `src/memory/feedback_tracker.py` | Track implicit feedback from search results (which results users use/click) | hephaestus | None |
| T1.2 | `src/memory/query_learner.py` | Learn common query patterns, pre-compute frequent results | hephaestus | None |

**Acceptance Criteria**:
- [ ] `feedback_tracker.py` records result interactions (query, result_id, used/not_used)
- [ ] `query_learner.py` identifies top 100 frequent queries and caches results
- [ ] Both modules persist data to SQLite
- [ ] Integration tests pass

### Wave 2: Knowledge Management (3 tasks, sequential)
**Goal**: Consolidate, prune, and forget knowledge

| Task | File | Description | Agent | Dependencies |
|------|------|-------------|-------|--------------|
| T2.1 | `src/memory/knowledge_consolidator.py` | Merge duplicate entities, resolve conflicts, prune stale knowledge | hephaestus | T1.1 |
| T2.2 | `src/memory/forgetting_engine.py` | Archive low-importance old memories, implement decay curves | hephaestus | T2.1 |
| T2.3 | `src/memory/driftdetector.py` | Detect topic shifts, reprioritize indexing based on current focus | hephaestus | T2.2 |

**Acceptance Criteria**:
- [ ] Consolidator merges entities with >80% similarity
- [ ] Forgetting engine archives memories older than threshold with low importance
- [ ] Drift detector identifies topic shifts and triggers re-prioritization
- [ ] All modules integrate with existing knowledge_graph.py

### Wave 3: Strategy Learning (2 tasks, parallel)
**Goal**: Learn optimal retrieval strategies

| Task | File | Description | Agent | Dependencies |
|------|------|-------------|-------|--------------|
| T3.1 | `src/memory/strategy_optimizer.py` | Learn which retrieval methods work best for which query types | hephaestus | T1.1, T1.2 |
| T3.2 | `src/memory/preference_model.py` | Learn user preferences for result types (code vs docs vs configs) | hephaestus | T1.1 |

**Acceptance Criteria**:
- [ ] Strategy optimizer tracks retrieval method success per query type
- [ ] Preference model learns user's result type preferences over time
- [ ] Both modules adapt router behavior based on learned patterns
- [ ] Integration tests show improved result relevance

### Wave 4: Integration & Testing (3 tasks, sequential)
**Goal**: Integrate all learning modules into daemon, test end-to-end

| Task | File | Description | Agent | Dependencies |
|------|------|-------------|-------|--------------|
| T4.1 | `src/memory/learning_orchestrator.py` | Orchestrates all learning modules, runs learning cycles | hephaestus | T2.3, T3.1, T3.2 |
| T4.2 | `src/memory/learning_integration.py` | Integrates learning modules into existing daemon and router | hephaestus | T4.1 |
| T4.3 | `tests/test_self_learning.py` | Comprehensive test suite for all self-learning modules | hephaestus | T4.2 |

**Acceptance Criteria**:
- [ ] Learning orchestrator runs all modules in correct order
- [ ] Daemon integrates learning cycles (runs every 30 minutes)
- [ ] Router uses learned strategies for result ranking
- [ ] All tests pass (50+ test cases)
- [ ] End-to-end test shows measurable improvement in result relevance

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Storage | SQLite (existing DB) | Reuse existing infrastructure, no new dependencies |
| Learning Algorithm | Heuristic-based + simple statistics | No ML dependencies, interpretable, fast |
| Feedback Collection | Implicit (result usage tracking) | No UI changes needed, passive collection |
| Consolidation Threshold | 80% similarity | Balance between merging duplicates and over-merging |
| Forgetting Threshold | 90 days + low importance | Prevents losing important recent memories |
| Learning Cycle | Every 30 minutes | Balance between freshness and resource usage |
| Strategy Tracking | Per-query-type success rates | Granular enough to be useful, not too noisy |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Learning degrades result quality | A/B testing framework, rollback to baseline |
| Memory bloat from learning data | Strict TTL on feedback data, periodic cleanup |
| Over-consolidation loses knowledge | Conservative merge threshold, manual review option |
| Forgetting important memories | Importance-based retention, never forget high-importance |
| Learning cycles impact performance | Run in background thread, resource limits |
| Circular dependencies between modules | Clear dependency graph, no circular imports |

## Execution Order

```
Wave 1 (Parallel) → Wave 2 (Sequential) → Wave 3 (Parallel) → Wave 4 (Sequential)
     T1.1, T1.2           T2.1 → T2.2 → T2.3        T3.1, T3.2        T4.1 → T4.2 → T4.3
```

**Total Tasks**: 10
**Estimated Time**: 8-12 person-days
**Critical Path**: T1 → T2 → T3 → T4 (sequential waves)

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Result relevance improvement | +30% | User feedback tracking |
| Query response time (cached) | <100ms | Benchmark suite |
| Knowledge graph quality | <5% duplicates | Consolidation metrics |
| Memory usage growth | <10% per month | Monitoring |
| Learning cycle duration | <30 seconds | Timing logs |
| Forgetting accuracy | <1% important memories lost | Audit trail |

## Agent Delegation Strategy

| Task Type | Agent | Why |
|-----------|-------|-----|
| Implementation | hephaestus | Code writing, follows patterns |
| Architecture review | oracle | Validates design decisions |
| Testing | hephaestus | Test writing, follows patterns |
| Integration | hephaestus | System integration work |

**Delegation Pattern**: Each task delegated to hephaestus with detailed prompt including:
1. TASK: Atomic goal
2. EXPECTED OUTCOME: Concrete deliverables
3. REQUIRED TOOLS: Read, Edit, Bash
4. MUST DO: Step-by-step requirements
5. MUST NOT DO: Forbidden actions
6. CONTEXT: File paths, existing patterns

## Quality Gates

Each task must pass:
1. `lsp_diagnostics` clean on changed files
2. Import test passes
3. Unit tests pass
4. Integration test passes (for Wave 4)
5. No new dependencies added
6. No modification to existing files (except integration tasks)

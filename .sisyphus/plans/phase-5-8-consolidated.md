# Phases 5-8: Cross-Session Transfer, Prompt Evolution, Bayesian Confidence, Integration

> **Date:** 2026-04-08
> **Total Effort:** ~16 days
> **Risk:** MEDIUM-HIGH

---

## Phase 5: Cross-Session Transfer (5-7 days)

### Oracle Recommendation
Split into two sprints: Tasks 5.1-5.2 first (2 days), defer 5.3-5.4 to Phase 7+.

### Task 5.1: Knowledge Graph
- Replace JSON storage with Neo4j graph nodes
- 5 knowledge types: decision, lesson, pattern, principle, anti-pattern
- Edges: derived_from, similar_to, contradicts, supports

### Task 5.2: Transferability Scoring
- Embedding-based similarity (not keyword overlap)
- Formula: `0.35 * generalizability + 0.35 * outcome_weight + 0.15 * repetition + 0.15 * cross_session_validation`

### Task 5.3: Session Injection (deferred)
- Tiered: Level 1 (top 3 critical), Level 2 (top 5 contextual), Level 3 (archive)

### Task 5.4: EWC Integration (deferred)
- Depends on Phase 3 MAML/EWC stability

---

## Phase 6: Prompt Evolution (3-4 days)

### Key Research Finding: GEPA (ICLR 2026 Oral)
- 35x fewer rollouts than RL
- 90x cheaper than Claude Opus
- Uses LLM reflection instead of scalar rewards

### Task 6.1: Outcome-Linked Scoring
- Link prompt versions to actual delegation outcomes
- Composite: `0.60 * success_rate + 0.25 * (1 if latency < 5s else 0.5) + 0.15 * min(total/50, 1.0)`

### Task 6.2: LLM Refinement
- Hybrid: use LLM only when heuristic plateaus (saves 70% cost)
- Complexity threshold > 0.7 → LLM, else heuristic

### Task 6.3: A/B Testing
- Z-test with power calculation
- Minimum 100 samples per variant
- α = 0.05, power = 0.80

### Task 6.4: Prompt Registry
- Version tracking, deprecation, rollback (keep last 3 versions)

---

## Phase 7: Bayesian Confidence (3-4 days)

### Task 7.1: Bayesian Confidence Estimator
- Beta distribution: `Beta(α + successes, β + failures)`
- Thompson sampling for exploration
- Credible intervals for confidence

### Task 7.2: Uncertainty-Aware Routing
- Explore when credible interval width > 0.3
- Fall back when uncertainty too high

### Task 7.3: Dashboard Visualization
- Confidence intervals on charts
- Exploration vs exploitation metrics

---

## Phase 8: Integration & Testing (5-6 days)

### Task 8.1: Component Integration Testing
- Test all interfaces
- Verify backward compatibility
- Test fallback chains

### Task 8.2: Performance Benchmarking
- P95 latency < 200ms
- P99 < 500ms
- Throughput > 100 req/s

### Task 8.3: A/B Testing Activation
- Embedding vs keyword routing
- Graph vs SQL retrieval
- Meta-learning vs static

### Task 8.4: Real Health Checks
- Replace "always healthy" with real checks
- Component-specific health indicators

### Task 8.5: Rollback Procedures
- Document rollback for each phase
- Recovery scripts

---

## Complete Timeline

| Phase | Duration | Start Day | End Day |
|-------|----------|-----------|---------|
| Phase 0: Foundation | 1-2 days | Day 1 | Day 2 |
| Phase 1: Semantic | 4-7 days | Day 3 | Day 9 |
| Phase 2: Graph Memory | 5-7 days | Day 8 | Day 14 |
| Phase 3: Meta-Learning | 4-5 days | Day 15 | Day 19 |
| Phase 4: Multi-Dim | 4-6 days | Day 13 | Day 18 |
| Phase 5: Cross-Session | 5-7 days | Day 20 | Day 26 |
| Phase 6: Prompt Evolution | 3-4 days | Day 27 | Day 30 |
| Phase 7: Bayesian | 3-4 days | Day 31 | Day 34 |
| Phase 8: Integration | 5-6 days | Day 35 | Day 40 |

**Total: ~40 days**

---

## Parallelization Opportunities

| Parallel Wave | Tasks | Duration Saved |
|---------------|-------|---------------|
| Wave 1 | Phase 0 all tasks | 1 day |
| Wave 2 | Phase 1.1 + Phase 1.4 | 1 day |
| Wave 3 | Phase 4.1 + Phase 4.2 + Phase 4.3 | 2 days |
| Wave 4 | Phase 2.1 + Phase 2.2 | 1 day |

---

## Critical Path

```
Phase 0 → Phase 1 → Phase 3 → Phase 5 → Phase 7 → Phase 8
           ↓              ↑
        Phase 2 ──────────┘
           ↓
        Phase 4 ──→ Phase 6
```

---

## Success Metrics (End State)

| Metric | Current | Target |
|--------|---------|--------|
| Routing accuracy | ~60% (keyword) | >85% (semantic + meta) |
| Memory recall | SQL LIKE | Graph + vector + keyword RRF |
| Learning signal | Binary (success/fail) | 5-dimensional |
| Confidence | Capped 1.00 (fake) | Bayesian credible intervals |
| Cross-session | None | Transfer learning with EWC |
| Prompts | Static | Evolved via GEPA |
| Strategy selection | Static fallback chain | LinUCB contextual bandit |

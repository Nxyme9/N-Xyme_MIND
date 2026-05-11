# N-Xyme_MIND — Dense Masterplan (ALL 9 Phases)

> **TL;DR:** Transform routing from keyword matching → self-learning intelligent system
> **Duration:** 40 days | **Risk:** Medium | **Reward:** 60% → 85% accuracy

---

## Phase Dependency Map

```
Phase 0 ──► Phase 1 ──► Phase 3 ──► Phase 5 ──► Phase 7 ──► Phase 8
     │           │              ▲
     │           └──► Phase 2 ──┘
     │
     └──► Phase 4 ──► Phase 6
```

---

## One-Line Per Phase

| Phase | What It Does | Days | Risk |
|-------|--------------|------|------|
| **0** | Install deps, DB schema, embedding cache, config | 1-2 | LOW |
| **1** | Semantic classifier (SGD), shadow mode routing | 4-7 | HIGH |
| **2** | Graph memory (Neo4j), temporal patterns, RRF | 5-7 | MED |
| **3** | LinUCB strategy selector, MAML (simple), EWC | 4-5 | HIGH |
| **4** | 5-dim rewards (success/quality/latency/cost/sat) | 4-6 | MED |
| **5** | Cross-session transfer, knowledge graph | 5-7 | MED |
| **6** | Prompt evolution (GEPA-style), A/B testing | 3-4 | MED |
| **7** | Bayesian confidence, uncertainty routing | 3-4 | MED |
| **8** | Integration, testing, benchmarking, rollout | 5-6 | LOW |

---

## Critical Path (Must Do In Order)

```
Phase 0 → Phase 1.1 → Phase 1.3 → Phase 2 → Phase 3 → Phase 8
              │                    │
              │                    └─► Phase 4
              │
              └─► Phase 5
```

---

## What Each Phase Actually Changes

| Phase | Before | After |
|-------|--------|-------|
| 0 | No ML | Dependencies + cache ready |
| 1 | Keywords | Understands meaning |
| 2 | SQL LIKE | Graph traversal + similarity |
| 3 | Random/fixed | Learns best strategy |
| 4 | Binary (1/0) | 5-dimensional reward |
| 5 | Stateless | Remembers across sessions |
| 6 | Static prompts | Evolves prompts |
| 7 | Fake confidence | Real Bayesian intervals |
| 8 | Ad-hoc | Production-ready |

---

## Parallelization Opportunities

| Wave | Can Run Together | Days Saved |
|------|-------------------|-------------|
| 1 | Phase 0 all tasks | 1 |
| 2 | Phase 1.1 + 1.4 | 1 |
| 3 | Phase 2.1 + 2.2 | 1 |
| 4 | Phase 4.1 + 4.2 + 4.3 | 2 |

---

## Success Metrics

| Metric | Current | Phase 1 | Phase 3 | Phase 8 |
|--------|---------|---------|---------|---------|
| Routing accuracy | 60% | 75% | 82% | 85% |
| Memory recall | 40% | 60% | 75% | 85% |
| Learning | None | Online | Meta | Transfer |
| Confidence | Fake | Calibrated | Bayesian | Full |
| Latency | 100ms | 150ms | 180ms | 200ms |

---

## Files Summary

| Phase | New Files | Modified Files | Total |
|-------|-----------|----------------|-------|
| 0 | 2 | 2 | 4 |
| 1 | 1 | 3 | 4 |
| 2 | 1 | 4 | 5 |
| 3 | 2 | 2 | 4 |
| 4 | 0 | 4 | 4 |
| 5 | 2 | 2 | 4 |
| 6 | 1 | 3 | 4 |
| 7 | 1 | 2 | 3 |
| 8 | 2 | 3 | 5 |
| **TOTAL** | **12** | **25** | **37** |

---

## Rollback Strategy

Each phase has rollback in its plan file. Quick rollback:
- Phase 0-4: `git checkout` + config flag
- Phase 5+: Requires migration scripts (documented per phase)

---

## Quick-Start (Minimal Viable)

If you only do 2 weeks:
```
Day 1-2:   Phase 0 (all tasks)
Day 3-5:   Phase 1.1 (classifier)
Day 6-7:   Phase 1.3 (shadow mode)
Day 8-14:  Phase 2 (graph)
```

This gets you 75% accuracy improvement.

---

## Detailed Plans

See individual phase files:
- `.sisyphus/plans/phase-0-foundation.md`
- `.sisyphus/plans/phase-1-semantic-understanding.md`
- `.sisyphus/plans/phase-2-graph-memory.md`
- `.sisyphus/plans/phase-3-meta-learning.md`
- `.sisyphus/plans/phase-4-multi-dimensional-learning.md`
- `.sisyphus/plans/phase-5-cross-session.md`
- `.sisyphus/plans/phase-6-prompt-evolution.md`
- `.sisyphus/plans/phase-7-bayesian.md`
- `.sisyphus/plans/phase-8-integration.md`

---

*Dense mode: 1 page overview. See individual files for task-level detail.*

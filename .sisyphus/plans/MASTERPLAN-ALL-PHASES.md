# N-Xyme_MIND Master Plan — All 5 Phases

> **Generated:** 2026-04-10
> **Total Duration:** ~40 days (staggered execution)
> **Target:** Industry-standard, ADHD-friendly, professional vibecoding system

---

## Executive Summary

This masterplan consolidates all 5 phases into an actionable implementation roadmap. The system transforms from a basic routing mechanism to an intelligent, self-learning orchestration engine with:

- **Semantic routing** (not just keyword matching)
- **Graph-powered memory** (not SQL LIKE)
- **Multi-dimensional rewards** (not binary success/fail)
- **Cross-session transfer** (not stateless)
- **Bayesian confidence** (not fake certainty)

---

## Phase Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PHASE DEPENDENCY GRAPH                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Phase 0 (Foundation) ──────────────────────────────────────────────►       │
│       │                                                                   │
│       ├──► Phase 1 (Semantic) ──────────► Phase 3 (Meta-Learning) ──►       │
│       │           │                                    │                  │
│       │           └──► Phase 2 (Graph) ──────► Phase 5+ ──────────────────►  │
│       │                                                               │      │
│       └──► Phase 4 (Multi-Dim) ───────────────► Phase 6 (Prompts) ──────────┘
│                                                                           │
│                                                    ◄─────── Phase 7 (Bayesian)
│                                                              │
│                                                    ◄─────── Phase 8 (Integration)
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 0: Foundation

> **Duration:** 1-2 days
> **Risk:** LOW (additive only)
> **Status:** NOT STARTED

### Tasks

| Task | Description | Files |
|------|-------------|-------|
| 0.1 | Install ML dependencies (torch, sentence-transformers, scipy, scikit-learn, faiss-cpu, statsmodels) | `packages/learning_engine/pyproject.toml` |
| 0.2 | Create DB schema migrations (task_embeddings, strategy_selections, cross_session_model, prompt_versions) | `.sisyphus/routing-migrations/phase0.sql` |
| 0.3 | Build embedding model cache (10k entries, LRU, disk persistence) | `packages/learning_engine/embeddings/model_cache.py` |
| 0.4 | Add config sections (EmbeddingConfig, MetaLearningConfig, RewardWeightsConfig, BayesianConfig) | `packages/learning_engine/config.py` |

### Go/No-Go Criteria

- [ ] All 6 packages import without errors
- [ ] 4 new tables created, existing queries work
- [ ] Embedding generation < 50ms, cache hit < 1ms
- [ ] Config loads with new sections

---

## Phase 1: Semantic Understanding

> **Duration:** 4-7 days
> **Risk:** HIGH (modifies routing path)
> **Dependencies:** Phase 0 complete
> **Status:** NOT STARTED

### Tasks

| Task | Description | Files |
|------|-------------|-------|
| 1.1 | Create embedding-based semantic classifier (SGDClassifier + cold-start fallback) | `packages/intelligence/router/semantic_classifier.py` |
| 1.2 | Enhance Q-Learning state with embeddings (QState with embedding/cluster_id) | `packages/learning_engine/rl/q_learning.py` |
| 1.3 | Implement shadow mode for hybrid routing (log both, use keyword first) | `packages/intelligence/router/unified.py` |
| 1.4 | Add vector similarity to memory router | `packages/intelligence/router/memory.py` |

### Key Architecture Decision

**SGDClassifier over Neural Net** — correct for routing:
- Online learning via `partial_fit()`
- < 5ms inference
- Interpretable weight vectors
- Works with 50 samples (not 500+)

### Deployment Schedule

```
Day 1-2: Shadow mode — log semantic predictions, never use
Day 3-4: 5% traffic to semantic, measure accuracy
Day 5-6: If semantic >= keyword - 5%, increase to 25%
Day 7: If accuracy > 80%, promote to PRIMARY
```

### Go/No-Go Criteria

- [ ] Shadow accuracy >= keyword - 5%
- [ ] Confidence calibration error < 0.15
- [ ] Routing latency P99 < 200ms

---

## Phase 2: Graph Memory

> **Duration:** 5-7 days
> **Risk:** MEDIUM (Neo4j dependency)
> **Dependencies:** Phase 0 complete
> **Status:** NOT STARTED

### Tasks

| Task | Description | Files |
|------|-------------|-------|
| 2.1 | Integrate graph store (populate nodes/edges from routing.db) | `packages/memory_core/stores/graph_store.py` |
| 2.2 | Add graph-based context retrieval (Cypher queries) | `packages/memory_core/router.py` |
| 2.3 | Extract temporal patterns (NEXT_TASK edges, time-decay) | `packages/learning_engine/cross_session_transfer.py` |
| 2.4 | Enhanced RRF fusion with temporal weighting | `packages/memory_core/retrievers/fusion.py` |

### Graph Schema

```
Nodes:
  Task: id, task_text, embedding, task_type, created_at, level, domain
  Agent: id, agent_type, capabilities[], performance_score
  Outcome: id, task_id, agent_id, success, latency_ms, tokens, created_at
  Session: id, created_at, agent_count, task_count, success_rate
  Tool: id, tool_name, tool_type
  Skill: id, skill_name, category
  Pattern: id, pattern_type, description, frequency, last_seen

Edges:
  Task --[PERFORMED_BY]--> Agent
  Task --[RESULTED_IN]--> Outcome
  Task --[BELONGED_TO]--> Session
  Task --[USED_TOOL]--> Tool
  Task --[REQUIRED_SKILL]--> Skill
  Agent --[HAS_SKILL]--> Skill
  Task --[SIMILAR_TO]--> Task (similarity score)
  Task --[NEXT_TASK]--> Task (gap_seconds)
```

### Rollback

```bash
echo "USE_GRAPH=false" >> .env
# Falls back to SQLiteGraphStore automatically
```

---

## Phase 3: Meta-Learning

> **Duration:** 4-5 days
> **Risk:** HIGH (complex ML)
> **Dependencies:** Phase 1 + 2 complete
> **Status:** NOT STARTED

### Oracle-Approved Simplifications

| Component | Full | Simplified | Benefit |
|-----------|------|------------|---------|
| Bandit | Neural Thompson | LinUCB | 95% benefit, 20% complexity |
| MAML | Full PyTorch | Inner-loop only | 70% benefit, 30% complexity |
| EWC | Empirical Fisher | Diagonal + weight decay | 80% benefit, 25% complexity |
| Arms | 4 strategies | 3 (merge bandit+heuristic) | Less exploration |

### Tasks

| Task | Description | Files |
|------|-------------|-------|
| 3.1 | Implement LinUCB strategy selector (3 arms: embedding, graph, heuristic) | `packages/learning_engine/meta/strategy_selector.py` |
| 3.2 | Simplified MAML (inner-loop only, 5 adaptation steps) | `packages/learning_engine/meta/maml.py` |
| 3.3 | Diagonal Fisher EWC (prevent catastrophic forgetting) | `packages/learning_engine/meta/ewc.py` |
| 3.4 | Meta-learning health monitor (alerts for arm starvation, loss spike) | `packages/learning_engine/meta/health_monitor.py` |

### Go/No-Go Criteria

- [ ] Data availability: ≥50 outcomes per strategy
- [ ] LinUCB validation regret < 0.2 after 100 tasks
- [ ] MAML few-shot >60% accuracy with 5 support examples
- [ ] EWC retained accuracy >80% after 10 tasks

---

## Phase 4: Multi-Dimensional Learning

> **Duration:** 4-6 days
> **Risk:** MEDIUM
> **Dependencies:** Phase 1 complete
> **Status:** NOT STARTED

### Reward Dimensions

| Dimension | Weight | Source |
|-----------|--------|--------|
| Success | 0.4 | Binary (1.0 or -1.0) |
| Quality | 0.2 | Auto-computed (error density, revision ratio, tool success) |
| Latency | 0.15 | Time-based normalization |
| Cost | 0.15 | Token-based normalization |
| Satisfaction | 0.1 | Implicit signals (acceptance, follow-up) |

### Quality Proxy Formula (no human feedback needed)

```python
quality = 0.4 * (1 - error_density) + 0.3 * (1 - revision_ratio) + 0.2 * tool_success_rate + 0.1 * token_efficiency
```

### Tasks

| Task | Description | Files |
|------|-------------|-------|
| 4.1 | Integrate quality signals (error density, revision ratio) | `packages/learning_engine/signals.py` |
| 4.2 | Cost-aware routing (agent-specific cost baselines) | `packages/intelligence/router/unified.py`, `packages/learning_engine/rl/rewards.py` |
| 4.3 | Collect satisfaction signals (acceptance rate, follow-up ratio) | `packages/learning_engine/signals.py` |
| 4.4 | Composite reward integration (MultiDimensionalReward dataclass) | `packages/learning_engine/rl/rewards.py` |

### MVP vs Full

| Phase | Dimensions | Weight Learning |
|-------|-----------|-----------------|
| MVP | 3 (success, latency, cost) | No |
| Phase 4.1 | 3 + auto-quality | No |
| Phase 4.2 | 4 + weight learning | Yes |
| Full | 5 + implicit satisfaction | Yes |

---

## Phase 5+: Advanced Features

> **Duration:** 16+ days
> **Status:** NOT STARTED

### Phase 5: Cross-Session Transfer (5-7 days)

| Task | Description |
|------|-------------|
| 5.1 | Knowledge graph (Neo4j nodes for decision/lesson/pattern) |
| 5.2 | Transferability scoring (embedding-based similarity) |
| 5.3 | Session injection (tiered: critical/contextual/archive) |
| 5.4 | EWC integration (from Phase 3) |

### Phase 6: Prompt Evolution (3-4 days)

Based on **GEPA** (ICLR 2026 Oral):
- 35x fewer rollouts than RL
- 90x cheaper than Claude Opus
- Uses LLM reflection instead of scalar rewards

| Task | Description |
|------|-------------|
| 6.1 | Outcome-linked scoring (link prompt versions to outcomes) |
| 6.2 | LLM refinement (hybrid: LLM only when heuristic plateaus) |
| 6.3 | A/B testing (Z-test, α=0.05, power=0.80) |
| 6.4 | Prompt registry (version tracking, rollback) |

### Phase 7: Bayesian Confidence (3-4 days)

| Task | Description |
|------|-------------|
| 7.1 | Bayesian confidence estimator (Beta distribution) |
| 7.2 | Uncertainty-aware routing (explore when interval width > 0.3) |
| 7.3 | Dashboard visualization (confidence intervals) |

### Phase 8: Integration & Testing (5-6 days)

| Task | Description |
|------|-------------|
| 8.1 | Component integration testing |
| 8.2 | Performance benchmarking (P95 < 200ms, P99 < 500ms) |
| 8.3 | A/B testing activation |
| 8.4 | Real health checks |
| 8.5 | Rollback procedures |

---

## Implementation Order

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         RECOMMENDED EXECUTION ORDER                         │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  WEEK 1-2: Phase 0 (Foundation)                                            │
│  ├── Task 0.1: Dependency installation                                    │
│  ├── Task 0.2: Database schema                                            │
│  ├── Task 0.3: Embedding cache                                            │
│  └── Task 0.4: Config validation                                          │
│                                                                            │
│  WEEK 2-3: Phase 1 (Semantic)                                              │
│  ├── Task 1.1: Semantic classifier (NEW FILE)                             │
│  ├── Task 1.2: Q-Learning enhancement                                    │
│  ├── Task 1.3: Shadow mode routing                                        │
│  └── 48h validation → gradual promotion                                   │
│                                                                            │
│  WEEK 3-4: Phase 2 (Graph Memory) + Phase 4.1 (Quality)                  │
│  ├── Task 2.1: Graph integration                                         │
│  ├── Task 2.2: Context retrieval                                          │
│  ├── Task 4.1: Quality signals                                           │
│  └── Task 4.2: Cost-aware routing                                         │
│                                                                            │
│  WEEK 5: Phase 3 (Meta-Learning)                                          │
│  ├── Task 3.1: LinUCB selector                                            │
│  ├── Task 3.2: Simplified MAML                                           │
│  ├── Task 3.3: EWC                                                        │
│  └── Task 3.4: Health monitor                                             │
│                                                                            │
│  WEEK 6-7: Phase 4 (Multi-Dim) + Phase 5 (Cross-Session)                  │
│  ├── Task 4.3: Satisfaction signals                                      │
│  ├── Task 4.4: Composite rewards                                         │
│  ├── Task 5.1: Knowledge graph                                            │
│  └── Task 5.2: Transferability scoring                                   │
│                                                                            │
│  WEEK 8-9: Phase 6 (Prompts) + Phase 7 (Bayesian)                         │
│  ├── Task 6.1-6.4: Prompt evolution                                       │
│  └── Task 7.1-7.3: Bayesian confidence                                    │
│                                                                            │
│  WEEK 10-11: Phase 8 (Integration)                                        │
│  ├── Task 8.1-8.5: Integration & testing                                 │
│  └── GO LIVE                                                              │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Routing accuracy | ~60% (keyword) | >85% (semantic + meta) |
| Memory recall | SQL LIKE | Graph + vector + keyword RRF |
| Learning signal | Binary (success/fail) | 5-dimensional |
| Confidence | Capped 1.00 (fake) | Bayesian credible intervals |
| Cross-session | None | Transfer learning with EWC |
| Prompts | Static | Evolved via GEPA |
| Strategy selection | Static fallback chain | LinUCB contextual bandit |

---

## ADHD-Friendly Features

From previous sessions, these features are already implemented:

- ✅ `N-Xyme.md` — CLAUDE.md equivalent with ADHD-friendly rules
- ✅ `bin/save-and-exit.sh` — One-command session checkpoint
- ✅ `bin/set-title.sh` — Terminal title breadcrumbs for progress visibility
- ✅ `bin/error-translator.py` — Human-readable error translations
- ✅ `bin/momentum-detector.sh` — Flow state detection
- ✅ MCP health check on startup

---

## Files Summary

| Phase | New Files | Modified Files |
|-------|-----------|----------------|
| 0 | 2 | 2 |
| 1 | 1 | 3 |
| 2 | 1 | 4 |
| 3 | 2 | 2 |
| 4 | 0 | 4 |
| 5-8 | 3 | 5 |

---

## Rollback Strategy

Each phase has documented rollback procedures in individual phase files:

- `.sisyphus/plans/phase-0-foundation.md` → Rollback in lines 487-505
- `.sisyphus/plans/phase-1-semantic-understanding.md` → Rollback in lines 436-450
- `.sisyphus/plans/phase-2-graph-memory.md` → Rollback in lines 246-252

---

## Next Steps

1. **Confirm Phase 0 start** — Dependencies need installation
2. **Oracle review** — Required before Phase 1.3 (shadow mode)
3. **Neo4j setup** — Required for Phase 2 (or use SQLite fallback)
4. **Data collection** — Need ≥50 outcomes per strategy before Phase 3

---

*Last updated: 2026-04-10*

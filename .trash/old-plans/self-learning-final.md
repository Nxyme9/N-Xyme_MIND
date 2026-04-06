# Final Plan: Self-Learning Memory System (Synthesized)

## Sources
- Original plan: `.sisyphus/plans/self-learning-masterplan.md`
- Metis gap analysis: 15 gaps identified
- Momus adversarial review: 47 issues (8 critical, 14 high, 15 medium, 10 low)
- Oracle architectural review: Consolidate 10 new modules → 3 new + 8 existing extended

## Key Decisions (From Reviews)

| Decision | Original Plan | Final Decision | Rationale |
|----------|--------------|----------------|-----------|
| New modules | 10 new files | **3 new + 8 existing extended** | Oracle: avoid module sprawl, reuse existing learning primitives |
| Feedback collection | Implicit result usage | **Proxy signals** (query reformulation, session context) | Momus: no click tracking in CLI |
| Cold start | Not addressed | **Baseline heuristics + seed data** | Momus: can't learn without data |
| Consolidation threshold | Hardcoded 80% | **Configurable, starts at 95%, auto-tunes** | Momus: arbitrary, needs rollback |
| Forgetting | Delete after 90 days | **Soft delete + audit trail + mandatory retention** | Momus: can't lose important memories |
| Learning cycle | Every 30 minutes | **Every 2 hours, adaptive** | Oracle: 30 min too aggressive |
| Storage | New SQLite tables | **Extend existing registry DB** | Oracle: keep transactions atomic |
| Integration | New learning daemon | **Extend existing daemon.py** | Oracle: single-process system |
| Router | Separate learning-aware router | **Feature flag in existing router** | Oracle: backward compatible |
| Agent delegation | All hephaestus | **Hephaestus + Oracle review after each wave** | Momus: need code review |

## Revised Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SELF-LEARNING LOOP                       │
│                                                             │
│  OBSERVE  →  priority_engine.update_access()               │
│              + MCP server logs (query reformulation)        │
│              + session context (which results used)         │
│                                                             │
│  LEARN    →  pattern_learning._check_patterns()            │
│              + procedural rule updates                      │
│              + preference_model (NEW)                       │
│                                                             │
│  ADAPT    →  router re-ranking (feature flag)              │
│              + priority_engine._adapt_weights()             │
│              + knowledge_graph merge/consolidate            │
│              + enhancements time-decay archival             │
└─────────────────────────────────────────────────────────────┘
```

## Revised Module Map

| Original Plan Module | Final Action | File |
|---------------------|-------------|------|
| feedback_tracker.py | **Extend** | `src/memory/priority_engine.py` — add query-level feedback |
| query_learner.py | **Extend** | `src/pattern_learning.py` — add SQLite persistence |
| knowledge_consolidator.py | **Extend** | `src/memory/knowledge_graph.py` — add merge logic |
| forgetting_engine.py | **Extend** | `src/memory/enhancements.py` — add archival |
| drift_detector.py | **Extend** | `src/memory/priority_engine.py` — add topic tracking |
| strategy_optimizer.py | **Extend** | `src/memory/procedural.py` — add query-type rules |
| preference_model.py | **CREATE** | `src/memory/preference_model.py` — only genuinely new |
| learning_orchestrator.py | **Extend** | `src/memory/daemon.py` — add learning cycle |
| learning_integration.py | **Modify** | `src/memory/router.py` — add learned re-ranking |
| test_self_learning.py | **CREATE** | `tests/test_self_learning.py` |
| — | **CREATE** | `src/memory/learning_config.py` — feature flags, thresholds |

**Net: 3 new files, 8 existing files extended.**

## Implementation Waves (Revised)

### Wave 1: Observation Layer (2 tasks, parallel)
**Goal**: Collect feedback data without changing behavior

| Task | File | Description | Agent |
|------|------|-------------|-------|
| T1.1 | Extend `priority_engine.py` | Add query-level feedback tracking, topic drift detection | hephaestus |
| T1.2 | Extend `pattern_learning.py` | Add SQLite persistence, query pattern detection | hephaestus |
| T1.3 | Create `learning_config.py` | Feature flags, thresholds, TTL settings | hephaestus |

**Acceptance Criteria**:
- [ ] `query_feedback` table created in existing DB
- [ ] Router logs which results are used (via session context)
- [ ] Pattern learning persists to SQLite (not just in-memory)
- [ ] Feature flags control all learning behavior (default: OFF)
- [ ] Zero behavior change — observation only

### Wave 2: Passive Learning (3 tasks, sequential)
**Goal**: Learn patterns in background without affecting results

| Task | File | Description | Agent |
|------|------|-------------|-------|
| T2.1 | Extend `procedural.py` | Add query-type strategy rules, success/failure tracking | hephaestus |
| T2.2 | Extend `knowledge_graph.py` | Add entity merge/dedup logic (95% threshold, configurable) | hephaestus |
| T2.3 | Extend `enhancements.py` | Add soft-delete archival with decay curves | hephaestus |

**Acceptance Criteria**:
- [ ] Strategy rules track retrieval method success per query type
- [ ] Knowledge graph suggests merges (doesn't auto-merge yet)
- [ ] Enhancement archival marks memories as "archived" (not deleted)
- [ ] All learning runs in daemon background thread
- [ ] Results logged but NOT applied to router

### Wave 3: Active Learning (2 tasks, parallel)
**Goal**: Enable learned behavior with guardrails

| Task | File | Description | Agent |
|------|------|-------------|-------|
| T3.1 | Create `preference_model.py` | Learn user result type preferences (code vs docs vs configs) | hephaestus |
| T3.2 | Modify `router.py` | Add learned re-ranking layer (feature flag, opt-in) | hephaestus |

**Acceptance Criteria**:
- [ ] Preference model tracks result type preferences over time
- [ ] Router applies learned re-ranking when feature flag enabled
- [ ] Exploration rate: 20% of results always diverse (no filter bubble)
- [ ] Confidence threshold: 0.8+ for applying learned patterns
- [ ] A/B logging: both learned and baseline rankings logged

### Wave 4: Integration & Testing (3 tasks, sequential)
**Goal**: Wire everything together, test end-to-end

| Task | File | Description | Agent |
|------|------|-------------|-------|
| T4.1 | Extend `daemon.py` | Add `_learning_cycle_loop()` (every 2 hours) | hephaestus |
| T4.2 | Extend `mcp_server.py` | Add `get_learning_stats` tool | hephaestus |
| T4.3 | Create `tests/test_self_learning.py` | Comprehensive test suite (50+ tests) | hephaestus |

**Acceptance Criteria**:
- [ ] Daemon runs learning cycles every 2 hours (configurable)
- [ ] MCP tool returns learning statistics
- [ ] All tests pass (unit + integration + simulation)
- [ ] Feature flags can disable all learning instantly
- [ ] Rollback to baseline works (set `learning.enabled = false`)

## Data Model (New Tables in Existing DB)

```sql
-- Query-level feedback
CREATE TABLE query_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    result_id TEXT NOT NULL,
    source TEXT NOT NULL,
    used INTEGER DEFAULT 0,
    ignored INTEGER DEFAULT 0,
    timestamp TEXT NOT NULL,
    session_id TEXT
);

-- Learned patterns
CREATE TABLE learned_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_type TEXT NOT NULL,
    pattern_key TEXT NOT NULL,
    pattern_value TEXT,
    confidence REAL DEFAULT 0.5,
    occurrences INTEGER DEFAULT 1,
    last_updated TEXT NOT NULL,
    UNIQUE(pattern_type, pattern_key)
);

-- Strategy performance
CREATE TABLE strategy_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_type TEXT NOT NULL,
    strategy TEXT NOT NULL,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    avg_latency_ms REAL,
    last_evaluated TEXT
);
```

## Feature Flags (learning_config.py)

```python
LEARNING_CONFIG = {
    "enabled": False,              # Master switch (default: OFF)
    "rerank_enabled": False,       # Router re-ranking
    "consolidate_enabled": False,  # Auto-merge entities
    "forget_enabled": False,       # Archive old memories
    "min_confidence": 0.8,         # Threshold for applying learned patterns
    "exploration_rate": 0.2,       # 20% diverse results (no filter bubble)
    "consolidation_threshold": 0.95, # Entity merge similarity (starts high)
    "learning_cycle_minutes": 120,  # Every 2 hours (not 30 min)
    "feedback_ttl_days": 90,       # Clean up old feedback data
    "mandatory_retention_days": 30, # Never forget recent memories
}
```

## Evolution Roadmap (4 Phases)

| Phase | Duration | What Changes | Risk |
|-------|----------|-------------|------|
| **1. Observation** | Week 1 | Collect feedback, no behavior change | Zero |
| **2. Passive Learning** | Week 2-3 | Learn patterns in background, log only | Low |
| **3. Active Learning** | Week 4-5 | Enable re-ranking with guardrails | Medium |
| **4. Full Autonomy** | Week 6+ | Lower thresholds, enable consolidation/forgetting | Medium |

## Rollback Strategy

```python
# Instant rollback: set in learning_config.py
LEARNING_CONFIG["enabled"] = False

# System immediately falls back to baseline behavior
# All learned data persists in DB (not deleted)
# Re-enable when issues are fixed
```

## Success Metrics (Measurable)

| Metric | Target | How Measured |
|--------|--------|-------------|
| Feedback data collected | 1000+ interactions/week | `query_feedback` table count |
| Pattern accuracy | >70% match rate | `learned_patterns.confidence` |
| Strategy improvement | +20% success rate | `strategy_performance` comparison |
| Consolidation quality | <5% false merges | Manual audit of merged entities |
| Forgetting accuracy | 0% important memories lost | Audit trail check |
| Learning cycle duration | <30 seconds | Timing logs |
| Query latency (learned) | <150ms | Benchmark suite |

## Atomic Commit Strategy

Each task = one commit with:
1. Implementation code
2. Test file
3. Integration stub (if applicable)
4. Updated config (if applicable)

Commit format: `memory: <module> - <description>`

Example:
```
commit 1: memory: priority_engine - add query-level feedback tracking
commit 2: memory: pattern_learning - add SQLite persistence
commit 3: memory: learning_config - feature flags and thresholds
```

## Quality Gates

Each task must pass:
1. `lsp_diagnostics` clean on changed files
2. Import test passes
3. Unit tests pass
4. No new dependencies added
5. Feature flags default to OFF (zero behavior change)
6. Oracle review after each wave

## Risk Mitigation (From Momus + Oracle)

| Risk | Mitigation |
|------|------------|
| Wrong learning patterns | Confidence threshold (0.8+), exploration rate (20%), instant rollback |
| Forgetting important memories | Mandatory retention (30 days), soft delete, audit trail |
| Over-consolidation | High threshold (95%), configurable, manual review for first 100 merges |
| Filter bubble | Exploration rate (20% diverse results) |
| Database bloat | Feedback TTL (90 days), aggregation over raw data |
| Learning cycle too slow | Start at 2 hours, adaptive scheduling, incremental processing |
| Circular dependencies | Learning modules read from DB directly, not through router |
| Cold start | Baseline heuristics, seed data, learning mode vs production mode |

## Total Effort: 8-12 person-days (revised from 10)

| Wave | Tasks | Effort |
|------|-------|--------|
| 1 | T1.1, T1.2, T1.3 | 2-3 days |
| 2 | T2.1, T2.2, T2.3 | 2-3 days |
| 3 | T3.1, T3.2 | 1-2 days |
| 4 | T4.1, T4.2, T4.3 | 2-3 days |
| Oracle review (after each wave) | 4 reviews | 1 day |

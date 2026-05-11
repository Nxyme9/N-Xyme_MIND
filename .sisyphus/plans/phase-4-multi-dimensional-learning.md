# Phase 4: Multi-Dimensional Learning — Detailed Implementation Plan

> **Date:** 2026-04-08
> **Effort:** 4-6 days
> **Risk:** MEDIUM
> **Dependencies:** Phase 1 complete

---

## Executive Summary

Phase 4 expands from binary success/failure to 5-dimensional reward: success (0.4), quality (0.2), latency (0.15), cost (0.15), satisfaction (0.1). Oracle recommends **MVP first**: 3 dimensions (success, latency, cost), add quality/satisfaction later.

**GO/NO-GO: GO** — Infrastructure exists, just needs connection.

---

## Task 4.1: Quality Signal Integration

### Files to Modify
- `packages/learning_engine/signals.py`
- `packages/learning_engine/outcome_logger.py`

### Quality Proxies (no human feedback needed)
```python
quality = 0.4 * (1 - error_density) + 0.3 * (1 - revision_ratio) + 0.2 * tool_success_rate + 0.1 * token_efficiency
```

---

## Task 4.2: Cost-Aware Routing

### Files to Modify
- `packages/intelligence/router/unified.py`
- `packages/learning_engine/rl/rewards.py`

### Agent-Specific Cost Baselines
```python
AGENT_COST_BASELINES = {
    "hephaestus": 0.015,
    "oracle": 0.020,
    "explore": 0.005,
    "librarian": 0.003,
}
```

---

## Task 4.3: Satisfaction Signal Collection

### Files to Modify
- `packages/learning_engine/signals.py`

### Implicit Signals
```python
satisfaction = 0.35 * (1 - revision_ratio) + 0.25 * acceptance_rate + 0.25 * (1 - follow_up_ratio) + 0.15 * tool_success_rate
```

---

## Task 4.4: Composite Reward Integration

### Files to Modify
- `packages/learning_engine/rl/rewards.py`
- `packages/learning_engine/delegation/learner.py`

### MultiDimensionalReward
```python
@dataclass
class MultiDimensionalReward:
    success: float        # 1.0 or -1.0
    quality: float        # 0-1
    latency: float        # -1 to 1
    cost: float           # -1 to 1
    satisfaction: float   # 0-1
    
    @property
    def total(self):
        weights = {"success": 0.4, "quality": 0.2, "latency": 0.15, "cost": 0.15, "satisfaction": 0.1}
        return sum(getattr(self, k) * w for k, w in weights.items())
```

---

## MVP vs Full

| Phase | Dimensions | Weight Learning |
|-------|-----------|-----------------|
| MVP | 3 (success, latency, cost) | No |
| Phase 1 | 3 + auto-quality | No |
| Phase 2 | 4 + weight learning | Yes |
| Full | 5 + implicit satisfaction | Yes |

---

## Go/No-Go

| Metric | Target |
|--------|--------|
| Quality signals captured | >90% of delegations |
| Cost tracking connected | Yes |
| Multi-dimensional reward | 5 dimensions computed |
| Cost reduction | >15% |

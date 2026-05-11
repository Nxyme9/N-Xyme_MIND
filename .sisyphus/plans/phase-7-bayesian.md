# Phase 7: Bayesian Confidence — Detailed Masterplan

> **Duration:** 3-4 days
> **Risk:** MEDIUM
> **Dependencies:** Phase 4 (Multi-dimensional rewards) complete
> **Oracle Review:** REQUIRED for Task 7.1

---

## Executive Summary

Phase 7 replaces **fake confidence** (capped at 1.0) with **real Bayesian credible intervals**. Instead of "I'm 90% confident", the system says "I'm 90% confident the true success rate is between 85% and 95%."

**Why It Matters:**
- Know when to trust vs explore
- Quantifies uncertainty honestly
- Enables better routing decisions

**GO/NO-GO:** Only proceed after ≥100 outcomes per agent.

---

## Tasks Overview

| Task | Name | Effort | Risk | Dependencies |
|------|------|--------|------|--------------|
| 7.1 | Bayesian Confidence Estimator | 1.5 days | MEDIUM | Phase 4 |
| 7.2 | Uncertainty-Aware Routing | 1 day | HIGH | 7.1 |
| 7.3 | Dashboard Visualization | 1 day | LOW | 7.1 + 7.2 |

---

## Task 7.1: Bayesian Confidence Estimator

### What It Does
Use Beta distribution to model success probability with credible intervals.

### Mathematics

```
Prior: Beta(α=1, β=1) = Uniform (no prior knowledge)
Posterior: Beta(α + successes, β + failures)

Credible Interval: [q_{0.025}, q_{0.975}] = 95% interval
Expected Value: E[p] = α / (α + β)
```

### Implementation

```python
# packages/learning_engine/bayesian/confidence.py

import numpy as np
from scipy import stats
from dataclasses import dataclass

@dataclass
class BayesianConfidence:
    successes: int
    failures: int
    alpha_prior: float = 1.0
    beta_prior: float = 1.0
    
    @property
    def alpha_post(self) -> float:
        return self.alpha_prior + self.successes
    
    @property
    def beta_post(self) -> float:
        return self.beta_prior + self.failures
    
    @property
    def expected(self) -> float:
        """Expected probability of success."""
        return self.alpha_post / (self.alpha_post + self.beta_post)
    
    @property
    def credible_interval_95(self) -> tuple:
        """95% credible interval."""
        return stats.beta.ppf(
            [0.025, 0.975],
            self.alpha_post,
            self.beta_post
        )
    
    @property
    def interval_width(self) -> float:
        """Width of 95% interval (uncertainty measure)."""
        lo, hi = self.credible_interval_95
        return hi - lo
    
    @property
    def samples_needed_for_width(self, target_width: float = 0.1) -> int:
        """How many more samples to achieve target interval width."""
        # Approximation: width ≈ 4 / sqrt(n + 4)
        n_needed = ((4 / target_width) ** 2) - (self.successes + self.failures)
        return max(0, int(n_needed))


class BayesianAgentTracker:
    """Track confidence per agent."""
    
    def __init__(self):
        self._trackers = {}  # agent_name -> BayesianConfidence
    
    def record(self, agent: str, success: bool):
        """Record an outcome."""
        if agent not in self._trackers:
            self._trackers[agent] = BayesianConfidence(0, 0)
        
        tracker = self._trackers[agent]
        if success:
            tracker.successes += 1
        else:
            tracker.failures += 1
    
    def get_confidence(self, agent: str) -> BayesianConfidence:
        """Get confidence for agent."""
        return self._trackers.get(agent, BayesianConfidence(0, 0))
    
    def get_all_confidences(self) -> dict:
        """Get all agent confidences."""
        return {
            agent: {
                "expected": c.expected,
                "interval_95": c.credible_interval_95,
                "width": c.interval_width,
                "n_samples": c.successes + c.failures
            }
            for agent, c in self._trackers.items()
        }
```

### Thompson Sampling Integration

```python
def thompson_sample(self, agent: str) -> float:
    """Sample from posterior for exploration."""
    c = self.get_confidence(agent)
    return np.random.beta(c.alpha_post, c.beta_post)
```

### Verification
```bash
.venv/bin/python3 -c "
from packages.learning_engine.bayesian.confidence import BayesianAgentTracker
t = BayesianAgentTracker()

# Record some outcomes
for _ in range(20):
    t.record('hephaestus', True)
for _ in range(5):
    t.record('hephaestus', False)

c = t.get_confidence('hephaestus')
print(f'Expected: {c.expected:.2f}')
print(f'95% Interval: {c.credible_interval_95}')
print(f'Width: {c.interval_width:.2f}')
"
```

### Success Criteria
- [ ] Expected value matches empirical rate
- [ ] Interval width decreases with more samples
- [ ] 100 outcomes → width < 0.15

---

## Task 7.2: Uncertainty-Aware Routing

### What It Does
Use confidence intervals to decide: explore new agents vs exploit known ones.

### Decision Rules

| Scenario | Action |
|----------|--------|
| Interval width < 0.15 | EXPLOIT (use best agent) |
| Interval width 0.15-0.30 | EXPLORE with probability proportional to uncertainty |
| Interval width > 0.30 | EXPLORE more (fallback to known agent) |
| No data | Use heuristic / explore randomly |

### Implementation

```python
# packages/learning_engine/bayesian/routing.py

class UncertaintyAwareRouter:
    def __init__(self, bayesian_tracker, fallback_router):
        self.tracker = bayesian_tracker
        self.fallback = fallback_router
    
    def route(self, task: str) -> dict:
        """Route with uncertainty awareness."""
        
        # Get confidences for all agents
        confidences = self.tracker.get_all_confidences()
        
        if not confidences:
            # No data - use fallback
            return self.fallback.route(task)
        
        # Find agents with low uncertainty
        low_uncertainty = [
            (agent, c) for agent, c in confidences.items()
            if c['width'] < 0.15
        ]
        
        if low_uncertainty:
            # Exploit: use best known agent
            best = max(low_uncertainty, key=lambda x: x[1]['expected'])
            return {
                "agent": best[0],
                "confidence": best[1]['expected'],
                "interval": best[1]['interval_95'],
                "strategy": "exploit",
                "uncertainty": best[1]['width']
            }
        
        # Explore: use Thompson sampling
        return self._thompson_route(task, confidences)
    
    def _thompson_route(self, task: str, confidences: dict) -> dict:
        """Thompson sample from posteriors."""
        samples = {}
        for agent, c in confidences.items():
            samples[agent] = self.tracker.thompson_sample(agent)
        
        best_agent = max(samples, key=samples.get)
        return {
            "agent": best_agent,
            "confidence": confidences[best_agent]['expected'],
            "interval": confidences[best_agent]['interval_95'],
            "strategy": "explore",
            "uncertainty": confidences[best_agent]['width']
        }
```

### Exploration Budget

```python
# Dynamic exploration rate based on system-wide uncertainty
EXPLORATION_RATE = {
    "high_uncertainty": 0.4,    # < 50 outcomes total
    "medium_uncertainty": 0.2,  # 50-200 outcomes
    "low_uncertainty": 0.1,     # > 200 outcomes
}
```

### Success Criteria
- [ ] Exploits when confident
- [ ] Explores when uncertain
- [ ] Exploration rate decreases with data

---

## Task 7.3: Dashboard Visualization

### What It Does
Show confidence intervals on dashboard for human monitoring.

### Metrics to Display

```
Agent: hephaestus
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Expected: 0.82 ████████████████████░░░░░░░░ 82%
95% CI:   [0.76, 0.87] ░░░░░████████████░░░░░
Samples: 150 | Width: 0.11 | Status: EXPLOIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Implementation

```python
# packages/learning_engine/bayesian/dashboard.py

def render_confidence_dashboard(tracker: BayesianAgentTracker) -> str:
    """Render ASCII dashboard."""
    confidences = tracker.get_all_confidences()
    
    lines = ["=== Agent Confidence Dashboard ===", ""]
    
    for agent, c in sorted(confidences.items(), key=lambda x: -x[1]['expected']):
        # ASCII bar for expected value
        bar_len = int(c['expected'] * 30)
        bar = "█" * bar_len + "░" * (30 - bar_len)
        
        # Interval visualization
        lo, hi = c['interval_95']
        lo_idx = int(lo * 30)
        hi_idx = int(hi * 30)
        interval_bar = "░" * lo_idx + "▓" * (hi_idx - lo_idx) + "░" * (30 - hi_idx)
        
        status = "EXPLOIT" if c['width'] < 0.15 else "EXPLORE"
        
        lines.append(f"Agent: {agent}")
        lines.append(f"Expected: {c['expected']:.2f} {bar}")
        lines.append(f"95% CI:   [{lo:.2f}, {hi:.2f}] {interval_bar}")
        lines.append(f"Samples: {c['n_samples']} | Width: {c['width']:.2f} | Status: {status}")
        lines.append("")
    
    return "\n".join(lines)
```

### Success Criteria
- [ ] Renders within 100ms
- [ ] Shows all tracked agents
- [ ] Updates after each outcome

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Beta prior wrong | MEDIUM | MEDIUM | Sensitivity analysis |
| Narrow intervals with few samples | HIGH | HIGH | Minimum sample requirement |
| Performance overhead | LOW | LOW | Async computation |

---

## Go/No-Go Criteria

| Criterion | Threshold |
|-----------|-----------|
| Expected matches empirical | ±5% |
| 100 samples → width | < 0.15 |
| 200 samples → width | < 0.10 |
| Routing latency | < 50ms |

---

## Files Modified

| File | Action | Description |
|------|--------|-------------|
| `packages/learning_engine/bayesian/confidence.py` | CREATE | Beta distribution confidence |
| `packages/learning_engine/bayesian/routing.py` | CREATE | Uncertainty-aware router |
| `packages/learning_engine/bayesian/dashboard.py` | CREATE | ASCII dashboard |

---

## Rollback

```bash
# Disable Bayesian confidence
echo "BAYESIAN_ENABLED=false" >> .env

# Fall back to capped confidence
# (use max(confidence, 0.85) or fixed)
```

---

*Phase 7 complete. See Phase 8 for integration.*

# Phase 8: Integration & Testing — Detailed Masterplan

> **Duration:** 5-6 days
> **Risk:** LOW (final integration)
> **Dependencies:** Phase 1-7 complete
> **Oracle Review:** REQUIRED for Task 8.3 (A/B activation)

---

## Executive Summary

Phase 8 is the **final integration phase**. All previous phases are built as independent modules. Phase 8 connects them, tests the whole system, and prepares for production deployment.

**GO/NO-GO:** Only proceed after all previous phases are validated.

---

## Tasks Overview

| Task | Name | Effort | Risk | Dependencies |
|------|------|--------|------|--------------|
| 8.1 | Component Integration | 1.5 days | MEDIUM | Phase 1-7 |
| 8.2 | Performance Benchmark | 1 day | LOW | 8.1 |
| 8.3 | A/B Testing Activation | 1.5 days | HIGH | All phases |
| 8.4 | Real Health Checks | 1 day | MEDIUM | 8.1 |
| 8.5 | Rollback Procedures | 0.5 day | LOW | All phases |

---

## Task 8.1: Component Integration

### Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ROUTING REQUEST                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   INPUT      │───►│   PHASE 1    │───►│   PHASE 3    │      │
│  │   PARSER     │    │  SEMANTIC    │    │   LinUCB     │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                   │              │
│         ▼                   ▼                   ▼              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              CONTEXT INJECTION (Phase 5)               │    │
│  │  Tier 1: Critical | Tier 2: Contextual | Tier 3: Arc  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│         ┌────────────────────┼────────────────────┐              │
│         ▼                    ▼                    ▼              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   PHASE 2    │    │   PHASE 4    │    │   PHASE 7    │      │
│  │   GRAPH      │    │   REWARD     │    │   BAYESIAN   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                   │              │
│         └───────────────────┼───────────────────┘              │
│                             ▼                                   │
│                      ┌──────────────┐                           │
│                      │   OUTPUT     │                           │
│                      │   ROUTING    │                           │
│                      └──────────────┘                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Integration Code

```python
# packages/intelligence/router/integrated.py

class IntegratedRouter:
    """Single entry point combining all phases."""
    
    def __init__(self):
        # Phase 1: Semantic
        self.semantic = SemanticTaskClassifier()
        
        # Phase 2: Graph Memory
        self.memory = IntegratedMemoryRouter()
        
        # Phase 3: Meta-Learning
        self.meta = LinUCBStrategySelector()
        
        # Phase 4: Rewards
        self.rewards = MultiDimensionalRewardEngine()
        
        # Phase 5: Cross-session
        self.session = SessionInjector()
        
        # Phase 7: Bayesian
        self.bayesian = BayesianAgentTracker()
    
    async def route(self, task: str, session_id: str) -> RoutingResult:
        """Full routing pipeline."""
        
        # Step 1: Semantic classification
        semantic_result = self.semantic.classify(task)
        
        # Step 2: Context injection
        context = self.session.inject_for_task(task, session_id)
        
        # Step 3: Graph memory retrieval
        memory_results = await self.memory.retrieve(task, context)
        
        # Step 4: Meta-learning strategy
        strategy = self.meta.select(task, context)
        
        # Step 5: Bayesian confidence
        confidence = self.bayesian.get_confidence(semantic_result.agent)
        
        # Combine signals
        agent = self._combine(semantic_result, memory_results, 
                           strategy, confidence)
        
        return RoutingResult(
            task=task,
            agent=agent,
            confidence=confidence.expected,
            interval=confidence.credible_interval_95,
            strategy=strategy,
            context=context
        )
    
    def _combine(self, semantic, memory, strategy, bayesian) -> str:
        """Combine signals from all phases."""
        
        # Weighted combination
        scores = {}
        for agent in ALL_AGENTS:
            score = (
                0.35 * semantic.all_scores.get(agent, 0) +
                0.25 * memory.scores.get(agent, 0) +
                0.20 * strategy.scores.get(agent, 0) +
                0.20 * bayesian.expected
            )
            scores[agent] = score
        
        return max(scores, key=scores.get)
```

### Interface Tests

```python
# tests/integration/test_integrated_router.py

import pytest

@pytest.mark.asyncio
async def test_route_task():
    router = IntegratedRouter()
    
    result = await router.route("fix bug in auth.py", "session-001")
    
    assert result.agent in ALL_AGENTS
    assert 0 <= result.confidence <= 1
    assert result.strategy in STRATEGIES

@pytest.mark.asyncio  
async def test_fallback_chain():
    """Test all fallbacks work."""
    router = IntegratedRouter()
    
    # No data - should fallback to heuristic
    result = await router.route("do something", "new-session")
    assert result.strategy == "heuristic"
    
    # Some data - should use semantic
    # ... add test data ...
    result = await router.route("fix bug", "session-002")
    assert result.strategy in ["semantic", "meta", "graph"]
```

### Success Criteria
- [ ] All 7 phases integrated
- [ ] Single entry point works
- [ ] Fallback chain complete
- [ ] Error handling at each phase

---

## Task 8.2: Performance Benchmark

### Metrics Targets

| Metric | Target | Current | Improvement |
|--------|--------|---------|--------------|
| P50 latency | 100ms | 150ms | 33% |
| P95 latency | 200ms | 300ms | 33% |
| P99 latency | 500ms | 800ms | 37% |
| Throughput | 100 req/s | 50 req/s | 100% |

### Benchmark Script

```python
# tests/benchmark/integrated_benchmark.py

import asyncio
import time
import numpy as np
from packages.intelligence.router.integrated import IntegratedRouter

async def benchmark_router(n_requests: int = 1000):
    """Benchmark the integrated router."""
    
    router = IntegratedRouter()
    test_tasks = [
        "fix bug in auth.py",
        "add feature to dashboard",
        "refactor user service",
        "find where session is stored",
        "review my changes",
    ]
    
    latencies = []
    
    for i in range(n_requests):
        task = test_tasks[i % len(test_tasks)]
        
        start = time.perf_counter()
        result = await router.route(task, f"bench-{i}")
        latency = (time.perf_counter() - start) * 1000
        
        latencies.append(latency)
        
        # Record for rewards (Phase 4)
        await router.rewards.record(result.agent, task, success=True, 
                                    latency_ms=latency)
    
    # Calculate percentiles
    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)
    throughput = n_requests / (sum(latencies) / 1000)
    
    return {
        "p50": p50,
        "p95": p95,
        "p99": p99,
        "throughput": throughput,
        "total_requests": n_requests
    }

if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    result = asyncio.run(benchmark_router(n))
    print(f"P50: {result['p50']:.1f}ms")
    print(f"P95: {result['p95']:.1f}ms")
    print(f"P99: {result['p99']:.1f}ms")
    print(f"Throughput: {result['throughput']:.1f} req/s")
```

### Run Commands

```bash
# Quick benchmark
python3 tests/benchmark/integrated_benchmark.py 100

# Full benchmark
python3 tests/benchmark/integrated_benchmark.py 1000
```

### Success Criteria
- [ ] P95 < 200ms
- [ ] P99 < 500ms
- [ ] Throughput > 100 req/s
- [ ] No memory leaks over 10k requests

---

## Task 8.3: A/B Testing Activation

### What It Does
Activate real A/B tests between routing strategies in production.

### Tests to Activate

| Test | Variant A | Variant B | Metric |
|------|-----------|-----------|--------|
| AB-1 | Keyword | Semantic | Accuracy |
| AB-2 | SQL | Graph | Recall |
| AB-3 | Static | LinUCB | Latency |
| AB-4 | Binary | Multi-dim | Quality |

### Traffic Split

```python
# Initial: 5% to B, 95% to A
# If B better by 5% for 48h → 25% to B
# If B better by 10% for 48h → 50% to B
# If B better by 10% for 48h → 100% to B (promote)
```

### Implementation

```python
# packages/intelligence/router/ab_manager.py

class ABTestManager:
    def __init__(self):
        self._tests = {}  # test_id -> config
    
    def create_test(self, test_id: str, variant_a: str, variant_b: str,
                   metric: str, minimum_delta: float = 0.05):
        self._tests[test_id] = {
            "variant_a": variant_a,
            "variant_b": variant_b,
            "metric": metric,
            "minimum_delta": minimum_delta,
            "traffic_split": {"a": 0.95, "b": 0.05},
            "results_a": [],
            "results_b": [],
            "status": "active"
        }
    
    def route_variant(self, test_id: str) -> str:
        """Get variant for this request."""
        import random
        test = self._tests[test_id]
        if random.random() < test["traffic_split"]["b"]:
            return "b"
        return "a"]
    
    def record_result(self, test_id: str, variant: str, value: float):
        """Record outcome."""
        test = self._tests[test_id]
        if variant == "a":
            test["results_a"].append(value)
        else:
            test["results_b"].append(value)
        
        # Check if should promote
        self._check_promotion(test_id)
    
    def _check_promotion(self, test_id: str):
        """Check if B should be promoted."""
        test = self._tests[test_id]
        
        if len(test["results_a"]) < 100 or len(test["results_b"]) < 100:
            return  # Not enough data
        
        # Calculate metric difference
        avg_a = sum(test["results_a"]) / len(test["results_a"])
        avg_b = sum(test["results_b"]) / len(test["results_b"])
        delta = abs(avg_b - avg_a) / avg_a
        
        if delta > test["minimum_delta"]:
            # Increase traffic to B
            test["traffic_split"]["b"] = min(0.5, test["traffic_split"]["b"] + 0.1)
            
            if test["traffic_split"]["b"] >= 0.5 and delta > 0.10:
                test["status"] = "promoted"
                test["winner"] = "b"
```

### ORACLE REVIEW REQUIRED
Before activating production A/B tests, Oracle must verify:
- All components stable
- Fallbacks working
- Monitoring in place

### Success Criteria
- [ ] 4 A/B tests running
- [ ] Auto-promotion working
- [ ] No negative impact on users

---

## Task 8.4: Real Health Checks

### What It Does
Replace fake "always healthy" checks with real component-specific checks.

### Health Check Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    L0 (Pre-flight)                      │
│  • File permissions                                     │
│  • Config valid                                         │
│  • Database accessible                                  │
├─────────────────────────────────────────────────────────┤
│                    L1 (Services)                         │
│  • MCP servers alive                                    │
│  • Model endpoints responding                           │
│  • VPN proxies available                                │
├─────────────────────────────────────────────────────────┤
│                    L2 (Deep)                             │
│  • Database queries work                                │
│  • Graph queries work                                   │
│  • ML models load                                       │
│  • Routing accuracy > threshold                         │
├─────────────────────────────────────────────────────────┤
│                    L3 (Integration)                      │
│  • End-to-end routing works                             │
│  • All fallbacks tested                                 │
│  • A/B tests running                                    │
└─────────────────────────────────────────────────────────┘
```

### Health Check Implementation

```python
# packages/monitoring/health.py

class ComponentHealth:
    def __init__(self):
        self._checks = {
            "semantic": self._check_semantic,
            "graph": self._check_graph,
            "meta": self._check_meta,
            "bayesian": self._check_bayesian,
        }
    
    async def check_all(self) -> dict:
        """Run all health checks."""
        results = {}
        
        for name, check in self._checks.items():
            try:
                start = time.perf_counter()
                await check()
                latency = (time.perf_counter() - start) * 1000
                
                results[name] = {
                    "status": "healthy",
                    "latency_ms": latency
                }
            except Exception as e:
                results[name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        # Overall status
        all_healthy = all(r["status"] == "healthy" for r in results.values())
        
        return {
            "overall": "healthy" if all_healthy else "degraded",
            "components": results,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _check_semantic(self):
        """Check semantic classifier."""
        from packages.intelligence.router.semantic_classifier import SemanticTaskClassifier
        c = SemanticTaskClassifier()
        result = c.classify("test task")
        assert result is not None
    
    async def _check_graph(self):
        """Check graph store."""
        from packages.memory_core.stores.graph_store import Neo4jGraphStore
        g = Neo4jGraphStore()
        assert g.stats()["connected"]
    
    async def _check_meta(self):
        """Check meta-learning."""
        from packages.learning_engine.meta.strategy_selector import LinUCBStrategySelector
        s = LinUCBStrategySelector()
        assert len(s.strategies) > 0
    
    async def _check_bayesian(self):
        """Check Bayesian tracker."""
        from packages.learning_engine.bayesian.confidence import BayesianAgentTracker
        t = BayesianAgentTracker()
        assert t is not None
```

### Success Criteria
- [ ] All 4 levels checkable
- [ ] Individual component status
- [ ] Auto-restart on failure

---

## Task 8.5: Rollback Procedures

### Documented Rollbacks

| Phase | Rollback Command | Time |
|-------|------------------|------|
| 0 | `git checkout packages/learning_engine/` | 30s |
| 1 | `SEMANTIC_ENABLED=false` | 10s |
| 2 | `USE_GRAPH=false` | 10s |
| 3 | `META_ENABLED=false` | 10s |
| 4 | `REWARD_DIMENSIONS=1` | 10s |
| 5 | `CROSS_SESSION_ENABLED=false` | 10s |
| 6 | `PROMPT_EVOLUTION_ENABLED=false` | 10s |
| 7 | `BAYESIAN_ENABLED=false` | 10s |
| 8 | `git checkout` + restart | 60s |

### Rollback Script

```bash
# scripts/emergency_rollback.sh

#!/bin/bash
set -e

PHASE=${1:-all}
echo "Rolling back Phase: $PHASE"

case $PHASE in
  0|all)
    echo "[Phase 0] Reverting ML dependencies..."
    git checkout packages/learning_engine/
    ;;
  1)
    echo "[Phase 1] Disabling semantic routing..."
    echo "SEMANTIC_ENABLED=false" >> .env
    ;;
  2)
    echo "[Phase 2] Disabling graph..."
    echo "USE_GRAPH=false" >> .env
    ;;
  3)
    echo "[Phase 3] Disabling meta-learning..."
    echo "META_ENABLED=false" >> .env
    ;;
  4)
    echo "[Phase 4] Reducing reward dimensions..."
    echo "REWARD_DIMENSIONS=1" >> .env
    ;;
  5)
    echo "[Phase 5] Disabling cross-session..."
    echo "CROSS_SESSION_ENABLED=false" >> .env
    ;;
  6)
    echo "[Phase 6] Disabling prompt evolution..."
    echo "PROMPT_EVOLUTION_ENABLED=false" >> .env
    ;;
  7)
    echo "[Phase 7] Disabling Bayesian..."
    echo "BAYESIAN_ENABLED=false" >> .env
    ;;
  8)
    echo "[Phase 8] Full rollback..."
    git checkout
    pkill -f "integrated_router"
    sleep 2
    echo "Restarting services..."
    # Restart commands
    ;;
esac

echo "Rollback complete for Phase $PHASE"
```

### Success Criteria
- [ ] All rollbacks tested
- [ ] < 60s for full rollback
- [ ] Documentation complete

---

## Go/No-Go Criteria (GO LIVE)

| Criterion | Threshold |
|-----------|-----------|
| Integration tests | 100% pass |
| P95 latency | < 200ms |
| P99 latency | < 500ms |
| All A/B tests | Running |
| Health checks | All green |
| Rollback tested | Yes |
| Documentation | Complete |

---

## Files Modified

| File | Action | Description |
|------|--------|-------------|
| `packages/intelligence/router/integrated.py` | CREATE | Full pipeline |
| `tests/integration/test_integrated_router.py` | CREATE | Integration tests |
| `tests/benchmark/integrated_benchmark.py` | CREATE | Benchmark script |
| `packages/intelligence/router/ab_manager.py` | CREATE | A/B test manager |
| `packages/monitoring/health.py` | CREATE | Health checks |
| `scripts/emergency_rollback.sh` | CREATE | Rollback script |

---

## 🎉 GO LIVE CHECKLIST

- [ ] Phase 0-7 implemented
- [ ] Integration tests pass
- [ ] Benchmark meets targets
- [ ] A/B tests running
- [ ] Health checks pass
- [ ] Rollback tested
- [ ] Documentation complete
- [ ] **PRODUCTION DEPLOY**

---

*Phase 8 complete. System ready for production.*

*See `.sisyphus/plans/DENSE-MASTERPLAN.md` for overview.*

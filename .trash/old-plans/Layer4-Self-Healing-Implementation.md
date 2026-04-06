# Layer 4: Self-Healing — Implementation Plan

> **Philosophy**: "We synthesize Frankenstein — stitch together what works from ALL sources, discard what failed."
> **Status**: Research Complete — Ready for Implementation
> **Context**: N-Xyme MIND v1.0, Python-only, MIT-licensed

---

## TL;DR

**Quick Summary**: Implement comprehensive self-healing system with circuit breaker integration, 4-tier graceful degradation, composite health scoring (0-100), and tool/context fallback chains. Build on existing health_core.py, circuit_breaker.py, and health_endpoint.py.

**Deliverables**:
- `health_monitor.py` — ENHANCE existing src/health_core.py with composite scoring
- `self_healer.py` — ENHANCE existing src/self_healer.py with degradation tiers
- `auto_recovery.py` — NEW: 4-tier autonomous recovery (openclaw patterns)
- `checkpoint_resume.py` — NEW: LangGraph-style state persistence

**Estimated Effort**: Medium-Large (15-20 tasks across 3 waves)
**Parallel Execution**: YES — 3 waves with maximum parallelism
**Critical Path**: health_schema → composite_scorer → degradation_tiers → auto_recovery → checkpoint_resume

---

## Context

### Original Request
Create a DENSE, ROBUST implementation plan for Layer 4: Self-Healing with:
- Circuit breaker (openclaw pattern: closed→open→half_open)
- Health check endpoints (liveness/readiness probes)
- Multi-tier graceful degradation (4 tiers: Full→Core→Minimal→Degraded)
- Composite health scoring (0-100: response time, error rate, resource, quality)
- Tool/context fallback chains (beyond model fallback)
- Standardized health score schema

### Interview Summary
**Key Discussions**:
- Existing health_core.py: Basic component registration with cache
- Existing circuit_breaker.py: Full CLOSED/OPEN/HALF_OPEN implementation (NEEDS INTEGRATION)
- Existing health_endpoint.py: /health, /live, /ready, /metrics endpoints
- Existing health_recovery.py: Auto-healing with restart/clear_cache/wait actions
- Missing: Composite scoring, degradation tiers, fallback chains, checkpoint/resume

**Research Findings**:
- openclaw/openclaw: Circuit breaker + loop detection (331K⭐) — PATTERNS APPLICABLE
- code-yeongyu/oh-my-openagent: Fallback chain system — PATTERNS APPLICABLE
- n8n-io/n8n: Circuit breaker utility — PATTERNS APPLICABLE
- getsentry/sentry: CircuitBreaker2 (OK/BROKEN/RECOVERY states) — PATTERNS APPLICABLE

### Metis Review
**Identified Gaps** (addressed in plan):
- Circuit breaker exists but NOT integrated with health_core — ADD INTEGRATION
- Composite scoring needs dependency-weighted algorithm — ADD health_composite.py
- No 4-tier degradation defined — ADD degradation_tiers.py with Full/Core/Minimal/Degraded
- Tool/context fallback chains completely missing — ADD fallback_registry.py
- No checkpoint/resume for long-running operations — ADD checkpoint_resume.py
- Health score schema not standardized — ADD health_schema.py

---

## Work Objectives

### Core Objective
Build a comprehensive self-healing system that:
1. Monitors component health with composite 0-100 scoring
2. Protects against cascading failures via circuit breaker
3. Provides 4-tier graceful degradation when degradation detected
4. Automatically recovers via tiered recovery strategies
5. Persists state for long-running operation resume

### Concrete Deliverables
- Enhanced `src/health_core.py` — Composite scoring, dependency graph, schema
- Enhanced `src/self_healer.py` — 4-tier degradation actions
- New `src/auto_recovery.py` — 4-tier recovery state machine
- New `src/checkpoint_resume.py` — LangGraph-style persistence
- New `src/fallback_registry.py` — Tool/context fallback chains
- New `src/health_schema.py` — Standardized health score schema

### Definition of Done
- [ ] All health checks return standardized 0-100 composite score
- [ ] Circuit breaker integrated with health monitoring
- [ ] 4-tier degradation (Full→Core→Minimal→Degraded) operational
- [ ] Fallback chains work for tools AND context sources
- [ ] Checkpoint/resume preserves state across restarts
- [ ] /live and /ready endpoints return correct status

### Must Have
- Composite health scoring with weighted component dependencies
- Circuit breaker state visible in health report
- Graceful degradation triggers automatically based on score thresholds
- Fallback chains support parallel and sequential fallback strategies
- Checkpoint persistence includes agent state, memory, and workflow position

### Must NOT Have (Guardrails)
- No hardcoded service names — all configurable
- No blocking operations in health checks (timeout required)
- No cascade failures from healing actions (isolation required)
- No data loss on checkpoint (atomic writes required)
- No circular fallback chains (detection required)

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (pytest, existing test files)
- **Automated tests**: YES (TDD approach)
- **Framework**: pytest + pytest-asyncio
- **TDD**: Each new class/function has corresponding test

### QA Policy
Every task includes agent-executed QA scenarios (Playwright for browser, interactive_bash for CLI, curl for API).

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — schema + scoring + breaker integration):
├── Task 1: Health schema definitions [quick]
├── Task 2: Composite health scorer [deep]
├── Task 3: Circuit breaker integration [deep]
├── Task 4: Enhanced health endpoint with scoring [quick]
└── Task 5: Health check definitions (response_time, error_rate, resource, quality) [quick]

Wave 2 (Recovery + Degradation):
├── Task 6: Degradation tier definitions [quick]
├── Task 7: Fallback registry (tools) [deep]
├── Task 8: Fallback registry (context) [deep]
├── Task 9: Auto-recovery state machine [deep]
├── Task 10: Self-healer enhancement with tiers [deep]
└── Task 11: Integration test: recovery flow [unspecified-high]

Wave 3 (Persistence + Polish):
├── Task 12: Checkpoint persistence [deep]
├── Task 13: Resume mechanism [deep]
├── Task 14: Checkpoint API endpoints [quick]
├── Task 15: ML predictor integration [unspecified-high]
├── Task 16: End-to-end integration test [unspecified-high]
└── Task 17: Documentation + examples [quick]

Wave FINAL (Verification):
├── Task F1: Plan compliance audit [oracle]
├── Task F2: Code quality review [unspecified-high]
├── Task F3: Real manual QA [unspecified-high]
└── Task F4: Scope fidelity check [deep]
```

### Dependency Matrix
- **Tasks 1-5**: No dependencies (Wave 1 parallel)
- **Task 6**: Depends on 1-5 (needs scoring + schema)
- **Tasks 7-8**: Depends on 1-5 (need scoring + schema)
- **Task 9**: Depends on 6, 7, 8 (needs all components)
- **Task 10**: Depends on 6, 9 (needs tier + auto-recovery)
- **Task 11**: Depends on 10 (needs full system)
- **Task 12**: Depends on 1-5 (needs schema)
- **Task 13**: Depends on 12 (needs checkpoint)
- **Task 14**: Depends on 12-13 (needs both)
- **Task 15**: Depends on 1-5 (needs scoring)
- **Task 16**: Depends on 11, 14 (integration)
- **Task 17**: Depends on all (final polish)

---

## TODOs

---

- [ ] 1. Health Schema Definitions

  **What to do**:
  - Define `HealthScore` dataclass with 0-100 composite score
  - Define `ComponentMetrics` for individual metric tracking
  - Define `HealthThresholds` for warning/critical levels
  - Create `HealthSchema` class with validation
  - Define metric weights: response_time (0.25), error_rate (0.30), resource (0.25), quality (0.20)

  **Must NOT do**:
  - No hardcoded thresholds — all configurable
  - No blocking calculations — use async/caching

  **Recommended Agent Profile**:
  > **Category**: `deep`
  >   Reason: Schema design requires careful thought about extensibility
  > **Skills**: [`python-typing`, `data-validation`]
  >   - `python-typing`: Strong typing for health metrics
  >   - `data-validation`: Schema validation patterns

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2-5)
  - **Blocks**: Tasks 6-16
  - **Blocked By**: None (start immediately)

  **References**:
  - `src/health_core.py:33-55` — HealthMetric, ComponentStatus patterns
  - `src/health_core.py:58-106` — HealthMonitor class structure

  **Acceptance Criteria**:
  - [ ] Schema validates composite score 0-100 range
  - [ ] ComponentMetrics tracks all 4 metric types
  - [ ] HealthThresholds configurable per component

  **QA Scenarios**:

  Scenario: Schema validation — valid score
    Tool: Bash (pytest)
    Preconditions: health_schema.py implemented
    Steps:
      1. cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
      2. python -c "from src.health_schema import HealthScore; s = HealthScore(component='test', total=85.0); print(s.total)"
    Expected Result: Output shows 85.0
    Evidence: .sisyphus/evidence/task-1-schema-valid.json

  Scenario: Schema validation — invalid score (out of range)
    Tool: Bash (pytest)
    Preconditions: health_schema.py implemented
    Steps:
      1. cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
      2. python -c "from src.health_schema import HealthScore; s = HealthScore(component='test', total=150)"
    Expected Result: Raises ValidationError
    Evidence: .sisyphus/evidence/task-1-schema-invalid.json

  **Commit**: YES
  - Message: `feat(health): Add standardized health score schema`
  - Files: `src/health_schema.py`
  - Pre-commit: `python -m py_compile src/health_schema.py`

---

- [ ] 2. Composite Health Scorer

  **What to do**:
  - Implement `CompositeHealthScorer` class
  - Calculate weighted score: response_time (25%), error_rate (30%), resource (25%), quality (20%)
  - Handle component dependency graph (critical path weighting)
  - Implement exponential decay for stale metrics
  - Add score trend calculation (improving/degrading/stable)

  **Must NOT do**:
  - No blocking calculations in hot path
  - No memory leaks from metric accumulation

  **Recommended Agent Profile**:
  > **Category**: `deep`
  >   Reason: Complex weighted scoring algorithm with dependency handling
  > **Skills**: [`algorithm-design`, `performance`]
  >   - `algorithm-design`: Weighted scoring with dependency graph
  >   - `performance`: Avoid blocking in health checks

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3-5)
  - **Blocks**: Tasks 6-10, 15-16
  - **Blocked By**: None (start immediately)

  **References**:
  - `src/health_core.py:137-151` — get_overall_health() existing logic
  - `src/plugin_health_ml.py` — PluginHealthPredictor sliding window pattern

  **Acceptance Criteria**:
  - [ ] Composite score returns 0-100 range
  - [ ] Weighted calculation matches specified percentages
  - [ ] Dependency graph affects critical components more
  - [ ] Stale metrics decay appropriately

  **QA Scenarios**:

  Scenario: Weighted scoring — balanced metrics
    Tool: Bash (pytest)
    Preconditions: health_composite.py implemented
    Steps:
      1. cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
      2. python -c "
from src.health_composite import CompositeHealthScorer
scorer = CompositeHealthScorer()
# Simulate balanced metrics
metrics = {'response_time': 50, 'error_rate': 50, 'resource': 50, 'quality': 50}
score = scorer.calculate(metrics)
print(f'Score: {score}')
"
    Expected Result: Score around 50
    Evidence: .sisyphus/evidence/task-2-scoring-balanced.json

  Scenario: Weighted scoring — high error rate penalization
    Tool: Bash (pytest)
    Preconditions: health_composite.py implemented
    Steps:
      1. cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
      2. python -c "
from src.health_composite import CompositeHealthScorer
scorer = CompositeHealthScorer()
# High error rate should drop score significantly
metrics = {'response_time': 90, 'error_rate': 10, 'resource': 90, 'quality': 90}
score = scorer.calculate(metrics)
print(f'Score: {score}')
"
    Expected Result: Score significantly lower due to 30% weight on error_rate
    Evidence: .sisyphus/evidence/task-2-scoring-error-penalty.json

  **Commit**: YES
  - Message: `feat(health): Add composite health scoring with weighted metrics`
  - Files: `src/health_composite.py`
  - Pre-commit: `python -m py_compile src/health_composite.py`

---

- [ ] 3. Circuit Breaker Integration

  **What to do**:
  - Integrate existing circuit_breaker.py with health_core.py
  - Create `CircuitBreakerMiddleware` class
  - Wire circuit state into health check responses
  - Add auto-trip when component consistently fails (integrate with composite scorer)
  - Expose circuit state in health report

  **Must NOT do**:
  - No duplicate circuit breaker instances
  - No blocking on circuit state checks

  **Recommended Agent Profile**:
  > **Category**: `deep`
  >   Reason: Integration work requires understanding both systems
  > **Skills**: [`system-integration`, `fault-tolerance`]
  >   - `system-integration`: Connect circuit_breaker with health_core
  >   - `fault-tolerance`: Ensure no cascade failures

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1-2, 4-5)
  - **Blocks**: Tasks 9-11
  - **Blocked By**: None (start immediately)

  **References**:
  - `src/circuit_breaker.py:23-101` — CircuitBreaker class
  - `src/circuit_breaker.py:103-140` — CircuitBreakerRegistry
  - `src/health_core.py:66-115` — HealthMonitor registration pattern

  **Acceptance Criteria**:
  - [ ] Circuit state visible in health report
  - [ ] Auto-trip triggers on failure threshold
  - [ ] Half-open state allows recovery probes
  - [ ] No blocking in health check path

  **QA Scenarios**:

  Scenario: Circuit integration — open circuit shows in health
    Tool: Bash (pytest)
    Preconditions: Circuit integration implemented
    Steps:
      1. cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
      2. python -c "
from src.health_core import HealthMonitor
from src.circuit_breaker import get_circuit_breaker

monitor = HealthMonitor()
cb = get_circuit_breaker('test-service')
# Simulate failures to open circuit
for i in range(3):
    try:
        cb.call(lambda: 1/0)
    except:
        pass
print(cb.get_state())
"
    Expected Result: Circuit state is OPEN
    Evidence: .sisyphus/evidence/task-3-circuit-open.json

  Scenario: Circuit integration — health report includes circuit state
    Tool: Bash (pytest)
    Preconditions: Circuit integration implemented
    Steps:
      1. cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
      2. python -c "
from src.health_core import HealthMonitor
from src.health_composite import CompositeHealthScorer

monitor = HealthMonitor()
scorer = CompositeHealthScorer()
report = monitor.get_full_report()
print('Circuit states in report:', 'circuit' in str(report).lower())
"
    Expected Result: Report includes circuit information
    Evidence: .sisyphus/evidence/task-3-circuit-report.json

  **Commit**: YES
  - Message: `feat(health): Integrate circuit breaker with health monitoring`
  - Files: `src/health_core.py` (enhanced)
  - Pre-commit: `python -m py_compile src/health_core.py`

---

- [ ] 4. Enhanced Health Endpoint with Scoring

  **What to do**:
  - Enhance existing health_endpoint.py with composite scoring
  - Add /metrics endpoint with Prometheus-format output
  - Add scoring breakdown in /health response
  - Implement proper liveness (/live) vs readiness (/ready) semantics

  **Must NOT do**:
  - No blocking in endpoint handlers
  - No exposure of internal circuit breaker states to unauthorized clients

  **Recommended Agent Profile**:
  > **Category**: `quick`
  >   Reason: Endpoint enhancement is straightforward
  > **Skills**: [`fastapi-or-aiohttp`, `api-design`]
  >   - `fastapi-or-aiohttp`: Existing endpoint framework
  >   - `api-design`: Proper REST semantics

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1-3, 5)
  - **Blocks**: Task 16
  - **Blocked By**: None (start immediately)

  **References**:
  - `src/health_endpoint.py` — Existing endpoint implementation

  **Acceptance Criteria**:
  - [ ] /live returns 200 when process alive
  - [ ] /ready returns 200 when all dependencies healthy
  - [ ] /health includes composite scores
  - [ ] /metrics outputs Prometheus format

  **QA Scenarios**:

  Scenario: Endpoint — liveness probe
    Tool: Bash (curl)
    Preconditions: Health endpoint running
    Steps:
      1. curl -s http://localhost:8080/live
    Expected Result: 200 OK
    Evidence: .sisyphus/evidence/task-4-live.json

  Scenario: Endpoint — readiness probe with degraded component
    Tool: Bash (curl)
    Preconditions: Health endpoint running with one degraded component
    Steps:
      1. curl -s http://localhost:8080/ready
    Expected Result: 503 Service Unavailable (if critical component degraded)
    Evidence: .sisyphus/evidence/task-4-ready-degraded.json

  **Commit**: YES
  - Message: `feat(health): Enhance health endpoints with composite scoring`
  - Files: `src/health_endpoint.py`
  - Pre-commit: `python -m py_compile src/health_endpoint.py`

---

- [ ] 5. Health Check Definitions

  **What to do**:
  - Create comprehensive health check functions for all 4 metrics:
    - `check_response_time()`: Timing-based check with thresholds
    - `check_error_rate()`: Success/failure tracking over time window
    - `check_resource()`: CPU, memory, disk usage thresholds
    - `check_quality()`: Output quality metrics (where applicable)
  - Integrate with existing health_checks.py
  - Add thresholds: warning (70), critical (40) for composite score

  **Must NOT do**:
  - No blocking checks that could deadlock
  - No hardcoded service-specific checks

  **Recommended Agent Profile**:
  > **Category**: `quick`
  >   Reason: Standard health check patterns
  > **Skills**: [`system-monitoring`, `metrics`]
  >   - `system-monitoring`: CPU, memory, disk checks
  >   - `metrics`: Time-series metric tracking

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1-4)
  - **Blocks**: Tasks 6, 15
  - **Blocked By**: None (start immediately)

  **References**:
  - `src/health_checks.py` — Existing check factories
  - `src/direct_health.py` — Low-level check functions

  **Acceptance Criteria**:
  - [ ] All 4 metric types implemented
  - [ ] Warning/critical thresholds configurable
  - [ ] Async-compatible (non-blocking)

  **Commit**: YES
  - Message: `feat(health): Add 4-metric health check definitions`
  - Files: `src/health_checks.py` (enhanced)
  - Pre-commit: `python -m py_compile src/health_checks.py`

---

- [ ] 6. Degradation Tier Definitions

  **What to do**:
  - Define 4 degradation tiers:
    - **FULL** (score 100-80): All features enabled
    - **CORE** (score 79-60): Non-critical features disabled, core functionality maintained
    - **MINIMAL** (score 59-40): Only essential features, increased caching
    - **DEGRADED** (score 39-0): Emergency mode, minimal functionality
  - Create `DegradationTier` enum and mapping
  - Define per-component tier behaviors
  - Implement tier transition logic

  **Must NOT do**:
  - No abrupt tier jumps — require sustained score changes
  - No data loss during tier transitions

  **Recommended Agent Profile**:
  > **Category**: `deep`
  >   Reason: State machine design for tier transitions
  > **Skills**: [`state-machine`, `fault-tolerance`]
  >   - `state-machine`: Tier transition logic
  >   - `fault-tolerance`: Ensure no data loss

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (after Wave 1)
  - **Blocks**: Tasks 9-11
  - **Blocked By**: Tasks 1-5

  **References**:
  - `src/health_core.py:24-30` — ComponentHealth enum pattern

  **Acceptance Criteria**:
  - [ ] All 4 tiers defined with clear boundaries
  - [ ] Tier transitions require sustained changes (not momentary blips)
  - [ ] Component-specific tier behaviors defined

  **QA Scenarios**:

  Scenario: Degradation — score 85 maps to FULL tier
    Tool: Bash (pytest)
    Preconditions: Degradation tiers implemented
    Steps:
      1. cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
      2. python -c "
from src.degradation_tiers import get_tier, DegradationTier
tier = get_tier(85)
print(f'Tier: {tier}')
"
    Expected Result: Tier.FULL
    Evidence: .sisyphus/evidence/task-6-tier-full.json

  Scenario: Degradation — score 55 maps to MINIMAL tier
    Tool: Bash (pytest)
    Preconditions: Degradation tiers implemented
    Steps:
      1. cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
      2. python -c "
from src.degradation_tiers import get_tier, DegradationTier
tier = get_tier(55)
print(f'Tier: {tier}')
"
    Expected Result: Tier.MINIMAL
    Evidence: .sisyphus/evidence/task-6-tier-minimal.json

  **Commit**: YES
  - Message: `feat(health): Add 4-tier graceful degradation definitions`
  - Files: `src/degradation_tiers.py`
  - Pre-commit: `python -m py_compile src/degradation_tiers.py`

---

- [ ] 7. Fallback Registry (Tools)

  **What to do**:
  - Create `FallbackRegistry` class for tool fallback chains
  - Implement decorator pattern: `@fallback_chain(primary, fallback1, fallback2)`
  - Support parallel fallback (try all, use first success)
  - Support sequential fallback (try primary, then fallback)
  - Integrate with circuit breaker state

  **Must NOT do**:
  - No circular fallback detection (prevent infinite loops)
  - No blocking on fallback selection

  **Recommended Agent Profile**:
  > **Category**: `deep`
  >   Reason: Complex fallback chain logic with integration requirements
  > **Skills**: [`decorator-pattern`, `fault-tolerance`]
  >   - `decorator-pattern`: Clean fallback wrapping
  >   - `fault-tolerance`: Circuit breaker integration

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (with Task 8)
  - **Blocks**: Tasks 9-11, 16
  - **Blocked By**: Tasks 1-5

  **References**:
  - `src/circuit_breaker.py:29-33` — CircuitBreakerOpen exception
  - code-yeongyu/oh-my-openagent patterns (from research)

  **Acceptance Criteria**:
  - [ ] Primary tool fails → automatic fallback to next
  - [ ] Circuit breaker open → skip to fallback
  - [ ] All fallbacks fail → raise composite exception
  - [ ] Circular detection prevents infinite loops

  **QA Scenarios**:

  Scenario: Fallback — primary fails, fallback succeeds
    Tool: Bash (pytest)
    Preconditions: Fallback registry implemented
    Steps:
      1. cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
      2. python -c "
from src.fallback_registry import FallbackRegistry

registry = FallbackRegistry()
def primary(): raise Exception('fail')
def fallback(): return 'success'

result = registry.execute_chain([primary, fallback])
print(f'Result: {result}')
"
    Expected Result: Result is 'success'
    Evidence: .sisyphus/evidence/task-7-fallback-success.json

  Scenario: Fallback — all tools fail
    Tool: Bash (pytest)
    Preconditions: Fallback registry implemented
    Steps:
      1. cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
      2. python -c "
from src.fallback_registry import FallbackRegistry

registry = FallbackRegistry()
def fail1(): raise Exception('fail1')
def fail2(): raise Exception('fail2')

try:
    result = registry.execute_chain([fail1, fail2])
except Exception as e:
    print(f'Exception: {e}')
"
    Expected Result: Composite exception with both failures
    Evidence: .sisyphus/evidence/task-7-fallback-all-fail.json

  **Commit**: YES
  - Message: `feat(health): Add tool fallback registry with chain support`
  - Files: `src/fallback_registry.py`
  - Pre-commit: `python -m py_compile src/fallback_registry.py`

---

- [ ] 8. Fallback Registry (Context)

  **What to do**:
  - Extend FallbackRegistry for context sources
  - Implement context fallback: vector_store → sql_cache → memory_only
  - Add context-specific recovery actions (rebuild index, reload cache)
  - Integrate with memory system (session_memory, knowledge_graph)

  **Must NOT do**:
  - No blocking on context fallback (async required)
  - No data loss during context fallback

  **Recommended Agent Profile**:
  > **Category**: `deep`
  >   Reason: Context integration with existing memory systems
  > **Skills**: [`data-layer`, `cache-strategies`]
  >   - `data-layer`: Database/cache integration
  >   - `cache-strategies`: SQL cache, memory fallback

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (with Task 7)
  - **Blocks**: Tasks 9-11, 16
  - **Blocked By**: Tasks 1-5

  **References**:
  - `src/session_memory.py` — Existing memory system
  - `src/metrics_store.py` — Metrics persistence

  **Acceptance Criteria**:
  - [ ] Vector store fails → SQL cache fallback
  - [ ] SQL cache fails → memory-only fallback
  - [ ] Context recovery rebuilds indexes on restore
  - [ ] All fallbacks fail → graceful degradation to minimal

  **Commit**: YES
  - Message: `feat(health): Add context fallback registry with multi-tier fallback`
  - Files: `src/fallback_registry.py` (enhanced)
  - Pre-commit: `python -m py_compile src/fallback_registry.py`

---

- [ ] 9. Auto-Recovery State Machine

  **What to do**:
  - Create `AutoRecovery` class with 4-tier recovery states
  - Implement state machine: DETECT → ASSESS → RECOVER → VERIFY → COMPLETE
  - Add recovery strategies per tier:
    - FULL: Self-heal (restart, clear cache)
    - CORE: Degrade non-critical, retry
    - MINIMAL: Emergency recovery, reduce load
    - DEGRADED: Preserve state, await manual intervention
  - Add recovery timeout and max retries

  **Must NOT do**:
  - No recursive recovery attempts (max 3 per incident)
  - No blocking recovery actions in health check path

  **Recommended Agent Profile**:
  > **Category**: `deep`
  >   Reason: Complex state machine with multiple recovery paths
  > **Skills**: [`state-machine`, `workflow-automation`]
  >   - `state-machine`: Recovery state transitions
  >   - `workflow-automation`: Recovery action sequencing

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (after Tasks 6-8)
  - **Blocks**: Tasks 10-11, 16
  - **Blocked By**: Tasks 6-8

  **References**:
  - `src/health_recovery.py:37-83` — Existing recovery logic
  - `src/self_healer.py:70-174` — Self-healer pattern

  **Acceptance Criteria**:
  - [ ] State machine transitions correctly
  - [ ] Each tier has appropriate recovery actions
  - [ ] Recovery timeout prevents infinite loops
  - [ ] Verification confirms recovery success

  **QA Scenarios**:

  Scenario: Recovery — tier CORE triggers correct actions
    Tool: Bash (pytest)
    Preconditions: Auto-recovery implemented
    Steps:
      1. cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
      2. python -c "
from src.auto_recovery import AutoRecovery, RecoveryTier

recovery = AutoRecovery()
# Simulate CORE tier
result = recovery.execute_recovery('ollama', RecoveryTier.CORE)
print(f'Actions: {result.actions}')
"
    Expected Result: Actions include degrade, retry
    Evidence: .sisyphus/evidence/task-9-recovery-core.json

  Scenario: Recovery — verification confirms success
    Tool: Bash (pytest)
    Preconditions: Auto-recovery implemented
    Steps:
      1. cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
      2. python -c "
from src.auto_recovery import AutoRecovery

recovery = AutoRecovery()
result = recovery.verify_recovery('ollama')
print(f'Verified: {result.success}')
"
    Expected Result: Verification returns success status
    Evidence: .sisyphus/evidence/task-9-recovery-verify.json

  **Commit**: YES
  - Message: `feat(health): Add 4-tier auto-recovery state machine`
  - Files: `src/auto_recovery.py`
  - Pre-commit: `python -m py_compile src/auto_recovery.py`

---

- [ ] 10. Self-Healer Enhancement with Tiers

  **What to do**:
  - Enhance existing self_healer.py with tier awareness
  - Add tier-specific healing policies
  - Integrate with AutoRecovery and DegradationTier
  - Add cooldown tracking per tier level

  **Must NOT do**:
  - No breaking changes to existing API
  - No loss of existing healing policies

  **Recommended Agent Profile**:
  > **Category**: `deep`
  >   Reason: Enhancement of existing system without breaking changes
  > **Skills**: [`api-compatibility`, `system-extension`]
  >   - `api-compatibility`: Maintain existing interface
  >   - `system-extension`: Add tier features cleanly

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (after Task 9)
  - **Blocks**: Task 11, 16
  - **Blocked By**: Tasks 6, 9

  **References**:
  - `src/self_healer.py:70-174` — Existing SelfHealer class

  **Acceptance Criteria**:
  - [ ] Existing API still works
  - [ ] New tier-based policies execute correctly
  - [ ] Cooldown per tier prevents rapid cycling

  **Commit**: YES
  - Message: `feat(health): Enhance self-healer with tier-aware policies`
  - Files: `src/self_healer.py` (enhanced)
  - Pre-commit: `python -m py_compile src/self_healer.py`

---

- [ ] 11. Integration Test: Recovery Flow

  **What to do**:
  - Create integration test covering full recovery flow
  - Test: failure detection → tier assessment → recovery action → verification
  - Test: circuit breaker integration throughout
  - Test: fallback chain triggers

  **Must NOT do**:
  - No mock-only tests (require real component behavior where possible)
  - No test that depends on external services being up

  **Recommended Agent Profile**:
  > **Category**: `unspecified-high`
  >   Reason: Integration testing requires broad system understanding
  > **Skills**: [`integration-testing`, `test-automation`]
  >   - `integration-testing`: Full flow testing
  >   - `test-automation`: pytest patterns

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (final task)
  - **Blocks**: Wave 3
  - **Blocked By**: Tasks 6-10

  **References**:
  - `tests/integration/` — Existing integration test patterns
  - `src/health_recovery.py:192-203` — get_stats() pattern

  **Acceptance Criteria**:
  - [ ] Full recovery flow test passes
  - [ ] Circuit breaker integration test passes
  - [ ] Fallback chain integration test passes

  **Commit**: YES
  - Message: `test(health): Add integration test for recovery flow`
  - Files: `tests/integration/test_health_recovery.py`
  - Pre-commit: `pytest tests/integration/test_health_recovery.py`

---

- [ ] 12. Checkpoint Persistence

  **What to do**:
  - Create `CheckpointManager` class for state persistence
  - Implement checkpoint creation with atomic writes
  - Support checkpoint metadata: timestamp, component, state_type, checksum
  - Implement cleanup of old checkpoints (retention policy)

  **Must NOT do**:
  - No blocking writes in main thread (async required)
  - No data loss from partial writes (atomic required)

  **Recommended Agent Profile**:
  > **Category**: `deep`
  >   Reason: Persistent state management with consistency requirements
  > **Skills**: [`persistence`, `atomic-operations`]
  >   - `persistence`: Checkpoint storage
  >   - `atomic-operations`: Prevent data loss

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (start)
  - **Blocks**: Tasks 13-14, 16
  - **Blocked By**: Tasks 1-5, 11

  **References**:
  - `src/langgraph_workflow.py` — Existing state management
  - `src/session_archiver.py` — Archive patterns

  **Acceptance Criteria**:
  - [ ] Checkpoint creation atomic (no partial state)
  - [ ] Checkpoint includes metadata
  - [ ] Retention policy cleans old checkpoints

  **QA Scenarios**:

  Scenario: Checkpoint — atomic write
    Tool: Bash (pytest)
    Preconditions: Checkpoint manager implemented
    Steps:
      1. cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
      2. python -c "
from src.checkpoint_resume import CheckpointManager
import json
import tempfile
import os

with tempfile.TemporaryDirectory() as td:
    cm = CheckpointManager(td)
    ckpt = cm.create_checkpoint('agent-1', {'state': 'test'}, ['memory', 'workflow'])
    print(f'Created: {ckpt.id}')
"
    Expected Result: Checkpoint created with ID
    Evidence: .sisyphus/evidence/task-12-checkpoint-create.json

  **Commit**: YES
  - Message: `feat(health): Add checkpoint persistence with atomic writes`
  - Files: `src/checkpoint_resume.py`
  - Pre-commit: `python -m py_compile src/checkpoint_resume.py`

---

- [ ] 13. Resume Mechanism

  **What to do**:
  - Implement resume from checkpoint functionality
  - Add state validation (checksum verification)
  - Support partial resume (memory only, workflow only)
  - Add resume conflict resolution

  **Must NOT do**:
  - No resume from corrupted checkpoint (validation required)
  - No blocking on resume operation

  **Recommended Agent Profile**:
  > **Category**: `deep`
  >   Reason: Complex state restoration with validation
  > **Skills**: [`state-restoration`, `data-validation`]
  >   - `state-restoration`: Resume from checkpoint
  >   - `data-validation`: Checksum verification

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (after Task 12)
  - **Blocks**: Tasks 14, 16
  - **Blocked By**: Task 12

  **References**:
  - `src/checkpoint_resume.py:Task 12` — Checkpoint creation

  **Acceptance Criteria**:
  - [ ] Resume restores exact state
  - [ ] Corrupted checkpoint rejected
  - [ ] Partial resume works correctly

  **QA Scenarios**:

  Scenario: Resume — from valid checkpoint
    Tool: Bash (pytest)
    Preconditions: Checkpoint created
    Steps:
      1. cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
      2. python -c "
from src.checkpoint_resume import CheckpointManager
import tempfile

with tempfile.TemporaryDirectory() as td:
    cm = CheckpointManager(td)
    ckpt = cm.create_checkpoint('agent-1', {'state': 'test'}, ['memory'])
    restored = cm.resume_checkpoint(ckpt.id)
    print(f'Restored: {restored.state}')
"
    Expected Result: Restored state matches original
    Evidence: .sisyphus/evidence/task-13-resume-valid.json

  Scenario: Resume — from corrupted checkpoint
    Tool: Bash (pytest)
    Preconditions: Corrupted checkpoint file
    Steps:
      1. cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
      2. python -c "
from src.checkpoint_resume import CheckpointManager
import tempfile
import os

with tempfile.TemporaryDirectory() as td:
    cm = CheckpointManager(td)
    # Write corrupted checkpoint
    ckpt_id = cm.create_checkpoint('agent-1', {'state': 'test'}, ['memory']).id
    # Corrupt the file
    with open(os.path.join(td, f'{ckpt_id}.json'), 'w') as f:
        f.write('corrupted')
    # Try to resume
    try:
        cm.resume_checkpoint(ckpt_id)
    except Exception as e:
        print(f'Rejected: {type(e).__name__}')
"
    Expected Result: Exception raised for corrupted checkpoint
    Evidence: .sisyphus/evidence/task-13-resume-corrupted.json

  **Commit**: YES
  - Message: `feat(health): Add resume mechanism with validation`
  - Files: `src/checkpoint_resume.py` (enhanced)
  - Pre-commit: `python -m py_compile src/checkpoint_resume.py`

---

- [ ] 14. Checkpoint API Endpoints

  **What to do**:
  - Add REST endpoints for checkpoint operations
  - POST /checkpoint — create checkpoint
  - GET /checkpoint/{id} — get checkpoint info
  - POST /resume/{id} — resume from checkpoint
  - GET /checkpoints — list available checkpoints

  **Must NOT do** - No blocking endpoint handlers
  - No exposure of internal state to unauthorized clients

  **Recommended Agent Profile**:
  > **Category**: `quick`
  >   Reason: Straightforward REST endpoints
  > **Skills**: [`rest-api`, `endpoint-design`]
  >   - `rest-api`: Standard REST patterns
  >   - `endpoint-design`: Proper HTTP semantics

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (after Task 13)
  - **Blocks**: Task 16
  - **Blocked By**: Tasks 12-13

  **References**:
  - `src/health_endpoint.py` — Existing endpoint patterns

  **Acceptance Criteria**:
  - [ ] All 4 endpoints implemented
  - [ ] Proper HTTP status codes
  - [ ] Async-compatible handlers

  **Commit**: YES
  - Message: `feat(health): Add checkpoint API endpoints`
  - Files: `src/health_endpoint.py` (enhanced)
  - Pre-commit: `python -m py_compile src/health_endpoint.py`

---

- [ ] 15. ML Predictor Integration

  **What to do**:
  - Integrate existing plugin_health_ml.py with health scoring
  - Feed prediction into composite score calculation
  - Add proactive degradation based on predicted failures
  - Add early warning scoring (score - predicted_impact)

  **Must NOT do**:
  - No blocking ML predictions in health check path
  - No ignoring prediction failures (fallback to non-ML scoring)

  **Recommended Agent Profile**:
  > **Category**: `unspecified-high`
  >   Reason: Integration of ML system with health scoring
  > **Skills**: [`ml-integration`, `predictive-analytics`]
  >   - `ml-integration`: Connect ML predictor with health
  >   - `predictive-analytics`: Use predictions for proactive actions

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (with Task 16)
  - **Blocks**: Task 16
  - **Blocked By**: Tasks 1-5

  **References**:
  - `src/plugin_health_ml.py:25-47` — PluginHealthPredictor

  **Acceptance Criteria**:
  - [ ] Predictions influence composite score
  - [ ] Proactive degradation triggers when prediction high risk
  - [ ] Fallback to non-ML scoring if ML unavailable

  **Commit**: YES
  - Message: `feat(health): Integrate ML predictor with composite scoring`
  - Files: `src/health_composite.py` (enhanced)
  - Pre-commit: `python -m py_compile src/health_composite.py`

---

- [ ] 16. End-to-End Integration Test

  **What to do**:
  - Create comprehensive E2E test covering all components
  - Test: Health scoring → Circuit breaker → Fallback → Recovery → Checkpoint
  - Add performance benchmarks (latency, throughput)
  - Add failure injection testing

  **Must NOT do**:
  - No test that requires external services (mock appropriately)
  - No test that takes >30 seconds

  **Recommended Agent Profile**:
  > **Category**: `unspecified-high`
  >   Reason: Comprehensive E2E testing
  > **Skills**: [`e2e-testing`, `performance-testing`]
  >   - `e2e-testing`: Full system testing
  >   - `performance-testing`: Latency/throughput benchmarks

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (final major task)
  - **Blocks**: Task 17
  - **Blocked By**: Tasks 11, 14-15

  **References**:
  - `tests/integration/test_core.py` — Existing E2E tests

  **Acceptance Criteria**:
  - [ ] All components work together
  - [ ] Performance within acceptable bounds
  - [ ] Failure injection handled correctly

  **Commit**: YES
  - Message: `test(health): Add E2E integration test with benchmarks`
  - Files: `tests/integration/test_health_e2e.py`
  - Pre-commit: `pytest tests/integration/test_health_e2e.py`

---

- [ ] 17. Documentation + Examples

  **What to do**:
  - Add docstrings to all new classes and functions
  - Create usage examples in docs/
  - Add API documentation
  - Create architecture diagram

  **Must NOT do**:
  - No documentation without working code examples
  - No outdated documentation

  **Recommended Agent Profile**:
  > **Category**: `quick`
  >   Reason: Documentation is straightforward
  > **Skills**: [`technical-writing`, `documentation`]
  >   - `technical-writing`: Clear explanations
  >   - `documentation`: Docstrings, examples

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (final)
  - **Blocks**: None
  - **Blocked By**: Tasks 1-16

  **Acceptance Criteria**:
  - [ ] All public APIs documented
  - [ ] Working examples for key use cases
  - [ ] Architecture diagram accurate

  **Commit**: YES
  - Message: `docs(health): Add documentation and examples for self-healing`
  - Files: `docs/health/`, `src/*.py` (docstrings)
  - Pre-commit: `python -m py_compile src/health*.py`

---

## Final Verification Wave

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Verify all "Must Have" implemented, all "Must NOT Have" absent, all tasks complete.

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run py_compile on all modified files, check for type hints, proper error handling.

- [ ] F3. **Real Manual QA** — `unspecified-high`
  Execute QA scenarios from all tasks, verify evidence files exist.

- [ ] F4. **Scope Fidelity Check** — `deep`
  Verify no feature creep, all gaps from masterplan addressed.

---

## Commit Strategy

| Wave | Tasks | Commit Message |
|------|-------|----------------|
| 1 | 1-5 | `feat(health): Add health schema, composite scorer, circuit integration, endpoints, checks` |
| 2 | 6-11 | `feat(health): Add degradation tiers, fallback registry, auto-recovery state machine` |
| 3 | 12-17 | `feat(health): Add checkpoint persistence, resume, API, ML integration, E2E tests` |

---

## Success Criteria

### Verification Commands
```bash
# All modified files compile
python -m py_compile src/health_schema.py src/health_composite.py src/health_core.py
python -m py_compile src/health_endpoint.py src/degradation_tiers.py src/fallback_registry.py
python -m py_compile src/auto_recovery.py src/checkpoint_resume.py

# Run health-related tests
pytest tests/ -k "health" -v
```

### Final Checklist
- [ ] All "Must Have" present (schema, scorer, breaker, tiers, fallback, checkpoint)
- [ ] All "Must NOT Have" absent (hardcoded names, blocking ops, circular fallbacks)
- [ ] Circuit breaker integrated with health monitoring
- [ ] 4-tier degradation operational
- [ ] Fallback chains work for tools AND context
- [ ] Checkpoint/resume preserves state
- [ ] /live and /ready endpoints correct
- [ ] 100+ existing tests still pass

---

## Dependencies Between Modules

```
health_schema.py (Task 1)
    ↑
    ├──→ health_composite.py (Task 2) ──→ degradation_tiers.py (Task 6)
    │           ↓
    │           ├──→ health_core.py (Task 3, enhanced)
    │           ├──→ health_endpoint.py (Task 4, enhanced)
    │           ├──→ health_checks.py (Task 5, enhanced)
    │           └──→ plugin_health_ml.py integration (Task 15)
    │
    ├──→ fallback_registry.py (Tasks 7-8) ──→ auto_recovery.py (Task 9)
    │                                              ↓
    │           └──→ self_healer.py (Task 10, enhanced)
    │                      ↓
    │                      └──→ integration test (Task 11)
    │
    └──→ checkpoint_resume.py (Tasks 12-13) ──→ health_endpoint.py (Task 14, enhanced)
             ↓
             └──→ E2E test (Task 16)
                       ↓
                       └──→ Documentation (Task 17)
```

---

## Implementation Order

**Wave 1 (Parallel - Foundation):**
1. Task 1: Health Schema Definitions
2. Task 2: Composite Health Scorer
3. Task 3: Circuit Breaker Integration
4. Task 4: Enhanced Health Endpoint
5. Task 5: Health Check Definitions

**Wave 2 (Sequential - Recovery + Degradation):**
6. Task 6: Degradation Tier Definitions (depends on 1-5)
7. Task 7: Fallback Registry (Tools) (depends on 1-5)
8. Task 8: Fallback Registry (Context) (depends on 1-5)
9. Task 9: Auto-Recovery State Machine (depends on 6-8)
10. Task 10: Self-Healer Enhancement (depends on 6, 9)
11. Task 11: Integration Test (depends on 10)

**Wave 3 (Sequential - Persistence):**
12. Task 12: Checkpoint Persistence (depends on 1-5, 11)
13. Task 13: Resume Mechanism (depends on 12)
14. Task 14: Checkpoint API Endpoints (depends on 12-13)
15. Task 15: ML Predictor Integration (depends on 1-5)
16. Task 16: E2E Integration Test (depends on 11, 14-15)
17. Task 17: Documentation (depends on all)

---

## Category + Skills Mapping

| Task | Category | Skills | Agent Model |
|------|----------|--------|-------------|
| 1 | deep | python-typing, data-validation | qwen3.6-plus-free (medium) |
| 2 | deep | algorithm-design, performance | qwen3.6-plus-free (high) |
| 3 | deep | system-integration, fault-tolerance | qwen3.6-plus-free (high) |
| 4 | quick | fastapi-or-aiohttp, api-design | minimax-m2.5-free |
| 5 | quick | system-monitoring, metrics | minimax-m2.5-free |
| 6 | deep | state-machine, fault-tolerance | qwen3.6-plus-free (high) |
| 7 | deep | decorator-pattern, fault-tolerance | qwen3.6-plus-free (high) |
| 8 | deep | data-layer, cache-strategies | qwen3.6-plus-free (high) |
| 9 | deep | state-machine, workflow-automation | qwen3.6-plus-free (high) |
| 10 | deep | api-compatibility, system-extension | qwen3.6-plus-free (medium) |
| 11 | unspecified-high | integration-testing, test-automation | qwen3.6-plus-free (medium) |
| 12 | deep | persistence, atomic-operations | qwen3.6-plus-free (high) |
| 13 | deep | state-restoration, data-validation | qwen3.6-plus-free (high) |
| 14 | quick | rest-api, endpoint-design | minimax-m2.5-free |
| 15 | unspecified-high | ml-integration, predictive-analytics | qwen3.6-plus-free (high) |
| 16 | unspecified-high | e2e-testing, performance-testing | qwen3.6-plus-free (medium) |
| 17 | quick | technical-writing, documentation | minimax-m2.5-free |

---

*Plan Generated: Layer 4 Self-Healing v1.0*
*For implementation, run: /start-work Layer4-Self-Healing-Implementation*
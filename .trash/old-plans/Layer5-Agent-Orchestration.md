# Layer 5: Agent Orchestration — Implementation Plan

## TL;DR

> **Quick Summary**: Build agent orchestration layer with A2A-compliant Agent Card Registry, resilience middleware (retry + circuit breaker + fallback), LLM-based task router with cost/latency scoring, and parallel execution via fan-out worker pools. Based on Google A2A, CrewAI hierarchical, and LangGraph patterns.
> 
> **Deliverables**:
> - `src/orchestration/agent_card_registry.py` — A2A Agent Card discovery and registry
> - `src/orchestration/resilience_middleware.py` — Retry, circuit breaker, fallback chains
> - `src/orchestration/task_router.py` — LLM-based intelligent routing with cost/latency scoring
> - `src/orchestration/parallel_executor.py` — Fan-out worker pools for parallel execution
> - `src/orchestration/network_orchestrator.py` — Hierarchical orchestration (CrewAI pattern)
> - `src/orchestration/a2a_protocol.py` — Google A2A protocol implementation
> 
> **Estimated Effort**: Medium-Large (12-15 tasks across 3 waves)
> **Parallel Execution**: YES — 3 waves with 4-5 tasks each
> **Critical Path**: Registry → Resilience → Router → Executor → Orchestrator

---

## Context

### Original Request
Create a dense, robust implementation plan for Layer 5: Agent Orchestration of N-Xyme MIND v1.0, addressing critical gaps: Agent Card Registry, resilience middleware, task router, parallel execution, capability matching, load balancing.

### Interview Summary
**Key Discussions**:
- Project location: `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/`
- Existing "agents" (Sisyphus, Prometheus, Hephaestus) are conceptual, not code files
- Layer 4 (Self-Healing) has working implementation in `src/self_healer.py`
- No actual agent registry exists - this is the critical gap

**Research Findings**:
- Google A2A Protocol: Agent Cards with JSON schema, capability discovery via `.well-known/agent-cards`
- CrewAI: Hierarchical process with `Crew`, `Agent`, `Task` classes, sequential/hierarchical/parallel processes
- LangGraph: State machine with `StateGraph`, conditional edges, node routing
- AutoGen: Group chat patterns, speaker selection, swarm orchestration

### Metis Review
**Identified Gaps** (addressed):
- Need to define exact Agent Card JSON schema compatibility
- Circuit breaker must integrate with existing self_healer.py
- Task router requires LLM integration - need fallback for when no LLM available
- Load balancing should support multiple strategies (round-robin, least-loaded, cost-aware)

---

## Work Objectives

### Core Objective
Implement Layer 5: Agent Orchestration with A2A-compliant agent discovery, resilience patterns, intelligent task routing, and parallel execution capabilities.

### Concrete Deliverables
1. **Agent Card Registry** — A2A-compliant JSON schema with capability matching
2. **Resilience Middleware** — Retry + circuit breaker + fallback chain implementation
3. **Task Router** — LLM-based routing with cost/latency scoring algorithm
4. **Parallel Executor** — ThreadPoolExecutor-based fan-out worker pools
5. **Network Orchestrator** — Hierarchical orchestration (CrewAI pattern)
6. **A2A Protocol** — Message passing, session management, artifact handling

### Definition of Done
- [ ] `python -m pytest tests/orchestration/ -v` → 20+ tests passing
- [ ] Agent Card Registry loads and discovers agents
- [ ] Circuit breaker transitions CLOSED → OPEN → HALF_OPEN correctly
- [ ] Task router selects optimal agent based on capability + cost + latency
- [ ] Parallel executor runs 10+ tasks concurrently with proper result aggregation
- [ ] Hierarchical orchestrator executes multi-level agent teams

### Must Have
- A2A Agent Card JSON schema compliance
- Retry with exponential backoff (configurable)
- Circuit breaker with configurable threshold
- Fallback chain execution
- Capability matching algorithm
- Load balancing (round-robin, least-loaded, cost-aware)

### Must NOT Have (Guardrails)
- NO hardcoded agent endpoints
- NO blocking synchronous execution in async context
- NO memory leaks in worker pool lifecycle
- NO circular dependencies between orchestration modules

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **Automated tests**: YES (TDD)
- **Framework**: pytest + pytest-asyncio
- **If TDD**: Each task follows RED (failing test) → GREEN (minimal impl) → REFACTOR

### QA Policy
Every task includes agent-executed QA scenarios - direct verification via running tests, not just code review.

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — 5 tasks):
├── T1: Create orchestration module structure + __init__.py
├── T2: Implement Agent Card data models + registry
├── T3: Implement resilience middleware base (retry + backoff)
├── T4: Implement circuit breaker state machine
└── T5: Implement fallback chain executor

Wave 2 (Core Logic — 5 tasks):
├── T6: Implement capability matching algorithm
├── T7: Implement task router with LLM scoring
├── T8: Implement parallel executor worker pools
├── T9: Implement A2A protocol message types
└── T10: Implement load balancing strategies

Wave 3 (Integration + Orchestration — 4 tasks):
├── T11: Implement network orchestrator (hierarchical)
├── T12: Integrate with existing self_healer.py
├── T13: Add A2A compatibility layer
└── T14: Write integration tests

Wave FINAL (Verification — 4 tasks):
├── F1: Plan compliance audit
├── F2: Code quality review (lint, type check)
├── F3: Integration test execution
└── F4: Scope fidelity check
```

### Dependency Matrix

- **T1-T5**: No dependencies — can run in parallel
- **T6**: T2 (needs registry) — T6 blocks T7, T8
- **T7**: T6 (needs matching) — T7 blocks T11
- **T8**: T5 (needs fallback), T3 (needs retry) — T8 blocks T14
- **T9-T10**: Independent of T6-T8 — can run parallel
- **T11**: T7, T10 (needs router + load balancing)
- **T12**: T3 (needs circuit breaker)
- **T13**: T9 (needs A2A messages)
- **T14**: T8, T11, T12, T13 (integration point)

### Agent Dispatch Summary
- **Wave 1**: 5 tasks → TDD with pytest
- **Wave 2**: 5 tasks → Implementation with unit tests
- **Wave 3**: 4 tasks → Integration work
- **FINAL**: 4 tasks → Verification agents

---

## TODOs

---

- [ ] 1. Create orchestration module structure

  **What to do**:
  - Create `src/orchestration/` directory
  - Create `src/orchestration/__init__.py` with module exports
  - Create `src/orchestration/types.py` for shared type definitions
  - Create `src/orchestration/exceptions.py` for orchestration-specific exceptions
  - Set up `tests/orchestration/` directory structure

  **Must NOT do**:
  - Import any external dependencies not already in project

  **Recommended Agent Profile**:
  > Category: `unspecified-low` — Simple file creation, no complex logic
  > Skills: [`filesystem`] — Creating directories and files
  > Skills Evaluated but Omitted: N/A

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T2-T5)
  - **Blocks**: T2-T5
  - **Blocked By**: None

  **References**:
  - `src/self_healer.py:1-50` — Existing module structure pattern
  - `src/__init__.py:1-20` — Module export pattern

  **Acceptance Criteria**:
  - [ ] `src/orchestration/` directory exists with `__init__.py`
  - [ ] `tests/orchestration/` directory exists
  - [ ] `python -c "from src.orchestration import *"` → No import errors

  **QA Scenarios**:
  ```
  Scenario: Module structure created correctly
    Tool: Bash
    Preconditions: Clean workspace
    Steps:
      1. python -c "import src.orchestration; print(src.orchestration.__file__)"
    Expected Result: Path to orchestration/__init__.py
    Evidence: .sisyphus/evidence/task-1-structure.{ext}
  ```

  **Commit**: YES
  - Message: `feat(orchestration): create module structure`
  - Files: `src/orchestration/`, `tests/orchestration/`

---

- [ ] 2. Implement Agent Card data models and registry

  **What to do**:
  - Create `src/orchestration/agent_card.py` with dataclasses:
    - `AgentCard` — name, version, description, capabilities[], endpoints, auth
    - `AgentCapability` — type, input_schema, output_schema, cost_estimate, latency_estimate
    - `AgentEndpoint` — url, auth_method, capabilities[]
  - Create `src/orchestration/registry.py`:
    - `AgentRegistry` class with in-memory store
    - `register(agent_card: AgentCard)` method
    - `discover(capabilities: list[str])` → list[AgentCard] method
    - `get(agent_id: str)` → AgentCard method
    - `list_all()` → list[AgentCard] method
  - Implement A2A-compliant `.well-known/agent-cards` endpoint simulation

  **Must NOT do**:
  - No persistent storage (use in-memory for v1.0)
  - No network calls (local registry only)

  **Recommended Agent Profile**:
  > Category: `deep` — Data models with complex relationships
  > Skills: [`python`] — Dataclass design, type hints
  > Skills Evaluated but Omitted: N/A

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T3-T5)
  - **Blocks**: T6 (capability matching)
  - **Blocked By**: T1 (module structure)

  **References**:
  - A2A Protocol JSON spec: `https://a2a.plus/docs/json-specification`
  - `src/memory/registry.py:1-100` — Registry pattern in existing code

  **Acceptance Criteria**:
  - [ ] AgentCard dataclass with all A2A fields
  - [ ] Registry can register and discover agents
  - [ ] `python -m pytest tests/orchestration/test_registry.py -v` → PASS

  **QA Scenarios**:
  ```
  Scenario: Register and discover agents
    Tool: Bash (pytest)
    Preconditions: Module structure exists
    Steps:
      1. python -c "from src.orchestration import AgentCard, AgentRegistry; r = AgentRegistry(); c = AgentCard(name='test', version='1.0', description='Test', capabilities=[]); r.register(c); print(len(r.list_all()))"
    Expected Result: 1
    Evidence: .sisyphus/evidence/task-2-registry.{ext}

  Scenario: Capability matching returns correct agents
    Tool: Bash (pytest)
    Preconditions: Registry with multiple agents
    Steps:
      1. Run pytest test_discover_by_capability
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-2-matching.{ext}
  ```

  **Commit**: YES
  - Message: `feat(orchestration): implement Agent Card registry`
  - Files: `src/orchestration/agent_card.py`, `src/orchestration/registry.py`
  - Pre-commit: `python -m pytest tests/orchestration/test_registry.py -v`

---

- [ ] 3. Implement resilience middleware base (retry + backoff)

  **What to do**:
  - Create `src/orchestration/resilience.py`:
    - `RetryConfig` — max_attempts, initial_delay, max_delay, exponential_base, jitter
    - `retry_with_backoff(func, config)` async decorator
    - `RetryStrategy` enum: FIXED, LINEAR, EXPONENTIAL, EXPONENTIAL_WITH_JITTER
  - Implement async retry with configurable backoff
  - Add retry hooks (on_retry, on_success, on_failure)
  - Support for retryable exceptions filtering

  **Must NOT do**:
  - No blocking sync retry in async context
  - No infinite retry loops (always respect max_attempts)

  **Recommended Agent Profile**:
  > Category: `deep` — Async patterns, decorator logic
  > Skills: [`python`, `async`] — asyncio patterns
  > Skills Evaluated but Omitted: N/A

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1-T2, T4-T5)
  - **Blocks**: T5 (fallback), T8 (parallel executor)
  - **Blocked By**: T1

  **References**:
  - `src/retry_handler.py:1-50` — Existing retry patterns
  - `openclaw/openclaw` — Circuit breaker patterns

  **Acceptance Criteria**:
  - [ ] Retry decorator works with async functions
  - [ ] Exponential backoff produces correct delays
  - [ ] `python -m pytest tests/orchestration/test_resilience.py -v` → PASS

  **QA Scenarios**:
  ```
  Scenario: Retry with exponential backoff
    Tool: Bash (pytest)
    Preconditions: Mock function that fails 2 times then succeeds
    Steps:
      1. python -c "import asyncio; from src.orchestration.resilience import retry_with_backoff, RetryConfig; @retry_with_backoff(RetryConfig(max_attempts=3)) async def f(): ...; asyncio.run(f())"
    Expected Result: Function succeeds after retries
    Evidence: .sisyphus/evidence/task-3-retry.{ext}

  Scenario: Retry exhaustion raises exception
    Tool: Bash (pytest)
    Preconditions: Mock function that always fails
    Steps:
      1. Run pytest test_retry_exhaustion
    Expected Result: Exception raised after max_attempts
    Evidence: .sisyphus/evidence/task-3-exhaustion.{ext}
  ```

  **Commit**: YES
  - Message: `feat(orchestration): implement retry with backoff`
  - Files: `src/orchestration/resilience.py`
  - Pre-commit: `python -m pytest tests/orchestration/test_resilience.py -v`

---

- [ ] 4. Implement circuit breaker state machine

  **What to do**:
  - Create `src/orchestration/circuit_breaker.py`:
    - `CircuitState` enum: CLOSED, OPEN, HALF_OPEN
    - `CircuitBreakerConfig` — failure_threshold, success_threshold, timeout, half_open_max_calls
    - `CircuitBreaker` class with state machine:
      - `call(func)` — Execute with circuit breaker protection
      - `record_success()` — Move toward CLOSED
      - `record_failure()` — Move toward OPEN
    - Integrate with existing health monitoring concepts

  **Must NOT do**:
  - No blocking calls inside async context
  - No race conditions in state transitions

  **Recommended Agent Profile**:
  > Category: `deep` — State machine, concurrent access
  > Skills: [`python`, `async`, `concurrency`] — Thread-safe state management
  > Skills Evaluated but Omitted: N/A

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1-T3, T5)
  - **Blocks**: T12 (integration with self_healer)
  - **Blocked By**: T1

  **References**:
  - `src/self_healer.py:50-100` — Policy state machine patterns
  - `openclaw/openclaw` — Circuit breaker implementation

  **Acceptance Criteria**:
  - [ ] Circuit breaker transitions CLOSED → OPEN → HALF_OPEN → CLOSED correctly
  - [ ] Configurable thresholds work
  - [ ] `python -m pytest tests/orchestration/test_circuit_breaker.py -v` → PASS

  **QA Scenarios**:
  ```
  Scenario: Circuit opens after threshold failures
    Tool: Bash (pytest)
    Preconditions: CircuitBreaker with failure_threshold=3
    Steps:
      1. Call circuit_breaker.call(failing_func) 3 times
    Expected Result: State is OPEN after 3rd failure
    Evidence: .sisyphus/evidence/task-4-open.{ext}

  Scenario: Circuit half-open after timeout
    Tool: Bash (pytest)
    Preconditions: Circuit in OPEN state, timeout=0.1s
    Steps:
      1. Wait 0.2s, call circuit_breaker.call(success_func)
    Expected Result: State is HALF_OPEN
    Evidence: .sisyphus/evidence/task-4-halfopen.{ext}
  ```

  **Commit**: YES
  - Message: `feat(orchestration): implement circuit breaker`
  - Files: `src/orchestration/circuit_breaker.py`
  - Pre-commit: `python -m pytest tests/orchestration/test_circuit_breaker.py -v`

---

- [ ] 5. Implement fallback chain executor

  **What to do**:
  - Create `src/orchestration/fallback.py`:
    - `FallbackChain` class — Ordered list of fallback handlers
    - `FallbackStrategy` — FIRST_SUCCESS, ALL_FAILED, WEIGHTED
    - `execute_with_fallback(primary_func, fallbacks, strategy)` method
  - Support async and sync functions
  - Track which fallback succeeded/failed
  - Return (result, fallback_used: bool, fallback_index: int)

  **Must NOT do**:
  - No recursive fallback chains (prevent infinite loops)
  - No executing all fallbacks when FIRST_SUCCESS would work

  **Recommended Agent Profile**:
  > Category: `deep` — Execution chain logic
  > Skills: [`python`, `async`] — Function chaining
  > Skills Evaluated but Omitted: N/A

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1-T4)
  - **Blocks**: T8 (parallel executor needs fallback)
  - **Blocked By**: T1

  **References**:
  - `code-yeongyu/oh-my-openagent` — Fallback chain system

  **Acceptance Criteria**:
  - [ ] Fallback chain executes in order
  - [ ] Returns correct fallback index on success/failure
  - [ ] `python -m pytest tests/orchestration/test_fallback.py -v` → PASS

  **QA Scenarios**:
  ```
  Scenario: Primary succeeds, no fallback used
    Tool: Bash (pytest)
    Preconditions: FallbackChain with 2 fallbacks
    Steps:
      1. execute_with_fallback(primary_succeeds, [fallback1, fallback2], FIRST_SUCCESS)
    Expected Result: (result, False, -1)
    Evidence: .sisyphus/evidence/task-5-primary.{ext}

  Scenario: Primary fails, fallback succeeds
    Tool: Bash (pytest)
    Preconditions: FallbackChain with working fallback
    Steps:
      1. execute_with_fallback(primary_fails, [fallback_works], FIRST_SUCCESS)
    Expected Result: (fallback_result, True, 0)
    Evidence: .sisyphus/evidence/task-5-fallback.{ext}
  ```

  **Commit**: YES
  - Message: `feat(orchestration): implement fallback chain executor`
  - Files: `src/orchestration/fallback.py`
  - Pre-commit: `python -m pytest tests/orchestration/test_fallback.py -v`

---

- [ ] 6. Implement capability matching algorithm

  **What to do**:
  - Create `src/orchestration/capability_matcher.py`:
    - `CapabilityMatch` — score, agent_card, matched_capabilities, missing_capabilities
    - `match_capabilities(required: list[str], available: list[AgentCapability])` → list[CapabilityMatch]
    - Implement scoring algorithm:
      - Exact match: 1.0
      - Partial match (subset): 0.8
      - Semantic match (using simple keyword matching): 0.5
      - No match: 0.0
    - Sort by score descending

  **Must NOT do**:
  - No LLM-based matching (too expensive for v1.0)
  - No complex NLP - simple keyword matching only

  **Recommended Agent Profile**:
  > Category: `deep` — Algorithm implementation
  > Skills: [`python`] — Algorithm design
  > Skills Evaluated but Omitted: N/A

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T2)
  - **Parallel Group**: N/A (sequential after T2)
  - **Blocks**: T7 (task router)
  - **Blocked By**: T2 (registry)

  **References**:
  - `src/memory/retrieval.py` — Simple matching patterns

  **Acceptance Criteria**:
  - [ ] Exact match scores 1.0
  - [ ] Partial match scores 0.8
  - [ ] No match returns empty list
  - [ ] `python -m pytest tests/orchestration/test_matcher.py -v` → PASS

  **QA Scenarios**:
  ```
  Scenario: Exact capability match
    Tool: Bash (pytest)
    Preconditions: Agent with capability "code-gen"
    Steps:
      1. match_capabilities(["code-gen"], agent.capabilities)
    Expected Result: Score 1.0
    Evidence: .sisyphus/evidence/task-6-exact.{ext}

  Scenario: Partial capability match
    Tool: Bash (pytest)
    Preconditions: Agent with capabilities ["code-gen", "debug"]
    Steps:
      1. match_capabilities(["code-gen"], agent.capabilities)
    Expected Result: Score 0.8 (subset)
    Evidence: .sisyphus/evidence/task-6-partial.{ext}
  ```

  **Commit**: YES
  - Message: `feat(orchestration): implement capability matching`
  - Files: `src/orchestration/capability_matcher.py`
  - Pre-commit: `python -m pytest tests/orchestration/test_matcher.py -v`

---

- [ ] 7. Implement task router with LLM scoring

  **What to do**:
  - Create `src/orchestration/router.py`:
    - `RouterConfig` — llm_endpoint, api_key, cost_weight, latency_weight, capability_weight
    - `TaskRouter` class:
      - `route(task: str, available_agents: list[AgentCard])` → AgentCard
    - Implement scoring algorithm:
      ```
      score = (capability_match_score * capability_weight) +
              ((1 - normalized_cost) * cost_weight) +
              ((1 - normalized_latency) * latency_weight)
      ```
    - Fallback to capability matching when LLM unavailable
    - Support cost/latency estimates from AgentCard

  **Must NOT do**:
  - No hardcoded LLM endpoint
  - No mandatory LLM - must have fallback

  **Recommended Agent Profile**:
  > Category: `deep` — Algorithm with external dependency
  > Skills: [`python`, `api-integration`] — LLM integration
  > Skills Evaluated but Omitted: N/A

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T6)
  - **Parallel Group**: N/A (sequential after T6)
  - **Blocks**: T11 (network orchestrator)
  - **Blocked By**: T6 (capability matcher)

  **References**:
  - `src/tui/api_client.py` — API client patterns

  **Acceptance Criteria**:
  - [ ] Router returns optimal agent based on combined score
  - [ ] Fallback to capability-only matching when LLM fails
  - [ ] `python -m pytest tests/orchestration/test_router.py -v` → PASS

  **QA Scenarios**:
  ```
  Scenario: Route to lowest cost when capability equal
    Tool: Bash (pytest)
    Preconditions: Two agents with same capability, different costs
    Steps:
      1. router.route("generate code", [agent1_cheap, agent2_expensive])
    Expected Result: agent1_cheap selected
    Evidence: .sisyphus/evidence/task-7-cost.{ext}

  Scenario: Fallback when LLM unavailable
    Tool: Bash (pytest)
    Preconditions: LLM endpoint not configured
    Steps:
      1. router.route("generate code", agents)
    Expected Result: Falls back to capability matching
    Evidence: .sisyphus/evidence/task-7-fallback.{ext}
  ```

  **Commit**: YES
  - Message: `feat(orchestration): implement task router`
  - Files: `src/orchestration/router.py`
  - Pre-commit: `python -m pytest tests/orchestration/test_router.py -v`

---

- [ ] 8. Implement parallel executor worker pools

  **What to do**:
  - Create `src/orchestration/executor.py`:
    - `WorkerPool` class — manages thread pool for parallel execution
    - `TaskResult` — task_id, result, error, execution_time, worker_id
    - `ParallelExecutor` class:
      - `execute_many(tasks: list[Callable], max_workers: int)` → list[TaskResult]
      - `execute_with_fanout(task, sub_tasks)` — Fan-out pattern
    - Support for:
      - Task cancellation
      - Progress tracking
      - Worker lifecycle management

  **Must NOT do**:
  - No memory leaks from thread pool
  - No blocking await on thread pool in async context

  **Recommended Agent Profile**:
  > Category: `deep` — Concurrency patterns
  > Skills: [`python`, `concurrency`, `threading`] — ThreadPoolExecutor
  > Skills Evaluated but Omitted: N/A

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T3, T5)
  - **Parallel Group**: N/A (sequential after T3, T5)
  - **Blocks**: T14 (integration tests)
  - **Blocked By**: T3 (retry), T5 (fallback)

  **References**:
  - Python concurrent.futures documentation
  - `athena/scripts/parallel_orchestrator.py` — Existing parallel patterns

  **Acceptance Criteria**:
  - [ ] Execute 10+ tasks concurrently
  - [ ] Return aggregated results in order
  - [ ] `python -m pytest tests/orchestration/test_executor.py -v` → PASS

  **QA Scenarios**:
  ```
  Scenario: Execute 10 tasks in parallel
    Tool: Bash (pytest)
    Preconditions: 10 simple tasks
    Steps:
      1. executor.execute_many(tasks, max_workers=5)
    Expected Result: All 10 results returned
    Evidence: .sisyphus/evidence/task-8-parallel.{ext}

  Scenario: Fan-out pattern execution
    Tool: Bash (pytest)
    Preconditions: 1 main task, 5 sub-tasks
    1. executor.execute_with_fanout(main, sub_tasks)
    Expected Result: All sub-task results aggregated
    Evidence: .sisyphus/evidence/task-8-fanout.{ext}
  ```

  **Commit**: YES
  - Message: `feat(orchestration): implement parallel executor'
  - Files: `src/orchestration/executor.py`
  - Pre-commit: `python -m pytest tests/orchestration/test_executor.py -v`

---

- [ ] 9. Implement A2A protocol message types

  **What to do**:
  - Create `src/orchestration/a2a_types.py`:
    - `A2AMessage` — Base message type
    - `TaskMessage` — task_id, payload, priority, timeout
    - `ResultMessage` — task_id, artifact, status, metadata
    - `ErrorMessage` — task_id, error_code, error_message, recoverable
    - `AgentMessage` — agent_id, message_type, content
  - Create `src/orchestration/a2a_protocol.py`:
    - `A2AClient` — Send messages to remote agents
    - `A2AServer` — Receive and process messages (stub for v1.0)
    - `MessageSerializer` — JSON encoding/decoding
    - Session management (basic)

  **Must NOT do**:
  - No actual network calls in v1.0 (local simulation only)
  - No production-grade security (stub only)

  **Recommended Agent Profile**:
  > Category: `deep` — Protocol design
  > Skills: [`python`, `serialization`] — JSON schema
  > Skills Evaluated but Omitted: N/A

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with T10)
  - **Blocks**: T13 (A2A compatibility)
  - **Blocked By**: T1

  **References**:
  - A2A Protocol: `https://a2a.plus/docs/json-specification`

  **Acceptance Criteria**:
  - [ ] Message serialization/deserialization works
  - [ ] All message types can be created and encoded
  - [ ] `python -m pytest tests/orchestration/test_a2a_types.py -v` → PASS

  **QA Scenarios**:
  ```
  Scenario: Serialize and deserialize message
    Tool: Bash (pytest)
    Preconditions: TaskMessage created
    Steps:
      1. json_str = serializer.encode(msg); decoded = serializer.decode(json_str)
    Expected Result: decoded == original
    Evidence: .sisyphus/evidence/task-9-serialization.{ext}
  ```

  **Commit**: YES
  - Message: `feat(orchestration): implement A2A protocol types'
  - Files: `src/orchestration/a2a_types.py`, `src/orchestration/a2a_protocol.py`
  - Pre-commit: `python -m pytest tests/orchestration/test_a2a_types.py -v`

---

- [ ] 10. Implement load balancing strategies

  **What to do**:
  - Create `src/orchestration/load_balancer.py`:
    - `LoadBalancer` abstract base class
    - `RoundRobinBalancer` — Sequential rotation
    - `LeastLoadedBalancer` — Select agent with fewest active tasks
    - `CostAwareBalancer` — Prefer lower cost agents
    - `LatencyAwareBalancer` — Prefer lower latency agents
    - `CompositeBalancer` — Combine multiple strategies with weights
  - Agent workload tracking (in-memory)

  **Must NOT do**:
  - No persistent workload tracking (in-memory only)
  - No complex distributed state

  **Recommended Agent Profile**:
  > Category: `deep` — Algorithm implementation
  > Skills: [`python`] — Selection algorithms
  > Skills Evaluated but Omitted: N/A

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with T9)
  - **Blocks**: T11
  - **Blocked By**: T1

  **References**:
  - Standard load balancing patterns

  **Acceptance Criteria**:
  - [ ] All 5 balancer strategies work correctly
  - [ ] Composite balancer combines strategies
  - [ ] `python -m pytest tests/orchestration/test_load_balancer.py -v` → PASS

  **QA Scenarios**:
  ```
  Scenario: Round robin distributes evenly
    Tool: Bash (pytest)
    Preconditions: 3 agents, 9 tasks
    Steps:
      1. balancer.select(agents) 9 times
    Expected Result: Each agent selected 3 times
    Evidence: .sisyphus/evidence/task-10-rr.{ext}

  Scenario: Least loaded selects available agent
    Tool: Bash (pytest)
    Preconditions: Agent A has 2 tasks, Agent B has 0
    Steps:
      1. balancer.select([A, B])
    Expected Result: Agent B selected
    Evidence: .sisyphus/evidence/task-10-ll.{ext}
  ```

  **Commit**: YES
  - Message: `feat(orchestration): implement load balancing'
  - Files: `src/orchestration/load_balancer.py`
  - Pre-commit: `python -m pytest tests/orchestration/test_load_balancer.py -v`

---

- [ ] 11. Implement network orchestrator (hierarchical)

  **What to do**:
  - Create `src/orchestration/orchestrator.py`:
    - `OrchestratorConfig` — max_depth, timeout, escalation_policy
    - `OrchestrationNode` — Agent with children (hierarchical structure)
    - `NetworkOrchestrator` class:
      - `create_team(manager: AgentCard, workers: list[AgentCard])` → OrchestrationNode
      - `execute_task(task, node)` — Recursive execution
      - `execute_hierarchical(task, team)` — CrewAI-style hierarchical
      - `execute_sequential(tasks, team)` — Sequential process
      - `execute_parallel(tasks, team)` — Parallel process
    - Support for task decomposition and result aggregation

  **Must NOT do**:
  - No infinite recursion in hierarchical execution
  - No unhandled task timeout

  **Recommended Agent Profile**:
  > Category: `deep` — Complex orchestration logic
  > Skills: [`python`, `recursion`] — Tree traversal
  > Skills Evaluated but Omitted: N/A

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T7, T10)
  - **Parallel Group**: N/A (sequential after T7, T10)
  - **Blocks**: T14
  - **Blocked By**: T7 (router), T10 (load balancer)

  **References**:
  - `crewAIInc/crewai` — Hierarchical process patterns

  **Acceptance Criteria**:
  - [ ] Hierarchical execution works with manager + workers
  - [ ] Sequential and parallel execution modes work
  - [ ] `python -m pytest tests/orchestration/test_orchestrator.py -v` → PASS

  **QA Scenarios**:
  ```
  Scenario: Hierarchical execution with manager delegation
    Tool: Bash (pytest)
    Preconditions: Team with manager + 2 workers
    Steps:
      1. orchestrator.execute_hierarchical(task, team)
    Expected Result: Manager delegates to workers, results aggregated
    Evidence: .sisyphus/evidence/task-11-hierarchical.{ext}

  Scenario: Parallel execution distributes tasks
    Tool: Bash (pytest)
    Preconditions: 3 tasks, 3 workers
    Steps:
      1. orchestrator.execute_parallel(tasks, workers)
    Expected Result: All tasks executed, results returned
    Evidence: .sisyphus/evidence/task-11-parallel.{ext}
  ```

  **Commit**: YES
  - Message: `feat(orchestration): implement network orchestrator'
  - Files: `src/orchestration/orchestrator.py`
  - Pre-commit: `python -m pytest tests/orchestration/test_orchestrator.py -v`

---

- [ ] 12. Integrate with existing self_healer.py

  **What to do**:
  - Create `src/orchestration/healing_integration.py`:
    - `OrchestrationHealer` — Integrates circuit breaker with self_healer
    - Map orchestration failures to healing actions:
      - Agent timeout → RESTART agent
      - Circuit open → FALLBACK to backup
      - All agents failed → NOTIFY + degrade
    - Add health check endpoint for orchestration components

  **Must NOT do**:
  - No circular import with self_healer
  - No breaking existing self_healer functionality

  **Recommended Agent Profile**:
  > Category: `deep` — Integration work
  > Skills: [`python`, `integration`] — Connecting components
  > Skills Evaluated but Omitted: N/A

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T4)
  - **Parallel Group**: N/A (sequential after T4)
  - **Blocks**: T14
  - **Blocked By**: T4 (circuit breaker)

  **References**:
  - `src/self_healer.py:50-150` — Healing policy patterns

  **Acceptance Criteria**:
  - [ ] Circuit breaker triggers healing actions
  - [ ] Integration works with existing self_healer
  - [ ] `python -m pytest tests/orchestration/test_healing_integration.py -v` → PASS

  **QA Scenarios**:
  ```
  Scenario: Circuit open triggers fallback healing
    Tool: Bash (pytest)
    Preconditions: Circuit breaker in OPEN state
    Steps:
      1. orchestration_healer.handle_circuit_open(agent_id)
    Expected Result: Fallback agent selected, healing action logged
    Evidence: .sisyphus/evidence/task-12-fallback.{ext}
  ```

  **Commit**: YES
  - Message: `feat(orchestration): integrate with self_healer'
  - Files: `src/orchestration/healing_integration.py`
  - Pre-commit: `python -m pytest tests/orchestration/test_healing_integration.py -v`

---

- [ ] 13. Add A2A compatibility layer

  **What to do**:
  - Create `src/orchestration/a2a_compat.py`:
    - `A2ACompatibilityLayer` — Adapts internal orchestrator to A2A
    - `agent_card_to_a2a(agent_card)` → A2A JSON
    - `a2a_to_agent_card(a2a_json)` → AgentCard
    - Implement `.well-known/agent-cards` endpoint (stub)
    - Add A2A-compliant error responses

  **Must NOT do**:
  - No breaking internal API compatibility
  - No complex protocol conversion

  **Recommended Agent Profile**:
  > Category: `deep` — Protocol adaptation
  > Skills: [`python`, `serialization`] — Format conversion
  > Skills Evaluated but Omitted: N/A

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T9)
  - **Parallel Group**: N/A (sequential after T9)
  - **Blocks**: T14
  - **Blocked By**: T9 (A2A types)

  **References**:
  - A2A Protocol: `https://a2a-protocol.org/dev/topics/agent-discovery`

  **Acceptance Criteria**:
  - [ ] Internal AgentCard converts to A2A JSON correctly
  - [ ] A2A JSON converts to internal AgentCard
  - [ ] `python -m pytest tests/orchestration/test_a2a_compat.py -v` → PASS

  **QA Scenarios**:
  ```
  Scenario: Convert internal to A2A format
    Tool: Bash (pytest)
    Preconditions: Internal AgentCard
    Steps:
      1. a2a_json = agent_card_to_a2a(agent_card)
    Expected Result: Valid A2A JSON with all fields
    Evidence: .sisyphus/evidence/task-13-a2a.{ext}
  ```

  **Commit**: YES
  - Message: `feat(orchestration): add A2A compatibility layer'
  - Files: `src/orchestration/a2a_compat.py`
  - Pre-commit: `python -m pytest tests/orchestration/test_a2a_compat.py -v`

---

- [ ] 14. Write integration tests

  **What to do**:
  - Create `tests/orchestration/test_integration.py`:
    - Test full orchestration flow: register → route → execute → result
    - Test hierarchical execution with multiple agents
    - Test resilience with circuit breaker + fallback + retry
    - Test load balancing under load
  - Create `tests/orchestration/conftest.py` with fixtures:
    - `sample_agents` — 3 test agents with different capabilities
    - `orchestrator_fixture` — Configured orchestrator

  **Must NOT do**:
  - No external API calls in tests
  - No tests that require network access

  **Recommended Agent Profile**:
  > Category: `unspecified-low` — Test writing
  > Skills: [`pytest`] — Test patterns
  > Skills Evaluated but Omitted: N/A

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T8, T11, T12, T13)
  - **Parallel Group**: N/A (sequential after all implementation)
  - **Blocks**: None
  - **Blocked By**: T8, T11, T12, T13

  **References**:
  - `tests/integration/test_core.py` — Existing integration test patterns

  **Acceptance Criteria**:
  - [ ] Full orchestration flow works
  - [ ] 20+ integration tests passing
  - [ ] All modules importable together without conflicts

  **QA Scenarios**:
  ```
  Scenario: Full orchestration flow
    Tool: Bash (pytest)
    Preconditions: All components registered
    Steps:
      1. pytest tests/orchestration/test_integration.py -v
    Expected Result: 20+ tests pass
    Evidence: .sisyphus/evidence/task-14-integration.{ext}
  ```

  **Commit**: YES
  - Message: `test(orchestration): add integration tests'
  - Files: `tests/orchestration/test_integration.py`, `tests/orchestration/conftest.py`
  - Pre-commit: `python -m pytest tests/orchestration/ -v`

---

## Final Verification Wave

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists. For each "Must NOT Have": search for forbidden patterns.
  Output: `Must Have [6/6] | Must NOT Have [5/5] | Tasks [14/14] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `python -m py_compile src/orchestration/*.py` + linter. Review all files for:
  - Type hints present
  - Docstrings on public methods
  - No `as any`, no bare except
  - Consistent naming
  Output: `Compile [PASS/FAIL] | Lint [PASS/FAIL] | Files [N clean] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high`
  Execute all test files and verify results. Run integration test and verify full flow works.
  Output: `Tests [N/N pass] | Integration [PASS/FAIL] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual code. Verify 1:1 mapping.
  Output: `Tasks [14/14 compliant] | No creep | VERDICT`

---

## Commit Strategy

- **1**: `feat(orchestration): create module structure` — T1
- **2**: `feat(orchestration): implement Agent Card registry` — T2
- **3**: `feat(orchestration): implement retry with backoff` — T3
- **4**: `feat(orchestration): implement circuit breaker` — T4
- **5**: `feat(orchestration): implement fallback chain` — T5
- **6**: `feat(orchestration): implement capability matching` — T6
- **7**: `feat(orchestration): implement task router` — T7
- **8**: `feat(orchestration): implement parallel executor` — T8
- **9**: `feat(orchestration): implement A2A protocol` — T9
- **10**: `feat(orchestration): implement load balancing` — T10
- **11**: `feat(orchestration): implement network orchestrator` — T11
- **12**: `feat(orchestration): integrate with self_healer` — T12
- **13**: `feat(orchestration): add A2A compatibility` — T13
- **14**: `test(orchestration): add integration tests` — T14
- **FINAL**: `chore(orchestration): complete Layer 5` — F1-F4

---

## Success Criteria

### Verification Commands
```bash
python -m pytest tests/orchestration/ -v  # Expected: 20+ tests pass
python -m py_compile src/orchestration/*.py  # Expected: No errors
```

### Final Checklist
- [ ] All 6 "Must Have" features present
- [ ] All 5 "Must NOT Have" patterns absent
- [ ] All 14 tasks completed with tests passing
- [ ] A2A Agent Card schema compliant
- [ ] Integration with self_healer.py working
- [ ] Version: Layer 5 complete
# N-Xyme MIND v1.0 — Layer 5: Agent Orchestration Implementation Plan

## Context

**Files to implement**:
1. sisyphus.py — ENHANCE existing plan executor
2. prometheus.py — ENHANCE existing plan builder
3. hephaestus.py — ENHANCE existing implementation agent
4. a2a_protocol.py — NEW: Agent-to-Agent (Google A2A, 150+ orgs)
5. network_orchestrator.py — NEW: CrewAI hierarchical + Swarms patterns

**Critical Gaps**:
- Agent Card Registry (A2A standard for capability discovery)
- Resilience middleware (retry + circuit breaker + fallback)
- Task router (LLM-based with cost/latency scoring)
- Parallel execution (fan-out worker pools)
- Capability matching algorithms
- Load balancing for agent work queues

**Repos to Study**:
- Google A2A Protocol — Agent Cards, task delegation
- crewAIInc/crewai — Hierarchical orchestration
- langchain-ai/langgraph — Conditional routing, state machines
- microsoft/autogen — Swarm patterns, group chat

---

## 1. File-by-File Breakdown

### 1.1 a2a_protocol.py (NEW)

**Classes**:
```python
class AgentCard:
    """A2A Agent Card for capability discovery."""
    agent_id: str
    name: str
    description: str
    capabilities: List[str]
    endpoints: Dict[str, str]
    version: str
    metadata: Dict

class A2ATask:
    """A2A task for delegation."""
    task_id: str
    source_agent: str
    target_agent: str
    task_type: str
    payload: Dict
    status: str  # pending, running, completed, failed
    result: Optional[Dict]

class A2AProtocol:
    """Agent-to-Agent communication protocol."""
    def register_agent(self, card: AgentCard) -> None
    def discover_agents(self, capability: str) -> List[AgentCard]
    def delegate_task(self, task: A2ATask) -> str
    def get_task_status(self, task_id: str) -> Dict
    def cancel_task(self, task_id: str) -> bool
```

### 1.2 network_orchestrator.py (NEW)

**Classes**:
```python
class AgentWorker:
    """Worker agent in the orchestration network."""
    agent_id: str
    capabilities: List[str]
    status: str  # idle, busy, offline
    load: float  # 0.0-1.0

class TaskRouter:
    """LLM-based task routing with cost/latency scoring."""
    def route_task(self, task: Dict, workers: List[AgentWorker]) -> str
    def score_worker(self, worker: AgentWorker, task: Dict) -> float

class LoadBalancer:
    """Load balancer for agent work queues."""
    def assign_task(self, task: Dict) -> str
    def get_worker_load(self, worker_id: str) -> float
    def rebalance(self) -> None

class NetworkOrchestrator:
    """Hierarchical orchestration (CrewAI patterns)."""
    def __init__(self, workers: List[AgentWorker])
    def create_crew(self, task: Dict) -> str
    def execute_parallel(self, tasks: List[Dict]) -> List[Dict]
    def execute_sequential(self, tasks: List[Dict]) -> Dict
    def execute_hierarchical(self, task: Dict) -> Dict
```

### 1.3 sisyphus.py (ENHANCE)

**Add**:
```python
class ResilienceMiddleware:
    """Retry + circuit breaker + fallback."""
    def execute_with_retry(self, func, max_retries=3, backoff=1.0)
    def execute_with_circuit_breaker(self, func, breaker_name: str)
    def execute_with_fallback(self, func, fallbacks: List[Callable])
```

### 1.4 prometheus.py (ENHANCE)

**Add**:
```python
class PlanValidator:
    """Validate plan feasibility before execution."""
    def validate(self, plan: Dict) -> Dict  # {valid: bool, issues: List[str]}

class PlanOptimizer:
    """Optimize plan for parallel execution."""
    def optimize(self, plan: Dict) -> Dict  # Reorder for max parallelism
```

### 1.5 hephaestus.py (ENHANCE)

**Add**:
```python
class ImplementationTracker:
    """Track implementation progress."""
    def record_progress(self, task_id: str, progress: float)
    def get_progress(self, task_id: str) -> float
    def estimate_completion(self, task_id: str) -> float
```

---

## 2. Dependencies

```
a2a_protocol.py ──┬──► network_orchestrator.py
                  │        │
                  │        ▼
sisyphus.py ──────┤   ResilienceMiddleware
                  │
prometheus.py ────┤   PlanValidator, PlanOptimizer
                  │
hephaestus.py ────┘   ImplementationTracker
```

---

## 3. Implementation Order

| Wave | Task | Depends On |
|------|------|------------|
| 1 | a2a_protocol.py | None |
| 1 | network_orchestrator.py | None |
| 2 | sisyphus.py (enhance) | a2a_protocol.py |
| 2 | prometheus.py (enhance) | network_orchestrator.py |
| 3 | hephaestus.py (enhance) | sisyphus.py, prometheus.py |

---

## 4. Test Strategy

- **a2a_protocol.py**: Agent registration, task delegation, status tracking
- **network_orchestrator.py**: Task routing, load balancing, parallel/sequential execution
- **sisyphus.py**: Retry logic, circuit breaker, fallback chains
- **prometheus.py**: Plan validation, optimization
- **hephaestus.py**: Progress tracking, completion estimation

---

## 5. Success Criteria

| File | Criteria |
|------|----------|
| a2a_protocol.py | Agent discovery works, task delegation succeeds |
| network_orchestrator.py | Task routing scores correctly, load balancing distributes evenly |
| sisyphus.py | Retry/circuit breaker/fallback all work |
| prometheus.py | Plan validation catches invalid plans |
| hephaestus.py | Progress tracking accurate within 10% |

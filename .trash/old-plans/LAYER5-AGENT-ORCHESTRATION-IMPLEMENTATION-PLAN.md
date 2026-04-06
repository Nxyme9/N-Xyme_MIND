# Layer 5: Agent Orchestration — Implementation Plan

## 📋 Overview

**Layer**: 5 (Agent Orchestration)  
**Status**: PLANNED (NOT YET IMPLEMENTED)  
**Priority**: HIGH — Critical for multi-agent coordination  
**Implementation Wave**: 3 (Weeks 5-6)

---

## 🎯 Executive Summary

This layer implements the core agent orchestration system for N-Xyme MIND v1.0, following the Google A2A Protocol standard (150+ organizations) while incorporating patterns from CrewAI hierarchical orchestration, LangGraph state machines, and Microsoft AutoGen swarm patterns.

**Core Components**:
1. `a2a_protocol.py` — Agent-to-Agent communication (NEW)
2. `network_orchestrator.py` — Hierarchical + swarm orchestration (NEW)
3. `sisyphus.py` — ENHANCE existing plan executor
4. `prometheus.py` — ENHANCE existing plan builder
5. `hephaestus.py` — ENHANCE existing implementation agent

---

## 📁 File Structure

```
src/
├── orchestration/
│   ├── __init__.py
│   ├── a2a_protocol.py        # NEW: A2A Agent Cards + task delegation
│   ├── agent_card.py          # NEW: Agent Card registry + discovery
│   ├── capability_matcher.py  # NEW: Capability matching algorithms
│   ├── network_orchestrator.py # NEW: Hierarchical + swarm patterns
│   ├── task_router.py         # NEW: LLM-based routing with cost/latency
│   ├── resilience_middleware.py # NEW: Retry + circuit breaker
│   ├── worker_pool.py         # NEW: Fan-out parallel execution
│   ├── load_balancer.py       # NEW: Agent work queue distribution
│   └── protocol.py            # NEW: A2A message types + serialization
├── sisyphus.py                # ENHANCE: Plan executor with orchestration
├── prometheus.py              # ENHANCE: Plan builder with task decomposition
└── hephaestus.py              # ENHANCE: Implementation agent with delegation
```

---

## 🔬 Component Analysis

### 1. a2a_protocol.py (NEW)

**Purpose**: Implement Google A2A Protocol for agent-to-agent communication

**Key Classes**:

```python
# ── A2A Message Types ───────────────────────────────────────────────────────
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class MessageRole(str, Enum):
    """A2A message roles."""
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"

class TaskState(str, Enum):
    """A2A task states."""
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input_required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

class MessagePart(BaseModel):
    """Single message part (text, file, or artifact reference)."""
    type: str = Field(..., description="Part type: text, file, or artifact")
    text: Optional[str] = None
    file: Optional[Dict[str, Any]] = None
    artifact_id: Optional[str] = None

class Message(BaseModel):
    """A2A message between agents."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole
    parts: List[MessagePart]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    thread_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Task(BaseModel):
    """A2A task representation."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    status: TaskState
    message: Optional[Message] = None
    history: List[Message] = Field(default_factory=list)
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AgentCard(BaseModel):
    """A2A Agent Card — capability discovery manifest."""
    agent_id: str
    name: str
    description: str
    version: str = "1.0.0"
    provider: str  # "opencode", "anthropic", "ollama", etc.
    model: str
    
    # Capability discovery
    capabilities: List[str] = Field(default_factory=list)  # ["text-generation", "code-analysis", "vision"]
    skills: List[Dict[str, Any]] = Field(default_factory=list)  # [{"name": "python", "version": "3.11"}]
    tags: List[str] = Field(default_factory=list)  # ["implementation", "research", "review"]
    
    # Performance characteristics
    avg_latency_ms: Optional[int] = None
    max_tokens: Optional[int] = None
    supports_streaming: bool = False
    supports_tools: bool = True
    
    # Authentication
    auth_type: str = "none"  # "none", "api_key", "jwt"
    endpoint: Optional[str] = None
    
    # Status
    status: str = "available"  # "available", "busy", "offline"
    last_heartbeat: Optional[str] = None
    
    # Metadata
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

**Key Functions**:

```python
class A2AProtocol:
    """A2A Protocol implementation for agent communication."""
    
    def __init__(self, agent_card: AgentCard):
        self.agent_card = agent_card
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._active_tasks: Dict[str, Task] = {}
    
    async def send_task(self, target_agent: AgentCard, task: Task) -> Task:
        """Send task to target agent via A2A protocol."""
        pass
    
    async def receive_task(self) -> Task:
        """Receive incoming task from queue."""
        pass
    
    async def send_message(self, target_agent: AgentCard, message: Message) -> Message:
        """Send message to target agent."""
        pass
    
    async def subscribe(self, session_id: str, callback: Callable):
        """Subscribe to task updates via SSE."""
        pass
    
    def to_jsonrpc(self, method: str, params: Dict[str, Any]) -> str:
        """Convert to JSON-RPC 2.0 format."""
        pass
    
    def from_jsonrpc(self, jsonrpc: str) -> Dict[str, Any]:
        """Parse JSON-RPC 2.0 message."""
        pass
```

**Test Strategy**:
- `test_agent_card_serialization` — Verify JSON schema compliance
- `test_message_serialization` — Round-trip Message ↔ JSON
- `test_task_state_transitions` — Verify valid state machine
- `test_jsonrpc_conformance` — Validate JSON-RPC 2.0 format
- `test_agent_card_discovery` — Registry lookup returns correct card

**Success Criteria**:
- ✅ Agent Card validates against A2A JSON schema
- ✅ Message serialization round-trips correctly
- ✅ Task state machine follows valid transitions
- ✅ JSON-RPC 2.0 compliance verified

---

### 2. agent_card.py (NEW)

**Purpose**: Agent Card Registry for capability discovery

**Key Classes**:

```python
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import hashlib

@dataclass
class AgentMetadata:
    """Extended metadata for agent registry."""
    primary_role: str  # "orchestrator", "planner", "implementer", "reviewer"
    fallback_chain: List[str] = field(default_factory=list)
    max_concurrent_tasks: int = 5
    cost_per_1k_tokens: float = 0.0
    avg_response_time_ms: int = 5000
    reliability_score: float = 1.0  # 0.0-1.0
    tags: List[str] = field(default_factory=list)

class AgentCardRegistry:
    """Central registry for A2A Agent Cards."""
    
    def __init__(self, storage_path: str = ".sisyphus/agent-cards"):
        self._cards: Dict[str, AgentCard] = {}
        self._metadata: Dict[str, AgentMetadata] = {}
        self._storage_path = storage_path
        self._index: Dict[str, List[str]] = {}  # capability → [agent_ids]
        self._lock = asyncio.Lock()
    
    async def register(self, card: AgentCard, metadata: AgentMetadata) -> None:
        """Register agent card with metadata."""
        pass
    
    async def unregister(self, agent_id: str) -> None:
        """Remove agent from registry."""
        pass
    
    async def discover(
        self,
        capabilities: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        min_reliability: float = 0.0,
        max_cost_per_1k: Optional[float] = None,
    ) -> List[AgentCard]:
        """Discover agents matching criteria."""
        pass
    
    async def get(self, agent_id: str) -> Optional[AgentCard]:
        """Get agent card by ID."""
        pass
    
    async def update_status(self, agent_id: str, status: str) -> None:
        """Update agent availability status."""
        pass
    
    async def heartbeat(self, agent_id: str) -> None:
        """Update agent last heartbeat timestamp."""
        pass
    
    async def get_available_agents(self) -> List[AgentCard]:
        """Get all available (not offline/busy) agents."""
        pass
    
    def _build_index(self) -> None:
        """Build capability → agent index for fast lookup."""
        pass
    
    def _compute_card_hash(self, card: AgentCard) -> str:
        """Compute deterministic hash for card verification."""
        pass
    
    async def export_cards(self, format: str = "json") -> str:
        """Export all cards in specified format."""
        pass
    
    async def import_cards(self, data: str, format: str = "json") -> int:
        """Import cards from external format."""
        pass
```

**Test Strategy**:
- `test_register_agent_card` — Verify card stored correctly
- `test_discover_by_capability` — Capability-based lookup returns correct agents
- `test_discover_by_tags` — Tag-based filtering works
- `test_heartbeat_tracking` — Status updates correctly
- `test_card_hash_integrity` — Hash computation is deterministic

**Success Criteria**:
- ✅ Registry stores/retrieves agent cards correctly
- ✅ Capability matching returns relevant agents
- ✅ Heartbeat tracking updates status in <100ms
- ✅ Export/import preserves all card data

---

### 3. capability_matcher.py (NEW)

**Purpose**: Intelligent capability matching for task routing

**Key Classes**:

```python
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np

@dataclass
class CapabilityScore:
    """Scored match between task requirements and agent capabilities."""
    agent_id: str
    capability_match: float  # 0.0-1.0
    tag_match: float  # 0.0-1.0
    cost_score: float  # 0.0-1.0 (lower is better)
    latency_score: float  # 0.0-1.0 (lower is better)
    reliability_score: float  # 0.0-1.0
    overall_score: float  # Weighted combination

@dataclass
class TaskRequirements:
    """Task requirements for matching."""
    required_capabilities: List[str]
    preferred_tags: List[str]
    max_cost_per_1k: Optional[float] = None
    max_latency_ms: Optional[int] = None
    min_reliability: float = 0.0
    allow_fallback: bool = True

class CapabilityMatcher:
    """LLM-aware capability matching for optimal agent selection."""
    
    def __init__(self, registry: AgentCardRegistry):
        self.registry = registry
        self._capability_embeddings: Dict[str, np.ndarray] = {}
    
    async def match(
        self,
        requirements: TaskRequirements,
        exclude: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[CapabilityScore]:
        """Match task requirements against available agents."""
        pass
    
    async def match_with_llm(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[CapabilityScore]:
        """Use LLM to analyze task and match capabilities."""
        pass
    
    async def suggest_fallback(
        self,
        primary_agent_id: str,
        requirements: TaskRequirements,
    ) -> Optional[AgentCard]:
        """Suggest fallback agent from fallback chain."""
        pass
    
    def _compute_capability_similarity(
        self,
        required: List[str],
        provided: List[str],
    ) -> float:
        """Compute similarity score between required and provided capabilities."""
        pass
    
    def _compute_weighted_score(
        self,
        scores: List[float],
        weights: List[float],
    ) -> float:
        """Compute weighted combination of scores."""
        pass
    
    async def explain_match(self, score: CapabilityScore) -> str:
        """Generate human-readable explanation of match."""
        pass
    
    async def batch_match(
        self,
        requirements_list: List[TaskRequirements],
    ) -> List[List[CapabilityScore]]:
        """Match multiple requirements in batch."""
        pass
```

**Test Strategy**:
- `test_capability_exact_match` — Exact capability match scores 1.0
- `test_capability_partial_match` — Partial match scores appropriately
- `test_tag_matching` — Tag-based matching works
- `test_cost_latency_filtering` — Filters exclude invalid agents
- `test_llm_matching` — LLM-based matching produces reasonable results
- `test_fallback_chain` — Fallback returns correct agent

**Success Criteria**:
- ✅ Exact matches score 1.0
- ✅ Partial matches score appropriately (0.5-0.9)
- ✅ Cost/latency filters work correctly
- ✅ LLM matching explains decisions

---

### 4. network_orchestrator.py (NEW)

**Purpose**: Hierarchical + swarm orchestration patterns

**Key Classes**:

```python
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio

class OrchestrationMode(str, Enum):
    """Orchestration strategy modes."""
    HIERARCHICAL = "hierarchical"  # Manager → Workers
    SWARM = "swarm"  # Peer-to-peer with dynamic handoffs
    SEQUENTIAL = "sequential"  # One agent after another
    PARALLEL = "parallel"  # All agents at once
    HYBRID = "hybrid"  # Combine modes

@dataclass
class WorkerConfig:
    """Configuration for worker agent pool."""
    agent_id: str
    max_concurrent: int = 3
    priority: int = 1  # 1-10, higher = more priority
    capabilities: List[str] = field(default_factory=list)

@dataclass
class OrchestrationTask:
    """Task to be executed by orchestration system."""
    task_id: str
    description: str
    requirements: TaskRequirements
    mode: OrchestrationMode
    workers: List[WorkerConfig]
    timeout_seconds: int = 300
    fallback_enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OrchestrationResult:
    """Result from orchestration execution."""
    task_id: str
    status: str  # "success", "partial", "failed"
    results: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    execution_time_ms: int
    agents_used: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

class NetworkOrchestrator:
    """Hierarchical + swarm orchestration engine."""
    
    def __init__(
        self,
        registry: AgentCardRegistry,
        matcher: CapabilityMatcher,
        resilience: "ResilienceMiddleware",
    ):
        self.registry = registry
        self.matcher = matcher
        self.resilience = resilience
        self._worker_pools: Dict[str, asyncio.Queue] = {}
        self._active_tasks: Dict[str, OrchestrationTask] = {}
        self._mode_defaults: Dict[OrchestrationMode, Callable] = {}
    
    async def execute(
        self,
        task: OrchestrationTask,
    ) -> OrchestrationResult:
        """Execute orchestration task based on mode."""
        pass
    
    async def execute_hierarchical(
        self,
        task: OrchestrationTask,
    ) -> OrchestrationResult:
        """Execute in hierarchical mode (manager → workers)."""
        pass
    
    async def execute_swarm(
        self,
        task: OrchestrationTask,
    ) -> OrchestrationResult:
        """Execute in swarm mode (peer-to-peer with handoffs)."""
        pass
    
    async def execute_parallel(
        self,
        task: OrchestrationTask,
    ) -> OrchestrationResult:
        """Execute in parallel mode (fan-out)."""
        pass
    
    async def execute_sequential(
        self,
        task: OrchestrationTask,
    ) -> OrchestrationResult:
        """Execute in sequential mode (pipeline)."""
        pass
    
    async def execute_hybrid(
        self,
        task: OrchestrationTask,
    ) -> OrchestrationResult:
        """Execute in hybrid mode (combine strategies)."""
        pass
    
    async def delegate_task(
        self,
        from_agent: str,
        to_agent: str,
        task: Task,
    ) -> Task:
        """Delegate task from one agent to another."""
        pass
    
    async def handoff(
        self,
        from_agent: str,
        to_agent: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Hand off execution from one agent to another."""
        pass
    
    async def broadcast(
        self,
        message: Message,
        target_agents: List[str],
    ) -> List[Message]:
        """Broadcast message to multiple agents."""
        pass
    
    async def get_task_status(self, task_id: str) -> Optional[OrchestrationTask]:
        """Get current status of orchestration task."""
        pass
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel running orchestration task."""
        pass
```

**Test Strategy**:
- `test_hierarchical_execution` — Manager delegates to workers correctly
- `test_swarm_handoff` — Dynamic handoff between agents
- `test_parallel_fanout` — All workers receive tasks simultaneously
- `test_sequential_pipeline` — Tasks execute in order
- `test_hybrid_combination` — Hybrid mode selects correct strategy

**Success Criteria**:
- ✅ Hierarchical mode delegates correctly
- ✅ Swarm handoffs preserve context
- ✅ Parallel execution distributes load
- ✅ Hybrid mode auto-selects best strategy

---

### 5. task_router.py (NEW)

**Purpose**: LLM-based intelligent task routing with cost/latency scoring

**Key Classes**:

```python
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import asyncio

class RoutingStrategy(str, Enum):
    """Task routing strategies."""
    COST_OPTIMIZED = "cost_optimized"
    LATENCY_OPTIMIZED = "latency_optimized"
    RELIABILITY_OPTIMIZED = "reliability_optimized"
    BALANCED = "balanced"
    CAPABILITY_MATCH = "capability_match"

@dataclass
class RouteDecision:
    """Decision from task router."""
    agent_id: str
    agent_card: AgentCard
    score: float
    reasoning: str
    strategy: RoutingStrategy
    estimated_cost: float
    estimated_latency_ms: int
    fallback_agent_id: Optional[str] = None

@dataclass
class TaskContext:
    """Context for routing decision."""
    task_description: str
    task_type: str  # "implementation", "research", "review", "debugging"
    complexity: str  # "simple", "moderate", "complex"
    estimated_tokens: Optional[int] = None
    required_capabilities: List[str] = []
    preferred_tags: List[str] = []
    user_preferences: Dict[str, Any] = {}
    session_context: Dict[str, Any] = {}

class TaskRouter:
    """LLM-based intelligent task routing."""
    
    def __init__(
        self,
        registry: AgentCardRegistry,
        matcher: CapabilityMatcher,
        llm_client: Optional[Any] = None,  # OpenAI-compatible
    ):
        self.registry = registry
        self.matcher = matcher
        self.llm_client = llm_client
        self._cost_cache: Dict[str, float] = {}
        self._latency_cache: Dict[str, int] = {}
    
    async def route(
        self,
        context: TaskContext,
        strategy: RoutingStrategy = RoutingStrategy.BALANCED,
    ) -> RouteDecision:
        """Route task to optimal agent."""
        pass
    
    async def route_with_llm(
        self,
        context: TaskContext,
    ) -> RouteDecision:
        """Use LLM to analyze task and make routing decision."""
        pass
    
    async def route_batch(
        self,
        contexts: List[TaskContext],
        strategy: RoutingStrategy = RoutingStrategy.BALANCED,
    ) -> List[RouteDecision]:
        """Route multiple tasks optimally."""
        pass
    
    async def estimate_cost(
        self,
        agent_id: str,
        task_description: str,
    ) -> float:
        """Estimate cost for task on agent."""
        pass
    
    async def estimate_latency(
        self,
        agent_id: str,
        task_description: str,
    ) -> int:
        """Estimate latency for task on agent."""
        pass
    
    def _compute_cost_score(
        self,
        estimated_cost: float,
        max_budget: Optional[float],
    ) -> float:
        """Compute cost score (0.0-1.0, lower cost = higher score)."""
        pass
    
    def _compute_latency_score(
        self,
        estimated_latency: int,
        max_latency: Optional[int],
    ) -> float:
        """Compute latency score (0.0-1.0, lower latency = higher score)."""
        pass
    
    async def explain_decision(self, decision: RouteDecision) -> str:
        """Generate human-readable explanation of routing decision."""
        pass
    
    async def record_outcome(
        self,
        decision: RouteDecision,
        actual_cost: float,
        actual_latency_ms: int,
        success: bool,
    ) -> None:
        """Record actual outcome for learning."""
        pass
    
    async def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics for analysis."""
        pass
```

**Test Strategy**:
- `test_cost_based_routing` — Lower cost agents selected when budget constrained
- `test_latency_based_routing` — Faster agents selected when time constrained
- `test_capability_routing` — Matching capabilities prioritized
- `test_llm_routing` — LLM analysis produces reasonable decisions
- `test_batch_routing` — Multiple tasks routed optimally

**Success Criteria**:
- ✅ Cost-aware routing minimizes spend
- ✅ Latency-aware routing minimizes wait time
- ✅ Capability matching finds suitable agents
- ✅ LLM routing explains decisions

---

### 6. resilience_middleware.py (NEW)

**Purpose**: Retry + circuit breaker + fallback for agent calls

**Key Classes**:

```python
from typing import Dict, List, Optional, Callable, Any, Type
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import asyncio
import time

class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: List[Type[Exception]] = []

@dataclass
class CircuitConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: float = 60.0
    half_open_max_calls: int = 3

@dataclass
class ResilienceConfig:
    """Combined resilience configuration."""
    retry: RetryConfig
    circuit: CircuitConfig
    fallback_enabled: bool = True
    timeout_seconds: float = 300.0

@dataclass
class CallResult:
    """Result from resilient call."""
    success: bool
    result: Any
    error: Optional[Exception]
    attempts: int
    latency_ms: int
    circuit_state: CircuitState

class ResilienceMiddleware:
    """Middleware for retry, circuit breaker, and fallback."""
    
    def __init__(self, config: ResilienceConfig):
        self.config = config
        self._circuit_states: Dict[str, CircuitState] = {}
        self._failure_counts: Dict[str, int] = {}
        self._success_counts: Dict[str, int] = {}
        self._last_failure_time: Dict[str, float] = {}
        self._half_open_calls: Dict[str, int] = {}
        self._fallback_handlers: Dict[str, Callable] = {}
    
    async def call(
        self,
        agent_id: str,
        func: Callable,
        *args,
        fallback: Optional[Callable] = None,
        **kwargs,
    ) -> CallResult:
        """Execute call with resilience patterns."""
        pass
    
    async def call_with_retry(
        self,
        agent_id: str,
        func: Callable,
        *args,
        **kwargs,
    ) -> CallResult:
        """Execute call with retry logic."""
        pass
    
    async def call_with_circuit(
        self,
        agent_id: str,
        func: Callable,
        *args,
        **kwargs,
    ) -> CallResult:
        """Execute call with circuit breaker."""
        pass
    
    def register_fallback(
        self,
        agent_id: str,
        handler: Callable,
    ) -> None:
        """Register fallback handler for agent."""
        pass
    
    async def get_circuit_state(self, agent_id: str) -> CircuitState:
        """Get current circuit state for agent."""
        pass
    
    async def reset_circuit(self, agent_id: str) -> None:
        """Manually reset circuit for agent."""
        pass
    
    def _should_retry(self, exception: Exception) -> bool:
        """Determine if exception is retryable."""
        pass
    
    def _compute_delay(self, attempt: int) -> float:
        """Compute delay for retry attempt."""
        pass
    
    async def _update_circuit(
        self,
        agent_id: str,
        success: bool,
    ) -> None:
        """Update circuit breaker state."""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get resilience statistics."""
        pass
```

**Test Strategy**:
- `test_retry_exponential_backoff` — Retry delays increase exponentially
- `test_retry_with_jitter` — Jitter prevents thundering herd
- `test_circuit_open_on_failures` — Circuit opens after threshold
- `test_circuit_half_open` — Circuit tests recovery
- `test_fallback_execution` — Fallback called when circuit open
- `test_timeout_enforcement` — Timeout cancels long calls

**Success Criteria**:
- ✅ Retry exponential backoff works correctly
- ✅ Circuit opens after 5 failures
- ✅ Circuit half-open tests recovery
- ✅ Fallback executes when enabled
- ✅ Timeout cancels hung calls

---

### 7. worker_pool.py (NEW)

**Purpose**: Fan-out parallel execution with worker pools

**Key Classes**:

```python
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio

class WorkerState(str, Enum):
    """Worker states."""
    IDLE = "idle"
    BUSY = "busy"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class WorkItem:
    """Item of work to be executed."""
    item_id: str
    payload: Any
    priority: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkResult:
    """Result from worker execution."""
    item_id: str
    success: bool
    result: Any
    error: Optional[str]
    worker_id: str
    execution_time_ms: int

@dataclass
class Worker:
    """Worker in the pool."""
    worker_id: str
    agent_id: str
    state: WorkerState
    current_item: Optional[WorkItem] = None
    completed_count: int = 0
    failed_count: int = 0

class WorkerPool:
    """Fan-out worker pool for parallel execution."""
    
    def __init__(
        self,
        max_workers: int = 10,
        max_queue_size: int = 100,
    ):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self._workers: Dict[str, Worker] = {}
        self._work_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._results: Dict[str, WorkResult] = {}
        self._active_count = 0
        self._lock = asyncio.Lock()
    
    async def submit(
        self,
        items: List[WorkItem],
        executor: Callable[[WorkItem], Any],
    ) -> List[WorkResult]:
        """Submit work items for parallel execution."""
        pass
    
    async def submit_with_dependencies(
        self,
        items: List[WorkItem],
        dependencies: Dict[str, List[str]],
        executor: Callable[[WorkItem], Any],
    ) -> List[WorkResult]:
        """Submit work with dependency resolution."""
        pass
    
    async def map_reduce(
        self,
        items: List[WorkItem],
        mapper: Callable[[WorkItem], Any],
        reducer: Callable[[List[Any]], Any],
    ) -> Any:
        """Execute map-reduce pattern."""
        pass
    
    async def _worker_loop(self, worker: Worker) -> None:
        """Main worker loop."""
        pass
    
    async def _execute_item(
        self,
        worker: Worker,
        item: WorkItem,
        executor: Callable[[WorkItem], Any],
    ) -> WorkResult:
        """Execute single work item."""
        pass
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get worker pool statistics."""
        pass
    
    async def scale_up(self, count: int) -> None:
        """Add workers to pool."""
        pass
    
    async def scale_down(self, count: int) -> None:
        """Remove idle workers from pool."""
        pass
    
    def get_idle_workers(self) -> List[str]:
        """Get list of idle worker IDs."""
        pass
```

**Test Strategy**:
- `test_parallel_execution` — Multiple workers execute simultaneously
- `test_work_distribution` — Work distributed evenly
- `test_map_reduce` — Map-reduce pattern produces correct results
- `test_dependency_resolution` — Dependencies enforced correctly
- `test_worker_scaling` — Dynamic scaling works

**Success Criteria**:
- ✅ Parallel execution uses all available workers
- ✅ Work distributed based on priority
- ✅ Map-reduce produces correct aggregated results
- ✅ Dependencies prevent invalid ordering

---

### 8. load_balancer.py (NEW)

**Purpose**: Agent work queue distribution and load balancing

**Key Classes**:

```python
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time

class BalanceStrategy(str, Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    COST_AWARE = "cost_aware"
    LATENCY_AWARE = "latency_aware"

@dataclass
class AgentLoad:
    """Current load state for an agent."""
    agent_id: str
    active_tasks: int = 0
    queued_tasks: int = 0
    avg_response_time_ms: int = 0
    error_rate: float = 0.0
    last_updated: float = field(default_factory=time.time)

@dataclass
class LoadBalanceConfig:
    """Configuration for load balancing."""
    strategy: BalanceStrategy = BalanceStrategy.LEAST_CONNECTIONS
    max_active_per_agent: int = 5
    max_queued_per_agent: int = 10
    health_check_interval_seconds: int = 30
    eviction_threshold: float = 0.5  # Error rate to evict

class LoadBalancer:
    """Load balancer for agent work queues."""
    
    def __init__(
        self,
        registry: AgentCardRegistry,
        config: LoadBalanceConfig,
    ):
        self.registry = registry
        self.config = config
        self._loads: Dict[str, AgentLoad] = {}
        self._round_robin_index: Dict[str, int] = {}
        self._weights: Dict[str, int] = {}
        self._lock = asyncio.Lock()
    
    async def select_agent(
        self,
        task_requirements: Optional[TaskRequirements] = None,
        exclude: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Select optimal agent based on load and strategy."""
        pass
    
    async def register_agent(
        self,
        agent_id: str,
        weight: int = 1,
    ) -> None:
        """Register agent for load balancing."""
        pass
    
    async def unregister_agent(self, agent_id: str) -> None:
        """Remove agent from load balancing."""
        pass
    
    async def update_load(
        self,
        agent_id: str,
        active_delta: int = 0,
        queued_delta: int = 0,
        response_time_delta: int = 0,
        error_delta: float = 0.0,
    ) -> None:
        """Update load metrics for agent."""
        pass
    
    async def get_load(self, agent_id: str) -> Optional[AgentLoad]:
        """Get current load for agent."""
        pass
    
    async def get_all_loads(self) -> Dict[str, AgentLoad]:
        """Get load for all agents."""
        pass
    
    async def health_check(self) -> List[str]:
        """Check agent health and return unhealthy agent IDs."""
        pass
    
    async def rebalance(self) -> Dict[str, str]:
        """Rebalance loads across agents."""
        pass
    
    def _select_round_robin(self, agent_ids: List[str]) -> str:
        """Select agent using round-robin."""
        pass
    
    def _select_least_connections(self, agent_ids: List[str]) -> str:
        """Select agent with least connections."""
        pass
    
    def _select_weighted(self, agent_ids: List[str]) -> str:
        """Select agent using weighted distribution."""
        pass
    
    def _select_cost_aware(self, agent_ids: List[str], requirements: TaskRequirements) -> str:
        """Select agent using cost-aware strategy."""
        pass
    
    def _select_latency_aware(self, agent_ids: List[str]) -> str:
        """Select agent using latency-aware strategy."""
        pass
```

**Test Strategy**:
- `test_round_robin_distribution` — Even distribution across agents
- `test_least_connections` — Lowest load agent selected
- `test_weighted_distribution` — Weighted based on capacity
- `test_health_eviction` — Unhealthy agents removed
- `test_cost_aware_selection` — Cost-optimized agent selected

**Success Criteria**:
- ✅ Round-robin distributes evenly
- ✅ Least connections selects optimal agent
- ✅ Weighted distribution respects capacity
- ✅ Health checks remove unhealthy agents

---

### 9. sisyphus.py (ENHANCE)

**Purpose**: Enhance existing plan executor with orchestration capabilities

**Changes to existing implementation**:
- Integrate with Agent Card Registry
- Add task decomposition for parallel execution
- Add fallback chain execution
- Add orchestration mode selection

**New Functions**:

```python
# ── New Orchestration Methods ────────────────────────────────────────────────

class SisyphusEnhanced:
    """Enhanced Sisyphus with orchestration capabilities."""
    
    def __init__(self):
        self.registry = AgentCardRegistry()
        self.matcher = CapabilityMatcher(self.registry)
        self.router = TaskRouter(self.registry, self.matcher)
        self.orchestrator = NetworkOrchestrator(
            self.registry,
            self.matcher,
            ResilienceMiddleware(ResilienceConfig(...))
        )
        self.load_balancer = LoadBalancer(self.registry, LoadBalanceConfig(...))
    
    async def execute_plan_with_orchestration(
        self,
        plan: "Plan",
        mode: OrchestrationMode = OrchestrationMode.HYBRID,
    ) -> "ExecutionResult":
        """Execute plan with intelligent orchestration."""
        pass
    
    async def decompose_task(
        self,
        task: str,
    ) -> List["SubTask"]:
        """Decompose task into parallelizable subtasks."""
        pass
    
    async def execute_with_fallback_chain(
        self,
        task: "Task",
        fallback_chain: List[str],
    ) -> "TaskResult":
        """Execute task with fallback chain."""
        pass
    
    async def select_optimal_agent(
        self,
        task: "Task",
    ) -> "RouteDecision":
        """Select optimal agent for task."""
        pass
```

**Test Strategy**:
- `test_plan_orchestration` — Plan executes with orchestration
- `test_task_decomposition` — Tasks decomposed correctly
- `test_fallback_chain_execution` — Fallback chain works
- `test_agent_selection` — Optimal agent selected

---

### 10. prometheus.py (ENHANCE)

**Purpose**: Enhance existing plan builder with task routing

**Changes to existing implementation**:
- Add LLM-based task analysis
- Add cost/latency estimation
- Add capability requirement extraction

**New Functions**:

```python
class PrometheusEnhanced:
    """Enhanced Prometheus with routing intelligence."""
    
    def __init__(self):
        self.router = TaskRouter(...)
    
    async def analyze_task_for_routing(
        self,
        task_description: str,
    ) -> TaskContext:
        """Analyze task to extract routing requirements."""
        pass
    
    async def estimate_task_properties(
        self,
        task: "Task",
    ) -> Dict[str, Any]:
        """Estimate tokens, complexity, and requirements."""
        pass
    
    async def build_routed_plan(
        self,
        tasks: List["Task"],
    ) -> "Plan":
        """Build plan with optimal agent routing."""
        pass
```

---

### 11. hephaestus.py (ENHANCE)

**Purpose**: Enhance existing implementation agent with delegation

**Changes to existing implementation**:
- Add A2A delegation support
- Add parallel implementation coordination
- Add result aggregation

**New Functions**:

```python
class HephaestusEnhanced:
    """Enhanced Hephaestus with delegation support."""
    
    def __init__(self):
        self.orchestrator = NetworkOrchestrator(...)
        self.resilience = ResilienceMiddleware(...)
    
    async def delegate_to_agent(
        self,
        task: "Task",
        agent_id: str,
    ) -> "TaskResult":
        """Delegate task to another agent via A2A."""
        pass
    
    async def coordinate_parallel_implementation(
        self,
        subtasks: List["SubTask"],
    ) -> List["TaskResult"]:
        """Coordinate parallel implementation of subtasks."""
        pass
    
    async def aggregate_results(
        self,
        results: List["TaskResult"],
    ) -> "AggregatedResult":
        """Aggregate results from multiple agents."""
        pass
```

---

## 🔗 Integration Points

### With Layer 2 (Memory System)
- Agent Cards stored in `.sisyphus/agent-cards/` (versioned via memory system)
- Task history and results stored in memory for learning

### With Layer 4 (Self-Healing)
- Health checks integrate with LoadBalancer health_check()
- Circuit breaker states visible in health dashboard

### With Layer 6 (MCP Servers)
- MCP tool definitions exposed as agent capabilities
- A2A ↔ MCP interoperability for context sharing

### With Layer 8 (Testing)
- MockAgent protocol for testing orchestration
- Trace format includes orchestration decisions

---

## 📦 Dependencies Between Modules

```
a2a_protocol.py
    └── agent_card.py (AgentCard model)
        └── capability_matcher.py
            └── task_router.py
                └── network_orchestrator.py
                    └── worker_pool.py
                    └── load_balancer.py
            └── resilience_middleware.py

sisyphus.py (enhanced)
    ├── a2a_protocol.py
    ├── agent_card.py
    ├── task_router.py
    └── network_orchestrator.py

prometheus.py (enhanced)
    └── task_router.py

hephaestus.py (enhanced)
    ├── network_orchestrator.py
    └── resilience_middleware.py
```

---

## 🧪 Test Strategy Summary

| Component | Unit Tests | Integration Tests | Mock Strategy |
|-----------|------------|-------------------|---------------|
| a2a_protocol.py | 8 | 4 | MockAgent |
| agent_card.py | 10 | 3 | In-memory storage |
| capability_matcher.py | 12 | 5 | MockLLM |
| network_orchestrator.py | 10 | 6 | MockAgentPool |
| task_router.py | 8 | 4 | MockRegistry |
| resilience_middleware.py | 15 | 5 | MockExecutor |
| worker_pool.py | 10 | 4 | MockExecutor |
| load_balancer.py | 8 | 3 | MockRegistry |

---

## ✅ Success Criteria

### Phase 1: Core Infrastructure
- [ ] Agent Card Registry operational
- [ ] A2A message types serialization working
- [ ] Capability matcher returns relevant agents

### Phase 2: Orchestration
- [ ] Task router selects optimal agents
- [ ] Network orchestrator executes in all modes
- [ ] Load balancer distributes work correctly

### Phase 3: Resilience
- [ ] Retry with exponential backoff works
- [ ] Circuit breaker opens/closes correctly
- [ ] Fallback execution triggers on failure

### Phase 4: Enhancement
- [ ] Sisyphus enhanced with orchestration
- [ ] Prometheus enhanced with routing
- [ ] Hephaestus enhanced with delegation

---

## 🎯 Implementation Order

### Sprint 1: Foundation (Week 5)
1. **Day 1-2**: `a2a_protocol.py` — Core message types
2. **Day 3-4**: `agent_card.py` — Registry implementation
3. **Day 5**: `capability_matcher.py` — Basic matching

### Sprint 2: Intelligence (Week 5-6)
4. **Day 6-7**: `task_router.py` — LLM-based routing
5. **Day 8**: `resilience_middleware.py` — Retry + circuit breaker

### Sprint 3: Execution (Week 6)
6. **Day 9-10**: `network_orchestrator.py` — Orchestration modes
7. **Day 11**: `worker_pool.py` — Parallel execution
8. **Day 12**: `load_balancer.py` — Work distribution

### Sprint 4: Integration (Week 6)
9. **Day 13**: `sisyphus.py` — Enhancement
10. **Day 14**: `prometheus.py` + `hephaestus.py` — Enhancement
11. **Day 15**: Integration testing

---

## 🔧 Category + Skills Mapping

| Task | Category | Skills | Agent |
|------|----------|--------|-------|
| A2A protocol implementation | deep | ["python", "async", "pydantic"] | hephaestus |
| Agent card registry | deep | ["python", "asyncio", "storage"] | hephaestus |
| Capability matching | ultrabrain | ["python", "algorithms", "llm"] | prometheus |
| Task routing | ultrabrain | ["python", "llm", "cost-optimization"] | prometheus |
| Resilience middleware | deep | ["python", "patterns", "circuit-breaker"] | hephaestus |
| Worker pool | deep | ["python", "async", "parallel"] | hephaestus |
| Load balancer | deep | ["python", "algorithms", "queues"] | hephaestus |
| Network orchestrator | ultrabrain | ["python", "orchestration", "state-machine"] | sisyphus |
| Sisyphus enhancement | deep | ["python", "delegation", "orchestration"] | hephaestus |
| Integration testing | unspecified-low | ["python", "pytest", "mocking"] | sisyphus-junior |

---

## 📊 Parallel Execution Opportunities

| Tasks | Can Run In Parallel | Dependencies |
|-------|---------------------|---------------|
| a2a_protocol.py + agent_card.py | ✅ Yes | agent_card.py uses AgentCard from a2a_protocol.py |
| capability_matcher + task_router | ❌ No | task_router uses matcher |
| resilience_middleware + worker_pool | ✅ Yes | No dependencies |
| load_balancer + network_orchestrator | ❌ No | orchestrator uses balancer |
| prometheus.py + hephaestus.py | ✅ Yes | Can implement simultaneously |
| All unit tests | ✅ Yes | Independent |

**Recommended parallel groups**:
1. **Group A**: a2a_protocol.py → agent_card.py → capability_matcher.py
2. **Group B**: resilience_middleware.py, worker_pool.py (independent)
3. **Group C**: prometheus.py, hephaestus.py (simultaneous enhancement)

---

## 🔨 Atomic Commit Strategy

### Commit 1: Core Types
```
feat(orchestration): Add A2A protocol core types

- Add Message, Task, AgentCard pydantic models
- Add MessageRole, TaskState enums
- Add JSON-RPC serialization helpers
- Add tests for serialization round-trip
```

### Commit 2: Registry
```
feat(orchestration): Add Agent Card Registry

- Add AgentCardRegistry with async registration
- Add capability-based discovery
- Add heartbeat tracking
- Add export/import functionality
```

### Commit 3: Capability Matching
```
feat(orchestration): Add capability matching

- Add CapabilityMatcher with similarity scoring
- Add LLM-based matching option
- Add fallback chain resolution
- Add match explanation generation
```

### Commit 4: Task Routing
```
feat(orchestration): Add intelligent task routing

- Add TaskRouter with cost/latency scoring
- Add multiple routing strategies
- Add routing decision explanation
- Add outcome recording for learning
```

### Commit 5: Resilience
```
feat(orchestration): Add resilience middleware

- Add RetryConfig with exponential backoff
- Add CircuitConfig with state machine
- Add ResilienceMiddleware with retry + circuit
- Add fallback handler registration
```

### Commit 6: Worker Pool
```
feat(orchestration): Add worker pool for parallel execution

- Add WorkerPool with fan-out execution
- Add WorkItem, WorkResult models
- Add map-reduce pattern support
- Add dependency resolution
```

### Commit 7: Load Balancer
```
feat(orchestration): Add load balancer

- Add LoadBalancer with multiple strategies
- Add AgentLoad tracking
- Add health check integration
- Add rebalancing support
```

### Commit 8: Network Orchestrator
```
feat(orchestration): Add network orchestrator

- Add NetworkOrchestrator with multiple modes
- Add hierarchical, swarm, parallel, sequential execution
- Add task delegation and handoff
- Add broadcast functionality
```

### Commit 9: Sisyphus Enhancement
```
feat(sisyphus): Enhance with orchestration capabilities

- Add AgentCardRegistry integration
- Add task decomposition for parallel execution
- Add fallback chain execution
- Add orchestration mode selection
```

### Commit 10: Prometheus Enhancement
```
feat(prometheus): Enhance with routing intelligence

- Add TaskContext extraction from task description
- Add cost/latency estimation
- Add capability requirement extraction
- Add routed plan building
```

### Commit 11: Hephaestus Enhancement
```
feat(hephaestus): Enhance with delegation support

- Add A2A delegation to agents
- Add parallel implementation coordination
- Add result aggregation
- Add fallback execution
```

### Commit 12: Integration
```
test(orchestration): Add integration tests

- Add end-to-end orchestration tests
- Add multi-agent coordination tests
- Add failure recovery tests
- Add performance benchmarks
```

---

## 📋 Acceptance Criteria

### Must Have (MVP)
- [ ] Agent Cards serialize/deserialize correctly
- [ ] Registry stores and retrieves agents
- [ ] Capability matching returns relevant agents
- [ ] Task router selects agents based on strategy
- [ ] Resilience middleware handles retries
- [ ] Worker pool executes in parallel
- [ ] Load balancer distributes work

### Should Have
- [ ] LLM-based task analysis for routing
- [ ] Circuit breaker state visible in health
- [ ] All orchestration modes work (hierarchical, swarm, parallel)
- [ ] Fallback chain executes on failure

### Nice to Have
- [ ] Map-reduce pattern for aggregation
- [ ] Dynamic worker scaling
- [ ] Cost/latency learning from outcomes
- [ ] A2A protocol compliance certified

---

## 🚀 Ultrawork Execution Notes

### Pre-Execution Checklist
- [ ] All environment variables set
- [ ] Dependencies installed (pydantic, asyncio)
- [ ] Test database initialized
- [ ] Mock agents configured

### Execution Mode
- **Recommended**: Use `/ulw-loop` for continuous execution
- **Batch size**: 2-3 files per cycle
- **Verification**: Run tests after each file

### Quality Gates
- **Type check**: `python -m mypy src/orchestration/`
- **Lint**: `python -m ruff src/orchestration/`
- **Tests**: `pytest src/orchestration/tests/ -v`
- **Import order**: `python -m isort --check-only src/orchestration/`

---

*Document Version: 1.0*  
*Created: 2026-04-04*  
*Layer: 5 (Agent Orchestration)*  
*Status: Ready for Implementation*

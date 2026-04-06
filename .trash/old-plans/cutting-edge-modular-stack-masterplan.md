# N-Xyme_MIND — Cutting-Edge Modular Stack Masterplan

> **Version**: 1.0 | **Date**: 2026-04-06
> **Goal**: Bundle all memory, learning, tools, and infrastructure into modular, hotswappable packages with clean interfaces. No more monolithic sprawl.

---

## 1. Current State Audit

### What Exists (Real, Not Hallucinated)

| Directory | Files | Status | Problem |
|-----------|-------|--------|---------|
| `src/memory/` | 70+ files | **BLOATED** | Everything mixed: vectors, graphs, sessions, file indexing, retrievers, migrations, daemons |
| `src/tools/` | 60+ files | **SCATTERED** | Intelligence, learning, middleware, observability, state, tracing all dumped here |
| `src/intelligence/` | 40+ files | **DUPLICATE** | Same files exist in both `src/tools/intelligence/` AND `src/intelligence/` |
| `src/learning/` | Empty | **DEAD** | Just `__init__.py`, actual learning code is in `src/tools/learning/` |
| `src/infrastructure/` | 50+ files | **MIXED** | Proxy, network, rate limiting, circuit breakers, cost tracking, telemetry |
| `src/orchestration/` | 60+ files | **MIXED** | Agents, workers, triggers, session management, tool registry |
| `src/observability/` | 2 files | OK | Logger + metrics |
| `src/security/` | Growing | OK | Audit, sandbox, policy |
| `bin/` | 50+ scripts | **SCATTERED** | Health, routing, model, VPN, quality gates, CLI tools |

### Duplication Found
- `src/intelligence/unified_router.py` ↔ `src/tools/intelligence/unified_router.py`
- `src/intelligence/learning.py` ↔ `src/tools/learning/`
- `src/memory/retrievers/` ↔ `src/memory/semantic.py` (duplicate retriever logic)
- `src/memory/mcp_server.py` ↔ `src/memory/mcp_server_v2.py`
- `src/memory/content_extractor.py` ↔ `src/memory/content_extractors.py`
- `src/infrastructure/metrics_store.py` ↔ `src/tools/observability/metrics.py`
- Learning code split across `src/tools/learning/`, `src/tools/intelligence/learning.py`, `src/infrastructure/proxy/learning_engine.py`

### Dependency Hell
- `src/tools/intelligence/unified_router.py` imports from `src/memory/`, `src/tools/learning/`, `src/tools/middleware/`
- `src/memory/mcp_server.py` imports from `src/tools/intelligence/`
- `src/orchestration/` imports from everywhere
- Circular: memory → intelligence → learning → intelligence

---

## 2. Target Architecture — 6 Bundles

### Bundle 1: `memory-core` — Unified Memory System
**What it owns**: All memory storage, retrieval, and indexing.

```
packages/memory-core/
├── __init__.py              # Public API: search(), store(), recall()
├── config.py                # Memory configuration
│
├── stores/                  # Storage backends (hotswappable)
│   ├── __init__.py
│   ├── base.py              # Abstract Store interface
│   ├── vector_store.py      # Chroma/Qdrant/LanceDB adapter
│   ├── graph_store.py       # Knowledge graph (NetworkX/Neo4j)
│   ├── relational_store.py  # SQLite for structured memory
│   └── file_store.py        # File-based episodic memory
│
├── retrievers/              # Retrieval strategies (hotswappable)
│   ├── __init__.py
│   ├── base.py              # Abstract Retriever interface
│   ├── semantic.py          # Embedding-based retrieval
│   ├── keyword.py           # BM25/text search
│   └── fusion.py            # RRF fusion of multiple retrievers
│
├── indexing/                # File indexing pipeline
│   ├── __init__.py
│   ├── scanner.py           # Drive/file scanner
│   ├── chunker.py           # Text chunking strategies
│   ├── embedder.py          # Embedding pipeline
│   ├── file_registry.py     # File tracking (SQLite)
│   └── watcher.py           # File change detection
│
├── sessions/                # Session memory
│   ├── __init__.py
│   ├── lifecycle.py         # Session start/end/archive
│   ├── context.py           # Working memory per session
│   └── archiver.py          # Session → long-term memory
│
├── cognitive/               # Cognitive memory features
│   ├── __init__.py
│   ├── forgetting.py        # Adaptive forgetting curves
│   ├── reconsolidation.py   # Memory consolidation during sleep
│   ├── sleep_engine.py      # Sleep cycle processing
│   ├── priority.py          # Memory priority scoring
│   ├── retention.py         # Retention policy
│   └── trust.py             # Trust-aware retrieval
│
├── migrations/              # Database migrations
│   ├── __init__.py
│   └── (migration files)
│
├── mcp_server.py            # MCP server for memory tools
├── health.py                # Memory system health checks
└── daemon.py                # Background indexing daemon
```

**Public Interface**:
```python
# Search across all memory sources
results = memory.search("query", limit=10, sources=["vector", "graph"])

# Store new memory
memory.store(content, type="episodic", tags=["code", "python"])

# Recall session context
ctx = memory.recall_session(session_id="...")

# Get memory stats
stats = memory.stats()
```

**Hotswap Points**:
- `stores/vector_store.py` — Swap Chroma → Qdrant → LanceDB without changing API
- `retrievers/` — Add new retrieval strategies without touching storage
- `indexing/` — Change chunking/embedding without affecting retrieval

---

### Bundle 2: `learning-engine` — Self-Learning System
**What it owns**: All ML, RL, routing optimization, delegation learning.

```
packages/learning-engine/
├── __init__.py              # Public API: learn(), predict(), adapt()
├── config.py                # Learning configuration
│
├── rl/                      # Reinforcement Learning (hotswappable)
│   ├── __init__.py
│   ├── q_learning.py        # Tabular Q-Learning with TD updates
│   ├── bandits.py           # Multi-Armed Bandit (UCB, Thompson)
│   ├── policy.py            # Policy management
│   └── rewards.py           # Reward function definitions
│
├── meta/                    # Meta-Learning
│   ├── __init__.py
│   ├── maml.py              # MAML-style adaptation
│   ├── ewc.py               # Elastic Weight Consolidation
│   └── active.py            # Active learning (uncertainty sampling)
│
├── routing/                 # Routing optimization
│   ├── __init__.py
│   ├── optimizer.py         # Routing weight optimization
│   ├── predictor.py         # ML-based routing predictions
│   ├── ab_testing.py        # A/B testing framework
│   └── counterfactual.py    # "What-if" analysis
│
├── delegation/              # Delegation learning
│   ├── __init__.py
│   ├── logger.py            # Outcome logging
│   ├── learner.py           # Delegation pattern learning
│   └── skill_registry.py    # Skill lifecycle management
│
├── models/                  # Model persistence
│   ├── __init__.py
│   ├── serializer.py        # Model save/load (joblib/pickle)
│   ├── versioning.py        # Model version tracking
│   └── rollback.py          # Model rollback on degradation
│
├── analytics/               # Learning analytics
│   ├── __init__.py
│   ├── metrics.py           # Learning progress metrics
│   ├── dashboard.py         # Real-time metrics dashboard
│   └── reports.py           # Periodic learning reports
│
├── db.py                    # Learning database (SQLite)
├── event_bus.py             # Learning event system
└── signals.py               # Learning signals/triggers
```

**Public Interface**:
```python
# Record delegation outcome
learning.record_outcome(task="fix bug", agent="hephaestus", success=True, latency_ms=1500)

# Get routing recommendation
decision = learning.route_task("implement JWT auth")

# Get learning status
status = learning.status()

# Trigger model retraining
learning.retrain()
```

**Hotswap Points**:
- `rl/` — Swap Q-Learning → PPO → SAC without touching routing code
- `meta/` — Add new meta-learning algorithms independently
- `models/serializer.py` — Change serialization format without affecting learning logic

---

### Bundle 3: `intelligence` — Routing & Delegation
**What it owns**: Task routing, agent delegation, complexity scoring, triggers.

```
packages/intelligence/
├── __init__.py              # Public API: route(), delegate(), score()
├── config.py                # Intelligence configuration
│
├── router/                  # Core routing
│   ├── __init__.py
│   ├── unified.py           # UnifiedDelegationRouter (6 strategies)
│   ├── trigger.py           # Trigger-based routing (24 patterns)
│   ├── memory.py            # Memory-augmented routing
│   ├── ml.py                # ML-based routing predictions
│   ├── local_model.py       # Ollama-based analysis
│   └── keyword.py           # Keyword fallback (L1-L5)
│
├── scoring/                 # Task scoring
│   ├── __init__.py
│   ├── complexity.py        # L1-L5 complexity scoring
│   ├── dynamic.py           # Dynamic scoring based on history
│   └── token_estimator.py   # Token cost estimation
│
├── delegation/              # Delegation execution
│   ├── __init__.py
│   ├── decomposer.py        # Task decomposition
│   ├── context_sharing.py   # Context passing between agents
│   └── communication.py     # Inter-agent communication
│
├── triggers/                # Trigger system
│   ├── __init__.py
│   ├── patterns.py          # Trigger pattern definitions
│   ├── dynamic.py           # Dynamic trigger generation
│   └── registry.py          # Trigger registration
│
├── middleware/              # Request/response middleware
│   ├── __init__.py
│   ├── interceptor.py       # DelegationInterceptor
│   ├── sandbox.py           # Security sandbox
│   └── rate_limiter.py      # Rate limiting
│
├── review/                  # Review triage
│   ├── __init__.py
│   ├── triage.py            # Review triage logic
│   ├── security_gate.py     # Security-sensitive path detection
│   └── quality.py           # Code quality tracking
│
├── templates/               # Prompt templates
│   ├── __init__.py
│   └── prompts.py           # Delegation prompt templates
│
└── db.py                    # Routing database (SQLite)
```

**Public Interface**:
```python
# Route a task
decision = intelligence.route("fix auth bug")
# Returns: RoutingDecision(level=3, agent="hephaestus", confidence=0.8, ...)

# Get complexity score
score = intelligence.score_complexity("implement JWT auth")
# Returns: ComplexityScore(level=4, estimated_tokens=15000, ...)

# Get available agents
agents = intelligence.available_agents()
```

**Hotswap Points**:
- `router/` — Add new routing strategies without changing the unified interface
- `triggers/` — Update trigger patterns without touching routing logic
- `scoring/` — Change complexity algorithm independently

---

### Bundle 4: `infrastructure` — Platform Services
**What it owns**: Proxy, network, rate limiting, circuit breakers, cost tracking, telemetry.

```
packages/infrastructure/
├── __init__.py              # Public API: proxy(), monitor(), track()
├── config.py                # Infrastructure configuration
│
├── proxy/                   # Model proxy (hotswappable)
│   ├── __init__.py
│   ├── server.py            # MCP proxy server
│   ├── router.py            # Intelligent model routing
│   ├── brain.py             # Router brain (learning-enabled)
│   ├── key_pool.py          # API key pooling
│   ├── connection_pool.py   # Connection pooling
│   ├── cache.py             # LRU cache for responses
│   └── dlq.py               # Dead letter queue
│
├── network/                 # Network layer
│   ├── __init__.py
│   ├── vpn_manager.py       # VPN management
│   ├── vpn_rotator.py       # IP rotation
│   └── socks5.py            # SOCKS5 proxy management
│
├── resilience/              # Resilience patterns
│   ├── __init__.py
│   ├── circuit_breaker.py   # Circuit breaker pattern
│   ├── retry.py             # Retry with backoff
│   ├── fallback.py          # Fallback registry
│   └── backpressure.py      # Backpressure handling
│
├── monitoring/              # Observability
│   ├── __init__.py
│   ├── health.py            # Health checks (L0/L1/L2)
│   ├── metrics.py           # Metrics collection
│   ├── telemetry.py         # Telemetry
│   ├── anomaly.py           # Anomaly detection
│   └── alerts.py            # Alert system
│
├── cost/                    # Cost management
│   ├── __init__.py
│   ├── tracker.py           # Cost tracking
│   ├── optimizer.py         # Cost optimization
│   └── budget.py            # Budget tracking
│
├── config/                  # Configuration management
│   ├── __init__.py
│   ├── manager.py           # Config management
│   ├── validation.py        # Config validation
│   └── feature_flags.py     # Feature flags
│
└── utils/                   # Shared utilities
    ├── __init__.py
    ├── serialization.py     # Data serialization
    ├── datetime.py          # DateTime utilities
    └── hashing.py           # Hashing utilities
```

**Public Interface**:
```python
# Route API request through proxy
response = infrastructure.proxy.request(model="gpt-4", messages=[...])

# Check system health
health = infrastructure.health.check()
# Returns: HealthStatus(level="L1", services={"ollama": "up", ...})

# Track cost
cost = infrastructure.cost.track(tokens=15000, model="gpt-4")
```

**Hotswap Points**:
- `proxy/` — Swap proxy implementation without affecting routing
- `network/` — Change VPN provider independently
- `monitoring/` — Add new health checks without touching other services

---

### Bundle 5: `orchestration` — Agent Coordination
**What it owns**: Agent lifecycle, task execution, session management, tool registry.

```
packages/orchestration/
├── __init__.py              # Public API: spawn(), execute(), manage()
├── config.py                # Orchestration configuration
│
├── agents/                  # Agent management
│   ├── __init__.py
│   ├── registry.py          # Agent card registry
│   ├── lifecycle.py         # Agent start/stop/restart
│   ├── worker.py            # Agent worker pool
│   ├── pool.py              # Worker pool management
│   └── preferences.py       # Agent preferences
│
├── tasks/                   # Task management
│   ├── __init__.py
│   ├── lifecycle.py         # Task state machine
│   ├── router.py            # Task routing (delegates to intelligence)
│   ├── dispatcher.py        # Parallel task dispatch
│   ├── executor.py          # Task execution
│   └── checkpoint.py        # Checkpoint/resume
│
├── sessions/                # Session management
│   ├── __init__.py
│   ├── manager.py           # Session lifecycle
│   ├── context.py           # Session context
│   ├── state.py             # Session state persistence
│   └── transfer.py          # Cross-session transfer
│
├── tools/                   # Tool management
│   ├── __init__.py
│   ├── registry.py          # Tool registry
│   ├── factory.py           # Tool factory
│   ├── contract.py          # Tool contracts
│   ├── search.py            # Tool search
│   └── errors.py            # Tool error definitions
│
├── triggers/                # Trigger engine
│   ├── __init__.py
│   ├── engine.py            # Trigger engine
│   └── router.py            # Trigger routing
│
├── governance/              # Governance
│   ├── __init__.py
│   ├── policy.py            # Governance policy
│   ├── permissions.py       # Permission system
│   └── grounding.py         # Grounding/fact verification
│
└── catalyst.py              # CATALYST workflow engine
```

**Public Interface**:
```python
# Spawn an agent task
task_id = orchestration.spawn(
    agent="hephaestus",
    task="fix bug in auth",
    context={"file": "src/auth.py"}
)

# Get task status
status = orchestration.task_status(task_id)

# Get available tools
tools = orchestration.tools.list()
```

**Hotswap Points**:
- `agents/` — Add new agent types without changing task execution
- `tools/` — Register new tools without restarting orchestration
- `triggers/` — Update trigger engine independently

---

### Bundle 6: `platform` — CLI, Dashboard, Scripts
**What it owns**: All bin/ scripts, TUI, dashboard, health monitors.

```
packages/platform/
├── __init__.py
├── cli/                     # CLI tools
│   ├── __init__.py
│   ├── queue.py             # Queue CLI
│   ├── trace.py             # Trace CLI
│   ├── security.py          # Security CLI
│   └── worker.py            # Worker CLI
│
├── dashboard/               # Monitoring dashboard
│   ├── __init__.py
│   ├── app.py               # Main dashboard app
│   ├── routing.py           # Routing metrics view
│   ├── learning.py          # Learning progress view
│   └── health.py            # Health status view
│
├── tui/                     # Terminal UI
│   ├── __init__.py
│   ├── app.py               # Main TUI app
│   └── styles.tcss          # TUI styles
│
├── scripts/                 # Operational scripts
│   ├── health/              # Health check scripts
│   │   ├── l0-blink.sh      # <1s pre-flight
│   │   ├── l1-pulse.sh      # <10s service check
│   │   └── l2-vitals.sh     # <60s deep integrity
│   ├── quality-gates/       # Quality gate scripts
│   │   ├── gate-1-typecheck.sh
│   │   ├── gate-2-lint.sh
│   │   ├── gate-3-format.sh
│   │   ├── gate-4-test.sh
│   │   ├── gate-5-secrets.sh
│   │   ├── gate-6-placeholders.sh
│   │   ├── gate-7-agent-calls.sh
│   │   ├── gate-8-security-paths.sh
│   │   ├── gate-9-deps.sh
│   │   ├── gate-10-sast.sh
│   │   └── gate-11-coverage-trend.sh
│   ├── model/               # Model management scripts
│   │   ├── router.py
│   │   ├── selector.py
│   │   ├── health.py
│   │   └── fallback.py
│   └── memory/              # Memory management scripts
│       ├── n-xyme-memory.sh
│       └── n-xyme-memory.service
│
└── launcher.py              # Main launcher (n-xyme-mind.sh replacement)
```

---

## 3. Dependency Graph

```
platform
    └── orchestration
            ├── intelligence (routing decisions)
            ├── memory-core (context loading)
            └── infrastructure (health monitoring)

orchestration
    ├── intelligence (task routing)
    ├── memory-core (session state)
    └── infrastructure (cost tracking)

intelligence
    ├── learning-engine (routing optimization)
    ├── memory-core (memory-augmented routing)
    └── infrastructure (rate limiting)

learning-engine
    ├── memory-core (storing learning data)
    └── infrastructure (metrics collection)

memory-core
    └── infrastructure (health monitoring)

infrastructure
    └── (no dependencies on other bundles — fully independent)
```

**Key Rule**: Dependencies flow DOWN. Lower bundles never import from higher bundles.
- `infrastructure` is the foundation (no deps)
- `memory-core` depends only on `infrastructure`
- `learning-engine` depends on `memory-core` + `infrastructure`
- `intelligence` depends on `learning-engine` + `memory-core` + `infrastructure`
- `orchestration` depends on `intelligence` + `memory-core` + `infrastructure`
- `platform` depends on everything (top-level consumer)

---

## 4. Hotswapping Architecture

### Plugin Registry Pattern

```python
# packages/memory-core/stores/base.py
class Store(Protocol):
    def search(self, query: str, **kwargs) -> list[Result]: ...
    def store(self, content: str, **kwargs) -> str: ...
    def delete(self, id: str) -> bool: ...
    def stats(self) -> dict: ...

# packages/memory-core/stores/registry.py
class StoreRegistry:
    def __init__(self):
        self._stores: dict[str, Store] = {}
        self._active: str = "chroma"

    def register(self, name: str, store: Store):
        self._stores[name] = store

    def switch(self, name: str):
        if name not in self._stores:
            raise ValueError(f"Store '{name}' not registered")
        self._active = name

    @property
    def active(self) -> Store:
        return self._stores[self._active]
```

### Version Compatibility

```python
# Each bundle declares its interface version
# packages/memory-core/__init__.py
__interface_version__ = "1.0.0"
__min_compatible__ = "0.9.0"

# Hotswap checks version compatibility before loading
def check_compatibility(new_version: str, current_version: str) -> bool:
    return semver.compare(new_version, current_version) >= 0
```

### State Migration

```python
# Each bundle has its own migration system
# packages/memory-core/migrations/
001_initial.py
002_add_trust_scores.py
003_migrate_to_chroma_v3.py

# Migration runner
def migrate(current_version: str, target_version: str):
    migrations = get_migrations_between(current_version, target_version)
    for migration in migrations:
        migration.apply()
        record_migration(migration.id)
```

### Rollback

```python
# Each bundle supports rollback
def rollback(bundle: str, to_version: str):
    state = load_state(bundle)
    migration = load_migration(state.version, to_version)
    migration.rollback()
    update_state(bundle, to_version)
```

---

## 5. Migration Strategy

### Phase 1: Foundation (Week 1)
1. Create `packages/` directory structure
2. Move `infrastructure/` first (no dependencies)
3. Create `pyproject.toml` for each bundle
4. Set up import aliases for backward compatibility

### Phase 2: Memory Core (Week 2)
1. Move `src/memory/` → `packages/memory-core/`
2. Consolidate duplicate files (mcp_server.py vs v2, content_extractor vs extractors)
3. Create clean public API in `__init__.py`
4. Update all imports to use `from packages.memory_core import ...`

### Phase 3: Learning Engine (Week 3)
1. Consolidate learning code from:
   - `src/tools/learning/` → `packages/learning-engine/rl/`, `meta/`
   - `src/tools/intelligence/learning.py` → `packages/learning-engine/routing/`
   - `src/infrastructure/proxy/learning_engine.py` → `packages/learning-engine/`
2. Connect AdvancedLearningEngine to unified router
3. Add model serialization/rollback

### Phase 4: Intelligence (Week 4)
1. Merge `src/intelligence/` + `src/tools/intelligence/` → `packages/intelligence/`
2. Remove duplicates
3. Create clean routing interface
4. Connect to learning-engine for optimization

### Phase 5: Orchestration (Week 5)
1. Move `src/orchestration/` → `packages/orchestration/`
2. Clean up agent framework
3. Connect to intelligence for routing
4. Connect to memory-core for sessions

### Phase 6: Platform (Week 6)
1. Move `bin/` → `packages/platform/scripts/`
2. Move `src/tui/` → `packages/platform/tui/`
3. Create unified launcher
4. Update all script paths

### Phase 7: Cleanup (Week 7)
1. Remove old `src/` directories
2. Update all imports
3. Run full test suite
4. Update documentation

---

## 6. File Movement Map

### From `src/memory/` (70 files) → `packages/memory-core/`

| Source | Destination | Notes |
|--------|-------------|-------|
| `vector_index.py`, `embeddings.py`, `embedding_service.py`, `embedding_pipeline.py`, `embedding_store.py`, `drive_embedder.py` | `stores/vector_store.py` | Consolidate into one |
| `knowledge_graph.py`, `multi_graph.py` | `stores/graph_store.py` | Merge |
| `file_registry.py`, `file_connector.py`, `file_content_connector.py`, `file_rrf.py` | `indexing/file_registry.py` | Consolidate |
| `chunker.py`, `metadata_extractor.py`, `content_extractor.py`, `content_extractors.py` | `indexing/chunker.py` | Merge extractors |
| `indexer.py`, `drive_scanner.py`, `multi_drive_scanner.py`, `scan_config.py`, `scan_scheduler.py` | `indexing/scanner.py` | Consolidate |
| `retrievers/semantic.py`, `retrievers/keyword.py`, `retrievers/fusion.py`, `semantic.py` | `retrievers/` | Keep structure, remove duplicate |
| `session_memory.py`, `session_lifecycle.py` | `sessions/` | Move as-is |
| `working.py`, `episodic.py`, `procedural.py`, `memory_types.py` | `sessions/context.py` | Consolidate |
| `adaptive_forgetting.py`, `core/forgetting.py` | `cognitive/forgetting.py` | Merge |
| `sleep_engine.py`, `core/sleep_cycle.py` | `cognitive/sleep_engine.py` | Merge |
| `memory_reconsolidation.py` | `cognitive/reconsolidation.py` | Move |
| `priority_engine.py` | `cognitive/priority.py` | Move |
| `retention_policy.py` | `cognitive/retention.py` | Move |
| `trust_aware_retrieval.py` | `cognitive/trust.py` | Move |
| `mcp_server.py`, `mcp_server_v2.py` | `mcp_server.py` | Merge into one |
| `health_monitor.py` | `health.py` | Move |
| `daemon.py` | `daemon.py` | Move |
| `config.py`, `learning_config.py` | `config.py` | Merge |
| `registry.py` | `registry.py` | Move |
| `migrations/` | `migrations/` | Keep structure |
| `memory_router.py`, `router.py` | **DELETE** | Superseded by intelligence router |
| `memory_manager.py`, `memory_files.py`, `memory_extractor.py`, `memory_age.py`, `memory_freshness.py`, `memory_relevance.py` | **CONSOLIDATE** | Merge into stores/ |
| `connectors.py`, `enhancements.py`, `synthesizer.py`, `topic_model.py`, `preference_model.py`, `observational_memory.py`, `context_awareness.py`, `event_bus_consumer.py`, `event_log.py`, `auto_recovery.py`, `activity_tracker.py`, `integrity_checker.py`, `relational_versioning.py`, `cleanup.py`, `migrator.py`, `migration_runner.py`, `mcp_file_tools.py`, `file_watcher.py` | **REVIEW** | Each file needs individual assessment |

### From `src/tools/` + `src/intelligence/` → `packages/intelligence/` + `packages/learning-engine/`

| Source | Destination | Notes |
|--------|-------------|-------|
| `src/tools/intelligence/unified_router.py` | `packages/intelligence/router/unified.py` | Move |
| `src/tools/intelligence/trigger_routing.py` | `packages/intelligence/router/trigger.py` | Move |
| `src/tools/intelligence/memory_routing.py` | `packages/intelligence/router/memory.py` | Move |
| `src/tools/intelligence/local_model_analysis.py` | `packages/intelligence/router/local_model.py` | Move |
| `src/tools/intelligence/ml_router.py` | `packages/intelligence/router/ml.py` | Move |
| `src/tools/intelligence/complexity_scorer.py`, `dynamic_scorer.py` | `packages/intelligence/scoring/` | Merge |
| `src/tools/intelligence/token_estimator.py` | `packages/intelligence/scoring/token_estimator.py` | Move |
| `src/tools/intelligence/task_decomposer.py` | `packages/intelligence/delegation/decomposer.py` | Move |
| `src/tools/intelligence/context_sharing.py` | `packages/intelligence/delegation/context_sharing.py` | Move |
| `src/tools/intelligence/agent_communication.py` | `packages/intelligence/delegation/communication.py` | Move |
| `src/tools/intelligence/dynamic_triggers.py`, `src/tools/intelligence/trigger_routing.py` | `packages/intelligence/triggers/` | Merge |
| `src/tools/middleware/delegation_interceptor.py` | `packages/intelligence/middleware/interceptor.py` | Move |
| `src/tools/intelligence/sandbox.py` | `packages/intelligence/middleware/sandbox.py` | Move |
| `src/tools/intelligence/routing_optimizer.py`, `src/tools/intelligence/learning.py` | `packages/learning-engine/routing/` | Move |
| `src/tools/intelligence/ab_testing.py` | `packages/learning-engine/routing/ab_testing.py` | Move |
| `src/tools/learning/advanced_learning.py` | `packages/learning-engine/rl/` + `meta/` | Split into components |
| `src/tools/learning/self_learning.py` | `packages/learning-engine/meta/` | Move |
| `src/tools/learning/db.py` | `packages/learning-engine/db.py` | Move |
| `src/tools/learning/event_bus.py` | `packages/learning-engine/event_bus.py` | Move |
| `src/tools/learning/skill_registry.py`, `skill_lifecycle.py` | `packages/learning-engine/delegation/` | Move |
| `src/tools/learning/prompt_evolution.py` | `packages/learning-engine/meta/` | Move |
| `src/tools/learning/signals.py` | `packages/learning-engine/signals.py` | Move |
| `src/tools/observability/` | `packages/infrastructure/monitoring/` | Move |
| `src/tools/state/` | `packages/orchestration/sessions/` | Move |
| `src/tools/tracing/` | `packages/infrastructure/monitoring/` | Move |
| `src/tools/blocks/` | **REVIEW** | GPU tools may be deprecated |
| `src/intelligence/` (all files) | **MERGE** with `src/tools/intelligence/` | Remove duplicates |

### From `src/infrastructure/` → `packages/infrastructure/`

| Source | Destination | Notes |
|--------|-------------|-------|
| `proxy/` (all files) | `packages/infrastructure/proxy/` | Move as-is |
| `network/` (all files) | `packages/infrastructure/network/` | Move as-is |
| `circuit_breaker.py` | `packages/infrastructure/resilience/circuit_breaker.py` | Move |
| `retry_handler.py` | `packages/infrastructure/resilience/retry.py` | Move |
| `rate_limiter.py` | `packages/infrastructure/resilience/rate_limiter.py` | Move |
| `error_handler.py` | `packages/infrastructure/resilience/fallback.py` | Move |
| `metrics_store.py`, `metrics_collector.py` | `packages/infrastructure/monitoring/metrics.py` | Merge |
| `telemetry.py`, `telemetry_service.py` | `packages/infrastructure/monitoring/telemetry.py` | Merge |
| `anomaly_detection.py` | `packages/infrastructure/monitoring/anomaly.py` | Move |
| `cost_tracking.py`, `cost_tracker_mcp.py`, `cost_optimizer.py` | `packages/infrastructure/cost/` | Consolidate |
| `config_manager.py`, `config_service.py` | `packages/infrastructure/config/` | Merge |
| `feature_flags.py` | `packages/infrastructure/config/feature_flags.py` | Move |
| `validation_service.py`, `verification_engine.py` | `packages/infrastructure/config/validation.py` | Merge |
| `serialization.py` | `packages/infrastructure/utils/serialization.py` | Move |
| `datetime_utils.py` | `packages/infrastructure/utils/datetime.py` | Move |
| `hash_service.py` | `packages/infrastructure/utils/hashing.py` | Move |
| `startup_optimizer.py`, `system_utils.py` | **REVIEW** | May be deprecated |
| `backup_manager.py`, `log_rotation.py`, `cloud_sync.py` | **REVIEW** | May be deprecated |
| `clipboard_handler.py`, `hotkey_engine.py`, `macro_engine.py` | **DELETE** | Not relevant to AI workspace |
| `comfyui_bridge.py`, `ir_loader.py`, `osm_bridge.py`, `fusion_bridge.py`, `metaphor_translator.py` | **DELETE** | Music/image bridges not needed |
| `news_mcp.py`, `whisper_transcription.py`, `voice_control.py` | **DELETE** | Not core functionality |
| `export_service.py`, `project_versioning.py`, `decision_tracker.py`, `diminishing_returns.py`, `performance_profiler.py`, `resource_monitor.py`, `dependency_checker.py` | **REVIEW** | Assess individually |

### From `src/orchestration/` → `packages/orchestration/`

| Source | Destination | Notes |
|--------|-------------|-------|
| `agent_card_registry.py`, `agent_coordinator.py` | `packages/orchestration/agents/` | Move |
| `workers/agent_worker.py`, `workers/pool.py` | `packages/orchestration/agents/` | Move |
| `task_lifecycle.py`, `task_router.py` | `packages/orchestration/tasks/` | Move |
| `parallel_dispatcher.py`, `parallel_executor.py` | `packages/orchestration/tasks/dispatcher.py` | Merge |
| `checkpoint_resume.py` | `packages/orchestration/tasks/checkpoint.py` | Move |
| `session_manager.py`, `session_context.py`, `session_memory.py`, `session_archiver.py` | `packages/orchestration/sessions/` | Consolidate |
| `tool_registry.py`, `tool_factory.py`, `tool_contract.py`, `tool_search.py`, `tool_errors.py` | `packages/orchestration/tools/` | Move |
| `trigger_engine.py`, `trigger_router.py` | `packages/orchestration/triggers/` | Move |
| `governance.py`, `permissions.py`, `grounding.py` | `packages/orchestration/governance/` | Move |
| `catalyst.py` | `packages/orchestration/catalyst.py` | Move |
| `a2a_agents.py`, `a2a_protocol.py` | **REVIEW** | May be deprecated |
| `agent_evaluation.py`, `ai_enhancement.py`, `athena_bridge.py`, `athena_executor.py` | **REVIEW** | Assess individually |
| `auto_capture.py`, `auto_launcher.py` | **DELETE** | Not needed |
| `collaboration.py`, `dependency_resolution.py`, `event_bus.py`, `fallback_registry.py`, `focus_manager.py`, `focus_mode.py`, `friction_detector.py`, `intent_orchestration.py`, `langgraph_workflow.py`, `module_registry.py`, `network_orchestrator.py`, `orchestrator_backpressure.js`, `pattern_learning.py`, `personality.py`, `planning_reasoning.py`, `plugin_scanner.py`, `progress.py`, `prompt_templates.py`, `queue_service.py`, `quick_actions.py`, `react_agent.py`, `reflexion_agent.py`, `reflexion_pattern.py`, `resilience_middleware.py`, `self_healer.py`, `system_registry.py`, `template_manager.py`, `thinking_effort.py`, `tool_call_collector.py`, `workspace_manager.py` | **REVIEW** | Each needs individual assessment |

### From `bin/` → `packages/platform/scripts/`

| Source | Destination | Notes |
|--------|-------------|-------|
| `health-l0-blink.sh`, `health-l1-pulse.sh`, `health-l2-vitals.sh`, `health-monitor.sh`, `health-check.sh` | `packages/platform/scripts/health/` | Move |
| `quality-gates/` (all files) | `packages/platform/scripts/quality-gates/` | Move |
| `model-router.py`, `model-selector.py`, `model-health.py`, `model-fallback.py`, `model_config.py`, `model_keywords.py` | `packages/platform/scripts/model/` | Move |
| `n-xyme-memory.sh`, `n-xyme-memory.service` | `packages/platform/scripts/memory/` | Move |
| `n-xyme-mind.sh` | `packages/platform/launcher.py` | Rewrite as Python |
| `queue-cli.py`, `trace-cli.py`, `security-cli.py`, `worker-cli.py` | `packages/platform/cli/` | Move |
| `monitoring-dashboard.py`, `dashboard.sh`, `routing-dashboard.py` | `packages/platform/dashboard/` | Move |
| `mcp-doctor.sh`, `ensure-services.sh`, `ensure-ollama.sh`, `index-drives.sh` | `packages/platform/scripts/ops/` | Move |
| `backup.sh`, `repair-paths.sh`, `trigger-status` | `packages/platform/scripts/ops/` | Move |
| `benchmark-delegation.sh`, `benchmark-models.py`, `check-results.sh`, `delegation-log.sh`, `complexity-score.sh`, `review-triage.sh`, `validate-agent-call.py`, `validate-config-driven.py`, `generate-report.py`, `mutation-test.sh`, `full-system-test.sh`, `e2e-test-helper.py`, `prompt-cache.py`, `migrate-to-sqlite.py` | **REVIEW** | Assess individually |
| `socks5-server.py`, `start-socks5-proxies.sh`, `stop-socks5-proxies.sh`, `start-router-proxy.sh`, `stop-router-proxy.sh`, `status-model-router.sh` | `packages/infrastructure/network/` | Move to infrastructure |
| `start-model-router.sh`, `stop-model-router.sh`, `status-model-router.sh`, `model-router.service` | `packages/infrastructure/proxy/` | Move to infrastructure |
| `vpn-rotate`, `wireproxy-manager.sh` | `packages/infrastructure/network/` | Move to infrastructure |
| `local-chain.py`, `local-pipeline.py`, `local-router.py` | **DELETE** | Superseded by unified router |

---

## 7. Cutting-Edge Stack Recommendations

### Memory Stack
| Component | Current | Recommended | Why |
|-----------|---------|-------------|-----|
| Vector DB | Chroma (local SQLite) | **LanceDB** | Serverless, embedded, faster than Chroma, better scaling |
| Graph DB | NetworkX (in-memory) | **NetworkX + SQLite persistence** | Keep NetworkX for simplicity, add persistence |
| Embeddings | Local model (Ollama) | **Keep Ollama** + add fallback to API | Cost-effective, privacy-first |
| Retrieval | Hybrid (semantic + keyword + RRF) | **Keep + add ColBERT reranking** | State-of-the-art reranking |
| File Indexing | Custom SQLite | **Keep** | Works well, no need to change |

### Learning Stack
| Component | Current | Recommended | Why |
|-----------|---------|-------------|-----|
| Q-Learning | Tabular | **Keep tabular** + add Deep Q-Network for complex states | Tabular works for current state space |
| Bandits | UCB | **Keep UCB** + add Thompson Sampling | Thompson better for non-stationary |
| Meta-Learning | MAML-style | **Keep** | Good for few-shot adaptation |
| EWC | Basic | **Keep** | Prevents catastrophic forgetting |
| Model Persistence | None | **Add joblib + versioning** | Critical for hotswapping |

### Infrastructure Stack
| Component | Current | Recommended | Why |
|-----------|---------|-------------|-----|
| Proxy | Custom SOCKS5 | **Keep** | Works, handles rate limiting |
| Circuit Breaker | Custom | **Keep** | Simple, effective |
| Rate Limiter | Custom | **Keep** | Token bucket works |
| Metrics | Custom SQLite | **Keep** | Lightweight, no external deps |
| Config | JSON files | **Keep + add Pydantic validation** | Simple, add type safety |

### Orchestration Stack
| Component | Current | Recommended | Why |
|-----------|---------|-------------|-----|
| Agent Framework | Custom | **Keep** | Tailored to OpenCode |
| Tool Registry | Custom | **Keep** | Works with MCP |
| Session Management | Custom | **Keep** | Integrated with memory |
| Trigger Engine | Custom | **Keep** | Fast, pattern-based |

---

## 8. Implementation Order

### Sprint 1: Foundation (Days 1-3)
- [ ] Create `packages/` directory structure
- [ ] Move `infrastructure/` (no dependencies)
- [ ] Create `pyproject.toml` for each bundle
- [ ] Set up import aliases for backward compatibility
- [ ] Run tests to verify nothing breaks

### Sprint 2: Memory Core (Days 4-7)
- [ ] Move `src/memory/` → `packages/memory-core/`
- [ ] Consolidate duplicate files
- [ ] Create clean public API
- [ ] Update all imports
- [ ] Run tests

### Sprint 3: Learning Engine (Days 8-11)
- [ ] Consolidate learning code from 3 locations
- [ ] Connect AdvancedLearningEngine to unified router
- [ ] Add model serialization/rollback
- [ ] Run tests

### Sprint 4: Intelligence (Days 12-15)
- [ ] Merge duplicate intelligence directories
- [ ] Remove duplicates
- [ ] Create clean routing interface
- [ ] Connect to learning-engine
- [ ] Run tests

### Sprint 5: Orchestration (Days 16-19)
- [ ] Move `src/orchestration/` → `packages/orchestration/`
- [ ] Clean up agent framework
- [ ] Connect to intelligence + memory-core
- [ ] Run tests

### Sprint 6: Platform (Days 20-22)
- [ ] Move `bin/` → `packages/platform/scripts/`
- [ ] Move `src/tui/` → `packages/platform/tui/`
- [ ] Create unified launcher
- [ ] Update all script paths
- [ ] Run tests

### Sprint 7: Cleanup (Days 23-25)
- [ ] Remove old `src/` directories
- [ ] Update all imports
- [ ] Run full test suite
- [ ] Update documentation
- [ ] Final verification

---

## 9. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Import breaks during migration | Use import aliases in `src/` that point to `packages/` |
| Data loss during migration | Backup all `.db` files before moving |
| Learning model degradation | Keep old model as fallback, A/B test new model |
| Script path breaks | Update all paths in one atomic commit |
| Circular dependencies | Enforce dependency graph, use linting to detect cycles |
| Performance regression | Benchmark before/after each sprint |

---

## 10. Success Criteria

- [ ] All code moved to `packages/` structure
- [ ] Zero import errors
- [ ] All tests pass
- [ ] Hotswapping works (can swap vector store without restart)
- [ ] Learning system records and uses outcomes
- [ ] Routing uses Q-Learning for decisions
- [ ] MCP server starts without errors
- [ ] All bin/ scripts work from new locations
- [ ] No circular dependencies
- [ ] Clean dependency graph (verified by linting)

---

*This is a living document. Update as we learn during migration.*
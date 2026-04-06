# N-Xyme_MIND Memory + Learning System Architecture

> Document Version: 1.0 | Last Updated: 2026-04-06 | Masterplan Phase: T7.3 Complete

---

## 1. System Overview

The N-Xyme_MIND memory+learning system is a hybrid architecture that combines:

- **Memory Core**: Persistent storage with semantic search, keyword matching, and RRF fusion
- **Learning Engine**: Q-Learning based routing optimization with outcome tracking
- **Cognitive Engines**: Forgetting, Trust, and Priority systems for adaptive memory management
- **Health Monitoring**: Comprehensive health checks for all system components

### Design Goals

| Goal | Implementation |
|------|---------------|
| Persistent memory | SQLite with WAL mode |
| Hybrid retrieval | TEMPR + Keyword + Vector RRF fusion |
| Self-improving routing | Q-Learning with real rewards |
| Resilience | Health checks, integrity validation |
| Configurability | Environment overrides + file-based config |

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              N-Xyme_MIND Architecture                               │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │                            External Interfaces                                │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │   OpenCode   │  │    MCP       │  │    CLI       │  │   Health    │   │  │
│  │  │     TUI      │  │   Servers    │  │   Scripts    │  │   Monitor   │   │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │  │
│  └─────────┼──────────────────┼──────────────────┼──────────────────┼───────────┘  │
│            │                  │                  │                  │              │
│  ┌─────────┴──────────────────┴──────────────────┴──────────────────┴───────────┐  │
│  │                              Memory + Learning Layer                          │  │
│  │  ┌───────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │                         AdaptiveRouter                                    │ │  │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │ │  │
│  │  │  │  Query       │  │   Memory     │  │  Outcome     │  │   Q-Learning │  │ │  │
│  │  │  │  Analysis    │──│   Router     │──│   Logger     │──│   Engine     │  │ │  │
│  │  │  └──────────────┘  └──────┬───────┘  └──────────────┘  └──────────────┘  │ │  │
│  │  │                            │                                             │ │  │
│  │  │         ┌──────────────────┼──────────────────┐                         │ │  │
│  │  │         │                  │                  │                         │ │  │
│  │  │  ┌──────┴───────┐  ┌───────┴──────┐  ┌────────┴────────┐                │ │  │
│  │  │  │  Retrieval  │  │     MMR      │  │  Cross-Encoder  │                │ │  │
│  │  │  │  Pipeline   │  │   Reranker   │  │    Reranker    │                │ │  │
│  │  │  └──────┬───────┘  └──────────────┘  └─────────────────┘                │ │  │
│  │  │         │                                                             │ │  │
│  │  └─────────┼───────────────────────────────────────────────────────────────┘ │  │
│  │            │                                                                 │  │
│  │  ┌─────────┴───────────────────────────────────────────────────────────────┐ │  │
│  │  │                          Retrievers                                      │ │  │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │ │  │
│  │  │  │   TEMPR      │  │   Keyword    │  │   Vector     │  │  Semantic  │ │ │  │
│  │  │  │  Retriever  │  │   Retriever  │  │   Store      │  │  Search    │ │ │  │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │ │  │
│  │  └───────────────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                                │  │
│  │  ┌───────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │                       Cognitive Engines                                    │ │  │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │ │  │
│  │  │  │   Forgetting │  │     Trust    │  │  Reconsolid  │  │  Priority  │ │ │  │
│  │  │  │    (Decay)   │  │   Engine     │  │    Engine    │  │   Engine   │ │ │  │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │ │  │
│  │  └───────────────────────────────────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
│  ┌────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              Storage Layer                                     │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │  │
│  │  │    SQLite    │  │   Vector     │  │   Outcomes   │  │   Routing   │      │  │
│  │  │   (Memory)   │  │   Index      │  │     DB       │  │    DB       │      │  │
│  │  │   WAL Mode   │  │   (HNSW)     │  │              │  │  (Q-Table)  │      │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘      │  │
│  └────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

Legend:
  ───   Primary data flow
  ....   Feedback/learning signal
```

---

## 3. Component Descriptions

### 3.1 MemoryManager

**Location**: `packages/memory_core/memory_manager.py`

The central coordinator for all memory operations.

| Feature | Description |
|---------|-------------|
| Thread-safe operations | Uses `threading.Lock()` for concurrent access |
| Single connection | One SQLite connection per instance |
| WAL mode enabled | Write-Ahead Logging for performance |
| Transaction support | Multi-operation sequences wrapped in transactions |

**API**:
```python
from packages.memory_core.memory_manager import MemoryManager

manager = MemoryManager(db_path="context/memory/mind_from_mind.db")
record_id = manager.add_memory(content="...", embedding=[...])
results = manager.search(query="...", top_k=10)
```

---

### 3.2 MemoryRouter

**Location**: `packages/memory_core/router.py`

Routes queries to optimal retriever based on query analysis.

| Query Type | Retriever Used |
|------------|----------------|
| Semantic (>5 words, no keywords) | TEMPRRetriever |
| Keyword (specific terms) | KeywordRetriever |
| Hybrid | Combined RRF |
| Filtered | VectorStore with filters |

**API**:
```python
from packages.memory_core.router import MemoryRouter

router = MemoryRouter()
results = router.search(query="find authentication middleware", top_k=10)
# Returns SearchResults with ranked results
```

---

### 3.3 AdaptiveRouter

**Location**: `packages/learning_engine/routing/adaptive_router.py`

Wraps MemoryRouter and adds learning capabilities.

**Flow**:
1. Receive query
2. Call MemoryRouter → get results
3. Log outcome via OutcomeLogger
4. Compute reward (success, latency, quality)
5. Update Q-Learning table

**API**:
```python
from packages.learning_engine.routing.adaptive_router import AdaptiveRouter

router = AdaptiveRouter()
results = router.route(query="...", top_k=10)
# Internally: logs outcome + updates Q-table
```

---

### 3.4 RetrievalPipeline

**Location**: `packages/memory_core/retrievers/pipeline.py`

End-to-end retrieval with multiple stages.

| Stage | Description |
|-------|-------------|
| Query Analysis | Determine query type (semantic/keyword/hybrid) |
| Retrieve | Call appropriate retriever(s) |
| RRF Fusion | Combine results with Reciprocal Rank Fusion |
| MMR Rerank | Apply diversity scoring |
| Cross-Encoder | Optional second-pass reranking |
| Return | Top-k results with scores |

---

### 3.5 OutcomeLogger

**Location**: `packages/learning_engine/outcome_logger.py`

Logs task outcomes for Q-Learning training.

**Schema**:
| Field | Type | Description |
|-------|------|-------------|
| task_id | TEXT | Unique task identifier |
| agent | TEXT | Agent that handled the task |
| success | INTEGER | 1=success, 0=failure |
| latency_ms | REAL | Task execution time |
| quality_score | REAL | 0.0-1.0 quality rating |
| timestamp | INTEGER | Unix timestamp |

**API**:
```python
from packages.learning_engine.outcome_logger import OutcomeLogger

logger = OutcomeLogger()
logger.log_outcome(
    task_id="task_001",
    agent="hephaestus",
    success=True,
    latency_ms=1500,
    quality_score=0.85
)
```

---

### 3.6 QLearningEngine

**Location**: `packages/learning_engine/q_learning.py`

Q-Learning for routing optimization.

| Parameter | Default | Description |
|-----------|---------|-------------|
| alpha | 0.1 | Learning rate |
| gamma | 0.9 | Discount factor |
| epsilon | 0.1 | Exploration rate |

**Update Rule**:
```
Q(s,a) = Q(s,a) + alpha * (reward + gamma * max(Q(s',a')) - Q(s,a))
```

**API**:
```python
from packages.learning_engine.q_learning import QLearningEngine

ql = QLearningEngine()
state = "semantic_query"
action = "tempr_retriever"
reward = 1.0

ql.update(state, action, reward)
best_action = ql.select_action(state)
stats = ql.get_all_agent_stats()
```

---

### 3.7 HealthCheck

**Location**: `packages/memory_core/health.py`

Comprehensive health monitoring.

| Check | Component | Details |
|-------|-----------|---------|
| memory_stores | RelationalStore, FileRegistry | Connectivity |
| learning_engine | OutcomeLogger, Q-Learning, EventBus | Database tables |
| mcp_servers | memory_core, learning_engine | Import status |
| database_integrity | SQLite | Integrity check, WAL mode |
| cognitive_engines | Forgetting, Trust, Priority | Engine stats |

**API**:
```python
from packages.memory_core.health import HealthCheck, quick_health

# Quick check
status = quick_health()

# Detailed check
checker = HealthCheck(timeout=5.0)
status = checker.get_overall_health()
```

---

### 3.8 Configuration System

**Memory Core Config**: `packages/memory_core/config.py`

**Learning Engine Config**: `packages/learning_engine/config.py`

Both support:
- Environment variable overrides (prefixed with `MEMORY_` or `LEARNING_`)
- JSON/YAML file config
- Hardcoded defaults

---

## 4. Configuration Reference

### 4.1 Memory Core Configuration

| Section | Parameter | Default | Description |
|---------|-----------|---------|-------------|
| **database** | | | |
| | path | context/memory/mind_from_mind.db | Database file path |
| | connection_timeout_ms | 30000 | Connection timeout |
| | busy_timeout_ms | 5000 | Busy timeout |
| | wal_mode | True | Write-Ahead Logging |
| | pool_size | 5 | Connection pool size |
| | check_same_thread | False | Thread safety |
| **retrieval** | | | |
| | rrf_k | 60 | RRF k parameter |
| | trust_weight | 0.3 | Trust rerank weight |
| | mmr_lambda | 0.5 | MMR diversity |
| | default_top_k | 10 | Default result count |
| | semantic_weight | 0.5 | Semantic query weight |
| | keyword_weight | 0.5 | Keyword query weight |
| | feedback_threshold | 100 | Weight adjustment threshold |
| **pipeline** | | | |
| | enable_query_analysis | True | Enable query analysis |
| | enable_cross_encoder | True | Enable cross-encoder |
| | enable_mmr_rerank | True | Enable MMR |
| | query_analysis_timeout_ms | 50.0 | Query analysis timeout |
| | retrieve_timeout_ms | 500.0 | Retrieval timeout |
| | rerank_timeout_ms | 200.0 | Rerank timeout |
| **cognitive** | | | |
| | decay_enabled | True | Enable forgetting |
| | decay_threshold | 0.3 | Decay threshold |
| | trust_initial | 0.5 | Initial trust value |
| | trust_verification_boost | 0.1 | Trust boost on verify |
| | trust_decay_days | 1 | Trust decay period |
| | conflict_detection_enabled | True | Enable conflict detection |
| | similarity_threshold | 0.85 | Similarity threshold |
| | priority_update_on_access | True | Update priority on access |
| **vector_store** | | | |
| | embedding_dimension | 384 | Embedding dimension |
| | index_type | hnsw | Index type |
| | m | 16 | HNSW m parameter |
| | ef_construction | 200 | HNSW ef_construction |
| | ef_search | 50 | HNSW ef_search |

### 4.2 Learning Engine Configuration

| Section | Parameter | Default | Description |
|---------|-----------|---------|-------------|
| **q_learning** | | | |
| | alpha | 0.1 | Learning rate |
| | gamma | 0.9 | Discount factor |
| | epsilon | 0.1 | Exploration rate |
| | ewc_lambda | 0.01 | EWC regularization |
| | ewc_task_interval | 10 | EWC interval |
| **bandit** | | | |
| | epsilon | 0.1 | Exploration rate |
| | ucb_c | 2.0 | UCB constant |
| | strategy | epsilon | Strategy (epsilon/ucb/thompson) |
| | min_pulls_before_selection | 0 | Min pulls for selection |
| **reward** | | | |
| | base_success | 1.0 | Success reward |
| | base_failure | -1.0 | Failure penalty |
| | latency_threshold_ms | 100.0 | Latency threshold |
| | latency_penalty_per_ms | 0.001 | Latency penalty |
| | baseline_latency_ms | 500.0 | Baseline latency |
| | quality_bonus_threshold | 0.8 | Quality bonus threshold |
| | quality_bonus_value | 0.5 | Quality bonus value |
| | exploration_bonus | 0.1 | Exploration bonus |
| | baseline_cost | 0.01 | Baseline cost |
| **routing** | | | |
| | ema_alpha | 0.1 | EMA learning rate |
| | latency_cap_ms | 10000.0 | Latency cap |
| | latency_weight | 0.3 | Latency weight |
| | min_sample_size | 3 | Min sample for recommendation |
| | min_success_rate_for_recommendation | 0.70 | Min success rate |
| **database** | | | |
| | outcomes_db_path | .sisyphus/outcomes.db | Outcomes DB |
| | routing_db_path | .sisyphus/routing_learning.db | Routing DB |
| | skills_db_path | skills.db | Skills DB |
| | prompts_db_path | prompts.db | Prompts DB |
| | self_learning_db_path | learning.db | Self-learning DB |

---

## 5. Testing Guide

### 5.1 Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Integration tests
python -m pytest tests/integration/ -v

# Unit tests
python -m pytest tests/unit/ -v

# Specific module
python -m pytest tests/unit/test_router.py -v
```

### 5.2 Health Checks

```bash
# Quick health check
python -c "from packages.memory_core.health import quick_health; import json; print(json.dumps(quick_health(), indent=2))"

# Detailed health check
python -c "
from packages.memory_core.health import HealthCheck
checker = HealthCheck()
result = checker.get_overall_health()
import json
print(json.dumps(result, indent=2))
"
```

### 5.3 Configuration Validation

```bash
# Memory core config
python -c "from packages.memory_core.config import get_config, validate_config; c = get_config(); v, e = validate_config(c); print('Valid' if v else e)"

# Learning engine config
python -c "from packages.learning_engine.config import get_config, validate_config; c = get_config(); v, e = validate_config(c); print('Valid' if v else e)"
```

---

## 6. Troubleshooting

### 6.1 Common Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Empty search results | `MemoryRouter.search()` returns empty | Check embeddings, verify retriever implementations |
| Q-Learning not learning | `get_all_agent_stats()` shows no improvement | Verify OutcomeLogger is wired to AdaptiveRouter |
| Database locked | SQLite busy timeout | Check `threading.Lock()` in MemoryManager |
| Import errors | Module not found | Run `source env.sh` or check PYTHONPATH |
| Health check timeout | Check hangs | Reduce timeout or investigate component |

### 6.2 Database Issues

```bash
# Check integrity
sqlite3 context/memory/mind_from_mind.db "PRAGMA integrity_check;"

# Check WAL mode
sqlite3 context/memory/mind_from_mind.db "PRAGMA journal_mode;"

# Backup database
cp context/memory/mind_from_mind.db context/memory/mind_from_mind.db.bak
```

### 6.3 Learning Engine Issues

```bash
# Check outcomes database
sqlite3 .sisyphus/outcomes.db "SELECT COUNT(*) FROM outcomes;"

# Check Q-table
sqlite3 .sisyphus/routing.db "SELECT * FROM q_learning LIMIT 10;"

# Reset learning (WARNING: deletes all learning)
rm .sisyphus/routing.db
```

### 6.4 Health Check Reference

| Component | Status | Meaning |
|-----------|--------|---------|
| memory_stores | healthy | All stores accessible |
| | degraded | Some stores not found |
| | unhealthy | Connection errors |
| learning_engine | healthy | 2+ components OK |
| | degraded | 1 component OK |
| | unhealthy | No components OK |
| mcp_servers | healthy | All importable |
| | degraded | 1 import error |
| | unhealthy | 2+ import errors |
| database_integrity | healthy | Integrity check = ok |
| | degraded | DB not found |
| | unhealthy | Integrity errors |
| cognitive_engines | healthy | 3+ engines OK |
| | degraded | 1-2 engines OK |
| | unhealthy | No engines OK |

---

## 7. File Locations

| Component | File |
|-----------|------|
| Memory Core Config | `packages/memory_core/config.py` |
| Learning Engine Config | `packages/learning_engine/config.py` |
| Health Check | `packages/memory_core/health.py` |
| Memory Manager | `packages/memory_core/memory_manager.py` |
| Memory Router | `packages/memory_core/router.py` |
| Adaptive Router | `packages/learning_engine/routing/adaptive_router.py` |
| Retrieval Pipeline | `packages/memory_core/retrievers/pipeline.py` |
| Outcome Logger | `packages/learning_engine/outcome_logger.py` |
| Q-Learning Engine | `packages/learning_engine/q_learning.py` |
| Masterplan | `.sisyphus/plans/masterplan-phase5-7.md` |

---

## 8. Quick Reference

### Environment Variables

```bash
# Memory Core
export MEMORY_RRF_K=60
export MEMORY_DATABASE_PATH=context/memory/mind_from_mind.db
export MEMORY_CONFIG_PATH=/path/to/config.json

# Learning Engine
export LEARNING_Q_ALPHA=0.1
export LEARNING_Q_GAMMA=0.9
export LEARNING_OUTCOMES_DB_PATH=.sisyphus/outcomes.db
export LEARNING_CONFIG_PATH=/path/to/config.json
```

### Python API Quick Start

```python
# Search memory
from packages.memory_core.router import MemoryRouter
router = MemoryRouter()
results = router.search("your query", top_k=10)

# Log outcome
from packages.learning_engine.outcome_logger import OutcomeLogger
logger = OutcomeLogger()
logger.log_outcome(task_id="...", agent="...", success=True, latency_ms=100)

# Check health
from packages.memory_core.health import quick_health
status = quick_health()

# Get config
from packages.memory_core.config import get_config
from packages.learning_engine.config import get_config
memory_config = get_config()
learning_config = get_config()
```

---

*Document generated as part of Masterplan T7.3 (Documentation)*

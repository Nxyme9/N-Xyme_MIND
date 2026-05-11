# Masterplan: Bleeding Edge Routing, Memory & Learning

> **Date:** 2026-04-08
> **Effort:** ~35 days across 8 phases
> **Priority:** Critical — highest impact work remaining
> **Status:** NOT STARTED

---

## Executive Summary

N-Xyme_MIND has a **world-class skeleton** (UnifiedDelegationRouter with 11 components, 11 agents, SQLite + Neo4j infrastructure, Q-learning + bandit frameworks) but **cardboard muscles** (keyword perceptrons, SQL LIKE search, tabular Q-tables, always-healthy health checks).

This plan upgrades every component from primitive keyword/statistical implementations to bleeding-edge 2026 capabilities: embedding-based semantic routing, graph memory traversal, contextual bandit strategy selection, multi-dimensional reward learning, cross-session transfer, Bayesian confidence calibration, and LLM-powered prompt evolution.

**All phases are incremental, independently deployable, and maintain backward compatibility with existing MCP tools.**

---

## Part 1: Current State Assessment (Brutally Honest)

### Component-by-Component Reality Check

| # | Component | File | Claims To Be | Actually Is | Quality |
|---|-----------|------|-------------|-------------|---------|
| 1 | ML Router | `intelligence/router/ml.py` | Machine learning routing | 20-keyword perceptron with additive weight updates | INTERMEDIATE |
| 2 | Memory Router | `intelligence/router/memory.py` | Memory-augmented routing | SQL substring matching + success rate bucketing | INTERMEDIATE |
| 3 | Trigger Router | `intelligence/router/trigger.py` | Pattern-based routing | Regex first-match with manual priority config | PRIMITIVE |
| 4 | Local Analyzer | `intelligence/router/local_model.py` | LLM complexity analysis | Ollama prompt with circuit breaker | ADVANCED |
| 5 | Complexity Scorer | `intelligence/router/keyword.py` | Dynamic complexity scoring | Regex keyword matching (L1=typo, L5=rewrite) | PRIMITIVE |
| 6 | Unified Router | `intelligence/router/unified.py` | Multi-strategy orchestration | Static fallback chain, no meta-learning | ADVANCED (architecture) |
| 7 | Q-Learning | `learning_engine/rl/q_learning.py` | Deep reinforcement learning | Tabular Q-table with TD updates, no neural net | INTERMEDIATE |
| 8 | Bandits | `learning_engine/rl/bandits.py` | Multi-armed bandit optimization | Epsilon-greedy + UCB + naive Thompson | INTERMEDIATE |
| 9 | MAML | `learning_engine/meta/maml.py` | Model-agnostic meta-learning | `param += reward * lr` — not real MAML | PRIMITIVE |
| 10 | EWC | `learning_engine/meta/ewc.py` | Elastic weight consolidation | Diagonal Fisher from reward variance | PRIMITIVE |
| 11 | Advanced Learning | `learning_engine/advanced_learning.py` | Multi-algorithm orchestration | Simplified proofs-of-concept, no real training | INTERMEDIATE |
| 12 | Prompt Evolution | `learning_engine/prompt_evolution.py` | Outcome-driven prompt optimization | Heuristic rule-based scorer (length, structure) | INTERMEDIATE |
| 13 | Skill Registry | `intelligence/skill_registry.py` | Dynamic skill matching | Static taxonomy with string overlap averaging | INTERMEDIATE |
| 14 | Health Monitor | `intelligence/health_monitor.py` | Predictive health modeling | Count-based with fixed thresholds, always healthy | INTERMEDIATE |
| 15 | Semantic Retriever | `memory_core/retrievers/semantic.py` | Vector similarity search | Cosine similarity on Ollama/hash embeddings | ADVANCED |
| 16 | Vector Store | `memory_core/stores/vector_store.py` | FAISS-style index | In-memory Python implementation, no actual FAISS | ADVANCED |
| 17 | Keyword Retriever | `memory_core/retrievers/keyword.py` | Learned sparse retrieval | SQLite FTS5 with BM25 | INTERMEDIATE |
| 18 | Hindsight Retriever | `memory_core/retrievers/hindsight.py` | Multi-strategy recall | External MCP wrapper, unavailable without pip package | PRIMITIVE |
| 19 | Priority Engine | `memory_core/cognitive/priority.py` | Learned priority weighting | 5-factor weighted sum with simple normalization | INTERMEDIATE |
| 20 | Context Sharing | `intelligence/delegation/context_sharing.py` | Cross-session context | SQLite queries with SQL LIKE | INTERMEDIATE |
| 21 | Task Decomposer | `intelligence/delegation/decomposer.py` | LLM-powered decomposition | Regex-based task splitting | INTERMEDIATE |
| 22 | A/B Testing | `learning_engine/routing/ab_testing.py` | Statistical significance testing | Z-test framework, never activated | INTERMEDIATE |
| 23 | Cross-Session Transfer | `learning_engine/cross_session_transfer.py` | Transfer learning | JSON-based knowledge storage | INTERMEDIATE |
| 24 | Outcome Logger | `intelligence/delegation/logger.py` | Multi-dimensional outcome tracking | SQLite logging with success/latency/tokens | INTERMEDIATE |

### Quality Distribution

| Quality Level | Count | Percentage | Examples |
|--------------|-------|------------|----------|
| **BLEEDING_EDGE** | 0 | 0% | — |
| **ADVANCED** | 4 | 17% | Local Analyzer, Semantic Retriever, Vector Store, Unified Router (architecture) |
| **INTERMEDIATE** | 14 | 58% | ML Router, Memory Router, Q-Learning, Bandits, Skill Registry, Health Monitor |
| **PRIMITIVE** | 6 | 25% | Trigger Router, Keyword Scorer, MAML, EWC, Hindsight Retriever |

### The Core Problem

**The ML Router always wins because it returns confidence 1.00 (capped) and short-circuits all other strategies at threshold 0.75.** But it's a keyword perceptron — not real ML. This means:

- Task: "redesign the entire system architecture for microservices" → Level 2 (WRONG, should be L5)
- Task: "fix typo in auth.ts" → Level 2 (correct, but for wrong reasons)
- All tasks route through the same 20-keyword feature space
- No semantic understanding, no embeddings, no graph reasoning

### What Actually Works

1. **UnifiedDelegationRouter architecture** (1280 lines) — solid orchestration with proper fallback chains
2. **Lazy initialization pattern** — components gracefully skip if unavailable
3. **11 agents defined** with roles and permissions
4. **SQLite routing.db** with historical outcomes (task, agent, success, latency, level)
5. **Langfuse integration** — configured but not actively tracing
6. **Neo4jGraphStore** — exists but never used for routing
7. **TEMPR retriever** with RRF fusion — exists but not leveraged for routing decisions
8. **Q-learning + Bandit infrastructure** — exists but never properly trains

---

## Part 2: Bleeding Edge Research (April 2026)

### What Production Systems Are Doing RIGHT NOW

#### 1. Semantic Task Routing

**Source**: Agentic Thinking — Smart Routing (Jan 2026), Zylos Research — AI Agent Model Routing (Mar 2026)

**State of the art**: Embed agent capability descriptions using `sentence-transformers/all-MiniLM-L6-v2` or OpenAI `text-embedding-3-small`. Embed incoming tasks with the same model. Route via cosine similarity with confidence threshold. Add multi-model routing: fast models for simple tasks, premium models for complex reasoning.

**Key insight**: Production systems no longer use keyword matching. They use semantic embeddings + similarity thresholds + fallback chains.

#### 2. Graph RAG for Agent Selection

**Source**: Graph Praxis — Graph RAG in 2026 (Feb 2026), Graphiti (Zep) — Temporal Knowledge Graph

**State of the art**: Knowledge graphs with nodes = agents, tasks, tools, outcomes; edges = "can_handle", "has_used", "succeeded_with". Query: "Which agents have succeeded with similar tasks in the past 7 days?" Hybrid retrieval: graph traversal (relational) + vector search (semantic). Temporal weighting: recent successes weighted higher.

**Key insight**: Flat vector similarity is being replaced by temporal knowledge graphs that answer "what worked recently" not "what worked ever."

#### 3. Contextual Bandits for Strategy Selection

**Source**: CoCoMaMa — Contextual Combinatorial Multi-Armed Bandit Router (Oct 2025), AAAI — Online Multi-LLM Selection via Contextual Bandits (2026)

**State of the art**: Treat agent selection as contextual bandit: context = task embedding, actions = available agents, reward = composite(success, latency, cost, quality). Thompson sampling for exploration-exploitation. Sliding window for non-stationary reward modeling (task distribution drifts over time).

**Key insight**: The best systems don't just learn which agent is best — they learn WHICH ROUTING STRATEGY works best for each task type.

#### 4. Multi-Dimensional Learning Signals

**Source**: Multi-Reward RLAIF Framework (Feb 2026), ICLR 2026 — Bradley-Terry Multi-Objective Reward Modeling

**State of the art**: Beyond binary success/failure. Reward signals: correctness, coherence, efficiency, verbosity, token cost, user satisfaction (implicit: revision frequency, acceptance rate). Weighted composite reward. Pareto-optimal policy learning.

**Key insight**: Single-bit learning signals are obsolete. Production systems use 5+ dimensional reward vectors.

#### 5. Cross-Session Transfer Learning

**Source**: ArXiv — Routing without Forgetting (Mar 2026), ArXiv — EWC Done Right (Mar 2026), ArXiv — Brainstacks (Apr 2026)

**State of the art**: Router parameterization: shared_encoder + task-specific heads. Elastic weight consolidation on shared encoder. Progressive networks: add new heads for new task types, don't touch old. Knowledge distillation from old router to new.

**Key insight**: Catastrophic forgetting is the #1 problem in continual routing. Systems that solve it outperform by 30%+ on long-running deployments.

#### 6. Prompt Evolution

**Source**: ArXiv — GEPA: Reflective Prompt Evolution (Feb 2026), ICLR 2026 — PRL: Prompts from Reinforcement Learning

**State of the art**: Maintain prompt variant pool. Execute tasks with different variants. Collect outcomes. LLM reflects on failures, proposes specific changes. Crossover/mutation of high-performing elements. Iterate until convergence.

**Key insight**: Static prompts are dead. Systems that evolve prompts based on outcomes outperform hand-tuned prompts by 15-25%.

#### 7. Open Source Implementations

**LangGraph**: `add_conditional_edges` for state-based routing. `tools_condition` for tool selection. Production-grade graph workflows.

**CrewAI**: Role-based agent system with built-in task delegation. A2A protocol for external agent delegation.

**AutoGen**: Group chat with speaker selection. Nested chats for delegation. Custom speaker selection logic.

---

## Part 3: 8-Phase Implementation Masterplan

### Phase 0: Foundation (Days 1-2)

**Objective**: Establish infrastructure foundation for all subsequent upgrades without modifying existing functionality.

#### Task 0.1: Dependency Installation & Environment Setup

**Files**: `requirements.txt`, `packages/learning_engine/requirements.txt`

**Required Libraries**:
```bash
.venv/bin/pip install sentence-transformers torch numpy scipy scikit-learn faiss-cpu statsmodels
```

**Library Justification**:
| Library | Purpose | Used In |
|---------|---------|---------|
| `sentence-transformers` | Task/agent embeddings | Phase 1, 4, 5, 7 |
| `torch` | Neural Q-network, MAML, EWC | Phase 3, 4 |
| `numpy` | Vector operations, bandit math | Phase 1, 3, 4, 7 |
| `scipy` | Bayesian distributions (beta) | Phase 7 |
| `scikit-learn` | Classifiers, metrics | Phase 1, 4 |
| `faiss-cpu` | Approximate nearest neighbors | Phase 1, 2 |
| `statsmodels` | Statistical significance for A/B | Phase 8 |

**Success Criteria**: All imports work without version conflicts; existing test suite passes.

**Effort**: < 4 hours
**Risk**: Low
**Dependencies**: None

---

#### Task 0.2: Database Schema Extensions

**Files**: `.sisyphus/routing.db`

**New Tables**:
```sql
-- Embedding storage for tasks
CREATE TABLE IF NOT EXISTS task_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_hash TEXT UNIQUE NOT NULL,
    embedding_blob BLOB NOT NULL,
    model_version TEXT DEFAULT 'all-MiniLM-L6-v2',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Strategy selection tracking (for meta-learning)
CREATE TABLE IF NOT EXISTS strategy_selections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_hash TEXT NOT NULL,
    strategy TEXT NOT NULL,
    confidence REAL NOT NULL,
    outcome TEXT,
    latency_ms REAL,
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cross-session model weights (for transfer learning)
CREATE TABLE IF NOT EXISTS cross_session_model (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_type TEXT NOT NULL,
    weight_blob BLOB NOT NULL,
    session_id TEXT NOT NULL,
    task_types TEXT,
    performance_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Prompt version tracking (for prompt evolution)
CREATE TABLE IF NOT EXISTS prompt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_name TEXT NOT NULL,
    version INTEGER NOT NULL,
    prompt_text TEXT NOT NULL,
    score REAL DEFAULT 0.0,
    outcome_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(prompt_name, version)
);
```

**Success Criteria**: Schema migrations apply without data loss; all existing queries still work.

**Effort**: < 2 hours
**Risk**: Low
**Dependencies**: Task 0.1

---

#### Task 0.3: Embedding Model Selection & Caching

**Files**: `packages/learning_engine/embeddings/model_cache.py` (new)

**Model**: `sentence-transformers/all-MiniLM-L6-v2` (384-dim, fast, good quality)

**Implementation**: Thread-safe embedding cache with LRU eviction (max 10,000 entries), batch encoding support, MD5 hash-based caching.

**Success Criteria**: Embedding generation < 50ms for typical queries; cache hit rate > 80%.

**Effort**: 2-4 hours
**Risk**: Low
**Dependencies**: Task 0.1

---

#### Task 0.4: Configuration Schema Validation

**Files**: `packages/learning_engine/config.py`

**New Config Keys**:
- `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `EMBEDDING_CACHE_SIZE`
- `META_LEARNING_ENABLED`, `META_STRATEGY_POOL`, `META_ADAPTATION_SHOTS`
- `REWARD_WEIGHTS` (success: 0.4, quality: 0.2, latency: 0.15, cost: 0.15, satisfaction: 0.1)
- `BAYESIAN_PRIOR_ALPHA`, `BAYESIAN_PRIOR_BETA`, `EXPLORATION_THRESHOLD`

**Success Criteria**: All existing configs load without errors; new configs validate properly.

**Effort**: < 2 hours
**Risk**: Low
**Dependencies**: Task 0.1

---

### Phase 0 Summary

| Task | Effort | Risk | Parallel? |
|------|--------|------|-----------|
| 0.1 Dependencies | Quick (< 4h) | Low | Yes |
| 0.2 DB Schema | Quick (< 2h) | Low | Yes |
| 0.3 Embedding Cache | Short (2-4h) | Low | Yes |
| 0.4 Config Validation | Quick (< 2h) | Low | Yes |

**Phase 0 Deliverable**: All foundation dependencies installed; database schemas ready; embedding model cached and tested; configuration validated.

**Total Phase 0 Effort**: 1-2 days (all tasks parallelizable)

---

### Phase 1: Semantic Understanding (Days 3-7)

**Objective**: Replace keyword-based ML router with embedding-based semantic understanding.

#### Task 1.1: Embedding-Based Task Classifier

**Files**: `packages/intelligence/router/semantic_classifier.py` (new)

**Implementation**: Replace 20-keyword feature extraction with semantic embeddings. Use SGDClassifier (scikit-learn) on top of 384-dim embeddings. Supports online learning via `partial_fit`.

**Fallback**: When untrained, use embedding similarity to known task patterns.

**Success Criteria**: Classification accuracy > 85% on held-out tasks; latency < 100ms.

**Effort**: 1-2 days
**Risk**: Medium
**Dependencies**: Phase 0

---

#### Task 1.2: Vector-Enhanced Q-Learning State Representation

**Files**: `packages/learning_engine/rl/q_learning.py` (modify QState class)

**Changes**:
- Replace string-hash state with embedding-based similarity clustering
- Use FAISS for approximate nearest neighbor state lookups
- States that are semantically similar share Q-values (generalization)

**Success Criteria**: Similar tasks cluster correctly; state retrieval accuracy > 80%.

**Effort**: 1-2 days
**Risk**: Medium
**Dependencies**: Phase 0, Task 1.1

---

#### Task 1.3: Hybrid Routing Decision

**Files**: `packages/intelligence/router/unified.py` (modify Strategy 2)

**Changes**: Replace keyword perceptron with semantic classifier. Update pipeline:

```
Old: trigger → keyword_perceptron → memory → keyword_fallback
New: trigger → semantic_classifier → embedding_memory → q_learning → keyword_fallback
```

**Critical**: Semantic classifier becomes PRIMARY when confidence > 0.75 (same threshold, but now real).

**Success Criteria**: Routing accuracy improves by > 15%; backward compatibility maintained.

**Effort**: 1-2 days
**Risk**: HIGH (critical path for all routing)
**Dependencies**: Tasks 1.1, 1.2

**ORACLE REVIEW REQUIRED**: This is the highest-risk single change. Must be reviewed before merging.

---

#### Task 1.4: Embedding-Based Memory Router

**Files**: `packages/memory_core/router.py` (modify `_classify_query`)

**Changes**: Replace keyword classification with embedding-based query classification. Use cosine similarity on task embeddings instead of keyword overlap.

**Success Criteria**: Query classification accuracy > 90%; semantic search recall > 85%.

**Effort**: 1 day
**Risk**: Medium
**Dependencies**: Phase 0

---

### Phase 1 Summary

| Task | Effort | Risk | Dependencies |
|------|--------|------|--------------|
| 1.1 Semantic Classifier | Medium (1-2d) | Medium | Phase 0 |
| 1.2 Vector Q-States | Medium (1-2d) | Medium | 1.1 |
| 1.3 Hybrid Routing | Medium (1-2d) | HIGH | 1.1, 1.2 |
| 1.4 Embedding Memory | Short (1d) | Medium | Phase 0 |

**Quick Win**: Task 1.1 creates new components without modifying existing logic.

**Phase 1 Deliverable**: ML Router upgraded from 20-keyword perceptron to embedding-based semantic classifier; Q-learning states use vector similarity; memory router uses semantic search.

**Total Phase 1 Effort**: 4-7 days

---

### Phase 2: Graph Memory (Days 8-12)

**Objective**: Replace SQL-based memory routing with graph traversal and temporal pattern analysis.

#### Task 2.1: Graph Store Integration

**Files**: `packages/memory_core/stores/graph_store.py`

**Changes**: Connect to existing `Neo4jGraphStore` (already exists but unused). Implement node types: Task, Agent, Outcome, Session, Tool, Skill. Edge types: performed_by, resulted_in, belonged_to, used_tool, required_skill, has_skill, similar_to.

**Success Criteria**: Graph connection established; basic CRUD operations work.

**Effort**: 1 day
**Risk**: Low (leverages existing Neo4j infrastructure)
**Dependencies**: Phase 0

---

#### Task 2.2: Graph-Based Context Retrieval

**Files**: `packages/memory_core/router.py` (new method: `_graph_retrieve`)

**Implementation**: Graph traversal queries for routing decisions. Example: "Which agents have succeeded with similar tasks in the past 7 days?"

**Success Criteria**: Context retrieval accuracy > 80%; latency < 200ms.

**Effort**: 2 days
**Risk**: Medium
**Dependencies**: Task 2.1

---

#### Task 2.3: Temporal Pattern Mining

**Files**: `packages/learning_engine/cross_session_transfer.py` (enhance)

**Changes**: Add temporal pattern extraction from graph. Identify recurring task sequences. Apply time-decay weighting: recent successes weighted higher.

**Success Criteria**: Patterns identified with > 70% precision; patterns stored in graph.

**Effort**: 1-2 days
**Risk**: Medium
**Dependencies**: Task 2.2

---

#### Task 2.4: Graph-Enhanced Memory Router

**Files**: `packages/memory_core/router.py` (modify `search` method)

**Changes**: Replace SQL LIKE queries with graph traversals. Hybrid retrieval: graph + vector + keyword fallback. Use existing RRF to combine results.

**Success Criteria**: Search precision > 85%; recall improvement > 20% over SQL baseline.

**Effort**: 2 days
**Risk**: HIGH (critical for memory system)
**Dependencies**: Tasks 2.1, 2.2, 2.3

**ORACLE REVIEW REQUIRED**: Modifies critical memory system path.

---

### Phase 2 Summary

| Task | Effort | Risk | Dependencies |
|------|--------|------|--------------|
| 2.1 Graph Store | Short (1d) | Low | Phase 0 |
| 2.2 Graph Retrieval | Medium (2d) | Medium | 2.1 |
| 2.3 Temporal Mining | Medium (1-2d) | Medium | 2.2 |
| 2.4 Graph Memory Router | Medium (2d) | HIGH | 2.1, 2.2, 2.3 |

**Quick Win**: Task 2.1 leverages existing Neo4j infrastructure.

**Phase 2 Deliverable**: Memory Router upgraded from SQL LIKE to graph traversal with temporal pattern mining; hybrid retrieval combines vector, graph, and keyword search.

**Total Phase 2 Effort**: 5-7 days

---

### Phase 3: Meta-Learning (Days 13-19)

**Objective**: Enable strategy selection learning using contextual bandits and meta-learning approaches.

#### Task 3.1: Contextual Bandit Strategy Selector

**Files**: `packages/learning_engine/meta/strategy_selector.py` (new)

**Implementation**: Context = task embedding (384-dim). Actions = [embedding_routing, graph_routing, bandit_routing, heuristic_routing]. Reward = composite(success, latency, cost, quality). Algorithm = Neural Thompson Sampling.

**Success Criteria**: Strategy selection accuracy > 75%; adaptation within 5 tasks.

**Effort**: 2-3 days
**Risk**: HIGH (complex ML component)
**Dependencies**: Phase 1, Phase 2

**ORACLE REVIEW REQUIRED**: First use of neural bandits in production routing.

---

#### Task 3.2: Real MAML with PyTorch

**Files**: `packages/learning_engine/meta/maml.py` (complete rewrite)

**Changes**: Replace fake `param += reward * lr` with actual MAML: shared encoder + task-specific heads, inner loop adaptation with create_graph=True, outer loop meta-update on query tasks.

**Success Criteria**: Real gradient-based meta-learning; few-shot adaptation works.

**Effort**: 2 days
**Risk**: HIGH (MAML math correctness critical)
**Dependencies**: Task 3.1

---

#### Task 3.3: Real EWC with Empirical Fisher

**Files**: `packages/learning_engine/meta/ewc.py` (complete rewrite)

**Changes**: Replace variance-based Fisher approximation with actual empirical Fisher from gradient histories. Per-weight regularization strength based on importance.

**Success Criteria**: Forgetting reduction > 50% on replay tasks; EWC penalty applied correctly.

**Effort**: 2 days
**Risk**: HIGH (EWC math correctness critical)
**Dependencies**: Task 3.2

---

#### Task 3.4: Meta-Learning Health Monitor

**Files**: `packages/learning_engine/meta/health_monitor.py` (new)

**Changes**: Track meta-learning convergence. Detect when adaptation is needed. Alert on training instability.

**Success Criteria**: Health alerts trigger appropriately; false positive rate < 10%.

**Effort**: 1 day
**Risk**: Medium
**Dependencies**: Tasks 3.1, 3.2, 3.3

---

### Phase 3 Summary

| Task | Effort | Risk | Dependencies |
|------|--------|------|--------------|
| 3.1 Contextual Bandit | Large (2-3d) | HIGH | Phase 1, 2 |
| 3.2 Real MAML | Medium (2d) | HIGH | 3.1 |
| 3.3 Real EWC | Medium (2d) | HIGH | 3.2 |
| 3.4 Meta Health | Short (1d) | Medium | 3.1, 3.2, 3.3 |

**ALL Phase 3 tasks require Oracle review** due to complexity and system-wide impact.

**Phase 3 Deliverable**: Strategy selection learned via contextual bandits; real MAML for fast adaptation; real EWC prevents catastrophic forgetting; meta-learning health monitoring.

**Total Phase 3 Effort**: 7-8 days

---

### Phase 4: Multi-Dimensional Learning (Days 20-24)

**Objective**: Expand from single success/failure signals to multi-dimensional reward signals.

#### Task 4.1: Quality Signal Integration

**Files**: `packages/learning_engine/signals.py` (enhance), `packages/learning_engine/rl/rewards.py`

**Changes**: Add quality scoring from outcome analysis. Integrate with Langfuse instrumentation. Add token count and output quality correlation.

**Success Criteria**: Quality signals captured for > 90% of delegations.

**Effort**: 1-2 days
**Risk**: Medium
**Dependencies**: Phase 1

---

#### Task 4.2: Cost-Aware Routing

**Files**: `packages/intelligence/router/unified.py` (enhance routing decision)

**Changes**: Add cost tracking per agent/model. Implement cost-aware reward shaping. Add budget constraints to routing decisions.

**Success Criteria**: Cost reduction > 15% while maintaining quality.

**Effort**: 1-2 days
**Risk**: Medium
**Dependencies**: Task 4.1

---

#### Task 4.3: Satisfaction Signal Collection

**Files**: `packages/learning_engine/session_hooks.py` (enhance)

**Changes**: Add implicit feedback collection (revision frequency, acceptance rate). Implement explicit feedback prompts. Add satisfaction score prediction.

**Success Criteria**: Satisfaction signals captured; prediction accuracy > 70%.

**Effort**: 1-2 days
**Risk**: Low
**Dependencies**: Task 4.1

---

#### Task 4.4: Composite Reward Integration

**Files**: `packages/learning_engine/rl/rewards.py` (enhance existing CompositeReward)

**Changes**: Combine: base (success), latency, cost, quality, satisfaction. Add reward normalization. Implement multi-objective optimization.

**Success Criteria**: Multi-dimensional rewards computed correctly; optimization improves overall metrics.

**Effort**: 1-2 days
**Risk**: Medium
**Dependencies**: Tasks 4.1, 4.2, 4.3

---

### Phase 4 Summary

| Task | Effort | Risk | Dependencies |
|------|--------|------|--------------|
| 4.1 Quality Signals | Medium (1-2d) | Medium | Phase 1 |
| 4.2 Cost-Aware | Medium (1-2d) | Medium | 4.1 |
| 4.3 Satisfaction | Short (1-2d) | Low | 4.1 |
| 4.4 Composite Reward | Medium (1-2d) | Medium | 4.1, 4.2, 4.3 |

**Quick Win**: Task 4.3 (Satisfaction Signal Collection) provides immediate value.

**Phase 4 Deliverable**: Multi-dimensional reward signals (quality, cost, satisfaction) integrated; composite rewards drive routing optimization.

**Total Phase 4 Effort**: 4-8 days

---

### Phase 5: Cross-Session Transfer (Days 25-29)

**Objective**: Enable transfer learning across sessions to retain and generalize knowledge.

#### Task 5.1: Cross-Session Knowledge Graph

**Files**: `packages/learning_engine/cross_session_transfer.py` (enhance significantly)

**Changes**: Convert to graph-based storage instead of JSON. Add knowledge types: decision, lesson, pattern, principle, anti-pattern. Implement semantic clustering of transferable knowledge.

**Success Criteria**: Knowledge graph populated with > 100 nodes per session; cross-session links established.

**Effort**: 2 days
**Risk**: Medium
**Dependencies**: Phase 2

---

#### Task 5.2: Transferability Scorer Enhancement

**Files**: `packages/learning_engine/cross_session_transfer.py` (enhance `_transferability_score`)

**Changes**: Add semantic generalizability scoring using embeddings. Implement outcome-based confidence weighting. Add repetition-based strengthening.

**Success Criteria**: Transferability scoring accuracy > 75%.

**Effort**: 1 day
**Risk**: Low
**Dependencies**: Task 5.1, Phase 1

---

#### Task 5.3: Session-Level Transfer Activation

**Files**: `packages/learning_engine/delegation/learner.py` (new method: `activate_session_transfer`)

**Changes**: Load relevant transferable knowledge at session start. Inject into routing context. Track knowledge utilization.

**Success Criteria**: Knowledge activated appropriately; routing decisions improved by > 10%.

**Effort**: 1-2 days
**Risk**: Medium
**Dependencies**: Tasks 5.1, 5.2

---

#### Task 5.4: Transfer Learning Model Updates

**Files**: `packages/learning_engine/advanced_learning.py` (enhance MetaLearningEngine)

**Changes**: Add cross-session weight transfer. Implement session-to-session gradient approximation. Add transfer failure detection and recovery.

**Success Criteria**: Transfer improves early-session performance; failures detected and handled.

**Effort**: 1-2 days
**Risk**: HIGH
**Dependencies**: Task 5.3, Phase 3

---

### Phase 5 Summary

| Task | Effort | Risk | Dependencies |
|------|--------|------|--------------|
| 5.1 Knowledge Graph | Medium (2d) | Medium | Phase 2 |
| 5.2 Transferability | Short (1d) | Low | 5.1, Phase 1 |
| 5.3 Session Transfer | Medium (1-2d) | Medium | 5.1, 5.2 |
| 5.4 Model Updates | Medium (1-2d) | HIGH | 5.3, Phase 3 |

**Phase 5 Deliverable**: Cross-session knowledge transfer active; session start includes relevant historical learnings; transfer learning model improves early-session performance.

**Total Phase 5 Effort**: 5-7 days

---

### Phase 6: Prompt Evolution (Days 30-32)

**Objective**: Evolve prompt templates based on actual outcomes rather than static templates.

#### Task 6.1: Outcome-Linked Prompt Scoring

**Files**: `packages/learning_engine/prompt_evolution.py` (enhance)

**Changes**: Link prompt versions to actual delegation outcomes. Implement outcome-based scoring (not just heuristic). Add token efficiency metrics.

**Success Criteria**: Prompt-outcome correlation identified; scoring reflects actual performance.

**Effort**: 1 day
**Risk**: Medium
**Dependencies**: Phase 4

---

#### Task 6.2: LLM-Powered Prompt Refinement

**Files**: `packages/learning_engine/prompt_evolution.py` (enhance `_default_refiner`, add LLM refiner)

**Changes**: Add optional LLM-based refinement using existing models. Implement critic that identifies semantic issues. Add constraint satisfaction for prompt requirements.

**Success Criteria**: LLM refinement produces better prompts than rule-based; latency < 5s per refinement.

**Effort**: 1 day
**Risk**: HIGH (LLM costs and consistency)
**Dependencies**: Task 6.1

**ORACLE REVIEW REQUIRED**: LLM-powered refinement has cost and consistency concerns.

---

#### Task 6.3: Prompt Version Selection

**Files**: `packages/learning_engine/routing/adaptive_router.py` (add prompt_version selection)

**Changes**: Select optimal prompt version per task type. Implement A/B testing for prompt versions. Add prompt performance tracking.

**Success Criteria**: Prompt selection improves delegation success by > 10%.

**Effort**: 1 day
**Risk**: Medium
**Dependencies**: Task 6.1, 6.2

---

#### Task 6.4: Prompt Template Registry

**Files**: `packages/learning_engine/prompt_evolution.py` (add registry)

**Changes**: Register all prompt templates used in system. Track version history. Implement template deprecation logic.

**Success Criteria**: All prompts tracked; versions accessible; deprecation works.

**Effort**: 0.5 day
**Risk**: Low
**Dependencies**: Tasks 6.1, 6.2, 6.3

---

### Phase 6 Summary

| Task | Effort | Risk | Dependencies |
|------|--------|------|--------------|
| 6.1 Outcome Scoring | Short (1d) | Medium | Phase 4 |
| 6.2 LLM Refinement | Medium (1d) | HIGH | 6.1 |
| 6.3 Version Selection | Short (1d) | Medium | 6.1, 6.2 |
| 6.4 Template Registry | Quick (0.5d) | Low | 6.1, 6.2, 6.3 |

**Phase 6 Deliverable**: Prompt templates evolve based on outcomes; A/B testing identifies best versions; registry tracks all templates.

**Total Phase 6 Effort**: 3-4 days

---

### Phase 7: Bayesian Confidence (Days 33-35)

**Objective**: Add proper uncertainty quantification using Bayesian methods for confidence scoring.

#### Task 7.1: Bayesian Confidence Estimator

**Files**: `packages/learning_engine/routing/confidence.py` (new)

**Implementation**: Beta distribution for success rate estimation. Thompson sampling for exploration. Credible intervals for confidence.

**Success Criteria**: Confidence intervals contain true success rate > 80% of time.

**Effort**: 1-2 days
**Risk**: Medium
**Dependencies**: Phase 1, Phase 4

---

#### Task 7.2: Uncertainty-Aware Routing

**Files**: `packages/learning_engine/routing/adaptive_router.py` (enhance)

**Changes**: Use confidence intervals to guide exploration. Add uncertainty threshold for fallback. Implement meta-learning uncertainty estimation.

**Success Criteria**: Routing avoids low-confidence decisions; exploration when uncertainty high.

**Effort**: 1 day
**Risk**: Medium
**Dependencies**: Task 7.1, Phase 3

---

#### Task 7.3: Confidence Visualization

**Files**: `packages/platform_layer/dashboard/routing-dashboard.py` (enhance)

**Changes**: Add confidence metrics display. Show uncertainty intervals on charts. Display exploration vs. exploitation metrics.

**Success Criteria**: Dashboard shows confidence data; intervals visualized correctly.

**Effort**: 1 day
**Risk**: Low
**Dependencies**: Tasks 7.1, 7.2

---

### Phase 7 Summary

| Task | Effort | Risk | Dependencies |
|------|--------|------|--------------|
| 7.1 Bayesian Estimator | Medium (1-2d) | Medium | Phase 1, 4 |
| 7.2 Uncertainty Routing | Short (1d) | Medium | 7.1, Phase 3 |
| 7.3 Visualization | Short (1d) | Low | 7.1, 7.2 |

**Phase 7 Deliverable**: Bayesian confidence scoring active; uncertainty guides exploration; dashboard displays confidence metrics.

**Total Phase 7 Effort**: 3-4 days

---

### Phase 8: Integration & Testing (Days 36-40)

**Objective**: End-to-end validation of all upgraded components; performance testing; rollback procedures.

#### Task 8.1: Component Integration Testing

**Files**: `tests/integration/test_upgraded_routing.py` (new)

**Changes**: Test all component interfaces. Verify backward compatibility. Test fallback chains.

**Success Criteria**: All integration tests pass; no regressions.

**Effort**: 2 days
**Risk**: HIGH (critical for production)
**Dependencies**: All previous phases

---

#### Task 8.2: Performance Benchmarking

**Files**: `tests/benchmark/test_routing_performance.py` (new)

**Changes**: Benchmark embedding generation latency. Benchmark graph traversal latency. Benchmark end-to-end routing latency.

**Success Criteria**: P95 latency < 200ms; P99 < 500ms; throughput > 100 req/s.

**Effort**: 1 day
**Risk**: Low
**Dependencies**: Task 8.1

---

#### Task 8.3: A/B Testing Activation

**Files**: `packages/learning_engine/routing/ab_testing.py` (enhance to actually activate)

**Changes**: Create tests for: embedding vs. keyword routing, graph vs. SQL retrieval, meta-learning vs. static. Implement traffic splitting. Add statistical significance monitoring.

**Success Criteria**: A/B tests run in production; winners determined statistically.

**Effort**: 1-2 days
**Risk**: Medium
**Dependencies**: Task 8.1

---

#### Task 8.4: Health Monitor Real Checks

**Files**: `packages/memory_core/health_monitor.py` (enhance)

**Changes**: Replace "always healthy" with real checks. Add component-specific health indicators. Implement graceful degradation.

**Success Criteria**: Health score reflects actual system state; alerts trigger correctly.

**Effort**: 1 day
**Risk**: Medium
**Dependencies**: All phases

---

#### Task 8.5: Rollback & Recovery Procedures

**Files**: `docs/routing-upgrade-rollback.md` (new)

**Changes**: Document rollback steps for each phase. Add health check for downgrade. Create recovery scripts.

**Success Criteria**: Rollback documented and tested.

**Effort**: 1 day
**Risk**: Low
**Dependencies**: All phases

---

### Phase 8 Summary

| Task | Effort | Risk | Dependencies |
|------|--------|------|--------------|
| 8.1 Integration Tests | Medium (2d) | HIGH | All |
| 8.2 Performance | Short (1d) | Low | 8.1 |
| 8.3 A/B Testing | Medium (1-2d) | Medium | 8.1 |
| 8.4 Real Health | Short (1d) | Medium | All |
| 8.5 Rollback | Short (1d) | Low | All |

**Phase 8 Deliverable**: All components integrated and tested; performance meets SLA; A/B testing active; rollback procedures documented.

**Total Phase 8 Effort**: 5-6 days

---

## Part 4: Implementation Strategy

### Parallelization Strategy

**PARALLEL (can run simultaneously)**:
- Phase 0 all tasks (independent setup)
- Phase 1.1 + Phase 1.4 (new components, no conflicts)
- Phase 4.1 + Phase 4.2 + Phase 4.3 (independent signal collection)

**SEQUENTIAL (must run in order)**:
- Phase 1 → Phase 2 (embeddings needed for graph)
- Phase 2 → Phase 3 (graph patterns needed for meta-learning)
- Phase 1 + 3 → Phase 4 (embedding + meta needed for multi-dimensional)
- Phase 4 → Phase 5 (quality signals needed for transfer)
- Phase 4 + 5 → Phase 6 (outcomes + transfer needed for prompt evolution)
- Phase 1 + 4 → Phase 7 (embedding + quality needed for confidence)
- All → Phase 8 (integration requires all components)

### Quick Wins Summary (< 1 day each, highest ROI first)

1. **Task 0.3**: Embedding model caching — foundation for all subsequent embedding work
2. **Task 1.1**: Embedding-based classifier — new component, doesn't break existing
3. **Task 2.1**: Graph store integration — leverages existing Neo4j infrastructure
4. **Task 4.3**: Satisfaction signal collection — adds new signal with minimal risk
5. **Task 5.2**: Transferability scorer enhancement — improves existing system immediately
6. **Task 6.4**: Prompt template registry — metadata tracking without complex logic

### High-Risk Items Requiring Oracle Review

1. **Task 1.3**: Hybrid routing decision (Phase 1) — Critical path for all routing
2. **Task 2.4**: Graph-enhanced memory router (Phase 2) — Critical for memory system
3. **Task 3.1**: Contextual bandit strategy selector (Phase 3) — First neural bandits
4. **Task 3.2**: Real MAML with PyTorch (Phase 3) — Complex ML component
5. **Task 3.3**: Real EWC with empirical Fisher (Phase 3) — Math correctness critical
6. **Task 5.4**: Transfer learning model updates (Phase 5) — Cross-session complexity
7. **Task 6.2**: LLM-powered prompt refinement (Phase 6) — Cost and consistency
8. **Task 8.1**: Component integration testing (Phase 8) — Critical for production

### Success Metrics by Phase

| Phase | Primary Metric | Target |
|-------|-----------------|--------|
| 0 | Dependencies installed | 0 errors |
| 1 | Routing accuracy | +15% |
| 2 | Memory recall | +20% |
| 3 | Strategy selection | >75% accuracy |
| 4 | Cost reduction | >15% |
| 5 | Early-session improvement | >10% |
| 6 | Prompt quality | >85% score |
| 7 | Confidence calibration | >80% coverage |
| 8 | End-to-end latency | P95 <200ms |

### Risk Assessment Summary

- **Total Phases**: 8
- **Low Risk Tasks**: 12
- **Medium Risk Tasks**: 16
- **High Risk Tasks**: 8
- **Oracle Review Required**: 8 tasks (marked above)

---

## Part 5: The Singularity Path

### What Happens When This Is Complete

1. **Semantic Understanding**: System understands tasks semantically, not by keywords
2. **Graph Memory**: Remembers what worked recently, not just what worked ever
3. **Meta-Learning**: Learns which routing strategy works best for each task type
4. **Multi-Dimensional**: Optimizes for quality, cost, speed, and satisfaction simultaneously
5. **Cross-Session**: Every session starts smarter than the last
6. **Prompt Evolution**: Prompts improve automatically based on outcomes
7. **Bayesian Confidence**: Knows when it doesn't know — explores when uncertain

### The End State

A self-improving routing system that:
- Routes tasks to the right agent with >85% accuracy
- Learns from every delegation outcome
- Prevents catastrophic forgetting across sessions
- Evolves its own prompts based on performance
- Quantifies uncertainty and explores when unsure
- Optimizes for multiple objectives simultaneously

**This is the path from "keyword perceptron" to "self-improving intelligence."**

---

## Version

- **Masterplan**: v1.0
- **Created**: 2026-04-08
- **Based on**: 3-agent synthesis (explore + librarian + oracle)
- **Research**: 7+ papers, 5+ production frameworks, 2026 state-of-the-art
- **Effort**: ~35 days across 8 phases
- **Risk**: 8 high-risk items requiring Oracle review


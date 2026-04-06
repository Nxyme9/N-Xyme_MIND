# N-Xyme MIND Memory + Learning System Consolidation Masterplan

**Version**: 1.0  
**Date**: 2026-04-06  
**Author**: Oracle (Architecture Expert)  
**Status**: Draft - Pending Implementation

---

## Executive Summary

This masterplan consolidates the N-Xyme MIND memory and learning systems into a unified, type-safe architecture. The current codebase suffers from broken imports, disconnected components, and missing typed interfaces between the cognitive layer, memory stores, and learning engine.

**Key Problems Identified:**
- 6 broken imports in MCP server (`mcp_server.py`)
- 9 broken imports in daemon (`daemon.py`)
- Graph store `add_edge()` doesn't persist to database
- Keyword retriever has `db_path` bug (line 18 overwrites parameter)
- Duplicate code in `fusion.py` (lines 67-68)
- Zero test coverage
- Cognitive layer (forgetting, reconsolidation, trust) implemented but not auto-triggered
- Learning engine components not connected to memory system
- No typed interfaces between components

**Target State:**
- Unified typed interfaces for all stores and retrievers
- Cognitive layer auto-triggered on memory writes
- Learning engine weights integrated into RRF fusion
- Cross-session transfer wired into session lifecycle
- 80%+ test coverage with quality gates

**Estimated Total Effort**: 3-4 weeks (Medium-Large)

---

## Phase-by-Phase Breakdown

### PHASE 0: CRITICAL FIXES (Week 1, Days 1-3)

**Objective**: Fix all blocking issues before any integration work.

| Task | Description | Agent | Effort | Dependencies |
|------|-------------|-------|--------|--------------|
| 0.1 | Fix MCP server broken imports (6 issues) | Hephaestus | Short | None |
| 0.2 | Fix daemon broken imports (9 issues) | Hephaestus | Short | None |
| 0.3 | Fix graph store add_edge() persistence bug | Hephaestus | Quick | None |
| 0.4 | Fix keyword retriever db_path bug (line 18) | Hephaestus | Quick | None |
| 0.5 | Remove duplicate code in fusion.py (lines 67-68) | Sisyphus-Junior | Quick | None |

#### Task Details

**0.1 MCP Server Fixes** (`packages/memory_core/mcp_server.py`):
- Import `packages.learning_engine` → Should be `packages.learning_engine` (check PYTHONPATH)
- Import `packages.learning_engine.event_bus` → Same
- Import `src.tools.middleware.delegation_interceptor` → Remove or stub
- Import `.priority_engine`, `.preference_model`, `.router` → These need to exist or be stubbed

**0.2 Daemon Fixes** (`packages/memory_core/daemon.py`):
- `.file_watcher`, `.scan_scheduler` → Create stubs or remove references
- `.priority_engine`, `.knowledge_graph`, `.enhancements` → Create stubs or remove
- `packages.infrastructure.cost.tracker` → Remove or stub
- `src.health.health_schema`, `src.health.health_composite`, `src.health.auto_recovery` → Remove or stub
- `.router` → Create stub or fix import

**0.3 Graph Store Fix** (`packages/memory_core/stores/graph_store.py`):
- The `KnowledgeGraph.add_edge()` method calls `_save()` but the `MultiGraphMemory.add_edge()` doesn't persist to SQLite
- Fix: Add `self._save_to_db(edge)` in `MultiGraphMemory.add_edge()`

**0.4 Keyword Retriever Fix** (`packages/memory_core/retrievers/keyword.py`, line 18):
```python
# BUG: Line 18 overwrites the parameter
self.db_path = db_path  # This should be: self.db_path = db_path or str(...)
# Fix: Remove line 18, line 17 already sets the default
```

**0.5 Fusion.py Deduplication** (`packages/memory_core/retrievers/fusion.py`, lines 67-68):
```python
# DUPLICATE CODE:
self._semantic_retriever = None  # Line 67 (duplicate of line 65)
self._keyword_retriever = None   # Line 68 (duplicate of line 66)
# Fix: Remove lines 67-68
```

#### Success Criteria for PHASE 0
- [ ] `lsp_diagnostics` shows zero import errors in `mcp_server.py` and `daemon.py`
- [ ] Graph store add_edge() persists edges to SQLite
- [ ] Keyword retriever uses correct db_path
- [ ] Fusion.py has no duplicate assignments

---

### PHASE 1: CORE INTEGRATION (Week 1-2, Days 4-14)

**Objective**: Create typed interfaces and integrate stores with retrievers.

| Task | Description | Agent | Effort | Dependencies |
|------|-------------|-------|--------|--------------|
| 1.1 | Create typed interfaces (VectorStore, RelationalStore, GraphStore, Retriever) | Oracle→Hephaestus | Medium | 0.* |
| 1.2 | Add migrations system to relational store | Hephaestus | Short | 1.1 |
| 1.3 | Implement hybrid search at store level | Hephaestus | Medium | 1.1, 1.2 |
| 1.4 | Integrate trust into retrieval pipeline | Hephaestus | Medium | 0.*, 1.1 |

#### 1.1 Typed Interface Definitions

```python
# packages/memory_core/stores/interfaces.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum

class MemoryTier(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    REASONING = "reasoning"

class MemoryScope(str, Enum):
    SESSION = "session"
    PROJECT = "project"
    GLOBAL = "global"

@dataclass
class MemoryRecord:
    id: str
    content: str
    kind: str
    scope: MemoryScope
    tier: MemoryTier
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    trust_score: Optional[float] = None

@dataclass
class SearchResult:
    id: str
    content: str
    score: float
    source: str
    metadata: Dict[str, Any]
    tier: Optional[MemoryTier] = None

class VectorStore(ABC):
    """Vector-based memory storage."""
    
    @abstractmethod
    def search(self, query_embedding: List[float], top_k: int = 10) -> List[SearchResult]:
        pass
    
    @abstractmethod
    def store(self, content: str, embedding: List[float], **kwargs) -> str:
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        pass

class RelationalStore(ABC):
    """SQLite-based structured memory."""
    
    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        pass
    
    @abstractmethod
    def store(self, content: str, **kwargs) -> str:
        pass
    
    @abstractmethod
    def get(self, id: str) -> Optional[MemoryRecord]:
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        pass
    
    @abstractmethod
    def migrate(self, from_version: int, to_version: int) -> bool:
        pass

class GraphStore(ABC):
    """Knowledge graph storage."""
    
    @abstractmethod
    def add_node(self, node_id: str, node_type: str, properties: Dict = None) -> None:
        pass
    
    @abstractmethod
    def add_edge(self, source: str, target: str, relation: str, properties: Dict = None) -> None:
        pass
    
    @abstractmethod
    def search(self, query: str) -> List[Dict]:
        pass
    
    @abstractmethod
    def get_neighbors(self, node_id: str, relation_type: Optional[str] = None) -> List[str]:
        pass

class Retriever(ABC):
    """Base retriever interface."""
    
    @abstractmethod
    def search(self, query: str, top_k: int = 10, **kwargs) -> List[SearchResult]:
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        pass
```

#### 1.2 Migrations System

Add version tracking and migration runner to `RelationalStore`:

```python
# In relational_store.py, add:
CURRENT_VERSION = 1

def get_schema_version(self) -> int:
    conn = sqlite3.connect(str(self.db_path))
    try:
        cursor = conn.execute("SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else 0
    finally:
        conn.close()

def migrate(self, target_version: int) -> bool:
    current = self.get_schema_version()
    for version in range(current + 1, target_version + 1):
        self._run_migration(version)
    return True
```

#### 1.3 Hybrid Search

Implement `HybridRetriever` that combines:
- Semantic (vector) search
- Keyword (FTS5) search
- Graph (neighborhood) search
- Trust-weighted reranking

#### 1.4 Trust Integration

Wire `TrustAwareRetrieval` into the retrieval pipeline:
- After RRF fusion, apply trust-weighted reranking
- Expose `trust_weight` parameter (default 0.3)

#### Success Criteria for PHASE 1
- [ ] All stores implement typed interfaces
- [ ] Migrations run successfully on fresh database
- [ ] Hybrid search returns results from all 3 sources
- [ ] Trust scores affect final ranking

---

### PHASE 2: LEARNING-MEMORY BRIDGE (Week 2-3, Days 15-21)

**Objective**: Connect cognitive layer to memory writes and learning engine.

| Task | Description | Agent | Effort | Dependencies |
|------|-------------|-------|--------|--------------|
| 2.1 | Connect cognitive layer to memory writes (auto-trigger forgetting/reconsolidation) | Hephaestus | Medium | 1.* |
| 2.2 | Add learning-based RRF weight tuning | Hephaestus | Medium | 1.*, learning_engine |
| 2.3 | Connect EWC to Q-Learning | Oracle→Hephaestus | Medium | learning_engine |
| 2.4 | Wire cross-session transfer into session lifecycle | Hephaestus | Medium | 1.*, learning_engine |

#### 2.1 Cognitive Auto-Trigger

Create a `CognitiveTrigger` class that hooks into memory writes:

```python
# packages/memory_core/cognitive/trigger.py

class CognitiveTrigger:
    """Auto-trigger cognitive processes on memory operations."""
    
    def __init__(self):
        self.forgetting = AdaptiveDecay()
        self.reconsolidation = MemoryReconsolidation()
        self.trust = TrustAwareRetrieval()
    
    def on_memory_write(self, memory_id: str, content: str) -> None:
        """Triggered when a memory is written."""
        # Initialize trust score for new memory
        self.trust.initialize_trust(memory_id)
    
    def on_memory_read(self, memory_id: str) -> None:
        """Triggered when a memory is accessed."""
        # Record access for forgetting calculation
        record_access(memory_id)
    
    def on_session_end(self) -> List[str]:
        """Triggered at session end."""
        # Apply forgetting decay
        actions = apply_decay_actions()
        # Trigger reconsolidation
        self.reconsolidation.consolidate()
        return actions
```

#### 2.2 Learning-Based RRF Weight Tuning

Connect `RoutingWeightOptimizer` to RRF:
- Learn optimal `k` value (RRF constant) based on task success
- Learn per-retriever weights based on click-through data

#### 2.3 EWC→Q-Learning Connection

- EWC (Elastic Weight Consolidation) protects important parameters
- Q-Learning uses those parameters for routing decisions
- Implement: Pass EWC importance scores to Q-Learning reward calculation

#### 2.4 Cross-Session Transfer

Wire `CrossSessionTransfer` into session lifecycle:
- On session start: Load relevant memories from previous sessions
- On session end: Archive important session memories to long-term storage

#### Success Criteria for PHASE 2
- [ ] Forgetting triggers automatically on session end
- [ ] Reconsolidation runs during sleep cycles
- [ ] RRF weights adjust based on learning feedback
- [ ] Cross-session memories accessible on session start

---

### PHASE 3: ADVANCED FEATURES (Week 3, Days 22-28)

**Objective**: Polish and add advanced capabilities.

| Task | Description | Agent | Effort | Dependencies |
|------|-------------|-------|--------|--------------|
| 3.1 | Adaptive priority weight learning | Hephaestus | Short | 2.* |
| 3.2 | Neo4j driver option for graph store | Oracle→Hephaestus | Medium | 1.1 |
| 3.3 | MMR diversity scoring | Hephaestus | Short | 1.3 |
| 3.4 | Cross-encoder reranking | Hephaestus | Medium | 1.3 |

#### Success Criteria for PHASE 3
- [ ] Priority weights adapt based on usage patterns
- [ ] Neo4j driver functional (optional, behind feature flag)
- [ ] MMR diversifies retrieval results
- [ ] Cross-encoder improves top-k ranking

---

### PHASE 4: VALIDATION (Week 4, Days 29-35)

**Objective**: Add tests, run gates, get reviews.

| Task | Description | Agent | Effort | Dependencies |
|------|-------------|-------|--------|--------------|
| 4.1 | Add test coverage (80% target) | Hephaestus | Large | All previous |
| 4.2 | Run quality gates (typecheck, lint, format, test) | Sisyphus | Short | 4.1 |
| 4.3 | Oracle architecture review | Oracle | Medium | 4.2 |
| 4.4 | Momus adversarial review | Momus | Medium | 4.3 |
| 4.5 | Documentation | Sisyphus | Medium | 4.4 |

#### Test Coverage Requirements
- Store interfaces: 100% coverage
- Retriever interfaces: 100% coverage
- Cognitive triggers: 80% coverage
- Integration tests: 60% coverage

#### Quality Gates
```bash
# Run all gates
./bin/quality-gates/gate-1-py-typecheck.sh
./bin/quality-gates/gate-2-py-lint.sh
./bin/quality-gates/gate-3-format.sh
./bin/quality-gates/gate-4-test.sh
./bin/quality-gates/gate-5-secrets.sh
./bin/quality-gates/gate-6-placeholders.sh
```

#### Success Criteria for PHASE 4
- [ ] Test coverage ≥ 80%
- [ ] All quality gates pass
- [ ] Oracle approves architecture
- [ ] Momus finds no critical issues
- [ ] Documentation complete

---

## Delegation Chain

### PHASE 0: Critical Fixes

| Task | Delegate To | Keep With | Send To Review |
|------|-------------|-----------|----------------|
| 0.1 MCP imports | Hephaestus | Sisyphus | - |
| 0.2 Daemon imports | Hephaestus | Sisyphus | - |
| 0.3 Graph store | Hephaestus | Sisyphus | - |
| 0.4 Keyword retriever | Hephaestus | - | - |
| 0.5 Fusion dedupe | Sisyphus-Junior | - | - |

**Rationale**: All PHASE 0 tasks are simple fixes. Hephaestus handles anything requiring logic changes; Sisyphus-Junior handles trivial deduplication.

### PHASE 1: Core Integration

| Task | Delegate To | Keep With | Send To Review |
|------|-------------|-----------|----------------|
| 1.1 Typed interfaces | - | Oracle | Oracle (design first) |
| 1.2 Migrations | Hephaestus | Sisyphus | - |
| 1.3 Hybrid search | Hephaestus | Sisyphus | - |
| 1.4 Trust integration | Hephaestus | Sisyphus | - |

**Rationale**: Task 1.1 requires architectural design before implementation. Send to Oracle for design review first.

### PHASE 2: Learning-Memory Bridge

| Task | Delegate To | Keep With | Send To Review |
|------|-------------|-----------|----------------|
| 2.1 Cognitive trigger | Hephaestus | Sisyphus | Oracle |
| 2.2 RRF weight tuning | Hephaestus | Sisyphus | Oracle |
| 2.3 EWC→Q-Learning | - | Oracle | Oracle (design) |
| 2.4 Cross-session | Hephaestus | Sisyphus | - |

**Rationale**: Tasks 2.1 and 2.2 require integration with existing cognitive code. Send to Oracle for integration review. Task 2.3 needs architectural design for EWC-Q connection.

### PHASE 3: Advanced Features

| Task | Delegate To | Keep With | Send To Review |
|------|-------------|-----------|----------------|
| 3.1 Priority learning | Hephaestus | - | - |
| 3.2 Neo4j driver | - | Oracle | Oracle (design) |
| 3.3 MMR scoring | Hephaestus | - | - |
| 3.4 Cross-encoder | Hephaestus | - | Oracle |

**Rationale**: Neo4j driver (3.2) is a significant architectural decision. Cross-encoder (3.4) needs Oracle review for model selection.

### PHASE 4: Validation

| Task | Delegate To | Keep With | Send To Review |
|------|-------------|-----------|----------------|
| 4.1 Tests | Hephaestus | Sisyphus | - |
| 4.2 Gates | - | Sisyphus | - |
| 4.3 Oracle review | - | Oracle | - |
| 4.4 Momus review | - | Momus | - |
| 4.5 Docs | Sisyphus | - | - |

**Rationale**: Standard validation flow. Tests written by Hephaestus (implementation), gates run by Sisyphus (orchestration), reviews by Oracle/Momus (reviewers).

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     MEMORY SYSTEM ARCHITECTURE                  │
└─────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │   MCP Server    │
                              │  (mcp_server)  │
                              └────────┬────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          │                            │                            │
          ▼                            ▼                            ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Memory Manager │      │   Daemon        │      │   Cognitive    │
│                 │      │  (background)   │      │   Trigger      │
└────────┬────────┘      └────────┬────────┘      └────────┬────────┘
         │                         │                         │
         │    ┌────────────────────┴────────────────────┐    │
         │    │            STORES LAYER                 │    │
         │    │  ┌──────────┐ ┌───────────┐ ┌─────────┐ │    │
         │    │  │ Vector   │ │ Relational│ │ Graph  │ │    │
         │    │  │ Store    │ │ Store     │ │ Store  │ │    │
         │    │  └────┬─────┘ └─────┬─────┘ └───┬───┘ │    │
         │    │       │             │           │     │    │
         │    │       └─────────────┴───────────┘     │    │
         │    │                 │                     │    │
         │    │                 ▼                     │    │
         │    │         ┌──────────────┐             │    │
         │    │         │  Retrievers  │             │    │
         │    │  ┌──────┴─────┐ ┌─────┴──────┐      │    │
         │    │  │  Semantic  │ │  Keyword   │      │    │
         │    │  └─────┬──────┘ └──────┬─────┘      │    │
         │    │        │               │            │    │
         │    │        └───────┬───────┘            │    │
         │    │                ▼                    │    │
         │    │         ┌─────────────┐             │    │
         │    │         │ RRF Fusion   │             │    │
         │    │         │ (TEMPR)      │             │    │
         │    │         └──────┬────────┘             │    │
         │    │                │                      │    │
         │    │                ▼                      │    │
         │    │         ┌─────────────┐              │    │
         │    │         │Trust Weight │              │    │
         │    │         │ Reranking   │              │    │
         │    │         └──────┬────────┘             │    │
         │    │                │                      │    │
         └────┼────────────────┼──────────────────────┘    │
              │                │                             │
              ▼                ▼                             ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Learning      │    │    Cognitive    │    │   Cross-Session │
│   Engine        │◄───►│    Layer        │    │   Transfer      │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    └─────────────────┘
│ │QLearning    │ │    │ │Forgetting   │ │
│ │MultiArmed   │ │    │ │Reconsolid.  │ │
│ │Bandit       │ │    │ │Trust        │ │
│ │EWC          │ │    │ │Priority     │ │
│ └─────────────┘ │    │ └─────────────┘ │
│                 │    │                 │
│ ┌─────────────┐ │    └─────────────────┘
│ │Routing      │ │
│ │Optimizer    │ │
│ └─────────────┘ │
└─────────────────┘
```

### Data Flow

1. **Write Path**: MCP Server → Memory Manager → Stores → Cognitive Trigger → Learning Engine
2. **Read Path**: MCP Server → Memory Manager → Retrievers → RRF Fusion → Trust Reranking → Response
3. **Background**: Daemon → Sleep Engine → Reconsolidation → Cross-Session Transfer

---

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Import errors not fully resolved | High | Medium | Comprehensive stub strategy |
| Cognitive triggers cause performance issues | Medium | Low | Add rate limiting, async processing |
| Trust scores degrade over time | Medium | Medium | Regular decay, verification prompts |
| RRF weight tuning diverges | Medium | Low | Bounded learning rate, sanity checks |
| EWC→Q-Learning connection unstable | High | Medium | Careful parameter passing, testing |
| Neo4j driver adds complexity | Low | Low | Feature flag, optional dependency |
| Test coverage target not met | Medium | Medium | Prioritize critical paths |

---

## Escalation Triggers

The following conditions justify escalating to a more complex solution:

| Condition | Trigger | Escalation Path |
|-----------|---------|-----------------|
| Import errors persist after PHASE 0 | >3 unresolved imports | → Oracle emergency design review |
| Hybrid search performance <100ms | Latency >500ms | → Optimize indexing, consider caching |
| Trust scores all converge to 0 or 1 | Variance <0.01 | → Reset trust, adjust decay params |
| RRF weight tuning diverges | Weight >10x initial | → Clamp weights, reset learning |
| EWC→Q-Learning causes routing failures | Success rate <80% | → Disable integration, fallback |
| Test coverage <50% after PHASE 4 | Coverage <50% | → Extend timeline, prioritize |
| Quality gates fail twice | 2 consecutive failures | → Block merge, full review |

---

## Typed Interface Definitions (Full)

### Store Interfaces

```python
# packages/memory_core/stores/interfaces.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import numpy as np

class MemoryTier(str, Enum):
    """Memory tier classification."""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    REASONING = "reasoning"

class MemoryScope(str, Enum):
    """Memory scope classification."""
    SESSION = "session"
    PROJECT = "project"
    GLOBAL = "global"

class MemoryKind(str, Enum):
    """Memory kind classification."""
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"

@dataclass
class MemoryRecord:
    """Complete memory record with all metadata."""
    id: str
    content: str
    kind: MemoryKind
    scope: MemoryScope
    tier: MemoryTier
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    embedding: Optional[np.ndarray] = None
    trust_score: Optional[float] = None
    access_count: int = 0
    last_accessed: Optional[str] = None

@dataclass
class SearchResult:
    """Search result with scoring."""
    id: str
    content: str
    score: float
    source: str
    tier: Optional[MemoryTier] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    trust_score: Optional[float] = None
    rank: int = 0

class VectorStore(ABC):
    """Vector-based memory storage interface."""
    
    @abstractmethod
    def search(self, query_embedding: np.ndarray, top_k: int = 10, 
               filters: Optional[Dict] = None) -> List[SearchResult]:
        """Search by vector similarity."""
        pass
    
    @abstractmethod
    def store(self, content: str, embedding: np.ndarray, 
              metadata: Optional[Dict] = None) -> str:
        """Store with embedding."""
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete by ID."""
        pass
    
    @abstractmethod
    def get_embedding(self, id: str) -> Optional[np.ndarray]:
        """Get embedding by ID."""
        pass

class RelationalStore(ABC):
    """SQLite-based structured memory interface."""
    
    @abstractmethod
    def search(self, query: str, limit: int = 10, 
               filters: Optional[Dict] = None) -> List[SearchResult]:
        """Full-text search."""
        pass
    
    @abstractmethod
    def store(self, content: str, kind: MemoryKind = MemoryKind.EPISODIC,
              scope: MemoryScope = MemoryScope.SESSION,
              tier: MemoryTier = MemoryTier.SHORT_TERM,
              metadata: Optional[Dict] = None) -> str:
        """Store memory record."""
        pass
    
    @abstractmethod
    def get(self, id: str) -> Optional[MemoryRecord]:
        """Get by ID."""
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        """Soft delete (archive)."""
        pass
    
    @abstractmethod
    def list_by_tier(self, tier: MemoryTier, limit: int = 100) -> List[MemoryRecord]:
        """List memories by tier."""
        pass
    
    @abstractmethod
    def update_access(self, id: str) -> bool:
        """Update access timestamp and count."""
        pass
    
    @abstractmethod
    def migrate(self, from_version: int, to_version: int) -> bool:
        """Run migration between versions."""
        pass

class GraphStore(ABC):
    """Knowledge graph storage interface."""
    
    @abstractmethod
    def add_node(self, node_id: str, node_type: str, 
                 label: str = "", content: str = "",
                 properties: Optional[Dict] = None) -> None:
        """Add a node."""
        pass
    
    @abstractmethod
    def add_edge(self, source: str, target: str, relation: str,
                 weight: float = 0.5, properties: Optional[Dict] = None) -> None:
        """Add an edge."""
        pass
    
    @abstractmethod
    def search_nodes(self, query: str) -> List[Dict]:
        """Search nodes by label or content."""
        pass
    
    @abstractmethod
    def get_neighbors(self, node_id: str, 
                      relation_type: Optional[str] = None,
                      min_weight: float = 0.0) -> List[Dict]:
        """Get neighboring nodes."""
        pass
    
    @abstractmethod
    def get_path(self, source: str, target: str, max_hops: int = 3) -> List[Dict]:
        """Find path between nodes."""
        pass

class Retriever(ABC):
    """Base retriever interface."""
    
    @abstractmethod
    def search(self, query: str, top_k: int = 10, 
               filters: Optional[Dict] = None) -> List[SearchResult]:
        """Search for relevant memories."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Retriever identifier."""
        pass
    
    @abstractmethod
    def supports_hybrid(self) -> bool:
        """Whether this retriever supports hybrid mode."""
        pass
```

### Learning Engine Interfaces

```python
# packages/learning_engine/interfaces.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class DelegationOutcome:
    """Record of a delegation result."""
    task_id: str
    task_description: str
    agent: str
    level: int
    success: bool
    latency_ms: float
    tokens_used: int
    timestamp: str

@dataclass
class RoutingRecommendation:
    """Recommended agent for a task."""
    agent: str
    confidence: float
    level: int
    alternatives: List[str]
    reason: str

class RoutingEngine(ABC):
    """Task routing interface."""
    
    @abstractmethod
    def route(self, task_description: str, level: int) -> RoutingRecommendation:
        """Route a task to optimal agent."""
        pass
    
    @abstractmethod
    def record_outcome(self, outcome: DelegationOutcome) -> None:
        """Record delegation outcome for learning."""
        pass
    
    @abstractmethod
    def get_weights(self) -> Dict[str, float]:
        """Get current routing weights."""
        pass

class LearningEngine(ABC):
    """Meta-learning interface."""
    
    @abstractmethod
    def update(self, outcome: DelegationOutcome) -> None:
        """Update model based on outcome."""
        pass
    
    @abstractmethod
    def get_importance_scores(self) -> Dict[str, float]:
        """Get EWC importance scores."""
        pass
    
    @abstractmethod
    def protect_parameters(self, importance_scores: Dict[str, float]) -> None:
        """Apply EWC regularization."""
        pass
```

---

## Timeline Summary

| Phase | Days | Focus | Key Deliverables |
|-------|------|-------|-------------------|
| PHASE 0 | 1-3 | Critical fixes | Zero import errors, bug fixes |
| PHASE 1 | 4-14 | Core integration | Typed interfaces, migrations, hybrid search, trust |
| PHASE 2 | 15-21 | Learning bridge | Cognitive triggers, RRF tuning, EWC→Q, cross-session |
| PHASE 3 | 22-28 | Advanced features | Priority learning, Neo4j, MMR, cross-encoder |
| PHASE 4 | 29-35 | Validation | Tests, gates, reviews, docs |

**Total**: ~35 days (5 weeks)

---

## Next Steps

1. **Immediate**: Run PHASE 0 tasks in parallel (Hephaestus for 0.1-0.4, Sisyphus-Junior for 0.5)
2. **After PHASE 0**: Verify zero import errors with `lsp_diagnostics`
3. **PHASE 1**: Start with Oracle design review for typed interfaces (1.1)
4. **Gateway**: After each phase, run quality gates before proceeding

---

*End of Masterplan*
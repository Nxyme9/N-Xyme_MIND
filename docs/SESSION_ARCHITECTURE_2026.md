# Session Architecture 2026

> Research findings on ML-native session management for N-Xyme_MIND
> Date: April 2026 | Author: Librarian Agent

---

## Executive Summary

This document synthesizes bleeding-edge approaches to AI agent session and context management, with specific recommendations for replacing legacy `.sisyphus` file-based sessions with a modern ML-native architecture. Our existing infrastructure—**memory_store** (storage), **learning_engine** (Q-Learning), and **brain_mcp** (orchestration)—provides a strong foundation for implementing production-grade session management that aligns with what big AI labs use in 2026.

---

## 1. Current Best Practices

### 1.1 What Big AI Labs Use

| System | Architecture | Key Innovation | Benchmark |
|--------|-------------|----------------|-----------|
| **Mem0** | Hybrid (vector + graph + KV) | Multi-scope memory (user/session/agent) | 66.9% LOCOMO, +26% vs OpenAI |
| **Zep** | Temporal Knowledge Graph | Fact validity windows, auto-versioning | 63.8% LongMemEval (15pt lead) |
| **Letta** | OS-tiered (MemGPT heritage) | Agent-managed memory blocks, MemFS | 74.0% TerminalBench |
| **Cognee** | Multi-strategy hybrid | Read-optimized, embedded PG + LanceDB | Growing fast (~12K stars) |

### 1.2 Key Architectural Patterns

**1.2.1 Multi-Scope Memory (Mem0 Pattern)**
- **User scope**: Persistent across all sessions (preferences, account state)
- **Session scope**: Temporary, cleared manually or on completion
- **Agent scope**: Shared across users or specific to agent instance

**1.2.2 Temporal Knowledge Graph (Zep Pattern)**
- Every fact stored with validity window ("as of [timestamp]")
- Automatic graph updates when facts change
- Can answer "what was X before it changed?"

**1.2.3 Tiered Memory (Letta Pattern)**
- **Core memory**: Fixed-size, always in context (identity, goals)
- **Archival memory**: Vector-stored, retrieved on demand
- **Recall functions**: Fetch/prioritize before LLM calls

---

## 2. N-Xyme_MIND Integration Recommendations

### 2.1 Current State Analysis

**Existing components:**
- `memory_store/session_memory.py`: JSON file-based session notes
- `learning_engine/routing/adaptive_router.py`: Q-Learning with circuit breaker
- `brain_mcp/namespaces/session.py`: SQLite-backed session list
- `memory_store/stores/vector_store.py`: 768-dim embeddings + FAISS

**Gap analysis:**
- Sessions stored as flat JSON files (no semantic retrieval)
- No temporal versioning (can't answer "what changed?")
- No hybrid storage (missing graph layer)
- Session recovery relies on exact ID matching

### 2.2 Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    N-Xyme_MIND Session Architecture              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │  HOT PATH    │    │  WARM PATH   │    │  COLD PATH   │     │
│  │  (Redis/in-   │    │  (Vector DB) │    │  (Postgres/   │     │
│  │   memory)     │    │  (Qdrant/    │    │   SQLite)    │     │
│  │              │    │   pgvector)  │    │              │     │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘     │
│         │                  │                  │              │
│         ▼                  ▼                  ▼              │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              SESSION MEMORY LAYER                        │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐     │  │
│  │  │Current  │  │ Session │  │  User   │  │ Project │     │  │
│  │  │Session  │  │ History │  │ Profile │  │ Context │     │  │
│  │  │(Core)  │  │(Archive)│  │(Long-term)│ (Global)│     │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘     │  │
│  └─────────────────────────────────────────────────────────┘  │
│                              │                                 │
│                              ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              EXTRACTION PIPELINE (LLM)                    │  │
│  │  - Semantic fact extraction from session text              │  │
│  │  - Entity resolution + relationship building               │  │
│  │  - Temporal metadata injection                            │  │
│  └─────────────────────────────────────────────────────────┘  │
│                              │                                 │
│                              ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              LEARNING ENGINE (Q-Learning)                │  │
│  │  - Session similarity → reward signal                      │  │
│  │  - Adaptive recovery (best session for task)               │  │
│  │  - Routing weights updated on outcome                      │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Implementation Using Existing Components

**Phase 1: Semantic Session Encoding**

```python
# NEW: packages/memory_store/session_embedder.py
from packages.memory_store.stores.vector_store import embed_text, EMBED_DIM

class SessionEmbedder:
    """Encode sessions as vectors for similarity retrieval."""
    
    def __init__(self):
        self.embedding_cache = {}  # session_id -> vector
    
    def embed_session(self, session_data: dict) -> list[float]:
        """Create semantic representation of session."""
        # Combine key fields into embedding text
        text = self._build_session_text(session_data)
        return embed_text(text)
    
    def _build_session_text(self, session: dict) -> str:
        """Extract key information for embedding."""
        parts = [
            session.get("title", ""),
            session.get("task_spec", ""),
            session.get("key_results", ""),
            session.get("errors", ""),
        ]
        return " | ".join(p for p in parts if p)
    
    def find_similar_sessions(
        self, 
        query: str, 
        top_k: int = 5
    ) -> list[tuple[str, float]]:
        """Find sessions by semantic similarity."""
        query_vec = embed_text(query)
        # Compare against all session embeddings
        # Return (session_id, similarity_score) pairs
```

**Phase 2: Hybrid Storage (Hot/Cold)**

```python
# NEW: packages/memory_store/session_store.py
from packages.memory_store.stores.vector_store import VectorIndex
import json
from pathlib import Path

class HybridSessionStore:
    """Hot path = in-memory, Cold path = vector DB."""
    
    def __init__(self, project_root: Path):
        self.hot_store = {}  # session_id -> session_data
        self.cold_index = VectorIndex(metric="cosine")
        self.project_root = project_root
        
    def create_session(self, session_id: str, data: dict) -> None:
        """Create session with dual storage."""
        # HOT: Immediate access
        self.hot_store[session_id] = data
        
        # COLD: Vector embedding for similarity search
        embedder = SessionEmbedder()
        vector = embedder.embed_session(data)
        self.cold_index.add_vector(
            vector, 
            {"session_id": session_id, "content": json.dumps(data)}
        )
        
        # PERSIST: SQLite for durability
        self._persist_to_sqlite(session_id, data)
    
    def recover_session(self, task_description: str) -> dict | None:
        """Use learning_engine to pick best session."""
        from packages.learning_engine.routing.adaptive_router import AdaptiveRouter
        
        router = AdaptiveRouter()
        routing = router.route(task_description)
        
        # Get similar sessions via vector search
        similar = self.cold_index.search_by_vector(
            embed_text(task_description), 
            top_k=3
        )
        
        # Return best match or None
        if similar:
            return self.get_session(similar[0].metadata["session_id"])
        return None
```

**Phase 3: Temporal Graph (Optional Enhancement)**

```python
# Enhancement: Add temporal knowledge graph for fact versioning
# Uses existing learning_engine infrastructure

class TemporalSessionGraph:
    """Track how session facts change over time."""
    
    def __init__(self):
        self.facts = {}  # session_id -> list of (fact, timestamp, valid_until)
    
    def add_fact(self, session_id: str, fact: str, valid_from: str, valid_until: str = None):
        """Record fact with temporal validity."""
        if session_id not in self.facts:
            self.facts[session_id] = []
        self.facts[session_id].append({
            "fact": fact,
            "valid_from": valid_from,
            "valid_until": valid_until or "infinity"
        })
    
    def get_fact_at(self, session_id: str, timestamp: str) -> list[dict]:
        """Get facts that were valid at a specific time."""
        valid_facts = []
        for fact in self.facts.get(session_id, []):
            if fact["valid_from"] <= timestamp < fact["valid_until"]:
                valid_facts.append(fact)
        return valid_facts
```

---

## 3. Migration Path from .sisyphus

### 3.1 Phase 0: Inventory (Week 1)

```bash
# Analyze existing .sisyphus structure
ls -la .sisyphus/
# Expected: sessions/, state.db, routing_learning.db

# Count sessions
sqlite3 .sisyphus/state.db "SELECT COUNT(*) FROM sessions;"

# Check session file sizes
du -sh .sisyphus/sessions/
```

### 3.2 Phase 1: Embed Existing Sessions (Week 2)

```python
# Migration script
import json
from pathlib import Path

def migrate_sessions():
    """Convert file-based sessions to vector + SQLite."""
    sessions_dir = Path(".sisyphus/sessions")
    embedder = SessionEmbedder()
    store = HybridSessionStore(Path.cwd())
    
    for session_file in sessions_dir.glob("*.json"):
        with open(session_file) as f:
            session_data = json.load(f)
        
        session_id = session_file.stem
        store.create_session(session_id, session_data)
        
        # Archive original to .trash
        archive_path = Path(f".trash/migrated_sessions/{session_id}.json")
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        session_file.rename(archive_path)

# Run: python -c "from migrate import migrate_sessions; migrate_sessions()"
```

### 3.3 Phase 2: Update brain_mcp (Week 3)

```python
# Update brain_mcp/namespaces/session.py
def session_list_mcp(limit: int = 10, semantic_query: str = None):
    """Enhanced session list with semantic search."""
    if semantic_query:
        # Use vector similarity instead of just recency
        store = HybridSessionStore(Path.cwd())
        similar = store.cold_index.search_by_vector(
            embed_text(semantic_query), 
            top_k=limit
        )
        return {"sessions": [s.metadata["session_id"] for s in similar]}
    
    # Fall back to existing SQLite query
    return original_session_list_mcp(limit)
```

### 3.4 Phase 3: Adaptive Recovery (Week 4)

```python
# Integrate learning_engine for session selection
def session_recover(task_description: str) -> dict:
    """Use Q-Learning to pick optimal session."""
    store = HybridSessionStore(Path.cwd())
    
    # Step 1: Get Q-Learning recommendation
    router = AdaptiveRouter()
    routing = router.route(task_description)
    
    # Step 2: Find similar sessions
    similar = store.cold_index.search_by_vector(
        embed_text(task_description),
        top_k=5
    )
    
    # Step 3: Return best match
    if similar:
        return store.get_session(similar[0].metadata["session_id"])
    
    # Fallback: return most recent
    return get_most_recent_session()
```

---

## 4. Key Implementation Details

### 4.1 Session Schema

```python
@dataclass
class NXYmeSession:
    session_id: str
    created_at: datetime
    last_active: datetime
    
    # Core (always in context)
    title: str
    current_state: str
    
    # Extracted facts (vectorized for similarity)
    task_spec: str
    key_files: list[str]
    errors: list[str]
    learnings: list[str]
    
    # Temporal metadata
    version: int
    valid_facts: list[TemporalFact]
    
    # Embedding (computed, not stored)
    embedding: list[float] = None
```

### 4.2 Quality Gates

```bash
# After implementation
./bin/quality-gates/gate-1-typecheck.sh
./bin/quality-gates/gate-2-lint.sh
./bin/quality-gates/gate-5-secrets-scan.sh
```

### 4.3 Migration Validation

```python
def validate_migration():
    """Ensure no data loss during .sisyphus -> hybrid migration."""
    original = load_all_file_sessions()
    migrated = load_all_hybrid_sessions()
    
    # Compare count
    assert len(original) == len(migrated)
    
    # Compare key fields
    for orig, migr in zip(original, migrated):
        assert orig["title"] == migr["title"]
        assert orig["created_at"] == migr["created_at"]
    
    # Verify embeddings exist
    for session in migrated:
        assert session.embedding is not None
        assert len(session.embedding) == 768
```

---

## 5. Summary of Recommendations

| Priority | Recommendation | Complexity | Impact |
|----------|---------------|------------|--------|
| HIGH | Add vector embeddings to sessions | Medium | Enables semantic recovery |
| HIGH | Implement hot/cold hybrid storage | Medium | Fast access + durability |
| MEDIUM | Integrate learning_engine for adaptive recovery | Medium | ML-native session selection |
| MEDIUM | Add temporal fact tracking | High | Answer "what changed?" |
| LOW | Add knowledge graph layer (optional) | High | Full Mem0/Zep parity |

### Key Insight

Our existing `adaptive_router` and `outcome_logger` already implement Q-Learning for delegation. We can extend this pattern to session recovery—treating each session retrieval as a "decision" that gets a reward signal based on whether the recovered session was useful for the task.

This creates a **self-improving session memory system** where the more sessions we recover, the better we get at picking the right one.

---

## References

- Mem0 Research (arXiv:2504.19413) - LOCOMO benchmark
- Zep Temporal Knowledge Graph (arXiv:2501.13956) - LongMemEval
- Letta/MemGPT (arXiv:2310.08560) - OS-tiered memory
- N-Xyme_MIND existing: `packages/memory_store/`, `packages/learning_engine/`, `packages/brain_mcp/`

---

*End of Document*

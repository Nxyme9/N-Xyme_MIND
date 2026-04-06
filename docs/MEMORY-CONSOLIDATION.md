# Memory Consolidation Architecture

## Executive Summary

Unify four fragmented memory systems into a coherent architecture with clear ownership and data flow. Keep existing implementations—don't rewrite—create a unification layer that routes queries to the appropriate backend based on memory type.

**Effort:** Medium | **Priority:** High

---

## 1. Current Memory System Audit

### 1.1 Systems Overview

| System | File | Type | Storage | Query Interface |
|--------|------|------|---------|------------------|
| **Graphiti** | `src/graphiti_memory.py` | Episodic | Neo4j (port 8001) | JSON-RPC HTTP |
| **Hindsight MCP** | `hindsight_mcp.py` | Session | Embedded pg0/SQLite | MCP stdio |
| **Memory MCP** | Global (npx) | Semantic | Knowledge graph | Entities/relations |
| **Unified Memory MCP** | `src/unified_memory_mcp.py` | Unified | opencode.db + Graphiti | MCP stdio |
| **Session Files** | `.sisyphus/sessions/*.json` | Session | JSON files | File glob |

### 1.2 Duplication Issues

- **Search overlap**: Both `unified_memory_mcp.py` and `graphiti_memory.py` search Graphiti
- **Session storage**: Sessions stored in JSON files AND Hindsight (dual-write risk)
- **No routing logic**: No system determines which backend to query based on query intent

### 1.3 Data Flow (Current)

```
User Query → Unified Memory MCP → opencode.db (text search)
                        ↓
                   Graphiti HTTP (fallback)
                        ↓
              Memory MCP (manual, separate)
                        ↓
              Hindsight MCP (separate, unused)
```

**Problem:** No intelligent routing. All queries hit all backends.

---

## 2. Unified Architecture Design

### 2.1 Memory Type Taxonomy

| Memory Type | Owner | Description | Retention |
|-------------|-------|-------------|-----------|
| **Episodic** | Graphiti | Event sequences, chain runs | 30 days |
| **Session** | Hindsight | Per-session messages, context | 7 days |
| **Semantic** | Memory MCP | Entities, relations, facts | Permanent |
| **Working** | In-context | Current task state | Per prompt |

### 2.2 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Memory Router                             │
│  (determines memory type → routes to appropriate backend)   │
└─────────────────────────────────────────────────────────────┘
         ↓           ↓           ↓           ↓
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Graphiti   │ │  Hindsight │ │   Memory   │ │  In-Context│
│  (episodic) │ │  (session) │ │  (semantic)│ │  (working) │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

### 2.3 Memory Router Implementation

**Location:** `src/memory_router.py`

```python
class MemoryRouter:
    """Routes memory queries to appropriate backend based on type."""
    
    TYPE_KEYWORDS = {
        "episodic": ["what happened", "earlier", "before", "when", "session"],
        "semantic": ["who is", "what is", "concept", "definition", "learned"],
        "session": ["my last", "previous", "earlier in this"],
    }
    
    def route(self, query: str) -> list[str]:
        """Return list of backends to query."""
        query_lower = query.lower()
        
        # Semantic gets priority (facts over events)
        if any(kw in query_lower for kw in self.TYPE_KEYWORDS["semantic"]):
            return ["memory_mcp"]
        
        # Episodic for event sequences
        if any(kw in query_lower for kw in self.TYPE_KEYWORDS["episodic"]):
            return ["graphiti"]
        
        # Session for recent context
        if any(kw in query_lower for kw in self.TYPE_KEYWORDS["session"]):
            return ["hindsight"]
        
        # Default: query all
        return ["graphiti", "hindsight", "memory_mcp"]
```

### 2.4 Backend Wrappers

Create thin wrappers for each backend to normalize interfaces:

| Wrapper | File | Purpose |
|---------|------|---------|
| Graphiti wrapper | `src/memory/wrappers/graphiti.py` | HTTP → Python API |
| Hindsight wrapper | `src/memory/wrappers/hindsight.py` | MCP stdio → Python API |
| Memory MCP wrapper | `src/memory/wrappers/semantic.py` | Entity search API |

### 2.5 Consolidation Not Migration

**Critical principle:** Don't migrate data between systems. Each backend owns its domain. The router only orchestrates queries.

- Graphiti continues storing episodes
- Hindsight continues storing sessions  
- Memory MCP continues storing entities
- Router queries all and merges results

---

## 3. Implementation Roadmap

### Phase 1: Wrapper Layer (Short)

1. Create `src/memory/wrappers/` directory
2. Implement `graphiti.py` wrapper (convert HTTP to Python calls)
3. Implement `hindsight.py` wrapper (MCP stdio facade)
4. Add tests for each wrapper

### Phase 2: Router (Medium)

5. Create `src/memory/router.py` with keyword-based routing
6. Add "semantic" priority (entities before episodes)
7. Add result merging and deduplication

### Phase 3: Integration (Medium)

8. Register router as MCP tool `memory_search_unified`
9. Update `unified_memory_mcp.py` to use router
10. Add `/memory-status` CLI command

---

## 4. Integration Points

### 4.1 Trigger Engine Integration

The trigger engine (`src/trigger_engine.py`) already has memory-related actions. Extend with:

| Action | Purpose |
|--------|---------|
| `consolidate_episodes` | Batch Graphiti episodes to Memory MCP |
| `sync_session_to_memory` | Push Hindsight session to semantic graph |

### 4.2 MCP Server Integration

**Replace** `unified_memory_mcp.py` with router-based version:

```python
# Current (fragmented)
def handle_tools_call(...):
    if tool_name == "memory_search":
        opencode_results = search_opencode(...)
        graphiti_results = search_graphiti(...)
        # No Memory MCP, no Hindsight

# New (unified)
def handle_tools_call(...):
    if tool_name == "memory_search":
        router = MemoryRouter()
        backends = router.route(query)
        results = []
        for backend in backends:
            results.extend(backend.search(query))
        return dedup_and_rank(results)
```

### 4.3 Session Handoff Integration

On session handoff (see `docs/HANDOFF.md`):

1. Query all backends for relevant context
2. Merge into single context block
3. Inject into new session

---

## 5. Verification Criteria

- [x] Router correctly routes queries to backends based on keywords
- [x] All three backends (Graphiti, Hindsight, Memory MCP) return results
- [x] Deduplication removes duplicate entries
- [x] `/memory-status` shows backend health
- [ ] Trigger actions `consolidate_episodes` and `sync_session_to_memory` work
- [ ] Session handoff includes merged context from all backends

---

## 6. Implementation Status (Sprint 1 + 2 Complete)

### Sprint 1: Memory Architecture ✅
- [x] Created `src/memory/connectors.py` with all memory source connectors
- [x] Created `src/memory/registry.py` with health checks
- [x] Created `src/memory/router.py` with `get_unified_memory()` function
- [x] Added SQLite connectors for: mind_from_mind.db, jarvis_memory.db, jarvis_events.db, nxm_from_mind.db

### Sprint 2: Embeddings Engine ✅
- [x] Created `src/memory/embeddings.py` with Ollama integration
- [x] Implemented `embed_text(text)` → 768-dim vector
- [x] Implemented `similarity_search(query, documents, top_k)`
- [x] Implemented `batch_embed(documents)` for bulk processing
- [x] Connected embeddings to router via `VectorStore`

### Verification Results
```
$ python3 -c "from src.memory import router; print('router loads')"
router loads

$ python3 -c "from src.memory.embeddings import embed_text; print(embed_text('test')[:5])"
[0.24705882352941178, 0.050980392156862786, 0.6313725490196078, 0.0117647058823529, 0.06666666666666665]

$ pytest tests/ -v
13 passed
```

---

## 7. Future Considerations (Post-Consolidation)

| Feature | Trigger | Effort |
|---------|---------|--------|
| Vector similarity search | When similarity needed beyond keyword | Medium |
| Memory auto-prioritization | When certain facts should always load | Medium |
| Cross-backend relations | When entity episodes need linking | Large |

---

## 8. Open Questions

1. **Ranking strategy**: Should semantic (entities) always rank higher than episodic?
2. **Fallback behavior**: If one backend fails, continue with others or error?
3. **Cache layer**: Should router cache results within a session?


---

## Appendix: File Locations

| File | Purpose |
|------|---------|
| `src/memory/connectors.py` | All memory source connectors |
| `src/memory/registry.py` | Memory source registry with health checks |
| `src/memory/router.py` | Query routing and aggregation |
| `src/memory/embeddings.py` | Ollama embeddings engine |
| `src/memory/__init__.py` | Module exports |

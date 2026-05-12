# Memory Core Layer

## Overview

The Memory Core Layer provides modular memory system with TEMPR retrieval. It handles semantic and keyword search with RRF fusion, stores memories in multiple backends (vector, graph, relational, file), manages session context, and implements cognitive processes like adaptive forgetting, sleep cycles, and memory reconsolidation.

## Public API

```python
# Search memories
results = search(query="authentication", limit=10, strategy="rrf_fusion")

# Store memory
result = store(content="User preference: dark mode", kind="preference", scope="global")

# Recall session
memories = recall_session(session_id="abc123", limit=50)

# Get stats
stats = stats()
```

## Architecture

### Core Modules

| Module | Purpose | Key Classes | Key Functions |
|--------|---------|-------------|---------------|
| retrievers/tempr.py | TEMPR retrieval engine | TEMPRRetriever | search(), semantic_search(), keyword_search() |
| retrievers/semantic.py | Semantic search | SemanticRetriever | semantic_search() |
| retrievers/keyword.py | Keyword search | KeywordRetriever | keyword_search() |
| retrievers/fusion.py | RRF fusion | rrf_fusion() | - |
| stores/vector_store.py | Vector storage | VectorStore | add(), search() |
| stores/graph_store.py | Graph storage | GraphStore | add_node(), add_edge(), query() |
| stores/relational_store.py | Relational storage | RelationalStore | insert(), query() |
| stores/file_store.py | File storage | FileStore | write(), read() |
| sessions/context.py | Session context | SessionContext | get(), set(), clear() |
| sessions/lifecycle.py | Session lifecycle | SessionLifecycle | create(), archive(), cleanup() |
| cognitive/forgetting.py | Adaptive forgetting | AdaptiveDecay | calculate_decay() |
| cognitive/sleep_engine.py | Sleep cycle processing | SleepEngine | process_sleep_cycle() |
| cognitive/reconsolidation.py | Memory reconsolidation | MemoryReconsolidation | consolidate() |
| cognitive/priority.py | Memory priority | MemoryPriority | rank() |
| cognitive/retention.py | Retention management | RetentionManager | should_retain() |
| cognitive/trust.py | Trust scoring | TrustEngine | update_trust() |

### Storage Backend Modules

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| stores/base.py | Base store interface | BaseStore |
| stores/lance_store.py | LanceDB storage | LanceStore |
| stores/__init__.py | Store factory | get_store() |

### Indexing Modules

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| indexing/chunker.py | Text chunking | TextChunker |
| indexing/scanner.py | File scanning | FileScanner |

## Components

### TEMPR Retriever

- **Purpose**: Multi-strategy retrieval with Reciprocal Rank Fusion (RRF)
- **Strategies**:
  - `semantic`: Vector similarity search
  - `keyword`: BM25 keyword matching
  - `rrf_fusion`: Combine multiple strategies
- **Key Methods**:
  - `search()`: Main entry point with configurable strategy
  - `semantic_search()`: Vector-based search
  - `keyword_search()`: BM25-based search

### Vector Store

- **Purpose**: Store and search embeddings
- **Backend**: LanceDB (default), configurable
- **Key Methods**:
  - `add()`: Add embeddings to store
  - `search()`: Search by similarity

### Graph Store

- **Purpose**: Store memory relationships as graph
- **Key Methods**:
  - `add_node()`: Add memory node
  - `add_edge()`: Add relationship edge
  - `query()`: Query graph patterns

### Session Context

- **Purpose**: Manage per-session memory context
- **Key Methods**:
  - `get()`: Get session variable
  - `set()`: Set session variable
  - `clear()`: Clear session

### Cognitive Processes

- **Adaptive Forgetting**: Calculate memory decay based on importance, recency, trust
- **Sleep Engine**: Process memories during sleep cycles
- **Memory Reconsolidation**: Update and consolidate memories
- **Priority**: Rank memories by relevance
- **Retention**: Decide which memories to keep
- **Trust**: Track information source reliability

## Relationships

- **Depends on**: learning_engine (for routing-based memory), local_llm (for embeddings)
- **Used by**: intelligence layer (memory-augmented routing), orchestration (session context)

## Notes

- TEMPR = Targeted Extraction with Multi-Strategy Path Retrieval
- Supports multiple embedding models
- Session lifecycle includes: create, archive, cleanup
- Self-healer and health monitor for reliability
- Tier manager for memory hierarchy (hot/warm/cold)
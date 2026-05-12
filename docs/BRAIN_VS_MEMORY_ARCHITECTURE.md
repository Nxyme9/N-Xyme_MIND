# Brain vs Memory Architecture

## Purpose

| Component | Layer | Responsibility |
|-----------|-------|----------------|
| **brain_mcp** | High-level orchestration | "What context does this agent need?" |
| **memory_store** | Low-level storage | "Where do we store/retrieve data?" |

## Relationship

```
User task → brain_mcp (orchestrator)
              ↓
         [Decides WHAT context needed]
              ↓
    memory_store (storage/search)
              ↓
         [Returns raw data]
              ↓
    brain_mcp formats & injects
              ↓
    Agent gets context
```

## Current Namespaces in brain_mcp

| Namespace | What it does | Uses memory_store? |
|-----------|--------------|-------------------|
| **memory** | Basic memory operations | Yes - wraps it |
| **fingerprint** | Context injection from past sessions | Yes - search_memories |
| **context** | Active/product/user context | No - file reads |
| **mind** | Session state | No - JSON files |
| **learning** | Q-Learning routing | Partially |
| **intelligence** | Code quality | No |
| **session** | Pool management | No |
| **triggers** | Command triggers | No |
| **catalyst** | Workflow orchestration | No |

## What Should Stay Where

### brain_mcp (orchestration layer)
- ✅ fingerprint - orchestrates context injection
- ✅ context - file-based, not memory
- ✅ mind - session state
- ✅ learning - routing decisions
- ✅ catalyst - workflow orchestration

### memory_store (storage layer)
- ✅ All stores (vector, graph, relational)
- ✅ All retrievers (semantic, keyword, TEMPR)
- ✅ Memory search operations

### Could Move
- `brain_mcp.namespaces.memory` → just wrap memory_store, no duplication needed

## Code Flow Example

```python
# Agent asks for context
result = get_full_injected_context(agent="hephaestus", task="implement JWT")

# Brain decides:
# 1. Get global context (file read)
# 2. Get cross-session memory (memory_store.search)
# 3. Get session context (file read)
# 4. Get preferences (file read)

# Brain formats all into single context string
return formatted_context
```

**Memory doesn't know about "context" - it just stores and retrieves.**

**Brain knows about "context" but shouldn't do storage.**
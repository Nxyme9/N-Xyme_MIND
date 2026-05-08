# Session Pool Optimization Brainstorm

## Current State
- ✅ 36 pre-warmed sessions (3 per agent × 12 agents)
- ✅ Tool caching (~200ms savings)
- ✅ Context caching (300s TTL)
- ✅ Fast polling (100ms vs 500ms)
- ✅ **1.3s saved per OMO call**

---

## Next-Level Optimizations

### 🔥 Tier 1: Quick Wins (Same Implementation Effort)

| Optimization | Est. Savings | Complexity |
|--------------|--------------|------------|
| **Connection multiplex** - Single TCP to OMO, multiple sessions | 50-100ms | Low |
| **Tool def deduplication** - Shared tool schema across agents | 20-50ms | Low |
| **Context diffing** - Only send delta, not full context | 30-80ms | Medium |
| **Request coalescing** - Batch similar agent calls | 100-200ms | Medium |

### 🚀 Tier 2: Architecture Changes

| Optimization | Est. Savings | Complexity |
|--------------|--------------|------------|
| **Predictive pre-warming** - Analyze task patterns, warm likely agents | 200-400ms | High |
| **Local LLM routing** - Fast-path for simple tasks via GGUF | 500-1000ms | High |
| **Ephemeral sessions** - Ultra-fast for stateless tasks | 100-150ms | Medium |
| **Session affinity** - Stick to same session for related tasks | 50-100ms | Medium |

### 🎯 Tier 3: Bleeding Edge

| Optimization | Est. Savings | Complexity |
|--------------|--------------|------------|
| **WebSocket persistent** - True long-lived connections | 200-300ms | High |
| **ML-based prediction** - Predict next agent from task context | 300-500ms | Very High |
| **Zero-copy IPC** - Shared memory for session data | 50-100ms | Very High |
| **Edge computing** - Pre-warm on CDN edge | 500ms+ | Extreme |

---

## Top 3 Recommended for Implementation

### 1. Connection Multiplexing
```python
# Instead of: new connection per agent call
# Do: single persistent connection, multiplex sessions

class MultiplexedConnection:
    """Single TCP connection, multiple virtual sessions."""
    def __init__(self):
        self.connection = None  # One persistent connection
        self.sessions = {}       # Virtual session mapping
    
    def send(self, session_id, message):
        # Add session header, reuse connection
        self.connection.send(session_id + "|" + message)
```

**Est. Impact:** 50-100ms per call
**Effort:** Low (1-2 days)

### 2. Context Diffing
```python
# Instead of: send full context each time
# Do: send only the delta (changes)

def get_context_delta(old_ctx, new_ctx):
    """Calculate diff between contexts."""
    return diff(old_ctx, new_ctx)  # Only ~10-20% of data

# Receiver reconstructs full context from last known + delta
def reconstruct_context(last_known, delta):
    return patch(last_known, delta)
```

**Est. Impact:** 30-80ms per call
**Effort:** Medium (3-5 days)

### 3. Request Coalescing
```python
# Instead of: multiple sequential agent calls
# Do: detect and batch similar calls

async def coalesce_requests(requests: List[AgentRequest]) -> List[AgentResponse]:
    # Group by similar context
    groups = group_by_similarity(requests)
    
    # Execute in parallel where possible
    results = await asyncio.gather(*[execute_group(g) for g in groups])
    
    return flatten(results)
```

**Est. Impact:** 100-200ms for batch of 3-5 calls
**Effort:** Medium (3-5 days)

---

## Implementation Priority

1. **Connection Multiplexing** - Quick win, high impact
2. **Request Coalescing** - Good for burst workloads
3. **Tool Deduplication** - Simple, low effort
4. **Context Diffing** - Good ROI
5. **Predictive Pre-warming** - Requires analysis of task patterns first

---

## Measurements Needed

Before implementing next optimizations:
- [ ] Log actual OMO call patterns (agent sequence, timing)
- [ ] Measure context size per agent
- [ ] Profile connection setup overhead
- [ ] Identify "hot" agent sequences (frequent patterns)
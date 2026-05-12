# MASTER PLAN: Parallel GGUF Inference Architecture

## Executive Summary

**Goal**: Enable parallel sub-agent execution (explore, librarian) using local GGUF models without request failures.

**Root Cause**: llama-cpp-python's `Llama` object is NOT thread-safe. Concurrent requests crash/freeze the server.

**Solution**: Multi-port server pool with load balancing.

---

## Research Findings

### Problem Analysis

| Issue | Impact | Solution |
|-------|--------|----------|
| GIL released during C++ inference | Threads interfere | Use processes, not threads |
| Single model instance shared | Race conditions | One model per process |
| ThreadedHTTPServer not enough | Parallel requests fail | Multiple server instances |

### Architecture Options Compared

| Option | Effort | Parallelism | Memory | Tool Support |
|--------|--------|-------------|--------|--------------|
| **A: Multi-port pool** | 2-4h | ✅ True | ~4.6GB/model | ⚠️ Manual |
| **B: llama-cpp-python server** | 1h | ⚠️ Serialized | Lower | Built-in |
| **C: vLLM replacement** | 2-3d | ✅ Full | Higher | ✅ Yes |
| **D: LM Studio** | 0h | ✅ Yes | GUI | ✅ Yes |

---

## Implementation Plan

### Phase 1: Quick Win (Today) - Multi-Port Pool

```
Architecture:
┌─────────────────────────────────────────────────────────────┐
│                    OpenCode Agent Router                     │
│              Routes to: 8081, 8082, 8083 (round-robin)      │
└─────────────────────────────────────────────────────────────┘
        │              │              │
        ▼              ▼              ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │ Server  │   │ Server  │   │ Server  │
   │  :8081  │   │  :8082  │   │  :8083  │
   │ qwen    │   │ qwen    │   │ nomic   │
   │ 0.5b    │   │ 7b      │   │ embed   │
   └─────────┘   └─────────┘   └─────────┘
```

**Steps:**
1. Create `start_gguf_8081.sh` (qwen 0.5b)
2. Create `start_gguf_8082.sh` (qwen 7b)
3. Create `start_gguf_8083.sh` (nomic embed)
4. Update opencode.json with fallback routing

**Files to Create:**
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/start_gguf_8081.sh`
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/start_gguf_8082.sh`  
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/start_gguf_8083.sh`

**opencode.json changes:**
```json
{
  "agent": {
    "explore": {
      "router_override": {
        "prefer": "gguf/qwen2.5-0.5b-instruct-q4_k_m",
        "fallback_order": ["gguf/qwen2.5-coder-7b-q4_k_m"]
      }
    },
    "librarian": {
      "router_override": {
        "prefer": "gguf/qwen2.5-coder-7b-q4_k_m"
      }
    }
  }
}
```

### Phase 2: Smart Load Balancer (Tomorrow)

**File:** `packages/local_llm/gguf_load_balancer.py`

Features:
- Tracks in-flight requests per port
- Routes to least-loaded server
- Circuit breaker for failing ports
- Health checks with model status

```python
class GGUFLoadBalancer:
    def __init__(self, servers: List[dict]):
        self.servers = {s["port"]: {"url": s["url"], "active": 0, "failures": 0} for s in servers}
    
    def get_server(self) -> dict:
        """Return server with minimum active requests"""
        available = [s for s in self.servers.values() if s["failures"] < 3]
        return min(available, key=lambda s: s["active"])
    
    def record_request(self, port: int):
        self.servers[port]["active"] += 1
    
    def record_response(self, port: int, success: bool):
        self.servers[port]["active"] -= 1
        if not success:
            self.servers[port]["failures"] += 1
```

### Phase 3: Tool Calling Support (If Needed)

Since Ollama doesn't handle tool calls well, consider:

1. **LangChain integration**: Use langchain-community with GGUF models
2. **Function calling via prompt**: Train/instruct model to output JSON tool calls
3. **Hybrid approach**: Use cloud model for tool calling, GGUF for generation

### Phase 4: Benchmark & Monitor

**Metrics to track:**
- Requests per second (throughput)
- Latency (p50, p95, p99)
- Token throughput (tok/s)
- Error rate
- Memory usage per model

---

## Benchmark Results (Current)

### Sequential Benchmark

| Model | Provider | Latency | Throughput | Notes |
|-------|----------|---------|------------|-------|
| Qwen 2.5 7B | Ollama | 1.37s | 115 tok/s | Works |
| Qwen 2.5 0.5B | GGUF | N/A | N/A | Server dies on parallel |
| Qwen 2.5 7B | GGUF | N/A | N/A | Not tested yet |

### Parallel Benchmark (Ollama - 2 workers)

| Metric | Value |
|--------|-------|
| Wall time | 3.07s |
| Successful requests | 6/6 |
| Throughput | 1.95 req/s |
| Token throughput | 318 tok/s |

---

## Next Actions

1. **Start 3 server instances** on ports 8081, 8082, 8083
2. **Run benchmark** comparing all models
3. **Update OpenCode config** for multi-port fallback
4. **Implement load balancer** for intelligent routing

---

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1 | 2-4 hours | 3 running servers |
| Phase 2 | 4-8 hours | Load balancer |
| Phase 3 | 1-2 days | Tool calling |
| Phase 4 | Ongoing | Monitoring |

---

## References

- Research: `bg_4082662b` (GGUF threading)
- Research: `bg_b68c3c3d` (concurrency docs)
- Research: `bg_993f821a` (architecture)
- Benchmark tool: `comprehensive_benchmark.py`

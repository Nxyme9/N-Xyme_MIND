# Frankenstein Engine - Master Plan v1.0

## Features to Add

### 1. Dynamic Batch Sizing
**Goal**: Auto-adjust `-np` based on queue depth

**How it works**:
- Monitor request queue (std::deque)
- If queue > N, increase batch size
- If queue empty, decrease to save GPU
- Smooth transitions (no thrashing)

**Implementation**:
```
main.cpp + queue_monitor thread
    ├── check_queue_size()
    ├── target_np = f(queue_size, gpu_util)
    └── gradual NP change (not abrupt)
```

**Files to modify**: `engine.cpp` (add queue logic)

---

### 2. KV Cache Optimization
**Goal**: Better memory management for long contexts

**How it works**:
- Pre-allocate larger KV cache
- Smart eviction (not LRU, but importance-based)
- Flash Attention already enabled (default)
- `--kv-unified` already set (from testing)

**Implementation**:
- Tune `-c` (context size) per model
- Add `--cache-ram` management
- Layer-wiseKV offloading options

**Key flags to expose**:
- `-c N` (context)
- `--cache-ram N` (RAM cache size)
- `--kv-unified` (already working)

---

### 3. Multiple Model Hot-Swap
**Goal**: Switch models without restart

**How it works**:
- Keep multiple `llama_model*` in memory
- HTTP endpoint to switch active model
- Or CLI flag to hot-swap

**Implementation**:
```
struct Engine {
    std::map<std::string, llama_model*> models;
    llama_model* active_model;
    // switch: active_model = models["new_model"]
}
```

**Files**: New `engine-multi.cpp` or extend `engine.cpp`

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    frankenstein-engine                        │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│  │   Queue     │───▶│  Scheduler  │───▶│   Batch     │       │
│  │  Monitor    │    │  (dynamic)  │    │  Processor  │       │
│  └─────────────┘    └─────────────┘    └─────────────┘       │
│        │                   │                  │              │
│        ▼                   ▼                  ▼              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │              llama_model (GPU offloaded)             │     │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐              │     │
│  │  │ Model A │  │ Model B │  │ Model C │  (hot-swap)   │     │
│  │  └─────────┘  └─────────┘  └─────────┘              │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Priority Order

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| 1 | Dynamic Batch Sizing | Medium | High |
| 2 | KV Cache Tuning | Low | Medium |
| 3 | Multi-Model Hot-Swap | High | High |

---

## Next Steps

1. **Dynamic Batch** - Start with queue monitoring
2. **Test each feature** - Verify before adding next
3. **Benchmark after each** - Compare vs current 1,711 tok/s

---

*Plan created: 2026-04-09*
*Status: Ready to implement*
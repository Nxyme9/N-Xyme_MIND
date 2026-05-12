# Frankenstein Engine v2.0 - Master Plan

> **Vision**: Build a production-ready local LLM inference server with slot management, OpenAI API compatibility, streaming, and all the bells and whistles.

---

## Executive Summary

| Component | Current State | Target State |
|-----------|---------------|--------------|
| **Slot Management** | ❌ None (ThreadedHTTPServer) | ✅ 8 slots with priority queue |
| **OpenAI API** | ⚠️ Basic (/v1/chat) | ✅ Full compatibility |
| **Streaming** | ❌ No SSE | ✅ Server-Sent Events |
| **Queue** | ❌ None | ✅ Priority queue |
| **Deployment** | ❌ Manual | ✅ CLI + systemd |

---

## Phase 1: Slot Management (Week 1)

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frankenstein Engine v2                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Request Queue (Priority)                                    │
│  ┌─────────────────────────────────────────┐                │
│  │ High Priority (1-2)  │ Standard (3-8)    │                │
│  └─────────────────────────────────────────┘                │
│           ↓                    ↓                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│  │  Slot 1   │  │  Slot 2   │  │  Slot N    │   (8 slots)  │
│  │  (async)   │  │  (async)  │  │  (async)  │              │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘              │
│        │              │               │                       │
│        └──────────────┴───────────────┘                       │
│                       │                                       │
│              ┌────────▼────────┐                             │
│              │  Shared Model   │  ← One Llama instance       │
│              │  (llama-cpp)    │    with KV cache per slot   │
│              └─────────────────┘                             │
└─────────────────────────────────────────────────────────────┘
```

### Slot States

```
idle ──(request)──> loading ──(model ready)──> processing ──(streaming)──> done ──(release)──> idle
                      │                              │
                      └──────(timeout 5min)──────────┘
```

### Implementation Tasks

| Task | File | Priority |
|------|------|----------|
| Create `SlotManager` class | `nx_engine/server/slot_manager.py` | P0 |
| Implement slot state machine | `nx_engine/server/slots.py` | P0 |
| Add priority queue | `nx_engine/server/queue.py` | P0 |
| Integrate with direct_pipeline | `nx_engine/server/__init__.py` | P1 |

---

## Phase 2: OpenAI API (Week 2)

### Endpoints

| Endpoint | Method | Streaming | Description |
|----------|--------|-----------|-------------|
| `/v1/chat/completions` | POST | ✅ SSE | Chat completion |
| `/v1/completions` | POST | ✅ SSE | Text completion |
| `/v1/embeddings` | POST | ❌ | Embedding generation |
| `/v1/models` | GET | — | List models |
| `/slots` | GET | — | Slot status |
| `/health` | GET | — | Health check |

### SSE Streaming Format

```python
# Server response
data: {"id":"chat-abc","choices":[{"delta":{"content":"Hello"},"index":0}]}

data: {"id":"chat-abc","choices":[{"delta":{"content":" world"},"index":0}]}

data: [DONE]
```

### Implementation Tasks

| Task | File | Priority |
|------|------|----------|
| FastAPI scaffold | `nx_engine/server/api.py` | P0 |
| /v1/chat/completions | `nx_engine/server/api.py` | P0 |
| SSE streaming | `nx_engine/server/streaming.py` | P0 |
| /v1/embeddings | `nx_engine/server/api.py` | P1 |
| /v1/models | `nx_engine/server/api.py` | P1 |

---

## Phase 3: Performance (Week 3)

### Optimization Targets

| Metric | Target | Current |
|--------|--------|---------|
| Throughput | 162+ tok/s | 162 tok/s |
| Concurrent slots | 8 | — |
| Latency (p50) | <100ms | — |
| Cold start | <3s | ~10s |

### Optimizations

1. **Pre-load models** at startup (not lazy)
2. **KV cache quantization** (`--cache-type-k q8_0`)
3. **Continuous batching** via llama.cpp
4. **TCP_NODELAY** for low latency

### Implementation Tasks

| Task | Priority |
|------|----------|
| Model pre-loader | P1 |
| KV cache optimization config | P2 |
| Metrics endpoint | P2 |

---

## Phase 4: Deployment (Week 4)

### CLI Commands

```bash
# Start server
frankenstein serve --port 8080 --slots 8

# List models
frankenstein models

# Check status
frankenstein status

# Hot-swap model
frankenstein load qwen2.5-coder-7b-q4_k_m.gguf

# Health check
frankenstein health
```

### Systemd Service

```ini
[Unit]
Description=Frankenstein Engine v2
After=network.target

[Service]
Type=simple
User=%u
ExecStart=/usr/local/bin/frankenstein serve --port 8080 --slots 8
Restart=on-failure

[Install]
WantedBy=default.target
```

### Implementation Tasks

| Task | Priority |
|------|----------|
| CLI tool with click | P1 |
| systemd unit file | P2 |
| Health checks | P1 |

---

## File Structure

```
nx_engine/
├── __init__.py
├── config.py                    # ✅ Done
├── local_llm/
│   ├── direct_pipeline.py       # ✅ Done
│   ├── rosetta_executor.py
│   └── brain.py
├── server/                      # NEW
│   ├── __init__.py
│   ├── slot_manager.py          # P0
│   ├── slots.py                 # P0
│   ├── queue.py                 # P0
│   ├── api.py                   # P0 (FastAPI)
│   ├── streaming.py             # P0
│   └── cli.py                   # P1
└── pyproject.toml
```

---

## Dependencies

```toml
[project]
name = "frankenstein-engine"
version = "2.0.0"
dependencies = [
    "llama-cpp-python>=0.2.0",
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.0.0",
    "click>=8.0.0",
    "numpy>=1.24.0",
]
```

---

## Key Decisions (Oracle Recommendation)

| Decision | Choice | Rationale |
|----------|--------|----------|
| **Web Framework** | FastAPI | Async-native, SSE built-in, OpenAPI docs |
| **Slot Count** | 8 | llama-server default, balances VRAM |
| **Queue Strategy** | Priority + FIFO | Latency-critical vs throughput |
| **Process Model** | Shared instance | GPU efficient, KV reuse |
| **Persistence** | None (stateless) | Simpler, no stale state |

---

## Success Metrics

- [ ] 8 concurrent slots working
- [ ] `/v1/chat/completions` returns valid JSON
- [ ] Streaming works (SSE)
- [ ] 162+ tok/s maintained
- [ ] CLI tool functional
- [ ] systemd service works

---

## References

- **llama.cpp server**: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- **llama-cpp-python server**: https://llama-cpp-python.readthedocs.io/en/latest/server/
- **OpenAI API**: https://platform.openai.com/docs/api-reference

---

*Generated: 2026-04-13*
*Based on: Parallel research (explore + librarian + oracle)*

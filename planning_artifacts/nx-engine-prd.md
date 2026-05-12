# Frankenstein Engine PRD

> **Project**: Frankenstein Engine (nx_engine)  
> **Version**: 2.0.0  
> **Status**: Brownfield - Code Already Exists  
> **Last Updated**: 2026-04-26

---

## 1. Executive Summary

**Frankenstein Engine** is a portable high-performance local LLM inference engine built from scratch with direct GGUF loading. It outperforms Ollama by **14x** in throughput (471+ tokens/sec vs 34) with **64ms** latency vs 412ms, featuring native real-time tool calling capability.

### Key Differentiators
- **Zero Network Overhead**: Direct llama-cpp-python bindings (no HTTP proxy)
- **True Parallel**: 8-16 concurrent slots with continuous batching
- **Tool Calling**: Native `--tools all` support
- **Auto-Routing**: Routes tasks to optimal model (0.5B→7B) based on complexity
- **Graceful Degradation**: Automatic fallback when components fail
- **Health Monitoring**: GPU, system, and server health checks

---

## 2. Problem Statement

### Current Pain Points

| Problem | Existing Solution | Frankenstein Fix |
|---------|-----------------|-----------------|
| Ollama limited tok/sec (34) | N/A | 14x faster (471+ tok/sec) |
| High latency (412ms) | N/A | 6.4x lower (64ms) |
| No real tool calling | Limited | Native tool calling |
| HTTP overhead | llama-server proxy | Direct Python bindings |
| Static model selection | Manual selection | Auto-routing by complexity |
| No health degradation | Basic health check | Graceful degradation |

### Market Need
- Developers need local LLM inference without cloud dependency
- Privacy-sensitive applications require on-premise AI
- High-throughput coding assistants (471+ tok/sec for real-time completion)
- Tool/capability calling for agentic workflows

---

## 3. Target Users

| User Segment | Use Case | Priority |
|-------------|--------|----------|
| **AI Developers** | Local coding assistants, IDE plugins | P0 |
| **Privacy-First Users** | On-premise AI, no cloud | P0 |
| **Research Teams** | Custom LLM fine-tuning, experiments | P1 |
| **Edge Deployment** | Local hardware inference | P1 |
| **Enterprise** | Private AI infrastructure | P2 |

---

## 4. User Stories

| ID | Story | Acceptance Criteria |
|----|-------|----------------|
| **US-01** | As a developer, I want to generate text with a single API call | `client.generate("prompt")` returns text |
| **US-02** | As a developer, I want auto-routing based on task complexity | `router.route("fix bug")` returns optimal model |
| **US-03** | As an operator, I want health monitoring | `HealthMonitor().check_all()` returns GPU/CPU/memory status |
| **US-04** | As an operator, I want automatic fallback when GGUF fails | Failed model auto-switches to fallback |
| **US-05** | As a user, I want streaming responses | `stream=True` returns Server-Sent Events |
| **US-06** | As a user, I want OpenAI-compatible API | `/v1/chat/completions` matches OpenAI spec |
| **US-07** | As a developer, I want CLI interface | `frankenstein generate "prompt"` works |
| **US-08** | As a developer, I want embedding generation | `embed("text")` returns vector |
| **US-09** | As an operator, I want slot management | Queue-based concurrent request handling |
| **US-10** | As a developer, I want tool calling | `tools` parameter enables function calls |

---

## 5. Functional Requirements

### 5.1 Core Engine (nx_engine/engine/)

| ID | Requirement | Description |
|----|------------|-------------|
| **F-01** | Direct GGUF Loading | Load GGUF models via llama-cpp-python without HTTP |
| **F-02** | Text Generation | `DirectLlamaClient().generate()` returns text |
| **F-03** | Chat Completion | OpenAI-compatible `/v1/chat/completions` |
| **F-04** | Streaming | Server-Sent Events for token streaming |
| **F-05** | Tool Calling | Parse and execute tool calls from model output |
| **F-06** | Embeddings | Generate embeddings via `embed_model` |
| **F-07** | LoRA Adapter Hot-Swap | Runtime adapter switching with GPU OOM protection |

### 5.2 Router (nx_engine/router/)

| ID | Requirement | Description |
|----|------------|-------------|
| **F-10** | Complexity Analysis | Classify task as simple/medium/complex |
| **F-11** | Model Routing | Route to optimal model (0.5B/7B) |
| **F-12** | Category Detection | Detect coding/reasoning/creative/math categories |
| **F-13** | Circuit Breaker | Open circuit after N failures, auto-recover |

### 5.3 Health Monitor (nx_engine/health/)

| ID | Requirement | Description |
|----|------------|-------------|
| **F-20** | Server Health | Check GGUF llama-server /health endpoint |
| **F-21** | GPU Monitoring | Temperature, VRAM, utilization |
| **F-22** | System Monitoring | CPU, memory, disk |
| **F-23** | Slot Availability | Track available inference slots |
| **F-24** | Degraded Mode | Activate fallback when health < threshold |
| **F-25** | Prometheus Metrics | Export /metrics for Prometheus |

### 5.4 Server (nx_engine/server/)

| ID | Requirement | Description |
|----|------------|-------------|
| **F-30** | FastAPI Server | OpenAI-compatible REST API |
| **F-31** | Slot Manager | 8-16 concurrent request slots |
| **F-32** | Request Queue | Queue-based batch processing |
| **F-33** | Priority Queue | High/normal/low priority levels |
| **F-34** | Continuous Batching | Dynamic batch assembly |

### 5.5 CLI (nx_engine/cli.py)

| ID | Requirement | Command |
|----|------------|--------|
| **F-40** | Generate | `frankenstein generate "prompt"` |
| **F-41** | Route | `frankenstein route "task"` |
| **F-42** | Health | `frankenstein health` |
| **F-43** | List Models | `frankenstein models` |
| **F-44** | Embed | `frankenstein embed "text"` |

---

## 6. Non-Functional Requirements

| ID | Requirement | Target | Priority |
|----|------------|--------|--------|
| **N-01** | Throughput | 471+ tokens/sec | P0 |
| **N-02** | Latency | <100ms first token | P0 |
| **N-03** | Concurrent Slots | 8-16 | P0 |
| **N-04** | Context Window | 8192 (131K extended) | P1 |
| **N-05** | GPU Utilization | 96%+ | P1 |
| **N-06** | Startup Time | <5s cold start | P1 |
| **N-07** | Memory (VRAM) | <12GB | P2 |
| **N-08** | Multi-GPU | Layer distribution | P2 |

---

## 7. Technical Architecture

### 7.1 Module Structure

```
nx_engine/
├── config.py              # FrankensteinConfig (Pydantic BaseSettings)
├── __init__.py           # Public API exports
├── compatibility.py      # Drop-in replacements
├── exceptions.py       # Custom exceptions
│
├── engine/             # Direct GGUF client
│   ├── __init__.py    # DirectLlamaClient, GPUMemoryManager
│   └── unified.py     # Unified client interface
│
├── router/             # Auto-routing
│   ├── __init__.py    # RouterBrain, LocalModelComplexityAnalyzer
│   └── ...
│
├── health/            # Health monitoring
│   ├── __init__.py    # HealthMonitor, get_health_monitor
│   └── ...
│
├── server/            # FastAPI server
│   ├── api.py        # FastAPI app, endpoints
│   ├── slot_manager.py # SlotManager, QueueFullError
│   ├── slots.py     # Slot tracking
│   ├── queue.py    # PriorityQueue
│   └── cli.py      # CLI entry point
│
├── adapters/          # LoRA adapter management
│   └── ...
│
└── local_llm/        # Local model clients
    ├── brain.py      # BrainClient
    ├── router.py    # ModelRouter
    └── ...
```

### 7.2 Data Flow

```
User Request
    ↓
[1] Router (analyzes complexity)
    ↓
[2] Model Selection (0.5B/7B)
    ↓
[3] Slot Manager (allocates slot)
    ↓
[4] DirectLlamaClient (loads GGUF, infers)
    ↓
[5] Tool Parser (if tools enabled)
    ↓
Response / Stream
```

### 7.3 Component Interactions

| Component | Responsibilities | Public API |
|-----------|---------------|----------|
| **DirectLlamaClient** | GGUF loading, inference, tool calling | `generate()`, `chat()`, `embed()` |
| **RouterBrain** | Complexity analysis, model routing | `route(task)` → `{complexity, model}` |
| **HealthMonitor** | Health checks, degradation | `check_all()` → `HealthStatus[]` |
| **SlotManager** | Concurrent slot allocation | `acquire()`, `release()`, `queue()` |
| **Slot** | Request context, timeout | `state`, `request`, `response` |

---

## 8. API Design

### 8.1 Chat Completions

**Endpoint**: `POST /v1/chat/completions`

```json
// Request
{
  "model": "qwen2.5-coder-7b-q4_k_m",
  "messages": [
    {"role": "system", "content": "You are a coding assistant."},
    {"role": "user", "content": "Write a hello world function"}
  ],
  "temperature": 0.7,
  "max_tokens": 2048,
  "stream": false,
  "tools": [{"type": "function", "function": {...}}]
}

// Response
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "qwen2.5-coder-7b-q4_k_m",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "def hello(): print('Hello, World!')"},
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60}
}
```

### 8.2 Embeddings

**Endpoint**: `POST /v1/embeddings`

```json
// Request
{
  "model": "nomic-embed-text-v1.5-q4_k_m",
  "input": "The quick brown fox"
}

// Response
{
  "object": "list",
  "data": [{"object": "embedding", "embedding": [0.123, ...], "index": 0}],
  "usage": {"prompt_tokens": 5, "total_tokens": 5}
}
```

### 8.3 Health

**Endpoint**: `GET /health`

```json
{
  "status": "healthy",
  "gpu": {"temp": 65, "util": 96, "mem_mb": 11200},
  "slots": {"used": 4, "available": 12, "total": 16},
  "model": "qwen2.5-coder-7b-q4_k_m"
}
```

### 8.4 Slots

**Endpoint**: `GET /slots`

```json
{
  "slots": [
    {"id": 0, "state": "idle"},
    {"id": 1, "state": "generating", "request_id": "..."},
    {"id": 2, "state": "queued", "queue_position": 1}
  ]
}
```

---

## 9. Configuration

All configuration via `FrankensteinConfig` (Pydantic BaseSettings):

### 9.1 Environment Variables

| Variable | Default | Description |
|----------|---------|-----------|
| `FRANKENSTEIN_MODELS_DIR` | `models/` | GGUF models directory |
| `FRANKENSTEIN_LLAMA_SERVER_PORT` | `8080` | Server port |
| `FRANKENSTEIN_DEFAULT_MODEL` | `qwen2.5-coder-7b-q4_k_m` | Primary model |
| `FRANKENSTEIN_N_GPU_LAYERS` | `-1` | GPU layers (-1=all) |
| `FRANKENSTEIN_N_CTX` | `8192` | Context window |
| `FRANKENSTEIN_N_THREADS` | `16` | CPU threads |

### 9.2 Feature Flags

| Flag | Default | Description |
|------|---------|-----------|
| `enable_rosetta_fast_mode` | `true` | Use 0.5B for simple tasks |
| `enable_embeddings` | `true` | Enable embedding API |
| `enable_health_monitoring` | `true` | Health checks |
| `enable_circuit_breaker` | `true` | Auto-retry logic |
| `auto_fallback` | `true` | Fallback on failure |

### 9.3 Advanced Settings

| Setting | Default | Description |
|---------|---------|-----------|
| `speculative_decoding` | `false` | Speculative token prediction |
| `cont_batching` | `true` | Continuous batching |
| `kv_cache_persist` | `true` | Persist KV cache to disk |
| `rope_scaling_type` | `yarn` | YaRN context extension |
| `rope_scale` | `4.0` | 4x context (32K→131K) |

---

## 10. Dependencies

### 10.1 Core

```
llama-cpp-python>=0.2.0
requests>=2.31.0
aiohttp>=3.9.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sse-starlette>=2.0.0
click>=8.1.0
```

### 10.2 Optional

```
# GPU
llama-cpp-python[gpu]>=0.2.0

# Development
pytest>=7.0
pytest-asyncio>=0.21
ruff>=0.1.0
pytest-cov>=4.0

# Embeddings (full)
sentence-transformers>=2.0
torch>=2.0
```

### 10.3 System Requirements

- **Python**: 3.10+
- **GPU**: CUDA-capable (optional)
- **RAM**: 16GB+ recommended
- **VRAM**: 12GB+ (RTX 3080 Ti optimized)

---

## 11. Success Metrics

### 11.1 Performance Targets

| Metric | Target | Current (Ollama) |
|--------|--------|-----------------|
| Tokens/sec | 471+ | 34 |
| First token latency | <100ms | 412ms |
| Concurrent slots | 8-16 | 4 |
| GPU utilization | 96%+ | ~50% |

### 11.2 Reliability Targets

| Metric | Target |
|--------|--------|
| Uptime | 99.9% |
| Health check accuracy | 100% |
| Fallback switch time | <5s |
| Recovery time | <30s |

### 11.3 Quality Targets

| Metric | Target |
|--------|--------|
| Routing accuracy | >90% |
| Tool call success | >95% |
| API compatibility | OpenAI 100% |

---

## 12. Testing

### 12.1 Test Files

```
tests/
├── test_engine.py     # DirectLlamaClient tests
├── test_router.py   # RouterBrain tests
├── test_health.py  # HealthMonitor tests
└── test_config.py  # Config validation
```

### 12.2 Benchmark Files

```
benchmark_compare.py    # Frankenstein vs Ollama
benchmark_frankenstein.py  # Frankenstein-only
benchmark_llama_server.py  # llama-server benchmarks
```

---

## 13. CLI Reference

### 13.1 Commands

```bash
# Generate text
frankenstein generate "Your prompt here"

# Route a task
frankenstein route "fix the bug in login.py"

# Check health
frankenstein health

# List models
frankenstein models

# Generate embeddings
frankenstein embed "Your text here"

# Start server
frankenstein-server --host 0.0.0.0 --port 8080
```

### 13.2 Python API

```python
from nx_engine import (
    DirectLlamaClient,
    RouterBrain,
    HealthMonitor,
)

# Generate
client = DirectLlamaClient()
response = client.generate("Hello!")

# Route
router = RouterBrain()
result = router.route("fix the bug")
print(result)  # {'complexity': 'complex', 'model': 'qwen2.5-coder-7b-q4_k_m'}

# Health
monitor = HealthMonitor()
print(monitor.show_status())
```

---

## 14. Roadmap (Future)

| Phase | Feature | Priority |
|-------|---------|---------|
| v2.1 | Multi-GPU layer distribution | P2 |
| v2.2 | Speculative decoding | P2 |
| v2.3 | KV cache persistence | P2 |
| v2.4 | LoRA adapters | P3 |
| v2.5 | Vision models | P3 |

---

## Appendix A: File Manifest

| Path | Purpose |
|------|---------|
| `nx_engine/config.py` | FrankensteinConfig settings |
| `nx_engine/__init__.py` | Public API |
| `nx_engine/engine/__init__.py` | DirectLlamaClient |
| `nx_engine/router/__init__.py` | RouterBrain |
| `nx_engine/health/__init__.py` | HealthMonitor |
| `nx_engine/server/api.py` | FastAPI server |
| `nx_engine/server/slot_manager.py` | Slot manager |
| `nx_engine/cli.py` | CLI interface |
| `pyproject.toml` | Package metadata |
| `frankenstein.cpp` | C++ inference core |
| `frankenstein.hpp` | C++ header |

---

## Appendix B: Benchmark Results

From `benchmark_results.json`:

| Model | Tokens/sec | Latency |GPU Util |
|-------|----------|--------|--------|
| qwen2.5-0.5b | 1,341+ | 32ms | 96% |
| qwen2.5-coder-7b | 471+ | 64ms | 96% |

Vs Ollama: **14x** throughput, **6.4x** latency improvement.

---

*Document Status: Brownfield - Existing code at `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_engine/`*
*Created: 2026-04-26*
# Frankenstein Engine Architecture

> **Document Type**: Architecture Specification  
> **Project**: nx_engine (Frankenstein Engine)  
> **Version**: 2.0.0  
> **Status**: Brownfield Documentation  
> **Date**: 2026-04-26

---

## 1. Architecture Principles

The Frankenstein Engine follows these foundational architectural principles:

### 1.1 Direct Execution (No Network Overhead)

- **Direct GGUF Loading**: Uses `llama-cpp-python` Python bindings instead of HTTP servers
- **Zero HTTP overhead**: No intermediate server when using `DirectLlamaClient`
- **Memory-mapped loading**: Models loaded directly via `llama_cpp.Llama` class

### 1.2 Auto-Routing by Complexity

- **Complexity-based routing**: Tasks routed to optimal model based on estimated complexity
- **Local model priority**: Uses local GGUF models before external APIs
- **Dual-model architecture**:
  - `ROSETTA_MODEL` (0.5B) for simple/fast tasks
  - `DEFAULT_MODEL` (7B) for complex reasoning

### 1.3 Health Monitoring & Graceful Degradation

- **Continuous health monitoring**: Checks GPU, system, server, slots
- **Degraded mode**: Automatic fallback when components fail
- **Circuit breaker pattern**: Prevents cascading failures

### 1.4 Modular Design

| Module | Responsibility |
|-------|---------------|
| `engine/` | Direct GGUF loading via llama-cpp-python |
| `router/` | Task complexity analysis & routing |
| `health/` | Health checks & degradation |
| `server/` | FastAPI with slot management |
| `local_llm/` | Brain, model pool, tool calling |
| `dictate/` | Voice dictation features |
| `trainer/` | Model training |

### 1.5 Thread Safety

- **Global singleton pattern**: `get_global_client()`, `get_health_monitor()`
- **RLock for adapter switching**: Thread-safe LoRA hot-swap
- **Lock-protected caches**: Thread-safe caching in router

---

## 2. Component Architecture

### 2.1 Core Components

```
nx_engine/
├── __init__.py          # Package exports (v2.0.0)
├── config.py           # Pydantic-based configuration
├── cli.py            # CLI entry point
├── compatibility.py   # Drop-in replacement API
├── exceptions.py     # Custom exceptions
├── adapters/         # LoRA adapter registry
│
├── engine/           # Direct GGUF loading
│   ├── __init__.py   # DirectLlamaClient, tool parsing
│   ├── unified.py    # Unified interface
│   └── whisper.py    # Whisper integration
│
├── router/          # Auto-routing
│   └── __init__.py   # RouterBrain, LocalModelComplexityAnalyzer
│
├── health/         # Health monitoring
│   └── __init__.py   # HealthMonitor, get_health_monitor()
│
├── server/         # FastAPI server
│   ├── __init__.py   # Server exports
│   ├── api.py       # FastAPI app
│   ├── slots.py     # Slot management
│   ├── queue.py    # Request queue
│   ├── slot_manager.py  # Slot manager
│   └── cli.py       # Server CLI
│
├── local_llm/      # Brain & model pool
│   ├── brain.py     # Brain wrapper
│   ├── brain_pool.py # Model pool
│   ├── brain_router.py # Model router
│   ├── tool_caller.py # Tool calling
│   └── ...
│
├── dictate/         # Dictation
│   ├── __init__.py   # DictationApp (lazy import)
│   ├── dictate_app.py # Main application
│   ├── core/        # Core engine
│   ├── audio.py     # Audio processing
│   ├── tts.py      # Text-to-speech
│   └── ...
│
└── trainer/        # Training
    └── __init__.py
```

### 2.2 DirectLlamaClient (engine/)

**Purpose**: Direct GGUF loading without HTTP overhead

**Key Classes**:
```python
class DirectLlamaClient:
    """Direct llama-cpp-python client - no HTTP"""
    
    # GPU memory management
    _adapter_lock: threading.RLock  # Thread-safe adapter switching
    
    # Initialization
    def __init__(
        self,
        model_path: str = None,       # Auto-detect from config
        n_gpu_layers: int = None,      # -1 = all to GPU
        n_ctx: int = None,          # 8192 default
        n_threads: int = None,       # 16 default
        adapter_name: str = None,     # LoRA adapter name
        allow_fallback: bool = True,  # CPU fallback on OOM
    )
    
    # Core methods
    def generate(self, prompt, system_prompt=None, **kwargs) -> str
    def chat(self, messages, **kwargs) -> Dict
    def embed(self, text) -> List[float]
    def get_token_count(self, text) -> int
    
    # Adapter management (thread-safe)
    def hot_swap_adapter(self, adapter_name: str) -> Tuple[bool, str]
    def swap_to(self, adapter_name: str) -> "DirectLlamaClient"
    
    # Alias
    LocalLLM = DirectLlamaClient
```

**Tool Call Parsing** (`engine/__init__.py`):
- `<tool_call>tool_name(args)</tool_call>` format
- `[TOOL_CALL]{tool => "name", args => {...}}[/TOOL_CALL]` format
- JSON `{name, arguments}` format

### 2.3 RouterBrain (router/)

**Purpose**: Auto-route tasks to optimal model

**Key Classes**:
```python
class RouterBrain:
    def __init__(self, use_llm: bool = False, ...):
        self.llama_server_url: str   # config.LLAMA_SERVER_URL
        self.model: str            # config.DEFAULT_MODEL
        self._llm_cache: OrderedDict  # TTL cache
    
    # Main method
    def route(self, prompt, system_prompt="", agent_type="") -> dict
    """Returns: {categories, complexity, recommended_model, routing_method}"""
    
    # LLM-based routing (slower, more accurate)
    def route_with_llm(self, prompt, ...) -> dict
    
    # Internal methods
    def _detect_categories(self, prompt) -> List[str]
    def _estimate_complexity(self, prompt, system_prompt) -> str  # simple/medium/complex
    def _analyze_with_llm(self, prompt, ...) -> dict
    def _route_keyword(self, prompt, ...) -> dict
```

**Category Detection** (`CATEGORY_KEYWORDS`):
| Category | Keywords |
|---------|----------|
| coding | code, function, bug, fix, refactor |
| reasoning | reason, logic, explain, why, analyze |
| creative | write, story, poem, brainstorm |
| math | calculate, equation, algorithm |
| summarization | summarize, summary, extract |
| analysis | analyze, investigate, review |

**Complexity Estimation**:
- `simple`: < 100 chars (uses ROSETTA_MODEL)
- `medium`: 100-500 chars
- `complex`: > 500 chars (uses DEFAULT_MODEL)

### 2.4 HealthMonitor (health/)

**Purpose**: Health monitoring with graceful degradation

**Key Classes**:
```python
class HealthMonitor:
    DEFAULT_GPU_TEMP_THRESHOLD = 85
    DEFAULT_VRAM_THRESHOLD_MB = 11000
    DEFAULT_LOAD_THRESHOLD = 16
    DEFAULT_MEM_THRESHOLD_RATIO = 0.9
    
    def __init__(self, url=None, check_interval=None, ...):
        self.url: str                    # config.LLAMA_SERVER_URL
        self.check_interval: float       # config.HEALTH_CHECK_INTERVAL
        self.health_threshold_ratio: float # 0.7
        self.degraded_mode: bool = False
    
    # Health checks
    def check_llama_server(self) -> HealthStatus
    def check_gpu(self) -> HealthStatus     # temp, util, mem_mb
    def check_system(self) -> HealthStatus  # load, memory
    def check_slots(self) -> HealthStatus   # idle slots
    def check_all(self) -> List[HealthStatus]
    
    # Degradation
    def is_degraded(self) -> bool
    def record_health(self, component: str, healthy: bool)
    
    # Monitoring loop
    def start(self)
    def stop(self)
    
    # Output
    def show_status(self) -> str  # Formatted status
    def get_prometheus_metrics(self) -> str
```

**HealthStatus dataclass**:
```python
@dataclass
class HealthStatus:
    name: str           # Component name
    healthy: bool      # Health state
    message: str      # Status message
    latency_ms: float = 0.0
    last_check: Optional[datetime] = None
```

### 2.5 Server Components (server/)

**Purpose**: FastAPI server with slot management

| Component | File | Responsibility |
|-----------|------|-------------|
| `app` | `api.py` | FastAPI application |
| `Slot` | `slots.py` | Slot representation |
| `SlotStateMachine` | `slots.py` | Slot state machine |
| `RequestQueue` | `queue.py` | Request queuing |
| `RequestScheduler` | `queue.py` | Priority scheduling |
| `SlotManager` | `slot_manager.py` | Global slot manager |

**API Endpoints** (inferred from llama.cpp server compatibility):
- `GET /health` - Health check
- `GET /slots` - Slot availability
- `POST /completion` - Text completion
- `POST /chat/completion` - Chat completion
- `POST /embeddings` - Embedding generation

### 2.6 Brain (local_llm/brain.py)

**Purpose**: Unified API for local GGUF inference

```
Brain
├── Model pool management (lazy load/auto-unload)
├── VRAM management (1GB headroom)
├── Text completion
├── Chat completion
├── Embeddings
└── Tool calling support
```

**Model Aliases**:
```python
MODEL_ALIASES = {
    "7b": DEFAULT_MODEL,      # qwen2.5-coder-7b-q4_k_m
    "0.5b": ROSETTA_MODEL,   # qwen2.5-0.5b-instruct-q4_k_m
    "fast": ROSETTA_MODEL,
    "rosetta": ROSETTA_MODEL,
    "embed": EMBED_MODEL,     # nomic-embed-text-v1.5-Q4_K_M
}
```

### 2.7 Dictation Module (dictate/)

**Purpose**: Voice-to-code dictation features

| Component | File | Purpose |
|-----------|------|---------|
| `DictationApp` | `dictate_app.py` | Main application |
| `DictationEngine` | `core/engine.py` | Core dictation engine |
| `AudioPipeline` | `core/audio.py` | Audio processing |
| `TTS` | `tts.py` | Text-to-speech |
| `Hotword` | `hotword.py` | Hotkey detection |
| `StateMachine` | `core/state.py` | State management |

---

## 3. Data Flow

### 3.1 Text Generation Flow

```
User Input
    │
    ▼
RouterBrain.route(prompt)  ───────┐
    │                           │
    │ Complexity Analysis       │
    │ Category Detection     │
    │                           │
    ▼                           │
DirectLlamaClient.generate()  ◄────┘
    │
    ├── LoRA Adapter (if configured)
    ├── GPU Layers (n_gpu_layers)
    └── RAG Context (if enabled)
    │
    ▼
Model Response + Tool Calls (if any)
    │
    ▼
Tool Call Parsing
<tool_call>format → execute → wrap_tool_result()
    │
    ▼
Final Response
```

### 3.2 Health Monitoring Flow

```
HealthMonitor.check_all()
    │
    ├── check_llama_server() → GET /health
    ├── check_gpu() → nvidia-smi
    ├── check_system() → /proc/loadavg, free
    └── check_slots() → GET /slots
    │
    ▼
HealthStatus List
    │
    ▼
record_health() → health_history[component]
    │
    ▼
is_degraded() ──→ degraded_mode = True if ratio < 0.7
    │
    ▼
show_status() / get_prometheus_metrics()
```

### 3.3 Request Flow (Server Mode)

```
HTTP Request
    │
    ▼
FastAPI (server/api.py)
    │
    ▼
SlotManager.find_available_slot()
    │
    ├── Slot available ──→ Process request
    │
    └── No slot ──→ RequestQueue.enqueue()
                    │
                    ▼
              RequestScheduler.schedule()
                    │
                    ▼
              Process when slot available
```

---

## 4. API Design

### 4.1 Public API (nx_engine/__init__.py)

```python
# Config
from nx_engine import config

# Engine
from nx_engine.engine import (
    DirectLlamaClient,    # Main client
    LocalLLM,          # Alias
    ChatResponse,       # Response dataclass
    ToolCall,          # Tool call dataclass
    get_global_client,
    call_llama_direct,
    parse_tool_calls,
    wrap_tool_result,
)

# Router
from nx_engine.router import (
    RouterBrain,
    LocalModelComplexityAnalyzer,
)

# Health
from nx_engine.health import (
    HealthMonitor,
    get_health_monitor,
)

# Compatibility (drop-in replacement)
from nx_engine.compatibility import (
    get_embedding,
    translate_to_tool_call,
    run_reasoning,
    get_embedding_client,
    DirectToolExecutor,
    process_request,
)
```

### 4.2 CLI Commands (cli.py)

```bash
# Generate text
frankenstein generate "Your prompt"

# Route task
frankenstein route "fix the bug"

# Health check
frankenstein health

# List models
frankenstein models

# Generate embeddings
frankenstein embed "Your text"

# Adapter management
frankenstein adapters list
frankenstein adapters load <name>
frankenstein adapters swap <name>
```

### 4.3 Server API (OpenAI-Compatible)

```python
# Chat Completion
POST /v1/chat/completion
{
    "model": "qwen2.5-coder-7b-q4_k_m",
    "messages": [{"role": "user", "content": "Hello"}],
    "temperature": 0.7,
    "max_tokens": 2048
}

# Text Completion
POST /v1/completion
{
    "model": "qwen2.5-coder-7b-q4_k_m",
    "prompt": "Hello",
    "temperature": 0.7
}

# Embeddings
POST /v1/embeddings
{
    "model": "nomic-embed-text-v1.5-Q4_K_M",
    "input": "Your text"
}

# Models
GET /v1/models
```

---

## 5. State Machine

### 5.1 Slot States (server/slots.py)

```
Slot State Machine:
┌─────────┐
│ CREATED  │ ──→ LOADING ──→ IDLE ──→ PROCESSING ──→ COMPLETED
│         │    │         │         │              │
│         │    │         │         │              ▼
│         │    │         │         │            ERROR ──→ IDLE
│         │    │         │         │
│         │    │         │         │ ◄──────────────┘
│         │    ▼         ▼         │
│         └── PAUSED ◄──────┘         │
│              (on pause)              │
└────────────────────────────────────┘
```

### 5.2 Health State

```
Normal Mode:
  - All components healthy (ratio ≥ 0.7)
  - Full capability

Degraded Mode:
  - Components unhealthy (ratio < 0.7)
  - Reduced capability
  - Automatic fallback to simpler models
```

### 5.3 Circuit Breaker (router/)

```
Circuit States:
┌────────┐
│ CLOSED  │ ──→ (failures ≥ threshold) ──→ OPEN
│        │         │                           │
│        │   ◄────┘ (timeout)              │
│        │         │                        ▼
│        │   HALF-OPEN ◄────────────────┘
│        │     (test request)
└───────┘
```

---

## 6. Configuration Management

### 6.1 Configuration Structure (config.py)

**FrankensteinConfig** (Pydantic BaseSettings):

| Category | Settings |
|----------|----------|
| **Paths** | `models_dir` |
| **Ports** | `llama_server_port` (8080), `ollama_fallback_port` (11434) |
| **Models** | `default_model`, `rosetta_model`, `embed_model` |
| **Inference** | `n_gpu_layers`, `n_ctx`, `n_threads`, `n_batch` |
| **RoPE** | `rope_scaling_type`, `rope_scale`, `rope_freq_base` |
| **Features** | `enable_rosetta_fast_mode`, `enable_embeddings`, `enable_rag` |
| **Health** | `health_check_interval` (30s), `health_threshold_ratio` (0.7) |
| **GPU** | `gpu_temp_threshold` (85°C), `gpu_vram_threshold_mb` (11000) |
| **Circuit** | `circuit_breaker_threshold` (3), `circuit_breaker_timeout` (60s) |
| **LoRA** | `default_adapter`, `adapters_dir` |
| **Logging** | `log_level`, `log_format` |

### 6.2 Environment Variables

All config supports `FRANKENSTEIN_` prefix:

```bash
export FRANKENSTEIN_MODELS=/path/to/models
export FRANKENSTEIN_LLAMA_SERVER_PORT=8080
export FRANKENSTEIN_DEFAULT_MODEL=qwen2.5-coder-7b-q4_k_m
export FRANKENSTEIN_MAX_VRAM_MB=12500
```

### 6.3 Config Access Patterns

```python
# Function-based (recommended)
from nx_engine import config
port = config.get_config().llama_server_port

# Module-level proxy
url = config.LLAMA_SERVER_URL  # Uses __getattr__

# Backward-compatible functions
url = config._get_llama_server_url()
```

### 6.4 Configuration Priority

1. Environment variables (highest priority)
2. `.env` file in project root
3. Code defaults (FrankensteinConfig)

---

## 7. Error Handling

### 7.1 Exception Hierarchy (exceptions.py)

```python
# Base exception
 FrankensteinError(Exception)
    │
    ├── ModelLoadError        # GGUF load failure
    │   └── GPUOOMError      # GPU out of memory
    │
    ├── AdapterError        # LoRA adapter issues
    │   ├── AdapterNotFoundError
    │   └── AdapterValidationError
    │
    ├── RouterError       # Routing failures
    │   └── CircuitBreakerOpenError
    │
    ├── HealthError       # Health check failures
    │
    └── ServerError       # Server-related errors
        ├── SlotUnavailableError
        └── RequestQueueError
```

### 7.2 Error Handling Patterns

**GPU OOM Fallback** (engine/__init__.py):
```python
try:
    self._llama = self._create_llama_instance()
except Exception as e:
    if "out of memory" in str(e).lower():
        if self.n_gpu_layers > 0 and allow_fallback:
            self.n_gpu_layers = 0  # CPU fallback
            self._llama = self._create_llama_instance()
```

**Circuit Breaker** (router/__init__.py):
```python
if self._circuit_state == "open":
    if time.time() - self._circuit_open_time > timeout:
        self._circuit_state = "half-open"
    else:
        return {"level": 3, "confidence": 0.0, "reason": "Circuit open"}
```

**Auto-Fallback Chain**:
```
Direct GGUF (port 8080)
    │
    ├── Fail → Ollama fallback (port 11434)
    │         │
    │         └── Fail → Keyword routing (offline)
    │
    └── GPU Layers → CPU fallback
```

---

## 8. Dependencies

### 8.1 Core Dependencies

| Package | Version | Purpose |
|--------|---------|---------|
| `llama-cpp-python` | latest | Direct GGUF loading |
| `pydantic` | >=2.0 | Configuration |
| `pydantic-settings` | latest | Settings from env |
| `requests` | latest | HTTP health checks |
| `aiohttp` | latest | Async operations |

### 8.2 Optional Dependencies

| Package | Purpose |
|--------|---------|
| `fastapi` | Server API |
| `uvicorn` | Server runner |
| ` numpy` | Embeddings |
| `sounddevice` | Dictation audio |
| `pyaudio` | Audio input |

### 8.3 Internal Dependencies

```
nx_engine/
├── engine/__init__.py
│   └── llama_cpp (llama-cpp-python)
├── config.py
│   └── pydantic, pydantic_settings
├── router/__init__.py
│   └── urllib, requests
├── health/__init__.py
│   └── requests, subprocess (nvidia-smi)
└── server/api.py
    └── fastapi, uvicorn
```

---

## 9. Security

### 9.1 Security Considerations

| Area | Implementation |
|------|----------------|
| **Model Files** | Local filesystem only |
| **No API Keys** | All local inference |
| **No Network** | Direct Python bindings when possible |
| **Config Secrets** | Environment variables only |

### 9.2 Security Best Practices

- Never commit model files (`.gguf`) to repository
- Use `.env` for local overrides (add to `.gitignore`)
- Validate adapter files before loading
- Circuit breaker prevents DoS from repeated failures

---

## 10. Performance

### 10.1 Performance Optimizations

| Optimization | Config | Impact |
|--------------|--------|-------|
| GPU Layers | `n_gpu_layers=-1` | 10-50x |
| Flash Attention | `--flash-attn on` | 1.2-1.5x |
| Batch Size | `n_batch=512` | Higher throughput |
| Context Keep | `n_keep=256` | Faster context |
| Thread Tuning | `n_threads=16` | Better CPU balance |
| KV Cache Quantization | `-ctk q4_0 -ctv q4_0` | 2x context |
| Continuous Batching | `cont_batching=True` | 20-30% |

### 10.2 RoPE Scaling (Extended Context)

```python
# Enable 131K context on 32K models
rope_scaling_type: "yarn"   # YaRN method
rope_scale: 4.0            # 4x extension
rope_freq_base: 1000000.0  # Qwen uses 1M
yarn_orig_ctx: 32768       # Original context
```

### 10.3 Benchmarks (Inferred)

| Metric | Expected |
|--------|----------|
| Tokens/sec | 471+ (7B, GPU) |
| Latency | ~64ms |
| VRAM Usage | ~7GB (7B Q4) |

---

## 11. Testing Strategy

### 11.1 Test Structure

```
nx_engine/tests/
├── test_engine.py    # DirectLlamaClient tests
├── test_router.py    # RouterBrain tests
├── test_health.py   # HealthMonitor tests
└── test_config.py   # Configuration tests
```

### 11.2 Test Categories

| Category | Focus |
|----------|-------|
| **Unit** | Individual components |
| **Integration** | Component interaction |
| **Health** | Health monitoring |
| **Performance** | Benchmarking |

### 11.3 Running Tests

```bash
# Run all tests
pytest tests/

# Run specific module
pytest tests/test_engine.py

# With coverage
pytest tests/ --cov=nx_engine
```

---

## Appendix A: File Quick Reference

| File | Exports | Key Classes |
|------|---------|-------------|
| `nx_engine/__init__.py` | Package API | 11 exports |
| `config.py` | Configuration | `FrankensteinConfig` |
| `cli.py` | CLI | `cmd_*` functions |
| `engine/__init__.py` | Engine | `DirectLlamaClient`, `GPUMemoryManager` |
| `router/__init__.py` | Router | `RouterBrain`, `CATEGORY_KEYWORDS` |
| `health/__init__.py` | Health | `HealthMonitor`, `HealthStatus` |
| `server/__init__.py` | Server | `Slot`, `RequestQueue` |
| `local_llm/brain.py` | Brain | `Brain`, `MODEL_ALIASES` |

---

## Appendix B: Version History

| Version | Date | Changes |
|---------|------|--------|
| 2.0.0 | 2026-04 | Current version |
| 1.x | Earlier | Initial development |

---

*Document created from brownfield codebase analysis.*
*Architecture reflects existing implementation as of v2.0.0.*
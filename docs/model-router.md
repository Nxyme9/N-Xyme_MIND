# Model Router System Documentation

The Model Router is a multi-provider LLM routing system that intelligently routes requests to optimal models based on task type, VRAM availability, and provider health. It provides both a Python API (hook) and an HTTP proxy server.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Model Router Architecture                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                  │
│  │  HTTP Proxy │────▶│ Task Detect │────▶│  Provider   │                  │
│  │ (FastAPI)   │     │ (heuristic) │     │  Selection  │                  │
│  └─────────────┘     └─────────────┘     └─────────────┘                  │
│        │                    │                    │                          │
│        │                    ▼                    ▼                          │
│        │            ┌─────────────┐     ┌─────────────┐                  │
│        │            │Rate Limiter │     │Circuit Breaker│                 │
│        │            │ (token bucket)│   │(per-provider)│                  │
│        │            └─────────────┘     └─────────────┘                  │
│        │                    │                    │                          │
│        │                    ▼                    ▼                          │
│        │            ┌─────────────┐     ┌─────────────┐                  │
│        │            │VRAM Manager │     │  Providers   │                  │
│        │            │(nvidia-smi) │     │ - opencode  │                  │
│        │            └─────────────┘     │ - openrouter│                  │
│        │                    │            │ - ollama    │                  │
│        │                    ▼            └─────────────┘                  │
│        │            ┌─────────────┐                                       │
│        │            │Ollama Manager│                                       │
│        │            │(local models)│                                       │
│        │            └─────────────┘                                       │
│        │                                                                  │
│        ▼                                                                  │
│  ┌─────────────┐                                                          │
│  │  Hook API   │                                                          │
│  │route_request│                                                          │
│  │get_status   │                                                          │
│  └─────────────┘                                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Request Pipeline

When a request comes through `route_request()`:

1. **Rate Limit Check** - Token bucket validation (8 requests/60 seconds)
2. **Task Classification** - Agent type mapped to model/route
3. **Circuit Breaker** - Check if primary model is healthy
4. **VRAM Check** - Verify GPU memory for local models
5. **Model Loading** - Ensure Ollama model is in VRAM
6. **Fallback Selection** - Use fallback if primary unavailable

---

## Components

### VRAM Manager

**File:** `src/model_router/vram_manager.py`

Monitors GPU VRAM using `nvidia-smi` and makes model loading decisions.

```python
from model_router.vram_manager import VRAMManager, MODEL_SIZES

# Initialize with 12GB max, 1GB safety margin
manager = VRAMManager(max_vram_gb=12.0, safety_margin_gb=1.0)

# Check current usage
usage = manager.get_vram_usage()
print(f"VRAM: {usage['used_gb']:.1f} / {usage['total_gb']:.1f} GB")

# Check if model fits
can_load = manager.can_load_model("qwen2.5-coder:7b")  # True/False

# Get budget summary
budget = manager.get_vram_budget()
print(f"Headroom: {budget['headroom_gb']:.1f} GB")
```

**Known Model Sizes (GB):**

| Model | VRAM (GB) |
|-------|-----------|
| llama3.2:1b | 0.7 |
| llama3.2:3b | 2.0 |
| qwen2.5-coder:7b | 4.5 |
| qwen2.5-coder:14b | 9.0 |
| qwen3:8b | 5.2 |
| deepseek-r1:14b | 9.0 |
| llava:7b | 4.5 |

### Ollama Manager

**File:** `src/model_router/ollama_manager.py`

Manages Ollama model lifecycle: loading, unloading, health checking.

```python
from model_router.ollama_manager import OllamaManager

manager = OllamaManager(ollama_url="http://localhost:11434")

# Health check
if manager.health_check():
    print("Ollama is online")

# Get loaded models
loaded = manager.get_loaded_models()
for m in loaded:
    print(f"Loaded: {m.name}")

# Get available models
available = manager.get_available_models()

# Load model (keeps in VRAM permanently)
manager.load_model("qwen2.5-coder:7b", keep_alive="-1")

# Ensure model is loaded (lazy load)
manager.ensure_model_loaded("llama3.2:3b")

# Unload model
manager.unload_model("qwen2.5-coder:7b")
```

**Key Methods:**
- `health_check() -> bool` - Check Ollama server reachability
- `get_loaded_models() -> List[LoadedModel]` - Models currently in VRAM
- `get_available_models() -> List[ModelInfo]` - All pulled models
- `load_model(model, keep_alive="-1") -> bool` - Load into VRAM
- `unload_model(model) -> bool` - Unload from VRAM
- `ensure_model_loaded(model) -> bool` - Lazy load if not loaded

### Circuit Breaker

**File:** `src/model_router/circuit_breaker.py`

Per-model failure tracking with exponential backoff and state persistence.

```python
from model_router.circuit_breaker import CircuitBreaker

cb = CircuitBreaker(
    failure_threshold=3,    # Open after 3 failures
    reset_timeout=300,      # 5 minute backoff
    base_delay=1.0,         # Start at 1 second
    max_delay=60.0,         # Max 60 seconds
    state_file=".cache/circuit-breaker.json"
)

# Record failures
cb.record_failure("ollama")
cb.record_failure("ollama")
cb.record_failure("ollama")

# Check availability
if cb.is_available("ollama"):
    print("Model is healthy")
else:
    print("Circuit is open, check backoff")

# Get state
state = cb.state("ollama")
print(f"is_open: {state['is_open']}, failures: {state['failures']}")

# Record success (resets counter)
cb.record_success("ollama")
```

**Behavior:**
- After 3 consecutive failures, circuit opens
- Exponential backoff: 1s, 2s, 4s, 8s... (capped at 60s)
- Optional jitter adds 0-50% random delay
- State persisted to `.cache/circuit-breaker.json`

### Rate Limiter (Token-Aware)

**File:** `src/model_router/rate_limiter.py`

Token bucket rate limiter with thread-safe blocking. Now supports token-based consumption for more precise control.

```python
from model_router.rate_limiter import RateLimiter

rl = RateLimiter(max_requests=8, window_seconds=60)

# Consume specific token amount (useful for multi-model requests)
rl.consume(50)  # Consume 50 tokens (each request = 1 token by default)

# Non-blocking try
if rl.try_acquire():
    print("Request allowed")
else:
    wait = rl.get_wait_time()
    print(f"Retry in {wait:.1f}s")

# Blocking acquire (waits until token available)
rl.acquire()

# Get stats
stats = rl.get_stats()
print(f"Tokens: {stats['available_tokens']:.1f} / {stats['max_requests']}")
```

**Token-Aware Features:**
- `consume(n)` - Deduct N tokens from bucket (default: 1 token per request)
- Per-request token costs can be customized based on model complexity
- Automatic token refill over time within the window

**File:** `src/model_router/rate_limiter.py`

Token bucket rate limiter with thread-safe blocking.

```python
from model_router.rate_limiter import RateLimiter

rl = RateLimiter(max_requests=8, window_seconds=60)

# Non-blocking try
if rl.try_acquire():
    print("Request allowed")
else:
    wait = rl.get_wait_time()
    print(f"Retry in {wait:.1f}s")

# Blocking acquire (waits until token available)
rl.acquire()

# Get stats
stats = rl.get_stats()
print(f"Tokens: {stats['available_tokens']:.1f} / {stats['max_requests']}")
```
### Semantic Cache

**File:** `src/model_router/semantic_cache.py`

LRU cache with TTL and semantic similarity matching for request deduplication.

```python
from model_router.semantic_cache import SemanticCache

cache = SemanticCache(
    max_size=1000,      # Max cached entries
    ttl_seconds=3600,   # Time-to-live per entry
    similarity_threshold=0.95  # Minimum similarity for hit
)

# Cache a response
cache.put("user request", "model_name", "cached response")

# Retrieve (returns None if not found or expired)
result = cache.get("user request", "model_name")

# Check stats
stats = cache.get_stats()
print(f"Hits: {stats['hits']}, Misses: {stats['misses']}")

# Clear expired entries
cache.cleanup()
```

**Features:**
- LRU eviction when max_size reached
- TTL-based expiration (default 1 hour)
- Stores model-specific responses
- Thread-safe operations

---

### Hook (Main API)
### Hook (Main API)

**File:** `src/model_router/hook.py`

Single entry point for complete routing pipeline.

```python
from model_router.hook import route_request, get_system_status

# Route a request
result = route_request("explore", "find all Python files in src/")
print(result)
# {
#   'model': 'minimax-m2.5-free',
#   'provider': 'opencode',
#   'confidence': 0.9,
#   'reason': "Routed 'explore' to minimax-m2.5-free (opencode)",
#   'fallback_used': False,
#   'rate_limited': False,
#   'circuit_broken': False,
#   'vram_blocked': False,
#   'complexity': 'simple',
#   'priority': 2
# }

# Get system status
status = get_system_status()
print(status)
# {
#   'vram': {'used_gb': 4.5, 'total_gb': 12.0, 'free_gb': 7.5, 'percent': 37.5},
#   'ollama_health': True,
#   'circuit_breakers': {...},
#   'rate_limiter': {'max_requests': 8, 'window_seconds': 60, 'available_tokens': 7.5},
#   'loaded_models': ['qwen2.5-coder:7b'],
#   'timestamp': 1234567890.0
# }

# Record outcomes for circuit breaker
record_success("minimax-m2.5-free")
record_failure("ollama")
```

**Supported Agent Types:**
- `explore` - Codebase search → minimax-m2.5-free
- `librarian` - External research → minimax-m2.5-free
- `oracle` - Architecture review → mimo-v2-pro-free
- `hephaestus` - Implementation → mimo-v2-pro-free
- `sisyphus` - Orchestration → mimo-v2-pro-free
- `multimodal` - Visual analysis → opencode vision model

---

## API Reference

### Proxy Server Endpoints

The proxy runs on `http://localhost:8080` (configurable via `MODEL_ROUTER_PORT`).

#### POST /v1/chat/completions

OpenAI-compatible chat completion endpoint.

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Agent-Type: explore" \
  -d '{
    "model": "minimax-m2.5-free",
    "messages": [{"role": "user", "content": "Find all Python files"}],
    "temperature": 0.7,
    "max_tokens": 1000
  }'
```

**Headers:**
- `X-Agent-Type` - Optional agent type for classification
- `X-VRAM-Used-GB` - Response header with current VRAM usage
- `X-Provider` - Response header with actual provider used

#### GET /v1/models

List available models across all providers.

```bash
curl http://localhost:8080/v1/models
```

**Response:**
```json
{
  "models": [
    {"id": "opencode/mimo-v2-pro-free", "provider": "opencode"},
    {"id": "opencode/minimax-m2.5-free", "provider": "opencode"},
    {"id": "qwen2.5-coder:7b", "provider": "ollama"},
    ...
  ]
}
```
#### GET /v1/health

OpenAI-compatible health check endpoint.

```bash
curl http://127.0.0.1:8080/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": 1234567890.0,
  "ollama": "online",
  "vram_used_gb": 2.36,
  "vram_free_gb": 9.64
}
```

#### GET /v1/models/{id}

Get details for a specific model.

```bash
curl http://127.0.0.1:8080/v1/models/opencode/minimax-m2.5-free
```

**Response:**
```json
{
  "id": "opencode/minimax-m2.5-free",
  "provider": "opencode",
  "object": "model"
}
```

#### DELETE /v1/models/{id}

Unload a specific model from VRAM (Ollama models only).

```bash
curl -X DELETE http://127.0.0.1:8080/v1/models/qwen2.5-coder:7b
```

**Response:**
```json
{
  "deleted": "qwen2.5-coder:7b",
  "success": true
}
```

#### GET /health
#### GET /health

Health check endpoint.

```bash
curl http://localhost:8080/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": 1234567890.0,
  "ollama": "online",
  "vram_used_gb": 4.5,
  "vram_free_gb": 7.5
}
```

#### GET /stats

Usage statistics from SQLite database.

```bash
curl http://localhost:8080/stats
```

**Response:**
```json
{
  "providers": [
    {"provider": "opencode", "requests": 150, "tokens": 45000, "rate_limits": 2, "last_used": 1234567890.0},
    {"provider": "ollama", "requests": 45, "tokens": 12000, "rate_limits": 0, "last_used": 1234567880.0}
  ],
  "recent_requests": [...]
}
```

#### GET /vram

VRAM usage and budget status.

```bash
curl http://localhost:8080/vram
```

**Response:**
```json
{
  "usage": {
    "used_gb": 4.5,
    "total_gb": 12.0,
    "free_gb": 7.5,
    "percent": 37.5
  },
  "budget": {
    "max_gb": 12.0,
    "safety_margin_gb": 1.0,
    "effective_limit_gb": 11.0,
    "used_gb": 4.5,
    "available_gb": 7.5,
    "headroom_gb": 6.5
  },
  "loaded_models": {"qwen2.5-coder:7b": 4.5},
  "over_limit": false
}
```

#### GET /models/loaded

Currently loaded Ollama models.

```bash
curl http://localhost:8080/models/loaded
```

**Response:**
```json
{
  "models": [
    {"name": "qwen2.5-coder:7b", "size_bytes": 4700000000, "digest": "...", "expires_at": "-1"}
  ],
  "count": 1
}
```

#### POST /models/load

Load a model into Ollama VRAM.

```bash
curl -X POST http://localhost:8080/models/load \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.2:3b", "keep_alive": "-1"}'
```

#### POST /models/unload

Unload a model from Ollama VRAM.

```bash
curl -X POST "http://localhost:8080/models/unload?model=llama3.2:3b"
```

#### GET /circuit-breaker

Circuit breaker state for all providers.

```bash
curl http://localhost:8080/circuit-breaker
```

**Response:**
```json
{
  "providers": {
    "ollama": {"model": "ollama", "failures": 0, "last_failure_time": 0, "is_open": false, "threshold": 3},
    "opencode": {"model": "opencode", "failures": 0, "last_failure_time": 0, "is_open": false, "threshold": 3}
  },
  "failure_threshold": 3,
  "reset_timeout": 300
}
```

#### GET /rate-limiter

Rate limiter status.

```bash
curl http://localhost:8080/rate-limiter
```

**Response:**
```json
{
  "max_requests": 8,
  "window_seconds": 60,
  "available_tokens": 7.5,
  "wait_time_seconds": 0.0
}
```

#### POST /vpn/rotate

Manually trigger VPN rotation (requires VPN rotator module).

```bash
curl -X POST http://localhost:8080/vpn/rotate
```

#### POST /vpn/status

Get VPN connection status.

```bash
curl -X POST http://localhost:8080/vpn/status
```

---

## Hook API

### route_request(agent_type: str, task_content: str = "") -> Dict[str, Any]

Primary function for routing requests through the complete pipeline.

**Parameters:**
- `agent_type` - Agent identifier (explore, oracle, hephaestus, sisyphus, librarian, multimodal)
- `task_content` - Optional task description for dynamic routing

**Returns:**
```python
{
    "model": str,           # Selected model name
    "provider": str,        # "ollama", "opencode", "openrouter"
    "confidence": float,    # 0.0–1.0 routing confidence
    "reason": str,          # Human-readable explanation
    "fallback_used": bool,  # Whether fallback was selected
    "rate_limited": bool,   # Request blocked by rate limit
    "circuit_broken": bool, # Primary model circuit is open
    "vram_blocked": bool,   # VRAM prevented local model loading
    "complexity": str,      # "simple", "medium", "complex", "deep", "unknown"
    "priority": int,        # Route priority (1=highest)
}
```

**Example:**
```python
from model_router.hook import route_request

result = route_request("hephaestus", "implement a REST API endpoint")
print(f"Using {result['model']} via {result['provider']}")
```

### get_system_status() -> Dict[str, Any]

Returns a snapshot of the entire routing system.

**Returns:**
```python
{
    "vram": {
        "used_gb": float,
        "total_gb": float,
        "free_gb": float,
        "percent": float
    },
    "ollama_health": bool,
    "circuit_breakers": Dict[str, Dict],  # Models with issues
    "rate_limiter": {
        "max_requests": int,
        "window_seconds": float,
        "available_tokens": float
    },
    "loaded_models": List[str],
    "timestamp": float,
}
```

### record_success(model: str) -> None

Record successful API call. Resets circuit breaker failure counter.

```python
from model_router.hook import record_success

record_success("minimax-m2.5-free")
```

### record_failure(model: str) -> None

Record failed API call. Increments circuit breaker counter.

```python
from model_router.hook import record_failure

record_failure("ollama")
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_ROUTER_PORT` | 8080 | Proxy server port |
| `MODEL_ROUTER_HOST` | 127.0.0.1 | Proxy server host |
| `MODEL_ROUTER_MAX_VRAM_GB` | 12.0 | Maximum VRAM allocation in GB |
| `MODEL_ROUTER_VRAM_SAFETY_MARGIN_GB` | 1.0 | Safety margin to reserve in GB |
| `MODEL_ROUTER_CIRCUIT_THRESHOLD` | 3 | Failures before circuit opens |
| `MODEL_ROUTER_CIRCUIT_TIMEOUT` | 300 | Circuit reset timeout in seconds |
| `MODEL_ROUTER_RATE_LIMIT` | 8 | Max requests per window |
| `MODEL_ROUTER_RATE_WINDOW` | 60 | Rate limit window in seconds |
| `MODEL_ROUTER_CACHE_SIZE` | 1000 | Semantic cache max entries |
| `MODEL_ROUTER_CACHE_TTL` | 3600 | Cache TTL in seconds |
| `MODEL_ROUTER_CACHE_SIMILARITY` | 0.95 | Semantic similarity threshold |
| `MODEL_ROUTER_TOKENS_PER_REQUEST` | 1 | Default tokens consumed per request |
| `OPENCODE_API_KEY` | - | API key for OpenCode provider |
| `OPENROUTER_API_KEY` | - | API key for OpenRouter provider |

### Centralized Configuration

**File:** `src/model_router/config.py`

Centralized configuration module for all model router settings.

```python
from model_router.config import (
    MODEL_SIZES,       # Dict of model name -> size in GB
    PROVIDERS,         # Dict of provider name -> config
    ROUTE_MAP,         # Agent type -> model routing rules
    DEFAULT_PROVIDER,  # Fallback provider
    get_model_size,    # Get size for a model
    get_provider      # Get provider config
)

# Access centralized config
print(f"Models: {len(MODEL_SIZES)}")
print(f"Providers: {len(PROVIDERS)}")
print(f"Default: {DEFAULT_PROVIDER}")

# Get model size
size = get_model_size("qwen2.5-coder:7b")  # Returns 4.5

# Get provider config
provider = get_provider("opencode")
```

**Configuration Variables:**

| Variable | Description |
|----------|-------------|
| `MODEL_SIZES` | Dict mapping model names to VRAM size (GB) |
| `PROVIDERS` | Dict of provider configs with endpoints, api_keys |
| `ROUTE_MAP` | Agent type -> routing rules |
| `DEFAULT_PROVIDER` | Fallback provider name |
| `CIRCUIT_BREAKER_DEFAULTS` | Default threshold, timeout, delays |
| `RATE_LIMITER_DEFAULTS` | Default max_requests, window_seconds |

### opencode.json Settings
| `MODEL_ROUTER_RATE_WINDOW` | 60 | Rate limit window in seconds |
| `OPENCODE_API_KEY` | - | API key for OpenCode provider |
| `OPENROUTER_API_KEY` | - | API key for OpenRouter provider |

### opencode.json Settings

The local-proxy provider connects to the model router:

```json
{
  "enabled_providers": ["openrouter", "opencode", "google", "local-proxy"],
  "local-proxy": {
    "base_url": "http://localhost:8080/v1",
    "api_key": "local",
    "models": ["local-proxy/auto"]
  }
}
```

### Component Configuration (in hook.py)

```python
_vram_manager = VRAMManager(max_vram_gb=12.0, safety_margin_gb=1.0)
_ollama_manager = OllamaManager()
_circuit_breaker = CircuitBreaker(failure_threshold=3, reset_timeout=300)
_rate_limiter = RateLimiter(max_requests=8, window_seconds=60)
```

---

## Usage Examples

### Python Import

```python
# Direct hook usage
import sys
sys.path.insert(0, '/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/src')

from model_router.hook import route_request, get_system_status

# Route a coding task
result = route_request("hephaestus", "write a function to parse JSON")
print(result["model"], result["provider"])

# Check system health
status = get_system_status()
print(f"Ollama: {'ONLINE' if status['ollama_health'] else 'OFFLINE'}")
print(f"VRAM: {status['vram']['percent']:.0f}% used")
```

### curl Commands

```bash
# Health check
curl http://localhost:8080/health

# List models
curl http://localhost:8080/v1/models

# Chat completion
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Agent-Type: explore" \
  -d '{
    "model": "minimax-m2.5-free",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# VRAM status
curl http://localhost:8080/vram

# Circuit breaker status
curl http://localhost:8080/circuit-breaker
```

---

## Troubleshooting

### Ollama Not Running

**Symptom:** `ollama_health: false` in status

**Solution:**
```bash
# Start Ollama
ollama serve

# Or in background
nohup ollama serve > logs/ollama.log 2>&1 &
```

### VRAM Full

**Symptom:** `vram_blocked: true` in route result

**Solution:**
```bash
# Check VRAM usage
curl http://localhost:8080/vram

# Unload unused models
curl -X POST "http://localhost:8080/models/unload?model=qwen2.5-coder:7b"
```

### Rate Limited

**Symptom:** `rate_limited: true` in route result

**Solution:**
```bash
# Check wait time
curl http://localhost:8080/rate-limiter

# Wait and retry, or adjust rate limiter config
```

### Circuit Breaker Open

**Symptom:** `circuit_broken: true` for a provider

**Solution:**
```bash
# Check circuit state
curl http://localhost:8080/circuit-breaker

# Wait for backoff period (default 5 min), or manually reset
```

### Model Not Found in Ollama

**Symptom:** Model load fails

**Solution:**
```bash
# Pull the model
ollama pull qwen2.5-coder:7b

# List available models
ollama list
```

---

## Performance Benchmarks

Based on typical hardware (RTX 3080, 12GB VRAM):

| Operation | Latency |
|-----------|---------|
| VRAM query (nvidia-smi) | ~50ms |
| Ollama health check | ~100ms |
| Model load (7B model) | ~2-5s |
| Local inference (7B) | ~100-500ms/token |
| OpenCode API | ~1-3s total |
| OpenRouter API | ~2-5s total |
| Proxy startup | ~1s |
| Circuit breaker check | <1ms |
| Rate limiter check | <1ms |

### Throughput

- Rate limit: 8 requests/60 seconds (configurable)
- Concurrent requests: Up to 100 connections (httpx limits)
- VRAM capacity: 2-3 models (7B size) simultaneously
- Circuit breaker: Per-provider, state persisted to disk

### Security Features

- **Input validation**: Model names validated against regex pattern `^[a-zA-Z0-9_:.-]+$`
- **Error sanitization**: Internal paths and stack traces never leak to clients
- **Rate limiting**: Token bucket algorithm prevents abuse
- **Circuit breaker**: Automatically isolates failing providers
- **VRAM management**: Prevents out-of-memory crashes with configurable safety margin
- **Audit logging**: All requests logged with provider, model, task type, and latency
- **Graceful shutdown**: SIGTERM/SIGINT handlers clean up HTTP clients and database connections
---

## Deployment Guide

### Startup Script

**File:** `bin/start-model-router.sh`

```bash
# Start the model router
bash bin/start-model-router.sh

# Output:
# Starting model router on 127.0.0.1:8080...
# Model router started (PID: 12345)
# Log file: logs/model-router.log
# Health check passed
```

### Manual Start

```bash
# Activate virtual environment
source venv/bin/activate

# Run proxy directly
python -m uvicorn src.proxy.model_router:app \
    --host 127.0.0.1 \
    --port 8080 \
    --log-level info
```

### systemd Service (Optional)

Create `/etc/systemd/system/model-router.service`:

```ini
[Unit]
Description=Model Router Proxy
After=network.target

[Service]
Type=simple
User=nxyme
WorkingDirectory=/home/nxyme/N-Xyme_CODE/N-Xyme_MIND
ExecStart=/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/venv/bin/python -m uvicorn src.proxy.model_router:app --host 127.0.0.1 --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable model-router
sudo systemctl start model-router

# Check status
sudo systemctl status model-router
```

### Docker (Optional)

```dockerfile
FROM python:3.11-slim
RUN pip install fastapi uvicorn httpx pydantic
WORKDIR /app
COPY src/ ./src/
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "src.proxy.model_router:app", "--host", "0.0.0.0"]
```

---

## File Structure

src/model_router/
├── __init__.py
├── hook.py          # Main API entry point
├── model_router.py  # Task classifier and routing logic
├── vram_manager.py  # GPU VRAM monitoring
├── ollama_manager.py # Ollama lifecycle management
├── circuit_breaker.py # Per-model failure tracking
├── rate_limiter.py  # Token bucket rate limiting
├── semantic_cache.py # LRU cache with TTL
├── config.py       # Centralized configuration
└── __init__.py      # Package init

src/proxy/
└── model_router.py  # FastAPI proxy server
src/model_router/
├── __init__.py
├── hook.py          # Main API entry point
├── model_router.py  # Task classifier and routing logic
├── vram_manager.py  # GPU VRAM monitoring
├── ollama_manager.py # Ollama lifecycle management
├── circuit_breaker.py # Per-model failure tracking
└── rate_limiter.py  # Token bucket rate limiting

src/proxy/
└── model_router.py  # FastAPI proxy server

bin/
└── start-model-router.sh  # Startup script

.cache/
└── circuit-breaker.json   # Circuit breaker state (auto-created)

data/proxy/
└── usage.db               # Usage logs SQLite DB (auto-created)
```
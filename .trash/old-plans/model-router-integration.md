# Model Router Integration Plan

> **Goal**: Wire trained weights into routing decisions + add missing features
> **Created**: 2026-04-06
> **Status**: Draft - awaiting approval

---

## Current State

| Component | Status |
|-----------|--------|
| Trained weights (`.sisyphus/model_weights.json`) | ✅ Exists, 7 models, converged |
| Circuit breaker (`packages/intelligence/circuit_breaker.py`) | ✅ Working |
| Fallback chain (`packages/intelligence/fallback.py`) | ✅ Working |
| Training loop (`scripts/train-model-router.py`) | ✅ Working |
| Router (`packages/intelligent_router_mcp/__init__.py`) | ⚠️ Weights NOT loaded |
| Config (`configs/model_router.json`) | ⚠️ Features defined, not implemented |
| Agent model assignments (from other session) | ⚠️ Not wired into router |

---

## Phase 1: Wire What Exists (Critical Path)

### 1.1 Load Trained Weights at Router Init

**File**: `packages/intelligent_router_mcp/__init__.py`

**Change**: Add `_load_trained_weights()` method, call in `Router.__init__()`

```python
def _load_trained_weights(self) -> None:
    """Load trained weights from .sisyphus/model_weights.json."""
    weights_path = Path(".sisyphus/model_weights.json")
    if weights_path.exists():
        with open(weights_path) as f:
            data = json.load(f)
            self._model_weights = data.get("weights", {})
            self._category_best = data.get("category_best", {})
            self._weights_trained_at = data.get("trained_at", 0)
            self._weights_total_samples = data.get("total_samples", 0)
            self._weights_converged = data.get("converged", False)
    else:
        # Fall back to equal weights
        self._model_weights = {m: 1.0/len(MODEL_CAPABILITIES) for m in MODEL_CAPABILITIES}
        self._category_best = {}
        self._weights_trained_at = 0
```

**Success criteria**: `router._model_weights` populated on init, not empty `{}`

**Tests**: Unit test for weight loading (file exists / file missing / malformed JSON)

---

### 1.2 Fix Model Name Mapping

**Problem**: Trained weights use short names (`qwen3.6-plus`) but config uses full names (`opencode/qwen3.6-plus-free`).

**File**: `packages/intelligent_router_mcp/__init__.py`

**Change**: Add name translation layer

```python
# Model name mapping: trained key → config/actual key
MODEL_NAME_MAP = {
    "qwen3.6-plus": "opencode/qwen3.6-plus-free",
    "qwen3-coder": "openrouter/qwen/qwen3-coder:free",
    "deepseek-r1": "openrouter/deepseek/deepseek-r1:free",
    "minimax-m2.5": "opencode/minimax-m2.5-free",
    "gemini-2.5-flash": "opencode/gemini-2.5-flash-free",
    "ollama/qwen2.5-coder:7b": "ollama/qwen2.5-coder:7b",  # already matches
    "ollama/llama3.2:3b": "ollama/llama3.2:3b",  # already matches
}

# Reverse map for lookups
MODEL_NAME_REVERSE = {v: k for k, v in MODEL_NAME_MAP.items()}
```

**Change**: In `_load_trained_weights()`, translate keys:
```python
translated = {}
for short_name, weight in data["weights"].items():
    full_name = MODEL_NAME_MAP.get(short_name, short_name)
    translated[full_name] = weight
self._model_weights = translated
```

**Success criteria**: `router._model_weights` keys match `configs/model_router.json` model names

---

### 1.3 Apply Agent Overrides in select_route()

**File**: `packages/intelligent_router_mcp/__init__.py` + `configs/model_router.json`

**Current**: `agent_overrides` defined in config but never read.

**Change**: Load `agent_overrides` from config, apply in `select_route()`:

```python
# In Router.__init__
self._agent_overrides = self._load_agent_overrides()

# In select_route(), after brain analysis:
agent_type = agent_type or analysis.get("agent_type", "")
if agent_type and agent_type in self._agent_overrides:
    override = self._agent_overrides[agent_type]
    # Apply model preference for this agent type
    preferred = override.get("preferred_model")
    if preferred and preferred not in avoided:
        selected_model = preferred
        selection_reason = f"agent_override:{agent_type}"
```

**Config update**: Ensure `configs/model_router.json` has `agent_overrides` matching the agent assignments:

```json
{
  "agent_overrides": {
    "sisyphus": { "preferred_model": "opencode/qwen3.6-plus-free" },
    "prometheus": { "preferred_model": "opencode/mimo-v2-pro-free" },
    "oracle": { "preferred_model": "opencode/mimo-v2-pro-free" },
    "metis": { "preferred_model": "opencode/mimo-v2-pro-free" },
    "momus": { "preferred_model": "opencode/kimi-k2.5-free" },
    "hephaestus": { "preferred_model": "opencode/minimax-m2.5-free" },
    "atlas": { "preferred_model": "opencode/minimax-m2.5-free" },
    "explore": { "preferred_model": "opencode/minimax-m2.5-free" },
    "librarian": { "preferred_model": "opencode/minimax-m2.5-free" },
    "sisyphus-junior": { "preferred_model": "ollama/llama3.2:3b" },
    "multimodal-looker": { "preferred_model": "opencode/mimo-v2-omni-free" }
  }
}
```

**Success criteria**: Routing for `sisyphus` agent returns `qwen3.6-plus-free`, `hephaestus` returns `minimax-m2.5-free`

---

### 1.4 Dynamic Fallback Chain

**File**: `packages/intelligent_router_mcp/__init__.py`

**Current**: Static fallback chain from config, checked sequentially.

**Change**: Make fallback weight-aware + circuit-breaker-aware:

```python
def _get_weighted_fallback(self, excluded_model: str = None) -> List[str]:
    """Get fallback models sorted by weight, respecting circuit breaker state."""
    available = []
    for model, weight in sorted(self._model_weights.items(), key=lambda x: -x[1]):
        if model == excluded_model:
            continue
        if self._model_circuit_breaker.can_execute(model):
            available.append(model)

    # If all weighted models fail, fall back to local models
    local_fallbacks = ["ollama/qwen2.5-coder:7b", "ollama/llama3.2:3b"]
    for lf in local_fallbacks:
        if lf not in available:
            available.append(lf)

    return available
```

**Success criteria**: When primary model fails, fallback uses next-highest-weight model that's healthy

---

### 1.5 Health Penalty on Weights

**File**: `packages/intelligent_router_mcp/__init__.py`

**Change**: Add weight adjustment based on circuit breaker state:

```python
def _adjust_weight_for_health(self, model: str, base_weight: float) -> float:
    """Reduce weight based on circuit breaker state."""
    if not self._model_circuit_breaker.can_execute(model):
        breaker = self._model_circuit_breaker.get_breaker(model)
        state = breaker.get_state()

        if state == "open":
            return base_weight * 0.1  # 90% penalty
        elif state == "half_open":
            return base_weight * 0.5  # 50% penalty

    return base_weight
```

**Apply in select_route()**: Before scoring models, adjust weights:
```python
adjusted_weights = {
    m: self._adjust_weight_for_health(m, w)
    for m, w in self._model_weights.items()
}
```

**Success criteria**: Model with OPEN circuit breaker drops to bottom of ranking

---

### 1.6 Weight Staleness Check

**File**: `packages/intelligent_router_mcp/__init__.py`

**Change**: Add staleness warning + blend reduction:

```python
STALENESS_THRESHOLD_SECONDS = 7 * 24 * 3600  # 7 days

def _get_weight_blend_ratio(self) -> float:
    """How much to trust trained weights (1.0 = full trust, 0.0 = no trust)."""
    if self._weights_trained_at == 0:
        return 0.0  # No training data
    age = time.time() - self._weights_trained_at
    if age > STALENESS_THRESHOLD_SECONDS:
        # Linearly decay from 1.0 to 0.5 over 7-14 days
        decay = max(0.5, 1.0 - (age - STALENESS_THRESHOLD_SECONDS) / STALENESS_THRESHOLD_SECONDS)
        return decay
    return 1.0
```

**Success criteria**: Weights older than 7 days trigger warning, blend ratio reduces

---

## Phase 2: Add Missing Features

### 2.1 Active Health Checks

**File**: `scripts/model-health-monitor.py` (enhance) + `packages/intelligent_router_mcp/__init__.py`

**Current**: Only reads static `.sisyphus/model_health.json` file.

**Change**: Implement active health checks:

```python
def _check_ollama_health(self) -> dict:
    """Ping Ollama /api/tags endpoint."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = resp.json().get("models", [])
        return {
            "status": "healthy" if resp.status_code == 200 else "degraded",
            "models": [m["name"] for m in models],
            "latency_ms": resp.elapsed.total_seconds() * 1000,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

def _check_cloud_health(self, provider: str) -> dict:
    """Test cloud provider with minimal request."""
    # Use a lightweight model call to verify connectivity
    pass
```

**Background thread**: Run health checks every 30 seconds, update `model_health.json`

**Success criteria**: Health check runs every 30s, updates health file, circuit breaker reacts

---

### 2.2 Latency Tracking (p50/p95/p99)

**File**: `packages/intelligent_router_mcp/__init__.py`

**Change**: Track latency percentiles per model:

```python
class LatencyTracker:
    def __init__(self, window_size: int = 100):
        self._latencies: Dict[str, List[float]] = defaultdict(list)
        self._window_size = window_size

    def record(self, model: str, latency_ms: float):
        self._latencies[model].append(latency_ms)
        if len(self._latencies[model]) > self._window_size:
            self._latencies[model] = self._latencies[model][-self._window_size:]

    def get_percentiles(self, model: str) -> dict:
        latencies = sorted(self._latencies.get(model, []))
        if not latencies:
            return {"p50": 0, "p95": 0, "p99": 0, "count": 0}
        return {
            "p50": latencies[len(latencies) // 2],
            "p95": latencies[int(len(latencies) * 0.95)],
            "p99": latencies[int(len(latencies) * 0.99)],
            "count": len(latencies),
        }
```

**Success criteria**: `router.get_latency_stats()` returns p50/p95/p99 per model

---

### 2.3 VRAM Monitoring for Local Models

**File**: `scripts/model-health-monitor.py` (enhance)

**Current**: Config defines `vram_limits` but no code checks VRAM.

**Change**: Add VRAM check via `nvidia-smi`:

```python
def _check_vram_usage(self) -> dict:
    """Check GPU VRAM usage via nvidia-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        used, total = map(int, result.stdout.strip().split(","))
        return {
            "used_mb": used,
            "total_mb": total,
            "available_mb": total - used,
            "usage_pct": round(used / total * 100, 1),
        }
    except Exception as e:
        return {"error": str(e)}
```

**Routing impact**: If VRAM < model requirement, skip local model, route to cloud

**Success criteria**: Router skips Ollama models when VRAM insufficient

---

### 2.4 Fix execute_with_fallback

**File**: `packages/intelligent_router_mcp/__init__.py` (lines 2268-2286)

**Current**: `dummy_task_callable` raises `NotImplementedError`.

**Change**: Replace with real fallback execution:

```python
async def _execute_with_fallback(self, task_callable, fallback_models):
    """Execute task with model fallback on failure."""
    last_error = None
    for model in fallback_models:
        try:
            return await task_callable(model)
        except Exception as e:
            last_error = e
            self._model_circuit_breaker.record_failure(model)
            continue
    raise last_error
```

**Success criteria**: Fallback tool executes task across models, records failures

---

### 2.5 Add Ollama Models to MODEL_CAPABILITIES

**File**: `packages/intelligent_router_mcp/__init__.py`

**Current**: `MODEL_CAPABILITIES` only has cloud models.

**Change**: Add Ollama models:

```python
MODEL_CAPABILITIES = {
    # ... existing cloud models ...
    "ollama/qwen2.5-coder:7b": {
        "reasoning": 0.70,
        "coding": 0.75,
        "creative": 0.60,
        "math": 0.65,
        "analysis": 0.68,
        "summarization": 0.65,
        "context_window": 8192,
        "is_local": True,
        "vram_gb": 7,
    },
    "ollama/llama3.2:3b": {
        "reasoning": 0.55,
        "coding": 0.50,
        "creative": 0.60,
        "math": 0.50,
        "analysis": 0.55,
        "summarization": 0.58,
        "context_window": 4096,
        "is_local": True,
        "vram_gb": 4,
    },
}
```

**Success criteria**: Ollama models appear in `brain.analyze_request()` model scores

---

## Phase 3: Advanced Features

### 3.1 Semantic Caching (GPTCache Pattern)

**New file**: `packages/intelligence/semantic_cache.py`

**Features**:
- Exact match cache (hash-based) for identical prompts
- Semantic cache (embedding-based) for similar prompts
- TTL-based expiration
- LRU eviction

**Integration**: Check cache before `select_route()`, store results after response

**Success criteria**: Repeated prompts return cached response, <10ms latency

---

### 3.2 Shadow Mode Evaluation

**File**: `packages/intelligent_router_mcp/__init__.py` (ShadowEvaluator already exists)

**Current**: `ShadowEvaluator` class exists but not activated.

**Change**: Enable shadow mode for 10% of traffic:

```python
def _maybe_shadow_evaluate(self, prompt: str, primary_model: str, result: dict):
    """Evaluate shadow models on 10% of traffic."""
    if random.random() > 0.1:  # 10% shadow rate
        return

    shadow_models = ["opencode/minimax-m2.5-free", "ollama/qwen2.5-coder:7b"]
    for model in shadow_models:
        # Fire async, don't wait
        asyncio.create_task(self._shadow_evaluator.evaluate(model, prompt))
```

**Success criteria**: Shadow evaluations logged, comparison data available

---

### 3.3 Cost-Aware Routing

**File**: `packages/intelligent_router_mcp/__init__.py`

**Change**: Add cost tracking + quality/price scoring:

```python
MODEL_COSTS = {
    "opencode/qwen3.6-plus-free": 0.0,  # free tier
    "opencode/minimax-m2.5-free": 0.0,
    "opencode/gemini-2.5-flash-free": 0.0,
    "ollama/qwen2.5-coder:7b": 0.0,  # local, electricity only
    "ollama/llama3.2:3b": 0.0,
}

def _score_model_cost_quality(self, model: str, prompt: str) -> float:
    """Score = quality / (cost + epsilon). Higher is better."""
    quality = self._estimate_quality(model, prompt)
    cost = MODEL_COSTS.get(model, 0.01)  # Default small cost for unknown
    return quality / (cost + 0.001)
```

**Success criteria**: Router prefers free models when quality is comparable

---

### 3.4 Streaming vs Non-Streaming Routing

**File**: `packages/intelligent_router_mcp/__init__.py`

**Change**: Add streaming decision to `select_route()`:

```python
def _should_stream(self, request: dict) -> bool:
    """Decide streaming based on request characteristics."""
    # Explicit preference
    if request.get("stream") is not None:
        return request["stream"]

    # Chat sessions benefit from streaming
    if request.get("agent_type") in ["sisyphus", "hephaestus"]:
        return True

    # Batch analysis doesn't need streaming
    if request.get("agent_type") in ["explore", "librarian"]:
        return False

    return True  # Default to streaming
```

**Success criteria**: Routing decision includes `stream: true/false` in response

---

### 3.5 A/B Testing Framework

**New file**: `scripts/ab-test-models.py`

**Features**:
- Compare 2+ models on test prompt suite
- Configurable assertions (contains, similarity, latency threshold)
- CI/CD integration
- Results stored in routing outcomes DB

**Success criteria**: `python3 scripts/ab-test-models.py --model-a X --model-b Y` produces comparison report

---

## Testing Strategy

### Unit Tests (Phase 1)

| Test | File | What |
|------|------|------|
| `test_load_trained_weights` | `tests/test_router_weights.py` | Weight loading from JSON |
| `test_model_name_mapping` | `tests/test_router_weights.py` | Short→full name translation |
| `test_agent_overrides` | `tests/test_router_weights.py` | Agent-specific model selection |
| `test_dynamic_fallback` | `tests/test_router_fallback.py` | Weight-sorted fallback chain |
| `test_health_penalty` | `tests/test_router_health.py` | Circuit breaker weight reduction |
| `test_staleness_check` | `tests/test_router_weights.py` | Weight decay over time |

### Integration Tests (Phase 2)

| Test | File | What |
|------|------|------|
| `test_health_check_loop` | `tests/test_health_monitor.py` | Active health checks run every 30s |
| `test_latency_trackinging` | `tests/test_latency_tracker.py` | p50/p95/p99 calculation |
| `test_vram_routing` | `tests/test_vram_routing.py` | Local models skipped when VRAM low |
| `test_fallback_execution` | `tests/test_fallback_execution.py` | Real fallback across models |

### Shadow Tests (Phase 3)

| Test | File | What |
|------|------|------|
| `test_shadow_mode` | `tests/test_shadow_mode.py` | 10% shadow traffic |
| `test_ab_comparison` | `tests/test_ab_comparison.py` | A/B test execution |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Model name mapping incorrect | HIGH | Test each mapping against actual API calls |
| Weight loading breaks existing routing | HIGH | Keep fallback to brain scores if weights fail |
| Health checks add latency | MEDIUM | Run in background thread, non-blocking |
| VRAM check fails on non-GPU systems | LOW | Graceful degradation (skip check, log warning) |
| Semantic cache returns stale responses | MEDIUM | TTL + model version invalidation |

---

## Rollout Plan

1. **Phase 1** → Deploy, verify routing decisions match expected agent→model mapping
2. **Phase 2** → Deploy, monitor health check dashboard, verify latency tracking
3. **Phase 3** → Deploy shadow mode first, validate A/B results, then enable caching

Each phase is independently deployable. No phase depends on a later phase.

# Optimal Delay Calculation & Tool Wrapping Masterplan

> **Goal**: Calculate perfect delays, wrap local models to match cloud quality
> **Date**: 2026-04-06
> **Status**: READY FOR IMPLEMENTATION

---

## CURRENT STATE

### Available Models
- **Local (Ollama)**: qwen2.5-coder:7b, llama3.2:3b, nomic-embed-text:latest
- **Cloud (OpenRouter)**: qwen/qwen3.6-plus:free, minimax/minimax-m2.5:free
- **Rate Limit Issue**: "Request rate increased too quickly" from Alibaba

### Existing Infrastructure
- `src/orchestration/tool_call_collector.py` — Tracks latency, success rates, model hierarchy
- `src/orchestration/react_agent.py` — ReAct agent pattern
- `src/infrastructure/fusion_bridge.py` — Model fusion bridge
- `src/infrastructure/metrics_store.py` — Metrics storage
- `src/infrastructure/telemetry.py` — Telemetry system

---

## OPTIMAL DELAY CALCULATION

### Rate Limit Analysis
- **Free tier models**: ~10 requests/minute (Alibaba/Qwen free tier)
- **Optimal delay**: 6 seconds between requests (60s / 10 requests)
- **With burst tolerance**: 4-6 seconds (allows occasional bursts)

### Dynamic Delay Calculation
```python
def calculate_optimal_delay(metrics, base_delay=6.0):
    """Calculate optimal delay based on recent success/failure rates."""
    recent_failures = metrics.get('recent_failures', 0)
    recent_successes = metrics.get('recent_successes', 0)
    total = recent_failures + recent_successes
    
    if total == 0:
        return base_delay
    
    failure_rate = recent_failures / total
    
    # Increase delay if failures are high
    if failure_rate > 0.3:
        return min(base_delay * 2, 12.0)  # Max 12s delay
    elif failure_rate > 0.1:
        return base_delay * 1.5
    else:
        return max(base_delay * 0.8, 3.0)  # Min 3s delay
```

---

## TOOL WRAPPING FOR LOCAL MODELS

### The Problem
Local models (qwen2.5-coder:7b, llama3.2:3b) don't have native tool calling like cloud models.

### The Solution: Tool Wrapper Layer
```
User Request → Tool Wrapper → Local Model → Parse Response → Execute Tool → Return Result
```

### Implementation Plan

1. **Create `src/tools/tool_wrapper.py`**
   - Wraps local models with tool calling capability
   - Uses structured output parsing
   - Implements ReAct pattern for tool use
   - Falls back to cloud models when local fails

2. **Create `src/tools/local_tool_enhancer.py`**
   - Adds chain-of-thought prompting
   - Implements self-correction loops
   - Adds tool result validation
   - Implements retry with exponential backoff

3. **Create `src/tools/model_router.py`**
   - Routes requests to best available model
   - Uses ToolCallCollector for performance tracking
   - Implements dynamic delay calculation
   - Falls back gracefully on rate limits

---

## IMPLEMENTATION

### Phase 1: Fix Critical Bugs (15 min)
1. Fix BrainPipeline CircuitBreaker import
2. Fix unified_router indent error
3. Verify all imports work

### Phase 2: Create Tool Wrapper (30 min)
1. Create `src/tools/tool_wrapper.py`
2. Create `src/tools/local_tool_enhancer.py`
3. Create `src/tools/model_router.py`
4. Test tool wrapping with local models

### Phase 3: Integrate with Existing System (30 min)
1. Connect tool wrapper to BrainPipeline
2. Connect tool wrapper to unified_router
3. Connect ToolCallCollector to model router
4. Test end-to-end flow

### Phase 4: Optimize Delays (15 min)
1. Implement dynamic delay calculation
2. Add rate limit detection
3. Add exponential backoff
4. Test with rate limit scenarios

---

## FILE STRUCTURE

```
src/
├── tools/
│   ├── tool_wrapper.py           # NEW: Tool calling wrapper for local models
│   ├── local_tool_enhancer.py    # NEW: Enhances local model tool use
│   ├── model_router.py           # NEW: Intelligent model routing
│   └── intelligence/
│       └── unified_router.py     # FIXED: Indent error
├── brain/
│   └── pipeline.py               # FIXED: CircuitBreaker calls
└── orchestration/
    └── tool_call_collector.py    # EXISTING: Performance tracking
```

---

## EXECUTION

Begin with Phase 1: Fix Critical Bugs

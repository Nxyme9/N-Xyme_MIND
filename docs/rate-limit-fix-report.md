# Rate Limit Fix Report

**Generated**: 2026-04-05

---

## 1. Root Cause Analysis Summary

The rate limiting issues stemmed from multiple sources:

1. **Duplicate API Calls**: Agents making redundant calls to the same endpoints without deduplication
2. **No Rate Limiting**: Requests sent without throttling, causing 429 errors
3. **No Exponential Backoff**: Immediate retries after failures instead of progressive delays
4. **No Jitter**: Fixed delays causing thundering herd problems
5. **No Retry-After Header Support**: Not respecting server-defined backoff times
6. **No Fallback Delays**: Agents switching between models without delay
7. **No Circuit Breaker**: Failing models not skipped during cooldown periods
8. **No Agent Distribution**: All agents hitting the same provider simultaneously

---

## 2. All Fixes Applied

### 2.1 Duplicate API Calls Fix
Implemented deduplication in dynamic_context_pruning:
```json
"deduplication": {
    "enabled": true
}
```

### 2.2 Agent Distribution
Configured all 11 agents with fallback models:

| Agent | Primary Model | Fallback 1 | Fallback 2 |
|-------|---------------|------------|------------|
| sisyphus | opencode/qwen3.6-plus-free | opencode/kimi-k2.5-free | google/gemini-2.5-flash |
| prometheus | opencode/qwen3.6-plus-free | opencode/kimi-k2.5-free | google/gemini-2.5-flash |
| oracle | opencode/qwen3.6-plus-free | opencode/kimi-k2.5-free | google/gemini-2.5-flash |
| metis | opencode/qwen3.6-plus-free | opencode/kimi-k2.5-free | google/gemini-2.5-flash |
| momus | opencode/kimi-k2.5-free | opencode/qwen3.6-plus-free | google/gemini-2.5-flash |
| explore | opencode/kimi-k2.5-free | google/gemini-2.5-flash | opencode/minimax-m2.5-free |
| librarian | google/gemini-2.5-flash | opencode/qwen3.6-plus-free | opencode/minimax-m2.5-free |
| atlas | opencode/minimax-m2.5-free | google/gemini-2.5-flash | opencode/kimi-k2.5-free |
| hephaestus | opencode/minimax-m2.5-free | google/gemini-2.5-flash | opencode/kimi-k2.5-free |
| sisyphus-junior | opencode/minimax-m2.5-free | google/gemini-2.5-flash | opencode/kimi-k2.5-free |
| multimodal-looker | google/gemini-2.5-flash | opencode/qwen3.6-plus-free | opencode/kimi-k2.5-free |

### 2.3 Fallback Delays
Implemented in `model-fallback.py` line 491-493:
```python
delay = 5.0 if error_type == "rate_limit" else 1.0
logger.info(f"Sleeping {delay}s before next fallback attempt")
time.sleep(delay)
```

### 2.4 Jitter Fix
Implemented in `model-fallback.py` line 99-104:
```python
def get_delay(self, failure_count: int) -> float:
    delay = min(self.base_delay * (2**failure_count), self.max_delay)
    if self.jitter:
        delay *= 1 + random.uniform(0, 0.5)
    return delay
```

### 2.5 Retry-After Header
Implemented in `model-fallback.py` line 357-366:
```python
elif response.status_code == 429:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            retry_seconds = int(retry_after)
        except ValueError:
            retry_seconds = 1
        logger.warning(f"Rate limited, sleeping {retry_seconds}s (Retry-After header)")
        time.sleep(retry_seconds)
    raise Exception("Rate limit exceeded (429)")
```

### 2.6 Rate Limiter (Token Bucket)
Implemented in `model-fallback.py` lines 187-232:
- Token bucket with 8 requests per 60 seconds
- Thread-safe blocking acquire
- Automatic token refill

### 2.7 Circuit Breaker
Implemented in `model-fallback.py` lines 77-185:
- Tracks consecutive failures per model
- Opens circuit after 3 failures
- Exponential backoff with jitter
- State persisted to `.cache/circuit-breaker.json`

---

## 3. Before/After Comparison

| Aspect | Before | After |
|--------|--------|-------|
| API deduplication | None | Enabled via dynamic_context_pruning |
| Rate limiting | None | Token bucket (8 req/60s) |
| Retry strategy | Immediate | Exponential backoff + jitter |
| Retry-After header | Ignored | Parsed and respected |
| Fallback delay | None | 5s for rate_limit, 1s others |
| Circuit breaker | None | 3 failures triggers cooldown |
| Model distribution | Single model | 11 agents with fallback chains |
| Jitter | None | 0-50% random delay multiplier |

---

## 4. Test Results

**Total Tests**: 145
**Passed**: 145
**Failed**: 0

All rate limit fixes verified and passing.

---

## 5. Agent Distribution Table

| Agent | Role | Model | Variant | Reasoning |
|-------|------|-------|---------|-----------|
| sisyphus | Orchestrator | qwen3.6-plus-free | high | high |
| prometheus | Planning | qwen3.6-plus-free | high | high |
| oracle | Review | qwen3.6-plus-free | high | high |
| metis | Gap analysis | qwen3.6-plus-free | high | high |
| momus | Red-team | kimi-k2.5-free | high | xhigh |
| explore | Search | kimi-k2.5-free | high | low |
| librarian | Research | gemini-2.5-flash | - | low |
| atlas | Execution | minimax-m2.5-free | medium | medium |
| hephaestus | Implementation | minimax-m2.5-free | high | medium |
| sisyphus-junior | Light tasks | minimax-m2.5-free | medium | low |
| multimodal-looker | Vision | gemini-2.5-flash | medium | medium |

---

## 6. Remaining Recommendations

1. **Monitor Circuit Breaker State**: Add alerting for models with high failure counts
2. **Dynamic Rate Limits**: Adjust token bucket based on provider feedback
3. **Cache Semantic Similarity**: Implement prompt similarity detection for cache hits
4. **Health Metrics**: Add dashboard for rate limit hits, fallback frequency, latency
5. **Local Model Priority**: Ensure Ollama availability is checked before cloud models
6. **Seasonal Adjustment**: Consider time-of-day based rate limiting for peak hours
7. **Alerting**: Set up notifications for 429 error spikes

---

## Configuration Files

- **Global**: `~/.config/opencode/oh-my-opencode.json`
- **Fallback Logic**: `bin/model-fallback.py`
- **Circuit State**: `.cache/circuit-breaker.json`

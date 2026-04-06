# Test Report

**Generated**: 2026-04-04T16:40:49.429742

---

## Test Summary

- **Total Tests**: 27
- **Passed**: 26
- **Failed**: 1
- **Skipped**: 0

### Errors

- [ 60%]
- tests/test_integration.py::TestModelRouter::test_env_override - Assert...

---

## Coverage

### Tested Modules

- model_config
- model_router

### Untested Modules

- model_fallback
- model_selector
- prompt_cache

---

## Benchmark Results

- **Latency**: 0.00 ms
- **Throughput**: 0.00 req/s
- **Cache Hit Rate**: 0.00%
- **Iterations**: 200

---

## Migration Status

### Using Environment Variables (needs migration)

_None_

### Using Config Files (migrated)

- model-fallback.py
- generate-report.py
- model_config.py
- benchmark-models.py

---

## Health Check

**Status**: HEALTHY

- blink: healthy
- pulse: healthy

---

## Recommendations

1. Fix 1 failing tests to ensure code quality
2. Add tests for untested modules: model_fallback, model_selector, prompt_cache
3. Improve cache hit rate by adding more semantic caching for similar prompts

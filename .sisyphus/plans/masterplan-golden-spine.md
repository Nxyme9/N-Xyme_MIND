# Golden Spine Masterplan — Revised, Optimized, Fully Featured

> Created: 2026-04-07 | Priority: P0 (Highest ROI)
> Source: 3-agent research (Explore + Librarian + Oracle) + Archive extraction
> Goal: Isolated, resilient execution path that never breaks when cortex code breaks

---

## The Core Philosophy

> *"Seal Golden Spine v1 as an isolated, boring path that never breaks when cortex code breaks."*

The Golden Spine is NOT another AI feature. It's **infrastructure insurance** — a separate execution path that continues working even when the entire application layer is broken.

**Analogy**: Control plane vs data plane in Kubernetes. The control plane can crash, but the data plane (your workloads) keeps running.

---

## What We Already Have (13 Reusable Components)

| Component | Location | What It Does | Reuse |
|-----------|----------|--------------|-------|
| **Ollama Client** | `packages/local_llm/ollama_client.py` | HTTP client with tool calling | ✅ Direct |
| **Tool Execution** | `packages/local_llm/wrapper.py` | 2-pass pipeline: model → tools → return | ✅ Direct |
| **Circuit Breaker (Runtime)** | `packages/infrastructure/resilience/circuit_breaker.py` | CLOSED→OPEN→HALF_OPEN states | ✅ Direct |
| **Circuit Breaker (Persistent)** | `packages/intelligence/circuit_breaker.py` | State persistence to JSON | ✅ Direct |
| **Fallback Chain** | `packages/intelligence/fallback.py` | Model failover (local→cloud) | ✅ Direct |
| **Retry Handler** | `packages/infrastructure/resilience/retry_handler.py` | Exponential backoff | ✅ Direct |
| **Rate Limiter** | `packages/infrastructure/resilience/rate_limiter.py` | Token bucket | ✅ Direct |
| **Health Monitor** | `packages/infrastructure/proxy/health_monitor.py` | HTTP health checks | ✅ Direct |
| **VCR Recorder** | `packages/intelligence/request_recorder.py` | Request/response recording | ✅ Direct |
| **Config Manager** | `packages/infrastructure/config/config_manager.py` | YAML/JSON with env overrides | ✅ Direct |
| **CLI Pattern** | `packages/platform_layer/cli/worker-cli.py` | argparse subcommands | ✅ Reference |
| **Session Hooks** | `packages/nx-mind-mcp/session_hooks.py` | Context injection | ✅ Direct |
| **Session Writer** | `packages/nx-mind-mcp/session_writer.py` | Context persistence | ✅ Direct |

**Zero new dependencies needed.** Everything exists. We just wire them together.

---

## Architecture: The Golden Spine

```
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER (Complex, Can Break)        │
│  memory_core ↔ learning_engine ↔ orchestration ↔ intelligence   │
│  (Can crash, can fail, can be restarted — doesn't matter)       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼ (HTTP only, no shared state)
┌─────────────────────────────────────────────────────────────────┐
│                    GOLDEN SPINE (Boring, Isolated)               │
│                                                                  │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │ Config   │→ │ Circuit      │→ │ LocalLLM    │→ │ Run      │ │
│  │ Manager  │  │ Breaker      │  │ (Ollama)    │  │ Tracker  │ │
│  └──────────┘  └──────────────┘  └─────────────┘  └──────────┘ │
│       ↑               ↑                ↑               ↑        │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │ Health   │  │ Retry        │  │ Fallback    │  │ Rate     │ │
│  │ Monitor  │  │ Handler      │  │ Chain       │  │ Limiter  │ │
│  └──────────┘  └──────────────┘  └─────────────┘  └──────────┘ │
│                                                                  │
│  Interface: start() | stop() | probe() | run() | status()       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼ (HTTP to localhost:11434)
┌─────────────────────────────────────────────────────────────────┐
│                    OLLAMA (External Process)                     │
│  qwen2.5-coder:7b | llama3.2:3b | nomic-embed-text              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 16 Action Plan — 9 Tasks, ~8hr

### T16.1: Create Spine Package Structure (15min)
**Files**: `packages/infrastructure/spine/__init__.py`
**Action**: Create package with exports: `GoldenSpine`, `SpineConfig`, `RunRecord`

### T16.2: Implement SpineConfig (15min)
**Files**: `packages/infrastructure/spine/config.py`
**Action**: Dataclass with model_path, bind_host, port, ctx, gpu_layers, fallback_models, failure_threshold, reset_timeout, max_retries

### T16.3: Implement RunRecord + RunTracker (30min)
**Files**: `packages/infrastructure/spine/run_tracker.py`
**Action**: SQLite-based run tracking with request/response/metadata storage. Structured logging with request correlation IDs.

### T16.4: Implement Spine Health Probe (30min)
**Files**: `packages/infrastructure/spine/health.py`
**Action**: 3-layer health: process alive → model loaded → can respond. Background monitoring thread.

### T16.5: Implement Spine Fallback Chain (30min)
**Files**: `packages/infrastructure/spine/fallback.py`
**Action**: Wrap `packages/intelligence/fallback.py` with spine-specific configuration. Model rotation on failure.

### T16.6: Implement GoldenSpine Core (2hr)
**Files**: `packages/infrastructure/spine/spine.py`
**Action**: Main orchestrator class that wraps LocalLLM with circuit breakers, retry, fallback, health monitoring. Methods: start(), stop(), probe(), run(), status(), config().

### T16.7: Implement Spine CLI (1hr)
**Files**: `packages/infrastructure/spine/cli.py`
**Action**: argparse CLI: `spine start|stop|probe|run|status|config`. JSON output for machine readability.

### T16.8: Integrate with Existing System (1hr)
**Files**: `packages/local_llm/integration.py`, `packages/nx-mind-mcp/`
**Action**: Add spine as optional resilient layer. Add MCP tools: `spine_probe()`, `spine_run()`, `spine_status()`.

### T16.9: Write Tests (2hr)
**Files**: `packages/infrastructure/spine/tests/`
**Action**: Test failure scenarios: circuit breaker opens, fallback triggers, health probe fails, run tracking persists.

---

## Delegation Chain

```
Sisyphus (Orchestrator)
    ↓
┌─────────────────────────────────────────────────────────────┐
│ WAVE 1 (Parallel — Independent, 1hr)                       │
├─────────────────────────────────────────────────────────────┤
│ Hephaestus #1: T16.1-T16.3 (Structure + Config + Tracker)  │
│ Hephaestus #2: T16.4-T16.5 (Health + Fallback)             │
└─────────────────────────────────────────────────────────────┘
    ↓ (Verify Wave 1)
┌─────────────────────────────────────────────────────────────┐
│ WAVE 2 (Sequential — T16.6 depends on Wave 1, 2hr)         │
├─────────────────────────────────────────────────────────────┤
│ Hephaestus #3: T16.6 (GoldenSpine Core)                    │
└─────────────────────────────────────────────────────────────┘
    ↓ (Verify Wave 2)
┌─────────────────────────────────────────────────────────────┐
│ WAVE 3 (Parallel — Independent, 3hr)                       │
├─────────────────────────────────────────────────────────────┤
│ Hephaestus #4: T16.7 (CLI)                                 │
│ Hephaestus #5: T16.8 (Integration)                         │
│ Hephaestus #6: T16.9 (Tests)                               │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ FINAL: Oracle Review → Momus Review → Commit → Push        │
└─────────────────────────────────────────────────────────────┘
```

---

## Success Criteria

- [ ] `GoldenSpine` class wraps LocalLLM with full resilience pipeline
- [ ] Circuit breaker opens after 3 consecutive failures
- [ ] Fallback chain rotates to secondary model on failure
- [ ] Health probe verifies: process alive → model loaded → can respond
- [ ] Run tracking stores request/response/metadata in SQLite
- [ ] CLI: `spine start|stop|probe|run|status|config` all work
- [ ] MCP tools: `spine_probe()`, `spine_run()`, `spine_status()` available
- [ ] All tests pass (failure scenarios covered)
- [ ] Zero new dependencies
- [ ] Committed and pushed

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Circular imports between spine and local_llm | Medium | High | Use lazy imports, dependency injection |
| Circuit breaker state lost on restart | Low | Medium | Use persistent circuit breaker from intelligence/ |
| Ollama process management conflicts | Low | Medium | Spine doesn't manage Ollama — assumes external |
| Run tracking slows down inference | Low | Low | Async logging, batch writes |

---

## Effort Estimate

| Wave | Tasks | Effort | Parallel? |
|------|-------|--------|-----------|
| Wave 1: Structure + Health + Fallback | T16.1-T16.5 | 1.5hr | ✅ Parallel |
| Wave 2: Core Orchestrator | T16.6 | 2hr | ❌ Sequential |
| Wave 3: CLI + Integration + Tests | T16.7-T16.9 | 4hr | ✅ Parallel |
| **Total** | **9 tasks** | **~7.5hr** | |

---

*Masterplan created: 2026-04-07 | 9 tasks, 7.5hr, zero new dependencies*

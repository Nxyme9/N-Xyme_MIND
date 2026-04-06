# Master Plan: Seamless Local↔Cloud Model Switching in OpenCode

**Generated**: 2026-04-06
**Hardware**: AMD Ryzen 7 7800X3D, 32GB RAM, RTX 3080 Ti (12GB VRAM)

---

## Executive Summary

Build intelligent routing that automatically switches between:
- **Local**: qwen2.5-coder:7b, llama3.2:3b (Ollama port 11434)
- **Cloud**: opencode/minimax-m2.5-free, openrouter models

**Target**: Seamless switching based on task complexity, availability, and performance.

---

## Current Architecture (GAP ANALYSIS)

| Component | Status | Gap |
|-----------|--------|-----|
| Ollama (port 11434) | ✅ Running | - |
| Provider config (opencode.json) | ✅ Configured | Hardcoded to minimax-m2.5-free |
| intelligent-router MCP | ⚠️ Defined | Not used |
| Health monitoring | ❌ Missing | No circuit breaker |
| Fallback chain | ❌ Missing | No auto-fallback |

**4 parallel routing systems exist** (HybridRouter, ModelRouter, Intelligent Router MCP, ModelFallback) but NONE are integrated with OpenCode's core.

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal**: Basic routing infrastructure

| Task | File | Action |
|------|------|--------|
| Create routing config | `config/model_router.json` | NEW - routing rules |
| Health check script | `scripts/model-health-monitor.py` | NEW - 30s interval checks |
| Test basic routing | - | Verify local responds <2s |

### Phase 2: Intelligent Routing (Week 2)
**Goal**: Complexity-based model selection

| Task | File | Action |
|------|------|--------|
| Complexity classifier | `packages/intelligence/routing_decision.py` | NEW |
| Integrate with MCP | `packages/intelligent_router_mcp/` | MODIFY |
| Agent overrides | `opencode.json` agent configs | MODIFY |

### Phase 3: Fallback & Resilience (Week 3)
**Goal**: Auto-fallback when models fail

| Task | File | Action |
|------|------|--------|
| Fallback chain | `packages/intelligence/fallback.py` | NEW |
| Circuit breaker | `packages/intelligence/circuit_breaker.py` | NEW |
| Health → brain-cli | `scripts/brain_mcp.py` | MODIFY |

### Phase 4: RTX 3080 Ti Optimization (Week 4)
**Goal**: Maximum local inference performance

| Task | Action |
|------|--------|
| VRAM monitoring | Auto-switch models based on 12GB limit |
| Model warm-up | Pre-load during idle |
| Latency optimization | Provider selection by fastest response |

---

## Configuration Approach (opencode.json)

```json
{
  "model_router": {
    "enabled": true,
    "default_provider": "ollama",
    "fallback_chain": [
      {"provider": "ollama", "model": "qwen2.5-coder:7b"},
      {"provider": "ollama", "model": "llama3.2:3b"},
      {"provider": "opencode", "model": "minimax-m2.5-free"},
      {"provider": "openrouter", "model": "mimo-v2-pro-free"}
    ],
    "latency_threshold": {
      "local_ms": 2000,
      "cloud_ms": 5000
    }
  },
  "agent": {
    "hephaestus": {
      "model": "qwen2.5-coder:7b",
      "router_override": {"preferred_provider": "ollama", "fallback_to_cloud": true}
    },
    "oracle": {
      "model": "minimax-m2.5-free",
      "router_override": {"skip_local": true}
    }
  }
}
```

---

## Decision Criteria

### When to use LOCAL:
- Task complexity: L1 (simple) - L3 (medium)
- VRAM available: >5GB
- Latency requirement: <2s
- Offline mode: No internet

### When to use CLOUD:
- Task complexity: L4 (complex) - L5 (architectural)
- VRAM available: <5GB
- Context needed: >32K tokens
- Offline mode: N/A

---

## Fallback Chain

```
qwen2.5-coder:7b → llama3.2:3b → minimax-m2.5-free → openrouter free
     ↓ (fail)        ↓ (fail)           ↓ (fail)           ↓ (fail)
   Circuit       Circuit            Rate Limit         Report Error
   Breaker       Breaker            Retry 3x
```

---

## Files to Create/Modify

### Create (NEW):
- `config/model_router.json` - Routing rules
- `scripts/model-health-monitor.py` - Health check daemon
- `packages/intelligence/routing_decision.py` - Complexity classifier
- `packages/intelligence/fallback.py` - Fallback chain logic
- `packages/intelligence/circuit_breaker.py` - Circuit breaker

### Modify (EXISTING):
- `opencode.json` - Add model_router section, agent overrides
- `packages/intelligent_router_mcp/__init__.py` - Integrate routing
- `scripts/brain_mcp.py` - Display health status

---

## Verification Checklist

- [ ] Local models respond <2s
- [ ] Cloud models respond <5s
- [ ] Fallback activates within 2s of failure
- [ ] Circuit breaker disables model after 3 failures
- [ ] Health status displays in brain-cli
- [ ] VRAM never exceeds 12GB
- [ ] Offline mode works with local models

---

## Key Resources

- **OpenCode Config Docs**: https://opencode.ai/docs/config/
- **MCP Servers**: https://opencode.ai/docs/mcp-servers/
- **Provider Setup**: https://opencode.ai/docs/providers/
- **Agent Fallbacks**: https://docs.8labs.id/docs/opencode/configuration

---

## Next Steps

1. **Start Phase 1**: Create `config/model_router.json` with basic routing rules
2. **Test locally**: Verify qwen2.5-coder:7b responds <2s
3. **Add health check**: Implement 30s interval monitoring
4. **Iterate**: Build complexity classifier in Phase 2
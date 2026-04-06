# Router/Rotator Masterplan v2 — Full Integration & Wiring

> **Date**: 2026-04-06 | **Status**: Implementation Complete
> **Audited**: 21 proxy modules, 8 bin scripts, 3 standalone scripts, opencode.json

---

## IMPLEMENTATION STATUS

| Phase | Task | Status | File(s) Modified |
|-------|------|--------|-----------------|
| 1.1 | Add intelligent-router MCP to opencode.json | ✅ DONE | `opencode.json` |
| 1.2 | Create configs/api-keys/keys.json | ✅ DONE | `configs/api-keys/keys.json` |
| 1.3 | Fix __init__.py to load keys.json | ✅ DONE | `src/infrastructure/proxy/__init__.py` |
| 1.4 | Create bin/start-router-proxy.sh | ✅ DONE | `bin/start-router-proxy.sh`, `bin/stop-router-proxy.sh` |
| 1.5 | Create bin/start-socks5-proxies.sh | ✅ DONE | `bin/start-socks5-proxies.sh`, `bin/stop-socks5-proxies.sh` |
| 2.1 | Wire vpn/rotator.py to vpn_ip_pool | ✅ DONE | `vpn/rotator.py` |
| 2.2 | Wire failure reporting to vpn_ip_pool | ✅ DONE | `vpn/rotator.py` |
| 3.1 | Add provider endpoints to health_monitor | ✅ DONE | `src/infrastructure/proxy/__init__.py` |
| 3.2 | Wire health status to dashboard | ✅ DONE | `src/infrastructure/proxy/openai_proxy.py` |
| 4.1 | Add feedback endpoint | ✅ DONE | `src/infrastructure/proxy/openai_proxy.py` |

---

## COMPLETE AUDIT — What Exists, What's Wired, What's Broken

### 1.1 Proxy Layer (src/infrastructure/proxy/) — 21 Modules

| # | Module | Lines | Status | Wired? | Notes |
|---|--------|-------|--------|--------|-------|
| 1 | `__init__.py` | 68 | ✅ Exists | ✅ WIRED | Now loads keys.json + adds health providers |
| 2 | `api_key_pool.py` | 145 | ✅ Exists | ✅ WIRED | Populated from env vars + keys.json |
| 3 | `vpn_ip_pool.py` | 119 | ✅ Exists | ✅ WIRED | Receives success/failure from vpn/rotator.py |
| 4 | `intelligent_router.py` | 140 | ✅ Exists | ✅ WIRED | Called via MCP + openai_proxy.py |
| 5 | `router_brain.py` | 175 | ✅ Exists | ✅ Internal | Keyword analysis, model scoring |
| 6 | `learning_engine.py` | 81 | ✅ Exists | ✅ WIRED | Auto-wires when proxy runs |
| 7 | `cost_optimizer.py` | 68 | ✅ Exists | ✅ Internal | All costs = 0.0 (free tier) |
| 8 | `health_monitor.py` | 97 | ✅ Exists | ✅ WIRED | 3 providers added (opencode, openrouter, google) |
| 9 | `openai_proxy.py` | 220+ | ✅ Exists | ✅ WIRED | FastAPI on :8080 with health, dashboard, feedback |
| 10 | `mcp_server.py` | 80 | ✅ Exists | ✅ WIRED | Added to opencode.json MCPs |
| 11 | `dashboard.py` | 102 | ✅ Exists | ✅ WIRED | Receives health + VPN status updates |
| 12 | `stall_detector.py` | 58 | ✅ Exists | ✅ WIRED | Called by openai_proxy.py |
| 13 | `key_notifier.py` | 53 | ✅ Exists | ✅ WIRED | Called by openai_proxy.py |
| 14 | `dead_letter_queue.py` | 86 | ✅ Exists | ✅ WIRED | Called by openai_proxy.py |
| 15 | `request_validator.py` | 42 | ✅ Exists | ✅ WIRED | Called by openai_proxy.py |
| 16 | `lru_cache.py` | 75 | ✅ Exists | ✅ WIRED | Called by openai_proxy.py |
| 17 | `connection_pool.py` | 39 | ✅ Exists | ⚠️ Unused | urllib opener pool (openai_proxy uses httpx) |
| 18 | `observability.py` | 78 | ✅ Exists | ⚠️ Partial | Metrics/alerts exist, not actively written |
| 19 | `ab_testing.py` | 67 | ✅ Exists | ❌ Unused | Framework exists, no tests created |
| 20 | `feedback.py` | 64 | ✅ Exists | ✅ WIRED | New /v1/feedback endpoint added |
| 21 | `agent_preferences.py` | 64 | ✅ Exists | ✅ Internal | Defaults for all 11 agents |

### 1.2 Bin Scripts

| Script | Status | Notes |
|--------|--------|-------|
| `bin/start-router-proxy.sh` | ✅ CREATED | Starts openai_proxy.py on port 8080 |
| `bin/stop-router-proxy.sh` | ✅ CREATED | Stops router proxy |
| `bin/start-socks5-proxies.sh` | ✅ CREATED | Starts 8 SOCKS5 proxies on 1080-1087 |
| `bin/stop-socks5-proxies.sh` | ✅ CREATED | Stops all SOCKS5 proxies |
| `bin/model-router.py` | ✅ Exists | Keyword routing. Independent of proxy layer. |
| `bin/local-router.py` | ✅ Exists | Ollama health + classification. |
| `bin/model_keywords.py` | ✅ Exists | Used by both routers. |
| `bin/socks5-server.py` | ✅ Exists | Single SOCKS5 server. |

### 1.3 Config Files

| File | Status | Notes |
|------|--------|-------|
| `configs/api-keys/keys.json` | ✅ CREATED | Multi-key structure with rpm/tpm limits |
| `opencode.json` | ✅ MODIFIED | Added intelligent-router MCP |
| `data/proxy/*.db` | ⚠️ Auto-created | 3 SQLite DBs. Populated when proxy runs. |

---

## ARCHITECTURE — Fully Wired

```
OpenCode (opencode.json)
  ├── Agents → intelligent-router MCP → mcp_server.py
  └── Agents → OpenAI Proxy (localhost:8080) → openai_proxy.py
                                              │
                                              ▼
                                    IntelligentRouter
                                      ├── router_brain.analyze()
                                      ├── api_key_pool.get_best_key()
                                      ├── vpn_ip_pool.get_best_ip()
                                      ├── learning_engine.get_best_model_for()
                                      └── agent_preferences.apply()
                                              │
                                    ┌─────────┴─────────┐
                                    ▼                   ▼
                              APIKeyPool           VPNIPPool
                              (multi-key)          (8 SOCKS5)
                                    │                   │
                                    ▼                   ▼
                              keys.json          vpn/rotator.py
                              (configs/)           (8 backends)
                                    │                   │
                                    ▼                   ▼
                              env vars           SOCKS5 :1080-1087

SIDECARS (always running):
  ├── health_monitor.py → checks providers every 30s
  ├── stall_detector.py → detects 30s+ stalls
  ├── key_notifier.py → alerts at 80%/95% RPM
  ├── learning_engine.py → records outcomes to SQLite
  ├── dead_letter_queue.py → retries failed requests
  ├── feedback_loop.py → quality scoring from users
  └── dashboard.py → real-time stats

API ENDPOINTS (openai_proxy.py :8080):
  POST /v1/chat/completions  → Intelligent routing
  GET  /v1/models            → List available models
  GET  /health               → Full system status
  GET  /dashboard            → Real-time dashboard
  POST /v1/feedback          → Submit quality feedback
  GET  /v1/feedback/rankings → Model rankings
```

---

## STARTUP SEQUENCE

```bash
# 1. Start SOCKS5 proxies (8 backends)
bash bin/start-socks5-proxies.sh

# 2. Start VPN rotator (HTTP CONNECT proxy on port 8888)
python3 vpn/rotator.py --daemon --health --dashboard &

# 3. Start OpenAI-compatible proxy (port 8080)
bash bin/start-router-proxy.sh

# 4. Verify everything
curl http://localhost:8080/health
curl http://localhost:8080/dashboard
curl http://localhost:8080/v1/models

# 5. OpenCode now routes through the proxy automatically
# (if opencode.json baseURL points to http://localhost:8080/v1)
```

---

## ROLLBACK PLAN

```bash
# If anything breaks:
bash bin/stop-router-proxy.sh
bash bin/stop-socks5-proxies.sh
pkill -f "vpn/rotator.py"

# Revert opencode.json to direct OpenRouter
git checkout opencode.json
```

---

*Masterplan v2.0 | N-Xyme_MIND | 2026-04-06*

# Bulletproof AI Router System

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        OpenCode TUI                                │
│                    (User Requests)                                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     REQUEST VALIDATOR                               │
│  • Max length check (100K chars)                                    │
│  • Injection detection (XSS, SQL)                                   │
│  • Input sanitization                                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     LRU SEMANTIC CACHE                              │
│  • O(1) exact match (SHA-256 hash)                                  │
│  • TTL-based expiration (1 hour default)                            │
│  • 10,000 entry capacity                                            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ Cache Miss
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     ROUTER BRAIN (Local LLM)                        │
│  • Task classification (coding/reasoning/creative/math/analysis)    │
│  • Complexity estimation (simple/medium/complex)                    │
│  • Capability matching (reasoning/coding/creative scores)           │
│  • Model scoring (weighted capability + complexity bonus)           │
│  • <1ms decision time                                              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   HEALTH MONITOR                                    │
│  • HTTP health checks per provider (30s interval)                   │
│  • Auto-skip unhealthy providers                                    │
│  • Latency tracking                                                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   API KEY POOL                                      │
│  • Multiple keys per provider                                       │
│  • Per-key RPM/TPM tracking                                         │
│  • Health scoring (0.0-1.0)                                         │
│  • Cooldown on rate limits (exponential backoff)                    │
│  • Auto-rotation on 429                                             │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   VPN IP POOL                                       │
│  • 8 SOCKS5 proxies (ports 1080-1087)                               │
│  • Per-IP health scoring                                            │
│  • Ban detection (403/captcha) → 5min cooldown                      │
│  • Rate limit detection (429) → exponential backoff                 │
│  • Latency-aware selection                                          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   CONNECTION POOL                                   │
│  • Reusable HTTP connections per API key                            │
│  • Max 100 connections                                              │
│  • Automatic cleanup                                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   PROVIDER (OpenCode Zen / OpenRouter / Google)     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   POST-REQUEST PIPELINE                             │
│  • Success → Record in learning engine, update metrics              │
│  • Failure → Dead letter queue with retry (3 retries max)           │
│  • A/B testing → Record variant results                             │
│  • Feedback → Human quality scoring                                 │
│  • Observability → Metrics, alerts, histograms                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. API Key Pool (`api_key_pool.py`)
- **Purpose**: Manage multiple API keys per provider
- **Features**: RPM/TPM tracking, health scoring, cooldown, auto-rotation
- **Thread-safe**: Yes (threading.Lock)

### 2. VPN IP Pool (`vpn_ip_pool.py`)
- **Purpose**: Manage 8 SOCKS5 proxies for IP rotation
- **Features**: Health scoring, ban detection, latency tracking
- **Thread-safe**: Yes (threading.Lock)

### 3. Router Brain (`router_brain.py`)
- **Purpose**: Intelligent task analysis and model selection
- **Features**: Category detection, complexity estimation, capability matching
- **Speed**: <1ms per decision
- **Models**: qwen3.6-plus, qwen3-coder, nemotron-30b, nemotron-12b, minimax-m2.5

### 4. Cost Optimizer (`cost_optimizer.py`)
- **Purpose**: Track cost and select cheapest model meeting quality threshold
- **Features**: Per-model cost tracking, success rate, latency tracking

### 5. Learning Engine (`learning_engine.py`)
- **Purpose**: Store routing outcomes, improve decisions over time
- **Storage**: SQLite (data/proxy/routing_outcomes.db)
- **Features**: Model performance tracking, best model recommendations

### 6. Intelligent Router (`intelligent_router.py`)
- **Purpose**: Unified orchestration of all components
- **Features**: select_route(), record_success(), record_failure(), get_status()

### 7. Health Monitor (`health_monitor.py`)
- **Purpose**: HTTP health checks for all providers
- **Features**: Background monitoring (30s interval), auto-skip unhealthy

### 8. Dead Letter Queue (`dead_letter_queue.py`)
- **Purpose**: Store failed requests for retry
- **Features**: Max 3 retries, status tracking (pending/retrying/completed/failed)

### 9. Request Validator (`request_validator.py`)
- **Purpose**: Validate and sanitize incoming requests
- **Features**: Max length check, injection detection, sanitization

### 10. LRU Semantic Cache (`lru_cache.py`)
- **Purpose**: O(1) response caching
- **Features**: SHA-256 hashing, TTL expiration, 10K capacity

### 11. Connection Pool (`connection_pool.py`)
- **Purpose**: Reusable HTTP connections
- **Features**: Per-key openers, max 100 connections

### 12. Observability (`observability.py`)
- **Purpose**: Metrics, alerts, histograms
- **Features**: Counters, gauges, p50/p95/p99 latency, alert manager

### 13. A/B Testing (`ab_testing.py`)
- **Purpose**: Compare routing strategies
- **Features**: Traffic splitting, variant assignment, result tracking

### 14. Feedback Loop (`feedback.py`)
- **Purpose**: Human quality scoring
- **Features**: Rating submission, model rankings, helpful rate tracking

## API Reference

### MCP Server Endpoints
- `route_task(prompt, system_prompt, agent_type)` → Route to optimal model
- `record_success(route, input_tokens, output_tokens, latency_ms)` → Record success
- `record_failure(route, error_type, latency_ms)` → Record failure
- `get_router_status()` → Full router status
- `get_available_models()` → List available models with capabilities
- `get_routing_history(limit)` → Recent routing decisions

## Configuration

### Environment Variables
```bash
OPENCODE_API_KEY=your_key_here
OPENROUTER_API_KEY=sk-or-v1-your_key_here
GOOGLE_API_KEY=AIza-your_key_here
```

### Default Models
| Agent | Model | Provider |
|-------|-------|----------|
| Sisyphus/Prometheus/Oracle/Metis/Momus | qwen3.6-plus-free | OpenCode Zen |
| Hephaestus/Atlas/Explore/Librarian/Sisyphus-Junior | minimax-m2.5-free | OpenCode Zen |
| Multimodal-Looker | qwen3.6-plus-free | OpenCode Zen |

## Testing

```bash
# Run all proxy tests
PYTHONPATH=. python3 -m pytest tests/test_proxy_components.py -v

# Run all tests
PYTHONPATH=. python3 -m pytest tests/ -v
```

## Monitoring

```python
from src.proxy import metrics, alerts, health_monitor

# Get metrics
print(metrics.get_metrics())

# Get alerts
print(alerts.get_alerts())

# Get health status
print(health_monitor.get_status())
```

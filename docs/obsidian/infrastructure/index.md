# Infrastructure Layer

## Overview

The Infrastructure Layer provides platform services including proxy routing, network management, resilience patterns, monitoring, and cost tracking. It implements bulletproof, lightspeed, accurate, self-learning LLM routing with IP rotation, health monitoring, and intelligent failover.

## Public API

```python
# Circuit breaker
cb = CircuitBreaker("opencode", config)
if cb.allow_request():
    # Make request

# Cost tracking
tracker = CostTracker()
tracker.record(model="qwen", tokens=1000, cost=0.01)

# Metrics store
store = MetricsStore()
store.record(metric_name="latency", value=150)
```

## Architecture

### Core Modules

| Module | Purpose | Key Classes | Key Functions |
|--------|---------|-------------|---------------|
| proxy/__init__.py | Main proxy module | APIKeyPool, VPNIPPool, RouterBrain | routing logic |
| proxy/api_key_pool.py | API key management | APIKeyPool | add_key(), get_key(), rotate() |
| proxy/vpn_ip_pool.py | VPN IP rotation | VPNIPPool | rotate(), get_current() |
| proxy/router_brain.py | Routing brain | RouterBrain | route(), decide() |
| proxy/cost_optimizer.py | Cost tracking | CostTracker | record(), get_cost() |
| proxy/health_monitor.py | Health monitoring | HealthMonitor | check(), add_provider() |
| proxy/intelligent_router.py | Intelligent routing | IntelligentRouter | route() |
| proxy/dead_letter_queue.py | Failed requests | DeadLetterQueue | enqueue(), retry() |
| proxy/request_validator.py | Request validation | RequestValidator | validate() |
| proxy/lru_semantic_cache.py | Semantic caching | LRUSemanticCache | get(), set() |
| proxy/connection_pool.py | Connection pooling | ConnectionPool | acquire(), release() |
| proxy/ab_testing.py | A/B testing | ABTestingFramework | start_test(), record() |
| resilience/circuit_breaker.py | Fault tolerance | CircuitBreaker, CircuitState | record_success(), record_failure() |
| monitoring/metrics.py | Metrics collection | MetricsStore | record(), query() |
| cost/tracker.py | Cost management | CostTracker, ModelProvider, UsageRecord | track(), summarize() |
| spine/ | Golden Spine execution | SpineConfig, get_run_record(), get_golden_spine() | model serving |

### Network Module

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| network/ | Network utilities | - |

### Config Module

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| config/ | Configuration management | - |

## Components

### API Key Pool

- **Purpose**: Manage multiple API keys per provider with rate limiting
- **Key Methods**:
  - `add_key()`: Add API key with RPM/TPM limits
  - `get_key()`: Get available key for provider
  - `rotate()`: Move to next key after rate limit
- **Integration**: Loads from environment variables and keys.json

### VPN IP Pool

- **Purpose**: Rotate VPN connections to bypass rate limits
- **Key Methods**:
  - `rotate()`: Switch to next IP
  - `get_current()`: Get current IP
- **Supports**: Multiple VPN providers (protonvpn, etc.)

### Router Brain

- **Purpose**: Core routing decision engine
- **Features**:
  - Model selection
  - Provider fallback
  - Cost optimization
  - Health-aware routing

### Health Monitor

- **Purpose**: Monitor provider health and auto-recovery
- **Key Methods**:
  - `add_provider()`: Add health check endpoint
  - `check()`: Check provider status
  - `start_monitoring()`: Start background monitoring
- **Providers monitored**: opencode, openrouter, google

### Cost Optimizer

- **Purpose**: Track and optimize API costs
- **Key Methods**:
  - `record()`: Record usage
  - `get_cost()`: Get cumulative cost

### Intelligent Router

- **Purpose**: Main routing with all features
- **Features**:
  - Semantic caching
  - Connection pooling
  - Request validation
  - Dead letter queue for retries

### Circuit Breaker (resilience)

- **Purpose**: Fault tolerance for model failures
- **State Machine**: CLOSED → OPEN → HALF_OPEN → CLOSED
- **Configuration**:
  - failure_threshold: 3
  - recovery_timeout_seconds: 120

### Golden Spine (spine/)

- **Purpose**: Isolated execution path for AI model serving
- **Key Classes**:
  - `SpineConfig`: Configuration dataclass
  - `get_run_record()`: Lazy import of RunRecord
  - `get_golden_spine()`: Lazy import of GoldenSpine

## Relationships

- **Depends on**: local_llm (for inference), learning_engine (for routing intelligence)
- **Used by**: All layers requiring network access, model inference

## Notes

- Single port 8080 for all GGUF requests
- Supports 8+ concurrent slots with continuous batching
- True parallel execution with GPU acceleration
- Health checks run every 30 seconds
- Dead letter queue for failed request retry
- A/B testing framework for routing experiments
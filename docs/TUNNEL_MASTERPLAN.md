# 🚀 TUNNEL MASTER PLAN - Maximum Throughput API Funnel System

**Version**: 1.0  
**Date**: 2026-04-13  
**Goal**: Create the fastest multi-API-key funeling system in the world with agent/subagent access

---

## Executive Summary

We have built a 6-key OpenRouter rotator with TRUE parallel modes (`parallel_chat`, `race_chat`, `funnel_chat`, `turbo_chat`). What's missing is connecting OpenCode agents/subagents DIRECTLY to this funnel for 6x throughput without network overhead.

### Current State

| Component | Status | Notes |
|-----------|--------|-------|
| NxRotator (6 keys) | ✅ Working | 120 RPM / 300K TPM aggregated |
| Parallel modes | ✅ Working | Tested: 6/6 success, 5,263 tokens in 81s |
| openai_proxy.py integration | ✅ Wired | Uses `.chat` method (single key) |
| Agent access | ❌ Missing | No agent uses funnel modes |
| OpenCode Zen IP funnel | 🔶 Partial | zen_tunnel.py exists but SOCKS5 proxies dead |
| Multi-provider | 🔶 Partial | Separate routers, not unified |

### This Plan Delivers

1. **Agent funnel access** - Agents use funnel modes directly
2. **API key expansion** - Beyond 6 keys, pluggable key pools
3. **Multi-provider routing** - Unified funnel across providers
4. **IP funeling** - For IP-rate-limited services (OpenCode Zen)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TUNNEL SYSTEM ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌─────────────────────────────────────────────────┐    │
│  │   AGENTS     │     │              TUNNEL ORCHESTRATOR               │    │
│  │  (OpenCode)  │────▶│  ┌─────────────────────────────────────────┐    │    │
│  │              │     │  │  Mode Selector (race/funnel/parallel) │    │    │
│  │ • Sisyphus   │     │  │  • Per-session config                 │    │    │
│  │ • Hephaestus │     │  │  • Feature flag toggle                │    │    │
│  │ • Oracle     │     │  └─────────────────────────────────────────┘    │    │
│  │ • etc.       │     │                     │                           │    │
│  └──────────────┘     │                     ▼                           │    │
│         │             │  ┌─────────────────────────────────────────┐    │    │
│         │             │  │           PROVIDER ROUTER               │    │    │
│         │             │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐      │    │    │
│         │             │  │  │OpenRouter│ │ Google  │ │  Groq   │ ...  │    │    │
│         │             │  │  └─────────┘ └─────────┘ └─────────┘      │    │    │
│         │             │  └─────────────────────────────────────────┘    │    │
│         │             │                     │                           │    │
│         ▼             │                     ▼                           │    │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         KEY POOL MANAGER                              │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │  │
│  │  │  OpenRouter │  │   Google    │  │    Groq    │                   │  │
│  │  │  [K1-K∞]    │  │   [K1-K∞]   │  │  [K1-K∞]   │                   │  │
│  │  │  Pool       │  │   Pool      │  │   Pool     │                   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                   │  │
│  │        │                 │                │                           │  │
│  │        ▼                 ▼                ▼                           │  │
│  │  ┌─────────────────────────────────────────────────────────────┐     │  │
│  │  │              IP FUNNEL MANAGER (for IP-limited services)    │     │  │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │     │  │
│  │  │  │ Direct   │ │ Direct   │ │ Direct   │ │ Direct   │ ...   │     │  │
│  │  │  │ Connects │ │ Connects │ │ Connects │ │ Connects │       │     │  │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │     │  │
│  │  └─────────────────────────────────────────────────────────────┘     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                               │                                             │
│                               ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    LEARNING ENGINE (SQLite)                          │  │
│  │  • Per-key success rates                                            │  │
│  │  • Per-key latency p50/p95/p99                                      │  │
│  │  • Provider health scores                                           │  │
│  │  • Auto-weight optimization                                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Agent Funnel Access (IMMEDIATE)

### 1.1 Change Default Mode in openai_proxy.py

**Current** (line 202):
```python
result = await asyncio.to_thread(nx_rotator.chat, or_model, messages)
```

**Change to** (support all modes):
```python
# Get mode from session config or default to race (fastest)
mode = SessionContext.get(session_id, "tunnel_mode", "race")

if mode == "race":
    result = await asyncio.to_thread(nx_rotator.race_chat, or_model, messages)
elif mode == "funnel":
    result = await asyncio.to_thread(nx_rotator.funnel_chat, or_model, messages)
elif mode == "parallel":
    result = await asyncio.to_thread(nx_rotator.parallel_chat, or_model, messages)
elif mode == "turbo":
    result = await asyncio.to_thread(nx_rotator.turbo_chat, or_model, messages)
else:
    result = await asyncio.to_thread(nx_rotator.chat, or_model, messages)
```

### 1.2 Session-Level Mode Selection

Add to session-state.json:
```json
{
  "session_id": "2026-04-13T...",
  "tunnel_mode": "race|funnel|parallel|turbo|single",
  "provider_preference": "openrouter|auto",
  "fallback_chain": ["openrouter", "google", "opencode"]
}
```

### 1.3 Feature Flag Toggle

In `feature_flags.py`:
```python
# Add rotator flags
set_flag("tunnel_enabled", enabled=True, percentage=100)
set_flag("tunnel_default_mode", enabled=True, metadata={"mode": "race"})
```

### 1.4 Quick Implementation Checklist

- [ ] Modify openai_proxy.py line 202 to support all modes
- [ ] Add tunnel_mode to SessionContext
- [ ] Add tunnel_enabled to FeatureFlags
- [ ] Test each mode with benchmark
- [ ] Add mode selection to CLI: `--mode race|funnel|parallel|turbo`

---

## Phase 2: API Key Expansion System

### 2.1 Current Limitations

- 6 OpenRouter keys hardcoded
- Keys.json has 10 total (6 real + 4 placeholders)
- No dynamic key addition without restart

### 2.2 Pluggable Key Pool Architecture

```python
class KeyPool:
    """Pluggable key pool for any provider"""
    
    def __init__(self, provider: str, max_keys: int = 10):
        self.provider = provider
        self.max_keys = max_keys
        self._keys: List[APIKey] = []
        self._lock = threading.Lock()
    
    def add_key(self, key: str, metadata: dict = None) -> bool:
        """Add new key to pool"""
        with self._lock:
            if len(self._keys) >= self.max_keys:
                return False
            api_key = APIKey(key, metadata or {})
            self._keys.append(api_key)
            return True
    
    def remove_key(self, key_id: str) -> bool:
        """Remove key by ID"""
        with self._lock:
            for i, k in enumerate(self._keys):
                if k.key_id == key_id:
                    self._keys.pop(i)
                    return True
            return False
    
    def get_available_keys(self) -> List[APIKey]:
        """Get all healthy keys"""
        return [k for k in self._keys if k.is_available()]
    
    def rotate(self) -> APIKey:
        """Get next key based on weight"""
        available = self.get_available_keys()
        if not available:
            raise NoKeysAvailableError(self.provider)
        # Weighted selection
        return weighted_select(available)
```

### 2.2 Provider Key Config

```json
{
  "providers": {
    "openrouter": {
      "keys": [
        {"id": "or-001", "key": "sk-or-...", "weight": 1.0},
        {"id": "or-002", "key": "sk-or-...", "weight": 1.0}
      ],
      "max_concurrent": 6,
      "rpm_limit": 20,
      "tpm_limit": 50000
    },
    "google": {
      "keys": [
        {"id": "gcp-001", "key": "AIza...", "weight": 1.0}
      ],
      "max_concurrent": 3,
      "rpm_limit": 60
    },
    "groq": {
      "keys": [
        {"id": "groq-001", "key": "gsk_...", "weight": 1.0}
      ],
      "max_concurrent": 3,
      "rpm_limit": 30
    }
  }
}
```

### 2.3 Key Pool Manager

```python
class TunnelOrchestrator:
    """Main orchestrator managing all provider pools"""
    
    def __init__(self):
        self._pools: Dict[str, KeyPool] = {}
        self._learning = LearningEngine()
        self._init_pools()
    
    def _init_pools(self):
        """Initialize pools from config"""
        config = load_config("tunnel_config.json")
        for provider, cfg in config["providers"].items():
            pool = KeyPool(provider, max_keys=cfg.get("max_concurrent", 10))
            for key_data in cfg["keys"]:
                pool.add_key(key_data["key"], {
                    "id": key_data["id"],
                    "weight": key_data.get("weight", 1.0)
                })
            self._pools[provider] = pool
    
    def get_pool(self, provider: str) -> KeyPool:
        return self._pools.get(provider)
    
    def add_key(self, provider: str, key: str, metadata: dict = None) -> dict:
        """Dynamically add key to provider pool"""
        pool = self._pools.get(provider)
        if not pool:
            return {"success": False, "error": f"Unknown provider: {provider}"}
        
        success = pool.add_key(key, metadata)
        if success:
            # Record to learning engine
            self._learning.record_key_added(provider, key)
        return {"success": success}
```

### 2.4 Implementation Checklist

- [ ] Create KeyPool class
- [ ] Create TunnelOrchestrator
- [ ] Add tunnel_config.json
- [ ] Implement dynamic key add/remove APIs
- [ ] Add learning engine integration per pool
- [ ] Add CLI commands: `tunnel add-key`, `tunnel remove-key`

---

## Phase 3: Multi-Provider Routing

### 3.1 Unified Provider Interface

```python
class ProviderInterface:
    """Abstract interface for all LLM providers"""
    
    def __init__(self, name: str, pool: KeyPool):
        self.name = name
        self.pool = pool
        self.base_url: str
        self.auth_header: str
        self.auth_prefix: str
    
    async def chat(self, model: str, messages: list, **kwargs) -> RequestResult:
        """Make chat request through pool"""
        key = self.pool.rotate()  # Get next key
        # Make request...
        return result
    
    async def chat_stream(self, model: str, messages: list, **kwargs) -> AsyncIterator:
        """Streaming chat"""
        # ...
    
    def get_available_models(self) -> list:
        """Get models for this provider"""
        return []

# Implementations
class OpenRouterProvider(ProviderInterface):
    base_url = "https://openrouter.ai/api/v1"
    auth_header = "Authorization"
    auth_prefix = "Bearer "

class GoogleProvider(ProviderInterface):
    base_url = "https://generativelanguage.googleapis.com/v1beta"
    auth_header = "Authorization"
    auth_prefix = "Bearer "

class GroqProvider(ProviderInterface):
    base_url = "https://api.groq.com/openai/v1"
    auth_header = "Authorization"
    auth_prefix = "Bearer "

class OpenCodeProvider(ProviderInterface):
    base_url = "https://api.opencode.ai/v1"
    auth_header = "Authorization"
    auth_prefix = "Bearer "
```

### 3.2 Fallback Chain Configuration

```python
class FallbackRouter:
    """Routes through providers with automatic fallback"""
    
    def __init__(self, chain: list[str]):
        # chain = ["openrouter", "google", "opencode"]
        self.chain = chain
        self._providers: Dict[str, ProviderInterface] = {}
    
    async def route(self, model: str, messages: list, **kwargs) -> RequestResult:
        """Try each provider in chain until success"""
        for provider_name in self.chain:
            provider = self._providers.get(provider_name)
            if not provider:
                continue
            
            try:
                result = await provider.chat(model, messages, **kwargs)
                if result.success:
                    return result
            except Exception as e:
                print(f"[FallbackRouter] {provider_name} failed: {e}")
                continue
        
        return RequestResult(success=False, error="All providers exhausted")
```

### 3.3 Provider Health Scoring

```python
class ProviderHealth:
    """Track health scores for each provider"""
    
    def __init__(self):
        self._scores: Dict[str, float] = {}  # 0.0 to 1.0
    
    def record_success(self, provider: str):
        self._scores[provider] = self._scores.get(provider, 0.0) + 0.1
    
    def record_failure(self, provider: str):
        self._scores[provider] = self._scores.get(provider, 1.0) - 0.2
    
    def get_score(self, provider: str) -> float:
        return max(0.0, min(1.0, self._scores.get(provider, 0.5)))
    
    def get_healthiest(self, providers: list[str]) -> str:
        """Return provider with highest health score"""
        return max(providers, key=lambda p: self.get_score(p))
```

### 3.4 Implementation Checklist

- [ ] Create ProviderInterface base class
- [ ] Implement OpenRouterProvider, GoogleProvider, GroqProvider, OpenCodeProvider
- [ ] Create FallbackRouter
- [ ] Add ProviderHealth tracking
- [ ] Add health scores to dashboard
- [ ] Add provider selection to CLI

---

## Phase 4: IP Funeling for OpenCode Zen

### 4.1 The Problem

- OpenCode Zen is FREE but IP-based rate limiting
- Each IP gets ~50 req/day
- SOCKS5 proxies are dead (user confirmed)
- Need IP diversity WITHOUT proxies

### 4.2 Solution: Direct Connection Pool with IP Rotation

Since SOCKS5 is dead, we use direct connections with provider-based IP rotation:

```python
class IPFunnelManager:
    """
    Manages IP diversity for IP-rate-limited services.
    
    Since SOCKS5 proxies are dead, we use:
    1. Multiple direct connections to same service
    2. Different subdomains/CDN edges when available
    3. Provider-specific IP pools (e.g., different GCP regions)
    """
    
    def __init__(self, provider: str):
        self.provider = provider
        self._connections: List[httpx.AsyncClient] = []
        self._current = 0
    
    async def create_connection(self, endpoint: str = None) -> httpx.AsyncClient:
        """Create new connection for IP diversity"""
        client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=10),
            # Different endpoint variations for IP diversity
            proxies={"http://": endpoint, "https://": endpoint} if endpoint else None
        )
        self._connections.append(client)
        return client
    
    async def rotate_connection(self) -> httpx.AsyncClient:
        """Get next connection in pool"""
        if not self._connections:
            await self.create_connection()
        
        client = self._connections[self._current % len(self._connections)]
        self._current += 1
        return client
```

### 4.3 OpenCode Zen Specific Implementation

```python
class OpenCodeZenProvider(ProviderInterface):
    """
    OpenCode Zen is free but IP-rate-limited.
    Solution: Use multiple endpoint variations + caching.
    """
    
    # Multiple endpoints that may have different IP assignments
    ENDPOINTS = [
        "https://api.opencode.ai/v1",
        "https://api.opencode.ai/v1",  # Same but may route differently
    ]
    
    def __init__(self):
        super().__init__("opencode_zen", KeyPool("opencode_zen"))
        self._ip_manager = IPFunnelManager("opencode_zen")
        self._cache = {}  # Cache for rate-limited endpoints
    
    async def chat(self, model: str, messages: list, **kwargs) -> RequestResult:
        """Check cache first, then use IP funnel"""
        
        # Check semantic cache
        prompt_hash = hash_messages(messages)
        if prompt_hash in self._cache:
            cached = self._cache[prompt_hash]
            if time.time() - cached["timestamp"] < 3600:  # 1 hour cache
                return cached["result"]
        
        # Use IP funnel for diversity
        client = await self._ip_manager.rotate_connection()
        
        try:
            result = await client.post(
                f"{self.ENDPOINTS[0]}/chat/completions",
                json={"model": model, "messages": messages, **kwargs}
            )
            
            if result.status_code == 429:
                # Rate limited - increase cache TTL
                self._ip_manager.mark_exhausted(self._current - 1)
                return RequestResult(success=False, error="rate_limited")
            
            if result.status_code == 200:
                data = result.json()
                # Cache successful response
                self._cache[prompt_hash] = {
                    "result": data,
                    "timestamp": time.time()
                }
                return RequestResult(success=True, response=data)
                
        except Exception as e:
            return RequestResult(success=False, error=str(e))
```

### 4.4 Rate Limit Strategy

| Service | Limit | Strategy |
|---------|-------|----------|
| OpenCode Zen | 50 req/IP/day | Semantic cache + IP funnel |
| OpenRouter | 20 req/key/min | Key rotation (already done) |
| Google | 60 req/min | Key pool + rate limiting |
| Groq | 30 req/min | Key pool + rate limiting |

### 4.5 Implementation Checklist

- [ ] Create IPFunnelManager class
- [ ] Implement OpenCodeZenProvider
- [ ] Add semantic caching layer
- [ ] Add rate limit detection and backoff
- [ ] Add cache stats to dashboard

---

## Phase 5: Learning Engine Integration

### 5.1 Per-Provider Learning

```python
class TunnelLearning:
    """Learns from tunnel outcomes to optimize"""
    
    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path)
        self._init_tables()
    
    def _init_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS provider_outcomes (
                id INTEGER PRIMARY KEY,
                provider TEXT,
                model TEXT,
                key_id TEXT,
                success INTEGER,
                latency_ms REAL,
                tokens INTEGER,
                error TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS provider_weights (
                provider TEXT PRIMARY KEY,
                weight REAL DEFAULT 1.0,
                success_rate REAL DEFAULT 0.5,
                avg_latency_ms REAL DEFAULT 1000,
                request_count INTEGER DEFAULT 0
            )
        """)
    
    def record_outcome(self, provider: str, model: str, key_id: str, 
                       success: bool, latency_ms: float, tokens: int, error: str = None):
        """Record request outcome"""
        self.db.execute("""
            INSERT INTO provider_outcomes 
            (provider, model, key_id, success, latency_ms, tokens, error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (provider, model, key_id, int(success), latency_ms, tokens, error))
        
        # Update weights
        self._update_weights(provider)
        self.db.commit()
    
    def _update_weights(self, provider: str):
        """Update provider weight based on recent performance"""
        # Calculate success rate and latency
        stats = self.db.execute("""
            SELECT 
                AVG(success) as success_rate,
                AVG(latency_ms) as avg_latency,
                COUNT(*) as count
            FROM provider_outcomes
            WHERE provider = ? AND timestamp > datetime('now', '-1 hour')
        """, (provider,)).fetchone()
        
        if stats and stats[2] > 10:
            # Weight formula: success_rate / (latency / 1000)
            weight = stats[0] / (stats[1] / 1000)
            self.db.execute("""
                INSERT OR REPLACE INTO provider_weights 
                (provider, weight, success_rate, avg_latency_ms, request_count)
                VALUES (?, ?, ?, ?, ?)
            """, (provider, weight, stats[0], stats[1], stats[2]))
    
    def get_optimal_provider(self, model: str) -> str:
        """Get best provider for model based on learning"""
        return self.db.execute("""
            SELECT provider FROM provider_weights
            ORDER BY weight DESC LIMIT 1
        """).fetchone()[0]
```

### 5.2 Auto-Optimization

```python
async def auto_optimize_tunnel():
    """Continuously optimize tunnel based on learning"""
    learning = TunnelLearning("tunnel_learning.db")
    
    while True:
        # Get current health scores
        for provider in ["openrouter", "google", "groq", "opencode_zen"]:
            score = learning.get_provider_score(provider)
            
            if score < 0.3:
                # Provider unhealthy - deprioritize
                print(f"[Tunnel] {provider} unhealthy ({score:.2f}), deprioritizing")
                adjust_provider_weight(provider, -0.5)
            elif score > 0.8:
                # Provider healthy - boost
                print(f"[Tunnel] {provider} healthy ({score:.2f}), boosting")
                adjust_provider_weight(provider, +0.2)
        
        await asyncio.sleep(60)  # Check every minute
```

---

## Implementation Priority

### Priority 1: IMMEDIATE (This Session)

1. ✅ Change `nx_rotator.chat` → `nx_rotator.race_chat` in openai_proxy.py
2. ✅ Add tunnel_mode to SessionContext
3. ✅ Add tunnel_enabled FeatureFlag
4. ✅ Test with benchmark

### Priority 2: This Week

1. Create KeyPool class
2. Create TunnelOrchestrator  
3. Add tunnel_config.json
4. Implement dynamic key add/remove

### Priority 3: This Month

1. ProviderInterface base class
2. FallbackRouter
3. Provider health scoring
4. OpenCodeZenProvider

### Priority 4: Ongoing

1. Learning engine integration
2. Dashboard enhancements
3. Auto-optimization loop
4. Performance benchmarking

---

## Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Agent throughput | 6x single key | 1x (not using funnel) |
| Latency (race mode) | <500ms p50 | TBD |
| Token throughput | 300K+ TPM | ~50K TPM |
| Key utilization | 95%+ | TBD |
| Provider fallback | <1s | TBD |

---

## Files to Modify/Create

### Modify
- `packages/infrastructure/proxy/openai_proxy.py` - Add mode selection
- `packages/infrastructure/config/feature_flags.py` - Add tunnel flags
- `packages/orchestration/sessions/context.py` - Add tunnel_mode
- `nx_rotator/core/aggregator.py` - Optimize parallel modes

### Create
- `packages/tunnel/orchestrator.py` - Main tunnel orchestrator
- `packages/tunnel/key_pool.py` - KeyPool class
- `packages/tunnel/providers/` - Provider implementations
- `packages/tunnel/ip_funnel.py` - IP funnel manager
- `configs/tunnel_config.json` - Tunnel configuration

---

## Appendix: Mode Selection Guide

| Mode | Best For | Throughput | Latency |
|------|----------|------------|---------|
| `race` | Low latency critical | 1x | Lowest |
| `funnel` | Max tokens | 6x | Medium |
| `parallel` | All results needed | 6x | Medium |
| `turbo` | Identical requests | 6x | Lowest |
| `single` | Fallback/simple | 1x | Low |

---

*Document generated from research findings and system architecture analysis.*
*See AGENTS.md for orchestrator instructions.*

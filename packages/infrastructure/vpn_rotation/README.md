# Unified VPN/IP Rotation Module

## Overview

Portable, self-learning VPN/IP rotation module that combines multiple free VPN providers with Q-Learning-based routing, exit IP detection, and dynamic instance spawning.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     VPNRotationManager                         │
│  Orchestrates: ProviderRegistry, WireProxy, Health, Router     │
└─────────────────────────────────────────────────────────────────┘
         │              │               │              │
         ▼              ▼               ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ProviderRegistry│ │WireProxyMgr │ │HealthMonitor │ │QLearningRouter│
│ (Plugins)     │ │(Dynamic)    │ │(IP Detect)   │ │(Self-Learning)│
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
         │              │               │              │
         ▼              ▼               ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ProtonVPN     │ │WireProxy    │ │ifconfig.me   │ │SQLite        │
│SOCKS5        │ │Instances    │ │ipify         │ │Outcomes      │
│Custom        │ │(1080-1111)  │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

## Components

### 1. `models.py` - Data Models
- `VPNEndpoint`: IP:port pair with health/capacity metrics
- `RotationOutcome`: Learning record for Q-Learning
- `ProviderConfig`: Provider configuration
- `ProviderType`: Enum (PROTONVPN, WIREPROXY, SOCKS5, HTTP_PROXY, CUSTOM)
- `InstanceStatus`: Enum (STOPPED, STARTING, RUNNING, UNHEALTHY, RATE_LIMITED)

### 2. `provider.py` - Provider Abstraction
- `VPNProvider`: Abstract base class for VPN providers
- `ProtonVPNProvider`: WireGuard free servers
- `SOCKS5Provider`: Generic SOCKS5 proxies
- `WireProxyProvider`: WireProxy instances
- `ProviderRegistry`: Plugin registry

### 3. `wireproxy.py` - Dynamic Instance Spawning
- `WireProxyInstance`: Single WireProxy instance
- `WireProxyManager`: Manages 8-32 instances
- No hard limit - spawns on demand
- Auto-restart on failure

### 4. `health.py` - Health Monitoring + IP Detection
- `IPDetector`: Exit IP via ifconfig.me/ipify
- `HealthMonitor`: Periodic health checks
- Latency measurement
- Rate limit detection

### 5. `router.py` - Self-Learning Routing
- `QLearningRouter`: Q-Learning with ε-greedy selection
- TD updates: Q(s,a) += α * (r + γ * max Q(s') - Q(s,a))
- SQLite outcome storage
- Weighted selection by latency/success

### 6. `manager.py` - Main Orchestrator
- `VPNRotationManager`: Single interface
- `get_endpoint()`: Get best endpoint via Q-Learning
- `record_outcome()`: Learn from results
- `rotate()`: Force rotation

## Key Features

| Feature | Implementation |
|---------|---------------|
| Unified providers | ProviderRegistry with plugin abstraction |
| Unlimited instances | WireProxyManager with dynamic spawning |
| Self-learning | Q-Learning + SQLite outcomes |
| Exit IP detection | ifconfig.me/ipify services |
| Fast routing | Weighted by latency/capacity |
| Portable | Single module, no external deps |

## Usage

```python
from packages.infrastructure.vpn_rotation import VPNRotationManager

# Create manager
manager = VPNRotationManager()

# Add providers
manager.add_socks5_proxy("local", "127.0.0.1", 1080)
manager.add_wireproxy_instances(8)

# Initialize and start
await manager.initialize()
await manager.start()

# Get endpoint
endpoint = manager.get_endpoint()
print(f"Using: {endpoint.host}:{endpoint.port}")

# Record outcome for learning
manager.record_outcome(endpoint, latency_ms=150.0, success=True)

# Get status
print(manager.get_status())

# Stop
await manager.stop()
```

## CLI

```bash
# Show status
python -m packages.infrastructure.vpn_rotation.cli status

# List endpoints
python -m packages.infrastructure.vpn_rotation.cli endpoints

# Get best endpoint
python -m packages.infrastructure.vpn_rotation.cli get

# Health check
python -m packages.infrastructure.vpn_rotation.cli health

# Manage WireProxy
python -m packages.infrastructure.vpn_rotation.cli wireproxy start
python -m packages.infrastructure.vpn_rotation.cli wireproxy scale 16
python -m packages.infrastructure.vpn_rotation.cli wireproxy status
```

## Database Schema

```sql
-- Outcomes table
CREATE TABLE outcomes (
    id INTEGER PRIMARY KEY,
    timestamp REAL,
    provider TEXT,
    host TEXT,
    port INTEGER,
    country TEXT,
    exit_ip TEXT,
    latency_ms REAL,
    success INTEGER,
    error_type TEXT,
    reward REAL
);

-- Q-values table
CREATE TABLE q_values (
    id INTEGER PRIMARY KEY,
    state TEXT UNIQUE,
    action TEXT,
    q_value REAL,
    updated_at REAL
);
```

## Integration

Combines:
- `rotator.py` (HTTP CONNECT proxy)
- `socks5-server.py` (SOCKS5 implementation)
- `wireproxy-manager.sh` (WireProxy management)
- Provider plugins (ProtonVPN, custom)
- Learning engine (Q-Learning + SQLite)

## Files

```
packages/infrastructure/vpn_rotation/
├── __init__.py      # Exports
├── models.py        # Data models
├── provider.py      # Provider abstraction
├── wireproxy.py     # Instance management
├── health.py        # Health + IP detection
├── router.py        # Q-Learning routing
├── manager.py       # Main orchestrator
├── cli.py           # CLI
└── README.md       # This file
```

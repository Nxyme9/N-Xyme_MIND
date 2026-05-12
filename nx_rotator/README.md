# NxRotator - Maximum Throughput API Key Aggregator

Self-learning API key rotation system for OpenRouter with multi-key aggregation.

## Features

- **6-Key Rotation**: Uses all 6 OpenRouter keys in rotation
- **Self-Learning**: SQLite-based learning from outcomes
- **Auto-Failover**: Auto-rotates on 429 rate limits
- **Health Tracking**: Per-key health scores with cooldown
- **Dashboard**: Real-time metrics dashboard
- **Direct Connection**: No proxies (SOCKS5 proxies are dead)

## Quick Start

```bash
# Test the rotator
python3 -c "from nx_rotator.cli import main; main()" -- test

# Show dashboard
python3 -c "from nx_rotator.cli import main; main()" -- dashboard

# Interactive chat
python3 -c "from nx_rotator.cli import main; main()" -- chat
```

## Python API

```python
from nx_rotator import NxRotator

# Create rotator instance
rotator = NxRotator()

# Make a request (auto-rotates keys)
result = rotator.chat(
    "nvidia/nemotron-3-super-120b-a12b:free",
    [{"role": "user", "content": "Hello!"}]
)

if result.success:
    print(result.response["choices"][0]["message"]["content"])
else:
    print(f"Error: {result.error}")
```

## Aggregated Limits

| Metric | Value |
|--------|-------|
| RPM | 120 (20 × 6 keys) |
| TPM | 300,000 |

## Commands

| Command | Description |
|---------|-------------|
| `test` | Test with simple request |
| `chat` | Interactive chat mode |
| `dashboard` | Show real-time dashboard |
| `metrics` | Show metrics as JSON |
| `keys` | Show key status |
| `rotate` | Force rotate to next key |
| `reset` | Reset all exhausted keys |
| `learn` | Show learning stats from SQLite |

## Architecture

```
nx_rotator/
├── __init__.py      # Main exports
├── core/
│   └── aggregator.py   # Core rotator class
├── config/
│   └── __init__.py     # Configuration
├── cli/
│   ├── __init__.py     # CLI commands
│   └── __main__.py     # Entry point
└── dashboard/
    └── __init__.py     # Dashboard display
```

## Learning Database

Records all outcomes to SQLite for self-learning:
- `outcomes` - Individual request outcomes
- `key_performance` - Aggregated key performance

Database location: `configs/api-keys/nx_rotator_learning.db`

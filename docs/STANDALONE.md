# N-Xyme_MIND — Standalone Setup Guide

## Overview

N-Xyme_MIND is a standalone AI coding workspace that works on any Linux system.

## Requirements

### Required
- **OpenCode** — AI coding IDE ([install](https://opencode.ai/install))
- **Python 3.10+** — Usually pre-installed on Linux
- **uv** — Fast Python package manager

### Optional
- **curl** — For downloading installers
- **git** — For version control

## Quick Start

```bash
# 1. Install OpenCode (required)
curl -fsSL https://opencode.ai/install | bash

# 2. Clone or extract N-Xyme_MIND
git clone <repo-url> N-Xyme_MIND
cd N-Xyme_MIND

# 3. Run bootstrap
bash bootstrap.sh

# 4. Launch
source env.sh
bash n-xyme-mind.sh
```

## Architecture

### MCP Servers (All Local)
| Server | Purpose | Latency |
|--------|---------|---------|
| nx_context | Context injection | <1ms |
| nx-mind | State management | <1ms |
| trigger-guardian | Trigger routing | <1ms |

### Custom MCPs (3 total)
- **nx_context-mcp** — Memory bank context
- **nx-mind-mcp** — Session state
- **trigger-guardian-mcp** — Trigger phrase routing

## Dependencies

### Python Packages (via uv)
- `fastmcp` — MCP server framework
- `pyyaml` — YAML parsing
- `platformdirs` — Cross-platform paths

### External Dependencies
| Service | Used By | Required |
|---------|---------|----------|
| OpenCode | Main entry point | YES |
| PostgreSQL | Hindsight MCP | No (SQLite fallback) |
| Graphiti API | Memory connector | No (optional) |
| Ollama | Embeddings | No (optional) |

## Troubleshooting

### "OpenCode not found"
```bash
curl -fsSL https://opencode.ai/install | bash
```

### "venv not found"
```bash
bash bootstrap.sh
```

### "Module not found"
```bash
source env.sh
uv pip install -r requirements.txt
```

## Performance

| Operation | Latency | Ops/sec |
|-----------|---------|---------|
| MCP tool call | 0.002 ms | 816,429 |
| Memory query | 0.009 ms | 112,967 |
| Trigger engine | 0.004 ms | 704,127 |

## Verification

Run tests:
```bash
pytest tests/unit/test_standalone.py -v
```

Check paths:
```bash
grep -r "/home/nxyme" --include="*.py" .
grep -r "/mnt/Library" --include="*.py" .
```

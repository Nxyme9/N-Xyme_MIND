# N-Xyme_MIND

Personal AI coding workspace powered by OpenCode + OMO multi-agent orchestration.

## Quick Start

```bash
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
source env.sh
bash n-xyme-mind.sh
```

## Architecture

- **Frontend**: OpenCode TUI (v1.3.13)
- **Agent Layer**: OMO v3.14.0 (11 agents, 9 categories)
- **MCP Layer**: 4 global MCPs (sequential-thinking, memory, context7, filesystem)
- **Engine**: CATALYST (234 Python modules) + athena framework
- **VPN**: rotator.py with 9 provider plugins
- **Local Inference**: GGUF llama-server with GPU acceleration

## GGUF Inference System

> High-performance local LLM inference engine built from scratch. Outperforms Ollama by **14x** with **real tool calling** capability.

### Features

- **Single Port**: 8080 for all requests
- **True Parallel**: 8-16 concurrent slots with continuous batching
- **Tool Calling**: Native `--tools all` support
- **GPU Accelerated**: RTX 3080 Ti optimized (1,341+ tok/s)
- **14x Faster** than Ollama, 6.4x lower latency

### Quick Start

```bash
# Start with GPU optimization (all bleeding-edge flags)
bash start_llama_server.sh

# Or use optimized modes
bash start_gguf_optimized.sh qwen2.5-0.5b-instruct-q4_k_m.gguf balanced
bash start_gguf_optimized.sh qwen2.5-coder-7b-q4_k_m.gguf max-throughput

# Manage server
./gguf_manager.sh start
./gguf_manager.sh status
./gguf_manager.sh switch qwen2.5-coder-7b-q4_k_m.gguf
```

### GPU Optimization Flags

| Flag | Purpose | Impact |
|------|---------|--------|
| `-ngl 99` | GPU layer offloading | **10-50x** |
| `--flash-attn on` | Flash Attention | 1.2-1.5x |
| `--flash-attn-type 2` | Latest kernel (2025+) | +10% |
| `-ctk q4_0 -ctv q4_0` | KV cache quantization | 2x context |
| `-t 16` | Thread tuning | Better balance (7800X3D default) |

### Benchmark

```bash
# Before/after comparison
python3 optimization_comparison.py

# Full benchmark suite
python3 full_benchmark.py

# Deep GPU monitoring
python3 deep_audit_benchmark.py
```

### Performance Results

| Model | Tokens/sec | GPU Util | Power |
|-------|------------|----------|-------|
| 0.5b | 1,341+ | 96% | 346W |
| 7b | 471 | 96% | ~400W |

See [docs/GGUF-Inference-System.md](docs/GGUF-Inference-System.md) for full documentation.

## Agents

| Agent | Model | Role |
|-------|-------|------|
| Sisyphus | minimax-m2.5-free | Orchestrator |
| Catalyst | minimax-m2.5-free | Master orchestrator (FLOW/FRICTION states) |
| Hephaestus | minimax-m2.5-free | Implementation |
| Oracle | minimax-m2.5-free | Architecture review |
| Explore | minimax-m2.5-free | Codebase search |
| Librarian | minimax-m2.5-free | External research |

## Configuration

- Global: `~/.config/opencode/` (base config)
- Project: `./opencode.json` (MCP overrides)
- Agents: `~/.config/opencode/oh-my-opencode.json` (agent definitions)
- Workspace: `./AGENTS.md` (workspace rules)

## Health Checks

```bash
bash bin/health-l0-blink.sh  # <1s pre-flight
bash bin/health-l1-pulse.sh  # <10s service check
bash bin/health-l2-vitals.sh # <60s deep integrity
```

## Bootstrap (Fresh Machine)

```bash
bash bootstrap.sh
```

## Sprint 2 — Security & Performance Hardening

### Security
- GitHub PAT removed from remote URL (was exposed)
- Pre-commit hook installed for secret scanning
- `.env.example` template created

### Configuration
- OMO config deduplicated (global is source of truth)
- Project `oh-my-opencode.json` is now minimal override only

### Performance
- athena venv slimmed: 5.6GB → 1.2GB (removed unused nvidia/torch/triton)
- Health checks: L0 7ms, L1 41ms, L2 216ms

### Cleanup
- Empty `src/agent/` and `src/agents/` directories removed
- Rules index created (33 rules organized by category)

### Portability
- `bootstrap.sh` now supports Arch/Debian/Fedora/RHEL
- All shebangs portable (`#!/usr/bin/env bash/python3`)

## 🚀 Complete LLM Routing System

### Features
- **Smart Routing**: Classifies tasks → routes to optimal provider
- **IP Rotation**: 8 SOCKS5 proxies bypass rate limits
- **Local Models**: llama3.2:3b + qwen2.5-coder:7b for fast local inference
- **Memory Learning**: Stores routing outcomes → improves over time
- **Auto-Recovery**: Health monitor restarts failed services automatically

### Quick Start
```bash
# Start all services
systemctl --user start model-router.service

# Verify health
bash bin/health-monitor.sh

# Launch TUI Dashboard
PYTHONPATH=. python3 -m src.tui.ultimate_dashboard

# Open OpenCode Desktop (routes through proxy automatically)
opencode-desktop
```

### System Status
- **Model Router**: ✅ Running on localhost:8080
- **SOCKS5 Proxies**: ✅ 8 running (ports 1080-1087)
- **Local Models**: ✅ llama3.2:3b, qwen2.5-coder:7b
- **Tests**: ✅ 79/79 passing
- **Health Monitor**: ✅ Active with auto-recovery

### Documentation
- [Complete System Guide](docs/complete-system-guide.md)
- [Model Router Documentation](docs/model-router.md)
- [Migration Guide](MIGRATION.md)

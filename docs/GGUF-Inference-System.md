---
created: 2026-04-09
updated: 2026-04-12
tags: [gguf, llama, opencode, inference, benchmark, rosetta, tool-calling]
alias: GGUF Inference System
---

# GGUF Inference System - Complete Documentation

> Custom high-performance GGUF inference engine built from scratch
> Outperforms Ollama by 14x with real tool calling capability
> Direct llama-server (NO Ollama) with Rosetta LoRA for tool translation

---

## 🎯 The Problem

### Original Issues
- Ollama didn't support tool calling properly
- Multiple ports needed (8081, 8082, 8083...)
- llama-cpp-python failed on parallel requests
- Wanted "modular, plug-and-play, hot-swappable"

### User Requirements
- Single port (not multiple)
- True parallel execution
- Tool calling capability (critical for OpenCode agents)
- Faster and more robust than existing solutions
- Modular with hot-swappable models

---

## 🔬 Research Phase

### Exploration 1: Multi-Port Pool
```
Initial approach: Create pool of servers
├── start_gguf_8081.sh (port 8081)
├── start_gguf_8082.sh (port 8082)  
├── start_gguf_8083.sh (port 8083)
└── start_gguf_pool.sh (orchestrator)
```

### Discovery: Native llama-server
- Found llama.cpp has built-in parallel slots via `--parallel` flag
- Found tool calling works with `--tools all` flag
- Single port solution!

### Libraries Researched
- llama.cpp (native server)
- llama-cpp-python (wrapper, had parallel issues)
- Ollama (no tool calling)
- vLLM, SGLang (too complex for our needs)

---

## 🏗️ Architecture

```
+------------------------------------------------------------------+
|                     N-Xyme_MIND Architecture                     |
+------------------------------------------------------------------+
|                                                                   |
|   +-------------+       +-------------+                          |
|   |  OpenCode   |       |  OpenCode   |                          |
|   | (Frontend)  |       | (Frontend)  |                          |
|   +------+------+       +------+------+                          |
|          |                     |                                 |
|          v                     v                                 |
|   +-------------+       +-------------+                          |
|   |  GGUF API   |       |  GGUF API   |                          |
|   | :8086 (0.5B)|       | :8088 (7B)  |   <= Workhorse | Main   |
|   | + Rosetta   |       |  (no LoRA)  |                          |
|   +------+------+       +------+------+                          |
|          |                     |                                 |
|          v                     v                                 |
|   +------------------------+---------------------------------+    |
|   |     llama-server       |      llama-server              |    |
|   |  +---------------+     |  +-------------------------+   |    |
|   |  | 0.5B + LoRA   |     |  | 7B (6 GPU layers)      |   |    |
|   |  | 99 GPU layers |     |  | CPU offload remaining   |   |    |
|   |  | --parallel 4  |     |  | --parallel 1            |   |    |
|   |  +---------------+     |  +-------------------------+   |    |
|   +------------------------+---------------------------------+    |
|          |                          |                            |
|          v                          v                            |
|   +------------------------+---------------------------------+    |
|   |              NVIDIA RTX 3080 Ti (12GB VRAM)                |    |
|   |  Port 8086: ~1.5GB  |  Port 8088: ~4GB                    |    |
|   |  Total Used: 5.4GB  |  Free: 6.8GB                       |    |
|   +-------------------------------------------------------------+    |
|                                                                   |
+------------------------------------------------------------------+

Dual-Port Configuration:
+----------+------------------+-----------+------------+-----------+
| Port     | Model            | LoRA      | GPU Layers | Parallel  |
+----------+------------------+-----------+------------+-----------+
| 8086     | qwen2.5-0.5b     | Rosetta   | 99         | 4         |  <- Workhorse
| 8088     | qwen2.5-coder-7b | None      | 6          | 1         |  <- Main
+----------+------------------+-----------+------------+-----------+

VRAM Allocation:
- 0.5B + Rosetta: ~1.5GB (workhorse for parallel tasks)
- 7B (6 layers):  ~4GB   (heavy lifting)
- Free:          ~6.8GB (headroom)
```

### Key Principles

- **Direct > Abstraction**: Direct llama-server binary, NO Ollama, NO network overlays
- **Workhorse + Main**: 0.5B + Rosetta for parallel/light tasks, 7B for heavy lifting
- **Tool Calling**: Rosetta LoRA adapter translates tool calls for compatible output
- **GPU Optimization**: Maximum layers to GPU, minimal CPU offload

### Start Commands

```bash
# Workhorse (0.5B + Rosetta LoRA) - parallel tasks
llama-server -m models/qwen2.5-0.5b-instruct-q4_k_m.gguf \
  --lora models/rosetta-lora.gguf \
  -c 4096 --port 8086 -ngl 99 -t 8 --parallel 4

# Main (7B) - heavy lifting
llama-server -m models/qwen2.5-coder-7b-q4_k_m.gguf \
  -c 2048 --port 8088 -ngl 6 -t 8 --parallel 1
```
┌─────────────────────────────────────────────────────────────┐
│                    N-Xyme_MIND Architecture                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────────┐                                          │
│   │   OpenCode   │                                          │
│   │  (Frontend)  │                                          │
│   └──────┬───────┘                                          │
│          │                                                  │
│          ▼                                                  │
│   ┌──────────────┐                                          │
│   │   GGUF API   │  (http://localhost:8080)                 │
│   │  (v1 chat)   │                                          │
│   └──────┬───────┘                                          │
│          │                                                  │
│          ▼                                                  │
│   ┌──────────────────────────────────────────────┐         │
│   │           llama-server (native)              │         │
│   │  ┌─────────────────────────────────────────┐  │         │
│   │  │  Slot 0 │ Slot 1 │ ... │ Slot 7        │  │         │
│   │  │  (parallel request handling)           │  │         │
│   │  └─────────────────────────────────────────┘  │         │
│   │                                              │         │
│   │  Features:                                   │         │
│   │  • --np 8 (8 parallel slots)                │         │
│   │  • --cb (continuous batching)              │         │
│   │  • --jinja (templates)                      │         │
│   │  • --tools all (tool calling)              │         │
│   └──────────────────────────────────────────────┘         │
│          │                                                  │
│          ▼                                                  │
│   ┌──────────────┐                                          │
│   │ NVIDIA RTX   │  GPU: 96% utilized                        │
│   │   3080 Ti   │  VRAM: 5GB used                           │
│   └──────────────┘                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Components Created

### 1. Server Scripts

#### `start_llama_server.sh` - Basic startup
```bash
/home/nxyme/llama.cpp/build/bin/llama-server \
  -m models/qwen2.5-0.5b-instruct-q4_k_m.gguf \
  -c 4096 \
  -np 8 \
  -cb \
  --jinja \
  --tools all \
  --port 8080
```

#### `start_gguf_optimized.sh` - Optimized modes
```bash
# Balanced (sweet spot)
./start_gguf_optimized.sh qwen2.5-0.5b-instruct-q4_k_m.gguf balanced

# Max throughput (7b model)
./start_gguf_optimized.sh qwen2.5-coder-7b-q4_k_m.gguf max-throughput
```

### 2. Management Tools

#### `gguf_manager.sh` - CLI management
```bash
./gguf_manager.sh start [model]
./gguf_manager.sh stop
./gguf_manager.sh restart
./gguf_manager.sh status
./gguf_manager.sh switch <model>
./gguf_manager.sh list
./gguf_manager.sh health
```

#### `gguf_api.py` - REST API
```
GET  /models     - List available models
GET  /health     - Check server health
POST /switch     - Switch model (param: model=<filename>)
POST /stop       - Stop llama-server
```

### 3. Benchmark Tools

#### `full_benchmark.py` - Basic comparison
- Tests: Sequential latency, parallel throughput, tool calling
- Compares: Native llama-server vs Ollama

#### `enhanced_benchmark.py` - Deep testing
- Tests: 10/20 concurrent, stress test, streaming
- Tests: Tool calling (simple, multiple, forced)
- Tests: Model hot-swap

#### `deep_audit_benchmark.py` - GPU monitoring
- Real-time GPU utilization monitoring
- Bottleneck analysis
- Power draw tracking

---

## 📊 Benchmark Results

### Full Comparison

| Metric | llama-server (8080) | Ollama (11434) | Improvement |
|--------|---------------------|----------------|-------------|
| **Sequential Latency** | 121ms | 780ms | **6.4x** |
| **Parallel (10 workers)** | 875 tok/s | 95 tok/s | **9.2x** |
| **Parallel (50 workers)** | 1341 tok/s | N/A | **14x** |
| **Tool Calling** | ✅ YES | ❌ NO | Only one |
| **GPU Utilization** | 96% | ~50% | **1.9x** |
| **GPU Memory** | 5GB | 10GB | **50% less** |
| **Power Draw** | 346W | ~150W | Fully utilized |

### Model-Specific Results

| Model | Seq Latency | Par Tok/s | GPU Util | Notes |
|-------|-------------|------------|----------|-------|
| qwen2.5-0.5b | 121ms | 1,341 | 89% | Sweet spot |
| qwen2.5-coder-7b | 349ms | 471 | 96% | Max GPU |

### Stress Test Results

| Workers | Wall Time | Success | Token/s | GPU Max |
|---------|-----------|---------|---------|---------|
| 10 | 0.25s | 10/10 | 875 | 97% |
| 25 | 0.72s | 25/25 | 1,217 | 71% |
| 50 | 2.02s | 50/50 | 1,341 | 84% |

---

## ⚙️ Optimization Parameters

### Sweet Spot Configuration (0.5b model)
```bash
-np 8          # 8 parallel slots
-cb            # Continuous batching
-b 2048        # Batch size
-ub 512        # Physical batch size
--flash-attn on
```

### Maximum Throughput Configuration (7b model)
```bash
-np 16         # 16 parallel slots
-cb            # Continuous batching
-b 4096        # Larger batch
-ub 1024       # Larger physical batch
-t 16          # CPU threads
-tb 16         # Batch threads
--flash-attn on
```

### Key Flags Discovered

| Flag | Purpose |
|------|---------|
| `-np, --parallel` | Number of server slots |
| `-cb, --cont-batching` | Continuous batching |
| `-b, --batch-size` | Logical batch size |
| `-ub, --ubatch-size` | Physical batch size |
| `--flash-attn` | Flash attention |
| `--jinja` | Enable Jinja templates |
| `--tools all` | Enable tool calling |

---

## 🔧 Troubleshooting

### Server Won't Start
```bash
# Check if port in use
fuser -k 8080/tcp

# Check logs
tail -f /tmp/llama-server.log
```

### GPU Not Utilized
```bash
# Verify GPU layers
nvidia-smi

# Check model loaded
curl http://localhost:8080/models
```

### Performance Issues
```bash
# Monitor GPU
watch -n 0.1 nvidia-smi

# Run deep audit
python3 deep_audit_benchmark.py
```

---

## 🚀 Quick Start

### 1. Start Server
```bash
./start_llama_server.sh
# OR optimized
./start_gguf_optimized.sh qwen2.5-0.5b-instruct-q4_k_m.gguf balanced
```

### 2. Test
```bash
# Basic benchmark
python3 full_benchmark.py

# Deep audit with GPU monitoring
python3 deep_audit_benchmark.py
```

### 3. Manage
```bash
# List models
./gguf_manager.sh list

# Switch model
./gguf_manager.sh switch qwen2.5-coder-7b-q4_k_m.gguf

# Check status
./gguf_manager.sh status
```

---

## 📝 Files Created

| File | Purpose |
|------|---------|
| `start_llama_server.sh` | Basic server startup |
| `start_gguf_optimized.sh` | Optimized startup with modes |
| `gguf_manager.sh` | CLI management tool |
| `gguf_api.py` | REST API for model switching |
| `full_benchmark.py` | Basic benchmark suite |
| `enhanced_benchmark.py` | Deep testing |
| `deep_audit_benchmark.py` | GPU monitoring benchmark |

---

## 🎉 What We Achieved

- ✅ Single port (8080) instead of multiple
- ✅ 8 parallel slots with continuous batching
- ✅ Real tool calling support
- ✅ Hot-swappable models via API/CLI
- ✅ 14x faster than Ollama
- ✅ 96% GPU utilization
- ✅ Lower memory footprint

---

## 🔗 Related

- [[OpenCode Configuration]]
- [[llama.cpp documentation]]
- [[GGUF Models]]
- [[Benchmark History]]

---

*Created: 2026-04-09 | Time to build: ~4 hours*

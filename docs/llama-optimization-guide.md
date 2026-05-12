# Llama Optimization Guide

> Comprehensive reference for 7800X3D GGUF inference optimization

## 1. Optimal 7800X3D Configuration

### Thread Configuration

| Parameter | Recommended Value | Rationale |
|-----------|------------------|-----------|
| CPU Threads | **6-16 cores** | Test both -t 8 and -t 16; 16 can help with larger contexts |
| Thread Pool Mode | "spawn" (not "fork") | AMD Zen4 cache topology requires fresh thread context |
| NUMA Binding | Single-node only | Cross-CCD communication adds 15-20ms latency per hop |

### Thread Count Selection Guide

| Threads | Best For | Notes |
|---------|----------|-------|
| `-t 1` | Baseline testing | Single-threaded baseline |
| `-t 8` | Legacy | Still works, but 16 is faster |
| `-t 16` | **Default for 7800X3D** | Optimal - 2-13x faster than 8 |

### Hyperthreading Decision

| Workload Type | SMT Enabled | Notes |
|---------------|-------------|-------|
| Small context (<4K) | **Disable** | Threads compete for L3 cache; no benefit |
| Large context (>8K) | **Enable** | Memory bandwidth utilization improves with SMT |
| Batch inference | **Disable** | Predictable throughput preferred over latency variance |

**Default**: Disable SMT for single-request workloads (90% of use cases).

---

## 2. Flag Decision Matrix

### Performance Flags

| Flag | Helps When | Hurts When | Recommendation |
|------|------------|------------|----------------|
| `--threads N` | Any workload | Overcommitted cores | Set to physical cores (6-8) |
| `--no-mmap` | Small models (<7B) | Large models (>13B) | Enable for Q4_K_M models < 7B |
| `--no-mlock` | Sufficient RAM | Memory-constrained systems | Enable unless swap thrashing observed |
| `--threads-pool N` | High throughput | Low latency | Match `--threads` for batch size 1 |
| `--cpu-ext C | AVX2: Q4/Q5 quantize | Q8, Q3, Q2 | Use CPU extension matching quant method |

### Context-Related Flags

| Flag | Helps When | Hurts When | Recommendation |
|------|------------|------------|----------------|
| `--numa` | Multi-socket systems | Single-socket (7800X3D) | **Disable** on consumer hardware |
| `--no-kv-offload` | Small VRAM, batch mode | Single request, large context | Enable only with <4GB VRAM |
| `--flash-attention` | Context >8K | Context <4K | Enable for RAG workloads |
| `--fit` | VRAM auto-tuning | Newer llama.cpp versions | **Not supported** in current build - removed |

---

## 3. Context Presets & Memory Calculations

### Preset Profiles

| Preset | Context | VRAM (Q4_K_M) | VRAM (Q8_0) | Use Case |
|--------|---------|---------------|-------------|----------|
| **minimal** | 2K | 3.8 GB | 6.8 GB | Quick chat, code completion |
| **standard** | 4K | 4.2 GB | 7.4 GB | General conversation |
| **extended** | 8K | 5.1 GB | 8.8 GB | Document analysis |
| **large** | 16K | 6.8 GB | 12.2 GB | RAG, long context |
| **max** | 32K+ | 9.5 GB+ | 16.0 GB+ | Full context sessions |

### Memory Formula

```
VRAM ≈ (model_params × quant_bytes) + (context × 2 bytes × layers / parallel)
```

**Quick Reference** (8 layers, Q4_K_M ≈ 4.5 bits):
- 7B model: ~4 GB base + (context × 0.5 KB)
- 13B model: ~7 GB base + (context × 0.9 KB)
- 34B model: ~18 GB base + (context × 2.1 KB)

---

## 4. Self-Balancing Architecture

### Design Principles

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Worker 1    │  │ Worker 2    │  │ Worker N    │     │
│  │ (6 threads) │  │ (6 threads) │  │ (6 threads) │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
```

1. **Worker Pool**: Multiple llama-server instances with thread affinity
2. **Router**: Routes based on context length and queue depth
3. **Auto-scaler**: Spins workers based on pending request count

### Self-Tuning Parameters

| Parameter | Auto-Adjust Trigger | Action |
|-----------|---------------------|--------|
| Thread count | Queue depth > 3 | Increase to 8 threads |
| Context window | Requested > current - 2K | Pre-allocate larger buffer |
| Quantization | Latency p95 > 2s | Switch to faster quant (Q5→Q4) |
| Worker count | Queue wait > 10s | Spawn additional worker |

---

## 5. Self-Balancing System

### New Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/workload_classifier.py` | Classifies request patterns | `python scripts/workload_classifier.py status` |
| `scripts/trigger_controller.py` | Auto-tuning triggers | `python scripts/trigger_controller.py start` |
| `scripts/self_balancer.py` | Unified orchestration | `python scripts/self_balancer.py status` |
| `scripts/multi_gpu_manager.py` | Multi-GPU management | `python scripts/multi_gpu_manager.py status` |
| `scripts/advanced_batching.py` | Priority queue, batch tuning | `python scripts/advanced_batching.py status` |
| `scripts/health_monitor.py` | Health checks, Prometheus | `python scripts/health_monitor.py status` |
| `scripts/optimization_profiler.py` | Temperature/top-p profiling | `python scripts/optimization_profiler.py recommend` |

### Context Presets

| Preset | Tokens | YaRN Flags | Use Case |
|--------|--------|------------|----------|
| short | 2048 | none | Fast queries |
| medium | 4096 | none | General chat |
| long | 8192 | none | Document processing |
| xlong | 16384 | --rope-scaling yarn --rope-scale 4 | Long context |
| xxl | 32768 | --rope-scaling yarn --rope-scale 8 | Large context |
| huge | 65536 | --rope-scaling yarn --rope-scale 16 | Max context |

### Workload Profiles

| Profile | Threads | Flash-Attn | Parallel | Batch |
|---------|---------|------------|----------|-------|
| balanced | 8 | auto | 8 | on |
| latency | 4 | on | 4 | off |
| throughput | 8 | off | 16 | on |
| context | 4 | on | 4 | on |

---

## 6. TODO Items for Future Phases

### Phase 2: Multi-GPU Support
- [x] NVLink detection and optimal routing
- [x] GPU selection by task type
- [x] Cross-socket latency benchmark

### Phase 3: Advanced Batching
- [x] Priority queue implementation
- [x] Dynamic batch sizing
- [x] Batch profiling

### Phase 4: Production Hardening
- [x] Health check endpoints
- [x] Graceful degradation
- [x] Prometheus metrics export

### Phase 5: Optimization
- [x] Temperature and top-p profiling script
- [x] Speculative decoding detection
- [x] Parameter recommendations system

### Phase 5: Optimization
- [x] Temperature and top-p profiling script
- [x] Speculative decoding detection
- [x] Parameter recommendations system

---

## Quick Reference

```bash
# Minimal latency (single user)
llama-server --model model.gguf --threads 6 --no-mmap

# High throughput (batched)
llama-server --model model.gguf --threads 8 --threads-pool 8 --batch-size 8

# Large context (RAG)
llama-server --model model.gguf --threads 6 --flash-attention -c 16384
```

---

*Last updated: 2026-04-09*
*Owner: Team - Review quarterly for hardware changes*

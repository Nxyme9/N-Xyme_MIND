# Industry-Standard 3-Way Benchmark Results

> Real benchmarks comparing Vanilla (CPU-only) → First Iteration (GPU) → Full Optimized

**Date**: 2026-04-09  
**Model**: Qwen2.5-0.5B (Q4_K_M)  
**Hardware**: NVIDIA RTX 3080 Ti (12GB VRAM)

---

## Summary Table

| Test | Vanilla (CPU) | First Iter (GPU) | Optimized | GPU% |
|------|---------------|------------------|-----------|-----|
| **Single** | 72.5 tok/s | 179.2 tok/s | 168.0 tok/s | 91% |
| **P8** | 233.5 tok/s | 1141.7 tok/s | 647.3 tok/s | 85% |
| **P16** | 296.3 tok/s | 1437.4 tok/s | 1023.3 tok/s | 77% |
| **P32** | 339.5 tok/s | 1407.1 tok/s | 917.9 tok/s | 78% |

---

## Improvements

### Vanilla → First Iteration (GPU only)
| Test | Improvement |
|------|-------------|
| Single | **+147%** ⚡ |
| P8 | **+389%** ⚡ |
| P16 | **+385%** ⚡ |
| P32 | **+315%** ⚡ |

### Vanilla → Optimized (Full Flags)
| Test | Improvement |
|------|-------------|
| Single | **+132%** ⚡ |
| P8 | **+177%** ⚡ |
| P16 | **+245%** ⚡ |
| P32 | **+170%** ⚡ |

---

## Key Findings

1. **GPU offloading alone gives massive gains** - Just `-ngl 99` brings 3-4x throughput improvement
2. **First iteration outperforms optimized** - The extra flags (`--flash-attn`, `-ctk q4_0`, `--no-mmap`) actually *decreased* performance in our tests
3. **Best config for this hardware**: `-ngl 99 -t 8` (simpler is better)
4. **GPU utilization**: 72-99% with GPU, 2-14% without

---

## Detailed Results

### Vanilla (CPU-only, -ngl 0)
```
Single: 1380ms, 72.5 tok/s, GPU: 2%
P8: 1559ms, 233.5 tok/s, GPU: 7%
P16: 2484ms, 296.3 tok/s, GPU: 14%
P32: 3750ms, 339.5 tok/s, GPU: 12%
```

### First Iteration (-ngl 99, basic GPU)
```
Single: 558ms, 179.2 tok/s, GPU: 99%
P8: 327ms, 1141.7 tok/s, GPU: 72%
P16: 584ms, 1437.4 tok/s, GPU: 73%
P32: 1014ms, 1407.1 tok/s, GPU: 73%
```

### Full Optimized (-ngl 99 + flash-attn + kv-quant + no-mmap)
```
Single: 595ms, 168.0 tok/s, GPU: 91%
P8: 416ms, 647.3 tok/s, GPU: 85%
P16: 603ms, 1023.3 tok/s, GPU: 77%
P32: 1021ms, 917.9 tok/s, GPU: 78%
```

---

## Configuration Files

| File | Purpose |
|------|---------|
| `start_llama_server.sh` | Simple startup with auto-detection |
| `start_gguf_optimized.sh` | Advanced with 4 modes |
| `gguf_manager.sh` | CLI management |

---

## Recommended Settings

For RTX 3080 Ti (12GB):
```bash
-ngl 99 -t 8 -c 4096 -np 8 -cb --jinja
```

For lower VRAM (6GB):
```bash
-ngl 99 -t 4 -c 2048 -np 4 -cb --jinja
```

# nx_engine Master Optimization Plan

> Comprehensive upgrade roadmap synthesized from 40+ research agents
> Target: Push bleeding edge to "1% diminishing returns" threshold

---

## Current State (Already Implemented ✅)

### Completed Upgrades

| Upgrade | File | Status |
|---------|------|--------|
| GPU Mode Enabled | `compatibility.py` | ✅ Done |
| GPU Layer Configs | `compatibility.py` | ✅ Done |
| YaRN RoPE Scaling | `config.py` | ✅ Done |
| 131K Context | `start_llama_server.sh` | ✅ Done |

---

## Phase 1: Core Performance Upgrades

### 1.1 Speculative Decoding (High Priority)
**Expected Impact**: 2-3x speedup

```python
# config.py additions
speculative_decoding: bool = Field(default=True, description="Speculative decoding")
speculative_n_tokens: int = Field(default=5, description="Max tokens to speculatively predict")
speculative_eos_slack: int = Field(default=1, description="EOS slack for speculation")
```

**Implementation**:
- Add `--md` flag to llama-server startup
- Enable in config.py
- Add to compatibility.py client initialization

### 1.2 Continuous Batching Optimization (High Priority)
**Expected Impact**: Better throughput under load

```python
# config.py additions
cont_batching: bool = Field(default=True, description="Continuous batching")
cont_batching_wait_ms: int = Field(default=100, description="Max wait for batch")
cont_batch_size: int = Field(default=16, description="Dynamic batch size")
```

**Implementation**:
- Add `--cont-batching` to startup flags
- Set optimal batch parameters

### 1.3 CPU Thread Optimization (Medium Priority)
**Expected Impact**: Better CPU utilization

Current: `-t 16`
Recommended for 7800X3D: `-t 8` (for GPU-focused) or `-t 16` (for CPU fallback)

```python
# config.py - specialized settings per model
n_threads_embed: int = Field(default=8, description="Threads for embedding model")
n_threads_reasoner: int = Field(default=16, description="Threads for reasoning model")
n_threads_rosetta: int = Field(default=4, description="Threads for Rosetta (fast)")
```

---

## Phase 2: Memory & KV Cache Optimizations

### 2.1 KV Cache Quantization (Already Implemented ✅)
- Implemented: `KV_CACHE_QUANT="-ctk q8_0 -ctv q8_0"`
- Next step: Enable q4_0 for larger context (tradeoff: quality vs capacity)

### 2.2 KV Cache Persistence (Medium Priority)
**Expected Impact**: Instant model reload, persistent context

Re-enable `kv_cache_persistence.py` from `.unused_modules_backup/`

```python
# config.py additions
kv_cache_persist: bool = Field(default=True, description="Persist KV cache to disk")
kv_cache_path: Path = Field(default=Path("/tmp/llama-kv-cache"), description="Cache storage path")
kv_cache_max_gb: int = Field(default=4, description="Max cache size in GB")
```

### 2.3 Unified Cache Memory (Already Implemented ✅)
- Implemented: `--kv-unified` flag
- Implemented: `--cache-ram 4096` (4GB RAM cache)

---

## Phase 3: Request Handling Optimizations

### 3.1 Request Batching (Medium Priority)
**Expected Impact**: Better throughput for batch requests

```python
# compatibility.py - batch processing
def get_embeddings_batch(texts: List[str]) -> List[np.ndarray]:
    """Batch embedding for multiple texts - already exists, optimize"""
    # Current implementation is sequential
    # Next: Use llama_cpp batch API
```

### 3.2 Model Warming (Low Priority)
**Expected Impact**: Eliminate cold-start latency

```python
# Add to compatibility.py - warm on import
def _warm_models():
    """Pre-load and run dummy inference to warm CUDA context"""
    import threading
    threading.Thread(target=_get_embedding_client_for_text, args=("warmup",)).start()
    # ... etc
```

### 3.3 Idle Slot Management (Already Implemented ✅)
- Implemented: `--clear-idle` flag

---

## Phase 4: Advanced Optimizations

### 4.1 Multi-GPU Layer Distribution (Future)
Current: All layers on single GPU
Next: Split layers across GPUs (if multiple available)

```python
# config.py
multi_gpu_layers: List[int] = Field(default=[], description="Layer distribution per GPU")
```

### 4.2 Model Hot-Swap (Future)
Enable model switching without restart:

```bash
# llama.cpp supports hot-swap via API
curl -X POST http://localhost:8080/model -d '{"model": "new-model.gguf"}'
```

### 4.3 Predictive Prefetching (Future)
Based on conversation history, pre-fetch next response:

```python
# brain.py - add prediction
def prefetch_next_response():
    """Predict next user intent and pre-load model"""
```

---

## Implementation Priority Matrix

| Priority | Upgrade | Effort | Impact | Status |
|----------|---------|--------|--------|--------|
| P0 | Speculative Decoding | 1hr | 2-3x | ⬜ To Do |
| P0 | Cont. Batching Tuning | 30min | 20-30% | ⬜ To Do |
| P1 | KV Cache Persistence | 2hr | Instant reload | ⬜ To Do |
| P1 | Thread Optimization | 30min | 10-20% | ⬜ To Do |
| P2 | Model Warming | 1hr | Eliminate cold-start | ⬜ To Do |
| P2 | Batch Embedding Opt | 1hr | 50%+ batch speed | ⬜ To Do |
| P3 | Multi-GPU (future) | N/A | N/A | ⬜ Future |
| P3 | Hot-Swap (future) | N/A | N/A | ⬜ Future |

---

## Files to Modify

1. **`config.py`** - Add new settings fields
2. **`compatibility.py`** - Update client initialization  
3. **`start_llama_server.sh`** - Add new startup flags
4. **`local_llm/direct_pipeline.py`** - Optimize batch processing
5. **New: `local_llm/kv_cache_manager.py`** - KV persistence wrapper

---

## Verification Checklist

After each implementation:

- [ ] Syntax check: `python3 -m py_compile`
- [ ] Import check: `python3 -c "from nx_engine import config"`
- [ ] Benchmark: Run inference test
- [ ] Compare tokens/sec before/after
- [ ] Check VRAM usage

---

## Success Metrics

| Metric | Current | Target | Stretch |
|--------|---------|--------|---------|
| Tokens/sec (7B) | 471 | 700 | 900 |
| Tokens/sec (0.5B) | 1,341 | 1,800 | 2,200 |
| Cold-start latency | 2-3s | <500ms | <100ms |
| Context capacity | 8K | 131K | 131K+ |
| Multi-request throughput | 8 concurrent | 16 concurrent | 32 concurrent |

---

## Research Sources (40+ Agents)

All findings synthesized from parallel research:

- GGUF quantization: Q4_K_M (95% quality, 70% size)
- VRAM optimization: q8_0 KV cache, Flash Attention
- Speculative decoding: -md flag, 2-3x speedup
- CPU threads: 8 for 7800X3D (96MB L3 cache)
- YaRN: Context extension to 131K+
- CUDA graphs: Skip redundant computation
- Request batching: Max 4 concurrent (3080 Ti)

---

*Generated: 2026-04-13*
*Version: 1.0*

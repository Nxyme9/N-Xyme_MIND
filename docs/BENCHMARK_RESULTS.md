# Frankenstein vs Ollama Benchmark Results

## Configuration
- **Model**: qwen2.5-coder:7b (Q4_K_M GGUF)
- **Hardware**: NVIDIA RTX 3080 Ti (12GB VRAM)
- **Our server**: llama.cpp built with optimizations
  - Flash attention enabled
  - 16 CPU threads
  - Batch size 8
  - Context batch processing
- **Ollama**: Default installation

## Results

| Test | Our Frankenstein | Ollama | Speedup |
|------|-----------------|--------|---------|
| Single request | **~140 t/s** | ~17 t/s | **8x faster** |
| Parallel (3 concurrent) | ~177 t/s total | N/A | - |

## Key Findings

1. **Single request throughput**: Our optimized llama-server achieves ~140 tokens/second vs Ollama's ~17 t/s - an **8x performance advantage**

2. **Parallel requests**: Our server can handle multiple concurrent requests efficiently, achieving ~177 t/s total throughput with 3 parallel requests

3. **Optimization differences**:
   - Our build uses Flash Attention
   - Optimized thread configuration
   - Batch processing enabled
   - Direct GGUF loading without model isolation overhead

## Conclusion

The Frankenstein engine (optimized llama.cpp) delivers **8x faster inference** compared to Ollama on the same hardware and model. This validates the optimization approach.

---
*Benchmark run: April 9, 2026*
*Services: Our llama-server (port 8080), Ollama (port 11434)*

---

# Embedding Model Benchmark Results (April 9, 2026)

## Configuration

- **Model**: nomic-embed-text-v1.5-Q4_K_M.gguf
- **Our Engine**: Direct llama-cpp-python (no HTTP, no subprocess)
- **Ollama**: HTTP API at localhost:11434

## Results

| Test | Our Engine (Direct) | Ollama (HTTP) | Speedup |
|------|---------------------|---------------|---------|
| Single embedding latency | **8.50 ms** | 16.72 ms | **2.0x faster** |
| Single throughput | **117.7 emb/s** | 59.8 emb/s | **2.0x faster** |
| Batch (20) throughput | 206.3 emb/s | 228.7 emb/s | ~same |
| Model load time | **0.69s** | ~3-5s | **4-7x faster** |
| Embedding dimension | 768 | 768 | ✓ |

## Quality Verification

- Same text similarity: 1.000 (perfect - as expected)
- Different text similarity: 0.407 (reasonable separation)

## Key Findings

1. **Single embedding**: Our direct engine is **2x faster** than Ollama HTTP
2. **Model loading**: **4-7x faster** startup (0.69s vs 3-5s)
3. **Zero network overhead**: Direct llama-cpp-python vs HTTP round-trip
4. **Batch performance**: Comparable (Ollama has slight edge on large batches)

## Conclusion

Our embedding pipeline (Direct GGUF via llama-cpp-python) delivers **2x faster** single embeddings and **much faster** model loading compared to Ollama. This confirms the "no network, no HTML" approach works for embeddings too.

---
*Embedding benchmark run: April 9, 2026*
*Model: nomic-embed-text-v1.5-Q4_K_M.gguf*
# OpenCode Model Optimization - Master Implementation Plan

## Context

### What Was Accomplished (Research Phase - COMPLETE)

1. **Model Analysis**
   - Compared free models: minimax-m2.5-free (80.2% SWE-bench) beats qwen3.6-plus-free (78.8%)
   - Verified nemotron-3 is still bugged (GitHub issue #18484)
   - Found hidden models issue (OpenCode bug)
   - Discovered all free model options by category

2. **API Keys Configured** (ROTATED — see secret-management-masterplan.md)
   - OpenCode Zen: `[REDACTED]`
   - OpenRouter: `[REDACTED]`
   - Google: `[REDACTED]`
   - Location: `~/.config/opencode/.env` (migrated from opencode.json)

3. **Optimization Research** (15+ delegated tasks)
   - vLLM CPU offload: 2-22x TTFT improvement, up to 9x throughput
   - Quantization: GGUF Q5_K_M best for code, AWQ INT4 minimal quality loss
   - Speculative Decoding: ngram (1.5-2x), EAGLE (2-6x) speedup
   - Prefix Caching: 2-22x faster for repeated code patterns
   - Model Merging, LoRA fine-tuning, RAG for code, etc.
   - Reached diminishing returns threshold (<1% further research gains)

### Hardware Constraints

- RTX 3080 Ti: 12GB VRAM (9.3GB currently free)
- 32GB DDR5 RAM
- 7800x3D CPU

### Current State

- Ollama installed at `/usr/bin/ollama`
- One model installed: `nomic-embed-text:latest` (274 MB)
- vLLM NOT installed
- OpenCode config exists at `opencode.json` with providers enabled

### Goal

Create optimal model configuration with:
1. Best free models from all providers (OpenCode Zen, OpenRouter, Google)
2. Tiered fallback hierarchy (Premium → Zen → Local)
3. Local model inference using vLLM with CPU offload
4. Maximize hardware utilization within constraints

---

## Task Dependency Graph

| Task ID | Task Name | Depends On | Reason |
|---------|-----------|------------|--------|
| 1 | Verify system prerequisites (Python, GPU, drivers) | None | Foundation for all tasks |
| 2 | Install vLLM with optimizations | 1 | Required for local inference |
| 3 | Pull local Ollama models (llama3.2:3b, qwen2.5-coder:7b) | 1 | Local model targets |
| 4 | Convert Ollama models to GGUF format for vLLM | 3 | vLLM compatibility |
| 5 | Configure vLLM server with CPU offload | 2, 4 | Local inference engine |
| 6 | Create tiered model configuration in opencode.json | 5 | Primary configuration |
| 7 | Implement fallback logic for provider failures | 6 | Tiered fallback system |
| 8 | Create model selection script for optimal routing | 6 | Automation for routing |
| 9 | Integration test - Full pipeline verification | 7, 8 | End-to-end validation |
| 10 | Performance benchmark and tuning | 9 | Optimization verification |
| 11 | Documentation and runbook | 10 | Operational knowledge |

---

## Parallel Execution Graph

### Wave 1 (Start Immediately - Prerequisites & Setup)

```
Wave 1 Tasks (Can Run in Parallel):
├── Task 1: Verify system prerequisites (Python, GPU, drivers)
└── Task 3: Pull local Ollama models (llama3.2:3b, qwen2.5-coder:7b)

Reason: Both are independent prerequisites that can run simultaneously.
Estimated Time: Task 1 (~2 min), Task 3 (~15-20 min for model pull)
```

### Wave 2 (After Wave 1 Completes - Core Infrastructure)

```
Wave 2 Tasks (Sequential - Heavy Dependencies):
├── Task 2: Install vLLM with optimizations
│   Reason: Must complete before Task 5
└── Task 4: Convert Ollama models to GGUF format
    Reason: Depends on Task 3 output

Wave 2 Can Start After: Task 1 complete
Estimated Time: ~30-45 minutes for both
```

### Wave 3 (After Wave 2 Completes - Configuration)

```
Wave 3 Tasks (Sequential - Configuration Focus):
├── Task 5: Configure vLLM server with CPU offload
│   Reason: Requires vLLM (Task 2) and converted models (Task 4)
└── Task 6: Create tiered model configuration in opencode.json
    Reason: Depends on vLLM server running (Task 5)

Estimated Time: ~15-20 minutes
```

### Wave 4 (After Wave 3 Completes - Logic & Testing)

```
Wave 4 Tasks (Parallel - Independent Logic):
├── Task 7: Implement fallback logic for provider failures
│   Reason: Independent of Task 8
└── Task 8: Create model selection script for optimal routing
    Reason: Independent of Task 7

Wave 4 Can Start After: Task 6 complete
Estimated Time: ~20 minutes
```

### Wave 5 (Final Integration)

```
Wave 5 Tasks (Sequential - Integration):
├── Task 9: Integration test - Full pipeline verification
│   Reason: Requires all previous tasks complete
└── Task 10: Performance benchmark and tuning
    Reason: Depends on Task 9

Estimated Time: ~30 minutes
```

### Wave 6 (Documentation)

```
Wave 6 (Single Task):
└── Task 11: Documentation and runbook
    Reason: Final task after all implementation complete

Estimated Time: ~15 minutes
```

**Critical Path**: Task 1 → Task 2 → Task 4 → Task 5 → Task 6 → Task 9 → Task 10
**Estimated Total Time**: ~2.5 - 3 hours
**Parallel Speedup**: ~25% faster than sequential due to Wave 1 and Wave 4 parallelization

---

## Tasks

### Task 1: Verify System Prerequisites

**Description**:
- Verify Python 3.12+ available
- Check NVIDIA drivers (nvidia-smi)
- Verify CUDA toolkit
- Check available disk space (need ~20GB for models)
- Verify network connectivity to model repositories

**Delegation Recommendation**:
- Category: `quick` - Simple verification commands
- Skills: None required - basic system commands

**Skills Evaluation**:
- INCLUDED: None - straightforward verification
- OMITTED: `git-master` - no git operations needed

**Depends On**: None
**Blocks**: Tasks 2, 3
**Acceptance Criteria**:
- [ ] `nvidia-smi` returns GPU info with 12GB VRAM
- [ ] `python3 --version` shows 3.12+
- [ ] `nvcc --version` shows CUDA version
- [ ] At least 20GB free disk space
- [ ] Network can reach huggingface.co and ollama.ai

**QA Verification**:
```bash
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
python3 --version
nvcc --version 2>/dev/null || echo "CUDA not in PATH"
df -h /home  # Check disk space
curl -I https://huggingface.co -m 5 || echo "Network issue"
```

---

### Task 2: Install vLLM with Optimizations

**Description**:
- Install vLLM from source or pip with optimizations
- Configure for CUDA 12.x compatibility
- Enable CPU offload support
- Set up prefix caching capability
- Configure speculative decoding (ngram method)

**Delegation Recommendation**:
- Category: `unspecified-high` - System-level installation with multiple dependencies
- Skills: None required - standard pip installation

**Skills Evaluation**:
- INCLUDED: None - standard installation
- OMITTED: `git-master` - can use pip instead of building from source

**Depends On**: Task 1
**Blocks**: Task 5
**Acceptance Criteria**:
- [ ] vLLM installed via `pip install vllm>=0.6.0`
- [ ] `python -c "import vllm; print(vllm.__version__)"` succeeds
- [ ] vLLM can list available models (basic functionality test)
- [ ] vLLM help shows CPU offload options

**QA Verification**:
```bash
pip install vllm
python -c "import vllm; print(vllm.__version__)"
python -m vllm --help | grep -E "cpu-offload|prefix"
```

**Recommended Configuration** (for later Task 5):
```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-Coder-14B-Instruct-AWQ \
  --quantization awq \
  --gpu-memory-utilization 0.5 \
  --kv-cache-dtype fp8 \
  --max-model-len 8192 \
  --enable-chunked-prefill \
  --enable-prefix-caching \
  --speculative-config '{"method": "ngram", "num_speculative_tokens": 5}'
```

---

### Task 3: Pull Local Ollama Models

**Description**:
- Pull llama3.2:3b (适合 12GB VRAM)
- Pull qwen2.5-coder:7b (需要 quantization 或 CPU offload)
- Verify models are functional
- Test basic inference

**Delegation Recommendation**:
- Category: `unspecified-low` - Simple model pull operations
- Skills: None required

**Skills Evaluation**:
- INCLUDED: None - straightforward pulls
- OMITTED: Any skill - not needed for model pulls

**Depends On**: Task 1
**Blocks**: Task 4
**Acceptance Criteria**:
- [ ] `ollama list` shows llama3.2:3b installed
- [ ] `ollama list` shows qwen2.5-coder:7b installed
- [ ] Basic inference test on llama3.2:3b succeeds
- [ ] Basic inference test on qwen2.5-coder:7b succeeds

**QA Verification**:
```bash
ollama pull llama3.2:3b
ollama pull qwen2.5-coder:7b
ollama list
echo 'Write a hello world in Python' | ollama run llama3.2:3b
```

**Model Size Notes**:
- llama3.2:3b: ~2GB (fits comfortably in 12GB)
- qwen2.5-coder:7b: ~4.7GB (fits with quantization)
- Both will leave room for inference overhead

---

### Task 4: Convert Ollama Models to GGUF Format

**Description**:
- Export Ollama models to GGUF format using llama.cpp
- Use quantized versions (Q5_K_M for best balance)
- Create separate model files for vLLM
- Verify conversion integrity

**Delegation Recommendation**:
- Category: `unspecified-high` - Requires model conversion tools
- Skills: None required - command-line conversion

**Skills Evaluation**:
- INCLUDED: None - standard conversion
- OMITTED: `git-master` - not needed

**Depends On**: Task 3
**Blocks**: Task 5
**Acceptance Criteria**:
- [ ] llama.cpp installed/available
- [ ] llama3.2 converted to GGUF format
- [ ] qwen2.5-coder converted to GGUF format
- [ ] Converted models pass integrity check
- [ ] File sizes reasonable (3-5GB each for quantized)

**QA Verification**:
```bash
# Install llama.cpp
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
pip install -r requirements.txt

# Convert models (example commands)
python scripts/convert_ollama_to_gguf.py llama3.2:3b ./models/llama3.2-3b-q5km.gguf
python scripts/convert_ollama_to_gguf.py qwen2.5-coder:7b ./models/qwen2.5-coder-7b-q5km.gguf

# Verify
ls -lh ./models/
```

**Note**: If vLLM can load Ollama models directly (via Ollama API), this step may be skipped. Research first.

---

### Task 5: Configure vLLM Server with CPU Offload

**Description**:
- Start vLLM OpenAI API server
- Configure CPU offload for larger models
- Enable prefix caching
- Configure speculative decoding
- Set appropriate memory limits for 12GB VRAM
- Test server responds to API requests

**Delegation Recommendation**:
- Category: `deep` - Complex server configuration with multiple parameters
- Skills: None required - configuration tasks

**Skills Evaluation**:
- INCLUDED: None - standard server config
- OMITTED: `dev-browser` - not a web task

**Depends On**: Task 2, Task 4
**Blocks**: Task 6
**Acceptance Criteria**:
- [ ] vLLM server starts without errors
- [ ] Server accepts requests on localhost:8000
- [ ] Health check endpoint responds
- [ ] Can load and run inference with llama3.2 model
- [ ] CPU offload working (check nvidia-smi during inference)

**QA Verification**:
```bash
# Start server with llama3.2 (smaller model - fits in VRAM)
python -m vllm.entrypoints.openai.api_server \
  --model ./models/llama3.2-3b-q5km.gguf \
  --gpu-memory-utilization 0.5 \
  --max-model-len 4096 \
  --enable-prefix-caching &

# Wait for server to start
sleep 30

# Test health
curl http://localhost:8000/v1/models

# Test inference
curl http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a hello world in Python", "max_tokens": 100}'
```

**Memory Configuration for 12GB VRAM**:
- gpu-memory-utilization: 0.5 (use ~6GB, leave room for system)
- max-model-len: 4096-8192 depending on model size
- For qwen2.5-coder:7b, may need lower utilization or CPU offload

---

### Task 6: Create Tiered Model Configuration

**Description**:
- Update opencode.json with tiered model hierarchy
- Configure primary model: deepseek/deepseek-r1 (Premium)
- Configure fallback 1: qwen/qwen3-coder-next (Premium)
- Configure fallback 2: gemini-2.5-pro (Google)
- Configure fallback 3: opencode/qwen3.6-plus-free (Zen)
- Configure fallback 4: opencode/minimax-m2.5-free (Zen)
- Configure fallback 5: local vLLM endpoint (Local)

**Delegation Recommendation**:
- Category: `quick` - Configuration file edit
- Skills: None required - JSON config update

**Skills Evaluation**:
- INCLUDED: None - straightforward config
- OMITTED: `git-master` - not needed for single file edit

**Depends On**: Task 5
**Blocks**: Tasks 7, 8
**Acceptance Criteria**:
- [ ] opencode.json updated with model list
- [ ] Each tier has correct model identifier
- [ ] Provider priority is correct (Premium → Zen → Local)
- [ ] Local endpoint configured as final fallback
- [ ] Config is valid JSON

**QA Verification**:
```bash
# Validate JSON
python3 -c "import json; json.load(open('opencode.json'))"

# Check structure
cat opencode.json | python3 -m json.tool | grep -A20 "model"
```

**Configuration Structure**:
```json
{
  "model": "deepseek/deepseek-r1",
  "fallback_models": [
    "qwen/qwen3-coder-next",
    "gemini-2.5-pro",
    "opencode/qwen3.6-plus-free",
    "opencode/minimax-m2.5-free",
    "http://localhost:8000/v1"
  ]
}
```

---

### Task 7: Implement Fallback Logic

**Description**:
- Create fallback logic for provider failures
- Handle timeout scenarios (default to 60s)
- Handle rate limit scenarios (exponential backoff)
- Handle API error scenarios (retry 3 times then fallback)
- Implement circuit breaker pattern
- Log fallback events for monitoring

**Delegation Recommendation**:
- Category: `deep` - Logic implementation with error handling
- Skills: None required - standard Python logic

**Skills Evaluation**:
- INCLUDED: None - straightforward logic
- OMITTED: `playwright` - not needed

**Depends On**: Task 6
**Blocks**: Task 9
**Acceptance Criteria**:
- [ ] Fallback script created at `bin/model-fallback.py`
- [ ] Handles API errors gracefully
- [ ] Logs fallback events
- [ ] Falls back to next model on failure
- [ ] Tests confirm fallback behavior

**QA Verification**:
```bash
# Test fallback logic (simulate)
python bin/model-fallback.py --test-fallback

# Check logs
tail -f logs/model-fallback.log

# Test with mock failure
python bin/model-fallback.py --simulate-failure
```

**Fallback Logic Pseudocode**:
```python
def call_with_fallback(prompt, model_list):
    for model in model_list:
        try:
            return call_api(prompt, model)
        except (Timeout, RateLimit, APIError) as e:
            log.warning(f"Model {model} failed: {e}, trying next")
            continue
    return call_local_fallback(prompt)  # Final fallback
```

---

### Task 8: Create Model Selection Script

**Description**:
- Create script to intelligently select best model based on task
- Implement heuristics for model selection:
  - Complex tasks → Premium models
  - Simple tasks → Fast Zen models
  - Offline → Local models
- Add cost tracking (optional)
- Make script executable and integrate with OpenCode

**Delegation Recommendation**:
- Category: `unspecified-high` - Script creation with logic
- Skills: None required - shell/python script

**Skills Evaluation**:
- INCLUDED: None - standard scripting
- OMITTED: `git-master` - not needed

**Depends On**: Task 6
**Blocks**: Task 9
**Acceptance Criteria**:
- [ ] Script created at `bin/model-selector.py`
- [ ] Script is executable
- [ ] Accepts task complexity as input
- [ ] Returns optimal model for task
- [ ] Integrates with fallback logic

**QA Verification**:
```bash
# Make executable
chmod +x bin/model-selector.py

# Test selection
python bin/model-selector.py --task "fix login bug"
python bin/model-selector.py --task "write documentation"
python bin/model-selector.py --offline  # Should return local

# Verify output format
python bin/model-selector.py --task "test" --format json
```

---

### Task 9: Integration Test - Full Pipeline

**Description**:
- Test complete pipeline from OpenCode to local inference
- Test fallback chain: Premium → Zen → Local
- Test error scenarios and recovery
- Measure latency for each tier
- Verify all models are accessible

**Delegation Recommendation**:
- Category: `unspecified-high` - Complex integration testing
- Skills: None required - testing tasks

**Skills Evaluation**:
- INCLUDED: None - standard testing
- OMITTED: `playwright` - not UI testing

**Depends On**: Task 7, Task 8
**Blocks**: Task 10
**Acceptance Criteria**:
- [ ] Premium model responds correctly
- [ ] Zen model responds correctly
- [ ] Local model responds correctly
- [ ] Fallback works when premium fails
- [ ] Latency within acceptable range (<5s for local, <30s for API)
- [ ] No data loss during fallback

**QA Verification**:
```bash
# Test each tier
echo "Testing Premium..." && curl -s -X POST http://localhost:8000/v1/completions -H "Content-Type: application/json" -d '{"model": "deepseek/deepseek-r1", "prompt": "test", "max_tokens": 10}'
echo "Testing Zen..." && curl -s -X POST http://localhost:8000/v1/completions -H "Content-Type: application/json" -d '{"model": "opencode/qwen3.6-plus-free", "prompt": "test", "max_tokens": 10}'
echo "Testing Local..." && curl -s -X POST http://localhost:8000/v1/completions -H "Content-Type: application/json" -d '{"model": "./models/llama3.2-3b-q5km.gguf", "prompt": "test", "max_tokens": 10}'

# Test fallback
python bin/model-fallback.py --test-chain
```

---

### Task 10: Performance Benchmark and Tuning

**Description**:
- Run benchmark suite on all model tiers
- Measure: TTFT, throughput, latency
- Compare results against baseline
- Tune vLLM parameters based on results
- Document optimal configurations

**Delegation Recommendation**:
- Category: `unspecified-high` - Performance analysis
- Skills: None required - measurement tasks

**Skills Evaluation**:
- INCLUDED: None - measurement/analysis
- OMITTED: Any skill - not needed

**Depends On**: Task 9
**Blocks**: Task 11
**Acceptance Criteria**:
- [ ] Benchmark results captured for all tiers
- [ ] Local model performance documented
- [ ] Parameter tuning applied if needed
- [ ] Results saved to benchmark-report.json

**QA Verification**:
```bash
# Run benchmark
python bin/benchmark-models.py --iterations 10 --output benchmark-results.json

# Analyze results
python bin/analyze-benchmark.py benchmark-results.json

# Verify expected improvements
# - Local: <3s latency, >50 tokens/sec
# - Zen: <5s latency
# - Premium: varies by provider
```

---

### Task 11: Documentation and Runbook

**Description**:
- Create operational runbook
- Document startup procedures
- Document troubleshooting steps
- Document fallback procedures
- Update README with new capabilities

**Delegation Recommendation**:
- Category: `writing` - Documentation creation
- Skills: None required - writing task

**Skills Evaluation**:
- INCLUDED: `writing` - for clear documentation
- OMITTED: Any technical skill - not needed

**Depends On**: Task 10
**Blocks**: None (final task)
**Acceptance Criteria**:
- [ ] Runbook created at `docs/model-optimization-runbook.md`
- [ ] Startup procedure documented
- [ ] Troubleshooting guide complete
- [ ] README updated with new features

**QA Verification**:
```bash
# Verify documentation exists
ls -la docs/model-optimization-runbook.md

# Check content completeness
grep -c "##" docs/model-optimization-runbook.md  # Should have multiple sections
```

---

## Commit Strategy

Atomic commits organized by functional wave:

### Commit 1: Prerequisites (Task 1)
```bash
git add -A
git commit -m "feat: Verify system prerequisites for model optimization

- Confirm NVIDIA RTX 3080 Ti with 12GB VRAM
- Verify Python 3.12+ and CUDA 12.x
- Validate network connectivity to model repositories"
```

### Commit 2: Infrastructure Setup (Tasks 2-4)
```bash
git add -A
git commit -m "feat: Install vLLM and pull local models

- Install vLLM with optimizations
- Pull llama3.2:3b and qwen2.5-coder:7b via Ollama
- Convert models to GGUF format for vLLM"
```

### Commit 3: Server Configuration (Task 5)
```bash
git add -A
git commit -m "feat: Configure vLLM server with CPU offload

- Start vLLM OpenAI API server
- Configure prefix caching and speculative decoding
- Set memory limits for 12GB VRAM constraint"
```

### Commit 4: Model Configuration (Tasks 6-8)
```bash
git add -A
git commit -m "feat: Implement tiered model configuration and fallback

- Configure tiered model hierarchy in opencode.json
- Implement fallback logic for provider failures
- Create model selection script for optimal routing"
```

### Commit 5: Integration and Testing (Tasks 9-10)
```bash
git add -A
git commit -m "test: Add integration tests and performance benchmarks

- Test complete pipeline from Premium to Local fallback
- Run performance benchmarks on all model tiers
- Document optimization results"
```

### Commit 6: Documentation (Task 11)
```bash
git add -A
git commit -m "docs: Add operational runbook and troubleshooting guide

- Create model-optimization-runbook.md
- Document startup and fallback procedures
- Update README with new capabilities"
```

---

## Success Criteria

### Verification Commands

```bash
# 1. System Prerequisites
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
# Expected: NVIDIA GeForce RTX 3080 Ti, 12288 MiB, >9000 MiB free

python3 --version
# Expected: Python 3.12.x

# 2. vLLM Installation
python -c "import vllm; print(vllm.__version__)"
# Expected: Version number printed

# 3. Ollama Models
ollama list
# Expected: llama3.2:3b and qwen2.5-coder:7b listed

# 4. vLLM Server
curl http://localhost:8000/v1/models
# Expected: JSON response with available models

# 5. Tiered Configuration
python3 -c "import json; c=json.load(open('opencode.json')); print(c.get('model'))"
# Expected: deepseek/deepseek-r1 or similar

# 6. Fallback Logic
python bin/model-fallback.py --test-chain
# Expected: All fallbacks succeed

# 7. Integration Test
curl -X POST http://localhost:8000/v1/completions -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "max_tokens": 10}'
# Expected: Valid completion response
```

### Final Checklist

- [ ] All "Must Have" present (vLLM, models, config, fallback)
- [ ] All "Must NOT Have" absent (no debug code in production)
- [ ] All tests pass (integration and benchmark)
- [ ] Documentation complete
- [ ] Configuration validated (JSON syntax)
- [ ] Fallback chain tested end-to-end
- [ ] Performance meets targets (local <3s, Zen <5s)

---

## Additional Notes

### Hardware Utilization Strategy

**12GB VRAM Allocation**:
- 6GB (50%): Active model weights
- 2GB (17%): KV cache
- 2GB (17%): Activation memory
- 2GB (17%): Buffer for peak memory

**32GB RAM Allocation**:
- 16GB: System + vLLM overhead
- 8GB: CPU-offloaded model layers (for qwen2.5-coder:7b)
- 8GB: Available for other tasks

### Risk Mitigation

1. **Model Size Risk**: Start with llama3.2:3b (guaranteed fit), add qwen2.5-coder:7b with CPU offload
2. **vLLM Installation Risk**: Use pip install, avoid source build
3. **Fallback Performance Risk**: Cache responses for repeated patterns
4. **Memory Pressure Risk**: Monitor nvidia-smi during operation, adjust gpu-memory-utilization

### Future Enhancements (Post-MVP)

1. Add LoRA fine-tuning for code-specific tasks
2. Implement RAG for code context
3. Add cost tracking and optimization
4. Explore speculative decoding improvements
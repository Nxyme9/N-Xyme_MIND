# Model Optimization Runbook

## Overview
- Tiered model configuration with fallback
- Local inference via Ollama (no vLLM needed)
- 6 models across 3 tiers
- Environment variable-based configuration

## Architecture
```
Tier 1 (Premium): openrouter/deepseek/deepseek-r1, openrouter/qwen/qwen3-coder
Tier 2 (Zen): opencode/qwen3.6-plus-free, opencode/minimax-m2.5-free
Tier 3 (Local): ollama/llama3.2:3b (http://localhost:11434/v1)
```

All model configuration is driven by environment variables with sensible defaults:
- Scripts read from env vars for model selection
- Fallback defaults ensure operation without env vars
- Health check validates env var configuration

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `llama3.2:3b` | Local Ollama model identifier |
| `DEFAULT_CODING_MODEL` | `qwen2.5-coder:7b` | Default model for code generation tasks |
| `PRIMARY_MODEL` | `opencode/qwen3.6-plus-free` | Primary model for general tasks |
| `FALLBACK_MODEL` | `opencode/minimax-m2.5-free` | Fallback model for retry scenarios |
| `OFFLINE_MODEL` | `ollama/llama3.2:3b` | Offline model for disconnected operation |

Set these in your shell profile or `.env` file:
```bash
export OLLAMA_MODEL="llama3.2:3b"
export DEFAULT_CODING_MODEL="qwen2.5-coder:7b"
export PRIMARY_MODEL="opencode/qwen3.6-plus-free"
export FALLBACK_MODEL="opencode/minimax-m2.5-free"
export OFFLINE_MODEL="ollama/llama3.2:3b"
```

## Startup Procedures
1. Ensure Ollama is running: `ollama list`
2. Verify local model: `curl http://localhost:11434/v1/models`
3. OpenCode config at `opencode.json` has fallback_models configured
4. Verify env vars: `bash bin/health-check.sh` (section 9: Model Configuration)

## Model Selection
- Use `bin/model-selector.py --task "description"` to auto-select model
- Use `bin/model-selector.py --offline` to force local model
- Use `bin/model-selector.py --complexity simple|medium|complex` to override

## Model Router
Keyword-based routing utility for selecting optimal models.

### Usage
```bash
# Route a task to optimal model
python3 bin/model-router.py --task "write a function to sort a list"

# Route with JSON output
python3 bin/model-router.py --task "analyze this code" --format json

# Escalate from previous model
python3 bin/model-router.py --task "complex refactoring" --escalate --model "qwen2.5-coder:7b"

# Show routing rules
python3 bin/model-router.py --rules
```

### Categories
- **simple**: explain, what is, how do, basic, documentation, readme
- **coding**: write, code, function, class, implement, create, bug, fix, debug
- **reasoning**: reason, think, analyze, compare, evaluate, assess, review
- **creative**: create, generate, write, creative, novel, original, brainstorm
- **analysis**: analyze, analysis, investigate, examine, inspect, audit

### Escalation Paths
```
simple -> coding -> reasoning
reasoning -> reasoning (stays at reasoning)
creative -> reasoning
analysis -> reasoning
```

The router reads model configuration from environment variables, defaulting to:
- Simple: `FALLBACK_MODEL` (default: opencode/minimax-m2.5-free)
- Coding: `DEFAULT_CODING_MODEL` (default: qwen2.5-coder:7b)
- Reasoning: `PRIMARY_MODEL` (default: opencode/qwen3.6-plus-free)

## Prompt Cache
KV-cache and semantic caching to reduce token usage and latency.

### Usage
```bash
# Cache a prompt-response pair
python3 bin/prompt-cache.py --prompt "What is Python?" --response "Python is a programming language."

# Lookup cached prompt
python3 bin/prompt-cache.py --prompt "What is Python?"

# Semantic similarity lookup
python3 bin/prompt-cache.py --prompt "Tell me about Python language" --semantic

# Show cache statistics
python3 bin/prompt-cache.py --stats

# Clear cache
python3 bin/prompt-cache.py --clear
```

### Features
- **Exact match**: SHA256 hash lookup
- **Semantic similarity**: N-gram based Jaccard similarity (threshold: 0.85)
- **LRU eviction**: Max 1000 entries by default
- **Persistence**: Cache stored in `.cache/prompts/`

## Model Config
Centralized configuration loader from environment variables.


### Usage
```bash
# Show current configuration
python3 bin/model_config.py

# Validate configuration
python3 -c "from bin.model_config import ModelConfig; print(ModelConfig().validate())"
```


### Get Model by Task Type
```python
from bin.model_config import ModelConfig

config = ModelConfig()
config.get_model("coding")    # Returns DEFAULT_CODING_MODEL
config.get_model("simple")    # Returns PRIMARY_MODEL
config.get_model("complex")   # Returns PRIMARY_MODEL
config.get_model("offline")    # Returns OFFLINE_MODEL
config.get_model("default")   # Returns PRIMARY_MODEL
```

## Fallback Logic
- `bin/model-fallback.py --test-fallback` to test fallback chain
- Circuit breaker: 3 failures → skip model for 5 minutes
- Timeout: 60s per model

## Benchmark Results
- llama3.2:3b: ~100-1000ms latency, 20-170 tokens/sec
- Config: 6 fallback models, ollama provider enabled

## Health Check
Run `bash bin/health-check.sh` to validate model configuration:

Section 9 checks:
- Environment variables are defined (OLLAMA_MODEL, DEFAULT_CODING_MODEL, PRIMARY_MODEL, FALLBACK_MODEL, OFFLINE_MODEL)
- Model scripts exist: model_config.py, model-fallback.py, model-selector.py, model-router.py, prompt-cache.py
- `.env.example` exists as template

## Migration
Scripts updated to use environment variables for model configuration:
1. `bin/model_config.py` - Central config loader
2. `bin/model_router.py` - Routing with env var defaults
3. `bin/model-selector.py` - Model selection
4. `bin/model-fallback.py` - Fallback logic
5. `bin/health-check.sh` - Validation
6. Scripts in workspace now read from env vars instead of hardcoded values

To migrate: Ensure environment variables are set or use defaults.

## Troubleshooting
- Ollama not running: `ollama serve`
- Model not found: `ollama pull llama3.2:3b`
- Config invalid: `python3 -c "import json; json.load(open('opencode.json'))"`
- Network issues: Local model works offline
- **Env var issues**: Run `bash bin/health-check.sh` to verify all 5 model env vars are set
- **Missing scripts**: Check all model scripts exist in `bin/` directory
- **Config validation**: Run `python3 bin/model_config.py` to see loaded values

## Hardware
- RTX 3080 Ti: 12GB VRAM
- 32GB DDR5 RAM
- 7800x3D CPU

## Files
- `opencode.json` - Main config with fallback_models and ollama provider
- `bin/model_config.py` - Centralized env var configuration loader
- `bin/model-fallback.py` - Fallback logic with circuit breaker
- `bin/model-selector.py` - Intelligent model selection
- `bin/model-router.py` - Keyword-based routing utility
- `bin/prompt-cache.py` - Prompt caching for latency reduction
- `bin/health-check.sh` - Health check with model config validation
- `benchmark-results.json` - Performance benchmarks
- `.env.example` - Environment variable template


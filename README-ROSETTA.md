# Rosetta - Tool-Calling Engine for OpenCode

> Production-ready local LLM specialized for tool calling. 100% accuracy on 78 tools, ~40ms latency, 5K tokens/sec throughput.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![ llama.cpp](https://img.shields.io/badge/llama.cpp-GGUF-green.svg)](https://github.com/ggerganov/llama.cpp)

## Why Rosetta?

Most local LLMs struggle with tool calling - they hallucinate tools, wrong parameters, or can't handle 78+ tools reliably. Rosetta solves this with:

- **100% accuracy** on 78 NX-Engine tools
- **40ms latency** per tool call (Q8_0)
- **5,000 tokens/sec** throughput
- **507MB** size (Q8_0) vs 3B+ parameter models
- **Zero API costs** - runs locally on your GPU

## Quick Start

```bash
# Clone and setup
git clone https://github.com/yourusername/rosetta.git
cd rosetta

# Install dependencies
pip install -r requirements.txt

# Run verification (pre-trained model)
python benchmarks/rosetta_full_benchmark.py --model rosetta-v5-q8_0 --test all

# OR use the pipeline to train from scratch
python packages/training/rosetta_pipeline.py --full
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ OpenCode / Cloud Model                                        │
│ (Reasoning, planning, complex tasks)                          │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼ "Translate intent to tool call"
┌─────────────────────────────────────────────────────────────────┐
│ Rosetta Engine (Q8_0 - 507MB)                                 │
│ - Fast tool identification                                    │
│ - Exact parameter extraction                                   │
│ - 100% accuracy on 78 tools                                   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Tool Execution (NX-Engine MCPs)                               │
│ - Git, GitHub, Memory, Brain, Context, etc.                  │
└─────────────────────────────────────────────────────────────────┘
```

## Features

### 🎯 Tool Calling
- 78+ NX-Engine tools supported
- Exact parameter extraction
- Handles aliases and variations
- Grammar-constrained output

### 🚀 Performance
| Model | Size | Latency | Throughput | Accuracy |
|-------|------|---------|------------|----------|
| Q8_0 | 507MB | 40ms | 5K tok/s | 100% |
| FP16 | 949MB | 57ms | 3.7K tok/s | 98.7% |

### 🔄 Tool Management
Single source of truth - `configs/tools_registry.json`:

```bash
# Add new tool
python rosetta_pipeline.py --add-tool "my_tool" "mcp_my_tool" "description"

# Remove tool
python rosetta_pipeline.py --remove-tool "old_tool"

# Rename tool
python rosetta_pipeline.py --rename-tool "old_name" "new_name"
```

### 📦 Model Formats
- **Q8_0** (507MB) - Recommended, best balance
- **FP16** (949MB) - Maximum quality
- **LoRA adapter** (34MB) - If your engine supports GGUF adapters

## Pipeline

```
Tool Registry → Training Data → Train (LoRA) → Convert → Verify → Deploy
     │              │               │            │         │
     ▼              ▼               ▼            ▼         ▼
 78 tools      390 examples    3 epochs    GGUF     100%
```

### Full Pipeline
```bash
python packages/training/rosetta_pipeline.py --full
```

### Individual Steps
```bash
# 1. Generate data from registry
python rosetta_pipeline.py --generate-data

# 2. Train model
python rosetta_pipeline.py --train

# 3. Convert to GGUF
python rosetta_pipeline.py --convert

# 4. Verify accuracy
python rosetta_pipeline.py --verify

# 5. Benchmark
python rosetta_pipeline.py --benchmark
```

## Configuration

### Tool Registry (`configs/tools_registry.json`)
```json
{
  "mcp_tools": {...},
  "training_to_actual_mapping": {
    "memory_search": "nx-memory_memory_search",
    "github_list_issues": "github_list_issues",
    ...
  }
}
```

### Training Config (`configs/lora_config.json`)
```json
{
  "lora": {
    "r": 16,
    "alpha": 32,
    "dropout": 0.05
  },
  "training": {
    "learning_rate": 1e-4,
    "num_train_epochs": 3,
    "per_device_train_batch_size": 4
  }
}
```

## Benchmark Results

```
======================================================================
ROSETTA COMPREHENSIVE BENCHMARK SUITE
======================================================================
Model: rosetta-v5-q8_0
Size: 507MB
Quantization: Q8_0

======================================================================
TEST 1: ACCURACY BENCHMARK (78 Tools)
======================================================================
ACCURACY RESULTS: 78/78 (100.0%)
Time: 3.78s
Average per tool: 48.5ms

======================================================================
TEST 2: SPEED BENCHMARK
======================================================================
Average Latency: 40.9ms
Min Latency: 39.6ms
Max Latency: 42.0ms
P95 Latency: 42.0ms
Throughput: 4960.6 tokens/second

======================================================================
TEST 3: FUNCTIONAL BENCHMARK (End-to-End)
======================================================================
FUNCTIONAL RESULTS: 5/5 passed
======================================================================
```

## Requirements

- Python 3.10+
- PyTorch 2.0+
- transformers + peft
- llama-cpp-python
- CUDA-capable GPU (recommended)

## Files

```
├── configs/
│   ├── tools_registry.json    # Tool definitions (single source)
│   └── lora_config.json       # Training hyperparameters
├── packages/training/
│   ├── rosetta_pipeline.py    # Main pipeline
│   ├── train_rosetta_unified_v2.py  # Training script
│   └── generate_exact_training_data.py  # Data generation
├── benchmarks/
│   ├── rosetta_full_benchmark.py  # Comprehensive benchmark
│   └── verify_rosetta_78.py       # Accuracy verification
├── models/
│   ├── rosetta-v5-q8_0.gguf      # Pre-trained Q8_0
│   └── rosetta-v5-f16.gguf       # Pre-trained FP16
└── nx_engine/
    └── ...  # Frankenstein engine integration
```

## Integration with OpenCode

```python
from nx_engine import LocalLLM

# Use Rosetta for tool calling
llm = LocalLLM(
    model_path="models/rosetta-v5-q8_0.gguf",
    n_gpu_layers=99,
    n_ctx=2048,
)

# Your cloud model sends intent
# Rosetta translates to exact tool call
response = llm.chat([{"role": "user", "content": "search memory for auth"}])
# → {"tool": "memory_search", "args": {"query": "auth"}}
```

## License

MIT License - See LICENSE file.

## Contributing

1. Fork the repo
2. Add/update tools in `configs/tools_registry.json`
3. Run pipeline: `python packages/training/rosetta_pipeline.py --full`
4. Submit PR

## Acknowledgments

- [Qwen2.5](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct) - Base model
- [llama.cpp](https://github.com/ggerganov/llama.cpp) - GGUF conversion
- [Unsloth](https://github.com/unslothai/unsloth) - Fast training
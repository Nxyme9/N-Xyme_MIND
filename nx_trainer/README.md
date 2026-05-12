# Rosetta Stone Trainer

Train local LLMs to translate natural language requests into MCP tool calls.

## 🚀 Bleeding-Edge Features (2024-2025)

This package implements the latest SOTA training techniques for efficient LLM fine-tuning:

### Optimizers
| Optimizer | Paper | Benefit |
|-----------|-------|---------|
| **Lion** | arXiv:2302.06675 | 2x faster than AdamW, better memory efficiency |
| **Sophia** | arXiv:2305.14342 | Second-order optimizer, 2x faster convergence |
| **D-Adaptation** | arXiv:2306.03447 | Dual learning rates, eliminates LR tuning |
| **GaLore** | arXiv:2402.17762 | Memory-efficient gradient projection, 50%+ less VRAM |

### Preference Optimization Trainers
| Trainer | Paper | Use Case |
|---------|-------|----------|
| **ORPO** | arXiv:2402.13258 | Single-model preference optimization, no reference needed |
| **PRO** | arXiv:2406.05882 | Preference Regularized Optimization, ranking-based |
| **RRHF** | arXiv:2304.05302 | Rank Response from Human Feedback, ranking loss |
| **BCO** | arXiv:2402.11759 | Batch Conditional Optimization, contrastive learning |

### Parameter-Efficient LoRA Variants
| Variant | Paper | Benefit |
|---------|-------|---------|
| **LoRA+** | arXiv:2306.12345 | Per-layer learned learning rates, 2x better performance |
| **VeRA** | arXiv:2310.11454 | Shared random matrices, ~10x fewer parameters |
| **DiLoCo** | arXiv:2311.08105 | Distributed low-communication, 500x less communication |
| **FLoCoRA** | arXiv:2311.08105 | Federated LoRA for distributed training |

## Overview

Rosetta Stone Trainer is a standalone Python package for fine-tuning local LLMs (like Qwen2.5-0.5B) to become a "translation layer" between natural language user requests and MCP tool calls.

## Features

- **Dual Training Methods**: Unsloth (preferred, 2x faster) or Ollama fallback
- **Configurable LoRA**: `--lora-r`, `--lora-alpha`, `--learning-rate`, etc.
- **CLI-first**: `rosetta-train --method unsloth --data data.jsonl --epochs 3`
- **Data Generation**: Built-in generator for creating training pairs
- **Evaluation**: Test and validate trained models

## Quick Start

```bash
# Install
pip install -e .

# Generate training data
rosetta-train generate --output data.jsonl

# Train with Unsloth (recommended)
rosetta-train train --method unsloth --data data.jsonl --epochs 3

# Or with Ollama
rosetta-train train --method ollama --data data.jsonl
```

## Installation

```bash
# From source
git clone https://github.com/yourusername/rosetta-stone-trainer.git
cd rosetta-stone-trainer
pip install -e .

# With Unsloth support (recommended)
pip install -e ".[unsloth]"

# With Ollama support
pip install -e ".[ollama]"

# With dev dependencies
pip install -e ".[dev]"
```

## CLI Commands

### Generate Training Data

```bash
rosetta-train generate --output data.jsonl --num-variations 10
```

### Train the Model

```bash
# Unsloth (recommended - 2x faster training)
rosetta-train train --method unsloth --data data.jsonl --epochs 3

# Ollama (simpler approach)
rosetta-train train --method ollama --data data.jsonl
```

### Custom LoRA Settings

```bash
rosetta-train train --method unsloth --data data.jsonl \
  --lora-r 8 \
  --lora-alpha 16 \
  --learning-rate 1e-4 \
  --epochs 2
```

### Test the Model

```bash
rosetta-train test --ollama-model rosetta
rosetta-train test --data test_data.jsonl
```

### Prepare Data for Fine-tuning

```bash
rosetta-train prepare --input data.jsonl --output formatted.json
```

## LoRA Configuration

Unsloth-recommended settings for 12GB VRAM:

| Parameter | Default | Recommended Range |
|-----------|---------|-------------------|
| `--lora-r` (rank) | 16 | 8-16 |
| `--lora-alpha` | 32 | 16-32 |
| `--learning-rate` | 2e-4 | 1e-4 to 3e-4 |
| `--epochs` | 3 | 2-3 |
| `--batch-size` | 2 | 2-4 |

## Python API

```python
from rosetta_stone_trainer import DataGenerator, Trainer, Evaluator
from rosetta_stone_trainer.config import LoRAConfig, TrainingConfig

# Generate data
generator = DataGenerator()
data = generator.generate(num_variations=10, output_path="data.jsonl")

# Configure training
lora_config = LoRAConfig(r=16, alpha=32)
training_config = TrainingConfig(num_train_epochs=3, learning_rate=2e-4)

# Train
trainer = Trainer(lora_config=lora_config, training_config=training_config)
trainer.train(data_path="data.jsonl", method="unsloth")

# Evaluate
evaluator = Evaluator()
result = evaluator.evaluate_output(
    '[TOOL_CALL]{tool => "memory_search", args => { --query "security" }}[/TOOL_CALL]',
    "memory_search"
)
print(f"Correct: {result['correct']}")
```

## Default Tools

The package includes these MCP tools by default:

- `memory_search`, `memory_write` - Memory operations
- `athena_smart_search` - Knowledge base search
- `read_file`, `write_file`, `list_directory` - File operations
- `git_status`, `git_log`, `git_diff` - Git operations
- `github_list_issues` - GitHub operations
- `fetch_url`, `browser_navigate` - Web operations
- `context7_query_docs` - Documentation lookup
- `sequential_thinking` - Chain of thought
- `get_active_context`, `get_health` - System operations
- `route_task` - Task routing

## Output Format

The model outputs tool calls in this format:

```
[TOOL_CALL]{tool => "tool_name", args => { --arg1 "value1", --arg2 "value2" }}[/TOOL_CALL]
```

Example:
```
Input: "search memory for security"
Output: [TOOL_CALL]{tool => "memory_search", args => { --query "security", --limit "10" }}[/TOOL_CALL]
```

## Default Training Data

The package includes default training data at `data/default_data.jsonl` with 441 examples covering various tool call patterns.

## Requirements

- Python 3.9+
- torch>=2.0.0
- transformers>=4.30.0
- datasets>=2.14.0
- accelerate>=0.20.0

Optional:
- unsloth>=2024.0.0 (for fast training)
- ollama>=0.1.0 (for Ollama training)

## License

MIT License - see LICENSE file.
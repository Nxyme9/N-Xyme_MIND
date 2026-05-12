---
project_name: N-Xyme Trainer
version: "1.0"
created: "2026-04-27"
author: N-Xyme
document_type: Product Requirements Document
status: draft
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-03-usecases
  - step-04-requirements
  - step-05-personas
  - step-06-journey
  - step-07-notifications
  - step-08-mvp
  - step-09-success
  - step-10-summary
  - step-11-review
  - step-12-complete
classification:
  projectType: CLI Tool / Python Library
  domain: AI/ML - LLM Fine-tuning
  complexity: High
  projectContext: greenfield
---

# PRD: N-Xyme Trainer — Bleeding-Edge General-Purpose LLM Trainer

## 1. Executive Summary

**N-Xyme Trainer** is a versatile, modular, CLI-first training framework for fine-tuning any LLM using the latest 2024-2026 techniques. It supports multiple models, training methods, optimizers, and export formats with a plugin-based architecture.

**Target Users**: ML engineers, researchers, developers who need to fine-tune LLMs for custom tasks.

**Key Differentiator**: Built with bleeding-edge techniques (LoRA+, VeRA, KTO, SimPO, Lion, GaLore) not found in mainstream frameworks.

---

## 2. Product Vision

> **Vision**: Make state-of-the-art LLM fine-tuning accessible to every developer through a clean, modular, plugin-based CLI that supports the latest 2024-2026 techniques.

**Mission**: Democratize advanced LLM training methods by providing a unified interface that abstracts complexity while exposing full power.

---

## 3. Target Users

| Persona | Needs | Pain Points |
|---------|-------|-------------|
| **ML Engineer** | Fast iteration, multiple methods | Switching between Axolotl/Unsloth/TRL |
| **Researcher** | Latest methods, experiments | Hard to compare methods |
| **Developer** | Simple CLI, good defaults | Overwhelming config, unclear what to use |
| **Startup** | Quick fine-tuning, production-ready | No clear path from experiment to deploy |

---

## 4. Use Cases

### UC1: Fine-tune Qwen for Tool Calling
```
trainer train \
  --model Qwen/Qwen2.5-7B \
  --method qlora \
  --data tool_calls.jsonl \
  --output my-model
```

### UC2: Preference Tune with KTO
```
trainer train \
  --model meta-llama/Llama-3-8B \
  --method kto \
  --data feedback.jsonl \
  --output preference-model
```

### UC3: Train on Consumer GPU (24GB)
```
trainer train \
  --model Qwen/Qwen2.5-7B \
  --method qlora \
  --optimizer galore \
  --data dataset.jsonl \
  --output 7b-on-24gb
```

### UC4: Export to GGUF for Inference
```
trainer export \
  --input my-model \
  --format gguf_q4_k_m \
  --output model-q4.gguf
```

### UC5: Create Ollama Model
```
trainer export \
  --input my-model \
  --format ollama \
  --system "You are a coding assistant" \
  --output ./model
```

---

## 5. Functional Requirements

### FR1: Multi-Model Support
- **FR1.1**: Load any HuggingFace-compatible model (Qwen, Llama, Mistral, Phi, etc.)
- **FR1.2**: Support GGUF models for inference-only operations
- **FR1.3**: Auto-detect model architecture and apply optimal configurations

### FR2: Training Methods
| Method | Description | Status |
|--------|-------------|--------|
| **LoRA** | Low-Rank Adaptation | Required |
| **QLoRA** | Quantized LoRA (4-bit) | Required |
| **LoRA+** | Per-layer learning rates (ηB = λ × ηA) | Required |
| **VeRA** | Vector-based Random Adaptation | Required |
| **FTT** | Full Fine-Tuning | Required |
| **KTO** | Kahneman-Tversky Optimization | Required |
| **ORPO** | Odds Ratio Preference Optimization | Required |
| **SimPO** | Simple Preference Optimization | Required |
| **DPO** | Direct Preference Optimization | Required |

### FR3: Optimizers
| Optimizer | Description | Status |
|----------|-------------|--------|
| **AdamW** | Default PyTorch | Required |
| **Lion** | Sign-based, 2x faster | Required |
| **Sophia** | Second-order, 2x convergence | Required |
| **GaLore** | 65% less VRAM | Required |
| **Adafactor** | Sublinear memory | Required |

### FR4: Memory Optimization
- **FR4.1**: Flash Attention 2 integration
- **FR4.2**: Gradient checkpointing
- **FR4.3**: 4-bit NF4 quantization (bitsandbytes)
- **FR4.4**: FSDP (Fully Sharded Data Parallel)
- **FR4.5**: BF16/FP16 mixed precision

### FR5: Data Pipeline
- **FR5.1**: JSONL format support
- **FR5.2**: JSON format support
- **FR5.3**: CSV format support
- **FR5.4**: HuggingFace datasets integration
- **FR5.5**: ChatML / Alpaca / ShareGPT format support
- **FR5.6**: DPO format (prompt, chosen, rejected)
- **FR5.7**: KTO format (prompt, response, label)
- **FR5.8**: Tokenizer auto-configuration
- **FR5.9**: Chat template application

### FR6: Export Options
- **FR6.1**: LoRA adapter (safetensors)
- **FR6.2**: Merged model (HF format)
- **FR6.3**: GGUF quantization (Q2_K to Q8_0)
- **FR6.4**: Ollama modelfile export
- **FR6.5**: Weight interpolation (linear, SLERP, TARI)

### FR7: Configuration
- **FR7.1**: YAML config file support
- **FR7.2**: CLI argument overrides
- **FR7.3**: Python API for programmatic use
- **FR7.4**: Config inheritance/extension

### FR8: Monitoring & Logging
- **FR8.1**: Training progress with loss/throughput
- **FR8.2**: GPU memory monitoring
- **FR8.3**: Checkpoint saving with resume
- **FR8.4**: Validation metrics

---

## 6. Non-Functional Requirements

### Performance
- **NFR1**: Training speed within 10% of Unsloth
- **NFR2**: Memory usage competitive with Axolotl
- **NFR3**: Support models up to 70B parameters

### Extensibility
- **NFR4**: Add new optimizer via single decorator
- **NFR5**: Add new training method via plugin
- **NFR6**: Add new model via entry point

### Usability
- **NFR7**: Default config works out of box
- **NFR8**: Clear error messages with suggestions
- **NFR9**: Graceful degradation (fallbacks for unsupported features)

---

## 7. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI (Typer)                             │
│              train | eval | export | config                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Configuration Manager                       │
│         YAML → CLI Override → Python API                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Trainer Orchestrator                     │
│    ┌─────────────┬─────────────┬──────────────────────┐    │
│    │   Model     │   Dataset  │   Training          │    │
│    │   Factory   │   Pipeline  │   Loop              │    │
│    └─────────────┴─────────────┴──────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  HF Backend     │ │ llama.cpp      │ │ Optimizer       │
│  (training)    │ │ Backend        │ │ Registry        │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **CLI** | Entry points: train, eval, export, models, config |
| **Config Manager** | YAML loading, CLI overrides, validation |
| **Model Factory** | Load models, apply adapters, configure |
| **Dataset Pipeline** | Load, preprocess, tokenize, batch |
| **Trainer Loop** | Main training, checkpointing, callbacks |
| **Optimizer Registry** | Lion, Sophia, GaLore, AdamW |
| **HF Backend** | Full training, HF format export |
| **llama.cpp Backend** | GGUF export, inference |

---

## 8. CLI Interface

```bash
# Training
trainer train --config config.yaml
trainer train --model Qwen/Qwen2.5-7B --method qlora --data data.jsonl
trainer train --model meta-llama/Llama-3-8B-Instruct --method kto --data feedback.jsonl

# Evaluation
trainer eval --model ./output --data test.jsonl

# Export
trainer export --input ./model --format gguf_q4_k_m --output model.gguf

# Configuration
trainer config show
trainer config validate config.yaml

# Models
trainer models list
trainer models info Qwen/Qwen2.5-7B
```

---

## 9. Data Formats

### SFT Training (JSONL)
```json
{"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
```

### DPO Training (JSONL)
```json
{"prompt": "...", "chosen": "...", "rejected": "..."}
```

### KTO Training (JSONL)
```json
{"prompt": "...", "completion": "...", "label": "desirable"}
{"prompt": "...", "completion": "...", "label": "undesirable"}
```

---

## 10. Configuration Example

```yaml
# config.yaml
project: my-fine-tune
model:
  name: Qwen/Qwen2.5-7B-Instruct
  torch_dtype: bfloat16
  attn_implementation: flash_attention_2

method:
  name: qlora
  rank: 32
  alpha: 64
  loraplus_lr_ratio: 16
  target_modules: [q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj]
  lora_dropout: 0.05

optimizer:
  name: lion
  lr: 3e-5
  weight_decay: 0.01

dataset:
  path: ./data/training.jsonl
  format: jsonl
  max_length: 4096

training:
  epochs: 3
  batch_size: 4
  gradient_accumulation: 4
  logging_steps: 10
  save_steps: 500

export:
  formats:
    - lora_adapter
    - gguf_q4_k_m
```

---

## 11. Success Metrics

| Metric | Target |
|--------|--------|
| CLI help response time | < 1s |
| Model loading time | < 30s |
| Training speed vs Unsloth | Within 10% |
| Memory usage vs Axolotl | Within 10% |
| GGUF export accuracy | > 99% |
| Config validation | 100% coverage |

---

## 12. Out of Scope (v1.0)

- Web UI / GUI
- Cloud training (AWS, GCP)
- Multi-GPU training orchestration
- RLHF (PPO) training
- RL (Reinforcement Learning)
- Vision models
- Audio models

---

## 13. Dependencies

| Package | Purpose |
|---------|---------|
| `torch` | Core ML framework |
| `transformers` | Model loading |
| `peft` | LoRA/LoRA+ implementation |
| `trl` | DPO/KTO/ORPO training |
| `unsloth` | Fast training (optional) |
| `bitsandbytes` | 4-bit quantization |
| `llama.cpp` | GGUF export |
| `typer` | CLI |
| `pydantic` | Config validation |

---

## 14. Roadmap

### Phase 1 (MVP)
- [x] Research complete
- [ ] PRD → Architecture → Implementation
- [ ] Core training (LoRA, QLoRA)
- [ ] Basic optimizers (AdamW, Lion)
- [ ] JSONL data format

### Phase 2
- [ ] Preference learning (KTO, ORPO, SimPO, DPO)
- [ ] Advanced optimizers (Sophia, GaLore)
- [ ] GGUF export

### Phase 3
- [ ] Ollama export
- [ ] Config inheritance
- [ ] Plugin system

---

## 15. Appendix: Research Summary

### Training Methods (2024-2026)
- **LoRA+**: Per-layer LR (ηB = λ × ηA), λ = 8-16
- **VeRA**: Shared random matrices, 10x fewer params
- **KTO**: Binary signal, no preference pairs needed
- **ORPO**: Single-step SFT + preference, reference-free
- **SimPO**: Best AlpacaEval scores, reference-free

### Optimizers
- **Lion**: Sign-based, 2x faster, 50% less memory
- **Sophia**: Hessian-based, 2x convergence
- **GaLore**: 65% less VRAM, 7B on 24GB GPU

### Memory Techniques
- Flash Attention 2: 2x speed
- Gradient checkpointing: 30-50% memory savings
- 4-bit NF4: 75% memory reduction
- QLoRA: 70B on 24GB

### Export Formats
- GGUF: Q4_K_M (4.1GB/7B) recommended default
- Ollama: Custom modelfile
- Merged: HF safetensors

---

*Document Version: 1.0*
*Created: 2026-04-27*
*Status: Ready for Architecture Phase*
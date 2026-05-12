---
project_name: N-Xyme Trainer
version: "1.0"
created: "2026-04-27"
document_type: Epics and Stories
status: draft
epics:
  - id: epic-001
    name: Core Infrastructure
    description: Build the foundational infrastructure - CLI, config, plugin system
    priority: P0
    stories:
      - id: story-001
        title: CLI Entry Points
        description: Create CLI with train/eval/export/config commands using Typer
        acceptance: "train --help, eval --help, export --help work"
        estimate: 3
        status: pending
      - id: story-002
        title: Configuration System
        description: YAML config loading, CLI overrides, Pydantic validation
        acceptance: "Config loads from YAML, CLI args override, validation errors clear"
        estimate: 5
        status: pending
      - id: story-003
        title: Plugin Registry System
        description: Protocol-based registry for optimizers, methods, models
        acceptance: "Add optimizer via @register decorator works"
        estimate: 5
        status: pending
      - id: story-004
        title: Logging & Monitoring
        description: Training progress, GPU memory, checkpoint logging
        acceptance: "Loss, throughput, memory logged during training"
        estimate: 2
        status: pending

  - id: epic-002
    name: Model Loading
    description: Model loading from HF, GGUF, local paths with proper configuration
    priority: P0
    stories:
      - id: story-005
        title: HuggingFace Model Loader
        description: Load any HF model with proper dtype and attention config
        acceptance: "Loads Qwen, Llama, Mistral from HF"
        estimate: 5
        status: pending
      - id: story-006
        title: GGUF Model Loader
        description: Load GGUF models for inference-only operations
        acceptance: "Loads GGUF for export inference test"
        estimate: 3
        status: pending
      - id: story-007
        title: Model Architecture Detection
        description: Auto-detect model type and apply optimal configurations
        acceptance: "Detects Qwen/Llama/Mistral automatically"
        estimate: 3
        status: pending

  - id: epic-003
    name: Data Pipeline
    description: Data loading, preprocessing, tokenization for SFT and preference training
    priority: P0
    stories:
      - id: story-008
        title: JSONL Data Loader
        description: Load and parse JSONL training data
        acceptance: "Loads standard JSONL format"
        estimate: 3
        status: pending
      - id: story-009
        title: ChatML/ShareGPT Format Support
        description: Support ChatML and ShareGPT conversation formats
        acceptance: "Parses ChatML and ShareGPT correctly"
        estimate: 3
        status: pending
      - id: story-010
        title: Tokenizer Configuration
        description: Auto-apply chat templates, configure max_length
        estimate: 3
        status: pending
      - id: story-011
        title: DPO Dataset Format
        description: Support (prompt, chosen, rejected) format for DPO
        estimate: 3
        status: pending
      - id: story-012
        title: KTO Dataset Format
        description: Support (prompt, response, label) format for KTO
        estimate: 3
        status: pending

  - id: epic-004
    name: Training Methods
    description: Implement all training methods - LoRA, QLoRA, LoRA+, FTT, DPO, KTO, ORPO, SimPO
    priority: P0
    stories:
      - id: story-013
        title: LoRA Implementation
        description: Standard LoRA with PEFT integration
        acceptance: "LoRA training runs and produces adapter"
        estimate: 5
        status: pending
      - id: story-014
        title: QLoRA Implementation
        description: 4-bit quantized LoRA with bitsandbytes
        acceptance: "QLoRA runs on 24GB GPU with 7B model"
        estimate: 5
        status: pending
      - id: story-015
        title: LoRA+ Implementation
        description: Per-layer learning rates (ηB = λ × ηA)
        acceptance: "LoRA+ with λ=16 works correctly"
        estimate: 3
        status: pending
      - id: story-016
        title: Full Fine-Tuning
        description: Full parameter fine-tuning option
        acceptance: "FTT runs with gradient checkpointing"
        estimate: 4
        status: pending
      - id: story-017
        title: DPO Trainer
        description: Direct Preference Optimization via TRL
        acceptance: "DPO training completes on preference data"
        estimate: 5
        status: pending
      - id: story-018
        title: KTO Trainer
        description: Kahneman-Tversky Optimization via TRL
        acceptance: "KTO training with binary labels works"
        estimate: 4
        status: pending
      - id: story-019
        title: ORPO Trainer
        description: Odds Ratio Preference Optimization
        acceptance: "ORPO training runs reference-free"
        estimate: 4
        status: pending
      - id: story-020
        title: SimPO Trainer
        description: Simple Preference Optimization
        acceptance: "SimPO training with margin works"
        estimate: 4
        status: pending

  - id: epic-005
    name: Optimizers
    description: Implement all optimizers - AdamW, Lion, Sophia, GaLore, Adafactor
    priority: P0
    stories:
      - id: story-021
        title: AdamW Optimizer
        description: Standard PyTorch AdamW integration
        acceptance: "AdamW training works correctly"
        estimate: 2
        status: pending
      - id: story-022
        title: Lion Optimizer
        description: Sign-based optimizer (2x faster)
        acceptance: "Lion with lr=3e-5 works"
        estimate: 3
        status: pending
      - id: story-023
        title: Sophia Optimizer
        description: Second-order optimizer with Hessian
        acceptance: "Sophia converges 2x faster"
        estimate: 4
        status: pending
      - id: story-024
        title: GaLore Optimizer
        description: Gradient Low-Rank Projection (65% less VRAM)
        acceptance: "GaLore trains 7B on 24GB GPU"
        estimate: 5
        status: pending
      - id: story-025
        title: Adafactor Optimizer
        description: Sublinear memory optimizer
        acceptance: "Adafactor uses 40% less memory"
        estimate: 2
        status: pending

  - id: epic-006
    name: Memory Optimization
    description: Flash Attention, gradient checkpointing, mixed precision
    priority: P1
    stories:
      - id: story-026
        title: Flash Attention 2 Integration
        description: Enable flash_attention_2 for models that support it
        acceptance: "FA2 provides 2x speedup"
        estimate: 3
        status: pending
      - id: story-027
        title: Gradient Checkpointing
        description: Implement gradient checkpointing for memory savings
        acceptance: "30-50% memory reduction"
        estimate: 3
        status: pending
      - id: story-028
        title: BF16/FP16 Mixed Precision
        description: Configure and use mixed precision training
        acceptance: "BF16 training works correctly"
        estimate: 2
        status: pending
      - id: story-029
        title: FSDP Support
        description: Fully Sharded Data Parallel for multi-GPU
        acceptance: "FSDP distributes model across GPUs"
        estimate: 5
        status: pending

  - id: epic-007
    name: Export & Deployment
    description: Export to LoRA adapter, merged model, GGUF, Ollama
    priority: P1
    stories:
      - id: story-030
        title: LoRA Adapter Export
        description: Export trained LoRA adapter as safetensors
        acceptance: "Adapter exports and loads correctly"
        estimate: 3
        status: pending
      - id: story-031
        title: Merged Model Export
        description: Merge LoRA weights into base model
        acceptance: "Merged model runs standalone"
        estimate: 4
        status: pending
      - id: story-032
        title: GGUF Export
        description: Export to GGUF with quantization options
        acceptance: "Exports Q2_K through Q8_0 correctly"
        estimate: 5
        status: pending
      - id: story-033
        title: Ollama Export
        description: Create Ollama modelfile with system prompt
        acceptance: "Ollama loads and runs model"
        estimate: 3
        status: pending
      - id: story-034
        title: Weight Interpolation
        description: Linear, SLERP, TARI interpolation methods
        acceptance: "Interpolation blends adapters correctly"
        estimate: 3
        status: pending

  - id: epic-008
    name: Evaluation & Validation
    description: Model evaluation, validation metrics, testing
    priority: P2
    stories:
      - id: story-035
        title: Basic Evaluation
        description: Run inference on test dataset
        acceptance: "Produces predictions on test data"
        estimate: 3
        status: pending
      - id: story-036
        title: Metrics Calculation
        description: Calculate loss, perplexity, accuracy
        acceptance: "Reports metrics after evaluation"
        estimate: 3
        status: pending

---

## Summary

| Epic | Stories | Total Points |
|------|---------|--------------|
| Core Infrastructure | 4 | 15 |
| Model Loading | 3 | 11 |
| Data Pipeline | 5 | 15 |
| Training Methods | 8 | 34 |
| Optimizers | 5 | 16 |
| Memory Optimization | 4 | 16 |
| Export & Deployment | 5 | 18 |
| Evaluation | 2 | 6 |

**Total: 8 Epics, 36 Stories, 135 Points**

## Priority Order

1. **P0** (Must Have): Core Infrastructure, Model Loading, Data Pipeline, Training Methods, Optimizers
2. **P1** (Should Have): Memory Optimization, Export & Deployment
3. **P2** (Nice to Have): Evaluation

---

*Document Version: 1.0*
*Created: 2026-04-27*
*Status: Ready for Sprint Planning*
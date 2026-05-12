---
project_name: N-Xyme Trainer
version: "1.0"
created: "2026-04-27"
document_type: Sprint Status
status: draft
---

# Sprint Planning: N-Xyme Trainer

## Overview

| Metric | Value |
|--------|-------|
| Total Stories | 36 |
| Total Points | 135 |
| Epics | 8 |
| Estimated Sprints | 6-8 |

## Sprint Breakdown

### Sprint 1: Core Infrastructure (MVP Start)
**Goal**: Get CLI and config working as foundation

| Story | Points | Status |
|-------|--------|--------|
| CLI Entry Points (story-001) | 3 | TODO |
| Configuration System (story-002) | 5 | TODO |
| Plugin Registry System (story-003) | 5 | TODO |
| Logging & Monitoring (story-004) | 2 | TODO |

**Sprint Total**: 15 points

**Deliverable**: CLI with `train --help` working, config loads from YAML

---

### Sprint 2: Model Loading & Data Pipeline
**Goal**: Can load models and prepare data for training

| Story | Points | Status |
|-------|--------|--------|
| HuggingFace Model Loader (story-005) | 5 | TODO |
| GGUF Model Loader (story-006) | 3 | TODO |
| Model Architecture Detection (story-007) | 3 | TODO |
| JSONL Data Loader (story-008) | 3 | TODO |
| ChatML/ShareGPT Format (story-009) | 3 | TODO |
| Tokenizer Configuration (story-010) | 3 | TODO |

**Sprint Total**: 20 points

**Deliverable**: Can load Qwen/Llama from HF, parse JSONL/ChatML data

---

### Sprint 3: Basic Training (LoRA + AdamW)
**Goal**: Run basic LoRA training successfully

| Story | Points | Status |
|-------|--------|--------|
| LoRA Implementation (story-013) | 5 | TODO |
| DPO Dataset Format (story-011) | 3 | TODO |
| KTO Dataset Format (story-012) | 3 | TODO |
| AdamW Optimizer (story-021) | 2 | TODO |
| Gradient Checkpointing (story-027) | 3 | TODO |
| BF16 Mixed Precision (story-028) | 2 | TODO |

**Sprint Total**: 18 points

**Deliverable**: Can train LoRA with AdamW, save adapter

---

### Sprint 4: Advanced Training Methods
**Goal**: Implement all training methods (QLoRA, LoRA+, DPO, KTO, ORPO, SimPO)

| Story | Points | Status |
|-------|--------|--------|
| QLoRA Implementation (story-014) | 5 | TODO |
| LoRA+ Implementation (story-015) | 3 | TODO |
| Full Fine-Tuning (story-016) | 4 | TODO |
| DPO Trainer (story-017) | 5 | TODO |
| KTO Trainer (story-018) | 4 | TODO |
| ORPO Trainer (story-019) | 4 | TODO |
| SimPO Trainer (story-020) | 4 | TODO |

**Sprint Total**: 29 points

**Deliverable**: All training methods work

---

### Sprint 5: Advanced Optimizers & Memory
**Goal**: Implement Lion, Sophia, GaLore, memory optimizations

| Story | Points | Status |
|-------|--------|--------|
| Lion Optimizer (story-022) | 3 | TODO |
| Sophia Optimizer (story-023) | 4 | TODO |
| GaLore Optimizer (story-024) | 5 | TODO |
| Adafactor Optimizer (story-025) | 2 | TODO |
| Flash Attention 2 (story-026) | 3 | TODO |
| FSDP Support (story-029) | 5 | TODO |

**Sprint Total**: 22 points

**Deliverable**: All optimizers work, 7B trains on 24GB GPU

---

### Sprint 6: Export & Deployment
**Goal**: All export formats working

| Story | Points | Status |
|-------|--------|--------|
| LoRA Adapter Export (story-030) | 3 | TODO |
| Merged Model Export (story-031) | 4 | TODO |
| GGUF Export (story-032) | 5 | TODO |
| Ollama Export (story-033) | 3 | TODO |
| Weight Interpolation (story-034) | 3 | TODO |
| Basic Evaluation (story-035) | 3 | TODO |
| Metrics Calculation (story-036) | 3 | TODO |

**Sprint Total**: 24 points

**Deliverable**: Can export to GGUF, Ollama, run evaluation

---

## Story to Sprint Mapping

| Sprint | Epics | Stories | Points |
|--------|-------|---------|--------|
| 1 | Infrastructure | 4 | 15 |
| 2 | Model Loading, Data Pipeline | 9 | 20 |
| 3 | Training Methods (Basic) | 6 | 18 |
| 4 | Training Methods (Advanced) | 7 | 29 |
| 5 | Optimizers, Memory | 6 | 22 |
| 6 | Export, Evaluation | 7 | 24 |

---

## Dependencies

```
Sprint 1 (Foundation)
    │
    ▼
Sprint 2 (Data + Models)
    │
    ▼
Sprint 3 (Basic Training) ──────► Sprint 5 (Advanced Optimizers)
    │                                  │
    ▼                                  ▼
Sprint 4 (Advanced Methods) ◄──────┘
    │
    ▼
Sprint 6 (Export)
```

---

## Parallel Paths

- **Sprint 3** can start after Sprint 2 completes
- **Sprint 5** can start after Sprint 3 (basic training works)
- **Sprint 4** depends on Sprint 3 (training loop ready)
- **Sprint 6** depends on Sprint 4 (training methods ready)

---

## Quick Start Command

```bash
# After Sprint 1
trainer --help
trainer train --config config.yaml --model Qwen/Qwen2.5-7B

# After Sprint 2  
trainer train --data data.jsonl --method lora

# After Sprint 3
trainer train --method qlora --optimizer lion

# After Sprint 6
trainer export --format gguf_q4_k_m
```

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Complex optimization (Sophia, GaLore) | Start with proven AdamW/Lion |
| GGUF export complexity | Use llama.cpp tools |
| Memory constraints | Prioritize QLoRA + GaLore |

---

*Document Version: 1.0*
*Created: 2026-04-27*
*Status: Ready for Implementation*
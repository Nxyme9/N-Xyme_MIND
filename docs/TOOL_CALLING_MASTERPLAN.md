# N-Xyme Masterplan: Perfect Small Model for Tool Calling

**Version**: 1.0  
**Date**: 2026-04-13  
**Goal**: Train optimal small model (0.5B-3B) for extremely accurate tool/task execution in N-Xyme system

---

## Executive Summary

| Aspect | Recommendation |
|--------|---------------|
| **Target Model** | Qwen2.5-3B-Instruct or Phi-4-Mini (3.8B) |
| **Training Data** | 1,000-3,000 high-quality examples (synthetics from GPT-4o) |
| **Method** | SFT + LoRA (QLoRA for VRAM efficiency) |
| **Expected Accuracy** | 85-95% tool selection + parameter correctness |
| **VRAM Requirement** | 6-8GB (QLoRA) on RTX 3080 Ti |

**Key Research Findings**:
- 350M-3B models can achieve 77-98% tool call accuracy with proper fine-tuning
- Quality > Quantity: 500 curated examples outperform 10K raw
- SFT + GRPO hybrid is leading approach for multi-turn tool calling
- Optimal LR: 1e-5 to 3e-5 for small models

---

## 1. Current System Analysis

### N-Xyme Tools (40+ MCP Tools)

| Category | Tools |
|----------|-------|
| **Memory** | memory_search, memory_write, athena_smart_search, get_active_context |
| **Files** | read_file, write_file, list_directory |
| **Git** | git_status, git_log, git_diff |
| **Web** | browser_navigate, fetch_url, context7_query_docs |
| **AI/Reasoning** | sequential_thinking, route_task |
| **GitHub** | github_list_issues |
| **System** | get_health |

### Existing Trained Models

| Model | Path | Checkpoints | Status |
|-------|------|-------------|--------|
| rosetta-lora | `/models/rosetta-lora/` | 50, 63 | Legacy |
| rosetta-lora-v2 | `/models/rosetta-lora-v2/` | 450, 460 | Current best |
| rosetta-lora-ecosystem | `/models/rosetta-lora-ecosystem/` | 950, 1000 | Extended |

### Current Training Data

| Dataset | Examples | Tools Covered |
|---------|----------|---------------|
| rosetta_combined.jsonl | 441 | 17 tools |
| rosetta_full_training.jsonl | 300 | ~20 tools |
| rosetta_ecosystem_full.jsonl | 141 | ~25 tools |

---

## 2. Target Architecture

### Model Selection Rationale

```
┌─────────────────────────────────────────────────────────────────┐
│                    MODEL SELECTION MATRIX                       │
├─────────────┬──────────────┬─────────────┬─────────────────────┤
│ Model       │ Size         │ VRAM        │ Tool Call Accuracy  │
├─────────────┼──────────────┼─────────────┼─────────────────────┤
│ Qwen2.5-0.5B│ 0.5B params  │ 4-5GB       │ 70-80% (baseline)   │
│ Qwen2.5-1.5B│ 1.5B params  │ 6GB         │ 80-90% (recommended)│
│ Qwen2.5-3B  │ 3B params    │ 8GB         │ 85-95% (optimal)    │
│ Phi-4-Mini  │ 3.8B params  │ 8GB         │ 90-97% (cutting edge│
└─────────────┴──────────────┴─────────────┴─────────────────────┘

RECOMMENDATION: Start with Qwen2.5-1.5B (balance of speed/accuracy)
UPGRADE PATH: Qwen2.5-3B → Phi-4-Mini as data grows
```

### Training Pipeline

```
┌──────────────────────────────────────────────────────────────────────┐
│                        TRAINING PIPELINE v3.0                        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ Data Sources │───▶│   Merging    │───▶│  Quality Filter     │  │
│  │ - rosetta_   │    │  + Dedupe    │    │  (execution check)  │  │
│  │   combined   │    │              │    │                     │  │
│  │ - synthetics │    │              │    │                     │  │
│  │ - edge cases │    │              │    │                     │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                    │                │
│                                                    ▼                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ Data Aug     │───▶│  Tokenize    │───▶│  SFT Trainer         │  │
│  │ (masking,    │    │  (chat       │    │  (Unsloth/TRL)       │  │
│  │  paraphrasing│    │   template)  │    │                     │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                    │                │
│                                                    ▼                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ Evaluation   │◀───│  LoRA Adapter│◀───│  Model Merger        │  │
│  │ (BFCL-v4,    │    │  (adapter.bin)│    │  (if needed)        │  │
│  │  custom)     │    │              │    │                     │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                    │                │
│                                                    ▼                │
│                                    ┌──────────────────────────────┐ │
│                                    │     GGUF Export              │ │
│                                    │     (llama-server compatible)│ │
│                                    └──────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Training Data Strategy

### Data Requirements by Complexity

| Scenario | Examples | Coverage |
|----------|----------|----------|
| Single-tool calls | 500 | 40 tools |
| Sequential chains (2-3 tools) | 300 | common sequences |
| Parallel tool execution | 200 | read+write, search+read |
| Error recovery / retry | 150 | timeout, invalid args |
| Edge cases ("no tool needed") | 150 | boundary cases |
| **TOTAL** | **1,300** | |

### Data Augmentation Techniques

1. **Function Name Masking**: Randomize tool names → forces learning from descriptions
2. **Irrelevance Synthesis**: Generate "no tool needed" examples (15% of data)
3. **Parameter Variation**: Multiple valid values for same parameter
4. **Paraphrasing**: Rephrase same intent 3-5 ways
5. **Error Injection**: Malformed calls → train error recovery

### Data Quality Metrics

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA QUALITY CHECKLIST                       │
├─────────────────────────────────────────────────────────────────┤
│ ✅ Tool name matches one of 40+ defined tools                  │
│ ✅ Parameters match tool schema (types, required/optional)     │
│ ✅ Output format: [TOOL_CALL]{tool => "...", args => {...}}[/TOOL_CALL]│
│ ✅ No hallucinated tools (only trained tools allowed)         │
│ ✅ Parameter values are valid (paths exist, URLs valid)       │
│ ✅ Multi-turn coherence (sequential tools make sense)         │
└─────────────────────────────────────────────────────────────────┘
```

### Synthetic Data Generation Pipeline

```python
# Generate high-quality synthetic data using frontier LLMs
SYNTHETIC_PROMPT = """
Generate training data for N-Xyme tool calling system.

Available tools:
{tool_schema}

Generate diverse examples covering:
- Simple tool calls
- Multi-tool chains  
- Edge cases
- Error scenarios

Output format: JSON with input, output, tool, args fields
"""
```

---

## 4. Hyperparameters (Research-Backed)

### SFT Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Learning Rate** | 2e-5 | Research: 1e-5 to 3e-5 optimal for tool-calling |
| **Epochs** | 2-3 | More epochs = overfitting risk |
| **Batch Size** | 4-8 | 4 for 0.5B, 8 for 1.5B, 4 for 3B (QLoRA) |
| **Gradient Accumulation** | 4-8 | Effective batch = 16-64 |
| **Max Seq Length** | 2048 | Tool definitions + context |
| **Warmup Ratio** | 0.1 | Gradual LR ramp |
| **LR Scheduler** | cosine | Smooth decay |
| **Optimizer** | adamw_8bit | 50% less memory |

### LoRA Configuration (QLoRA)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **LoRA Rank (r)** | 32 | Higher for more capacity |
| **LoRA Alpha** | 32-64 | Equal to or 2x rank |
| **LoRA Dropout** | 0.05 | Light dropout |
| **Target Modules** | q,k,v,o,gate,up,down | All linear layers |
| **Quantization** | nf4 (4-bit) | QLoRA default |
| **Bits** | 4 | 70% less VRAM |

### Full Configuration (for config.py)

```python
# Research-backed config for optimal tool calling
OPTIMAL_CONFIG = {
    "model_name": "Qwen/Qwen2.5-1.5B-Instruct",  # RECOMMENDED
    "max_seq_length": 2048,
    "lora_r": 32,
    "lora_alpha": 64,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", 
                       "gate_proj", "up_proj", "down_proj"],
    "batch_size": 4,
    "gradient_accumulation": 8,
    "learning_rate": 2e-5,
    "epochs": 3,
    "quantization": "nf4",
    "bits": 4,
    "vram_requirement": "~6GB",
}
```

---

## 5. Evaluation Framework

### Metrics Definition

```
┌─────────────────────────────────────────────────────────────────────┐
│                    EVALUATION METRICS                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ 1. Tool Selection Accuracy (TSA)                                  │
│    Formula: correct_tool / total_calls                              │
│    Target: >90%                                                    │
│                                                                     │
│ 2. Parameter Correctness (PC)                                      │
│    Formula: correct_params / total_params                           │
│    Target: >85%                                                    │
│                                                                     │
│ 3. Format Validity (FV)                                            │
│    Formula: valid_format / total_calls                             │
│    Target: >95%                                                    │
│                                                                     │
│ 4. Multi-turn Coherence (MTC)                                      │
│    Formula: coherent_chains / total_chains                         │
│    Target: >80%                                                    │
│                                                                     │
│ 5. Error Recovery Rate (ERR)                                      │
│    Formula: recovered / errors                                     │
│    Target: >70%                                                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Benchmark Suite

| Benchmark | Tests | Purpose |
|-----------|-------|---------|
| **BFCL-v4 subset** | 30 | Industry standard |
| **N-Xyme Custom** | 50 | System-specific tools |
| **Edge Cases** | 20 | Boundary conditions |
| **Multi-turn** | 25 | Chain accuracy |

### Test Cases Example

```python
TEST_CASES = [
    # Single tool
    ("search memory for auth", "memory_search", {"query": "auth"}),
    ("read config.py", "read_file", {"path": "config.py"}),
    
    # Multi-tool chain
    ("find API file and read it", "glob", {"pattern": "**/api*.py"}, 
                                       "read_file", {"path": "<filename>"}),
    
    # Edge case - no tool needed
    ("hello how are you", None, {}),
    
    # Error recovery
    ("read /nonexistent/file.txt", "read_file", {"path": "/nonexistent/file.txt"}),
]
```

---

## 6. Implementation Timeline

### Phase 1: Foundation (Week 1-2)

| Task | Duration | Status |
|------|----------|--------|
| Audit existing data quality | 2 days | PENDING |
| Generate 500 synthetic examples | 3 days | PENDING |
| Implement data augmentation pipeline | 2 days | PENDING |
| Set up evaluation harness | 2 days | PENDING |
| **Milestone**: 1K quality-assured examples + eval | 9 days | |

### Phase 2: Training (Week 3-4)

| Task | Duration | Status |
|------|----------|--------|
| Train Qwen2.5-1.5B LoRA | 2 days | PENDING |
| Evaluate on BFCL-v4 | 1 day | PENDING |
| Analyze failure cases | 1 day | PENDING |
| Iterate with augmented data | 3 days | PENDING |
| **Milestone**: Working model >85% accuracy | 7 days | |

### Phase 3: Optimization (Week 5-6)

| Task | Duration | Status |
|------|----------|--------|
| GRPO/DAPO refinement (if needed) | 3 days | PENDING |
| GGUF export + llama-server integration | 1 day | PENDING |
| End-to-end system test | 2 days | PENDING |
| Documentation | 1 day | PENDING |
| **Milestone**: Production-ready model | 7 days | |

### Total Timeline: 6 weeks

```
Week 1-2: Foundation (Data + Eval)
Week 3-4: Training + Iteration  
Week 5-6: Optimization + Deployment
```

---

## 7. Key Decisions Required

### Decision 1: Model Size
- **Option A**: Qwen2.5-0.5B (fast, 4GB, 70-80%)
- **Option B**: Qwen2.5-1.5B (recommended, 6GB, 80-90%)
- **Option C**: Qwen2.5-3B (best, 8GB, 85-95%)

### Decision 2: Training Method
- **Option A**: SFT only (fast, simple, 80-85%)
- **Option B**: SFT + GRPO (better, 85-90%, 2x time)

### Decision 3: Data Generation
- **Option A**: Use existing 441 examples + augment
- **Option B**: Generate 1000+ new synthetic examples
- **Option C**: Both combined

### Decision 4: Evaluation Standard
- **Option A**: Quick internal test (50 cases)
- **Option B**: Full BFCL-v4 benchmark (industry standard)

---

## 8. Immediate Action Items

### Day 1-2: Data Audit
```bash
# 1. Analyze existing datasets
python3 analyze_tool_distribution.py

# 2. Identify gaps in tool coverage
python3 check_tool_coverage.py --tools 40

# 3. Generate synthetic data for gaps
python3 generate_synthetic.py --count 500 --gaps-only
```

### Day 3-5: Training Preparation
```bash
# 1. Update config with research hyperparameters
rosetta-train config --lr 2e-5 --lora-r 32 --target-modules all

# 2. Prepare evaluation dataset
python3 create_eval_set.py --benchmark bfcl --count 50

# 3. Start first training run
rosetta-train train --model qwen2.5-1.5b --data merged.jsonl
```

### Day 6-7: Evaluation + Iteration
```bash
# 1. Run evaluation
python3 evaluate.py --model outputs/rosetta-v3

# 2. Analyze failures
python3 analyze_failures.py --results results.json

# 3. Iterate or proceed to export
```

---

## 9. Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Overfitting | Medium | High | Early stopping, eval on held-out set |
| Catastrophic forgetting | Low | High | Keep base model, LoRA only |
| VRAM overflow | Low | High | QLoRA, reduce batch size |
| Poor generalization | Medium | High | Diverse training data |
| Tool schema drift | Low | Medium | Regular data refresh |

---

## 10. Success Metrics

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SUCCESS CRITERIA                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ ✅ Tool Selection Accuracy > 90%                                   │
│ ✅ Parameter Correctness > 85%                                      │
│ ✅ Format Validity > 95%                                            │
│ ✅ Multi-turn Coherence > 80%                                       │
│ ✅ Training time < 2 hours per epoch                                │
│ ✅ VRAM usage < 8GB (QLoRA)                                         │
│ ✅ GGUF export < 1GB                                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Appendix A: Tool Schema

```python
N_XYME_TOOLS = {
    # Memory & Context
    "memory_search": {"query": "str", "limit": "int"},
    "memory_write": {"content": "str", "kind": "str"},
    "athena_smart_search": {"query": "str"},
    "get_active_context": {},
    "get_product_context": {},
    "get_user_context": {},
    "get_constraints": {},
    
    # Filesystem
    "read_file": {"path": "str"},
    "write_file": {"path": "str", "content": "str"},
    "list_directory": {"path": "str"},
    
    # Git
    "git_status": {"repo_path": "str"},
    "git_log": {"repo_path": "str", "max_count": "int"},
    "git_diff": {"repo_path": "str", "target": "str"},
    
    # Web
    "browser_navigate": {"url": "str"},
    "fetch_url": {"url": "str", "format": "str"},
    "context7_query_docs": {"library_id": "str", "query": "str"},
    
    # AI/Reasoning
    "sequential_thinking": {"thought": "str", "nextThoughtNeeded": "bool", 
                            "thoughtNumber": "int", "totalThoughts": "int"},
    "route_task": {"task_description": "str"},
    
    # GitHub
    "github_list_issues": {"owner": "str", "repo": "str"},
    "github_search_code": {"q": "str"},
    
    # System
    "get_health": {"level": "str"},
}
```

---

## Appendix B: Research Sources

- **RC-GRPO Paper** (arXiv:2602.03025): SFT + GRPO for tool calling
- **ToolBench** (arXiv:2306.14401): 16K API benchmark
- **BFCL-v4**: Berkeley Function Calling Leaderboard
- **Microsoft Fine-tuning Guide**: techcommunity.microsoft.com (Jan 2025)
- **APIGen**: 3-stage verification pipeline
- **ToolACE**: Self-evolution synthesis
- **FunctionGemma**: 270M model achieving 90-97% tool accuracy
# N-Xyme Brain Architecture Masterplan

## Executive Summary

Transform N-Xyme_MIND into a proper "brain" with specialized small models (0.5B-3B) trained on ALL current MCP tools. This plan addresses the critical gap: the existing LoRA adapter was trained on only 10 tools, but the system now has **40+ MCP tools** across 7 categories.

**Target Architecture**: Routing pyramid with triage (0.5B) → specialized experts (1-3B)  
**VRAM Constraint**: RTX 3080 Ti (12.5GB)  
**Goal**: 85-95% tool selection + parameter correctness

---

## Phase 1: Analysis & Discovery (COMPLETED)

### 1.1 Frankenstein Engine Analysis

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| Direct GGUF Client | `engine/__init__.py` | 388 | ✅ LoRA support added |
| Configuration | `config.py` | 276 | ✅ Pydantic-validated |
| Router | `router/__init__.py` | 416 | ⚠️ Keyword-only, needs LLM upgrade |
| Compatibility Layer | `compatibility.py` | 548 | ✅ Rosetta Stone + MCP execution |

### 1.2 Training Pipeline Analysis

| Script | Purpose | Status |
|--------|---------|--------|
| `scripts/train_rosetta_stone.py` | Main training entry | ✅ Working |
| `scripts/unsloth_train.py` | Unsloth-based QLoRA | ✅ 2-5x faster |
| `datasets/rosetta_merged_training.jsonl` | Training data | ⚠️ Only 10 tools |

**Critical Finding**: LoRA adapter (`rosetta-lora.gguf`, 17MB) trained on OLD tools only - NEEDS RETRAINING with ALL current MCP tools.

### 1.3 MCP Tool Catalog (40+ Tools)

| Category | Tools | Package |
|----------|-------|---------|
| **Memory** | search_memories, create_memory, recall_session, get_memory_stats, memory_write, memory_rank | memory_core |
| **Learning** | route_task, score_complexity, record_outcome, get_learning_stats, get_recommendations | learning_engine |
| **Intelligence** | get_routing_history, available_agents, intelligence_route | intelligence |
| **Filesystem** | read_file, write_file, edit_file, list_directory, glob, grep, ast_grep_search | filesystem |
| **Git** | git_status, git_log, git_diff, git_commit, git_blame | git |
| **GitHub** | list_issues, create_issue, search_code, search_repositories, get_issue | github |
| **Context** | get_active_context, get_user_context, get_product_context, get_constraints | nx_context |
| **Mind** | get_mind_state, update_mind_state, get_session_history, mind_log_task_completion | nx-mind |
| **Documentation** | context7_query_docs, context7_resolve-library-id | context7 |
| **Reasoning** | sequential_thinking | sequential-thinking |
| **Quality** | run_typecheck, run_lint, run_format, run_tests, run_secrets_scan | quality-gates |
| **Triggers** | register_trigger, check_trigger, list_triggers, clear_triggers | trigger-guardian |
| **Orchestration** | orchestrate, detect_state, list_workflows | orchestration |

---

## Phase 2: Architecture Design (RECOMMENDED)

### 2.1 Multi-Model Brain Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER REQUEST                                 │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  MODEL 0: TRIAGE (Qwen2.5-0.5B) - 19 layers, ~500MB                │
│  Purpose: Fast classification → routing to specialized model       │
│  Input: Natural language request                                     │
│  Output: {category: str, complexity: "simple|medium|complex"}      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
            ┌──────────┐   ┌──────────┐   ┌──────────┐
            │ TOOL     │   │ PARAM    │   │ REASONER │
            │ SELECTOR │   │ EXTRACTOR│   │ (7B)     │
            │ (0.5B)   │   │ (0.5B)   │   │          │
            └──────────┘   └──────────┘   └──────────┘
                    │             │             │
                    ▼             ▼             ▼
            ┌──────────┐   ┌──────────┐   ┌──────────┐
            │ 40+ MCP  │   │ arguments │   │ FINAL    │
            │ tools    │   │ dict      │   │ RESPONSE │
            └──────────┘   └──────────┘   └──────────┘
```

### 2.2 Specialized Model Functions

| Model | Size | VRAM | Purpose | LoRA |
|-------|------|------|---------|------|
| Triage | 0.5B | ~1GB | Classify request category & complexity | triage-lora.gguf |
| Tool Selector | 0.5B | ~1GB | Choose correct MCP tool | tool-select-lora.gguf |
| Param Extractor | 0.5B | ~1GB | Extract arguments from request | param-extract-lora.gguf |
| Reasoner | 7B | ~5GB | Complex reasoning (fallback) | - |

**Total VRAM**: ~8GB (leaves ~4.5GB for GPU ops)

### 2.3 Tool Call Format (Rosetta Stone)

```python
# Input format (user request)
"search memory for auth patterns"

# Output format (tool call)
[TOOL_CALL]{tool => "memory_search", args => { --query "auth patterns", --limit 10 }}[/TOOL_CALL]
```

---

## Phase 3: Training Data Generation

### 3.1 Generate Training Data for ALL 40+ Tools

**Script**: `scripts/generate_full_training_data.py` (exists, needs update)

**Required Changes**:
1. Update `MCPToolLoader` to fetch ALL current tools (not just 10)
2. Generate 500-1000 examples per tool category
3. Use Unsloth's data generation for diversity

**Example Generation Template**:
```python
# Memory tools
("search memory for {query}", "memory_search", {"query": "{query}", "limit": 10})
("remember {content}", "memory_write", {"content": "{content}", "kind": "episodic"})

# Git tools  
("check git status", "git_status", {"repo_path": "."})
("show me the diff", "git_diff", {"repo_path": ".", "target": "HEAD"})

# Quality gates
("run typecheck", "run_typecheck", {})
("run linting", "run_lint", {})

# ... repeat for ALL 40+ tools
```

### 3.2 Quality Over Quantity

**Key Finding from Research**: 500-1k quality examples > 50k low-quality examples

**Training Data Requirements**:
- Diverse phrasings for each tool
- Edge cases (empty inputs, boundary values)
- Malformed input handling examples
- Error cases with proper error messages

---

## Phase 4: LoRA Training Pipeline

### 4.1 Unsloth-Based QLoRA (Recommended)

```bash
# Train each LoRA adapter
python scripts/unsloth_train.py \
  --model qwen2.5-0.5b-instruct-q4_k_m \
  --data datasets/brain_training.jsonl \
  --output models/triage-lora.gguf \
  --task triage

python scripts/unsloth_train.py \
  --model qwen2.5-0.5b-instruct-q4_k_m \
  --data datasets/tool_selection.jsonl \
  --output models/tool-select-lora.gguf \
  --task tool_selection
```

### 4.2 Training Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Base Model | Qwen2.5-0.5B-Instruct | Best tool calling in 0.5B |
| LoRA Rank | 16 | Balance quality vs size |
| LoRA Alpha | 32 | Standard ratio |
| LoRA Dropout | 0.05 | Prevent overfitting |
| Learning Rate | 2e-4 | Unsloth default |
| Epochs | 3-5 | Early stopping |
| Batch Size | 4 | VRAM constraint |
| Gradient Steps | 4 | Effective batch 16 |

### 4.3 Multi-Adapter Loading

Frankenstein engine supports loading multiple LoRA adapters:

```python
from frankenstein_engine.engine import DirectLlamaClient

client = DirectLlamaClient(
    model_path="qwen2.5-0.5b-instruct-q4_k_m.gguf",
    n_gpu_layers=19,
    # Load multiple LoRAs
    lora_path="triage-lora.gguf,tool-select-lora.gguf",
    lora_scale=0.8,  # Blend weight
)
```

---

## Phase 5: Integration with OpenCode

### 5.1 Brain MCP Server

Create `brain_mcp.py` that exposes the brain as MCP tools:

```python
from fastmcp import FastMCP
mcp = FastMCP("N-Xyme Brain")

@mcp.tool()
def brain_route(prompt: str) -> dict:
    """Route prompt through brain pipeline."""
    # 1. Triage → 2. Tool Select → 3. Param Extract → 4. Execute
    pass

@mcp.tool()
def brain_execute(prompt: str) -> str:
    """Execute full brain pipeline and return result."""
    pass
```

### 5.2 Wire into opencode.json

```json
{
  "mcp": {
    "brain": {
      "command": ["python3", "scripts/brain_mcp.py"],
      "env": {
        "MODEL_PATH": "models/qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "LORA_PATHS": "models/triage-lora.gguf,models/tool-select-lora.gguf"
      }
    }
  }
}
```

---

## Phase 6: Optimization & Tightening

### 6.1 Trainer Improvements

| Issue | Fix |
|-------|-----|
| Only 10 tools in dataset | Regenerate with ALL 40+ tools |
| No validation | Add holdout set (20% of data) |
| No evaluation | Add tool selection accuracy metric |
| No caching | Cache embeddings for repeated prompts |

### 6.2 Inference Optimizations

| Technique | Impact |
|-----------|--------|
| KV Cache Quantization | 2x context, minimal quality loss |
| Flash Attention | 1.2-1.5x speedup |
| Continuous Batching | Higher throughput |
| Speculative Decoding | 1.5x speedup (if supported) |

### 6.3 Router Upgrades

Current: Keyword-only routing (`router/__init__.py`)  
Recommended: LLM-based routing with fallback

```python
class RouterBrain:
    def route(self, prompt: str) -> dict:
        # Try LLM-based analysis first
        try:
            return self._analyze_with_llm(prompt)
        except:
            # Fallback to keyword
            return self._route_keyword(prompt)
```

---

## Implementation Roadmap

### Week 1: Foundation

| Day | Task | Owner |
|-----|------|-------|
| 1 | Update MCPToolLoader for all 40+ tools | Hephaestus |
| 2 | Generate training data (500 examples x 40 tools) | Hephaestus |
| 3 | Validate training data quality | Review |
| 4 | Set up Unsloth training environment | Hephaestus |
| 5 | Train triage LoRA (0.5B) | Automated |

### Week 2: Model Training

| Day | Task | Owner |
|-----|------|-------|
| 1 | Train tool-select LoRA | Automated |
| 2 | Train param-extract LoRA | Automated |
| 3 | Evaluate on holdout set | Review |
| 4 | Fix any accuracy issues | Hephaestus |
| 5 | Freeze models, create backups | Automated |

### Week 3: Integration

| Day | Task | Owner |
|-----|------|-------|
| 1 | Create brain_mcp.py server | Hephaestus |
| 2 | Test full pipeline end-to-end | Review |
| 3 | Wire into opencode.json | Hephaestus |
| 4 | Performance benchmarking | Review |
| 5 | Documentation | Hephaestus |

### Week 4: Optimization

| Day | Task | Owner |
|-----|------|-------|
| 1 | VRAM optimization (quantization) | Hephaestus |
| 2 | Latency optimization | Hephaestus |
| 3 | Add caching layer | Hephaestus |
| 4 | Load testing | Review |
| 5 | Production deployment | Sisyphus |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LoRA training fails | High | Use pre-trained adapters from Hub |
| VRAM overflow | High | Reduce batch size, use 4-bit quantization |
| Tool selection accuracy < 85% | Medium | Increase training data, add more epochs |
| Training takes too long | Medium | Use Unsloth (2-5x faster), smaller dataset |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Tool selection accuracy | ≥85% | Holdout eval |
| Parameter extraction accuracy | ≥90% | Holdout eval |
| Inference latency (triage) | <50ms | Benchmark |
| Total VRAM usage | <10GB | nvidia-smi |
| Training time (per LoRA) | <2hr | Time measurement |

---

## Appendix: File Locations

```
frankenstein_engine/
├── config.py              # Configuration
├── engine/__init__.py     # Direct GGUF + LoRA
├── router/__init__.py     # Routing logic
├── compatibility.py       # Rosetta + MCP execution
└── health/__init__.py     # Health monitoring

scripts/
├── train_rosetta_stone.py    # Main trainer
├── unsloth_train.py           # Unsloth-based training
├── generate_full_training_data.py  # Data generation
└── brain_mcp.py              # Brain MCP server (to create)

models/
├── qwen2.5-0.5b-instruct-q4_k_m.gguf  # Base model
├── qwen2.5-coder-7b-q4_k_m.gguf        # Reasoner
├── triage-lora.gguf                   # (to create)
├── tool-select-lora.gguf              # (to create)
└── param-extract-lora.gguf            # (to create)

datasets/
├── rosetta_merged_training.jsonl  # Current (10 tools)
└── brain_training.jsonl          # (to create - 40+ tools)
```
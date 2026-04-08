# Rosetta Stone - Local Tool Call Translator Masterplan

## Project Overview

**Goal**: Build a "Rosetta Stone" local LLM that translates natural language to tool calls, enabling any small local model to use tools effectively.

**Philosophy**: Training + Prompt Engineering = Best of Both Worlds

**Hardware**: 7800x3D + RTX 3080Ti (12GB VRAM) + 32GB RAM

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ROSETTA STONE ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  USER MESSAGE                                                              │
│       │                                                                    │
│       ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STAGE 1: TOOL CALL TRANSLATOR (Rosetta Stone)                     │   │
│  │  - Qwen2.5-0.5B-Instruct (fine-tuned on tool calling)              │   │
│  │  - Runs in 2-3GB VRAM                                               │   │
│  │  - Decides: call tool OR pass through                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                    │
│       ├───→ VALID TOOL CALL ──→ EXECUTE VIA MCP ──→ RETURN RESULT        │
│       │                                                                    │
│       └───→ NO TOOL CALL ──→ PASS TO MAIN MODEL (qwen2.5-coder:7b)       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component 1: Perfect Model Selection

### Model Choice Rationale

| Model | Parameters | VRAM | Tool Calling | Notes |
|-------|------------|------|--------------|-------|
| **Qwen2.5-0.5B-Instruct** | 0.5B | 1-2GB | Can be trained | BEST - smallest, fits easily |
| Qwen2.5-1.5B-Instruct | 1.5B | 2-3GB | Better after training | Good alternative |
| **Phi-3.5-mini** | 3.8B | 3-4GB | Excellent | Microsoft quality |
| Llama-3.2-2B-Instruct | 2B | 2-3GB | Good | Meta's model |

### Recommended: Qwen2.5-0.5B-Instruct

**Why**:
- Smallest (0.5B) = fastest inference
- Qwen family has best JSON output after training
- Already fits in 2GB VRAM with room for LoRA
- Can run alongside main model (7B)

---

## Component 2: Tool Wrapper (Enhancement)

### Current State
- `packages/local_llm/wrapper.py` exists ✓
- `packages/local_llm/mcp_tool_loader.py` has 30+ tools ✓

### Enhancements Needed

#### 2.1 Prompt Engineering Layer
```python
# Enhanced system prompt for tool calling
SYSTEM_PROMPT = """You are a tool call translator. Your job is to:
1. Analyze user requests
2. If tools are needed, output ONLY valid JSON tool calls
3. If no tools needed, output plain text

Available tools:
{tool_schemas}

Output format (for tool calls):
{"type": "tool_call", "name": "tool_name", "arguments": {...}}

Output format (no tools):
{"type": "text", "content": "..."}

Examples:
{ few_shot_examples }
"""
```

#### 2.2 Output Validation
```python
def validate_tool_call(response: str) -> Optional[ToolCall]:
    # 1. Parse JSON
    # 2. Validate against tool schema
    # 3. Return None if invalid (fallback to main model)
```

#### 2.3 Fallback Chain
```
Rosetta Stone (0.5B) → Invalid? → qwen2.5-coder:7b → Still invalid? → Cloud (qwen3.6-plus-free)
```

---

## Component 3: Training Pipeline (Cloud-to-Local)

### Overview
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRAINING DATA PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐              │
│   │ Tool Schema  │────▶│   Prompt     │────▶│    Cloud     │              │
│   │  Generator   │     │  Generator   │     │    Model     │              │
│   └──────────────┘     └──────────────┘     └──────────────┘              │
│         │                    │                     │                       │
│         │                    │                     ▼                       │
│         │                    │            ┌──────────────┐                 │
│         │                    │            │  Tool Call   │                 │
│         │                    │            │   Collector  │                 │
│         │                    │            └──────────────┘                 │
│         │                    │                     │                       │
│         ▼                    ▼                     ▼                       │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │              TRAINING DATASET (JSONL)                          │       │
│   │   {"messages": [...], "tool_calls": [...], "valid": true}     │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│                              │                                             │
│                              ▼                                             │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │                    UNSLOTH FINE-TUNING                          │       │
│   │   - QLoRA (rank=32, alpha=64)                                  │       │
│   │   - 3 epochs, batch_size=1                                      │       │
│   │   - ~2-3 hours on 12GB VRAM                                    │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│                              │                                             │
│                              ▼                                             │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │              rosetta-stone-v1 (fine-tuned model)               │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Implementation

#### Step 1: Generate Training Prompts
```python
# From tool schemas, generate varied user requests
TOOL_PROMPTS = {
    "read_file": [
        "Show me what's in config.py",
        "Read the contents of settings.json",
        "What does main.py contain?",
        "Display the file at path /home/user/app.py"
    ],
    "git_status": [
        "What's the current git status?",
        "Show me modified files",
        "Check if there are uncommitted changes"
    ],
    # ... for each tool
}
```

#### Step 2: Call Cloud Model
```python
# Use OpenCode cloud model as teacher
import openai

client = openai.OpenAI(
    api_key=os.environ["OPENCODE_API_KEY"],
    base_url="https://opencode.ai/api/v1"
)

response = client.chat.completions.create(
    model="qwen3.6-plus-free",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ],
    tools=tool_schemas,  # OpenAI function calling format
    temperature=0.1
)
```

#### Step 3: Collect Valid Tool Calls
```python
# Save to JSONL
with open("datasets/cloud_generated_tool_calls.jsonl", "a") as f:
    for tool_call in response.tool_calls:
        f.write(json.dumps({
            "messages": messages_history,
            "tool_calls": [tc.model_dump()],
            "valid": True  # or validate
        }) + "\n")
```

#### Step 4: Fine-tune with Unsloth
```python
from unsloth import FastLanguageModel
import torch

# Load model
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="Qwen/Qwen2.5-0.5B-Instruct",
    max_seq_length=2048,
    dtype=torch.float16,
    load_in_4bit=True
)

# Add LoRA
model = FastLanguageModel.get_peft_model(
    model,
    r=32,
    lora_alpha=64,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]
)

# Train
trainer = SFTTrainer(
    model=model,
    train_dataset=train_dataset,
    tokenizer=tokenizer,
    max_steps=1000
)
trainer.train()
```

---

## Implementation Roadmap

### Phase 1: Data Generation (Week 1)
| Task | Description | Output |
|------|-------------|--------|
| 1.1 | Generate 50 prompts per tool (30 tools = 1500 prompts) | `prompts/per_tool_prompts.json` |
| 1.2 | Call cloud model for each prompt | Raw responses |
| 1.3 | Filter valid tool calls | `datasets/tool_calling_train.jsonl` (target: 1000+) |
| 1.4 | Validate and clean data | Clean dataset |

### Phase 2: Model Training (Week 2)
| Task | Description | Output |
|------|-------------|--------|
| 2.1 | Install Unsloth | `pip install unsloth` |
| 2.2 | Prepare training dataset | train.jsonl, val.jsonl |
| 2.3 | Configure QLoRA | config.yaml |
| 2.4 | Run training | `models/rosetta-stone-v1/` |
| 2.5 | Export to GGUF | `rosetta-stone-v1.gguf` |

### Phase 3: Wrapper Enhancement (Week 3)
| Task | Description | Output |
|------|-------------|--------|
| 3.1 | Update system prompts | Enhanced wrapper |
| 3.2 | Add validation layer | tool_validator.py |
| 3.3 | Implement fallback chain | Fallback logic |
| 3.4 | Test with real prompts | Validated wrapper |

### Phase 4: Integration (Week 4)
| Task | Description | Output |
|------|-------------|--------|
| 4.1 | Add to Ollama | `ollama create rosetta-stone` |
| 4.2 | Integrate with orchestrator | AgentCoordinator changes |
| 4.3 | End-to-end testing | Working pipeline |
| 4.4 | Benchmark vs baseline | Metrics |

---

## File Structure

```
/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/
├── datasets/
│   ├── tool_calling_examples.jsonl        # Original 20 examples
│   ├── cloud_generated_tool_calls.jsonl    # NEW: Generated from cloud
│   └── rosetta_training.jsonl              # NEW: Cleaned training data
│
├── packages/local_llm/
│   ├── wrapper.py                          # EXISTING - enhance
│   ├── mcp_tool_loader.py                   # EXISTING - has 30+ tools
│   ├── tool_validator.py                    # ENHANCE - add validation
│   ├── rosetta_translator.py               # NEW - main translator
│   ├── data_generator.py                   # NEW - cloud data collection
│   └── prompt_engineering.py               # NEW - prompt enhancements
│
├── models/
│   └── rosetta-stone-v1/                   # NEW - trained model
│       ├── adapter_config.json
│       ├── adapter_model.safetensors
│       └── rosetta-stone-v1.gguf           # For llama.cpp
│
├── scripts/
│   ├── generate_training_data.py           # NEW - run cloud calls
│   ├── train_rosetta.sh                    # NEW - training script
│   └── export_gguf.sh                      # NEW - export to GGUF
│
└── config/
    ├── rosetta-prompt-template.txt         # NEW - system prompt
    └── training-config.yaml                # NEW - QLoRA config
```

---

## Quality Gates

| Gate | Criteria | Test |
|------|----------|------|
| Data Quality | 1000+ examples, >90% valid | Validate JSONL |
| Training | Loss converges <0.1 | TensorBoard |
| Inference | <500ms latency | Benchmark |
| Tool Call Accuracy | >85% on seen tools | Test set |
| Integration | No breaking changes | E2E tests |

---

## Budget: $0

- Cloud models: FREE (qwen3.6-plus-free, minimax-m2.5-free)
- Training: FREE (Unsloth, 4-bit LoRA on 12GB VRAM)
- Inference: FREE (Ollama, local)
- Total: $0

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Training Data | 1000+ examples | JSONL line count |
| Tool Call Accuracy | >85% | Test set evaluation |
| Inference Latency | <500ms | Benchmark |
| Fallback Rate | <15% | Production logs |
| Cost | $0 | No API bills |

---

## Next Steps (Action Items)

1. [ ] **Start Phase 1**: Generate training prompts from tool schemas
2. [ ] **Call cloud model**: 1500 prompts → collect tool calls
3. [ ] **Clean dataset**: 1000+ valid examples
4. [ ] **Pull Qwen2.5-0.5B-Instruct**: `ollama pull qwen2.5:0.5b`
5. [ ] **Install Unsloth**: `pip install unsloth`
6. [ ] **Run training**: 2-3 hours
7. [ ] **Enhance wrapper**: Add prompts + validation
8. [ ] **Integrate**: Add to orchestrator
9. [ ] **Benchmark**: Compare to baseline

---

*Document Version: 1.0*
*Created: 2026-04-08*
*Project: Rosetta Stone - Local Tool Call Translator*
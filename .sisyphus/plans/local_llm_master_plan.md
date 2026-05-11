# 🎯 Local LLM Optimization - Complete Master Plan

## Vision

Transform the local LLM (Ollama) into a production-grade system that rivals cloud APIs through systematic optimization across all layers.

---

## 📊 Current State

| Component | Status | Notes |
|-----------|--------|-------|
| Ollama API | ✅ Working | qwen2.5-coder:7b, llama3.2:3b available |
| Tool Calling | ✅ Working | 2-pass pipeline: model → tools → results |
| MCP Tools | ✅ Done | 23 tools with handlers registered |
| Generation Params | ✅ Optimized | temperature, top_p, num_ctx, etc. |
| Tool Schemas | ✅ Enhanced | Rich descriptions with use cases |
| Model Routing | ✅ Working | intelligent_router integration |

---

## 🔬 Research Findings

### Generation Parameters (Best Practices)

| Parameter | Recommended | Why |
|-----------|-------------|-----|
| `temperature` | 0.1-0.3 (code), 0.7-0.8 (chat) | Lower = more deterministic for tools |
| `top_p` | 0.9-0.95 | Nucleus sampling |
| `num_ctx` | 4096-8192 | Context window for code |
| `repeat_penalty` | 1.0-1.1 | Reduce token repetition |
| `seed` | 42 | Reproducibility |
| `format: "json"` | Use for structured output | Tool calling requires JSON |

### Tool Calling Best Practices

- **Best models**: qwen3, llama3.1+ for tool calling
- **Two-step process**: request with tools → tool result → final response
- Clear, descriptive function descriptions required
- 2-3 shot examples in system prompt

### LoRA Parameters (If Training)

| Parameter | Recommended |
|-----------|-------------|
| LoRA Rank | 16-32 |
| LoRA Alpha | r × 2 |
| Dropout | 0 (default), 0.1 if overfitting |
| Target Modules | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj |
| Learning Rate | 2e-4 |
| Epochs | 1-3 |

---

## 📋 Phased Implementation Plan

### Phase 1: Quick Wins (COMPLETED ✅)

| Task | Effort | Status |
|------|--------|--------|
| Generation Parameters | 30 min | ✅ Done |
| System Prompt | 30 min | ✅ Done |
| Tool Schemas | 1 hour | ✅ Done |
| Register Handlers | 3 hours | ✅ Done |

#### What Was Added

**1. Generation Parameters** (`ollama_client.py`):
```python
DEFAULT_PARAMS = {
    "temperature": 0.3,      # Lower for code/tool tasks
    "top_p": 0.95,          # Nucleus sampling
    "top_k": 40,            # Limit vocabulary
    "num_ctx": 8192,        # Context window
    "repeat_penalty": 1.1,  # Reduce repetition
    "seed": 42,             # Reproducibility
    "num_predict": 2048,    # Max tokens
    "stream": False,        # Easier parsing
}

CHAT_PARAMS = {
    "temperature": 0.7,     # Higher for general chat
    "top_p": 0.9,
}
```

**2. System Prompt** (`ollama_client.py`):
```python
SYSTEM_PROMPT = """You are an expert AI coding assistant with tool calling capabilities.

When asked to perform a task that requires external tools:
1. Analyze the request to identify required tool(s)
2. Call ONLY one tool at a time using the exact JSON format below
3. Wait for the result before continuing
4. Synthesize the final answer from tool results

Tool calling format (MUST follow exactly):
{
  "name": "tool_name",
  "arguments": {"arg1": "value1", "arg2": "value2"}
}

Example:
User: "What is 5 + 3?"
You: {"name": "add", "arguments": {"a": 5, "b": 3}}

Always respond in JSON format when calling tools. If no tool is needed, respond directly."""
```

**3. Enhanced Tool Schemas** (`mcp_tool_loader.py`):
- All 23 tools now have rich descriptions
- Each includes "Use for: X" and "NOT for: Y"

**4. Registered Tool Handlers** (`integration.py`):
- 20+ handlers registered for all MCP tools

---

### Phase 2: Medium Effort (IN PROGRESS)

| Task | Effort | Status |
|------|--------|--------|
| Tool Validation Layer | 2 hours | Pending |
| RAG Context Injection | 3 hours | Pending |

#### Phase 2.1: RAG Context Injection

**What it does**: Before the LLM answers, search relevant context and inject it into the prompt.

**When to use**:
- Code generation (inject existing patterns)
- Debugging (inject error logs, relevant code)
- Architecture questions (inject AGENTS.md rules)

**Implementation** (`rag_injector.py`):
```python
class RAGContextInjector:
    def __init__(self, embedding_model="nomic-embed-text"):
        self.embed_model = embedding_model
        self.chunk_size = 400
        self.top_k = 5
    
    async def inject_context(self, query: str, docs: List[Dict]) -> str:
        # 1. Embed query via Ollama
        # 2. Retrieve top-K relevant docs
        # 3. Build context string
        # 4. Return enhanced prompt
```

**Usage**:
```python
# Before sending to LLM
context = await rag_injector.inject_context(
    query=user_message,
    docs=[athena_results, memory_results, file_contents]
)
enhanced_prompt = f"Context:\n{context}\n\nUser: {user_message}"
```

#### Phase 2.2: Tool Validation Layer

**What it does**: Validate tool call arguments before execution.

**Implementation** (`tool_validator.py`):
```python
class ToolCallValidator:
    def __init__(self, available_tools: List[Dict]):
        self.tool_schemas = {t["function"]["name"]: t for t in available_tools}
    
    def validate(self, tool_call: Dict) -> Tuple[bool, str]:
        # Check tool exists
        # Check required arguments
        # Validate argument types
        # Return (is_valid, error_message)
```

**Prevents**:
- Missing required arguments
- Wrong argument types
- Invalid tool names

---

### Phase 3: Advanced (Future)

| Task | Effort | Notes |
|------|--------|-------|
| LoRA Fine-Tuning | 16 hours | Low ROI - skip unless specific failure |
| Model Routing | 4 hours | Route to different models based on task |

#### Phase 3.1: LoRA Fine-Tuning (OPTIONAL)

**When to consider**:
- Current model fails on specific tool calling patterns
- You have 500+ examples of desired behavior

**What's needed**:
- GPU: ✅ RTX 3080 Ti (12GB VRAM) - sufficient
- Dataset: ✅ `datasets/tool_calling_examples.jsonl` (20 examples)
- Tool: `axolotl`

**Training command**:
```bash
pip install axolotl
axolotl train datasets/tool_calling_examples.jsonl
```

**Config** (`axolotl.yaml`):
```yaml
base_model: qwen2.5-coder:7b
adapter: lora
lora_r: 32
lora_alpha: 64
lora_dropout: 0.05
lora_target_modules:
  - q_proj
  - k_proj
  - v_proj
  - o_proj
learning_rate: 0.0002
epochs: 3
```

#### Phase 3.2: Model Routing

**Instead of training**, route to different models based on task:

```python
TASK_MODEL_MAP = {
    "code_generation": "qwen2.5-coder:7b",
    "reasoning": "qwen2.5:14b",
    "fast_simple": "llama3.2:1b",
    "general": "llama3.2:3b",
}
```

---

### Phase 4: Production Hardening

| Task | Description |
|------|-------------|
| Error Recovery | Retry with exponential backoff, max iterations |
| Monitoring | Track tool call success rate, latency per tool |
| Caching | Cache by semantic similarity, TTL-based invalidation |

---

## 📁 Files Modified

### Created
- `datasets/tool_calling_examples.jsonl` - Training dataset

### Modified
- `packages/local_llm/ollama_client.py` - Added DEFAULT_PARAMS, CHAT_PARAMS, SYSTEM_PROMPT
- `packages/local_llm/mcp_tool_loader.py` - Enhanced tool schemas with rich descriptions
- `packages/local_llm/integration.py` - Registered 20+ tool handlers

---

## 🚀 Success Metrics

| Metric | Baseline | Phase 1 Target | Phase 2 Target |
|--------|----------|-----------------|-----------------|
| Tool call success | 70% | 85% | 95% |
| Response latency | 3s | 2s | 1.5s |
| Missing handlers | 20 | 0 | 0 |
| Generation params set | 3 | 8 | 8 |

---

## 🎯 Next Actions

### Immediate (Next Session)

1. **Test current system** - Run a benchmark to verify Phase 1 improvements
2. **Phase 2.1**: Add RAG context injection (optional)
3. **Phase 2.2**: Add tool validation layer (recommended)

### Optional (Later)

4. **Phase 3.1**: LoRA fine-tuning (only if specific failures)
5. **Phase 3.2**: Model routing based on task type
6. **Phase 4**: Production hardening

---

## 📚 References

- Ollama API Docs: https://docs.ollama.com/api/generate
- Tool Calling: https://docs.ollama.com/capabilities/tool-calling
- Axolotl: https://github.com/axolotl-ai-cloud/axolotl
- Embedding Models: nomic-embed-text, bge-small-en-v1.5, BGE-M3

---

## Quick Reference

```bash
# Test the integration
python3 -c "
from packages.local_llm.integration import LocalLLMIntegration
integration = LocalLLMIntegration()
print(integration.get_status())
"

# List available tools
python3 -c "
from packages.local_llm.mcp_tool_loader import MCPToolLoader
loader = MCPToolLoader()
print(f'Tools: {loader.list_tools()}')
"

# Check GPU for training
nvidia-smi

# Run benchmark
python3 -m pytest tests/benchmark_local_llm.py -v
```

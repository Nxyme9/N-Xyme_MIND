# Masterplan: Local LLM Optimization

## Vision

Transform local LLM from a working prototype into a production-grade system that rivals cloud APIs through systematic optimization across all layers.

---

## Current State (Verified via Exploration)

| Component | Status | Notes |
|-----------|--------|-------|
| Ollama API | ✅ Working | qwen2.5-coder:7b, llama3.2:3b |
| Tool Calling | ✅ Working | 2-pass pipeline |
| MCP Tools | ⚠️ Partial | 26 tools defined, **6 handlers registered**, 20 missing |
| Model Routing | ✅ Working | intelligent_router integration |
| Simple Chat | ✅ Fixed | No longer auto-loads all tools |

### Gaps Identified

| Area | Current State | Gap |
|------|---------------|-----|
| **Generation params** | temperature, num_predict, top_k | **Missing**: top_p, num_ctx, repeat_penalty, seed, stop |
| **Tool handlers** | 6 registered | 20 missing (memory_write, github_*, fetch, browser_*, etc.) |
| **Tool validation** | None | No input schema validation before execution |
| **Timeouts** | None | No timeout on tool execution |

---

## Research Findings Summary

### 1. Ollama Best Practices (from Librarian)

| Parameter | Recommended | Current |
|-----------|-------------|---------|
| `temperature` | 0.1-0.3 (code), 0.7-0.8 (chat) | 0.3-0.8 (varies) |
| `top_p` | 0.9-0.95 | **NOT SET** |
| `num_ctx` | 4096-8192 (code) | **NOT SET** |
| `repeat_penalty` | 1.0-1.1 | **NOT SET** |
| `format: "json"` | Use for structured output | Not used |

### 2. Tool Calling Best Practices

- **Best models**: qwen3, llama3.1+ for tool calling
- **Two-step process**: request with tools → tool result → final
- Use `format: "json"` for structured output
- Clear, descriptive function descriptions required

### 3. LoRA Parameters (from Librarian)

| Parameter | Recommended |
|-----------|-------------|
| LoRA Rank | 16-32 |
| LoRA Alpha | r × 2 |
| Dropout | 0 (default), 0.1 if overfitting |
| Target Modules | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj |
| Learning Rate | 2e-4 for LoRA |
| Epochs | 1-3 |

### 4. RAG Embeddings (from Librarian)

| Model | Params | Use Case |
|-------|--------|----------|
| nomic-embed-text | 137M | CPU-only, lightweight |
| bge-small-en-v1.5 | 33M | Default, fast |
| BGE-M3 | 568M | Multilingual |

---

## Optimization Phases

### Phase 1: Quick Wins (0-2 hours)

**Goal**: Immediate performance gains with minimal effort

#### 1.1 Generation Parameters Tuning ✅ PRIORITY 1

**Add missing parameters** to `packages/local_llm/ollama_client.py`:

```python
DEFAULT_PARAMS = {
    "temperature": 0.3,      # Lower for code/tool tasks
    "top_p": 0.95,          # Add: nucleus sampling
    "top_k": 40,            # Keep: limit vocabulary
    "num_ctx": 8192,        # Add: context window
    "repeat_penalty": 1.1,  # Add: reduce repetition
    "seed": 42,             # Add: reproducibility
    "num_predict": 2048,    # Keep: max tokens
    "stream": False,        # Add: easier parsing
}
```

**Task**: Edit `ollama_client.py` to add these parameters

#### 1.2 System Prompt Optimization ✅ PRIORITY 2

Create optimized system prompt in `packages/local_llm/ollama_client.py`:

```python
SYSTEM_PROMPT = """You are an expert AI coding assistant with tool calling capabilities.

When asked to perform a task that requires external tools:
1. Analyze the request to identify required tool(s)
2. Call ONLY one tool at a time using the exact JSON format
3. Wait for the result before continuing
4. Synthesize the final answer from tool results

Tool calling format (MUST follow exactly):
{
  "name": "tool_name",
  "arguments": {"arg1": "value1", "arg2": "value2"}
}

Available tools: {tool_list}

Always respond in the requested format. If no tool is needed, respond directly."""
```

#### 1.3 Tool Schema Improvement ✅ PRIORITY 3

Enhance tool descriptions in `packages/local_llm/mcp_tool_loader.py`:

```python
# Before: Minimal
"add": {"description": "Add two numbers", ...}

# After: Rich descriptions
"add": {
    "description": "Perform arithmetic addition of two integers or floats. " +
                   "Use for calculations, sums, totals, mathematical operations. " +
                   "NOT for string concatenation.",
    "parameters": {
        "properties": {
            "a": {"description": "First number (integer or float)"},
            "b": {"description": "Second number (integer or float)"}
        }
    }
}
```

---

### Phase 2: Medium Effort (2-8 hours)

#### 2.1 RAG Context Injection

**Create**: `packages/local_llm/rag_injector.py`

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

**Use cases**:
- Inject AGENTS.md rules before execution
- Inject codebase context for code generation

#### 2.2 Tool Validation Layer

**Create**: `packages/local_llm/tool_validator.py`

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

#### 2.3 Register Missing Handlers

**Add handlers** for 20 missing tools in `packages/local_llm/integration.py`:

| Tool | Handler Needed |
|------|----------------|
| memory_write | ✅ |
| athena_smart_search | ✅ |
| git_log | ✅ |
| git_diff | ✅ |
| github_search_repositories | ✅ |
| github_list_issues | ✅ |
| fetch_url | ✅ |
| context7_query_docs | ✅ |
| sequential_thinking | ✅ |
| get_active_context | ✅ |
| get_user_context | ✅ |
| record_outcome | ✅ |
| run_typecheck | ✅ |
| run_lint | ✅ |
| browser_navigate | ✅ |
| browser_click | ✅ |
| sqlite_query | ✅ |

---

### Phase 3: Advanced (8-40 hours)

#### 3.1 LoRA Fine-Tuning

**Dataset** (create: `datasets/tool_calling_examples.jsonl`):
```json
{"messages": [{"role": "user", "content": "What is 5 + 3?"}, {"role": "assistant", "tool_calls": [{"function": {"name": "add", "arguments": {"a": 5, "b": 3}}}]}]}
{"messages": [{"role": "user", "content": "Search memory for test"}, {"role": "assistant", "tool_calls": [{"function": {"name": "memory_search", "arguments": {"query": "test"}}}]}]}
```

**Config** (axolotl):
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

#### 3.2 Multi-Model Routing (Skip Merging)

Instead of model merging (risky), implement smart routing:

```python
# Route based on task type
TASK_MODEL_MAP = {
    "code_generation": "qwen2.5-coder:7b",
    "reasoning": "qwen2.5:14b",
    "fast_simple": "llama3.2:1b",
    "general": "llama3.2:3b",
}
```

---

### Phase 4: Production Hardening

#### 4.1 Error Recovery

- Add retry with exponential backoff
- Add max iteration limits
- Add timeout on tool execution

#### 4.2 Monitoring

- Track tool call success rate
- Track latency per tool
- Track error distribution

#### 4.3 Caching (Semantic)

- Cache by semantic similarity
- TTL-based invalidation

---

## Implementation Order (Revised)

Based on Oracle's ROI analysis + Research findings:

```
Phase 1.1: Generation params      [30 min]  ✅ DONE
Phase 1.2: System prompt          [30 min]  ✅ DONE
Phase 1.3: Tool schemas          [1 hour]   ✅ DONE

Phase 2.3: Missing handlers      [3 hours]  ← HIGH IMPACT (20 tools)
Phase 2.2: Tool validation      [2 hours]
Phase 2.1: RAG injection        [3 hours]

Phase 3.1: LoRA fine-tuning     [16 hours] ← DEPRECATE (low ROI)
Phase 3.2: Model routing        [4 hours]

Phase 4: Production hardening   [6 hours]
```

---

## Oracle's Recommendations

### Do Immediately:
1. **Tune temperature to 0.3-0.5** for tool calls (lower = more deterministic)
2. **Simplify tool schemas** - reduce parsing failures
3. **Add 2-3 shot examples** in system prompt for tool calling format

### Skip for Now:
- ❌ LoRA (unless specific failure modes)
- ❌ Model merging (too experimental)
- ❌ Aggressive caching (add after validation)

### Alternative Approaches:
1. **Model routing > merging**: Route queries to optimal model based on task
2. **Prompt templates > fine-tuning**: Few-shot examples match LoRA quality
3. **Semantic caching**: Cache by similarity, not exact match

---

## Success Metrics

| Metric | Baseline | Phase 1 Target | Phase 2 Target |
|--------|----------|-----------------|----------------|
| Tool call success | 70% | 85% | 95% |
| Response latency | 3s | 2s | 1.5s |
| Missing handlers | 20 | 6 | 0 |
| Generation params set | 3 | 8 | 8 |

---

## Files to Create/Modify

### Create
- `packages/local_llm/rag_injector.py` - RAG context injection
- `packages/local_llm/tool_validator.py` - Tool call validation
- `datasets/tool_calling_examples.jsonl` - Fine-tuning dataset

### Modify
- `packages/local_llm/ollama_client.py` - **Phase 1.1**: Add top_p, num_ctx, repeat_penalty
- `packages/local_llm/mcp_tool_loader.py` - **Phase 1.3**: Enhance schemas
- `packages/local_llm/integration.py` - **Phase 2.3**: Register 20 missing handlers

---

## Next Actions

1. **Start Phase 1.1 NOW**: Add generation parameters to `ollama_client.py`
2. **Test**: Run benchmark after each change
3. **Then Phase 1.2**: Optimize system prompt
4. **Then Phase 1.3**: Enhance tool schemas
5. **Then Phase 2.3**: Register missing handlers

---

## References

- Ollama API Docs: https://docs.ollama.com/api/generate
- Tool Calling: https://docs.ollama.com/capabilities/tool-calling
- Axolotl: https://github.com/axolotl-ai-cloud/axolotl
- Embedding Models: nomic-embed-text, bge-small-en-v1.5, BGE-M3

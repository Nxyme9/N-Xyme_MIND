# Rosetta Stone Training - Research Summary
**Date:** 2026-04-14
**Goal:** Achieve 90-100% tool calling accuracy for nx_trainer (Rosetta Stone Trainer)

---

## 1. Checkpoints Found

### Training Outputs

| Location | Checkpoints | Status |
|----------|-------------|--------|
| `rosetta-stone-trainer/output/rosetta-v4/` | checkpoint-84 | Final (loss: 0.056) |
| `models/rosetta-lora/` | checkpoint-50, checkpoint-63 | Smaller adapter |
| `models/rosetta-lora-ecosystem/` | checkpoint-1000, checkpoint-950 | High-step count |
| `models/rosetta-lora-extended/` | checkpoint-450, checkpoint-460 | Extended training |
| `models/rosetta-lora-full/` | checkpoint-200, checkpoint-230 | Full training |
| `models/rosetta-lora-new/` | checkpoint-100, checkpoint-147 | Newest |
| `models/rosetta-lora-v2/` | checkpoint-450, checkpoint-460 | V2 |

### GGUF Models (merged/inference-ready)

- `models/rosetta-lora.gguf` (17.6 MB)
- `models/rosetta-lora-new.gguf` (17.6 MB)
- `models/rosetta-merged.gguf` (0 bytes - incomplete)

---

## 2. Training Configuration (from checkpoint-84)

```json
{
  "epoch": 3.0,
  "global_step": 84,
  "train_batch_size": 1,
  "num_train_epochs": 3,
  "save_steps": 500,
  "eval_steps": 500
}
```

### Loss Progression
| Step | Loss | Learning Rate |
|------|------|---------------|
| 10 | 1.477 | 1.94e-05 |
| 20 | 0.126 | 1.76e-05 |
| 30 | 0.103 | 1.47e-05 |
| 40 | 0.084 | 1.11e-05 |
| 50 | 0.070 | 7.41e-06 |
| 60 | 0.064 | 4.06e-06 |
| 70 | 0.058 | 1.53e-06 |
| 80 | 0.056 | 1.74e-07 |

**Excellent convergence:** Loss went from 1.48 → 0.056 (96% reduction)

---

## 3. Anthropic Source Code Insights

### Tool Execution Pipeline (from `/ant-source-code-main/`)

**Key Files:**
- `services/tools/toolExecution.ts` (1745 lines) - Core execution
- `services/tools/toolOrchestration.ts` (188 lines) - Concurrency handling
- `services/tools/toolHooks.ts` (650 lines) - Pre/post execution hooks
- `constants/tools.ts` (112 lines) - Tool definitions
- `utils/toolErrors.ts` (132 lines) - Error formatting

### Key Techniques Found

#### A. Tool Partitioning Strategy
```typescript
// Partition tool calls into batches:
// 1. Single non-read-only tool (serial)
// 2. Multiple consecutive read-only tools (concurrent)
function partitionToolCalls(toolUseMessages, context): Batch[]
```

#### B. Zod Validation Error Formatting
```typescript
// Human-readable error messages for LLM
formatZodValidationError(toolName, error) → 
"The parameter `query` is missing"
"The parameter `path` type is expected as `string` but provided as `number`"
```

#### C. Schema Caching
```typescript
// Session-scoped cache prevents mid-session GB refreshes from busting cache
const TOOL_SCHEMA_CACHE = new Map<string, CachedSchema>()
```

#### D. Concurrency Safety Check
```typescript
// Each tool can declare if it's safe to run concurrently
tool?.isConcurrencySafe(parsedInput.data)
```

---

## 4. Current Training Pipeline

### Scripts Available
- `scripts/train_rosetta_stone.py` - Template-based generation
- `packages/training/train_rosetta_unified.py` - Full pipeline (download → train → export)
- `packages/training/train_rosetta.py` - Basic trainer
- `packages/training/train_rosetta_lora.py` - LoRA trainer

### Training Approach
1. **Template-based generation:** Simple phrase → tool call
2. **Instruction tuning:** `<|im_start|>user` → `<|im_start|>assistant`
3. **LoRA fine-tuning:** Qwen2.5-0.5B base + adapter
4. **GGUF export:** Merge adapter with base

---

## 5. Training Data Templates

From `train_rosetta_stone.py`:

```python
templates = [
    # Memory tools
    ("search memory for {query}", "memory_search", {"query": "{query}", "limit": 10}),
    ("look up {query} in memory", "memory_search", {"query": "{query}"}),
    ("find info about {query}", "athena_smart_search", {"query": "{query}"}),
    
    # File tools
    ("read file {path}", "read_file", {"path": "{path}"}),
    ("create file at {path}", "write_file", {"path": "{path}", "content": ""}),
    ("list directory {path}", "list_directory", {"path": "{path}"}),
    
    # Git tools
    ("check git status", "git_status", {"repo_path": "."}),
    ("show git log", "git_log", {"repo_path": ".", "max_count": 10}),
    ("show diff", "git_diff", {"repo_path": ".", "target": "HEAD"}),
    
    # Web tools
    ("fetch {url}", "fetch_url", {"url": "{url}", "format": "markdown"}),
    ("get docs for {lib}", "context7_query_docs", {"library_id": "/{lib}", "query": "basics"}),
    
    # Thinking
    ("think about {problem}", "sequential_thinking", {"thought": "{problem}", "nextThoughtNeeded": True, "thoughtNumber": 1, "totalThoughts": 3}),
]
```

---

## 6. Path to 90-100% Accuracy

### Current State
- Training loss: 0.056 (excellent convergence)
- Training data: ~100 examples per tool
- Model size: 0.5B parameters (Qwen2.5-0.5B)

### Gaps Identified

1. **Training data volume:** Need 100+ examples per tool × 60 tools = 6000+ examples
2. **Curriculum learning:** Not implemented - all tools trained equally
3. **Hard negative mining:** No counterexamples taught
4. **Error recovery:** No retry patterns in training data
5. **Multi-tool sequences:** Only single-tool examples
6. **Argument validation:** Training doesn't teach error handling

### Recommended Approach

#### Phase 1: Expand Training Data
```python
# Current: ~100 examples total
# Target: 6000+ examples (100 per tool × 60 tools)

categories = {
    "file_ops": ["read", "write", "edit", "glob", "grep", "list_directory"],
    "git_ops": ["git_status", "git_log", "git_diff", "git_commit"],
    "memory_ops": ["memory_search", "memory_write", "memory_stats"],
    "context_ops": ["get_active_context", "get_user_context", "get_product_context"],
    "routing_ops": ["route_task", "record_outcome", "get_recommendations"],
    "web_ops": ["fetch_url", "fetch_markdown", "context7_query"],
    "thinking_ops": ["sequential_thinking"],
    "mcp_ops": ["mcp_*"]  # All MCP tools
}
```

#### Phase 2: Curriculum Learning
```
Stage 1: Easy tools (single argument) - 500 examples
Stage 2: Medium tools (2-3 arguments) - 2000 examples
Stage 3: Complex tools (nested objects) - 3000 examples
Stage 4: Multi-tool sequences - 500 examples
```

#### Phase 3: Error Handling
```python
error_templates = [
    ("search memory for {invalid}", "ERROR: query parameter is required"),
    ("read file {nonexistent}", "ERROR: file not found"),
    ("fetch {invalid_url}", "ERROR: invalid URL format"),
]
```

---

## 7. Anthropic Techniques to Adopt

### From `toolErrors.ts`

```typescript
// LLM-friendly error messages
export function formatZodValidationError(toolName, error):
  → "The parameter `X` is missing"
  → "The parameter `Y` type is expected as `string` but provided as `number`"
```

### From `toolOrchestration.ts`

```typescript
// Read-only tools can run concurrently
// Non-read-only tools run serially
const isConcurrencySafe = tool?.isConcurrencySafe(parsedInput.data)
```

### From `constants/tools.ts`

```typescript
// Tool categories for curriculum learning
export const ASYNC_AGENT_ALLOWED_TOOLS = new Set([
  FILE_READ_TOOL_NAME,
  WEB_SEARCH_TOOL_NAME,
  // ... etc
])
```

---

## 8. Next Steps

### Immediate (This Session)
1. [ ] Expand training data to 6000+ examples
2. [ ] Implement curriculum learning (easy → hard)
3. [ ] Add error recovery examples
4. [ ] Add multi-tool sequence examples
5. [ ] Re-train with new dataset

### Validation
1. [ ] Test each checkpoint systematically
2. [ ] Measure accuracy per tool category
3. [ ] Identify failure patterns
4. [ ] Iterative refinement

---

## 9. Files Reference

### Training Scripts
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/scripts/train_rosetta_stone.py`
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/training/train_rosetta_unified.py`
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/training/train_rosetta.py`
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/training/train_rosetta_lora.py`

### Benchmark Scripts
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_engine/nx_engine/local_llm/benchmark_rosetta.py`

### Rosetta Executors
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_engine/nx_engine/local_llm/rosetta_executor.py`
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_engine/nx_engine/local_llm/rosetta_executor_direct.py`
- `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_engine/nx_engine/local_llm/rosetta_integration.py`

### Anthropic Source (Reference)
- `/home/nxyme/Documentos/CODE/source_code/ant-source-code-main/services/tools/toolExecution.ts`
- `/home/nxyme/Documentos/CODE/source_code/ant-source-code-main/services/tools/toolOrchestration.ts`
- `/home/nxyme/Documentos/CODE/source_code/ant-source-code-main/services/tools/toolHooks.ts`
- `/home/nxyme/Documentos/CODE/source_code/ant-source-code-main/utils/toolErrors.ts`
- `/home/nxyme/Documentos/CODE/source_code/ant-source-code-main/constants/tools.ts`

---

## 10. Accuracy Targets

| Metric | Current | Target |
|--------|---------|--------|
| Tool selection | ~60% | 100% |
| Argument extraction | ~60% | 100% |
| Error recovery | 0% | 95% |
| Multi-tool sequences | 0% | 90% |
| **Overall** | **~60%** | **95%+** |

---

*Last Updated: 2026-04-14*

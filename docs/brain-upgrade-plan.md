# N-Xyme MIND Brain Upgrade Implementation Plan

## Overview
Prioritized roadmap for upgrading the N-Xyme MIND brain based on 2025-2026 research.

**Hardware**: RTX 3080 Ti (12GB VRAM)
**Goal**: Maximize brain capabilities with local-first, no-cloud approach

---

## Phase 1: RAG System Enhancement ✅ EXISTING FOUNDATION

### Current State
- `RAGContextInjector` exists at `packages/local_llm/rag_injector.py`
- Uses `MemoryRouter` from `memory_core` 
- Uses direct GGUF embeddings (nomic-embed-text-v1.5-Q4_K_M.gguf)
- ChromaDB already installed

### Enhancements Needed
1. ✅ RAG Context Injector already exists
2. ⏳ Add hybrid search (keyword + semantic)
3. ⏳ Integrate with brain.py chat() method automatically

### Implementation
```python
# In brain.py, add RAG injection to chat()
def chat(self, messages, use_rag=True, **kwargs):
    if use_rag and messages:
        query = messages[-1].get("content", "")
        enhanced = self._rag_injector.inject_context(query)
        messages[-1]["content"] = enhanced
    return self._chat_internal(messages, **kwargs)
```

---

## Phase 2: Native Tool Calling Integration ⏳ NEXT

### Research Findings
- llama.cpp native `--tools all` support in mainline (2025+)
- Q4_K_M quantization: 5-10% better tool call success vs Q4_0
- Strict mode schemas with `additionalProperties: false` critical
- JSON native format recommended

### Available Models (already Q4_K_M!)
- `Qwen2.5-Coder-14B-Q4_K_M` (~8GB) - may need VRAM management
- `Qwen2.5-Coder-7B-Q4_K_M` (~4GB) - safe for 12GB with headroom
- `qwen2.5-0.5b-instruct-q4_k_m` (~700MB) - fast tool routing

### Tool Definitions (strict schema)
```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Search the knowledge base for relevant information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "get_time",
            "description": "Get current system time",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        }
    }
]
```

### Implementation Path
1. Update DirectLlamaClient to support `tools` parameter
2. Add tool execution loop in brain.py
3. Register first 3 tools: search_knowledge, get_time, echo

---

## Phase 3: Quantization Upgrade ✅ ALREADY DONE

### Current State
- All models already Q4_K_M quantized! ✅
- Qwen2.5-Coder-7B-Q4_K_M: 4GB (safe for 12GB)
- Qwen2.5-Coder-14B-Q4_K_M: ~8GB (tight but works)

### Potential Upgrades (future)
- IQ2/IQ3 formats for better quality at same size
- AWQ for 2-3% quality improvement over GGUF

---

## Phase 4: ReAct Agent Pattern ⏳

### Research Findings
- ReAct (Reason + Act): 90%+ production success
- Plan-Execute: 92% vs 85% for pure ReAct on complex tasks
- Reflexion adds self-correction: +5-10% success rate

### Implementation Pattern
```
1. THINK: Analyze the request
2. PLAN: Decide action sequence  
3. ACT: Execute tool/response
4. OBSERVE: Get result
5. REFLECT: Evaluate, retry if needed
```

### Code Structure
```python
class ReActAgent:
    def __init__(self, brain: Brain, max_iterations: int = 3):
        self.brain = brain
        self.max_iterations = max_iterations
    
    async def run(self, messages):
        for i in range(self.max_iterations):
            thought = await self.brain.think(messages)  # Reason
            if thought.needs_action:
                result = await self.execute(thought.action)  # Act
                messages.append({"role": "observation", "content": result})
            else:
                return thought.response  # Respond
        return "Max iterations reached"
```

---

## Phase 5: Multimodal Vision (Qwen3-VL)

### Research Findings
- **Qwen3-VL-4B-Q4**: Fits in 3-4GB VRAM, best balance for 12GB budget
- Qwen2.5-VL also available but Qwen3 has better instruction following
- Two-model pipeline: vision model → text model for reasoning

### VRAM Budget (12GB total)
| Component | Memory |
|-----------|--------|
| Qwen2.5-Coder-7B-Q4_K_M | 4GB |
| Qwen3-VL-4B-Q4 | 3.5GB |
| System overhead | 2GB |
| Headroom | 2.5GB |
| **Total** | 12GB (exactly) |

### Implementation
```python
class MultimodalBrain:
    def __init__(self):
        self.text_model = "qwen2.5-coder-7b-q4_k_m"
        self.vision_model = "qwen3-vl-4b-q4"
    
    async def process_image(self, image_path, query):
        # Step 1: Vision model describes image
        description = await self.vision_model.describe(image_path)
        
        # Step 2: Text model reasons about description + query
        context = f"Image shows: {description}\n\nUser asks: {query}"
        return await self.text_model.chat([{"role": "user", "content": context}])
```

---

## Dependencies

```
Phase 1 (RAG)     → No dependencies, can start now
Phase 2 (Tools)   → Requires Phase 1 (search_knowledge tool)
Phase 3 (Quant)   ✅ Already done!
Phase 4 (ReAct)   → Requires Phase 2 (tool execution)
Phase 5 (Vision)  → Requires Phase 2 (tool calling framework)
```

---

## Priority Order

1. **NOW**: Enhance RAG integration in brain.py
2. **NEXT**: Add native tool calling
3. **SOON**: Implement ReAct pattern
4. **LATER**: Add multimodal vision

---

## Risk Mitigation

| Risk | Mitigation |
|------|-------------|
| VRAM exhaustion | Use 7B models, implement auto-unload |
| Tool calls fail | Add retry logic + fallback to text-only |
| RAG retrieval slow | Use CPU-based Chroma, async embedding |
| Model quality loss | Stick with Q4_K_M (already tested) |

---

Last Updated: 2026-04-12
# BULLETPROOF LOCAL LLM ENGINE - MASTER PLAN

**Target**: RTX 3080 Ti (12GB VRAM)  
**Goal**: Unified, bulletproof module for all local LLM needs (loading, swapping, training, routing)

---

## EXECUTIVE SUMMARY

Create `ModelOrchestrator` - a unified module that wraps and enhances everything we have:
- **Direct GGUF** → No network overhead (llama-cpp-python direct)
- **Hot-swap** → Models + LoRA adapters without restart
- **Auto-routing** → Complexity-based + task-based + remote fallback
- **Training** → Rosetta Stone Trainer integrated
- **Bleeding-edge** → All optimization flags

---

## CURRENT STATE

### ✅ Already Working
| Component | Location | Status |
|-----------|----------|--------|
| Direct GGUF Client | `frankenstein_engine/engine/` | Direct llama-cpp-python |
| RouterBrain | `frankenstein_engine/router/` | Complexity-based routing |
| Adapter Registry | `frankenstein_engine/adapters/` | LoRA registry (rosetta-lora, etc) |
| Health Monitor | `frankenstein_engine/health/` | GPU/system/slot monitoring |
| Trainer Module | `frankenstein_engine/trainer/` | Data generation (823 lines) |
| GGUF Server | Port 8088 | Running, optimized |

### ⚠️ Needs Unification
| Component | Duplicate In | Issue |
|-----------|-------------|-------|
| Router logic | frankenstein_engine + packages/local_llm | Two implementations |
| HTTP Server | packages/local_llm/llama_server.py | Redundant with 8088 |
| Training | rosetta-stone-trainer/ (external) | Not integrated |
| Model management | DirectLlamaClient only | No hot-swap API |

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                     MODEL ORCHESTRATOR                          │
│                    (Single Entry Point)                         │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐
│  RequestRouter  │  │ AdapterRegistry│  │    ModelManager         │
│                 │  │                 │  │                         │
│ • Complexity    │  │ • discover()    │  │ • load_model()          │
│   (RouterBrain)│  │ • load()        │  │ • swap_model() (hot)   │
│                 │  │ • unload()      │  │ • generate() (direct) │
│ • Task          │  │ • hot-swap      │  │ • HTTP fallback        │
│   (consolidated)│  │                 │  │                         │
│                 │  │ [rosetta-lora] │  │ DirectLlamaClient      │
│ • Remote/Local │  │ [fast-explore] │  │ (llama-cpp-python)      │
│   decision      │  │ [benchmark]    │  │                         │
└────────┬────────┘  └────────┬────────┘  └───────────┬──────────┘
         │                    │                       │
         │              ┌─────┴─────┐            ┌────┴─────┐
         │              ▼           ▼            ▼          ▼
         │       ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐
         │       │ LoRA     │ │ LoRA     │ │  GGUF  │ │  GGUF  │
         │       │ Adapter  │ │ Adapter  │ │ Model  │ │ Model  │
         │       │ .safetensors │ │ .safetensors│ │ 0.5B  │ │  7B   │
         │       └──────────┘ └──────────┘ └────────┘ └────────┘
         │                                                 │
         ▼                                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RTX 3080 Ti (12GB VRAM)                   │
│              Optimized: -ngl 99 --flash-attn on                │
└─────────────────────────────────────────────────────────────────┘
```

---

## PHASE 1: FOUNDATION (Day 1)

### 1.1 Create Module Structure
```
packages/model_orchestrator/
├── __init__.py          # Public API: get_orchestrator()
├── orchestrator.py      # Main ModelOrchestrator class
├── config.py            # Unified config (merge existing)
├── model_manager.py     # GGUF loading, hot-swap, HTTP fallback
├── adapter_registry.py  # LoRA hot-swap
├── request_router.py    # Consolidated routing
├── training.py          # Rosetta integration
└── mcp_tools.py         # MCP tool exposure
```

### 1.2 Implement ModelManager
```python
class ModelManager:
    """Direct GGUF - no network overhead"""
    
    # Wraps DirectLlamaClient
    # GPU: -ngl 99, --flash-attn on, -ctk q4_0 -ctv q4_0
    # Context: 32768 (was 8192)
    # Threads: 16 (for 7800X3D)
    # Batch: 4096
    
    def load_model(self, model: str, adapter: str = None):
        """Load GGUF + optional LoRA"""
        
    def swap_model(self, new_model: str):
        """Hot-swap without restart"""
        
    def generate(self, prompt: str) -> str:
        """Direct llama-cpp-python, no HTTP"""
        
    def http_fallback(self, prompt: str) -> str:
        """If direct fails → localhost:8088"""
```

### 1.3 Implement AdapterRegistry
```python
class AdapterRegistry:
    """Hot-swappable LoRA adapters"""
    
    # Adapters discovered in: models/rosetta-lora*/
    # Current: rosetta-lora, fast-explore-lora, benchmark-lora
    # Hot-swap without model reload
    
    ADAPTERS = {
        "rosetta-lora": "rosetta-lora.gguf",
        "fast-explore-lora": "fast-explore-lora.gguf",
        "benchmark-lora": "benchmark-lora.gguf",
    }
    
    def load(self, name: str, scale: float = 1.0):
        """Hot-swap adapter"""
        
    def unload(self):
        """Remove current adapter"""
```

---

## PHASE 2: ROUTING (Day 1-2)

### 2.1 Consolidate RequestRouter
```python
class RequestRouter:
    """Consolidated from: RouterBrain + packages/local_llm/router.py"""
    
    # 1. Complexity analysis (from RouterBrain)
    #    - simple: <100 chars → qwen2.5-0.5b
    #    - medium: 100-500 chars → qwen2.5-coder-7b
    #    - complex: >500 chars → remote API or 7b
    
    # 2. Task classification (from ModelRouter)
    #    - coding, reasoning, creative, math, analysis
    
    # 3. Remote fallback decision
    #    - If complexity=complex → try remote
    #    - If VRAM < 2GB → remote
    
    def route(self, prompt: str) -> RoutingDecision:
        """Returns: {model, method, adapter, complexity}"""
```

### 2.2 Integrate with N-Xyme MIND MCP
```python
# MCP tools exposed:
# - orchestrator_generate(prompt, adapter=None) -> response
# - orchestrator_route(prompt) -> routing_decision
# - orchestrator_set_adapter(name, scale=1.0)
# - orchestrator_list_adapters() -> [names]
# - orchestrator_set_model(model_name)
# - orchestrator_train(tools="all", epochs=3) -> adapter_path
# - orchestrator_health() -> {gpu, vram, model, adapter}
```

---

## PHASE 3: TRAINING INTEGRATION (Day 2)

### 3.1 Integrate Rosetta Stone Trainer
```
Copy/link rosetta-stone-trainer/ → packages/model_orchestrator/training/
```

### 3.2 Training API
```python
class TrainingWrapper:
    """Wrapper around Rosetta Stone Trainer"""
    
    def train(self, adapter_name: str, tools: List[str] = None, epochs: int = 3):
        """Train LoRA via Unsloth (2x faster)"""
        # Uses: datasets/trainer_all.jsonl (435 examples, 57 tools)
        # Output: models/rosetta-lora*/
        
    def generate_data(self, tools: List[str], variations: int = 10):
        """Generate training data"""
        
    def evaluate(self, adapter_name: str, test_data: str):
        """Evaluate trained adapter"""
```

### 3.3 Auto-Training on MCP Calls (Future)
```python
# Pattern: Track MCP call patterns → auto-generate training data
# Hook: After N similar MCP calls → suggest/update adapter
```

---

## PHASE 4: OPTIMIZATION (Day 2-3)

### 4.1 GGUF Server Optimization
```bash
# Current (working):
-c 32768 -np 4 -ngl 99 --flash-attn on -t 16

# For 12GB VRAM - maximum throughput:
-c 32768 -np 4 -ngl 99 \
  --flash-attn on \
  --flash-attn-type 2 \
  -ctk q4_0 -ctv q4_0 \
  -t 16 \
  --no-mmap \
  --prerelease on
```

### 4.2 Benchmark Suite
```python
# Compare:
# 1. Direct llama-cpp-python vs localhost:8088 (HTTP)
# 2. With/without LoRA adapter
# 3. 0.5B vs 7B model
# 4. Different context sizes
```

---

## PHASE 5: MCP INTEGRATION (Day 3)

### 5.1 Tool Exposure
```python
# In N-Xyme MIND MCP servers - add:
@tool
async def orchestrate_generate(
    prompt: str,
    adapter: str = None,
    model: str = None
) -> str:
    orchestrator = get_orchestrator()
    return await orchestrator.generate(prompt, adapter=adapter, model=model)

@tool
async def orchestrate_route(prompt: str) -> dict:
    return get_orchestrator().route(prompt)
```

### 5.2 Health Monitoring
```python
@tool
async def orchestrator_health() -> dict:
    """GPU, VRAM, model, adapter, server status"""
    return {
        "gpu_temp": 65,
        "vram_used_mb": 8192,
        "vram_available_mb": 4608,
        "model": "qwen2.5-coder-7b-q4_k_m",
        "adapter": "rosetta-lora",
        "server_port": 8088,
        "direct_mode": True
    }
```

---

## IMPLEMENTATION CHECKLIST

### Week 1: Core
- [ ] Create `packages/model_orchestrator/` directory
- [ ] Implement ModelManager (direct GGUF, hot-swap)
- [ ] Implement AdapterRegistry (LoRA hot-swap)
- [ ] Test: Load 7B model + rosetta-lora adapter
- [ ] Benchmark: Direct vs HTTP (should be 14x faster)

### Week 2: Routing
- [ ] Implement RequestRouter (consolidate logic)
- [ ] Add complexity-based model selection
- [ ] Add task-based adapter selection
- [ ] Add remote fallback decision
- [ ] Test: Route various prompts

### Week 3: Training
- [ ] Copy Rosetta Stone Trainer into module
- [ ] Implement TrainingWrapper
- [ ] Test: Train new adapter on memory tools
- [ ] Test: Evaluate adapter accuracy

### Week 4: Integration
- [ ] Add MCP tool exposure
- [ ] Add health monitoring
- [ ] Add to N-Xyme MIND startup
- [ ] Full integration test

---

## FILES TO CREATE/MODIFY

### New Files
| File | Purpose |
|------|---------|
| `packages/model_orchestrator/__init__.py` | Public API |
| `packages/model_orchestrator/orchestrator.py` | Main class |
| `packages/model_orchestrator/model_manager.py` | GGUF management |
| `packages/model_orchestrator/adapter_registry.py` | LoRA registry |
| `packages/model_orchestrator/request_router.py` | Consolidated routing |
| `packages/model_orchestrator/training.py` | Rosetta integration |
| `packages/model_orchestrator/mcp_tools.py` | MCP exposure |

### Modify Existing
| File | Change |
|------|--------|
| `frankenstein_engine/__init__.py` | Import from new module |
| `frankenstein_engine/config.py` | Merge into unified config |
| `packages/local_llm/router.py` | Deprecate, use RequestRouter |

---

## SUCCESS METRICS

| Metric | Target |
|--------|--------|
| Direct GGUF latency | <50ms (vs 400ms Ollama) |
| Tokens/sec (0.5B) | 1,341+ |
| Tokens/sec (7B) | 471+ |
| LoRA hot-swap time | <100ms |
| Adapter accuracy | >85% tool call match |
| VRAM utilization | >90% during inference |

---

## COMMANDS

### Start Engine
```bash
# Direct mode (no HTTP)
python -c "from packages.model_orchestrator import get_orchestrator; o = get_orchestrator(); print(o.generate('Hello'))"

# With adapter
python -c "from packages.model_orchestrator import get_orchestrator; o = get_orchestrator(adapter='rosetta-lora'); print(o.generate('search memory'))"
```

### Train Adapter
```bash
python -m packages.model_orchestrator.training train \
  --adapter new-lora \
  --tools memory,filesystem \
  --epochs 3
```

### Health Check
```bash
python -m packages.model_orchestrator health
# Returns: {gpu, vram, model, adapter, status}
```

---

## DEPENDENCIES

```python
# requirements.txt
llama-cpp-python>=0.2.0
torch>=2.5.0
transformers>=4.40.0
unsloth>=2026.1.0
peft>=0.13.0
trl>=0.10.0
datasets>=2.18.0
accelerate>=0.30.0
pydantic>=2.0
pydantic-settings>=2.0
```

---

## Rollout Strategy

1. **MVP** (Day 1): ModelManager + AdapterRegistry → Direct GGUF works
2. **v1.0** (Day 3): + RequestRouter → Auto-routing works
3. **v1.1** (Day 5): + Training → Can train new adapters
4. **v2.0** (Day 7): + MCP + Health → Production ready
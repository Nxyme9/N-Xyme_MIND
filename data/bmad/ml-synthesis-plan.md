# N-Xyme MIND — ML Synthesis Plan
## Bleeding Edge Refinement from Archive → Root
## Date: 2026-05-17 | Synthesized from 6 parallel archive audits

---

## 📊 WHAT WE HAVE (Complete Inventory)

### 1. MODELS & WEIGHTS
| Asset | Size | Location | Status |
|-------|------|----------|--------|
| Qwen2.5 0.5B/1.5B GGUF | 380M/941M | archive/.archive/ | ✅ Exists |
| Rosetta LoRA checkpoints | 40+ runs | archive/nx_trainer/outputs/ | ✅ Exists |
| Whisper models (tiny→large) | Various | archive/.archive/whisper.cpp/ | ✅ Exists |
| Teacher embeddings (.npy) | ~3.5GB | archive/nx_trainer/data/ | ✅ Exists |
| Model weights (.safetensors) | ~6.3GB | LLMs/by-type/training/ | ✅ Exists |

### 2. LEARNING ENGINE (73 files, ~26,500 lines)
| Module | Lines | Key Classes | Status |
|--------|-------|-------------|--------|
| `rl/q_learning.py` | 665 | QLearningEngine, QState | Archive only |
| `rl/double_dqn.py` | 805 | DoubleDQN, PrioritizedReplayBuffer | Archive only |
| `rl/bandits.py` | 129 | EpsilonGreedy, UCB1 | Archive only |
| `rl/thompson_sampling.py` | 737 | ThompsonSamplingEngine | Archive only |
| `self_learning.py` | 735 | SelfLearningEngine, OutcomeTracker | Archive only |
| `advanced_learning.py` | 751 | AdvancedLearningEngine, MetaLearner | Archive only |
| `sica_style.py` | 624 | SICAEngine, SelfAuditor | Archive only |
| `prompt_evolution.py` | 677 | PromptWizard, CritiqueAgent | Archive only |
| `memory_bridge.py` | 806 | MemoryBridge, sync_to_memory | Archive only |
| `cross_session_transfer.py` | 435 | CrossSessionTransfer | Archive only |

### 3. MEMORY CORE (72 files, ~25,000 lines)
| Module | Lines | Key Classes | Status |
|--------|-------|-------------|--------|
| `tier_manager.py` | - | MemoryTierManager | Archive only |
| `reranker.py` | 84 | Reranker (cross-encoder) | Archive only |
| `semantic_cache.py` | - | SemanticCache | Archive only |
| `sleep_engine.py` | 388 | SleepEngine, process_during_sleep | Archive only |
| `self_healer.py` | - | SelfHealer | Archive only |
| `cognitive/forgetting.py` | 371 | ForgettingEngine, Ebbinghaus | Archive only |
| `cognitive/trust.py` | 258 | TrustCalculator | Archive only |
| `cognitive/priority.py` | 611 | PriorityEngine | Archive only |
| `stores/vector_store.py` | 1053 | VectorStore (FAISS) | Archive only |
| `stores/graph_store.py` | 1412 | GraphStore (NetworkX/Neo4j) | Archive only |

### 4. INTELLIGENCE (68 files, ~22,500 lines)
| Module | Lines | Key Classes | Status |
|--------|-------|-------------|--------|
| `intent_predictor.py` | 298 | IntentPredictor | Archive only |
| `predictive_router.py` | 177 | PredictiveRouter | Archive only |
| `delegation_learner.py` | 357 | DelegationLearner | Archive only |
| `agent_optimizer.py` | 423 | AgentOptimizer | Archive only |
| `realtime_learner.py` | 152 | RealTimeLearner | Archive only |
| `context_manager.py` | 409 | ContextManager, optimize_context | Archive only |
| `circuit_breaker.py` | 364 | CircuitBreaker (state machine) | Archive only |
| `load_balancer.py` | 418 | PredictiveLoadBalancer | Archive only |

### 5. TRAINING DATA
| Asset | Size | Count | Status |
|-------|------|-------|--------|
| `train.jsonl` | 1.79MB | 575 | ✅ Exists |
| `val.jsonl` | 206KB | 71 | ✅ Exists |
| `test.jsonl` | 229KB | 73 | ✅ Exists |
| `by-category/` | - | 8 categories | ✅ Exists |
| Transcripts | - | ~80+ JSONL files | ✅ Exists |
| 78-tool datasets | - | 3 generation scripts | ✅ Exists |

### 6. VECTOR STORES
| Asset | Size | Type | Status |
|-------|------|------|--------|
| ChromaDB `chroma.sqlite3` | 19.69GB | HNSW index | ✅ Exists |
| ChromaDB `data_level0.bin` | 2.55GB | Vector data | ✅ Exists |
| FAISS `index.faiss` | 110KB | Project index | ✅ Exists |
| FAISS `intent_vectors/` | 124KB | Intent index | ✅ Exists |
| LanceDB `memories.lance` | 292KB | Active store | ✅ Exists |
| SQLite databases | ~800MB | 60+ files | ✅ Exists |

### 7. C++ INFERENCE ENGINE
| Asset | Size | Features | Status |
|-------|------|----------|--------|
| `engine.cpp` | 502 lines | GGUF, CUDA, Flash Attention, KV cache quant | ✅ Compiled |
| `fused_ops.cu` | 52 lines | Normalize + Matryoshka + cosine | ✅ Compiled |
| llama.cpp archive | ~200+ .cu files | Full CUDA backend | Reference only |
| whisper.cpp archive | ~200+ .cu files | Full CUDA backend | Reference only |

**Benchmarks:** 7B model: 107-127 t/s (97% GPU util), 0.5B: 594-1,341 t/s

---

## 🔍 BLEEDING EDGE vs LEGACY

### Bleeding Edge (Keep & Synthesize)
| Component | Why Bleeding Edge | Action |
|-----------|------------------|--------|
| **Q-Learning + Thompson Sampling** | RL-based routing with SQLite persistence | Port to Rust |
| **Double DQN** | Deep reinforcement learning for complex routing | Port to Rust + PyTorch |
| **Prompt Evolution (PromptWizard)** | Self-improving prompts via critique/evaluation | Port to Python |
| **Cross-Session Transfer** | Knowledge transfer across sessions | Port to Rust |
| **Cognitive Models** | Ebbinghaus forgetting, trust, priority, reconsolidation | Port to Rust |
| **Sleep Engine** | Memory consolidation during idle | Port to Rust |
| **Circuit Breaker** | State machine for resilience | Port to Rust |
| **Fused CUDA Kernels** | Normalize + Matryoshka + cosine in one kernel | Keep as-is |
| **GGUF Inference Engine** | Dynamic batching, Flash Attention, KV quant | Keep as-is |
| **Agent Optimizer** | Per-task-type agent performance tracking | Port to Rust |
| **Delegation Learner** | Track agent performance, A/B testing | Port to Rust |
| **Intent Predictor** | Predict user intent from partial input | Port to Rust |

### Legacy (Archive/Deprecate)
| Component | Why Legacy | Action |
|-----------|-----------|--------|
| **llama.cpp full source** | Reference only, use whisper.cpp upstream | Archive |
| **whisper.cpp full source** | Reference only, use upstream | Archive |
| **40+ training script versions** | v2-v42, most are duplicates | Keep only v42 + v36_cont |
| **Deprecated Athena packages** | Old architecture | Archive |
| **Deprecated memory_store** | Replaced by memory_core | Archive |
| **IK llama.cpp variant** | Fork with no unique value | Archive |

### Missing (Need to Build)
| Component | Why Missing | Priority |
|-----------|------------|----------|
| **Rust port of learning engine** | All Python, no Rust integration | CRITICAL |
| **ChromaDB connector for nx_agents** | 27GB sitting idle | CRITICAL |
| **Session resume with memory restore** | Sessions start blank | CRITICAL |
| **Auto-injection of relevant memories** | Manual calls only | HIGH |
| **Cross-agent memory sharing** | Agents isolated | HIGH |
| **Training trigger pipeline** | Corrections never trigger retraining | HIGH |
| **RL-based routing in active system** | Uses TF-IDF only | MEDIUM |
| **A/B testing framework** | No routing accuracy measurement | MEDIUM |
| **Memory health monitoring** | Code exists but not running | MEDIUM |
| **VRAM management** | No GPU memory monitoring | LOW |

---

## 🎯 HIGHEST ROI IMPROVEMENTS

### Tier 1: Immediate ROI (<1 week each)
| Improvement | ROI | Effort | Impact |
|-------------|-----|--------|--------|
| **Delete meta-observer.js** | Eliminates system crash risk | 1h | CATASTROPHIC prevention |
| **Port circuit_breaker.py to Rust** | Prevents plugin cascade failures | 4h | System resilience |
| **Connect ChromaDB to nx_agents** | Unlocks 27GB of pre-computed vectors | 8h | Massive memory access |
| **Port intent_predictor.py to Rust** | Better tool routing from partial input | 6h | +20% routing accuracy |
| **Port delegation_learner.py to Rust** | Learn which agent handles what best | 6h | +15% delegation accuracy |

### Tier 2: High ROI (1-2 weeks each)
| Improvement | ROI | Effort | Impact |
|-------------|-----|--------|--------|
| **Port Q-Learning to Rust** | RL-based routing optimization | 12h | Self-improving routing |
| **Port cognitive models to Rust** | Forgetting, trust, priority | 10h | Smarter memory management |
| **Build session resume** | Agents start with past context | 8h | No more blank slate |
| **Auto-inject memories** | Relevant context before tool calls | 6h | Better tool execution |
| **Port agent_optimizer.py to Rust** | Track agent performance per task | 6h | Better agent selection |

### Tier 3: Strategic ROI (2-4 weeks each)
| Improvement | ROI | Effort | Impact |
|-------------|-----|--------|--------|
| **Port Double DQN to Rust+PyTorch** | Complex routing optimization | 20h | State-of-the-art routing |
| **Port PromptWizard to Python** | Self-improving prompts | 12h | Better prompt quality |
| **Build training trigger pipeline** | Corrections → retraining | 10h | Self-improving system |
| **Build A/B testing framework** | Measure routing accuracy | 8h | Data-driven optimization |
| **Port sleep_engine to Rust** | Memory consolidation during idle | 8h | Better long-term memory |

---

## 🏗️ SYNTHESIS PLAN: Archive → Root

### Phase 0: Foundation (Week 1)
**Goal:** Clean up, verify, prepare

| Task | Effort | Output |
|------|--------|--------|
| Delete meta-observer.js | 1h | System safe |
| Map archive structure | 2h | Complete inventory |
| Verify ChromaDB connectivity | 2h | Connection test |
| Verify nx_agents health | 1h | Health check |
| Create `ml/` directory in root | 1h | Structure ready |

### Phase 1: Port Core Learning Engine (Week 2-3)
**Goal:** Rust port of critical Python modules

| Task | Effort | Output |
|------|--------|--------|
| Port circuit_breaker.py | 4h | `ml/circuit_breaker.rs` |
| Port intent_predictor.py | 6h | `ml/intent_predictor.rs` |
| Port delegation_learner.py | 6h | `ml/delegation_learner.rs` |
| Port agent_optimizer.py | 6h | `ml/agent_optimizer.rs` |
| Port Q-Learning | 12h | `ml/q_learning.rs` |
| Integrate with nx_agents MCP | 8h | Working ML pipeline |

**Total:** 42 hours

### Phase 2: Port Memory & Cognitive (Week 4-5)
**Goal:** Rust port of memory management

| Task | Effort | Output |
|------|--------|--------|
| Port tier_manager.py | 6h | `ml/tier_manager.rs` |
| Port cognitive/forgetting.py | 6h | `ml/forgetting.rs` |
| Port cognitive/trust.py | 4h | `ml/trust.rs` |
| Port cognitive/priority.py | 6h | `ml/priority.rs` |
| Port sleep_engine.py | 8h | `ml/sleep_engine.rs` |
| Connect ChromaDB | 8h | `ml/chroma_connector.rs` |
| Build session resume | 8h | Session restore working |

**Total:** 46 hours

### Phase 3: Port Intelligence & Routing (Week 6-7)
**Goal:** Rust port of routing intelligence

| Task | Effort | Output |
|------|--------|--------|
| Port predictive_router.py | 6h | `ml/predictive_router.rs` |
| Port context_manager.py | 6h | `ml/context_manager.rs` |
| Port load_balancer.py | 6h | `ml/load_balancer.rs` |
| Port ab_testing.py | 8h | `ml/ab_testing.rs` |
| Build training trigger | 10h | `ml/training_trigger.rs` |
| Auto-inject memories | 6h | Working auto-injection |

**Total:** 42 hours

### Phase 4: Advanced ML (Week 8-10)
**Goal:** State-of-the-art ML integration

| Task | Effort | Output |
|------|--------|--------|
| Port Double DQN | 20h | `ml/double_dqn.rs` + PyTorch |
| Port PromptWizard | 12h | `ml/prompt_evolution.py` |
| Port Thompson Sampling | 8h | `ml/thompson_sampling.rs` |
| Build A/B testing | 8h | Routing accuracy measurement |
| Build health monitoring | 6h | `ml/health_monitor.rs` |
| VRAM management | 6h | GPU memory monitoring |

**Total:** 60 hours

**Grand Total:** 190 hours (~6.5 weeks at 30h/week)

---

## 📊 EXPECTED OUTCOMES

| Metric | Current | After Synthesis | Improvement |
|--------|---------|-----------------|-------------|
| Routing accuracy | TF-IDF baseline | +20-30% (RL-based) | 20-30% |
| Session startup | Blank slate | Past context restored | 100% |
| Memory injection | Manual only | Auto before tool calls | 100% |
| Plugin resilience | System crash | Circuit breaker isolation | 100% |
| Agent selection | Static | Learned from outcomes | +15% |
| Training loop | Never runs | Auto-trigger at 100 corrections | 100% |
| Memory management | Static | Cognitive models (forgetting, trust) | Smarter |
| Routing measurement | None | A/B testing framework | Data-driven |

---

## 🚀 QUICK START (First 48 Hours)

1. **Delete meta-observer.js** (1h)
   ```bash
   rm "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.opencode/plugins/meta-observer.jsbroken"
   ```

2. **Create ml/ directory structure** (1h)
   ```bash
   mkdir -p /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/ml/{src,tests,docs}
   ```

3. **Verify ChromaDB connectivity** (2h)
   ```python
   import chromadb
   client = chromadb.PersistentClient(path="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/archive/data_chaos/data_chaos/context/memory/file_chroma")
   collections = client.list_collections()
   print(f"Found {len(collections)} collections")
   ```

4. **Port circuit_breaker.py to Rust** (4h)
   - Copy logic from archive
   - Adapt to Rust patterns
   - Integrate with nx_agents MCP

5. **Test circuit breaker** (2h)
   - Simulate plugin failure
   - Verify system continues operating

---

*This plan synthesizes everything from the 6 parallel archive audits: 73 learning engine files, 72 memory core files, 68 intelligence files, 18 training files, 27GB ChromaDB, 60+ SQLite databases, C++ inference engine, and 40+ training runs.*

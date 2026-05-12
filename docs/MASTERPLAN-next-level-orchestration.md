# 🚀 N-Xyme MASTERPLAN — Next-Level AI Orchestration

> **Generated**: 2026-04-12  
> **Updated**: 2026-04-12 (Round 3: Revised based on Momus/Metis/Oracle review)
> **Note**: Phase 1.3 TTL and Phase 2 fingerprinting tools ALREADY IMPLEMENTED - revised to focus on activation
> **Source**: Deep dive research (explore + librarian + oracle agents)  
> **Goal**: Transform N-Xyme into a cutting-edge self-improving personal external brain

---

## 📊 EXECUTIVE SUMMARY

| Current State | Target State |
|---------------|---------------|
| 45+ tools, reactive routing | Predictive cognitive orchestration |
| Memory exists but underutilized | Contextual memory with injection |
| Static agents | Self-modifying agents |
| Manual tool calling | Tool-CallingLM composite sequences |
| Fixed orchestration topology | Emergent self-organizing hierarchy |

**Key Insight**: 57% of enterprise agent failures come from poor orchestration, not weak models. N-Xyme has strong models (minimax, qwen) — now we optimize the wiring.

**Bleeding Edge Insight** (2025-2026): "When LLM capabilities converge, the orchestration topology becomes the dominant lever for system performance." — AdaptOrch

---

## 🔬 RESEARCH FINDINGS SYNTHESIS

### Current N-Xyme Patterns (In Codebase)

| Pattern | Location | Status |
|---------|----------|--------|
| Q-Learning Routing | `learning_engine/rl/q_learning.py` | ✅ Active |
| Contextual Bandits | `learning_engine/meta/strategy_selector.py` | ✅ Implemented |
| Agent Handoffs | `orchestration/handoff.py` | ✅ OpenAI SDK-style |
| Circuit Breakers | `learning_engine/routing/adaptive_router.py` | ✅ Active |
| Task Lifecycle | `orchestration/tasks/lifecycle.py` | ✅ State machine |
| Pattern Learning | `orchestration/pattern_learning.py` | ✅ User actions |

### Industry Best Practices (2025-2026)

| Pattern | Source | Benefit |
|---------|--------|---------|
| LangGraph + LangChain | LMSYS, enterprise | Checkpointing, time-travel |
| RouteLLM | ICLR 2025 | 85% cost reduction |
| Model Tiering | Azure, OpenRouter | 90% cost reduction |
| Supervisor Pattern | Anthropic research | Best for decomposition |
| Reflection Loops | Reflexion, STaR | Self-correction without training |
| Tool Graph Composition | AutoGen, CrewAI | Composite actions |

---

## 🎯 MASTERPLAN: 5 PHASES (REVISED - Round 3)

### PHASE 1: MEMORY ACTIVATION (Quick Win — 1 Day)

**Goal**: Make memory contextual instead of passive

**Key Discovery**: TTL (Step 1.3) already implemented in `cognitive/forgetting.py`. Session fingerprinting tools (Phase 2) already exist in `nx_brain_mcp/__init__.py`. Focus on INTEGRATION not building.

**Delegation Pattern**: Sisyphus → Hephaestus (implement) → Oracle (review)

| Step | Action | File | Tool/Agent | Status |
|------|--------|------|------------|--------|
| 1.1 | Add auto-write to memory after each task completion | `nx_brain_mcp/__init__.py` | Hephaestus | ⏳ NEW |
| 1.2 | Implement importance scoring (success × recency × similarity) | New: `orchestration/memory_ranker.py` | Hephaestus | ⏳ NEW |
| ~~1.3~~ | ~~Add TTL for memories (30 days default)~~ | ~~REMOVED - already in `cognitive/forgetting.py`~~ | ~~-~~ | ✅ DONE |
| 1.4 | **Pre-agent memory injector** with token budget (max 500 tokens) | New: `orchestration/memory_injector.py` | Hephaestus | ⏳ NEW |
| 1.5 | Activate existing fingerprint tools in orchestration flow | `orchestration/fingerprint_activator.py` | Hephaestus | ⏳ NEW |
| 1.6 | Test memory activation | Verify with `memory_get_memory_stats` | Sisyphus | ⏳ TEST |

**Token Budget (NEW)**:
- Memory injection: max 500 tokens per prompt
- Compress/ellipsize if exceeds limit
- Priority: most recent + highest importance

**Implementation Details**:
```python
# Step 1.1: Auto-write after task completion
@mcp.tool()
def memory_auto_write(task_result: dict) -> dict:
    """Auto-write task completion to memory with importance scoring."""
    importance = task_result.get("success", False) * 1.0 + \
                 task_result.get("recency", 1.0) * 0.5 + \
                 task_result.get("similarity", 0.0) * 0.3
    return memory_write(
        content=f"Task: {task_result['task']}, Result: {task_result['outcome']}",
        kind="episodic",
        scope="global",
        metadata={"importance": importance}
    )

# Step 1.4: Pre-agent memory injector (NEW)
class PreAgentMemoryInjector:
    MAX_TOKENS = 500  # Token budget enforced
    
    def inject(agent: str, task: str) -> str:
        """Inject contextual memory BEFORE agent dispatch."""
        # 1. Search memory for relevant context
        memories = search_memories(task, limit=5)
        
        # 2. Rank by importance
        ranked = rank_memories(memories, task)
        
        # 3. Compress to token budget
        compressed = compress_to_tokens(ranked, MAX_TOKENS)
        
        return f"[CONTEXT FROM MEMORY]\n{compressed}\n[/CONTEXT]"
    
    def compress_to_tokens(memories: list, max_tokens: int) -> str:
        """Compress memories to fit token budget."""
        # Implementation: truncate, ellipsize, or summarize
```

**Success Metrics**:
- `learned_patterns` > 0 (currently 0)
- Memory queries return contextual results
- Pre-agent memory injection active with token budget enforced

---

### PHASE 2: SESSION FINGERPRINTING - ACTIVATION (Quick Win — 0.5 Day)

**Goal**: Continuity between sessions, not start fresh each time

**Key Discovery**: Session fingerprinting tools ALREADY EXIST in `nx_brain_mcp/__init__.py`:
- `fingerprint_get_session_context()` - line 1043
- `fingerprint_record_pattern()` - line 1069
- `fingerprint_get_user_preferences()` - line 1105

**REVISED**: Focus on INTEGRATION/ACTIVATION, not building new tools.

| Step | Action | File | Tool/Agent | Status |
|------|--------|------|------------|--------|
| ~~2.1~~ | ~~Explore existing session patterns~~ | ~~REMOVED - already explored~~ | ~~-~~ | ✅ DONE |
| ~~2.2~~ | ~~Create session fingerprint~~ | ~~REMOVED - tools exist in nx_brain_mcp~~ | ~~-~~ | ✅ DONE |
| 2.3 | **Connect fingerprint tools to orchestration flow** | `orchestration/fingerprint_activator.py` | Hephaestus | ⏳ NEW |
| 2.4 | Auto-inject fingerprint into agent prompts | `orchestration/agent_prompt.py` | Hephaestus | ⏳ NEW |
| 2.5 | Warm session pool based on fingerprint | `session_warm_pool()` integration | Hephaestus | ⏳ NEW |
| 2.6 | Verify fingerprint persistence | Test across sessions | Sisyphus | ⏳ TEST |

**Implementation Details**:
```python
# REVISED Step 2.3: Connect existing fingerprint tools to orchestration
class FingerprintActivator:
    """Activates existing fingerprint tools in orchestration flow."""
    
    def __init__(self):
        self.fingerprint_get_session_context = fingerprint_get_session_context
        self.fingerprint_record_pattern = fingerprint_record_pattern
        self.fingerprint_get_user_preferences = fingerprint_get_user_preferences
    
    def before_task(self, current_task: str) -> dict:
        """Before agent dispatch - get relevant context from past sessions."""
        # Use existing tool: fingerprint_get_session_context
        context = self.fingerprint_get_session_context(
            current_task=current_task,
            max_sessions=3
        )
        
        # Also get user preferences
        prefs = self.fingerprint_get_user_preferences()
        
        return {
            "session_context": context.get("content", ""),
            "user_preferences": prefs,
            "sessions_found": context.get("sessions_found", 0)
        }
    
    def after_task(self, task: str, outcome: str):
        """After task completion - record pattern for learning."""
        # Use existing tool: fingerprint_record_pattern
        self.fingerprint_record_pattern(
            action_type=task,
            outcome="success" if outcome == "success" else "failed",
            context={"timestamp": now()}
        )
    
    def warm_pool_based_on_fingerprint(self, fingerprint: dict):
        """Pre-warm session pool based on user's preferred agents."""
        preferred = fingerprint.get("preferred_agents", [])
        if preferred:
            session_warm_pool(agents=preferred[:3])
```

**Existing Tools to Activate** (already in `nx_brain_mcp/__init__.py`):
```python
# These exist - just need to be connected to orchestration
fingerprint_get_session_context()  # line 1043-1065
fingerprint_record_pattern()       # line 1069-1101
fingerprint_get_user_preferences() # line 1105-1119
```

**File Structure**:
```
orchestration/
├── session_fingerprint.py  # NEW
└── __init__.py

context/
└── session.db  # NEW - SQLite
```

**Success Metrics**:
- `session_archive` > 0 (currently 0)
- Context persists across sessions
- Fingerprint injects correctly

---

### PHASE 3: TOOL-CALLING LM (Medium — 3 Days)

**Goal**: Predict composite tool sequences instead of individual calls

**Delegation Pattern**: Sisyphus → Prometheus (plan) → Hephaestus (implement) → Oracle (review)

| Step | Action | File | Tool/Agent |
|------|--------|------|------------|
| 3.1 | Log 500+ tool sequences with outcomes | `learning_engine/outcome_logger.py` | Hephaestus |
| 3.2 | Create [task → tool_sequence] dataset | New: `datasets/tool_sequences.json` | Hephaestus |
| 3.3 | Analyze tool patterns, identify composites | Analysis script | Explore |
| 3.4 | Fine-tune Qwen2.5-Coder (7B) on sequences | New: `models/tool_calling_lm/` | Hephaestus |
| 3.5 | Replace individual calls with predicted sequences | `nx_brain_mcp/__init__.py` | Hephaestus |
| 3.6 | Add validation layer (schema check) | New: `orchestration/tool_validator.py` | Hephaestus |
| 3.7 | A/B test: individual vs composite | Run benchmark | Sisyphus |
| 3.8 | Oracle review: architecture soundness | Review plan vs implementation | Oracle |

**Implementation Details**:
```python
# Step 3.1: Enhanced outcome logger
class ToolSequenceLogger:
    def log_sequence(task: str, tools: list[dict], outcome: str):
        # Log: task_description, [tool1, tool2, ...], outcome, timestamp
        # Store in: datasets/tool_sequences.json
        
    def extract_composites():
        # Find patterns: [search → read → edit] = "code modification"
        # Cluster into composite actions
        
# Step 3.5: Composite tool predictor
class CompositePredictor:
    def predict(task: str) -> list[dict]:
        # Input: task description
        # Output: predicted tool sequence
        # Use fine-tuned model or pattern matching
        
    def validate(sequence: list[dict]) -> bool:
        # Schema check: each tool exists, args valid
```

**Dataset Format**:
```json
{
  "task": "add JWT auth to API",
  "sequence": [
    {"tool": "grep", "args": {"pattern": "def login"}},
    {"tool": "read", "args": {"file": "src/auth.py"}},
    {"tool": "edit", "args": {"old": "...", "new": "..."}},
    {"tool": "lsp_diagnostics", "args": {"file": "src/auth.py"}}
  ],
  "outcome": "success",
  "duration_ms": 4500
}
```

**File Structure**:
```
datasets/
└── tool_sequences.json  # NEW - 500+ sequences

models/
└── tool_calling_lm/
    ├── train.py
    ├── model/
    └── predictions.py

orchestration/
├── tool_validator.py  # NEW
└── composite_predictor.py  # NEW
```

**Expected Outcome**: 40-60% fewer round-trips

**Success Metrics**:
- Composite action usage > 50%
- Latency reduction > 30%

---

### PHASE 4: PREDICTIVE ROUTING (Medium — 2 Days)

**Goal**: Route BEFORE user finishes typing

**Delegation Pattern**: Sisyphus → Hephaestus (implement) → Explore (find embeddings) → Atlas (test)

| Step | Action | File | Tool/Agent |
|------|--------|------|------------|
| 4.1 | Explore existing embeddings in codebase | `learning_engine/embeddings/` | Explore |
| 4.2 | Build user intent vectors from history | New: `learning_engine/intent_vectors/` | Hephaestus |
| 4.3 | Track [query → agent] patterns | `learning_engine/outcome_logger.py` | Hephaestus |
| 4.4 | Implement FAISS index for similarity search | `learning_engine/embeddings/faiss_index.py` | Hephaestus |
| 4.5 | Pre-warm likely agents before submission | New: `orchestration/pre_warm.py` | Hephaestus |
| 4.6 | Add intent prediction from partial input | New: `intelligence/intent_predictor.py` | Hephaestus |
| 4.7 | Benchmark: current 1228ms vs target <300ms | Run routing benchmarks | Atlas |
| 4.8 | Verify prediction accuracy > 75% | A/B test | Sisyphus |

**Implementation Details**:
```python
# Step 4.2: Intent vector builder
class IntentVectorBuilder:
    def build_from_history():
        # Get all [query, agent] pairs from outcome_logger
        # Embed queries using sentence-transformers
        # Store vectors in FAISS index
        
    def add_query_vector(query: str, agent: str):
        # Add new query → agent mapping
        
# Step 4.5: Pre-warm agent pool
class AgentPreWarmer:
    def pre_warm(top_k: int = 3):
        # Get top-k likely agents from IntentVectorBuilder
        # Call session_get() for each to warm pool
        # Result: agents ready before user submits
        
# Step 4.6: Partial input predictor
class IntentPredictor:
    def predict(partial_input: str) -> list[str]:
        # Input: "add JWT" → Output: ["hephaestus", "explore"]
        # Use fuzzy matching + vector similarity
```

**File Structure**:
```
learning_engine/
└── intent_vectors/
    ├── index.faiss
    ├── metadata.json
    └── builder.py

intelligence/
└── intent_predictor.py  # NEW

orchestration/
└── pre_warm.py  # NEW
```

**Expected Outcome**: Sub-300ms routing vs current 1228ms

**Success Metrics**:
- Routing latency < 300ms
- Prediction accuracy > 75%

---

### PHASE 5: SELF-MODIFYING AGENTS (Large — 5+ Days)

**Goal**: Agents that learn from outcomes and adapt

**Delegation Pattern**: Sisyphus → Prometheus (plan) → Hephaestus (implement) → Oracle (review) → Momus (red-team)

| Step | Action | File | Tool/Agent |
|------|--------|------|------------|
| 5.1 | Implement failure pattern extraction | `learning_engine/self_learning.py` | Hephaestus |
| 5.2 | Add agent reflection on failure (Stuck Protocol → auto) | New: `orchestration/auto_reflection.py` | Hephaestus |
| 5.3 | Implement DAG-Shapley attribution | New: `orchestration/contribution_analyzer.py` | Hephaestus |
| 5.4 | Add dynamic role synthesis (P1 from Oracle) | New: `orchestration/role_synthesizer.py` | Hephaestus |
| 5.5 | Auto-simplify prompts that fail 3x | New: `learning_engine/prompt_evolution.py` | Hephaestus |
| 5.6 | Agent weight auto-update based on success | `learning_engine/rl/q_learning.py` | Hephaestus |
| 5.7 | Meta-learning: agents specialize over time | New: `orchestration/agent_specialization.py` | Hephaestus |
| 5.8 | Implement belief-guided delegation (P4) | Extend: `orchestration/two_stage_router.py` | Hephaestus |
| 5.9 | Oracle review: architecture soundness | Full system review | Oracle |
| 5.10 | Momus red-team: find gaps | Adversarial testing | Momus |
| 5.11 | Iterate on self-modification logic | Based on Momus feedback | Hephaestus |

**Implementation Details**:
```python
# Step 5.1: Failure pattern extraction
class FailureExtractor:
    def extract_patterns():
        # Get all failed outcomes from learning_engine
        # Cluster by: error_type, agent, task_type
        # Extract: "hephaestus fails on regex tasks 3x"
        
    def get_recommendations(pattern: dict) -> list[str]:
        # Input: failure pattern
        # Output: ["use atlas instead", "simplify prompt"]

# Step 5.2: Auto-reflection (Stuck Protocol → automatic)
class AutoReflector:
    def reflect(failure: dict) -> dict:
        # 1. What I tried: failure['attempted']
        # 2. What failed: failure['error']
        # 3. Why it failed: root_cause_analysis()
        # 4. What I'll do differently: get_alternative_approach()

# Step 5.3: DAG-Shapley attribution
class ContributionAnalyzer:
    def compute_shapley(task_id: str, agent_ids: list[str]) -> dict:
        # Input: multi-agent task, list of agents
        # Output: {agent_id: contribution_score}
        # Use DAG-Shapley approximation (not full - expensive)
        
# Step 5.4: Dynamic role synthesis (Oracle P1)
class RoleSynthesizer:
    def synthesize_role(task: str, feedback: dict) -> RoleSpec:
        # Input: task description, execution feedback
        # Output: modified role prompt
        # Example: "hephaestus for code" → "hephaestus-code-v2: prefers regex solutions"
        
# Step 5.5: Prompt evolution
class PromptEvolver:
    def evolve(agent: str, failures: list[dict]) -> str:
        # Input: agent name, list of failures
        # Output: evolved prompt
        # Logic: simplify if >3 failures, add examples if unclear
        
# Step 5.8: Belief-guided delegation (Oracle P4)
class BeliefGuidedRouter:
    def __init__(self):
        self.belief_states = {}  # agent → belief distribution
        self.priors = {}  # task_type → agent probabilities
        
    def route(task: str) -> str:
        # Thompson sampling over belief states
        # Update beliefs based on outcome
```

**File Structure**:
```
learning_engine/
├── self_learning.py  # Enhance existing
├── prompt_evolution.py  # NEW
└── contribution_tracker.py  # NEW

orchestration/
├── auto_reflection.py  # NEW
├── contribution_analyzer.py  # NEW
├── role_synthesizer.py  # NEW
├── agent_specialization.py  # NEW
└── two_stage_router.py  # EXTEND
```

**Self-Modification Loop**:
```
Task → Agent → Outcome
    ↓
Failure? → Yes → Extract pattern → Auto-reflect → Evolve prompt → Retry
    ↓
No → Record success → Update weights → Continue
```

**Success Metrics**:
- Agent success rate improvement over time
- Reduced repeat failures
- Role synthesis active (>0 synthesized roles)
- Belief-guided routing active

---

## 📋 DELEGATION MATRIX BY PHASE

| Phase | Sisyphus | Prometheus | Hephaestus | Explore | Oracle | Momus |
|-------|----------|------------|------------|---------|--------|-------|
| P1 | Plan | - | Implement | - | Review | - |
| P2 | Plan | - | Implement | Find patterns | - | - |
| P3 | Plan | Plan | Implement | Analyze | Review | - |
| P4 | Plan | - | Implement | Find embeddings | - | Test |
| P5 | Plan | Plan | Implement | - | Review | Red-team |

---

## 🛠️ TOOL USAGE BY PHASE

| Phase | Primary Tools | Secondary Tools |
|-------|---------------|------------------|
| P1 | read, edit, write, lsp_diagnostics | grep, glob |
| P2 | read, edit, write, grep, glob | session_* tools |
| P3 | read, edit, write, bash (training) | grep, lsp_diagnostics |
| P4 | read, edit, write, grep | glob, bash (FAISS) |
| P5 | read, edit, write, grep | glob, lsp_diagnostics, quality gates |

---

## ✅ SUCCESS CRITERIA BY PHASE

| Phase | Metric | Current | Target | Verification |
|-------|--------|---------|--------|--------------|
| P1 | learned_patterns | 0 | >100 | `memory_get_memory_stats` |
| P2 | session_archive | 0 | >10 | `context_get_archive_context` |
| P3 | round-trips/task | 5+ | 2-3 | Benchmark |
| P4 | routing latency | 1228ms | <300ms | Timing benchmark |
| P5 | success_rate_drift | static | improving | 30-day tracking |

---

## 🏗️ ARCHITECTURE DIAGRAM

```
                    ┌─────────────────────────────────────────────┐
                    │           COGNITIVE ORCHESTRATOR            │
                    └─────────────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────┐          ┌─────────────────┐          ┌───────────────┐
│   INTENT      │          │   TOOL GRAPH    │          │   EXECUTION   │
│   PREDICTOR   │────┐     │   COMPOSER      │────┐     │   POOL        │
└───────────────┘    │     └─────────────────┘    │     └───────────────┘
        │            │              │             │              │
        │            │              │             │              │
        ▼            ▼              ▼             ▼              ▼
┌───────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐
│ Session       │  │ Contextual      │  │ OUTCOME         │  │ Circuit       │
│ Fingerprint   │  │ Memory + Ranker │  │ LOGGER + Q-LEARN│  │ Breakers      │
└───────────────┘  └─────────────────┘  └─────────────────┘  └───────────────┘
        │                             │                             │
        └─────────────────────────────┼─────────────────────────────┘
                                      ▼
                    ┌─────────────────────────────────────────────┐
                    │           SELF-LEARNING ENGINE              │
                    │  (Pattern Extraction → Agent Adaptation)   │
                    └─────────────────────────────────────────────┘
```

---

## 📈 SUCCESS METRICS BY PHASE

| Phase | Metric | Current | Target | Timeline |
|-------|--------|---------|--------|----------|
| P1: Memory | learned_patterns | 0 | >100 | Day 1 |
| P1: Memory | query feedback → patterns | 356 | patterns>100 | Day 1 |
| P2: Fingerprint | session_archive | 0 | >10 | Day 2 |
| P3: Tool-CallingLM | round-trips/task | 5+ | 2-3 | Day 3-5 |
| P4: Predictive | routing latency | 1228ms | <300ms | Day 6-7 |
| P5: Self-modify | agent success drift | static | improving | Day 8-12 |

---

## 🔧 TECHNICAL REQUIREMENTS

### Dependencies Already in Codebase
- ✅ Q-Learning (`learning_engine/rl/q_learning.py`)
- ✅ Contextual Bandits (`learning_engine/meta/strategy_selector.py`)
- ✅ Outcome Logger (`learning_engine/outcome_logger.py`)
- ✅ Memory Core (`packages/memory_core/`)
- ✅ Session Pool (`packages/session_pool_mcp/`)

### New Dependencies Needed
| Package | Purpose | Priority |
|---------|---------|----------|
| `faiss-cpu` | Vector similarity for intent prediction | P4 |
| `sentence-transformers` | User intent embeddings | P4 |
| `transformers` (existing) | Fine-tuning Tool-CallingLM | P3 |

---

## ⚡ QUICK START

```bash
# Phase 1: Memory activation (do now)
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
source .venv/bin/activate

# Test memory write integration
python3 -c "
from packages.nx_brain_mcp import memory_memory_write
result = memory_memory_write(
    content='Test: User prefers Python over JavaScript',
    kind='episodic',
    scope='global'
)
print('Memory write:', result)
"
```

---

## 📋 PRIORITY ORDER

```
IMMEDIATE (Day 1-2):
├── P1: Memory activation (high impact, low effort)
└── P2: Session fingerprinting (high impact, low effort)

SHORT-TERM (Day 3-7):
├── P3: Tool-CallingLM (high impact, medium effort)
└── P4: Predictive routing (medium impact, medium effort)

LONG-TERM (Day 8+):
└── P5: Self-modifying agents (medium impact, high effort)
```

---

## 🎯 KEY FILES TO MODIFY

| File | Changes |
|------|---------|
| `packages/nx_brain_mcp/__init__.py` | Add fingerprint tools, auto-memory |
| `packages/learning_engine/outcome_logger.py` | Add tool sequence logging |
| `packages/orchestration/agent_prompt.py` | Inject contextual memory |
| `packages/nx_context_mcp/` | Add session fingerprinting |
| `packages/memory_core/mcp_server.py` | Add TTL, ranking |

---

## 🧪 EXPERIMENTAL FEATURES (Future)

| Feature | Idea | Feasibility |
|---------|------|--------------|
| Tool-CallingLM with RLHF | Fine-tune on user corrections | Medium |
| Multi-agent debate | Agents vote on best approach | High |
| Visual planning | Graph visualization of agent flow | Low (TUI) |
| Voice input | Speech → agent routing | Low (TUI) |

---

## 🎯 BLEEDING-EDGE RESEARCH FINDINGS (Round 2 - April 2026)

### Industry Cutting-Edge (2025-2026)

| Pattern | Source | Impact |
|---------|--------|--------|
| **Self-Modifying Prompts** | MetaAgent, SICA, DPT-Agent | Agents rewrite own prompts |
| **Meta-Learning** | MetaClaw, ALMA | Learn to learn from experience |
| **Autonomous Self-Improvement** | HyperAgents, Ouroboros | Recursive metacognitive improvement |
| **Tool Creation at Runtime** | MARIA OS, Yunjue Agent | Agents build their own tools |
| **Multi-Agent Negotiation** | Dialogue Diplomats (94.2% consensus) | Consensus building |
| **System 1/System 2 Switching** | DPT-Agent, Dualformer | Fast/slow thinking modes |

### N-Xyme Current Capabilities

| Component | Implementation | Status |
|-----------|----------------|--------|
| Q-Learning Routing | `unified-mcp_learning_route_task` | ✅ Production (96.4% hephaestus) |
| Thompson Sampling | Routing decisions | ✅ Production |
| Agent Handoffs | `handoff.py` (OpenAI SDK-style) | ✅ Production |
| Circuit Breakers | `task_watchdog.py`, AGENTS.md | ✅ Production |
| Task Lifecycle | `lifecycle.py` state machine | ✅ Production |
| Pattern Learning | `pattern_learning.py` SQLite | ✅ Production |
| BMAD Workflows | 11 workflows (catalyst, recall) | ✅ Production |

### Oracle Recommendations (Prioritized)

| Priority | Feature | Impact | Effort | Timeline |
|:---------|:--------|:-------|:-------|:---------|
| **P1** | Dynamic Role Synthesis | High | Short | Week 1 |
| **P2** | DAG-Shapley Attribution | Medium | Short | Week 1 |
| **P3** | Self-Modifying Prompts | High | Medium | Week 2-3 |
| **P4** | Belief-Guided Delegation | High | Medium | Week 2-3 |
| **P5** | Emergent Hierarchy | High | Medium | Week 3-4 |
| **P6** | MAS2 Self-Generation | Very High | Large | Month 2 |

### Key Insight: Endogenous Paradox

> "Optimal coordination emerges not from maximal control or maximal autonomy, but from the hybrid Sequential protocol — balancing imposed structure with autonomous role selection."

**N-Xyme Application**: Don't choose between fixed hierarchy and pure emergence. Implement hybrid where:
- Sisyphus provides mission framing
- Agents autonomously select roles based on capability matching
- Hierarchy emerges from demonstrated competence

---

## 🛠️ IMPLEMENTATION: PHASE 0 — BASELINE (Completed)

| Step | Status |
|------|--------|
| ✅ Gap analysis: nx-brain-mcp | Done |
| ✅ Add playwright_mcp, sqlite_mcp paths | Done |
| ✅ Add Browser tools (navigate, screenshot, click, fill) | Done |
| ✅ Add SQLite tools (query, list_tables, describe_table) | Done |
| ✅ Add Session Fingerprinting tools | Done |
| ✅ Verify all brain MCP tools working | Done |

---

## 📚 REFERENCES

- **RouteLLM** (ICLR 2025): https://arxiv.org/abs/2405.13755
- **LangGraph**: https://python.langchain.com/docs/langgraph/
- **Reflexion**: Self-correction without training
- **Strategy Selector**: `learning_engine/meta/strategy_selector.py`
- **Adaptive Router**: `learning_engine/routing/adaptive_router.py`

### Bleeding-Edge Papers (2025-2026)
- **MetaAgent** (arXiv:2508.00271): Meta tool learning
- **SICA** (arXiv:2504.15228): Self-Improving Coding Agent
- **HyperAgents** (arXiv:2603.19461): Recursive metacognitive self-improvement
- **Ouroboros** (GitHub: razzant/ouroboros): Autonomous self-evolving agent
- **MARIA OS** (2026): Tool creation architecture
- **Dialogue Diplomats** (arXiv:2511.17654): Multi-agent negotiation (94.2% consensus)
- **Moltbook** (2026): AI agent societies at scale

---

*This masterplan synthesizes findings from 5 parallel research agents (explore × 2 + librarian × 2 + oracle) and aligns with 2025-2026 industry best practices.*
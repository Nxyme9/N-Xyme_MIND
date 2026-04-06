# N-Xyme MIND: Master Delegation Protocol

> **Purpose**: Individual phase plans with optimal delegation for maximum speed and accuracy
> **Philosophy**: "Delegate optimally - Sisyphus orchestrates, specialists implement"

---

## 📋 EXECUTION SUMMARY

| Phase | Tasks | Delegation Pattern | Wave | Status |
|-------|-------|-------------------|------|--------|
| **Phase 1: Core Memory** | T1-T3 | Oracle → Hephaestus | W1 | Ready |
| **Phase 2: Self-Learning** | T4-T6 | Prometheus → Hephaestus | W2 | Ready |
| **Phase 3: Memory Ops** | T7-T9 | Atlas → Hephaestus | W3 | Ready |
| **Phase 4: Integration** | T10-T12 | Hephaestus → Integration | W4 | Ready |

---

## 🎯 DELEGATION PRINCIPLES

### 1. Decision Matrix: Delegate vs Direct

| Task Type | Action | Example |
|-----------|--------|---------|
| **Architecture/design** | Delegate to **Oracle** | Memory schema, graph structure |
| **Implementation code** | Delegate to **Hephaestus** | Classes, functions, modules |
| **Planning** | Delegate to **Prometheus/Metis** | Task breakdown, gap analysis |
| **Review/adversarial** | Delegate to **Oracle + Momus** | Edge cases, security |
| **Research/exploration** | Delegate to **Explore/Librarian** | Codebase patterns, docs |
| **Trivial config** | **DO DIRECTLY** | Single line fixes, status |
| **Documentation** | **DO DIRECTLY** | README updates, comments |

### 2. Category/Skill Mapping

| Complexity | Category | Model | Use For |
|------------|----------|-------|---------|
| **Architecture** | `ultrabrain` | qwen3.6-plus-free | Memory design, schema |
| **Implementation** | `deep` | qwen3.6-plus-free | Core classes, algorithms |
| **Planning** | `routing` | minimax-m2.5-free | Task orchestration |
| **Gap Analysis** | `unspecified-high` | qwen3.6-plus-free | Pre-planning |
| **Research** | — | minimax-m2.5-free | Explore/Librarian |
| **Execution** | `quick` | minimax-m2.5-free | Atlas tasks |
| **Review** | `ultrabrain` | qwen3.6-plus-free | Momus checks |
| **Simple** | `unspecified-low` | minimax-m2.5-free | Sisyphus-Junior |

### 3. Parallelization Rules

```
WAVE STRUCTURE:
┌─────────────────────────────────────────────────────────┐
│  Wave N: [T1] [T2] [T3] ──► All parallel (max 3)      │
│    │         │        │                                 │
│    ▼         ▼        ▼                                 │
│  Verify   Verify    Verify  ──► Sequential verification │
└─────────────────────────────────────────────────────────┘

RULES:
- Never parallelize dependent tasks
- Use run_in_background=true for Explore/Librarian
- Use run_in_background=false for implementation (wait)
- Max 3 concurrent tasks per wave
```

---

## 📦 PHASE 1: Core Memory (T1-T3)

**Duration**: ~1 week
**Goal**: Build foundational memory infrastructure

### T1: Hierarchical Memory System

| Field | Value |
|-------|-------|
| **What** | 4-tier memory (Working→Episodic→Semantic→Archival) |
| **File** | `src/memory/hierarchical.py` |
| **Delegation** | Prometheus (plan) → Hephaestus (implement) |
| **Category** | `deep` + `visual-engineering` (structure) |
| **Verification** | Oracle schema review + lsp_diagnostics |
| **QA** | Create test_hierarchical.py, run pytest |

**Delegation Prompt**:
```
Implement src/memory/hierarchical.py with:
- TieredMemory class with 4 tiers
- MemoryBlock dataclass
- add(), retrieve(), evict() methods
- Follow existing patterns in src/
Use: category="deep", load_skills=[]
```

### T2: Knowledge Graph Memory

| Field | Value |
|-------|-------|
| **What** | Graph-based entities + relationships |
| **File** | `src/memory/knowledge_graph.py` |
| **Delegation** | Oracle (design) → Hephaestus (implement) |
| **Category** | `ultrabrain` (complex logic) |
| **Verification** | Momus edge case test |
| **QA** | Test entity creation, relationship queries |

**Delegation Prompt**:
```
Design and implement src/memory/knowledge_graph.py:
- GraphMemory class using NetworkX
- Entity, Relationship dataclasses
- add_entity(), add_relation(), find_path(), query()
Reference: neo4j-labs/agent-memory patterns
Use: category="ultrabrain"
```

### T3: Vector Index (Hybrid)

| Field | Value |
|-------|-------|
| **What** | Semantic search with embeddings |
| **File** | `src/memory/vector_index.py` |
| **Delegation** | Metis (gap analysis) → Hephaestus |
| **Category** | `deep` |
| **Verification** | Integration test + search verification |
| **QA** | Test cosine similarity, hybrid query |

---

## 🧠 PHASE 2: Self-Learning (T4-T6)

**Duration**: ~1 week
**Goal**: Build learning capabilities

### T4: Skill Lifecycle Manager

| Field | Value |
|-------|-------|
| **What** | Skill state machine (Proposed→Experimental→Active→Deprecated→Archived) |
| **File** | `src/learning/skill_lifecycle.py` |
| **Delegation** | Prometheus → Atlas (orchestration) |
| **Category** | `routing` |
| **Verification** | Trigger verification + log review |
| **QA** | Test state transitions, auto-promote |

### T5: Prompt Evolution Engine

| Field | Value |
|-------|-------|
| **What** | Self-evolving prompts (Generate→Critique→Refine→Evaluate) |
| **File** | `src/learning/prompt_evolution.py` |
| **Delegation** | Oracle (design) → Hephaestus |
| **Category** | `ultrabrain` |
| **Verification** | Momus adversarial prompt test |
| **QA** | Run 3 evolution cycles, verify improvement |

### T6: Self-Learning from Outcomes

| Field | Value |
|-------|-------|
| **What** | Learn from success/failure patterns |
| **File** | `src/learning/self_learning.py` |
| **Delegation** | Metis → Hephaestus |
| **Category** | `deep` |
| **Verification** | Metric validation + 3-iteration test |
| **QA** | Test pattern extraction, recommendation |

---

## ⚙️ PHASE 3: Memory Operations (T7-T9)

**Duration**: ~1 week
**Goal**: Implement memory management

### T7: Sleep-Cycle Consolidation

| Field | Value |
|-------|-------|
| **What** | JOURNAL→CONSOLIDATE→RECALL pattern |
| **File** | `src/memory/sleep_cycle.py` |
| **Delegation** | Prometheus → Atlas |
| **Category** | `deep` |
| **Verification** | Health check + state transition test |
| **QA** | Test pattern extraction, consolidation |

### T8: Forgetting Mechanism

| Field | Value |
|-------|-------|
| **What** | Ebbinghaus forgetting curve decay |
| **File** | `src/memory/forgetting.py` |
| **Delegation** | Oracle (design) → Hephaestus |
| **Category** | `deep` |
| **Verification** | Momus data loss edge case + audit log |
| **QA** | Test importance calculation, decay |

### T9: Session Compaction

| Field | Value |
|-------|-------|
| **What** | Summarize sessions into semantic summaries |
| **File** | `src/memory/compaction.py` |
| **Delegation** | Metis → Hephaestus |
| **Category** | `deep` |
| **Verification** | Size reduction metric + integrity check |
| **QA** | Test LLM summarization, search |

---

## 🔌 PHASE 4: Integration (T10-T12)

**Duration**: ~1 week
**Goal**: Connect all systems

### T10: MCP Server for Memory

| Field | Value |
|-------|-------|
| **What** | FastMCP stdio server exposing memory tools |
| **File** | `mcp-servers/nx-memory/main.py` |
| **Delegation** | Hephaestus (direct) |
| **Category** | `deep` |
| **Verification** | skill_mcp list + connection test |
| **QA** | Test each tool via MCP protocol |

### T11: Athena Integration

| Field | Value |
|-------|-------|
| **What** | Wrap existing Athena memory with learning layer |
| **File** | `src/integrations/athena_memory.py` |
| **Delegation** | Oracle → Hephaestus |
| **Category** | `ultrabrain` |
| **Verification** | Integration test + context retrieval |
| **QA** | Verify backward compatibility |

### T12: End-to-End Testing

| Field | Value |
|-------|-------|
| **What** | Complete test suite for all components |
| **Files** | `tests/test_memory/*.py` |
| **Delegation** | Hephaestus (direct) |
| **Category** | `unspecified-low` |
| **Verification** | All tests pass + gate proof |
| **QA** | Run pytest, generate coverage report |

---

## 🚀 EXECUTION WAVES

```
┌────────────────────────────────────────────────────────────────────┐
│                        EXECUTION TIMELINE                          │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  WEEK 1          WEEK 2           WEEK 3          WEEK 4          │
│  ═══════         ═══════          ═══════         ═══════          │
│                                                                     │
│  [W1: Core]      [W2: Learn]     [W3: Ops]      [W4: Integ]      │
│  ┌─────┐         ┌─────┐          ┌─────┐         ┌─────┐          │
│  │T1 ██│         │T4 ██│          │T7 ██│         │T10██│          │
│  │T2 ██│►PARALLEL│T5 ██│►PARALLEL │T8 ██│►PARALLEL│T11██│          │
│  │T3 ██│         │T6 ██│          │T9 ██│         │T12██│          │
│  └─────┘         └─────┘          └─────┘         └─────┘          │
│  │││             │││             │││             │││               │
│  ▼▼▼             ▼▼▼             ▼▼▼             ▼▼▼              │
│  Verify          Verify           Verify          Verify           │
│  ┌───┐           ┌───┐            ┌───┐           ┌───┐            │
│  │Oracle│         │Momus│          │Momus│         │Full│           │
│  │+diag│          │+test│           │+log│          │test│           │
│  └───┘           └───┘            └───┘           └───┘            │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## ⚠️ FAILURE HANDLING PROTOCOL

### Delegation Failure Chain

```
Hephaestus fails
    │
    ├──► Retry with reflection (1 attempt)
    │    prompt: "Reflect on failure: {error}. Fix: {specific}"
    │
    └──► Escalate to Oracle (design guidance)
         session_id for context preservation

Oracle fails
    │
    ├──► Retry once with simpler prompt
    │
    └──► Escalate to Momus (alternative review)

Prometheus fails
    │
    ├──► Retry with simpler prompt
    │
    └──► Metis does gap analysis first

Explore/Librarian fails
    │
    ├──► Try different search angle
    │
    └──► Re-delegate via Sisyphus-Junior

2+ consecutive failures
    │
    └──► Switch to fallback agent
         (see Fallback Chain below)
```

### Fallback Chain

```
Hephaestus → Oracle (guidance) → Sisyphus
Oracle → Momus → Sisyphus
Explore → Sisyphus-Junior → Atlas
Atlas → Sisyphus-Junior → Hephaestus
```

### Stop Conditions

| Failure Count | Action |
|---------------|--------|
| 1 failure | Retry once |
| 2 failures | Switch fallback agent |
| 3+ failures | **STOP**, report to user with full history |

---

## ✅ VERIFICATION GATE

Every task MUST pass:

```bash
# Phase 1: Core Memory
lsp_diagnostics src/memory/*.py        # 0 errors
python3 -m json.tool src/config/*.json # valid
pytest tests/test_memory/ -v           # all pass

# Phase 2: Self-Learning
python3 src/learning/skill_lifecycle.py --test  # state transitions work
python3 src/learning/prompt_evolution.py --test # evolution works

# Phase 3: Memory Ops
python3 src/memory/sleep_cycle.py --test         # consolidation works
python3 src/memory/forgetting.py --test          # decay works

# Phase 4: Integration
./bin/mcp-connection-test.sh                      # MCP connects
pytest tests/test_integration.py -v                # all pass
```

---

## 📊 SUCCESS METRICS

| Phase | Metric | Target |
|-------|--------|--------|
| W1 | Files created + lsp_diagnostics clean | 3 files, 0 errors |
| W2 | Skills auto-promote correctly | 3+ state transitions |
| W3 | Memory size stable (no bloat) | <10MB growth |
| W4 | All MCP tools functional | 10+ tools available |

---

## 📁 FILE STRUCTURE

```
src/
├── memory/
│   ├── __init__.py
│   ├── hierarchical.py      # T1
│   ├── knowledge_graph.py   # T2
│   ├── vector_index.py      # T3
│   ├── sleep_cycle.py       # T7
│   ├── forgetting.py        # T8
│   └── compaction.py        # T9
├── learning/
│   ├── __init__.py
│   ├── skill_lifecycle.py  # T4
│   ├── prompt_evolution.py # T5
│   └── self_learning.py    # T6
├── integrations/
│   ├── __init__.py
│   └── athena_memory.py    # T11

mcp-servers/
└── nx-memory/
    ├── __init__.py
    └── main.py             # T10

tests/
└── test_memory/
    ├── __init__.py
    ├── test_hierarchical.py
    ├── test_knowledge_graph.py
    ├── test_skill_lifecycle.py
    ├── test_prompt_evolution.py
    ├── test_self_learning.py
    ├── test_sleep_cycle.py
    ├── test_forgetting.py
    └── test_integration.py
```

---

## 🎯 DELEGATION TEMPLATES

### Implementation Delegation
```python
task(
    category="deep",
    load_skills=["skill-1", "skill-2"],
    prompt="""TASK: Implement {file}
GOAL: Working class with {methods}
FILE: {path}
EXISTING: {reference files}
MUST: {specific requirements}
MUST NOT: {forbidden patterns}
VERIFICATION: {how to test}"""
)
```

### Research Delegation
```python
task(
    subagent_type="explore",
    load_skills=[],
    prompt="Find {pattern} in codebase",
    run_in_background=true
)
```

---

## 📋 CHECKLIST BEFORE STARTING

- [ ] All 12 tasks defined with files + methods
- [ ] Delegation matrix matches task → agent
- [ ] Category/skill assigned per task
- [ ] Verification criteria defined
- [ ] Fallback chains documented
- [ ] File structure created
- [ ] Dependencies verified (numpy, networkx, fastmcp)

---

## 🏁 READY TO EXECUTE

When ready, execute wave by wave:
1. **W1**: Fire T1, T2, T3 in parallel (3 Hephaestus instances)
2. **Verify**: lsp_diagnostics + Oracle review
3. **W2**: Fire T4, T5, T6 in parallel
4. **Verify**: Tests + Momus review
5. **W3**: Fire T7, T8, T9 in parallel
6. **Verify**: Logs + metrics
7. **W4**: Fire T10, T11, T12
8. **Verify**: Full test suite + gate proof

**Next**: Use `/start-work` to begin execution
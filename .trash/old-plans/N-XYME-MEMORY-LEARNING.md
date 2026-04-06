# N-Xyme MIND: Memory & Self-Learning System

> **Focus**: Build the BEST self-learning memory system for N-Xyme MIND v0.2.0+
> **Philosophy**: "We synthesize Frankenstein — stitch together what works from ALL sources, discard what failed."

SM|---
NH|## TL;DR
JT|
YB|| Layer | Source | Pattern | License |
RB||-------|--------|---------|---------|
VN|| **Hierarchical Memory** | MemGPT/Letta | Working→Episodic→Semantic→Archival | Concept |
WB|| **Sleep-Cycle** | smysle/agent-memory (9⭐) | JOURNAL→CONSOLIDATE→RECALL | ✅ **MIT** |
BV|| **Forgetting Curves** | YourMemory (11⭐) | Ebbinghaus decay | ⚠️ Verify |
MH|| **Prompt Evolution** | microsoft/PromptWizard (3.8k⭐) | Generate→Critique→Refine | ✅ **MIT** |
YR|| **Skill Lifecycle** | ace-agent/ace (891⭐) | Proposed→...→Archived | Apache 2.0 |
YN|| **Knowledge Graph** | neo4j-labs/agent-memory (103⭐) | Entities→Relations | ⚠️ Verify |
VB|| **Self-Learning** | MemMachine (5.4k⭐) | Success/Failure patterns | Apache 2.0 |
MK|| **Hybrid Memory** | memlayer (262⭐) | Vector + Symbolic | ✅ **MIT** |
VB|| **NEW: SimpleMem** | aiming-lab/SimpleMem (3.3k⭐) | Semantic compression | ✅ **MIT** |
YQ|
SM|---
NH|## MIT-Licensed Sources (Priority)
JT|
YB|| Source | GitHub | Stars | What We Take |
RB||--------|--------|-------|--------------|
VN|| **PromptWizard** | microsoft/PromptWizard | 3.8k⭐ | Prompt evolution |
WB|| **SimpleMem** | aiming-lab/SimpleMem | 3.3k⭐ | Semantic compression |
BV|| **memlayer** | divagr18/memlayer | 262⭐ | Plug-and-play memory |
MH|| **agentic-graph-mem** | agentic-graph-mem | 162⭐ | Graph memory |
YR|| **smysle/agent-memory** | smysle/agent-memory | 9⭐ | Sleep-cycle |
YN|| **elizaOS/agentmemory** | elizaOS/agentmemory | 234⭐ | ChromaDB+Postgres |

---

## Architecture: Complete Memory System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     N-Xyme Memory & Learning System                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    LAYER 1: Hierarchical Memory                       │   │
│  │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                    │   │
│  │   │Working  │→│Episodic │→│Semantic │→│Archival │                    │   │
│  │   │Session  │ │Sessions │ │Patterns │ │Historical│                    │   │
│  │   └─────────┘ └─────────┘ └─────────┘ └─────────┘                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                 LAYER 2: Self-Learning Engine                          │   │
│  │   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                 │   │
│  │   │SkillEvolution│ │PromptEvolution│ │PatternLearning│                │   │
│  │   │  (ace-agent) │ │(PromptWizard) │ │(MemMachine)  │                 │   │
│  │   └──────────────┘ └──────────────┘ └──────────────┘                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                 LAYER 3: Memory Operations                             │   │
│  │   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                 │   │
│  │   │Sleep-Cycle   │ │Forgetting    │ │Consolidation │                 │   │
│  │   │(smysle)      │ │(YourMemory)  │ │(summary)     │                 │   │
│  │   └──────────────┘ └──────────────┘ └──────────────┘                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                 LAYER 4: Storage & Retrieval                          │   │
│  │   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                 │   │
│  │   │KnowledgeGraph│ │Vector Index   │ │Symbolic Store│                 │   │
│  │   │(NetworkX)    │ │(nano-vectordb)│ │(JSON/SQLite) │                 │   │
│  │   └──────────────┘ └──────────────┘ └──────────────┘                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Source Repositories (MIT-licensed Priority)

### Tier 1: MIT Licensed (Use Directly)

| Source | GitHub | Stars | What We Take | License |
|--------|--------|-------|--------------|---------|
| **PromptWizard** | microsoft/PromptWizard | 3.8k⭐ | Prompt evolution feedback loops | ✅ **MIT** |
| **smysle/agent-memory** | smysle/agent-memory | 9⭐ | Sleep-cycle memory architecture | ✅ **MIT** |
| **YourMemory** | sachitrafa/YourMemory | 11⭐ | Ebbinghaus forgetting curve | ✅ **MIT** |
| **Mnemosyne** | 28naem-del/mnemosyne | 35⭐ | Multi-agent cognitive memory | ✅ **MIT** |
| **memlayer** | divagr18/memlayer | 262⭐ | Plug-and-play memory | ✅ **MIT** |
| **agentic-graph-mem** | agentic-graph-mem | 162⭐ | Production-grade graph memory | ✅ **MIT** |

### Tier 2: Apache 2.0 (Use with Attribution)

| Source | GitHub | Stars | What We Take | License |
|--------|--------|-------|--------------|---------|
| **MemMachine** | MemMachine/MemMachine | 5.4k⭐ | Episodic + profile memory | ⚠️ Apache 2.0 |
| **ace-agent/ace** | ace-agent/ace | 891⭐ | Context evolution + playbook updates | ⚠️ Apache 2.0 |
| **neo4j-labs/agent-memory** | neo4j-labs/agent-memory | 103⭐ | Graph-native memory | ⚠️ Apache 2.0 |

---

## Implementation Plan

### Phase 1: Core Memory (Week 1)

#### T1: Hierarchical Memory System
```
src/memory/hierarchical.py
├── TieredMemory class
├── MemoryBlock (content, tier, importance, timestamp)
├── add() → auto-tier assignment
├── retrieve() → search across tiers
└── evict() → move to lower tier
```

#### T2: Knowledge Graph Memory
```
src/memory/knowledge_graph.py
├── GraphMemory class
├── Entity (name, type, properties)
├── Relationship (from, to, type, weight)
├── add_entity(), add_relation()
├── find_path() → BFS path finding
└── query_relationships() → filtered queries
```

#### T3: Vector Index (Hybrid)
```
src/memory/vector_index.py
├── VectorIndex class
├── add() → embed + store
├── search() → cosine similarity
├── hybrid_query() → vector + symbolic
└── _deduplicate_and_rank()
```

### Phase 2: Self-Learning (Week 2)

#### T4: Skill Lifecycle Manager
```
src/learning/skill_lifecycle.py
├── SkillLifecycle class
├── STATES = ["proposed", "experimental", "active", "deprecated", "archived"]
├── record_use() → track success/failure
├── transition() → state machine
├── auto_promote() → based on criteria
└── get_active_skills() → ranked by relevance
```

#### T5: Prompt Evolution Engine
```
src/learning/prompt_evolution.py
├── PromptEvolver class
├── generate() → create variation
├── critique() → self-evaluate
├── refine() → improve based on feedback
├── evaluate() → A/B test
└── version history tracking
```

#### T6: Self-Learning from Outcomes
```
src/learning/self_learning.py
├── SelfLearning class
├── record_success() → store pattern
├── record_failure() → store anti-pattern
├── _find_similar_contexts() → semantic matching
└── get_recommended_actions() → ranked by past success
```

### Phase 3: Memory Operations (Week 3)

#### T7: Sleep-Cycle Consolidation
```
src/memory/sleep_cycle.py
├── SleepCycleMemory class
├── journal() → capture interaction
├── consolidate() → extract patterns, merge semantic
├── recall() → retrieve from consolidated
├── _extract_patterns() → LLM-based
└── _prune_buffer() → remove low-importance
```

#### T8: Forgetting Curve Implementation
```
src/memory/forgetting.py
├── ForgettingMemory class
├── importance() → Ebbinghaus decay calculation
├── stability → memory-specific decay rate
├── access_count → boost for frequent access
└── calculate_decay() → R = e^(-t/S)
```

#### T9: Session Compaction
```
src/memory/compaction.py
├── SessionCompactor class
├── should_compact() → threshold check
├── compact() → LLM summarization
├── SessionSummary (decisions, patterns, issues, skills)
└── store_summary() → vector index for search
```

### Phase 4: Integration (Week 4)

#### T10: MCP Server for Memory
```
mcp-servers/nx-memory/
├── main.py → FastMCP stdio server
├── tools/
│   ├── memory_add() → add to hierarchical
│   ├── memory_recall() → search
│   ├── skill_record() → track skill usage
│   └── skill_suggest() → recommend skills
└── resources/
    └── memory://session/{id} → session context
```

#### T11: Integration with Athena-Public
```
src/integrations/athena_memory.py
├── AthenaMemoryAdapter class
├── read_from_athena() → identity.md, user.md, constraints.md
├── write_to_athena() → update active_context
├── inject_learning() → add learned patterns to context
└── wrap_athena() → create learning layer wrapper
```

#### T12: End-to-End Testing
```
tests/test_memory/
├── test_hierarchical.py
├── test_self_learning.py
├── test_sleep_cycle.py
├── test_forgetting.py
├── test_integration.py
└── test_performance.py
```

---

## Key Implementation Patterns

### 1. Sleep-Cycle Pattern (smysle/agent-memory)

```python
class SleepCycleMemory:
    """
    Biological sleep-inspired memory integration.
    Pattern: JOURNAL → CONSOLIDATE → RECALL
    """
    
    def __init__(self, model_provider: ModelProvider):
        self.model = model_provider
        self.episodic_buffer = []  # Raw interactions
        self.semantic_memory = {}  # Consolidated patterns
        self.tier_budget = {
            "working": 50,      # Current session
            "episodic": 200,     # Recent sessions
            "semantic": 1000,   # Patterns
            "archival": 10000   # Historical
        }
    
    def journal(self, interaction: dict):
        """Capture every interaction immediately."""
        self.episodic_buffer.append({
            "content": interaction,
            "timestamp": time.time(),
            "salience": self._calculate_salience(interaction)
        })
    
    def consolidate(self):
        """Run periodically (session-end or scheduled)."""
        # 1. Extract patterns from episodic buffer
        patterns = self._extract_patterns(self.episodic_buffer)
        
        # 2. Merge into semantic memory
        for pattern in patterns:
            self._merge_into_semantic(pattern)
        
        # 3. Prune episodic buffer
        self.episodic_buffer = self._prune_buffer()
    
    def recall(self, query: str) -> list:
        """Retrieve from semantic memory."""
        return self.semantic_memory.search(query)
    
    def _extract_patterns(self, buffer: list) -> list:
        """Use LLM to extract reusable patterns."""
        prompt = f"""
        Extract reusable patterns from these interactions:
        {buffer}
        
        Return JSON list of patterns with:
        - what worked
        - context where it worked
        - skill(s) used
        """
        return self.model.complete(prompt)
    
    def _merge_into_semantic(self, pattern: dict):
        """Merge pattern into semantic memory."""
        key = pattern.get("context_type", "default")
        if key not in self.semantic_memory:
            self.semantic_memory[key] = []
        self.semantic_memory[key].append(pattern)
```

### 2. Forgetting Curve (YourMemory)

```python
class ForgettingMemory:
    """
    Ebbinghaus forgetting curve implementation.
    +16pp better recall than Mem0 on LoCoMo benchmark.
    """
    
    def __init__(self):
        self.memories = {}  # memory_id -> Memory
        self.decay_base = 0.01  # Decay rate
    
    def importance(self, memory_id: str) -> float:
        """Calculate current importance with decay."""
        memory = self.memories[memory_id]
        elapsed = time.time() - memory.created
        
        # Ebbinghaus formula: R = e^(-t/S)
        # S = stability (memory-specific)
        decay = math.exp(-elapsed / memory.stability)
        
        # Boost factors
        recency_boost = 0.0
        if time.time() - memory.last_accessed < 3600:  # Last hour
            recency_boost = 0.2
        
        frequency_boost = math.log(1 + memory.access_count) * 0.1
        
        importance = memory.initial_importance * decay + recency_boost + frequency_boost
        return min(1.0, importance)
    
    def should_forget(self, memory_id: str) -> bool:
        """Check if memory should be archived/deleted."""
        return self.importance(memory_id) < 0.1
    
    def access(self, memory_id: str):
        """Mark memory as accessed (boosts importance)."""
        self.memories[memory_id].last_accessed = time.time()
        self.memories[memory_id].access_count += 1
```

### 3. Prompt Evolution (PromptWizard)

```python
class PromptEvolver:
    """
    Self-evolving prompts via feedback loops.
    Pattern: Generate → Critique → Refine → Evaluate
    """
    
    def __init__(self, model: ModelProvider):
        self.model = model
        self.current_prompt = ""
        self.version = 1
        self.history = []
    
    def evolve(self, context: str, outcome: str) -> str:
        """One complete feedback loop."""
        
        # 1. Generate variation
        variation = self._generate_variation(self.current_prompt, context)
        
        # 2. Self-critique
        critique = self._critique(variation, context, outcome)
        
        # 3. Refine based on critique
        refined = self._refine(variation, critique)
        
        # 4. Evaluate (compare to current)
        if self._is_better(refined, self.current_prompt, context):
            self.history.append({
                "version": self.version,
                "prompt": self.current_prompt,
                "outcome": outcome
            })
            self.current_prompt = refined
            self.version += 1
        
        return self.current_prompt
    
    def _generate_variation(self, prompt: str, context: str) -> str:
        """Create prompt variation."""
        return self.model.complete(f"""
            Create a variation of this prompt that might work better for: {context}
            Original: {prompt}
        """)
    
    def _critique(self, variation: str, context: str, outcome: str) -> str:
        """Self-critique the variation."""
        return self.model.complete(f"""
            Critique this prompt variation for: {context}
            Outcome was: {outcome}
            Prompt: {variation}
            
            What's wrong? What could be improved?
        """)
    
    def _refine(self, variation: str, critique: str) -> str:
        """Improve based on critique."""
        return self.model.complete(f"""
            Improve this prompt based on the critique:
            Prompt: {variation}
            Critique: {critique}
            
            Return improved prompt only.
        """)
    
    def _is_better(self, new: str, old: str, context: str) -> bool:
        """A/B test - try both, measure outcome."""
        # Simplified: use LLM as judge
        return self.model.complete(f"""
            Which prompt would work better for: {context}
            
            A: {old}
            B: {new}
            
            Return just "A" or "B".
        """).strip() == "B"
```

### 4. Skill Lifecycle (ace-agent/ace)

```python
class SkillLifecycle:
    """
    Skill state machine with automatic evolution.
    States: proposed → experimental → active → deprecated → archived
    """
    
    STATES = ["proposed", "experimental", "active", "deprecated", "archived"]
    VALID_TRANSITIONS = {
        "proposed": ["experimental", "archived"],
        "experimental": ["active", "deprecated", "archived"],
        "active": ["deprecated", "archived"],
        "deprecated": ["archived", "active"],  # Can be reactivated
        "archived": []
    }
    
    def __init__(self):
        self.skills = {}  # skill_id -> Skill
    
    def register(self, name: str, description: str, context: str) -> str:
        """Register new skill in proposed state."""
        skill_id = f"skill_{hash(name) % 100000}"
        self.skills[skill_id] = Skill(
            id=skill_id,
            name=name,
            description=description,
            context=context,
            state="proposed",
            success_count=0,
            failure_count=0,
            version=1
        )
        return skill_id
    
    def record_use(self, skill_id: str, success: bool):
        """Record skill usage outcome."""
        skill = self.skills[skill_id]
        
        if success:
            skill.success_count += 1
        else:
            skill.failure_count += 1
        
        # Auto-promote/demote based on criteria
        self._evaluate_transition(skill_id)
    
    def _evaluate_transition(self, skill_id: str):
        """Evaluate if skill should transition states."""
        skill = self.skills[skill_id]
        
        # Promotion: experimental → active
        if skill.state == "experimental" and skill.success_count >= 3:
            self.transition(skill_id, "active")
        
        # Demotion: active → deprecated (50%+ failure rate)
        elif skill.state == "active":
            rate = skill.failure_count / (skill.success_count + skill.failure_count)
            if rate > 0.5:
                self.transition(skill_id, "deprecated")
    
    def transition(self, skill_id: str, new_state: str):
        """Transition skill to new state."""
        skill = self.skills[skill_id]
        
        if new_state in self.VALID_TRANSITIONS[skill.state]:
            skill.state = new_state
            skill.version += 1
    
    def get_recommended(self, context: str) -> list:
        """Get active skills ranked by relevance."""
        active = [s for s in self.skills.values() if s.state == "active"]
        
        # Rank by success rate * relevance to context
        scored = []
        for skill in active:
            rate = skill.success_count / (skill.success_count + skill.failure_count + 1)
            relevance = 1.0 if context.lower() in skill.context.lower() else 0.5
            scored.append((skill, rate * relevance))
        
        return [s for s, _ in sorted(scored, key=lambda x: x[1], reverse=True)]
```

### 5. Hybrid Memory (Vector + Symbolic)

```python
class HybridMemory:
    """
    Dual-channel: vector for semantic, symbolic for exact.
    """
    
    def __init__(self, model_provider: ModelProvider):
        self.model = model_provider
        self.vector_store = []  # [(embedding, content, metadata)]
        self.symbolic_store = {}  # entity_type -> [(id, data)]
    
    def add(self, content: str, metadata: dict = None):
        """Add to both channels."""
        # Vector channel
        embedding = self.model.embed(content)
        self.vector_store.append((embedding, content, metadata or {}))
        
        # Symbolic channel
        entity_type = metadata.get("type", "generic") if metadata else "generic"
        if entity_type not in self.symbolic_store:
            self.symbolic_store[entity_type] = []
        self.symbolic_store[entity_type].append((len(self.vector_store) - 1, metadata or {}))
    
    def query(self, query_str: str = None, exact_filters: dict = None, top_k: int = 5):
        """Query both channels, merge results."""
        results = []
        
        # Vector channel (semantic similarity)
        if query_str:
            query_emb = self.model.embed(query_str)
            vector_results = self._vector_search(query_emb, top_k * 2)
            results.extend([(item, "vector", score) for item, score in vector_results])
        
        # Symbolic channel (exact match)
        if exact_filters:
            symbolic_results = self._symbolic_search(exact_filters)
            results.extend([(item, "symbolic", 1.0) for item in symbolic_results])
        
        # Deduplicate and rank
        return self._deduplicate_and_rank(results, top_k)
    
    def _vector_search(self, query_emb: list, k: int) -> list:
        """Cosine similarity search."""
        scores = []
        for emb, content, meta in self.vector_store:
            sim = self._cosine(query_emb, emb)
            scores.append(((emb, content, meta), sim))
        
        return sorted(scores, key=lambda x: x[1], reverse=True)[:k]
    
    def _symbolic_search(self, filters: dict) -> list:
        """Exact match on metadata."""
        results = []
        for items in self.symbolic_store.values():
            for idx, meta in items:
                if all(meta.get(k) == v for k, v in filters.items()):
                    results.append(self.vector_store[idx])
        return results
    
    def _deduplicate_and_rank(self, results: list, top_k: int) -> list:
        """Merge and rank results."""
        seen = set()
        deduped = []
        
        for item, source, score in results:
            content = item[1]  # content is second element
            if content not in seen:
                seen.add(content)
                boost = 0.2 if source == "symbolic" else 0  # Prefer exact matches
                deduped.append((item, score + boost))
        
        return [item for item, _ in sorted(deduped, key=lambda x: x[1], reverse=True)[:top_k]]
    
    def _cosine(self, a: list, b: list) -> float:
        """Cosine similarity."""
        dot = sum(x * y for x, y in zip(a, b))
        norm = (sum(x * x for x in a) ** 0.5) * (sum(x * x for x in b) ** 0.5)
        return dot / norm if norm > 0 else 0
```

---

## Success Criteria

- [ ] Hierarchical memory (4 tiers) implemented and tested
- [ ] Knowledge graph stores entities and relationships
- [ ] Vector + symbolic hybrid search working
- [ ] Skill lifecycle auto-promotes/demotes correctly
- [ ] Prompt evolution improves prompts over time
- [ ] Self-learning recommends actions based on past success
- [ ] Sleep-cycle consolidates session data periodically
- [ ] Forgetting curve correctly decays old memories
- [ ] Session compaction summarizes conversations
- [ ] MCP server provides memory tools to agents
- [ ] Integration with Athena-Public preserves existing data
- [ ] All tests pass (100%+ coverage target)

---

## Dependencies

```
# Core
numpy>=1.24.0
networkx>=3.0
pydantic>=2.0

# Model Provider (for embeddings)
# Ollama (local) or OpenAI (optional)

# MCP
fastmcp>=2.14.0

# Testing
pytest>=7.0.0
pytest-asyncio>=0.21.0
```

---

## File Structure

```
src/
├── memory/
│   ├── __init__.py
│   ├── hierarchical.py      # T1
│   ├── knowledge_graph.py   # T2
│   ├── vector_index.py       # T3
│   ├── sleep_cycle.py        # T7
│   ├── forgetting.py         # T8
│   └── compaction.py         # T9
├── learning/
│   ├── __init__.py
│   ├── skill_lifecycle.py   # T4
│   ├── prompt_evolution.py  # T5
│   ├── self_learning.py     # T6
│   └── __init__.py
├── integrations/
│   ├── __init__.py
│   └── athena_memory.py      # T11
└── model_providers.py        # From v0.2.0

mcp-servers/
└── nx-memory/
    ├── __init__.py
    └── main.py              # T10

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

## Notes

1. **Ollama requirement**: All LLM calls go through model_providers.py abstraction
2. **Offline-first**: No external services required
3. **Athena compatibility**: Existing memory_bank/ files preserved
4. **Iterative improvement**: Each phase adds value independently
5. **MIT priority**: All tier-1 sources are MIT-licensed
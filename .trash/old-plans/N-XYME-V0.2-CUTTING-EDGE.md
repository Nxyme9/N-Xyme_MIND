# N-Xyme MIND: v0.2.0 Cutting-Edge Roadmap

> **Philosophy**: "We synthesize Frankenstein — stitch together what works from ALL sources, discard what failed."

---

## TL;DR

> **Goal**: Build v0.2.0 with cutting-edge patterns from 2025-2026 research.
>
RP|> **New Sources Added** (vs v0.1.0) — MIT/PRIORITY:
WY|> - **PromptWizard** (3.8k⭐, **MIT**) — Self-evolving prompts via feedback loops ⭐
BS|> - **smysle/agent-memory** (MIT) — Sleep-cycle consolidation (JOURNAL→CONSOLIDATE→RECALL) ⭐
JJ|> - **YourMemory** (MIT) — Ebbinghaus forgetting curve (+16pp vs Mem0) ⭐
JN|> - **Mnemosyne** (35⭐, **MIT**) — Multi-agent cognitive memory ⭐
QS|> - **memlayer** (262⭐, **MIT**) — Plug-and-play memory layer ⭐
PM|> - **ace-agent/ace** (891⭐, Apache 2.0) — Context evolution patterns
NW|>
NW|> **Also included** (license verify needed):
NW|> - **MemMachine** (5.4k⭐) — Episodic + profile memory
NW|> - **openagents-org/openagents** (2117⭐) — Network orchestration
NW|> - **memodb-io/Acontext** (3200⭐) — Skills as memory layer
NW|>
NW|> **Key Enhancements** (Memory-First):
VB|> 1. **Self-Learning Memory** — PromptWizard feedback loop
ZB|> 2. **Sleep-Cycle Consolidation** — smysle patterns
XZ|> 3. **Forgetting Curves** — YourMemory Ebbinghaus decay
KH|> 4. **Hierarchical Memory** — MemGPT-style 4 tiers
YT|> 5. **Knowledge Graph** — NetworkX entity→relationship→properties
RW|> 6. **Skill Evolution** — Proposed→Experimental→Active→Deprecated→Archived
WS|> 7. **Prompt Evolution** — Generate→Critique→Refine→Evaluate
WS|> 8. **Model provider abstraction** — Ollama, cloud as opt-in
> **Version**: v0.2.0-alpha
> **Target**: `/home/nxyme/N-Xyme_CODE/N-Xyme_MIND_v0.2/`
> **Prerequisite**: v0.1.0 completion

---

## Source Matrix (Updated)

QQ|| Source | GitHub | Stars | What We Take | License |
ZH||--------|--------|-------|--------------|---------|
RQ|| **MIT-PRIORITY SOURCES** | | | | |
VT|| **PromptWizard** | microsoft/PromptWizard | 3.8k⭐ | Self-evolving prompts via feedback loops | ✅ **MIT** |
BS|| **smysle/agent-memory** | smysle/agent-memory | 9⭐ | Sleep-cycle consolidation (JOURNAL→CONSOLIDATE→RECALL) | ✅ **MIT** |
JJ|| **YourMemory** | sachitrafa/YourMemory | 11⭐ | Ebbinghaus forgetting curve | ✅ **MIT** |
JN|| **Mnemosyne** | 28naem-del/mnemosyne | 35⭐ | Multi-agent cognitive memory | ✅ **MIT** |
QS|| **memlayer** | divagr18/memlayer | 262⭐ | Plug-and-play memory layer | ✅ **MIT** |
PM|| **memMachine** | MemMachine/MemMachine | 5.4k⭐ | Episodic + profile memory | ⚠️ Apache 2.0 |
NW|| **ace-agent/ace** | ace-agent/ace | 891⭐ | Context evolution + playbook updates | ⚠️ Apache 2.0 |
WY|| **EXISTING SOURCES** | | | | |
VB|| **Athena-Public** | winstonkoh87/athena-public | 445⭐ | Memory bank, governance, sentinel, flight_recorder | ✅ MIT |
ZB|| **OpenCode-Athena** | ZebulonRouseFrantzich/opencode-athena | 7⭐ | BMAD + Sisyphus bridge patterns | ✅ MIT-0 |
XZ|| **Other** | | | | |
KH|| **openagents** | openagents-org/openagents | 2117⭐ | Network orchestration + A2A patterns | ⏳ Verify |
YT|| **Acontext** | memodb-io/acontext | 3200⭐ | Skills as memory layer MCP | ⏳ Verify |
RW|| **codeany** | codeany-ai/codeany | 142⭐ | Go terminal agent patterns | ✅ MIT |
WS|| **Local** | N/A (local) | — | VPN rotator, BMAD workflows | N/A |

---

## Architecture (v0.2.0 Enhanced)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          N-Xyme MIND v0.2.0-alpha                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      LAYER 1: Core Foundation                         │   │
│  │   ├── governance.py          # Doom Loop + Triple-Lock               │   │
│  │   ├── sentinel.py            # Boot/shutdown checks + Protocol 420   │   │
│  │   ├── flight_recorder.py     # JSONL audit trail                     │   │
│  │   ├── skill_telemetry.py     # Usage tracking + dead skill detection │   │
│  │   └── delta_manifest.py      # O(1) file sync                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                   LAYER 2: Memory System (ENHANCED)                   │   │
│  │   ├── athena_memory/         # Base: markdown memory bank            │   │
│  │   ├── skill_memory.py        # NEW: MemOS patterns - skill evolution │   │
│  │   ├── session_compactor.py   # NEW: Semantic summary compaction      │   │
│  │   └── vector_index.py        # NEW: nano-vectordb selective indexing  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                 LAYER 3: Agent Orchestration (ENHANCED)              │   │
│  │   ├── model_providers.py     # NEW: Abstraction layer (Ollama, etc.) │   │
│  │   ├── a2a_protocol.py        # NEW: Agent-to-Agent communication     │   │
│  │   ├── network_orchestrator.py # NEW: openagents network patterns     │   │
│  │   ├── sisyphus.py            # Core: Plan executor                   │   │
│  │   ├── prometheus.py          # Core: Plan builder                    │   │
│  │   └── hephaestus.py          # Core: Implementation                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       LAYER 4: MCP Servers                            │   │
│  │   ├── athena-context/        # Context injection (enhanced)          │   │
│  │   ├── trigger-guardian/      # Trigger phrase routing                │   │
│  │   ├── nx-mind/              # MIND state management                  │   │
│  │   ├── skill-memory-mcp/     # NEW: Acontext patterns - skills cache  │   │
│  │   ├── eval-harness-mcp/     # NEW: llm-quality-gate integration     │   │
│  │   └── registry.yaml          # NEW: Local YAML MCP registry           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    LAYER 5: Quality & Evals                           │   │
│  │   ├── eval_harness.py        # NEW: Lightweight eval framework      │   │
│  │   ├── quality_gates.py       # Enhanced: 40+ checks (PRGuard)       │   │
│  │   └── regression_detector.py # NEW: Session comparison               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         LAYER 6: Infrastructure                      │   │
│  │   ├── _bmad/                 # BMAD workflows + 46 skills           │   │
│  │   ├── vpn/                   # VPN rotator system                    │   │
│  │   ├── bin/                   # CLI tools                              │   │
│  │   └── tests/evals/          # NEW: Eval test suite                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## What's NEW in v0.2.0

### 1. Model Provider Abstraction Layer

**Source**: Oracle recommendation
**Purpose**: Enable offline-first with local Ollama, allow cloud as opt-in

```python
# src/model_providers.py
class ModelProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, **kwargs) -> str:
        pass
    
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        pass

class OllamaProvider(ModelProvider):
    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
    
    def complete(self, prompt: str, **kwargs) -> str:
        # Use Ollama API
        ...
    
    def embed(self, text: str) -> list[float]:
        # Use nomic-embed-text
        ...

class OpenAIProvider(ModelProvider):
    # Only when OPENAI_API_KEY is set
    ...

class ProviderRegistry:
    def get_provider(self) -> ModelProvider:
        if os.getenv("OLLAMA_HOST"):
            return OllamaProvider()
        elif os.getenv("OPENAI_API_KEY"):
            return OpenAIProvider()
        else:
            raise RuntimeError("No model provider configured")
```

**Why**: Enables true offline-first, easy provider swapping, no vendor lock-in.

---

### 2. Session Compaction

**Source**: MemOS patterns + Oracle recommendation
**Purpose**: Prevent memory bloat, compress older sessions into semantic summaries

```python
# src/session_compactor.py
class SessionCompactor:
    """
    Compacts sessions > N messages into semantic summaries.
    Inspired by MemOS skill evolution + context compaction patterns.
    """
    
    def __init__(self, model: ModelProvider, threshold: int = 50):
        self.model = model
        self.threshold = threshold
    
    def should_compact(self, session: Session) -> bool:
        return len(session.messages) > self.threshold
    
    def compact(self, session: Session) -> SessionSummary:
        """Extract key patterns, decisions, and learnings."""
        prompt = f"""
        Summarize this session into:
        1. Key decisions made
        2. Patterns discovered
        3. Open issues / TODOs
        4. Skills used
        
        Session:
        {session.messages}
        """
        summary_text = self.model.complete(prompt)
        return SessionSummary(
            original_session_id=session.id,
            summary=summary_text,
            message_count=len(session.messages),
            timestamp=datetime.now()
        )
```

**Why**: Addresses memory growth without new database, inspired by MemOS skill evolution.

---

### 3. Skill Memory Evolution

**Source**: MemTensor/MemOS (8050⭐)
**Purpose**: Learn from past sessions, evolve skills over time

```python
# src/skill_memory.py
class SkillMemory:
    """
    Tracks skill usage and effectiveness across sessions.
    Inspired by MemOS persistent skill memory.
    """
    
    def __init__(self, storage_path: Path, model: ModelProvider):
        self.storage_path = storage_path / "skill_memory"
        self.model = model
        self.skill_graph = {}  # skill_id -> SkillMetrics
    
    def record_usage(self, skill: str, success: bool, context: dict):
        """Record skill usage for evolution."""
        if skill not in self.skill_graph:
            self.skill_graph[skill] = SkillMetrics(skill_id=skill)
        
        self.skill_graph[skill].add_usage(success, context)
    
    def suggest_skills(self, task: str) -> list[str]:
        """Suggest skills based on task context + historical success."""
        # Find similar tasks from history
        similar = self._find_similar_tasks(task)
        
        # Rank skills by historical success rate
        skill_scores = {}
        for session in similar:
            for skill_used in session.skills_used:
                if skill_used not in skill_scores:
                    skill_scores[skill_used] = []
                skill_scores[skill_used].append(session.success)
        
        # Return top-scoring skills
        ranked = sorted(skill_scores.items(), 
                      key=lambda x: mean(x[1]), 
                      reverse=True)
        return [skill for skill, _ in ranked[:5]]
    
    def evolve_skill(self, skill_id: str) -> EvolvedSkill:
        """Generate improved version of skill based on usage patterns."""
        metrics = self.skill_graph[skill_id]
        
        # Analyze failures → generate improvements
        improvements = self._analyze_failures(metrics)
        
        return EvolvedSkill(
            original_id=skill_id,
            improvements=improvements,
            confidence=metrics.success_rate
        )
```

**Why**: Beats Athena's static memory — learns and evolves over time.

---

### 4. Network Orchestration (A2A)

**Source**: openagents-org/openagents (2117⭐)
**Purpose**: Replace purely hierarchical with peer-to-peer agent coordination

```python
# src/a2a_protocol.py
class A2AMessage:
    """Agent-to-Agent message protocol."""
    
    def __init__(self, from_agent: str, to_agent: str, action: str, payload: dict):
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.action = action  # REQUEST, RESPONSE, BROADCAST, ESCALATE
        self.payload = payload
        self.timestamp = datetime.now()
        self.message_id = uuid4()

class A2AProtocol:
    """
    Agent-to-Agent communication layer.
    Inspired by openagents network orchestration patterns.
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.peers = {}  # agent_id -> AgentPeer
        self.inbox = asyncio.Queue()
        self.outbox = asyncio.Queue()
    
    def register_peer(self, peer_id: str, capabilities: list[str]):
        """Register another agent as a peer."""
        self.peers[peer_id] = AgentPeer(
            agent_id=peer_id,
            capabilities=capabilities,
            last_seen=datetime.now()
        )
    
    async def send(self, to: str, action: str, payload: dict):
        """Send message to peer agent."""
        msg = A2AMessage(
            from_agent=self.agent_id,
            to_agent=to,
            action=action,
            payload=payload
        )
        await self.outbox.put(msg)
    
    async def broadcast(self, action: str, payload: dict):
        """Broadcast to all peers."""
        for peer_id in self.peers:
            await self.send(peer_id, action, payload)
    
    async def receive(self) -> A2AMessage:
        """Receive message from inbox."""
        return await self.inbox.get()

# Usage: Hephaestus requests Prometheus for context
# await a2a.send("prometheus", "REQUEST_CONTEXT", {"task_id": task.id})
```

**Why**: Network orchestration enables dynamic collaboration vs fixed hierarchy.

---

### 5. Selective Vector Indexing

**Source**: nano-vectordb (MIT)
**Purpose**: Add semantic search where needed, don't force vector DB everywhere

```python
# src/vector_index.py
class VectorIndex:
    """
    Local vector database for selective semantic search.
    Uses nano-vectordb principles - minimal, hackable.
    """
    
    def __init__(self, storage_path: Path, model: ModelProvider):
        self.storage_path = storage_path
        self.model = model
        self.index_path = storage_path / "vector_index"
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        # Simple file-based index (nano-vectordb style)
        self.vectors = {}  # doc_id -> {"embedding": [], "metadata": {}}
    
    def add(self, doc_id: str, text: str, metadata: dict = None):
        """Add document to index."""
        embedding = self.model.embed(text)
        self.vectors[doc_id] = {
            "embedding": embedding,
            "text": text,
            "metadata": metadata or {}
        }
        self._persist()
    
    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        """Semantic search with cosine similarity."""
        query_embedding = self.model.embed(query)
        
        results = []
        for doc_id, doc in self.vectors.items():
            similarity = self._cosine_similarity(query_embedding, doc["embedding"])
            results.append((doc_id, similarity))
        
        return sorted(results, key=lambda x: x[1], reverse=True)[:top_k]
    
    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot / (norm_a * norm_b)
    
    def _persist(self):
        """Persist to disk (JSON for simplicity)."""
        with open(self.index_path / "index.json", "w") as f:
            json.dump({k: {"embedding": v["embedding"], "metadata": v["metadata"]} 
                       for k, v in self.containers.items()}, f)
```

**Why**: Semantic search for specific use cases (code search, documentation lookup) without full vector DB overhead.

---

### 6. Eval Harness

**Source**: llm-quality-gate (MIT)
**Purpose**: Detect regressions, validate prompt quality

```python
# src/eval_harness.py
class EvalHarness:
    """
    Lightweight eval framework for LLM outputs.
    Inspired by llm-quality-gate patterns.
    """
    
    def __init__(self, model: ModelProvider):
        self.model = model
        self.test_cases = []
    
    def add_test(self, name: str, prompt: str, expected: str, validator: callable = None):
        """Add test case."""
        self.test_cases.append({
            "name": name,
            "prompt": prompt,
            "expected": expected,
            "validator": validator or self._default_validator
        })
    
    def run(self) -> EvalResults:
        """Run all test cases."""
        results = []
        for test in self.test_cases:
            output = self.model.complete(test["prompt"])
            passed = test["validator"](output, test["expected"])
            results.append({
                "name": test["name"],
                "passed": passed,
                "output": output,
                "expected": test["expected"]
            })
        
        return EvalResults(
            total=len(results),
            passed=sum(1 for r in results if r["passed"]),
            failed=sum(1 for r in results if not r["passed"]),
            details=results
        )
    
    def _default_validator(self, output: str, expected: str) -> bool:
        """Default: substring match."""
        return expected.lower() in output.lower()
```

---

### 7. Local MCP Registry

**Source**: Librarian research + MCP Registry patterns
**Purpose**: Organize MCPs like VPN configs

```yaml
# ~/.nxyme/mcp-servers.yaml
version: 1
servers:
  athena-context:
    description: "Context injection from Athena memory"
    type: stdio
    command: python -m nxmind.mcp.athena_context
    enabled: true
  
  skill-memory:
    description: "Skill memory evolution (MemOS patterns)"
    type: stdio
    command: python -m nxmind.mcp.skill_memory
    enabled: true
  
  eval-harness:
    description: "Eval harness for quality gates"
    type: stdio
    command: python -m nxmind.mcp.eval_harness
    enabled: false  # Opt-in
  
  trigger-guardian:
    description: "Trigger phrase routing"
    type: stdio
    command: python -m nxmind.mcp.trigger_guardian
    enabled: true
  
  nx-mind:
    description: "MIND state management"
    type: stdio
    command: python -m nxmind.mcp.nx_mind
    enabled: true
```

HN|---
QB|
GM|## What's NEW in v0.2.0 — Memory & Self-Learning
KB|
GM|### 1. Sleep-Cycle Memory (from smysle/agent-memory, MIT)
KB|
KB|**Pattern**: JOURNAL → CONSOLIDATE → RECALL
KB|
KB|```python
KB|# src/memory/sleep_cycle.py
KB|class SleepCycleMemory:
KB|    """
KB|    Mimics biological sleep for memory integration.
KB|    Inspired by smysle/agent-memory (MIT).
KB|    """
KB|    
KB|    def journal(self, interaction: dict):
KB|        """Capture each interaction in detail."""
KB|        self.episodic_buffer.append({
KB|            "content": interaction,
KB|            "timestamp": time.time(),
KB|            "salience": self._calculate_salience(interaction)
KB|        })
KB|    
KB|    def consolidate(self):
KB|        """Periodic processing - like sleep."""
KB|        # 1. Extract patterns from episodic buffer
KB|        patterns = self._extract_patterns(self.episodic_buffer)
KB|        
KB|        # 2. Merge with semantic memory
KB|        for pattern in patterns:
KB|            self.semantic_memory.merge(pattern)
KB|        
KB|        # 3. Prune low-importance episodic
KB|        self.episodic_buffer = self._prune_buffer()
KB|    
KB|    def recall(self, query: str) -> list:
KB|        """Retrieve from consolidated memory."""
KB|        return self.semantic_memory.search(query)
KB|```
KB|
GM|### 2. Forgetting Curves (from YourMemory, MIT)
KB|
KB|**Pattern**: Ebbinghaus-inspired decay
KB|
KB|```python
KB|# src/memory/forgetting.py
KB|class ForgettingMemory:
KB|    """
KB|    Implements biological forgetting curve.
KB|    Inspired by YourMemory (MIT) - +16pp better than Mem0.
KB|    """
KB|    
KB|    def importance(self, memory: Memory) -> float:
KB|        """Calculate current importance with decay."""
KB|        elapsed = time.time() - memory.created
KB|        
KB|        # Ebbinghaus: R = e^(-t/S) where S = stability
KB|        decay = math.exp(-elapsed / memory.stability)
KB|        
KB|        # Boost for recency + frequency
KB|        boost = math.log(1 + memory.access_count) * 0.1
KB|        
KB|        return min(1.0, memory.initial_importance * decay + boost)
KB|```
KB|
GM|### 3. Prompt Evolution (from PromptWizard, MIT)
KB|
KB|**Pattern**: Generate → Critique → Refine → Evaluate
KB|
KB|```python
KB|# src/learning/prompt_evolution.py
KB|class PromptEvolver:
KB|    """
KB|    Self-evolving prompts via feedback.
KB|    Inspired by microsoft/PromptWizard (MIT).
KB|    """
KB|    
KB|    def evolve(self, context: str, outcome: str):
KB|        """One feedback loop cycle."""
KB|        # Generate variation
KB|        variation = self.generator.create_variation(self.current_prompt)
KB|        
KB|        # Self-critique
KB|        critique = self.critic.evaluate(variation, context)
KB|        
KB|        # Refine based on critique
KB|        refined = self.refiner.improve(variation, critique)
KB|        
KB|        # If better, promote
KB|        if self.evaluator.is_better(refined, self.current_prompt):
KB|            self.current_prompt = refined
KB|            self.version += 1
KB|```
KB|
GM|### 4. Skill Lifecycle (from ace-agent/ace, Apache 2.0)
KB|
KB|**Pattern**: Proposed → Experimental → Active → Deprecated → Archived
KB|
KB|```python
KB|# src/learning/skill_lifecycle.py
KB|class SkillLifecycle:
KB|    """
KB|    Skill state machine with evolution.
KB|    Inspired by ace-agent/ace (Apache 2.0).
KB|    """
KB|    
KB|    STATES = ["proposed", "experimental", "active", "deprecated", "archived"]
KB|    
KB|    def transition(self, skill_id: str, new_state: str):
KB|        if new_state in self.valid_transitions[self.skills[skill_id].state]:
KB|            self.skills[skill_id].state = new_state
KB|            self.skills[skill_id].version += 1
KB|    
KB|    def auto_promote(self, skill_id: str):
KB|        """Promote if criteria met."""
KB|        skill = self.skills[skill_id]
KB|        if skill.state == "experimental" and skill.success_count >= 3:
KB|            self.transition(skill_id, "active")
KB|```
KB|
GM|### 5. Hierarchical Memory (from MemGPT patterns)
KB|
KB|**Pattern**: Working → Episodic → Semantic → Archival
KB|
KB|```python
KB|# src/memory/hierarchical.py
KB|class HierarchicalMemory:
KB|    """
KB|    4-tier memory management.
KB|    Inspired by MemGPT/Letta patterns.
KB|    """
KB|    
KB|    TIERS = ["working", "episodic", "semantic", "archival"]
KB|    
KB|    def add(self, content: str, tier: str = "episodic"):
KB|        """Add to appropriate tier."""
KB|        self.tiers[tier].append(MemoryBlock(
KB|            content=content,
KB|            tier=tier,
KB|            importance=self._estimate_importance(content)
KB|        ))
KB|        
KB|        # Evict if over budget
KB|        if len(self.tiers[tier]) > self.tier_budget[tier]:
KB|            self._evict_to_next_tier(tier)
KB|    
KB|    def retrieve(self, query: str, tiers: list = None) -> list:
KB|        """Search across tiers."""
KB|        tiers = tiers or self.TIERS
KB|        results = []
KB|        for tier in tiers:
KB|            results.extend(self.tiers[tier].search(query))
KB|        return sorted(results, key=lambda x: x.importance, reverse=True)
KB|```
KB|
GM|### 6. Knowledge Graph Memory (from neo4j-labs/agent-memory)
KB|
KB|**Pattern**: Entities → Relationships → Properties
KB|
KB|```python
KB|# src/memory/knowledge_graph.py
KB|class KnowledgeGraphMemory:
KB|    """
KB|    Graph-based context memory.
KB|    Inspired by neo4j-labs/agent-memory (MIT).
KB|    """
KB|    
KB|    def add_entity(self, name: str, entity_type: str, properties: dict):
KB|        """Add entity node."""
KB|        self.nodes[name] = Entity(name, entity_type, properties)
KB|    
KB|    def add_relation(self, from_node: str, to_node: str, rel_type: str, weight: float):
KB|        """Add relationship edge."""
KB|        self.edges.append(Relationship(from_node, to_node, rel_type, weight))
KB|    
KB|    def find_path(self, start: str, end: str) -> list:
KB|        """Find relationship path between entities."""
KB|        return self.bfs_path(start, end)
KB|    
KB|    def query_relationships(self, entity_type: str) -> list:
KB|        """Query all relationships for entity type."""
KB|        return [e for e in self.edges if self.nodes[e.from_node].type == entity_type]
KB|```
KB|
GM|### 7. Self-Learning from Success/Failure
KB|
KB|**Pattern**: Track outcomes → Extract patterns → Adapt behavior
KB|
KB|```python
KB|# src/learning/self_learning.py
KB|class SelfLearning:
KB|    """
KB|    Learn from success and failure patterns.
KB|    """
KB|    
KB|    def record_outcome(self, context: str, actions: list, success: bool):
KB|        """Record task outcome."""
KB|        if success:
KB|            self.success_patterns.append((context, actions))
KB|        else:
KB|            self.failure_patterns.append((context, actions))
KB|    
KB|    def get_recommended_actions(self, context: str) -> list:
KB|        """Get actions that worked for similar contexts."""
KB|        similar = self._find_similar_contexts(context)
KB|        successful = [a for c, a in similar if c in self.success_patterns]
KB|        return sorted(set(successful), key=successful.count, reverse=True)
KB|```
KB|
GM|### 8. Hybrid Memory (Vector + Symbolic)
KB|
KB|**Pattern**: Semantic search + Exact recall
KB|
KB|```python
KB|# src/memory/hybrid.py
KB|class HybridMemory:
KB|    """
KB|    Dual-channel: vector for similarity, symbolic for exact.
KB|    """
KB|    
KB|    def query(self, query_str: str = None, exact_filters: dict = None):
KB|        """Query both channels, merge results."""
KB|        results = []
KB|        
KB|        # Vector channel (semantic)
KB|        if query_str:
KB|            results.extend(self.vector_store.search(query_str))
KB|        
KB|        # Symbolic channel (exact)
KB|        if exact_filters:
KB|            results.extend(self.symbolic_store.filter(**exact_filters))
KB|        
KB|        return self._deduplicate_and_rank(results)
KB|```
KB|
GM|---

## TODO: Implementation Tasks

### Wave 1: Foundation (Prerequisites)
- [ ] **T1**: Verify license on MemOS, openagents, Acontext
- [ ] **T2**: Create v0.2.0 directory structure
- [ ] **T3**: Copy v0.1.0 base systems
- [ ] **T4**: Implement model_providers.py (abstraction layer)

### Wave 2: Memory System
- [ ] **T5**: Implement session_compactor.py
- [ ] **T6**: Implement skill_memory.py (MemOS patterns)
- [ ] **T7**: Implement vector_index.py (nano-vectordb)
- [ ] **T8**: Enhance athena_memory with evolution

### Wave 3: Agent Orchestration
- [ ] **T9**: Implement a2a_protocol.py
- [ ] **T10**: Implement network_orchestrator.py (openagents patterns)
- [ ] **T11**: Update sisyphus to use A2A
- [ ] **T12**: Add peer discovery mechanism

### Wave 4: MCP Servers
- [ ] **T13**: Implement skill-memory-mcp (Acontext patterns)
- [ ] **T14**: Implement eval-harness-mcp
- [ ] **T15**: Create registry.yaml
- [ ] **T16**: Update all MCPs to use model_providers

### Wave 5: Quality & Evals
- [ ] **T17**: Implement eval_harness.py
- [ ] **T18**: Create tests/evals/ test suite
- [ ] **T19**: Implement regression_detector.py
- [ ] **T20**: Add 40+ quality checks (PRGuard patterns)

### Wave 6: Integration & Polish
- [ ] **T21**: End-to-end integration test
- [ ] **T22**: Performance benchmarks
- [ ] **T23**: Documentation update
- [ ] **T24**: Create v0.2.0 release

---

## Dependencies Matrix

```
T1 (license verify)
  ↓
T2 (dir structure) ← T1
T3 (copy v0.1.0)  ← T1
T4 (model_providers) ← T2
  ↓
T5 (session_compactor) ← T4
T6 (skill_memory)     ← T4
T7 (vector_index)      ← T4
T8 (enhance athena)   ← T4
  ↓
T9 (a2a_protocol) ← T4
T10 (network_orch) ← T9
T11 (update sisyphus) ← T9, T10
T12 (peer discovery)  ← T9
  ↓
T13 (skill-memory-mcp) ← T6
T14 (eval-harness-mcp) ← T17
T15 (registry.yaml)   ← T2
T16 (update MCPs)     ← T13, T14, T4
  ↓
T17 (eval_harness) ← T4
T18 (tests/evals)   ← T17
T19 (regression)    ← T17
T20 (quality checks) ← T17
  ↓
T21 (integration) ← T8, T11, T16, T20
T22 (benchmarks)   ← T21
T23 (docs)         ← T22
T24 (release)     ← T23
```

---

## Success Criteria

- [ ] All MCPs use model_providers abstraction (not hardcoded Ollama)
- [ ] Session compaction works for sessions > 50 messages
- [ ] Skill memory tracks usage and suggests improvements
- [ ] Vector index enables semantic code search
- [ ] A2A protocol enables peer-to-peer agent communication
- [ ] Eval harness runs 10+ test cases
- [ ] Quality gates catch regressions
- [ ] All tests pass
- [ ] v0.2.0 directory structure matches architecture diagram

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| MemOS license not MIT | Medium | High | T1 must verify before integration |
| Over-engineering | Medium | Medium | Stick to TODOs, defer extras |
| Performance regression | Low | Medium | Benchmarks in T22 |
| Embedding drift | Medium | Medium | Pin nomic-embed-text version |

---

## Deferred to v0.3.0

- UTCP adoption (emerging, not mature)
- Full vector DB with clustering
- Multi-agent parallel execution
- Cloud provider integrations (beyond Ollama)
- AutoGen/multi-agent framework

---

## Plan Files

- **v0.1.0**: `.sisyphus/plans/N-XYME-FRANKENSTEIN-SYNTHESIS.md`
- **v0.2.0**: `.sisyphus/plans/N-XYME-V0.2-CUTTING-EDGE.md` (this file)

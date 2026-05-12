---
type: mindmap
tags: [architecture, bosidian, system-design]
created: 2026-04-14
---

# Bosidian Architecture

## 🎯 Core Systems

### Orchestration Layer
- **Sisyphus** - Main orchestrator
  - Task decomposition
  - Agent delegation
  - Quality gates
- **Catalyst** - FLOW/FRICTION state machine
- **Prometheus** - Plan builder
- **Oracle** - Architecture review
- **Momus** - Adversarial reviewer
- **Atlas** - Plan executor

### Agent Layer
- [[Hephaestus]] - Implementation (minimax-m2.5-free)
- [[Explore]] - Codebase search
- [[Librarian]] - External research
- [[Multimodal-looker]] - Image/video processing

## 🧠 Learning Engine (`packages/learning_engine/`)

### RL Algorithms
- [[Q-Learning]] - Adaptive routing optimizer
- [[Double DQN]] - With Prioritized Experience Replay
- [[Bandits]] - Multi-armed bandits
- [[Meta-Learning]] - MAML, EWC implementations

### Core Components
- [[Outcome Logger]] - Logs all delegation outcomes
- [[Routing Optimizer]] - Q-learning weight updates
- [[Event Bus]] - Pub/sub for learning events
- [[Skill Lifecycle]] - Tracks agent skills

### Data Flow
```
User Request → Route Task → Log Outcome → Update Q-Weights → Persist
```

## 💾 Memory Store (`packages/memory_store/`)

### Storage Layer
- [[Vector Store]] - FAISS embeddings
- [[Relational Store]] - SQLite
- [[File Store]] - File-based
- [[Graph Store]] - Neo4j integration
- [[Lance Store]] - Columnar storage

### Cognitive Layer
- [[Forgetting]] - Adaptive decay
- [[Trust System]] - Trust-aware retrieval
- [[Reconsolidation]] - Memory updates
- [[Priority Engine]] - Ranking

### NEW: Advanced Features
- [[TwoPhase Memory]] - Mem0-style extraction/update
- [[Semantic Cache]] - Cost reduction caching

## 🧩 Brain MCP (`packages/brain_mcp/`)

### Namespaces (Tools)
- [[Memory Namespace]] - search_memories, get_memory_stats
- [[Context Namespace]] - get_active_context, inject_context
- [[Mind Namespace]] - session tracking, state management
- [[Session Namespace]] - pool management
- [[Fingerprint Namespace]] - pattern recognition
- [[Tunnel Namespace]] - VPN/key rotation
- [[Intelligence Namespace]] - routing decisions

### MCP Tools (47 total)
- Context retrieval
- Memory search
- Session management
- Routing decisions

## 🧠 Intelligence (`packages/intelligence/`)

### Routing
- [[Unified Router]] - Single entry point for all routing
- [[Predictive Router]] - ML-based predictions
- [[Memory Router]] - Semantic similarity routing
- [[Trigger Router]] - Command pattern matching

### Reliability
- [[Health Monitor]] - System health tracking
- [[Circuit Breaker]] - Failure isolation
- [[Error Recovery]] - Automatic retry/fallback
- [[Fallback Manager]] - Graceful degradation

### Coordination
- [[Multi-Agent Coordinator]] - Parallel execution
- [[Task Decomposer]] - Dependency analysis
- [[Dynamic Scorer]] - Context-aware scoring

## 🔧 Infrastructure

### Model Router
- 8 providers (OpenRouter, Google, Groq, etc.)
- Automatic failover
- Cost optimization

### VPN Rotation
- 8 SOCKS5 proxies (1080-1087)
- Key rotation
- IP rotation

### GGUF Inference
- RTX 3080 Ti optimized
- 1341 tok/s throughput
- Native tool calling

## 📊 Data Layer

### SQLite Databases
- `.sisyphus/outcomes.db` - Learning outcomes
- `.sisyphus/routing.db` - Routing history
- `context/memory/mind_from_mind.db` - Memory store

### Configuration
- `opencode.json` - Project config
- `oh-my-openagent.json` - Agent definitions
- `AGENTS.md` - Workspace rules

## 🔄 Integration Points

### MCP → Packages
- Memory MCP → memory_store/
- Context MCP → brain_mcp/
- Sequential Thinking → intelligence/

### Learning → Routing
- Outcome Logger → Q-Learning → Router
- Real weights from real results

### Health → Recovery
- Circuit Breaker triggers → Error Recovery
- Fallback Manager → Alternative routes
# N-XYME SELF-LEARNING SYSTEM MASTERPLAN

**Version:** 1.0  
**Date:** 2026-04-13  
**Status:** DRAFT - FOR IMPLEMENTATION  

---

## 1. EXECUTIVE SUMMARY

### 1.1 Current State

We have **90% of components built** but **not connected** into a closed self-learning loop:

| Component | Status | Notes |
|-----------|--------|-------|
| **LoRA Training** | ✅ Working | 95% accuracy achieved |
| **Tool Call Parser** | ✅ Fixed | Supports both formats |
| **Outcome Logger** | ✅ Working | 174 records in SQLite |
| **Memory Injection** | ✅ Working | 500 token budget |
| **Q-Learning Router** | ✅ Working | 1196 routing decisions |
| **11 SQLite DBs** | ✅ Filled | 1400+ total records |

**Gap**: The data flows stop at storage - nothing feeds back into model training.

### 1.2 Target State

```
User Request → Tool Call → Outcome Logged → Memory Indexed → 
Training Triggered → LoRA Trained → Adapter Hot-Swapped → 
Better Tool Calls → Faster Learning → User Request
```

**Closed continuous learning loop with zero manual intervention.**

---

## 2. SYNTHESIZED INFRASTRUCTURE

### 2.1 Internal Systems (From Explore Audit)

| System | Type | Tools/Output | Records |
|--------|------|---------------|---------|
| **unified-memory** | MCP | 9 memory tools | memory_tiers.db |
| **learning_engine** | MCP + Core | 9 learning tools, Q-Learning | routing.db (1196) |
| **orchestration** | MCP | 6 agent tools | outcomes.db (174) |
| **intelligence** | MCP | 5 routing tools | triggers (24) |
| **catalyst** | MCP | 6 BMAD tools | workflows |
| **session-pool** | MCP | 6 pool tools | session history |
| **frankenstein_engine** | Engine | GGUF + LoRA inference | adapters/ |
| **OutcomeLogger** | Learning | 174 outcomes + sequences | tool_sequences table |
| **AdaptiveRouter** | Learning | Q-values per agent | routing_learning.db |
| **RealTimeLearner** | Learning | Live weights | agent_weights table |

### 2.2 External Bleeding-Edge Systems (From Librarian Research)

| System | Category | Rating | Relevance |
|--------|----------|--------|-----------|
| **TOUCAN** (1.5M MCP trajectories) | Training Data | 🔴 BLEEDING-EDGE | Direct training input |
| **SICA** (17%→53% SWE-Bench) | Self-Improving Agent | 🔴 BLEEDING-EDGE | Architecture pattern |
| **ATLAS** (RL for MCP) | Training Framework | 🔴 BLEEDING-EDGE | RL integration |
| **AgentRL** (THUDM) | RL Framework | 🟢 APPLICABLE | Q-learning upgrade |
| **Memory-R1** | Memory RL | 🟡 INTERESTING | Memory operations |
| **Mem0** (48K stars, $24M) | Production Memory | 🟡 INTERESTING | Memory upgrade |
| **continualcode** | Gradient Updates | 🟡 INTERESTING | Real-time learning |
| **Verl-Tool** | Agentic RL | 🔴 BLEEDING-EDGE | Production pipeline |

### 2.3 Architecture Design (From Oracle)

**5-Component Pipeline:**
1. **ActivityCapture** - Tool calls, outcomes, sequences
2. **TrainingDataManager** - Extract patterns, generate JSONL
3. **LoRATrainer** - Unsloth training (existing, 95%)
4. **AdapterRegistry** - Hot-swap, version management
5. **HotSwap** - Zero-downtime adapter switching

---

## 3. GAP ANALYSIS

### 3.1 Identified Gaps (Priority Order)

| Gap | Current State | Solution | Priority | Effort |
|-----|---------------|----------|----------|--------|
| **Outcome→Memory Bridge** | Outcomes in SQLite, not in memory graph | outcome_to_memory_bridge.py | P0 | 2 hours |
| **Training Auto-Trigger** | Manual generate_training_from_system.py | training_trigger.py | P0 | 1 hour |
| **Auto-Injector Hook** | Manual PreAgentMemoryInjector calls | Hook into task() orchestrator | P0 | 1 hour |
| **Adapter Hot-Swap** | gpu-hotswap.py swaps models, not adapters | adapter_hotswap.py | P1 | 4 hours |
| **Training→Deployment** | Train → manual deploy | pipeline_automator.py | P1 | 4 hours |
| **Continuous Learning** | Real-time weight updates only | closed_loop.py | P2 | 8 hours |

### 3.2 Feature Gaps (Bleeding-Edge Synthesis)

| Feature | Current | Target | Approach |
|---------|---------|--------|----------|
| **Tool Sequence Prediction** | Logs sequences | Predict next tool | Train on tool_sequences |
| **Routing Optimization** | Q-learning | Upgrade to AgentRL pattern | Multi-agent reward |
| **Memory Prioritization** | Static 500 tokens | Dynamic by tier | Weight by memory tier |
| **Self-Correction Loop** | Manual feedback | Auto from failed outcomes | Pattern detection |
| **Continuous Training** | Manual triggers | Real-time on threshold | Event-driven pipeline |

---

## 4. IMPLEMENTATION PLAN

### Phase 0: Foundation (Immediate - 4 hours)

**Goal:** Connect existing components with minimal new code

#### Task 0.1: Outcome→Memory Bridge (P0)
```
File: packages/learning_engine/bridges/outcome_to_memory_bridge.py
- Trigger on: every task completion
- Action: Convert outcome → memory entry
- Metadata: success*1.0, recency*0.5, similarity*0.3
- Storage: memory_tiers.db (episodic tier)
```

#### Task 0.2: Training Auto-Trigger (P0)
```
File: packages/training/training_trigger.py
- Trigger: When 50+ new tool_sequences accumulate
- Action: Run generate_training_from_system.py
- Output: datasets/auto_generated.jsonl
- Notify: telegram/console on completion
```

#### Task 0.3: Auto-Injector Hook (P0)
```
File: packages/orchestration/task_hooks.py
- Hook: Pre-task dispatch in task() function
- Action: Call PreAgentMemoryInjector.inject()
- Include: Success patterns, tool usage guidance
- Budget: 500 tokens (existing)
```

### Phase 1: Training Pipeline (Day 1 - 8 hours)

#### Task 1.1: Adapter Hot-Swap System
```
File: frankenstein_engine/adapter_hotswap.py
- Function: load_adapter(), unload_adapter(), swap_adapter()
- Integration: DirectLlamaClient.add_lora()
- Trigger: After successful training validation
- Fallback: Keep current adapter if swap fails
```

#### Task 1.2: Training Pipeline Automator
```
File: packages/training/pipeline_automator.py
- Steps: Generate → Train → Validate → Deploy
- Validation: Run quality gates on generated tool calls
- Deployment: Hot-swap on success, rollback on failure
- Monitoring: Track success rate delta
```

#### Task 1.3: Tool Sequence Training Data
```
File: packages/training/generate_from_sequences.py
- Source: outcomes.db.tool_sequences
- Format: [context, tool_call, outcome] per sequence
- Enrichment: Add "when to use" vs "when NOT to use"
- Target: Balance positive/negative examples
```

### Phase 2: Advanced Features (Day 2-3 - 16 hours)

#### Task 2.1: Self-Correction Loop
```
File: packages/learning_engine/self_correction.py
- Detect: Failed outcomes with retry patterns
- Extract: What tool was wrong, what should have been called
- Generate: Counter-example training data
- Integrate: Add to training pipeline
```

#### Task 2.2: Memory-Weighted Context Injection
```
File: packages/orchestration/weighted_injector.py
- Input: Memory tiers (episodic, semantic, procedural)
- Weight: Tier importance * recency * success
- Output: Prioritized context within 500 token budget
- Include: "Use tool X" vs "Don't use tool X" guidance
```

#### Task 2.3: Multi-Agent Reward Routing
```
File: packages/learning_engine/routing/multi_reward_router.py
- Reward Components:
  - Task completion (0-1)
  - Tool efficiency (calls per task)
  - Latency (ms)
  - Quality score (0-1)
- Learning: Weighted multi-objective optimization
- Output: Optimized agent selection
```

### Phase 3: Bleeding-Edge Synthesis (Day 4-5 - 16 hours)

#### Task 3.1: TOUCAN-Style Data Collection
```
File: packages/data_collection/mcp_trajectory_collector.py
- Collect: Full MCP server interaction trajectories
- Format: TOUCAN compatible (1.5M trajectory format)
- Storage: datasets/mcp_trajectories.jsonl
- Target: Eventually submit to TOUCAN dataset
```

#### Task 3.2: SICA-Style Self-Improvement
```
File: packages/learning_engine/sica_style.py
- Monitor: Per-task improvement over time
- Trigger: Retrain when success rate drops
- Feedback: User corrections → immediate weight update
- Metrics: Track improvement % over baseline
```

#### Task 3.3: RL Integration (ATLAS/AgentRL style)
```
File: packages/learning_engine/rl_integration.py
- Framework: Multi-turn reward signals
- Tools: Success, efficiency, latency, quality
- Training: Episodic learning from tool sequences
- Integration: Connect to existing Q-learning
```

---

## 5. TECHNICAL SPECIFICATIONS

### 5.1 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLOSED SELF-LEARNING LOOP                          │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌─────────┐     ┌─────────────┐     ┌──────────┐     ┌─────────────┐
     │  User   │────▶│ Intelligence │────▶│  Agent   │────▶│   Tool      │
     │ Request │     │  (route)    │     │ Dispatch │     │   Call      │
     └─────────┘     └─────────────┘     └──────────┘     └─────────────┘
                                                                     │
                                                                     ▼
     ┌─────────────┐     ┌─────────────┐     ┌────────────┐     ┌──────────┐
     │  Hot-Swap   │◀────│   LoRA      │◀────│  Training  │◀────│  Outcome │
     │  Adapter    │     │   Trainer   │     │  Pipeline  │     │  Logger  │
     └─────────────┘     └─────────────┘     └────────────┘     └──────────┘
          │                                                                   │
          │                   ┌─────────────┐                               │
          └──────────────────▶│   Memory    │◀──────────────────────────────┘
                              │   Injection │
                              └─────────────┘
```

### 5.2 Database Schema Updates

#### New Table: training_runs
```sql
CREATE TABLE training_runs (
    id INTEGER PRIMARY KEY,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    source_data TEXT,           -- 'auto_generated', 'manual', 'correction'
    examples_count INTEGER,
    accuracy_before REAL,
    accuracy_after REAL,
    adapter_path TEXT,
    deployed BOOLEAN,
    hot_swap_time_ms INTEGER,
    success_rate_delta REAL
);
```

#### New Table: memory_tier_weights
```sql
CREATE TABLE memory_tier_weights (
    tier TEXT PRIMARY KEY,      -- 'episodic', 'semantic', 'procedural'
    base_weight REAL,
    recency_decay REAL,         -- 0.5
    success_bonus REAL,         -- 1.0
    last_updated TIMESTAMP
);
```

### 5.3 API Endpoints (New MCP Tools)

| Endpoint | Purpose | Input | Output |
|----------|---------|-------|--------|
| `trigger_training` | Manual training trigger | threshold_count | run_id |
| `get_training_status` | Check running training | run_id | status |
| `swap_adapter` | Hot-swap LoRA adapter | adapter_name | success |
| `get_active_adapter` | Current adapter info | - | adapter_info |
| `inject_memory_weighted` | Weighted injection | task_context | context_tokens |
| `get_self_improvement` | Improvement metrics | time_range | delta_percentage |

---

## 6. IMPLEMENTATION ORDER

### Week 1: Foundation Loop

| Day | Task | Deliverable | Dependencies |
|-----|------|-------------|--------------|
| Mon | 0.1 | outcome_to_memory_bridge.py | None |
| Mon | 0.2 | training_trigger.py | None |
| Mon | 0.3 | task_hooks.py | None |
| Tue | 1.1 | adapter_hotswap.py | Phase 0 complete |
| Tue | 1.2 | pipeline_automator.py | 1.1 |
| Wed | 1.3 | generate_from_sequences.py | outcome logging |

### Week 2: Advanced Features

| Day | Task | Deliverable | Dependencies |
|-----|------|-------------|--------------|
| Thu | 2.1 | self_correction.py | Phase 1 |
| Fri | 2.2 | weighted_injector.py | Phase 1 |
| Mon | 2.3 | multi_reward_router.py | Phase 1 |

### Week 3: Bleeding-Edge

| Day | Task | Deliverable | Dependencies |
|-----|------|-------------|--------------|
| Tue | 3.1 | mcp_trajectory_collector.py | Phase 2 |
| Wed | 3.2 | sica_style.py | Phase 2 |
| Thu | 3.3 | rl_integration.py | Phase 2 |

---

## 7. VALIDATION METRICS

### 7.1 Success Criteria

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **Tool Call Accuracy** | 95% | 98% | Training accuracy |
| **False Positive Rate** | High (simple math) | <5% | Negative examples |
| **Routing Success** | 70% | 85% | Agent selection |
| **Training Latency** | Manual | <30 min | Auto-trigger |
| **Hot-Swap Time** | Manual | <5 sec | Adapter swap |
| **Self-Improvement** | 0% | >10% | Weekly delta |

### 7.2 Monitoring

- **Real-time**: Success rate, tool call count, latency
- **Daily**: Training run count, adapter swaps
- **Weekly**: Self-improvement delta, routing accuracy
- **Monthly**: TOUCAN-compatible trajectory count

---

## 8. RISKS AND MITIGATION

| Risk | Impact | Mitigation |
|------|--------|-------------|
| **Training data imbalance** | Model over-triggers | Add negative examples |
| **Hot-swap failure** | System downtime | Fallback to current adapter |
| **Memory injection overflow** | Context length errors | Hard token budget |
| **Q-learning divergence** | Routing instability | EWC regularization |
| **Continuous training loop** | Infinite retraining | Max 1 run/day |

---

## 9. RESOURCE REQUIREMENTS

### 9.1 Compute

| Resource | Requirement | Usage |
|----------|-------------|-------|
| **GPU** | RTX 3080 Ti (12GB) | LoRA training, inference |
| **Storage** | 50GB additional | Trajectories, adapters |
| **RAM** | 32GB | SQLite, batch processing |

### 9.2 Dependencies

- **Python**: 3.10+
- **Key Libraries**: unsloth, llama-cpp-python, sqlite3
- **MCPs**: All existing 8 MCPs

---

## 10. APPENDIX

### A. File Structure After Implementation

```
N-Xyme_MIND/
├── packages/
│   ├── learning_engine/
│   │   ├── bridges/
│   │   │   └── outcome_to_memory_bridge.py  # NEW
│   │   ├── self_correction.py               # NEW
│   │   └── routing/
│   │       └── multi_reward_router.py        # NEW
│   ├── training/
│   │   ├── training_trigger.py               # NEW
│   │   ├── pipeline_automator.py              # NEW
│   │   ├── generate_from_sequences.py        # NEW
│   │   └── generate_training_from_system.py  # EXISTING
│   ├── orchestration/
│   │   ├── task_hooks.py                      # NEW
│   │   └── weighted_injector.py              # NEW
│   └── data_collection/
│       └── mcp_trajectory_collector.py       # NEW
├── frankenstein_engine/
│   ├── adapter_hotswap.py                    # NEW
│   └── adapters/                             # EXISTING
└── datasets/
    ├── auto_generated.jsonl                   # NEW
    └── mcp_trajectories.jsonl                # NEW
```

### B. Key Code Snippets

#### Hot-Swap Adapter
```python
def swap_adapter(client, new_adapter_path):
    client.unload_lora()
    client.load_lora(new_adapter_path)
    return {"status": "swapped", "adapter": new_adapter_path}
```

#### Outcome→Memory Bridge
```python
def bridge_outcome_to_memory(outcome):
    memory_entry = {
        "content": f"Task: {outcome.task_description}, Tool: {outcome.tool_used}, Success: {outcome.success}",
        "kind": "episodic",
        "metadata": {"success_weight": 1.0 if outcome.success else 0.0}
    }
    memory_client.write(memory_entry)
```

---

**END OF MASTERPLAN**

**Next Steps:** Start implementing Phase 0 tasks immediately.
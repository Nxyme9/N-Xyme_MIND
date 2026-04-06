# N-Xyme MIND - Learning Integration Masterplan

## Current State - SURPRISE! 🎉

The system already has **6 routing strategies** built-in:

| Strategy | Component | Status |
|----------|-----------|--------|
| 1 | Trigger-based | Working |
| 2 | ML-based (ml_router) | Working |
| 3 | Memory-augmented | Working |
| 4 | Local model analysis | Working |
| 5 | Learning-based (routing_optimizer) | Working |
| 6 | Keyword fallback | Working |

**The gap**: AdvancedLearningEngine (Q-Learning, Bandits) is NOT connected to Strategy 5.

---

## Masterplan: Connect Advanced Learning to Router

### Phase 1: Bridge AdvancedLearningEngine into Router (CRITICAL)

In `unified_router.py`, Strategy 5 section:
- Add AdvancedLearningEngine initialization
- Use Q-Learning for action selection instead of simple EMA
- Map ActionType results to agent names

### Phase 2: Add Semantic Embedding Store

Create `src/memory/embedding_store.py`:
- Task similarity search using embeddings
- Find similar successful past tasks
- Recommend agents based on history

### Phase 3: Integrate Skill Lifecycle + Prompt Evolution

- Wire skill_lifecycle.py into decision enhancement
- Wire prompt_evolution.py for optimization

### Phase 4: Observability

- Build metrics dashboard
- A/B test Q-Learning vs current

---

## Implementation Order

| # | Task | Why | Effort |
|---|------|-----|--------|
| 1 | Connect AdvancedLearning to Strategy 5 | Core ML missing | Medium |
| 2 | Create embedding store | Semantic search | Medium |
| 3 | Add SkillLifecycle integration | Better matching | Low |
| 4 | Build metrics dashboard | Visibility | Low |

---

## Files to Modify

1. `src/tools/intelligence/unified_router.py` - Add AdvancedLearning
2. `src/memory/embedding_store.py` - NEW

---

## Success Metrics

1. Q-Learning makes routing decisions
2. Bandit statistics improve selection
3. Embedding similarity finds related tasks
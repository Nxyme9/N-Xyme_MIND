# OMO Migration Plan: .sisyphus → memory_store + learning_engine

## Overview

**Goal**: Consolidate 13 SQLite databases in `.sisyphus/` into unified ML-native storage using existing `memory_store` and `learning_engine` components.

**Current State**: 66+ files directly reference `.sisyphus/`, 13 SQLite DBs
**Target State**: Unified storage via memory_store (vector+graph+relational) + learning_engine (Q-Learning)

---

## Executive Summary

| Phase | Risk | Target | Duration | Status |
|-------|------|--------|----------|--------|
| P1 | LOW | memory.db, graphs.db → memory_store | 1 week | ⏳ Pending |
| P2 | MEDIUM | state.db, context.db, messages.db → memory_store | 1-2 weeks | ⏳ Pending |
| P3 | HIGH | routing.db, outcomes.db → learning_engine | 2 weeks | ⏳ Pending |

---

## Pre-Flight Checks (Required Before Starting)

```bash
# 1. Verify infrastructure health
python3 -c "from packages.memory_store import MemoryManager; print('MemoryStore: OK')"
python3 -c "from packages.learning_engine import OutcomeLogger; print('LearningEngine: OK')"

# 2. Backup all .sisyphus DBs
mkdir -p .sisyphus-backup-$(date +%Y%m%d)
cp .sisyphus/*.db .sisyphus-backup-$(date +%Y%m%d)/

# 3. Identify all files requiring updates
grep -r "\.sisyphus" packages/ --include="*.py" -l > files_to_update.txt
```

---

## Phase 1: memory.db + graphs.db → memory_store (LOW RISK)

### Files to Create

1. `packages/memory_store/migrations/migrate_sisyphus_memory.py`
2. `packages/memory_store/migrations/migrate_sisyphus_graphs.py`

### Files to Modify

- `packages/context_store/archive_scanner.py`
- `packages/nx_mind_mcp/nx_mind_mcp/session_writer.py`
- `packages/platform-layer/tui/chat_backends.py`

### Tests

```bash
python3 -c "
from packages.memory_store import MemoryManager
mm = MemoryManager()
result = mm.on_memory_write('test_001', 'test content', 'episodic', 'session')
assert result.success
print('MemoryStore: OK')

from packages.memory_store.stores.graph_store import KnowledgeGraph
kg = KnowledgeGraph()
kg.add_node('test', 'type', {'label': 'test'})
assert kg.get_node('test') is not None
print('GraphStore: OK')
"
```

### Rollback

```bash
cp .sisyphus-backup-*/memory.db .sisyphus/memory.db
cp .sisyphus-backup-*/graphs.db .sisyphus/graphs.db
git checkout -- packages/memory_store/
```

---

## Phase 2: state.db + context.db + messages.db → memory_store (MEDIUM RISK)

### Files to Create

1. `packages/memory_store/stores/session_store.py` - NEW Session store

### Files to Modify

- `packages/orchestration/unified_session_manager.py` - Add dual-write
- `packages/nx_mind_mcp/nx_mind_mcp/bmad_state.py` - Add dual-write
- `packages/orchestration/tasks/lifecycle.py` - Add dual-write
- `packages/brain_mcp/namespaces/session.py` - Update to use SessionStore

### Pattern: Dual-Write

During transition, write to BOTH `.sisyphus` AND `memory_store`:

```python
def save_session(session):
    # Legacy (backward compat)
    legacy_conn.execute("INSERT INTO sessions ...", ...)
    legacy_conn.commit()
    
    # New store
    session_store.write_session(session)
    
    # Verify consistency
    assert data_matches(legacy_data, new_data)
```

### Rollback

```bash
cp .sisyphus-backup-*/state.db .sisyphus/state.db
cp .sisyphus-backup-*/context.db .sisyphus/context.db
cp .sisyphus-backup-*/messages.db .sisyphus/messages.db
git checkout -- packages/orchestration/ packages/nx_mind_mcp/ packages/brain_mcp/
```

---

## Phase 3: routing.db + outcomes.db → learning_engine (HIGH RISK)

### Files to Create

1. `packages/learning_engine/migrations/migrate_routing_data.py`

### Files to Modify

- `packages/learning_engine/outcome_logger.py`
- `packages/learning_engine/delegation/db.py`
- `packages/learning_engine/routing/adaptive_router.py`
- `packages/intelligence/router/unified.py` - A/B routing
- `packages/platform-layer/dashboard/routing-dashboard.py`

### A/B Testing Pattern

```python
class UnifiedRouter:
    def __init__(self):
        self.legacy_routing = LegacyRouting()  # .sisyphus
        self.learning_routing = LearningRouting()  # memory_store
        self.ab_ratio = 0.01  # Start with 1% new
    
    def route(self, task):
        if random.random() < self.ab_ratio:
            return self.learning_routing.route(task)
        return self.legacy_routing.route(task)
```

### Rollback

```bash
cp .sisyphus-backup-*/routing.db .sisyphus/routing.db
cp .sisyphus-backup-*/outcomes.db .sisyphus/outcomes.db
sed -i 's/self.ab_ratio = [0-9.]*/self.ab_ratio = 0/' packages/intelligence/router/unified.py
git checkout -- packages/learning_engine/
```

---

## Success Criteria

### Phase 1
- [ ] All memories queryable via memory_store.search_memories()
- [ ] Graph nodes traversable via KnowledgeGraph.traverse()
- [ ] No regression in MCP tool response times

### Phase 2
- [ ] Sessions load from memory_store
- [ ] Context retrieval < 100ms
- [ ] Inter-agent messages flow correctly

### Phase 3
- [ ] Q-Learning routing >= legacy accuracy
- [ ] Outcome logging < 50ms
- [ ] A/B test success rate > 80% at 50% traffic

### Overall
- [ ] Zero data loss
- [ ] All 66+ files updated
- [ ] .sisyphus deprecated (read-only fallback)

---

## Showstoppers (Must Solve First - From Momus)

1. **No Q-Learning weight migration path** → Document exact schema mapping
2. **No atomic rollback mechanism** → Create one-command rollback script
3. **Schema mismatch state.db → memory_store** → Document exact field-to-field mapping

---

## Timeline

| Approach | Total Duration |
|----------|----------------|
| Aggressive | 2-3 weeks |
| Conservative | 4-6 weeks |

---

## Created By

- Explore: Mapped 66 files, 13 DBs
- Librarian: LangGraph, Mem0, Letta patterns
- Oracle: 3-phase architecture
- Momus: 5 risks, 3 showstoppers
- Plan: Detailed implementation scripts
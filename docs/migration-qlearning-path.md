# Q-Learning Migration Path

> Design document for migrating routing.db and outcomes.db to learning_engine Q-Learning system.

---

## Overview

This document describes how to migrate:
1. **routing.db/agent_weights** → learning_engine Q-table (Q-learning)
2. **outcomes.db** → learning_engine outcome_logger

The goal is to preserve Q-values and ensure routing decisions remain consistent after migration.

---

## 1. Agent Weights Migration

### Source Schema: `routing.db/agent_weights`

| Column | Type | Description |
|--------|------|-------------|
| `agent` | TEXT PRIMARY KEY | Agent name (hephaestus, explore, etc.) |
| `success_rate` | REAL | Q-value base (0.0-1.0) |
| `avg_latency_ms` | REAL | Average latency |
| `total_tasks` | INTEGER | Total tasks handled |
| `success_count` | INTEGER | Successful tasks |
| `failure_count` | INTEGER | Failed tasks |
| `by_level` | TEXT | JSON per-level stats |
| `last_updated` | REAL | Unix timestamp |

### Target: `learning_engine/rl/q_learning.py`

The Q-Learning system uses:
- **QTable**: dict[state_key][action] → float
- **QState**: task + context_hash
- **ActionType**: explore, delegate, oracle, librarian, hephaestus, multimodal

### Migration Strategy

#### Step 1: Extract current Q-values

```python
# From routing.db
source_data = sqlite3.connect("routing.db").execute("""
    SELECT agent, success_rate, avg_latency_ms, total_tasks, 
           success_count, failure_count, by_level
    FROM agent_weights
""").fetchall()
```

#### Step 2: Map agent names to ActionType

| routing.db agent | ActionType |
|-----------------|------------|
| explore | ActionType.EXPLORE |
| librarian | ActionType.LIBRARIAN |
| oracle | ActionType.ORACLE |
| hephaestus | ActionType.HEPHAESTUS |
| metis | ActionType.DELEGATE |
| momus | ActionType.DELEGATE |
| plan | ActionType.DELEGATE |
| atlas | ActionType.DELEGATE |
| sisyphus-junior | ActionType.DELEGATE |
| prometheus | ActionType.DELEGATE |
| sisyphus | ActionType.DELEGATE |
| multimodal-looker | ActionType.MULTIMODAL |

#### Step 3: Initialize Q-table with source values

```python
from packages.learning_engine.rl.q_learning import QTable, ActionType

q_table = QTable()

# For each agent, create a default state with their Q-value
default_state = "default"  # Base state for all agents

for row in source_data:
    agent, success_rate, avg_latency, total_tasks, success, failure, by_level = row
    
    # Map agent to ActionType
    action = agent_to_action[agent]
    
    # Set Q-value directly (already normalized 0-1)
    q_table.set(default_state, action, success_rate)
    
    # Store metrics in metadata (for latency-aware selection)
    metadata[agent] = {
        "avg_latency_ms": avg_latency,
        "total_tasks": total_tasks,
        "success_count": success,
        "failure_count": failure,
        "by_level": json.loads(by_level or "{}")
    }
```

#### Step 4: Preserve per-level weights

The `by_level` column contains L1-L5 stats. These become separate state keys:

```python
# Create level-specific Q-values
for agent, level_data in by_level.items():
    level_state = f"level_{agent}"
    for level, stats in level_data.items():
        q_table.set(level_state, action, stats["success_rate"])
```

---

## 2. Outcomes Migration

### Source Schema: `outcomes.db/outcomes`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment |
| `task_id` | TEXT | Unique task identifier |
| `task_description` | TEXT | Description |
| `task_type` | TEXT | implementation/research/review/fix |
| `agent` | TEXT | Agent that handled |
| `level` | INTEGER | L1-L5 complexity |
| `success` | INTEGER | 0 or 1 |
| `latency_ms` | REAL | Execution time |
| `tokens_used` | INTEGER | Token count |
| `quality_score` | REAL | User feedback (0-1) |
| `context_json` | TEXT | Additional context |
| `timestamp` | TEXT | ISO timestamp |

### Target: `learning_engine/outcome_logger.py`

The outcome_logger uses:
- **DelegationOutcome** dataclass
- **ToolSequence** dataclass (Phase 3)

### Migration Strategy

#### Step 1: Extract outcomes

```python
source_outcomes = sqlite3.connect("outcomes.db").execute("""
    SELECT task_id, task_description, task_type, agent, level,
           success, latency_ms, tokens_used, quality_score, 
           context_json, timestamp
    FROM outcomes
""").fetchall()
```

#### Step 2: Replay into outcome_logger

```python
from packages.learning_engine.outcome_logger import OutcomeLogger, DelegationOutcome

logger = OutcomeLogger()

for row in source_outcomes:
    outcome = DelegationOutcome(
        task_id=row["task_id"],
        task_description=row["task_description"],
        task_type=row["task_type"],
        agent=row["agent"],
        level=row["level"],
        success=bool(row["success"]),
        latency_ms=row["latency_ms"],
        tokens_used=row["tokens_used"] or 0,
        quality_score=row["quality_score"],
        context=json.loads(row["context_json"] or "{}"),
        timestamp=row["timestamp"]
    )
    logger.log_outcome(outcome)
```

#### Step 3: Update Q-table from historical outcomes

```python
from packages.learning_engine.rl.q_learning import QLearningAgent

rl_agent = QLearningAgent()

# Replay all outcomes to rebuild Q-values
for outcome in source_outcomes:
    state = f"task_type:{outcome['task_type']}|level:{outcome['level']}"
    action = agent_to_action[outcome['agent']]
    reward = 1.0 if outcome['success'] else 0.0
    
    rl_agent.update(state, action, reward)
```

---

## 3. Verification Steps

### Verification 1: Q-values preserved

```python
# Compare source total Q vs target total Q
source_total = sum(row["success_rate"] for row in source_data)

target_q_values = []
for state, actions in q_table.values.items():
    for action, q in actions.items():
        target_q_values.append(q)
target_total = sum(target_q_values)

print(f"Source Q total: {source_total}")
print(f"Target Q total: {target_total}")
print(f"Difference: {abs(source_total - target_total)}")
```

**Acceptable tolerance**: < 0.01 (1% difference)

### Verification 2: Routing consistency

```python
# Test that routing still chooses same agents
def source_select_agent(task_type, level):
    """Original routing logic (from routing.db triggers)"""
    # ... original implementation

def target_select_agent(task_type, level):
    """New Q-learning routing"""
    state = f"task_type:{task_type}|level:{level}"
    return q_table.get_best_action(state)

# Compare for 100 random tasks
discrepancies = 0
for _ in range(100):
    task_type, level = random.choice(task_types), random.choice(levels)
    if source_select_agent(task_type, level) != target_select_agent(task_type, level):
        discrepancies += 1

print(f"Routing discrepancies: {discrepancies}/100")
```

**Acceptable tolerance**: < 5% discrepancy

### Verification 3: Outcome replay accuracy

```python
# Verify outcome_logger can replay all outcomes
logger = OutcomeLogger()
count = logger.get_outcome_count()

source_count = len(source_outcomes)
print(f"Source outcomes: {source_count}")
print(f"Target outcomes: {count}")
print(f"Match: {count == source_count}")
```

---

## 4. Migration Script Structure

```
scripts/
├── migrate_qlearning.sh          # Main migration runner
├── migrate_01_extract_weights.py # Step 1: Extract agent_weights
├── migrate_02_init_qtable.py     # Step 2: Initialize Q-table
├── migrate_03_replay_outcomes.py # Step 3: Replay outcomes
└── migrate_04_verify.py          # Step 4: Verify migration
```

### migrate_qlearning.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== Q-Learning Migration ==="

echo "Step 1: Extracting agent_weights..."
python3 scripts/migrate_01_extract_weights.py

echo "Step 2: Initializing Q-table..."
python3 scripts/migrate_02_init_qtable.py

echo "Step 3: Replaying outcomes..."
python3 scripts/migrate_03_replay_outcomes.py

echo "Step 4: Verifying migration..."
python3 scripts/migrate_04_verify.py

echo "=== Migration Complete ==="
```

---

## 5. Rollback Integration

The rollback script (`scripts/migration_rollback.sh`) handles Q-Learning migration rollback:

1. **Stop MCP servers** (prevents new outcomes being logged)
2. **Backup current state** (including Q-table if persisted)
3. **Delete learning_engine data** (Q-table, outcomes in memory_store)
4. **Restore routing.db and outcomes.db** (from .sisyphus.backup/)
5. **Restart MCP servers** (reconnect original routing)
6. **Verify delegation works** (test that routing.db is readable)

### Rollback verification

```bash
# After rollback, verify routing.db is intact
sqlite3 .sisyphus/routing.db "SELECT agent, success_rate FROM agent_weights;"

# Verify outcomes.db is intact
sqlite3 .sisyphus/outcomes.db "SELECT COUNT(*) FROM outcomes;"

# Test delegation still works (should use routing.db, not Q-table)
python3 -c "from packages.learning_engine.routing.optimizer import AdaptiveRouter; r = AdaptiveRouter(); print(r.route('test task'))"
```

---

## 6. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Q-values not preserved | Store original values in meta_json during migration |
| Routing changes unexpectedly | Run comparison test before/after (Verification 2) |
| Outcomes lost | Backup outcomes.db before migration |
| Performance regression | Run benchmark before/after (latency check) |
| Q-table corruption | Persist Q-table to disk after each update |

---

## 7. Post-Migration Tasks

1. **Update MCP tools** - Point `route_task` to use Q-table instead of routing.db
2. **Update `record_outcome`** - Write to outcome_logger (not outcomes.db)
3. **Update monitoring** - Dashboard should read from Q-table
4. **Update backups** - Include Q-table in regular backups
5. **Update documentation** - Remove references to routing.db for routing

---

## Summary

| Migration Step | Source | Target | Verification |
|---------------|--------|--------|--------------|
| Agent weights | routing.db/agent_weights | QTable (QState → ActionType) | Q-value sum match |
| Outcomes | outcomes.db/outcomes | OutcomeLogger | Count match |
| Routing logic | triggers table + weights | QLearningAgent | <5% discrepancy |
| Metrics | routing.db metrics | meta_json per agent | Latency preserved |
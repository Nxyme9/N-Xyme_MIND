# Phase 2: Graph Memory — Detailed Implementation Plan

> **Date:** 2026-04-08
> **Effort:** 5-7 days
> **Risk:** MEDIUM (Neo4j dependency, fallback to SQLite)
> **Dependencies:** Phase 0 complete
> **Oracle Review:** REQUIRED for Task 2.4

---

## Executive Summary

Phase 2 replaces SQL LIKE search with Neo4j graph traversal + temporal pattern analysis. Existing `Neo4jGraphStore` already exists with connection pooling, retry logic, and SQLite fallback. Main work: populate graph, add Cypher queries, integrate with RRF fusion.

**GO/NO-GO: GO** — Graph store already exists, low risk with SQLite fallback.

---

## Task 2.1: Graph Store Integration

### Files to Modify
- `packages/memory_core/stores/graph_store.py`

### Node Types to Add

```
Nodes:
  Task: id, task_text, embedding (384-dim), task_type, created_at, level, domain
  Agent: id, agent_type, capabilities[], performance_score
  Outcome: id, task_id, agent_id, success, latency_ms, tokens, quality, created_at
  Session: id, created_at, agent_count, task_count, success_rate
  Tool: id, tool_name, tool_type
  Skill: id, skill_name, category
  Pattern: id, pattern_type, description, frequency, last_seen

Edges:
  Task --[PERFORMED_BY]--> Agent
  Task --[RESULTED_IN]--> Outcome
  Task --[BELONGED_TO]--> Session
  Task --[USED_TOOL]--> Tool
  Task --[REQUIRED_SKILL]--> Skill
  Agent --[HAS_SKILL]--> Skill
  Task --[SIMILAR_TO]--> Task (similarity score)
  Task --[NEXT_TASK]--> Task (gap_seconds)
```

### Neo4j Configuration

Add to `.env`:
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password
NEO4J_DATABASE=neo4j
```

### Migration Script

```python
# scripts/migrate_memory_to_graph.py
import sqlite3
from packages.memory_core.stores.graph_store import Neo4jGraphStore

def migrate():
    graph = Neo4jGraphStore()
    conn = sqlite3.connect(".sisyphus/routing.db")
    
    cursor = conn.execute("""
        SELECT task_description, agent, success, latency_ms, tokens_used, timestamp 
        FROM outcomes WHERE timestamp > date('now', '-90 days')
    """)
    
    for row in cursor.fetchall():
        task, agent, success, latency, tokens, created = row
        task_id = f"task:{hash(task) & 0xFFFFFFFF:08x}"
        
        graph.execute_cypher("""
            MERGE (t:Task {id: $id})
            SET t.task_text = $text, t.created_at = $created
        """, id=task_id, text=task[:500], created=created)
        
        graph.execute_cypher("""
            MERGE (a:Agent {id: $id})
            SET a.agent_type = $type
        """, id=f"agent:{agent}", type=agent)
        
        graph.execute_cypher("""
            MATCH (t:Task {id: $task_id})
            MATCH (a:Agent {id: $agent_id})
            MERGE (t)-[:PERFORMED_BY]->(a)
        """, task_id=task_id, agent_id=f"agent:{agent}")
    
    conn.close()
    print(f"Migration complete. Nodes: {graph.stats()['nodes']}")
```

### Success Criteria
- Graph connection established
- Basic CRUD operations work
- 90 days of outcomes migrated

---

## Task 2.2: Graph-Based Context Retrieval

### New Method in Memory Router

```python
def _graph_retrieve(self, query: str, top_k: int = 10, time_window_days: int = 7) -> List[dict]:
    """Graph-based context retrieval for routing decisions."""
    embedding = self._cache.encode(query)
    
    results = self._graph.execute_cypher("""
        MATCH (t:Task)-[:RESULTED_IN]->(o:Outcome {success: true})
        WHERE o.created_at > datetime('now') - duration({days: $days})
        MATCH (t)-[:PERFORMED_BY]->(a:Agent)
        WITH a, count(t) as success_count, max(o.created_at) as last_success
        RETURN a.id as agent_id, success_count, 
               datetime.duration.inSeconds(last_success, datetime()).seconds as seconds_ago
        ORDER BY success_count DESC
        LIMIT $top_k
    """, days=time_window_days, top_k=top_k)
    
    return results
```

### Key Cypher Queries

**Find agents that succeeded with similar tasks recently:**
```cypher
MATCH (a:Agent)<-[:PERFORMED_BY]-(t:Task)-[:RESULTED_IN]->(o:Outcome {success: true})
WHERE o.created_at > datetime('now') - duration({days: 7})
RETURN a.id, count(t) as successes, max(o.created_at) as last
ORDER BY successes DESC LIMIT 5
```

**Time-decay weighted agent success:**
```cypher
MATCH (a:Agent)<-[:PERFORMED_BY]-(t:Task)-[:RESULTED_IN]->(o:Outcome {success: true})
WITH a, count(o) as total, collect(o.created_at) as dates
WITH a, total, reduce(w = 0, d IN dates | w + 
  CASE WHEN d > datetime('now') - duration({days: 7}) THEN 1.0
       WHEN d > datetime('now') - duration({days: 30}) THEN 0.5
       ELSE 0.2 END) as decay_weight
RETURN a.id, total, decay_weight ORDER BY decay_weight DESC
```

### Success Criteria
- Context retrieval accuracy > 80%
- Latency < 200ms

---

## Task 2.3: Temporal Pattern Mining

### Files to Modify
- `packages/learning_engine/cross_session_transfer.py`

### Implementation

```python
def extract_temporal_patterns(self) -> List[dict]:
    """Extract recurring task sequences from graph."""
    patterns = self._graph.execute_cypher("""
        MATCH (t1:Task)-[:NEXT_TASK]->(t2:Task)
        WITH t1.task_type as first, t2.task_type as second, count(*) as frequency
        WHERE frequency > 2
        RETURN first, second, frequency ORDER BY frequency DESC
    """)
    
    for p in patterns:
        pattern_id = f"pattern:{p['first']}_{p['second']}"
        self._graph.execute_cypher("""
            MERGE (p:Pattern {id: $id})
            SET p.first_type = $first, p.second_type = $second, p.frequency = $freq
        """, id=pattern_id, first=p['first'], second=p['second'], freq=p['frequency'])
    
    return patterns
```

### Time-Decay Weighting

Use exponential decay with 7-day half-life:
```
weight = base × e^(-λ×t) where λ = ln(2)/7
```

### Success Criteria
- Patterns identified with > 70% precision
- Patterns stored in graph

---

## Task 2.4: Graph-Enhanced Memory Router

### ⚠️ ORACLE REVIEW REQUIRED

### Files to Modify
- `packages/memory_core/router.py`
- `packages/memory_core/retrievers/fusion.py`

### Enhanced RRF with Temporal Weighting

```python
def rrf_fusion_enhanced(results_lists, k=60, retriever_weights=None, time_decay=True):
    if retriever_weights is None:
        retriever_weights = {"semantic": 0.4, "keyword": 0.4, "graph": 0.2}
    
    scores = defaultdict(float)
    for i, results in enumerate(results_lists):
        source = results[0].get("source", "unknown") if results else "unknown"
        weight = retriever_weights.get(source, 1.0)
        
        for rank, result in enumerate(results, 1):
            rid = result.get("id", str(rank))
            rrf_score = (1.0 / (k + rank)) * weight
            
            if time_decay and "created_at" in result.get("metadata", {}):
                age_days = (now - created).days
                if age_days < 30:
                    rrf_score *= (1.0 - (age_days / 30) * 0.5)
            
            scores[rid] += rrf_score
    
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

### Success Criteria
- Search precision > 85%
- Recall improvement > 20% over SQL baseline

---

## Files Modified

| File | Action | Description |
|------|--------|-------------|
| `packages/memory_core/stores/graph_store.py` | MODIFY | Add node/edge type helpers |
| `packages/memory_core/router.py` | MODIFY | Add graph retrieval |
| `packages/memory_core/retrievers/fusion.py` | MODIFY | Enhanced RRF with temporal decay |
| `packages/learning_engine/cross_session_transfer.py` | MODIFY | Temporal pattern extraction |
| `scripts/migrate_memory_to_graph.py` | CREATE | Migration script |

---

## Rollback

```bash
# Disable graph features
echo "USE_GRAPH=false" >> .env
# Falls back to SQLiteGraphStore automatically
```

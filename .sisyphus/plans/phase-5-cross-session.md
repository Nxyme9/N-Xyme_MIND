# Phase 5: Cross-Session Transfer — Detailed Masterplan

> **Duration:** 5-7 days
> **Risk:** MEDIUM
> **Dependencies:** Phase 0 + Phase 1 + Phase 3 (EWC) complete
> **Oracle Review:** REQUIRED for Task 5.1

---

## Executive Summary

Phase 5 enables the system to **remember across sessions**. Currently, each session starts fresh. After this phase, the system transfers learned knowledge from previous sessions to new ones.

**GO/NO-GO:** Only proceed after Phase 3 (EWC) is stable with ≥50 transfer attempts.

---

## Tasks Overview

| Task | Name | Effort | Risk | Dependencies |
|------|------|--------|------|--------------|
| 5.1 | Knowledge Graph | 2 days | MEDIUM | Phase 2 (Graph) |
| 5.2 | Transferability Scoring | 1 day | LOW | 5.1 |
| 5.3 | Session Context Injection | 1.5 days | MEDIUM | 5.2 |
| 5.4 | EWC Integration | 1.5 days | HIGH | Phase 3 (EWC) |

---

## Task 5.1: Knowledge Graph Migration

### What It Does
Replace JSON file storage with Neo4j graph nodes for knowledge.

### Node Types
```
Decision: id, context, decision, rationale, outcome, confidence
Lesson: id, context, lesson, frequency, last_applied
Pattern: id, pattern_type, description, frequency, success_rate
Principle: id, name, description, domain, applicability
AntiPattern: id, name, description, symptoms, solutions
```

### Edge Types
```
Decision --[DERIVED_FROM]--> Lesson
Decision --[SUPPORTS]--> Principle
Pattern --[SIMILAR_TO]--> Pattern
Lesson --[CONTRADICTS]--> AntiPattern
```

### Implementation

```python
# packages/learning_engine/knowledge_graph.py

class KnowledgeGraph:
    def __init__(self, graph_store):
        self.graph = graph_store
    
    def store_decision(self, context: str, decision: str, 
                       rationale: str, outcome: str) -> str:
        """Store a decision node."""
        node_id = f"decision:{hash(context) & 0xFFFFFFFF:08x}"
        self.graph.execute_cypher("""
            MERGE (d:Decision {id: $id})
            SET d.context = $context,
                d.decision = $decision,
                d.rationale = $rationale,
                d.outcome = $outcome,
                d.created_at = datetime()
        """, id=node_id, context=context, decision=decision, 
            rationale=rationale, outcome=outcome)
        return node_id
    
    def find_related_lessons(self, context: str) -> list:
        """Find lessons related to current context."""
        embedding = get_embedding_cache().encode(context)
        results = self.graph.execute_cypher("""
            MATCH (l:Lesson)
            WHERE l.context CONTAINS $keyword
            RETURN l.id, l.lesson, l.frequency
            ORDER BY l.frequency DESC
            LIMIT 5
        """, keyword=context[:50])
        return results
```

### Verification
```bash
.venv/bin/python3 -c "
from packages.learning_engine.knowledge_graph import KnowledgeGraph
kg = KnowledgeGraph(graph_store)
id = kg.store_decision('routing slow', 'use LinUCB', 'faster than neural', 'success')
print(f'Stored decision: {id}')
related = kg.find_related_lessons('routing slow')
print(f'Found {len(related)} related lessons')
"
```

### Success Criteria
- [ ] All 5 node types created
- [ ] All 4 edge types working
- [ ] Query latency < 200ms

---

## Task 5.2: Transferability Scoring

### What It Does
Score how transferable a piece of knowledge is from one session to another.

### Formula
```
transferability = 0.35 × generalizability 
               + 0.35 × outcome_weight 
               + 0.15 × repetition 
               + 0.15 × cross_session_validation
```

### Implementation

```python
# packages/learning_engine/transferability.py

class TransferabilityScorer:
    def __init__(self, graph_store):
        self.graph = graph_store
    
    def score(self, knowledge_id: str, target_context: str) -> float:
        """Score how well knowledge transfers to target context."""
        
        # 1. Generalizability (how broadly applicable)
        generalizability = self._calc_generalizability(knowledge_id)
        
        # 2. Outcome weight (how successful was it)
        outcome_weight = self._calc_outcome_weight(knowledge_id)
        
        # 3. Repetition (how many times applied)
        repetition = self._calc_repetition(knowledge_id)
        
        # 4. Cross-session validation (used in multiple sessions)
        cross_session = self._calc_cross_session(knowledge_id)
        
        score = (0.35 * generalizability + 
                 0.35 * outcome_weight +
                 0.15 * repetition + 
                 0.15 * cross_session)
        
        return score
    
    def _calc_generalizability(self, kid: str) -> float:
        """Based on number of contexts it's been applied to."""
        result = self.graph.execute_cypher("""
            MATCH (k)-[:APPLIED_IN]->(c:Context)
            WHERE k.id = $kid
            RETURN count(c) as contexts
        """, kid=kid)
        count = result[0]['contexts'] if result else 0
        return min(count / 10, 1.0)  # Cap at 10 contexts
    
    def _calc_outcome_weight(self, kid: str) -> float:
        """Based on success rate of applications."""
        result = self.graph.execute_cypher("""
            MATCH (k)-[:RESULTED_IN]->(o:Outcome)
            WHERE k.id = $kid
            RETURN avg(o.success) as avg_success
        """, kid=kid)
        return result[0]['avg_success'] if result else 0.0
    
    def _calc_repetition(kid: str) -> float:
        """How many times this knowledge was used."""
        # Implementation
        pass
    
    def _calc_cross_session(self, kid: str) -> float:
        """In how many different sessions."""
        # Implementation
        pass
```

### Success Criteria
- [ ] Score range 0.0-1.0
- [ ] Scores correlate with actual transfer success
- [ ] < 50ms per scoring operation

---

## Task 5.3: Session Context Injection

### What It Does
Inject relevant knowledge from previous sessions into new session context.

### Tiered Injection

| Tier | Count | Criteria | When |
|------|-------|-----------|------|
| **Level 1** | Top 3 | Critical (transferability > 0.8) | Always |
| **Level 2** | Top 5 | Contextual (transferability > 0.6) | If related |
| **Level 3** | Top 10 | Archive (transferability > 0.4) | On-demand |

### Implementation

```python
# packages/learning_engine/session_injector.py

class SessionInjector:
    def __init__(self, knowledge_graph, transfer_scorer):
        self.kg = knowledge_graph
        self.scorer = transfer_scorer
    
    def inject_for_task(self, task: str, session_id: str) -> dict:
        """Get relevant knowledge for a task."""
        
        # Find potential knowledge
        candidates = self.kg.find_related_lessons(task)
        
        # Score each for transferability
        scored = []
        for cand in candidates:
            score = self.scorer.score(cand['id'], task)
            scored.append({**cand, 'transferability': score})
        
        # Sort and tier
        scored.sort(key=lambda x: x['transferability'], reverse=True)
        
        level1 = [c for c in scored if c['transferability'] > 0.8][:3]
        level2 = [c for c in scored if 0.6 < c['transferability'] <= 0.8][:5]
        level3 = [c for c in scored if 0.4 < c['transferability'] <= 0.6][:10]
        
        # Record injection
        self._log_injection(session_id, task, level1 + level2 + level3)
        
        return {
            'critical': level1,
            'contextual': level2,
            'archive': level3
        }
    
    def _log_injection(self, session_id: str, task: str, knowledge: list):
        """Log what was injected for future reference."""
        self.graph.execute_cypher("""
            MERGE (s:Session {id: $sid})
            SET s.last_injected = datetime()
        """, sid=session_id)
```

### Success Criteria
- [ ] Injects within 100ms
- [ ] Level 1 always contains critical knowledge
- [ ] Logs injection history

---

## Task 5.4: EWC Integration

### What It Does
Connect Phase 3 EWC (Elastic Weight Consolidation) to prevent forgetting across sessions.

### Connection Points

```
Session N ends → Save Fisher matrix + optimal params
Session N+1 starts → Load Fisher + add regularization to loss
```

### Implementation

```python
# Connect to session_injector.py

class EWCSessionBridge:
    def __init__(self, ewc_engine, session_injector):
        self.ewc = ewc_engine
        self.injector = session_injector
    
    def on_session_start(self, session_id: str) -> dict:
        """Load EWC params and inject knowledge."""
        
        # Load previous session's Fisher info
        if self.ewc.has_saved_params():
            self.ewc.load_params()
            print(f"EWC: Loaded params from previous session")
        
        # Get knowledge for this session
        # (knowledge will be used as "support set" for EWC)
        return self.injector.get_context_for_session(session_id)
    
    def on_session_end(self, session_id: str):
        """Save current session's knowledge for next session."""
        
        # Compute Fisher for what we learned this session
        # (done by EWC engine)
        self.ewc.compute_fisher()
        self.ewc.save_params(session_id)
        print(f"EWC: Saved params for session {session_id}")
```

### Success Criteria
- [ ] Params persist across sessions
- [ ] Regularization applied to new learning
- [ ] No degradation in new session performance

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Knowledge graph unavailable | LOW | HIGH | SQLite fallback |
| Transferability scores wrong | MEDIUM | MEDIUM | A/B test with human validation |
| EWC slow | MEDIUM | LOW | Async computation |
| Session injection bloat | MEDIUM | MEDIUM | Limit to 18 items max |

---

## Go/No-Go Criteria

| Criterion | Threshold |
|-----------|-----------|
| Knowledge graph query | < 200ms |
| Transferability scoring | < 50ms |
| Session injection | < 100ms |
| EWC param load/save | < 500ms |
| Cross-session recall | > 60% |

---

## Files Modified

| File | Action | Description |
|------|--------|-------------|
| `packages/learning_engine/knowledge_graph.py` | CREATE | Graph-based knowledge storage |
| `packages/learning_engine/transferability.py` | CREATE | Transferability scoring |
| `packages/learning_engine/session_injector.py` | CREATE | Session context injection |
| `packages/learning_engine/ewc_bridge.py` | CREATE | EWC session bridge |

---

## Rollback

```bash
# Disable cross-session
echo "CROSS_SESSION_ENABLED=false" >> .env

# Fall back to stateless mode
# (knowledge stored in-memory only)
```

---

*Phase 5 complete. See Phase 6 for prompt evolution.*

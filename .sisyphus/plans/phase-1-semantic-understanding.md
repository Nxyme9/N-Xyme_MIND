# Phase 1: Semantic Understanding — Detailed Implementation Plan

> **Date:** 2026-04-08
> **Effort:** 4-7 days
> **Risk:** HIGH (modifies critical routing path)
> **Dependencies:** Phase 0 complete
> **Oracle Review:** REQUIRED for Task 1.3

---

## Executive Summary

Phase 1 replaces the 20-keyword perceptron ML router with embedding-based semantic understanding. This is the FIRST phase that modifies the live routing path — if done wrong, it breaks all routing. Must be deployed incrementally with shadow mode validation.

**GO/NO-GO: CONDITIONAL GO** — Only proceed after Phase 0 complete and Task 1.1 validated in shadow for 48+ hours.

---

## Task 1.1: Embedding-Based Task Classifier

### Files to Create
- `packages/intelligence/router/semantic_classifier.py` (new)

### Architecture Decision: SGDClassifier over Neural Net

| Factor | SGDClassifier | Neural Net |
|--------|--------------|------------|
| Online learning | `partial_fit()` | Requires full retrain |
| Inference latency | < 5ms | 50-200ms |
| Interpretability | Weight vectors | Black box |
| Data efficiency | Works with 50 samples | Needs 500+ |
| Cold start | Embedding similarity fallback | Random predictions |

**Verdict: SGDClassifier** — correct choice for routing.

### Implementation

```python
"""Semantic task classifier using embeddings + SGDClassifier."""

import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from sklearn.linear_model import SGDClassifier
from sklearn.calibration import CalibratedClassifierCV
from packages.learning_engine.embeddings.model_cache import get_embedding_cache

@dataclass
class ClassificationResult:
    predicted_agent: str
    predicted_level: int
    confidence: float  # Now REAL confidence (calibrated probability)
    method: str  # "semantic_classifier" | "embedding_similarity"
    all_scores: Dict[str, float]
    top_features: List[str]

AGENTS = [
    "sisyphus", "hephaestus", "prometheus", "atlas", "oracle",
    "momus", "metis", "explore", "librarian", "sisyphus-junior", "multimodal-looker"
]

# Pre-defined task cluster centroids for cold-start fallback
TASK_CLUSTERS = {
    "fix_bug": "fix bug error crash broken issue",
    "add_feature": "add feature implement create new functionality",
    "refactor": "refactor restructure improve clean up reorganize",
    "research": "find search explore investigate look up discover",
    "review": "review audit check verify validate inspect",
    "architect": "architecture design system redesign plan structure",
    "test": "test write tests unit integration coverage",
    "document": "document docs readme explain describe",
}

class SemanticTaskClassifier:
    """Classifies tasks to agents using semantic embeddings + SGDClassifier."""
    
    def __init__(self, db_path: str = ".sisyphus/routing.db"):
        self._cache = get_embedding_cache()
        self._classifier: Optional[SGDClassifier] = None
        self._calibrator: Optional[CalibratedClassifierCV] = None
        self._trained = False
        self._training_samples = 0
        self._min_samples = 50  # Minimum before using classifier
        self._db_path = db_path
    
    def classify(self, task_description: str) -> ClassificationResult:
        """Main entry point — classify task to agent."""
        embedding = self._cache.encode(task_description)
        
        if self._trained and self._training_samples >= self._min_samples:
            return self._predict_with_classifier(task_description, embedding)
        else:
            return self._embedding_similarity_fallback(task_description, embedding)
    
    def _predict_with_classifier(self, task: str, embedding: np.ndarray) -> ClassificationResult:
        """Predict using trained SGDClassifier with calibrated probabilities."""
        probs = self._calibrator.predict_proba([embedding])[0]
        best_idx = int(np.argmax(probs))
        
        return ClassificationResult(
            predicted_agent=AGENTS[best_idx],
            predicted_level=2,  # Default, complexity scorer overrides
            confidence=float(probs[best_idx]),
            method="semantic_classifier",
            all_scores={AGENTS[i]: float(probs[i]) for i in range(len(AGENTS))},
            top_features=self._get_top_features(embedding),
        )
    
    def _embedding_similarity_fallback(self, task: str, embedding: np.ndarray) -> ClassificationResult:
        """Cold-start fallback: cosine similarity to task cluster centroids."""
        scores = {}
        for cluster_name, centroid_text in TASK_CLUSTERS.items():
            centroid_emb = self._cache.encode(centroid_text)
            sim = float(np.dot(embedding, centroid_emb))
            scores[cluster_name] = sim
        
        # Map cluster to agent
        cluster_to_agent = {
            "fix_bug": "hephaestus",
            "add_feature": "hephaestus",
            "refactor": "hephaestus",
            "research": "explore",
            "review": "oracle",
            "architect": "prometheus",
            "test": "sisyphus-junior",
            "document": "librarian",
        }
        
        best_cluster = max(scores, key=scores.get)
        best_score = scores[best_cluster]
        
        return ClassificationResult(
            predicted_agent=cluster_to_agent.get(best_cluster, "hephaestus"),
            predicted_level=2,
            confidence=min(best_score, 0.7),  # Cap fallback confidence
            method="embedding_similarity",
            all_scores={agent: 0.0 for agent in AGENTS},
            top_features=[best_cluster],
        )
    
    def partial_fit(self, task_description: str, agent: str, success: bool):
        """Online learning — update classifier with new outcome."""
        if agent not in AGENTS:
            return
        
        embedding = self._cache.encode(task_description)
        agent_idx = AGENTS.index(agent)
        
        if self._classifier is None:
            self._classifier = SGDClassifier(
                loss="log_loss",
                penalty="l2",
                alpha=0.0001,
                class_weight="balanced",  # Critical for class imbalance
                max_iter=1000,
                tol=1e-4,
                random_state=42,
            )
            self._classifier.partial_fit(
                [embedding], [agent_idx], classes=list(range(len(AGENTS)))
            )
        else:
            self._classifier.partial_fit([embedding], [agent_idx])
        
        self._training_samples += 1
        
        # Recalibrate after every 100 samples
        if self._training_samples >= self._min_samples and self._training_samples % 100 == 0:
            self._recalibrate()
    
    def _recalibrate(self):
        """Recalibrate probabilities using isotonic regression."""
        # Load historical data for calibration
        tasks, agents = self._load_historical_data()
        if len(tasks) < self._min_samples:
            return
        
        embeddings = self._cache.encode(tasks)
        agent_indices = [AGENTS.index(a) for a in agents]
        
        self._calibrator = CalibratedClassifierCV(
            self._classifier, cv=3, method="isotonic"
        )
        self._calibrator.fit(embeddings, agent_indices)
        self._trained = True
    
    def _load_historical_data(self) -> tuple[List[str], List[str]]:
        """Load historical outcomes from routing.db."""
        import sqlite3
        conn = sqlite3.connect(self._db_path)
        rows = conn.execute(
            "SELECT task_description, agent FROM outcomes WHERE agent IS NOT NULL ORDER BY timestamp DESC LIMIT 1000"
        ).fetchall()
        conn.close()
        tasks = [r[0] for r in rows if r[0]]
        agents = [r[1] for r in rows if r[1]]
        return tasks, agents
    
    def _get_top_features(self, embedding: np.ndarray) -> List[str]:
        """Get top contributing features for interpretability."""
        if self._classifier is None:
            return []
        # Return agent names sorted by score
        scores = self._classifier.decision_function([embedding])[0]
        sorted_indices = np.argsort(scores)[::-1]
        return [AGENTS[i] for i in sorted_indices[:3]]
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "trained": self._trained,
            "training_samples": self._training_samples,
            "min_samples_needed": self._min_samples,
            "classifier_type": "SGDClassifier" if self._classifier else None,
        }
```

### Success Criteria
- Classification accuracy > 85% on held-out tasks
- Latency < 100ms (embedding + inference)
- Online learning works via `partial_fit()`
- Cold-start fallback returns reasonable predictions

### Verification Commands
```bash
.venv/bin/python3 -c "
from packages.intelligence.router.semantic_classifier import SemanticTaskClassifier
c = SemanticTaskClassifier()

# Cold-start test
r = c.classify('fix typo in auth.ts')
print(f'Cold-start: {r.predicted_agent} (confidence={r.confidence:.2f}, method={r.method})')

# Training test
for task, agent in [('fix bug', 'hephaestus'), ('research docs', 'explore'), 
                     ('review code', 'oracle'), ('fix error', 'hephaestus')]:
    c.partial_fit(task, agent, True)
print(f'Stats: {c.get_stats()}')
"
```

---

## Task 1.2: Vector-Enhanced Q-Learning State Representation

### Files to Modify
- `packages/learning_engine/rl/q_learning.py`

### Changes to QState

```python
@dataclass
class QState:
    task: str
    context_hash: str  # Keep for backward compat
    embedding: Optional[List[float]] = None  # NEW: 384-dim embedding
    cluster_id: Optional[str] = None  # NEW: similarity cluster ID
    
    def to_key(self) -> str:
        return f"{self.task}|{self.context_hash}"
    
    @staticmethod
    def from_context(task: str, context: dict, embedding: List[float] = None) -> "QState":
        ctx_hash = hashlib.md5(json.dumps(context, sort_keys=True).encode()).hexdigest()
        return QState(task=task, context_hash=ctx_hash[:16], embedding=embedding)
```

### Add FAISS State Lookup (only if > 5000 states)

```python
def get_similar_states(self, embedding: List[float], top_k: int = 5) -> List[QState]:
    """Find similar states using cosine similarity."""
    if len(self._q_table) < 100:
        # Brute force for small tables
        return self._brute_force_similar(embedding, top_k)
    
    # FAISS for large tables
    if self._faiss_index is None:
        self._build_faiss_index()
    
    distances, indices = self._faiss_index.search(
        np.array([embedding], dtype=np.float32), top_k
    )
    return [self._state_list[i] for i in indices[0] if i < len(self._state_list)]
```

### Success Criteria
- Similar tasks cluster correctly
- State retrieval accuracy > 80%
- Backward compatible with existing Q-table

---

## Task 1.3: Hybrid Routing Decision

### Files to Modify
- `packages/intelligence/router/unified.py` (lines 370-480)

### ⚠️ ORACLE REVIEW REQUIRED

This is the highest-risk single change. Must be reviewed before merging.

### Changes to Strategy 2 (ML Routing)

```python
# OLD (line 373-429):
ml_prediction = self._ml_router.predict(task_description)

# NEW:
if self._semantic_classifier:
    semantic_result = self._semantic_classifier.classify(task_description)
    
    # Shadow mode: log both but use old for first 48h
    if self._shadow_mode:
        logger.info(f"SHADOW: semantic={semantic_result.predicted_agent} vs ml={ml_prediction.get('predicted_agent')}")
    
    if semantic_result.confidence > 0.75 and not self._shadow_mode:
        decision = RoutingDecision(
            task_description=task_description,
            level=2,
            agent=semantic_result.predicted_agent,
            confidence=semantic_result.confidence,
            strategy_used="semantic",
            reason=f"Semantic classification ({semantic_result.method})",
            alternatives=alternatives,
            latency_ms=(time.time() - start_time) * 1000,
        )
```

### Deployment Strategy

```
Day 1-2: Shadow mode — log semantic predictions alongside keyword, never use them
Day 3-4: 5% traffic to semantic, measure accuracy vs keyword
Day 5-6: If semantic >= keyword - 5%, increase to 25%
Day 7: If accuracy > 80%, promote to PRIMARY
```

### Rollback
```python
# Config flag to disable semantic routing
SEMANTIC_ENABLED = False  # Falls back to keyword perceptron
```

---

## Task 1.4: Embedding-Based Memory Router

### Files to Modify
- `packages/intelligence/router/memory.py`

### Changes to `query_similar_tasks()`

```python
async def query_similar_tasks(self, task_description: str, limit: int = 5) -> List[SimilarTask]:
    # Get embedding
    embedding = self._cache.encode(task_description)
    
    # Vector similarity search
    results = await self._vector_search(embedding, top_k=limit)
    
    # Convert to SimilarTask
    similar_tasks = []
    for result in results:
        similar_tasks.append(SimilarTask(
            task_description=result["task"],
            agent=result["agent"],
            success=result["success"],
            embedding=result.get("embedding"),  # NEW
        ))
    return similar_tasks
```

### Similarity Threshold Tuning

| Scenario | Threshold | Rationale |
|----------|-----------|-----------|
| High-stakes (auth, payments) | 0.85-0.90 | Minimize misrouting |
| General task routing | 0.70-0.80 | Balance recall/precision |
| Exploration/memory recall | 0.60-0.70 | Maximize recall |

---

## Implementation Order

```
Phase 0 complete
    ↓
Task 1.1: Create semantic_classifier.py (new file, no existing code affected)
    ↓
Task 1.2: Modify QState class (backward compatible)
    ↓
Task 1.3: Shadow mode in unified.py (log only, no routing change)
    ↓
Task 1.4: Modify memory router (reuses vector store)
    ↓
48h shadow validation
    ↓
5% traffic → 25% → 100% promotion
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Classifier always returns same agent (class imbalance) | HIGH | CRITICAL | `class_weight='balanced'`, seed with 50 labeled examples |
| Confidence miscalibration | MEDIUM | HIGH | Isotonic regression calibration, validate before 0.75 threshold |
| Embedding latency breaks P95 SLA | MEDIUM | HIGH | Cache embeddings, batch encode, < 50ms target |
| A/B test inconclusive | MEDIUM | MEDIUM | Run shadow mode min 24h, boost traffic if needed |

---

## Go/No-Go Criteria for Phase 2

| Metric | Threshold | Verification |
|--------|-----------|--------------|
| Shadow accuracy vs keyword | Semantic >= keyword - 5% | Log comparison over 1000+ tasks |
| Confidence calibration error | < 0.15 | Isotonic regression validation |
| Routing latency P99 | < 200ms | Benchmark with real traffic |
| Class coverage | All 5+ agents predicted | Check class distribution |

---

## Files Modified

| File | Action | Description |
|------|--------|-------------|
| `packages/intelligence/router/semantic_classifier.py` | CREATE | New semantic classifier |
| `packages/learning_engine/rl/q_learning.py` | MODIFY | QState with embedding/cluster_id |
| `packages/intelligence/router/unified.py` | MODIFY | Strategy 2 shadow mode |
| `packages/intelligence/router/memory.py` | MODIFY | Vector similarity search |

---

## Rollback (Complete)

```bash
# Disable semantic routing
export SEMANTIC_ENABLED=false

# Verify fallback works
.venv/bin/python3 -c "
from packages.intelligence.router.unified import UnifiedDelegationRouter
import asyncio
r = UnifiedDelegationRouter()
d = asyncio.run(r.route_task('test task'))
print(f'Agent: {d.agent}, Strategy: {d.strategy_used}')
"
```

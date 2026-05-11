# Phase 0: Foundation — Detailed Implementation Plan

> **Date:** 2026-04-08
> **Effort:** 1-2 days (all tasks parallelizable)
> **Risk:** LOW — all changes are additive, no breaking changes
> **Dependencies:** None

---

## Executive Summary

Phase 0 establishes the infrastructure foundation for all 8 subsequent phases. Four independent tasks: dependency installation, database schema extensions, embedding model caching, and configuration validation. All tasks are parallelizable after Task 0.1 completes.

**GO/NO-GO: PROCEED WITH MODIFICATIONS** per Oracle review.

---

## Task 0.1: Dependency Installation & Environment Setup

### Current State
| Package | In .venv | In pyproject.toml |
|---------|----------|-------------------|
| numpy | 2.4.4 | learning_engine, intelligence |
| joblib | Missing | learning_engine only |
| sentence-transformers | Missing | Not listed |
| torch | Missing | Not listed |
| scipy | Missing | Not listed |
| scikit-learn | Missing | Not listed |
| faiss-cpu | Missing | Not listed |
| statsmodels | Missing | Not listed |

### Recommended Versions (April 2026)
| Package | Version | Notes |
|---------|---------|-------|
| sentence-transformers | 5.3.0 | Transformers v5 compatible |
| torch | 2.5.0 (CPU-only) | `--index-url https://download.pytorch.org/whl/cpu` |
| numpy | 2.x (already installed) | Compatible with torch 2.x |
| scipy | 1.15.1 | Compatible with numpy 2.x |
| scikit-learn | 1.3.0+ | Compatible with numpy 2.x |
| faiss-cpu | 1.9.0 | CPU-only, no CUDA |
| statsmodels | 0.14.0+ | Compatible with numpy 2.x |

### Implementation Steps

**Step 1**: Update `packages/learning_engine/pyproject.toml`:
```toml
[project]
dependencies = [
    "numpy>=1.24.0",
    "joblib>=1.3.0",
    "scipy>=1.11.0",
    "scikit-learn>=1.3.0",
    "faiss-cpu>=1.7.0",
    "statsmodels>=0.14.0",
]

[project.optional-dependencies]
ml = [
    "torch>=2.0.0",
    "sentence-transformers>=2.2.0",
]
```

**Step 2**: Install:
```bash
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
.venv/bin/pip install torch==2.5.0 --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install sentence-transformers==5.3.0 scipy==1.15.1 scikit-learn faiss-cpu statsmodels
```

**Step 3**: Verify:
```bash
.venv/bin/python3 -c "
import sentence_transformers; print(f'sentence-transformers {sentence_transformers.__version__} OK')
import torch; print(f'torch {torch.__version__} OK')
import scipy; print(f'scipy {scipy.__version__} OK')
import sklearn; print(f'sklearn {sklearn.__version__} OK')
import faiss; print(f'faiss {faiss.__version__} OK')
import statsmodels; print(f'statsmodels {statsmodels.__version__} OK')
"
```

### Rollback
```bash
.venv/bin/pip uninstall -y sentence-transformers torch scipy scikit-learn faiss-cpu statsmodels
```

### Success Criteria
- All 6 packages import without errors
- Existing tests still pass
- No version conflicts

---

## Task 0.2: Database Schema Extensions

### Current State
`routing.db` has 3 tables: outcomes (1196 rows), agent_weights (12 rows), triggers (24 rows).

### SQL Migration
Create `.sisyphus/routing-migrations/phase0.sql`:

```sql
-- Task embeddings for semantic routing
CREATE TABLE IF NOT EXISTS task_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_hash TEXT UNIQUE NOT NULL,
    task_text TEXT NOT NULL,
    embedding_blob BLOB NOT NULL,
    model_version TEXT DEFAULT 'all-MiniLM-L6-v2',
    embedding_dim INTEGER DEFAULT 384,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_task_embeddings_hash ON task_embeddings(task_hash);
CREATE INDEX IF NOT EXISTS idx_task_embeddings_created ON task_embeddings(created_at DESC);

-- Strategy selection tracking (for meta-learning)
CREATE TABLE IF NOT EXISTS strategy_selections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_hash TEXT NOT NULL,
    strategy TEXT NOT NULL,
    confidence REAL NOT NULL,
    level INTEGER,
    outcome TEXT,
    latency_ms REAL,
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_strategy_selections_task ON strategy_selections(task_hash);
CREATE INDEX IF NOT EXISTS idx_strategy_selections_strategy ON strategy_selections(strategy);
CREATE INDEX IF NOT EXISTS idx_strategy_selections_created ON strategy_selections(created_at DESC);

-- Cross-session model weights (for transfer learning)
CREATE TABLE IF NOT EXISTS cross_session_model (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_type TEXT NOT NULL,
    weight_blob BLOB NOT NULL,
    session_id TEXT NOT NULL,
    task_types TEXT,
    performance_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cross_session_model_type ON cross_session_model(model_type);
CREATE INDEX IF NOT EXISTS idx_cross_session_model_session ON cross_session_model(session_id);

-- Prompt version tracking (for prompt evolution)
CREATE TABLE IF NOT EXISTS prompt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_name TEXT NOT NULL,
    version INTEGER NOT NULL,
    prompt_text TEXT NOT NULL,
    score REAL DEFAULT 0.0,
    outcome_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(prompt_name, version)
);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_name ON prompt_versions(prompt_name);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_score ON prompt_versions(score);
```

### Implementation Steps
```bash
# Backup
cp .sisyphus/routing.db .sisyphus/routing.db.pre-phase0

# Apply
mkdir -p .sisyphus/routing-migrations
# Write SQL to .sisyphus/routing-migrations/phase0.sql
sqlite3 .sisyphus/routing.db < .sisyphus/routing-migrations/phase0.sql

# Verify
sqlite3 .sisyphus/routing.db ".tables"
sqlite3 .sisyphus/routing.db "SELECT COUNT(*) FROM outcomes;"  # Should still be 1196
```

### Rollback
```bash
cp .sisyphus/routing.db.pre-phase0 .sisyphus/routing.db
```

### Success Criteria
- 4 new tables created with indexes
- Existing tables unchanged (1196 outcomes still present)
- All existing queries still work

---

## Task 0.3: Embedding Model Cache

### Current State
`packages/memory_core/stores/vector_store.py` has `EmbeddingEngine` with query cache (256 entries). Need dedicated cache in learning_engine with 10,000 entries.

### Implementation
Create `packages/learning_engine/embeddings/__init__.py` and `packages/learning_engine/embeddings/model_cache.py`:

```python
"""Embedding model cache with LRU eviction and lazy initialization."""

import hashlib
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Optional
import numpy as np

class EmbeddingCache:
    """Thread-safe LRU cache for embeddings with disk persistence."""
    
    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    DIMENSION = 384
    
    def __init__(self, max_size: int = 10000, ttl: int = 3600,
                 cache_dir: str = ".sisyphus/embedding_cache"):
        self._model = None
        self._memory: OrderedDict[str, dict] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
    
    def _key(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()
    
    def get(self, text: str) -> Optional[np.ndarray]:
        k = self._key(text)
        with self._lock:
            if k in self._memory:
                entry = self._memory[k]
                if time.time() - entry['ts'] < self._ttl:
                    self._memory.move_to_end(k)
                    self._hits += 1
                    return entry['emb'].copy()
                del self._memory[k]
            self._misses += 1
        return None
    
    def put(self, text: str, embedding: np.ndarray):
        k = self._key(text)
        entry = {'emb': embedding.copy(), 'ts': time.time()}
        with self._lock:
            if k in self._memory:
                self._memory.move_to_end(k)
            else:
                if len(self._memory) >= self._max_size:
                    self._memory.popitem(last=False)
            self._memory[k] = entry
        # Persist to disk
        np.save(self._cache_dir / f"{k}.npy", embedding)
    
    def encode(self, text: str) -> np.ndarray:
        cached = self.get(text)
        if cached is not None:
            return cached
        emb = self._model.encode(text, normalize_embeddings=True).astype(np.float32)
        self.put(text, emb)
        return emb
    
    def encode_batch(self, texts: list[str]) -> np.ndarray:
        # Check cache first
        cached = []
        uncached = []
        uncached_idx = []
        for i, t in enumerate(texts):
            c = self.get(t)
            if c is not None:
                cached.append((i, c))
            else:
                uncached.append(t)
                uncached_idx.append(i)
        
        result = [None] * len(texts)
        for i, emb in cached:
            result[i] = emb
        
        if uncached:
            embs = self._model.encode(uncached, normalize_embeddings=True).astype(np.float32)
            for idx, emb in zip(uncached_idx, embs):
                result[idx] = emb
                self.put(texts[idx], emb)
        
        return np.stack(result)
    
    @property
    def _model(self):
        if self.__model is None:
            from sentence_transformers import SentenceTransformer
            self.__model = SentenceTransformer(self.MODEL_NAME)
        return self.__model
    
    @_model.setter
    def _model(self, val):
        self.__model = val
    
    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0
    
    @property
    def size(self) -> int:
        return len(self._memory)
    
    def clear(self):
        with self._lock:
            self._memory.clear()


# Singleton
_cache: Optional[EmbeddingCache] = None

def get_embedding_cache() -> EmbeddingCache:
    global _cache
    if _cache is None:
        _cache = EmbeddingCache()
    return _cache
```

### Verification
```bash
.venv/bin/python3 -c "
import time
from packages.learning_engine.embeddings.model_cache import get_embedding_cache
cache = get_embedding_cache()

# First call (miss + generate)
start = time.time()
e1 = cache.encode('test task query')
t1 = (time.time() - start) * 1000
print(f'First call: {t1:.1f}ms (miss)')

# Second call (cache hit)
start = time.time()
e2 = cache.encode('test task query')
t2 = (time.time() - start) * 1000
print(f'Second call: {t2:.1f}ms (hit)')

print(f'Hit rate: {cache.hit_rate:.0%}')
print(f'Cache size: {cache.size}')
print(f'Embedding shape: {e1.shape}')
assert e1.shape == (384,), f'Wrong shape: {e1.shape}'
assert np.allclose(e1, e2), 'Cache returned different embedding'
print('SUCCESS')
"
```

### Success Criteria
- Embedding generation < 50ms on cache miss
- Cache hit < 1ms
- Hit rate > 80% on repeated queries
- Embedding dimension = 384

---

## Task 0.4: Configuration Schema Validation

### Current State
`packages/learning_engine/config.py` has 9 config sections (QLearning, Bandit, Reward, Routing, ABTest, Database, EventBus, SkillLifecycle, Analytics). All use dataclasses with env var overrides.

### Add 4 New Config Sections

Add to `packages/learning_engine/config.py`:

```python
@dataclass
class EmbeddingConfig:
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimension: int = 384
    cache_size: int = 10000
    batch_size: int = 32
    device: str = "cpu"
    max_length: int = 256

@dataclass
class MetaLearningConfig:
    enabled: bool = False
    strategy_pool: list = field(default_factory=lambda: [
        "embedding_routing", "graph_routing", "bandit_routing", "heuristic_routing"
    ])
    adaptation_shots: int = 5
    ewc_lambda: float = 0.01
    maml_inner_lr: float = 0.01
    maml_outer_lr: float = 0.001

@dataclass
class RewardWeightsConfig:
    success: float = 0.4
    quality: float = 0.2
    latency: float = 0.15
    cost: float = 0.15
    satisfaction: float = 0.1

@dataclass
class BayesianConfig:
    prior_alpha: float = 1.0
    prior_beta: float = 1.0
    exploration_threshold: float = 0.3
    credible_interval: float = 0.8
```

Add to main `Config` dataclass:
```python
embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
meta_learning: MetaLearningConfig = field(default_factory=MetaLearningConfig)
reward_weights: RewardWeightsConfig = field(default_factory=RewardWeightsConfig)
bayesian: BayesianConfig = field(default_factory=BayesianConfig)
```

### Verification
```bash
.venv/bin/python3 -c "
from packages.learning_engine.config import get_config
c = get_config()
print(f'Embedding model: {c.embedding.model_name}')
print(f'Embedding dim: {c.embedding.dimension}')
print(f'Cache size: {c.embedding.cache_size}')
print(f'Meta enabled: {c.meta_learning.enabled}')
print(f'Reward weights: success={c.reward_weights.success}, quality={c.reward_weights.quality}')
print(f'Bayesian alpha: {c.bayesian.prior_alpha}')
print('SUCCESS: Config loads correctly')
"
```

### Success Criteria
- All existing configs load without errors
- New config sections accessible
- Environment variable overrides work

---

## Parallelization Strategy

All 4 tasks are independent after Task 0.1:

```
Task 0.1 (Dependencies) ─┬─ Task 0.2 (DB Schema)
                          ├─ Task 0.3 (Embedding Cache)
                          └─ Task 0.4 (Config Validation)
```

**Recommended order**: 0.1 first, then 0.2/0.3/0.4 in parallel.

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-------------|
| Dependency conflicts | Medium | High | CPU-only torch, test in venv first |
| Schema migration breaks queries | Low | High | Backup DB, test on copy |
| Embedding model download fails | Low | High | Cache model, graceful fallback |
| Config validation rejects values | Low | Medium | Validate before commit |

---

## Go/No-Go Criteria for Phase 1

**GO if ALL:**
- [ ] All 6 packages import without errors
- [ ] 4 new tables created, existing queries work
- [ ] Embedding generation < 50ms, cache hit < 1ms
- [ ] Config loads with new sections

**BLOCKER if ANY:**
- [ ] Dependency installation fails after 4 hours
- [ ] Existing tests fail (regression)
- [ ] Schema migration requires data loss
- [ ] No rollback procedure documented

---

## Files Modified

| File | Action | Description |
|------|--------|-------------|
| `packages/learning_engine/pyproject.toml` | MODIFY | Add 6 dependencies |
| `.sisyphus/routing-migrations/phase0.sql` | CREATE | 4 new tables + indexes |
| `packages/learning_engine/embeddings/model_cache.py` | CREATE | LRU cache (10k entries) |
| `packages/learning_engine/embeddings/__init__.py` | CREATE | Module init |
| `packages/learning_engine/config.py` | MODIFY | Add 4 config sections |

---

## Rollback (Complete)

```bash
# Dependencies
.venv/bin/pip uninstall -y sentence-transformers torch scipy scikit-learn faiss-cpu statsmodels 2>/dev/null

# Database
cp .sisyphus/routing.db.pre-phase0 .sisyphus/routing.db

# Embedding cache
rm -rf packages/learning_engine/embeddings/
rm -rf .sisyphus/embedding_cache/

# Config
# Revert config.py changes (git checkout or manual)

echo "Phase 0 rollback complete"
```

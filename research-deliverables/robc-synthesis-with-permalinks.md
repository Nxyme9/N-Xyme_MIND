# RoBC — Reverse Engineering Synthesis with Permalinks

**Compiled:** 2026-05-12
**Repo:** [agentlifylabs/RoBC](https://github.com/agentlifylabs/RoBC)
**Commit SHA:** [`53c4221`](https://github.com/agentlifylabs/RoBC/tree/53c42213ece2bfb8c21c2598b75f286db94d363f)
**Total source:** 1,682 Python lines across 12 files (6 core + tests + examples + trainer)

---

## 1. Architecture Overview

RoBC is an **online learning LLM router** — it selects between language models in real-time using **Thompson Sampling** over **Bayesian Gaussian posteriors**, segmented by **semantic clusters** of prompt embeddings.

### Core Pipeline (3 components in sequence):

1. **ClusterManager** — Assigns prompt embeddings to semantic clusters via kNN + softmax
2. **PosteriorManager** — Maintains Gaussian posteriors for every (model, cluster) pair
3. **ThompsonSampler** — Samples from posteriors to select model, balancing explore/exploit

---

## 2. Component Analysis with Permalinks

### 2.1 Controller — Orchestration Layer

**File:** [`robc/controller.py`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/controller.py) (226 lines)

| Method | Lines | Purpose |
|--------|-------|---------|
| `__init__` | [40-92](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/controller.py#L40-L92) | Inits cluster manager, posterior manager, and Thompson sampler |
| `route()` | [94-124](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/controller.py#L94-L124) | Gets cluster weights → aggregates posteriors → selects model |
| `route_with_details()` | [126-156](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/controller.py#L126-L156) | Same but returns full diagnostic dict |
| `update()` | [158-176](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/controller.py#L158-L176) | Feedback loop — updates posteriors with observed quality |
| `add_model()` | [178-183](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/controller.py#L178-L183) | Adds new model with uninformative priors |
| `save_posteriors()` | [185-193](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/controller.py#L185-L193) | Serializes learned beliefs to JSON |
| `load_posteriors()` | [195-208](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/controller.py#L195-L208) | Deserializes saved posteriors |
| `get_stats()` | [210-219](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/controller.py#L210-L219) | Returns selection counts and percentages |

**Key insight:** The `update()` method uses a **weight threshold** (`weight > 0.1`) at [line 175](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/controller.py#L175) to only update clusters with meaningful weight — prevents noise from irrelevant cluster assignments.

---

### 2.2 ClusterManager — Semantic Clustering

**File:** [`robc/cluster.py`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/cluster.py) (133 lines)

| Method | Lines | Purpose |
|--------|-------|---------|
| `get_cluster_weights()` | [79-121](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/cluster.py#L79-L121) | Core — kNN with softmax weighting, high-confidence skip |
| `get_primary_cluster()` | [123-128](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/cluster.py#L123-L128) | Returns single best cluster |

**Critical optimization** at [lines 102-103](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/cluster.py#L102-L103): **High-confidence skip** — if top cluster similarity >= 0.9, returns `{top_cluster: 1.0}` without running kNN.

**Softmax weighting** at [lines 116-121](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/cluster.py#L116-L121): Temperature-scaled softmax (default tau=0.2) for smooth interpolation between cluster assignments.

---

### 2.3 PosteriorManager — Bayesian Learning Core

**File:** [`robc/posterior.py`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/posterior.py) (211 lines)

| Component | Lines | Purpose |
|-----------|-------|---------|
| `GaussianPosterior` | [14-77](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/posterior.py#L14-L77) | Dataclass — mean, variance, observations count |
| `GaussianPosterior.update()` | [35-60](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/posterior.py#L35-L60) | **Bayesian update** — Conjugate Gaussian prior update |
| `PosteriorManager.update()` | [130-134](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/posterior.py#L130-L134) | Delegates to GaussianPosterior.update() |
| `get_aggregated_posterior()` | [136-169](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/posterior.py#L136-L169) | **GMM approximation** — combines multiple cluster posteriors |

**Bayesian update formula** at [lines 46-60](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/posterior.py#L46-L60):
```
prior_precision = 1 / sigma_prior
obs_precision   = 1 / sigma_obs
sigma_posterior = 1 / (prior_precision + obs_precision)
mu_posterior    = sigma_posterior * (mu_prior * prior_precision + outcome * obs_precision)
```

Standard conjugate Gaussian update.

**GMM aggregation** at [lines 155-161](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/posterior.py#L155-L161): Law of total variance:
```
E[X]   = sum(w_i * mu_i)
Var[X] = sum(w_i * (sigma_i^2 + mu_i^2)) - E[X]^2
```

---

### 2.4 ThompsonSampler — Exploration/Exploitation

**File:** [`robc/thompson_sampling.py`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/thompson_sampling.py) (106 lines)

| Method | Lines | Purpose |
|--------|-------|---------|
| `sample_with_bonus()` | [34-46](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/thompson_sampling.py#L34-L46) | Samples posterior + exploration bonus decaying with log(observations) |
| `select_model()` | [48-74](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/thompson_sampling.py#L48-L74) | Samples all models, picks max |
| `select_with_scores()` | [76-91](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/thompson_sampling.py#L76-L91) | Returns all sampled scores for debugging |
| `get_ucb_scores()` | [93-106](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/thompson_sampling.py#L93-L106) | Deterministic UCB alternative |

**Exploration bonus** at [lines 41-42](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/thompson_sampling.py#L41-L42):
```python
bonus = 0.02 / (1 + log(1 + n_obs))
```

Decays naturally as observations accumulate.

---

## 3. Data Flow (Request Lifecycle)

```
Request -> embedding vector (numpy)
  |
[1] ClusterManager.get_cluster_weights(embedding)
      -> cosine similarity to cluster centroids
      -> softmax weighting over top-k neighbors
      -> if top similarity >= 0.9: return {top: 1.0} immediately
      -> Dict[cluster_id -> weight]
  |
[2] PosteriorManager.get_aggregated_posterior(model, cluster_weights)
      -> For each model:
          -> For each cluster with weight > 0:
              -> GaussianPosterior(mean, variance, n) for (model, cluster)
          -> Weighted GMM using law of total variance
          -> GaussianPosterior(mean, variance, observations)
  |
[3] ThompsonSampler.select_model(posteriors)
      -> For each model:
          -> Draw random sample from posterior: N(mu, sigma)
          -> Add exploration bonus: 0.02 / (1 + log(1 + n))
          -> Store score
      -> Pick model with highest score
  |
Response -> model_id
  |
[4] Controller.update(model, embedding, quality_score)
      -> Get cluster_weights for embedding
      -> For each cluster where weight > 0.1:
          -> Bayesian update on posterior for (model, cluster)
```

---

## 4. Key Design Decisions

### 4.1 High-Confidence Skip
[`cluster.py:102-103`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/cluster.py#L102-L103)
If top cluster similarity >= 0.9, return `{top: 1.0}` immediately. Main reason for ~1ms routing.

### 4.2 Weighted Update Threshold
[`controller.py:175`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/controller.py#L175)
Only updates posteriors for clusters where weight > 0.1. Prevents noisy cluster assignments.

### 4.3 GMM Posterior Aggregation
[`posterior.py:155-161`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/posterior.py#L155-L161)
Law of total variance preserves uncertainty across cluster mixtures.

### 4.4 Exploration Bonus Decay
[`thompson_sampling.py:41-42`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/thompson_sampling.py#L41-L42)
`bonus = 0.02 / (1 + log(1 + n_obs))` — two-tier exploration (stochastic + deterministic).

### 4.5 Serialization for Persistence
[`controller.py:185-208`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/controller.py#L185-L208)
Posteriors save/load as JSON. Survivies process restarts.

### 4.6 Uninformative Priors for New Models
[`controller.py:178-183`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/controller.py#L178-L183)
New models start with mean=0.5, variance=1.0 — maximal uncertainty.

---

## 5. Test Coverage

| Test File | Lines | Tests |
|-----------|-------|-------|
| [`tests/test_cluster.py`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/tests/test_cluster.py) | 77 | Cluster assignment, similarity, centroid management |
| [`tests/test_controller.py`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/tests/test_controller.py) | 139 | Routing, updating, serialization, model lifecycle |
| [`tests/test_posterior.py`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/tests/test_posterior.py) | 102 | Bayesian update, aggregation, serialization |

---

## 6. Limitations

1. No concurrent update safety — `_posteriors` dict is unprotected
2. No NaN/Inf guarding — bad embeddings propagate silently
3. Single-threaded by design — no concurrent routing
4. Fixed cluster count — clusters don't split/merge dynamically

---

## 7. Related References

- **RoRF (comparison baseline):** https://github.com/Not-Diamond/RoRF
- **RouteLLM (inspiration):** https://github.com/lm-sys/RouteLLM
- **Agentlify (parent org):** https://agentlify.co


### 2.5 Trainer — Offline Training Pipeline

**File:** [`trainer.py`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/trainer.py) (283 lines)

The trainer is an **offline pipeline** that produces cluster centroids and initialized posteriors. It is NOT part of the online routing loop (controller.py never imports it).

| Component | Lines | Purpose |
|-----------|-------|---------|
| `TrainingConfig` | [29-36](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/trainer.py#L29-L36) | Dataclass — n_clusters=10, embedding_dim=768, prior_mean=0.5, prior_variance=0.25 |
| `train_clusters()` | [66-89](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/trainer.py#L66-L89) | sklearn K-Means (n_init=10) with L2-normalized centroids |
| `initialize_posteriors_from_scores()` | [94-132](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/trainer.py#L94-L132) | Data-driven shrinkage prior variance calculation |
| `save_training_artifacts()` | [137-166](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/trainer.py#L137-L166) | Serializes 3 files: centroids.npy, posteriors.json, config.json |
| `main()` | [171-283](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/trainer.py#L171-L283) | CLI entry point with argparse |

**K-Means with L2 normalization** at [lines 79-87](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/trainer.py#L79-L87):
```python
kmeans = KMeans(
    n_clusters=config.n_clusters,
    random_state=config.random_state,
    n_init=10,  # Multiple initializations for robustness
)
labels = kmeans.fit_predict(embeddings)
centroids = kmeans.cluster_centers_
centroids = centroids / np.linalg.norm(centroids, axis=1, keepdims=True)  # L2 normalize
```
Centroid normalization is essential — the router uses cosine similarity via `cosine_similarity` in `cluster.py:L85`, which requires unit vectors.

**Data-driven shrinkage prior** at [line 122](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/trainer.py#L122):
```python
variance = config.prior_variance / (1 + n * config.prior_variance / 0.01)
```
Where `0.01` is the observation noise variance (matches `posterior.py:35`). As `n` increases, variance shrinks toward 0 — more data = tighter prior. With `n=0`, variance equals `prior_variance` (0.25). The formula interpolates: with 10 observations, variance ≈ 0.25/(1+10*25) ≈ 0.001.

**Default models** at [lines 181-183](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/trainer.py#L181-L183):
```python
default=["openai:gpt-5.2", "google:gemini-2.5-flash", "anthropic:claude-4.5-sonnet"]
```

**Random centroid fallback** at [lines 246-248](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/trainer.py#L246-L248): When no embeddings are provided, generates random centroids for demo mode — same L2 normalization applied.

---

### 2.6 Package Exports — __init__.py

**File:** [`robc/__init__.py`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/__init__.py) (14 lines)

Minimal — exports all 6 classes from the 4 core modules and sets `__version__ = "0.1.0"`:

```python
from robc.controller import Controller
from robc.cluster import ClusterManager
from robc.posterior import GaussianPosterior, PosteriorManager
from robc.thompson_sampling import ThompsonSampler
```

---

### 2.7 Usage Example — Lifecycle Walkthrough

**File:** [`examples/basic_usage.py`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/examples/basic_usage.py) (133 lines)

The example demonstrates the complete RoBC lifecycle in 4 phases:

**Embedding simulation** at [line 15](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/examples/basic_usage.py#L15):
```python
np.random.seed(hash(text) % 2**32)
```
Deterministic hashing — same text always produces the same embedding, making the example reproducible.

**Quality matrix** at [lines 23-25](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/examples/basic_usage.py#L23-L25):
```python
quality_matrix = {
    "openai:gpt-5.2": {"reasoning": 0.93, "coding": 0.91, "creative": 0.86, "simple": 0.90},
    "google:gemini-2.5-flash": {"reasoning": 0.72, "coding": 0.76, "creative": 0.74, "simple": 0.84},
    "anthropic:claude-4.5-sonnet": {"reasoning": 0.91, "coding": 0.94, "creative": 0.93, "simple": 0.88},
}
```
Assumptions: GPT-5.2 leads on reasoning, Claude 4.5 Sonnet leads on coding/creative, Gemini 2.5 Flash trails by 10-20 points.

**Noise injection** at [line 28](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/examples/basic_usage.py#L28):
```python
return np.clip(base_quality + np.random.normal(0, 0.05), 0, 1)
```
Sigma=0.05 adds realistic observation noise (matches `posterior.py` default).

**Phase 1 — Cold routing** ([lines 57-70](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/examples/basic_usage.py#L57-L70)): Routes 3 prompts with uninformative priors (mean=0.5, var=1.0). Every model is equally likely — pure exploration.

**Phase 2 — Learning** ([lines 72-91](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/examples/basic_usage.py#L72-L91)): 100 random task iterations. Each iteration: route → observe quality → update posterior. After 100 rounds, `get_stats()` shows learned distribution — Claude should dominate coding clusters.

**Phase 3 — Learned routing** ([lines 93-107](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/examples/basic_usage.py#L93-L107)): Uses `route_with_details()` at [line 99](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/examples/basic_usage.py#L99) to show per-model Thompson-sampled scores. Post-learning selection should favour the best model for each task type.

**Phase 4 — Save/reload** ([lines 109-125](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/examples/basic_usage.py#L109-L125)): `save_posteriors()` at [line 113](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/examples/basic_usage.py#L113) serializes learned beliefs. A new `Controller` loads them via `posteriors_path` at [line 116](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/examples/basic_usage.py#L116), proving persistence.

---

## 8. Full Lifecycle Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  OFFLINE TRAINING (trainer.py)                              │
│                                                             │
│  embeddings ──→ K-Means (n_init=10) ──→ L2 centroids ──────┐│
│                  (trainer.py:79-87)                         ││
│                                                             ││
│  historical scores ──→ shrinkage prior ──→ posteriors.json ─┤│
│                        (trainer.py:122)                     ││
└─────────────────────────────────────────────────────────────┘│
                                                                │
┌─────────────────────────────────────────────────────────────┐│
│  ONLINE ROUTING (controller.py)                              ││
│                                                              ▼│
│  raw prompt ──→ embedding ──→ ClusterManager (cosine kNN)    │
│                     │           (cluster.py:79-121)          │
│                     │                                        │
│                     ▼                                        │
│              cluster_weights (dict)                          │
│                     │                                        │
│                     ▼                                        │
│              PosteriorManager (GMM aggregation)              │
│                (posterior.py:136-169)                        │
│                     │                                        │
│                     ▼                                        │
│              ThompsonSampler (sample + exploration bonus)    │
│                (thompson_sampling.py:48-74)                  │
│                     │                                        │
│                     ▼                                        │
│              selected_model_id ──→ LLM API call              │
│                     │                                        │
│                     ▼                                        │
│              quality_score ← LLM response                    │
│                     │                                        │
│                     ▼                                        │
│              Controller.update(model, embedding, quality)    │
│                (controller.py:158-176)                       │
│                     │                                        │
│                     ▼                                        │
│              Posterior backpropagation to (model, cluster)   │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Additional Design Decisions

### 9.1 Deterministic Embedding Hashing
[`basic_usage.py:15`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/examples/basic_usage.py#L15)
Uses `hash(text) % 2**32` for reproducible embeddings in examples. In production, this would be a real embedding model.

### 9.2 K-Means with n_init=10
[`trainer.py:79-83`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/trainer.py#L79-L83)
sklearn's default `n_init=10` prevents poor local minima — standard practice, not novel.

### 9.3 L2-Normalized Centroids
[`trainer.py:87`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/trainer.py#L87)
Critical for cosine similarity in ClusterManager. Without this, similarity scores would be meaningless.

### 9.4 Data-Driven Shrinkage Prior
[`trainer.py:122`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/trainer.py#L122)
`variance = prior_variance / (1 + n * prior_variance / 0.01)` — interpolates between uninformative prior (n=0) and empirical mean (n→∞). The constant `0.01` matches the observation noise variance in `posterior.py:35`.

### 9.5 Three-Artifact Serialization
[`trainer.py:137-166`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/trainer.py#L137-L166)
Training produces 3 files: `centroids.npy`, `posteriors.json`, `config.json`. Controller loads centroids directly and posteriors via `posteriors_path`.

### 9.6 Random Centroid Fallback
[`trainer.py:246-248`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/trainer.py#L246-L248)
When no data is provided, the trainer generates random centroids for demonstration — same L2 normalization, so the router still works (just poorly).

### 9.7 Noise Injection for Realism
[`basic_usage.py:28`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/examples/basic_usage.py#L28)
`np.random.normal(0, 0.05)` adds Gaussian noise matched to the observation variance — the example simulates the exact same noise model that the Bayesian update expects.

### 9.8 Minimal Package Surface
[`robc/__init__.py:1-14`](https://github.com/agentlifylabs/RoBC/blob/53c42213ece2bfb8c21c2598b75f286db94d363f/robc/__init__.py#L1-L14)
Exports only 5 classes and a version string. Trainer is NOT re-exported — it's a CLI script, not part of the library API.

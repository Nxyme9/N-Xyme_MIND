---
stepsCompleted: [1, 2, 3, 4]
status: 'complete'
completedAt: '2026-05-16'
inputDocuments:
  - data/bmad/architecture.md
  - data/bmad/design/rosenna-trainer-architecture-2026-05-16.md
  - data/bmad/research/technical-mojo-inference-engine-research-2026-05-16.md
  - data/bmad/brainstorming/brainstorming-session-20260516-ROI.md
---

# N-Xyme_MIND — Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for the Mojo Inference Engine + RosEnna Training System, decomposing requirements from architecture research, design documents, and 82 brainstorming ideas into implementable stories targeting v1.0 — the world's most bleeding-edge inference engine and automated training system.

## Requirements Inventory

### Functional Requirements

**Core Inference Engine:**
- FR1: Mojo daemon must route natural language queries to the correct tool via TF-IDF at <200μs
- FR2: Daemon must support Rosetta v13 embedding model for semantic scoring when TF-IDF confidence is low
- FR3: Embedding inference must run via llama-server on Unix socket (~10μs IPC, no HTTP)
- FR4: All tiers (Router, Embedding, LLM) must run in a single process tree with shared memory access
- FR5: LLM fallback (Qwen2.5-7B) must handle queries when both TF-IDF and embedding confidence are low

**Hot Training:**
- FR6: Daemon must log every correction (wrong tool → correct tool) to a JSONL file
- FR7: System must auto-trigger retraining when ≥100 new corrections accumulate
- FR8: Retraining must produce a new GGUF model and signal hot-reload to llama-server
- FR9: Live auto-tuner must adjust LR, temperature, and hard-neg ratio during training

**RosEnna Trainer:**
- FR10: Trainer must support contrastive learning via GISTEmbedLoss (InfoNCE + false negative filtering)
- FR11: Must support DoRA (Weight-Decomposed Low-Rank Adaptation) for fine-tuning
- FR12: Must support Prodigy auto-adaptive optimizer (no manual LR tuning)
- FR13: Must load all 23 existing training datasets and normalize them
- FR14: Must generate 10 paraphrases + 5 hard negatives per correction using local Qwen2.5-7B teacher
- FR15: Must export trained model to GGUF Q8_0 format

**Meta-Optimization:**
- FR16: Must log every training run as a JSONL manifest (hparams, data, results)
- FR17: Cross-run meta-optimizer must predict optimal hyperparams from past runs
- FR18: Must detect when correction feedback loop is chaotic (Lyapunov exponent > 0) and halt

**Bleeding-Edge Optimizations (from 82 brainstorm ideas):**
- FR19: Flash Embedding — fused attention kernel in Mojo SIMD (512-bit), no memory round-trips
- FR20: In-batch hard negative mining during training (not static pre-computed)
- FR21: Dynamic embedding dimension (MatryoshkaLoss — 896→512→256→128 adaptive)
- FR22: Online DoRA weight mixing for hot fixes (1-min adapter training instead of 30-min full retrain)
- FR23: Quantized similarity search (Q4_0 tool embeddings × f16 query embedding)
- FR24: Speculative routing (TF-IDF + 128-dim embed in parallel, agree=fast, disagree=full)
- FR25: Entropy-guided sampling during training (model teaches trainer where it's confused)
- FR26: Two-stage inference — rank (embedding) then classify (tiny 3-layer on top-3 candidates)
- FR27: Multi-objective loss — GISTEmbed + entropy bonus + similarity uniformity
- FR28: Temporal embeddings — corrections decay exponentially with age, recent ones dominate
- FR29: Hebbian learning at inference time — successful routes adjust embeddings by 0.001
- FR30: Correction-to-correction contrastive — pull same-intent queries together, push tools apart
- FR31: Sparse embedding space (10000-dim, <1% active) via learned semantic features
- FR32: Hyperbolic embedding space (64-dim hyperbolic > 1024-dim Euclidean)

### Non-Functional Requirements

- NFR1: Routing latency must be <10μs for Tier 0 (TF-IDF), <100μs for Tier 1 (embedding), <100ms for Tier 2 (LLM)
- NFR2: Training must complete in <30 min per cycle on RTX 3080 Ti (12GB VRAM)
- NFR3: Zero external API dependencies — all inference and training must run locally
- NFR4: System must survive daemon restarts (persistent correction buffer, model on disk)
- NFR5: Hot training must not block routing (asynchronous correction pipe)
- NFR6: Model hot-reload must complete in <1 second (no downtime for routing)
- NFR7: All IPC must use JSON-L over stdin/stdout or Unix sockets — no TCP/HTTP on hot path
- NFR8: Training must support QLoRA (4-bit base, FP16 adapter) to fit in 12GB VRAM
- NFR9: Meta-optimizer must not degrade accuracy — only suggest, never force hparams
- NFR10: Correction buffer must be deduplicated and validated before training

### Additional Requirements (Architecture)

- Integrate llama-server with CUDA support (RTX 3080 Ti, CUDA 13.2)
- Build llama.cpp as shared library (libllama.so) with `BUILD_SHARED_LIBS=ON`
- Python 3.14 + PyTorch + PEFT + bitsandbytes training environment
- Mojo 1.0.0b1 for daemon compilation
- Qwen2.5-0.5B base model for Rosetta (896-dim embeddings)
- All GGUF models stored at `LLMs/by-type/custom/Rosseta/`
- Training data at `services/rosenna_trainer/data/` (JSONL format)
- Each training run manifest saved for meta-optimizer

### FR Coverage Map

**Epic 1 — Mojo Router:**
FR1 (TF-IDF routing), FR2 (embedding fallback chain), FR3 (Unix socket IPC), FR4 (single process), NFR1 (latency budget), NFR7 (IPC protocol)

**Epic 2 — Rosetta v1 Semantic Engine:**
FR5 (LLM fallback), FR19 (Flash Embedding), FR21 (dynamic dimension), FR24 (speculative routing), FR26 (two-stage inference), NFR1 (latency budget)

**Epic 3 — RosEnna Trainer:**
FR10 (GISTEmbedLoss), FR11 (DoRA), FR12 (Prodigy optimizer), FR13 (23 datasets), FR14 (augmentation), FR15 (GGUF export), FR20 (in-batch hard neg), FR25 (entropy sampling), FR27 (multi-objective loss), FR30 (correction contrastive), NFR2 (30-min training), NFR8 (QLoRA 12GB)

**Epic 4 — Hot Loop:**
FR6 (correction logging), FR7 (auto-retrain trigger), FR8 (GGUF hot-reload), FR9 (live auto-tuner), FR22 (online DoRA mixing), FR28 (temporal embeddings), FR29 (Hebbian learning), NFR4 (persistence), NFR5 (async pipe), NFR6 (1s reload)

**Epic 5 — Bleeding-Edge:**
FR23 (quantized search), FR31 (sparse 10000-dim), FR32 (hyperbolic space), NFR3 (zero API deps)

**Epic 6 — Meta-Optimizer:**
FR16 (manifest logging), FR17 (cross-run prediction), FR18 (Lyapunov monitoring), NFR9 (suggest-only), NFR10 (dedup validation)

## Epic List

### Epic 1: Mojo Router — Real-Time Query Routing
Users send natural language queries and receive the correct tool in <200μs. TF-IDF routing handles 80%+ of common queries. Daemon runs as persistent process with stdin/stdout JSON-L IPC to nx-agents. No model required for basic operation.
**FRs covered:** FR1, FR2, FR3, FR4, NFR1, NFR7

### Epic 2: Rosetta v1 — Semantic Routing Engine
When TF-IDF confidence is low, the daemon sends queries via Unix socket to llama-server running Rosetta v13 GGUF on RTX 3080 Ti. 896-dim embeddings score all 25 tools semantically. Accuracy jumps to 95%+. Includes speculative routing (TF-IDF + 128-dim in parallel), dynamic dimension (adaptive 128→896), and two-stage ranking.
**FRs covered:** FR5, FR19, FR21, FR24, FR26

### Epic 3: RosEnna Trainer — Automated Contrastive Training
Production training pipeline. Loads all 23 datasets, generates augmentations via local Qwen2.5-7B teacher, trains with DoRA + GISTEmbedLoss + Prodigy, exports GGUF Q8_0. Four-phase curriculum learning with in-batch hard negatives. Single command: `python train.py --data data/ --output model.gguf`.
**FRs covered:** FR10, FR11, FR12, FR13, FR14, FR15, FR20, FR25, FR27, FR30, NFR2, NFR8

### Epic 4: Hot Loop — Self-Improving System
Daemon logs every correction. When 100+ accumulate, auto-retrains and hot-reloads the model. Includes online DoRA mixing for 1-min hot fixes, temporal embeddings (exponential decay weighting), Hebbian inference-time learning, and live auto-tuner adjusting hparams during training.
**FRs covered:** FR6, FR7, FR8, FR9, FR22, FR28, FR29, NFR4, NFR5, NFR6

### Epic 5: Bleeding-Edge Optimizations — Maximum Accuracy
Pushes routing accuracy from 95% → 99%. Quantized similarity search (Q4_0 tools × f16 queries), hyperbolic embedding space (64-dim hyperbolic > 1024-dim Euclidean), sparse 10000-dim embeddings with learned semantic features. Each optimization is independently testable and bolt-on.
**FRs covered:** FR23, FR31, FR32, NFR3

### Epic 6: Meta-Optimizer — Self-Training System
System learns to train itself better over time. Each training run logs a manifest. After 5+ runs, the meta-optimizer predicts optimal hyperparams. Live auto-tuner adjusts LR, temperature, hard-neg ratio during training. Lyapunov exponent monitors correction feedback loop for chaotic instability.
**FRs covered:** FR16, FR17, FR18, NFR9, NFR10

---

## Epic 2: Rosetta v1 — Semantic Routing Engine

**Goal:** When TF-IDF confidence is low, daemon queries via Unix socket to llama-server running Rosetta v13 GGUF on RTX 3080 Ti. 896-dim embeddings score all 25 tools semantically. Accuracy jumps from 80% → 95%+. Includes speculative routing and dynamic dimension.

### Story 2.1: llama-server Manager

As a user,
I want the bridge script to start and manage llama-server as a subprocess,
So that I don't have to manually start/kill it.

**Acceptance Criteria:**

**Given** the bridge script is launched
**When** it cannot connect to `/tmp/llama.sock`
**Then** it starts llama-server as subprocess with Rosetta v13 GGUF, `--embeddings --pooling mean`, all GPU layers
**And** waits until the Unix socket is accepting connections (up to 30s)
**When** the server process dies unexpectedly
**Then** the bridge restarts it automatically within 5 seconds
**When** the bridge exits
**Then** the llama-server subprocess is terminated gracefully

### Story 2.2: Unix Socket Embedding Query

As a user,
I want to send a query and receive a 896-dim embedding vector in <10ms,
So that I can score tool similarity.

**Acceptance Criteria:**

**Given** llama-server is running on `/tmp/llama.sock`
**When** I send `{"type": "embed", "text": "find memory keys", "id": "1"}` to the bridge
**Then** I receive `{"type": "embed_result", "embedding": [0.028, ...], "dim": 896, "latency_us": 5123, "id": "1"}`
**And** warm latency is <10ms (after first cold call excluded)
**And** the embedding dimension is exactly 896

### Story 2.3: Semantic Tool Scoring

As a user,
I want the daemon to use Rosetta embeddings to score all 25 tools when TF-IDF confidence is low,
So that accuracy improves.

**Acceptance Criteria:**

**Given** TF-IDF returned confidence <0.6 for a query
**When** the daemon requests a Rosetta embedding
**Then** it computes cosine similarity against all 25 tool embeddings
**And** returns the highest-scoring tool with its confidence score
**And** the combined (TF-IDF→embedding) accuracy on golden test cases is ≥95%

### Story 2.4: Speculative Routing — Parallel TF-IDF + Embedding

As a user,
I want the daemon to run TF-IDF and a fast 128-dim embedding in parallel,
So that I get best-of-both speeds.

**Acceptance Criteria:**

**Given** a query arrives
**When** TF-IDF confidence >0.8
**Then** return the TF-IDF result immediately (no embedding call)
**When** TF-IDF confidence is 0.6-0.8
**Then** run TF-IDF and 128-dim speculative embedding in parallel
**And** if they agree on the top tool, return immediately (~200μs total)
**When** they disagree or confidence <0.6
**Then** fall back to full 896-dim embedding (~5ms)

---

## Epic 1: Mojo Router — Real-Time Query Routing

**Goal:** Users send natural language queries and receive the correct tool in <200μs. TF-IDF routing handles 80%+ of common queries. Daemon runs as persistent process with stdin/stdout JSON-L IPC to nx-agents.

### Story 1.1: Daemon Startup & Lifecycle Management

As a user,
I want the daemon to start, initialize its tool set, and accept stdin/stdout connections,
So that I can route queries immediately.

**Acceptance Criteria:**

**Given** the daemon binary exists at `services/mojo-router/src/daemon`
**When** I launch it with `./daemon`
**Then** it loads its 25-tool lexicon and opens stdin for JSON-L
**And** responds to a `{"type": "status"}` query within 1 second
**And** the process stays resident using <10MB RAM

### Story 1.2: TF-IDF Routing Engine

As a user,
I want to send a natural language query and get a tool routed via TF-IDF,
So that I receive a tool match in <200μs.

**Acceptance Criteria:**

**Given** the daemon is running and listening on stdin
**When** I send `{"type": "route", "query": "find memory keys", "id": "1"}`
**Then** I receive `{"type": "route_result", "tool": "memory_search", "confidence": 0.85, "latency_us": 195, "id": "1"}`
**And** the latency for 100 consecutive valid queries never exceeds 250μs
**And** the correct tool is in the top 5 for ≥90% of the 80+ golden test cases

### Story 1.3: Error Handling & Graceful Degradation

As a user,
I want the daemon to never crash on malformed or edge-case input,
So that the system remains operational without supervision.

**Acceptance Criteria:**

**Given** the daemon is running
**When** I send invalid JSON to stdin
**Then** it returns `{"type": "error", "message": "parse error", "id": "0"}`
**And** continues accepting valid queries immediately after
**When** an empty query `""` is sent
**Then** it returns `{"type": "error", "code": "EMPTY_QUERY", "id": "1"}`
**When** stdin is closed (EOF)
**Then** the daemon exits cleanly with code 0

### Story 1.4: Performance Metrics & Logging

As an operator,
I want the daemon to log every routing decision with latency and confidence,
So that I can monitor system health and identify degradation.

**Acceptance Criteria:**

**Given** the daemon is running
**When** it processes 100 queries
**Then** it logs each with timestamp, query_hash, tool, confidence, latency_us
**And** exposes metrics via `{"type": "metrics"}` request returning p50/p95/p99 latency over the last 1000 queries
**When** confidence drops below 0.5 for ≥10% of recent queries
**Then** a warning message is emitted to stderr

---

## Epic 3: RosEnna Trainer — Automated Contrastive Training

**Goal:** Single command creates a production model. Loads all 23 datasets, augments via Qwen2.5-7B teacher, trains with DoRA + GISTEmbedLoss + Prodigy, exports GGUF Q8_0. Four-phase curriculum learning with in-batch hard negatives.

### Story 3.1: Training Environment & Configuration

As a developer,
I want to set up a Python 3.14 training environment with all dependencies,
So that I can run the trainer.

**Acceptance Criteria:**

**Given** the `services/rosenna_trainer/` directory exists
**When** I run `pip install -r requirements.txt`
**Then** PyTorch, transformers, peft, bitsandbytes, sentence-transformers, datasets, accelerate are installed
**And** all configs (model, data, training, export) load from `config.py` without errors
**And** `python -c "from config import *"` succeeds

### Story 3.2: Data Pipeline — Load 23 Datasets

As a developer,
I want to load all existing training datasets and normalize them into a unified format,
So that training has maximum data.

**Acceptance Criteria:**

**Given** the data files at `/home/nxyme/N-Xyme_CODE/nx_trainer/data/`
**When** I run `from data.dataset import load_all`
**Then** all JSONL files are loaded and normalized to `{"query": "str", "tool": "str", "text": "str"}`
**And** the total count matches the sum of all input files
**And** there are at least 100 examples per tool (2500+ total)

### Story 3.3: Data Augmentation — Local LLM Teacher

As a developer,
I want to generate 10 paraphrases + 5 hard negatives per training pair using local Qwen2.5-7B,
So that the model generalizes better.

**Acceptance Criteria:**

**Given** a training pair (query, tool) loaded from dataset
**When** I call `augment.generate(query, tool)`
**Then** it returns 10 paraphrases (same intent, different wording)
**And** 5 hard negatives (similar wording, DIFFERENT tool)
**And** the total training dataset grows by 15×
**And** 100% of generated pairs are unique (no duplicates)

### Story 3.4: DoRA Model Building

As a developer,
I want the trainer to build a Qwen2.5-0.5B model with DoRA adapters,
So that training fits in 12GB VRAM.

**Acceptance Criteria:**

**Given** the trainer is initialized
**When** it loads Qwen2.5-0.5B with 4-bit quantization (bitsandbytes)
**Then** DoRA adapters (rank 16, alpha 32, dropout 0.05) are applied to q_proj, k_proj, v_proj, o_proj
**And** total VRAM usage during training is <11GB
**And** the pooling head (mean pooling over non-padding tokens) is initialized fresh
**And** the base model is frozen, only adapter + head are trainable

### Story 3.5: Contrastive Training with Curriculum

As a developer,
I want the trainer to run through 4 curriculum phases,
So that the model converges to optimal accuracy.

**Acceptance Criteria:**

**Given** the model and data are loaded
**When** training starts
**Then** Phase 1 runs 2 epochs (1 random negative, temperature 0.1, easy pairs only)
**Then** Phase 2 runs 3 epochs (3 random negatives, temperature 0.05, all data)
**Then** Phase 3 runs 3 epochs (3 hard negatives + in-batch negatives, temperature 0.05)
**Then** Phase 4 runs 2 epochs (5 hard negatives only, temperature 0.03)
**And** the loss function is GISTEmbedLoss (InfoNCE with false negative filtering)
**And** the optimizer is Prodigy (auto-adaptive learning rate, no manual tuning)
**And** gradient clipping is applied at norm 1.0

### Story 3.6: GGUF Q8_0 Export

As a developer,
I want the trained model exported to GGUF Q8_0 format,
So that llama.cpp can load it for inference.

**Acceptance Criteria:**

**Given** training is complete
**When** I call `model.export_gguf("rosenna-v1-q8_0.gguf")`
**Then** the DoRA adapters are merged with the base model
**And** the merged model is converted to GGUF format at Q8_0 quantization
**And** the output file (<500MB) is loadable by `llama-server --embeddings`
**And** `llama-server` reports the correct architecture and embedding dimension

---

## Epic 4: Hot Loop — Self-Improving System

**Goal:** Daemon logs every correction. When 100+ accumulate, auto-retrains and hot-reloads the model. Includes online DoRA mixing for 1-min hot fixes, temporal embeddings (exponential decay), and Hebbian inference-time learning.

### Story 4.1: Correction Logging Buffer

As a user,
I want the daemon to log every routing correction to a persistent buffer,
So that the system can learn from mistakes.

**Acceptance Criteria:**

**Given** the daemon is running
**When** a correction arrives via `{"type": "correction", "query": "erase notes", "wrong_tool": "safe_delete", "correct_tool": "memory_write"}`
**Then** it is appended to `data/corrections.jsonl` with timestamp and source
**And** the in-memory correction count is incremented
**And** the daemon continues routing without interruption (zero latency impact)

### Story 4.2: Auto-Retrain Trigger

As a user,
I want the system to automatically retrain when enough corrections accumulate,
So that the model improves without manual intervention.

**Acceptance Criteria:**

**Given** the correction buffer has ≥100 new entries since last retrain
**When** a new correction arrives
**Then** the system triggers a retrain as a background process (routing continues on current model)
**And** the retrain runs `train.py <all corrections> --output /tmp/rosenna-hot.gguf`
**And** after successful training, signals hot-reload to the bridge
**When** accuracy drops ≥2% on golden test cases
**Then** retrain triggers immediately regardless of buffer size (rollback protection)

### Story 4.3: Hot-Reload Protocol

As a user,
I want the new model loaded into llama-server without restarting the daemon,
So that routing is always available.

**Acceptance Criteria:**

**Given** a new GGUF model is exported
**When** the bridge receives `{"type": "reload_model", "path": "/tmp/rosenna-hot.gguf"}`
**Then** it gracefully terminates the current llama-server
**And** starts a new llama-server instance with the new GGUF
**And** responds `{"type": "reload_ack", "status": "ok", "new_model": "rosenna-hot"}`
**And** the total routing downtime is <1 second (retries during reload use cached result)
**When** the new model fails to load (wrong architecture, corrupt file)
**Then** it restarts the OLD model and returns `{"type": "reload_ack", "status": "fail", "reason": "..."}`

### Story 4.4: Online DoRA Hot Fixes

As a user,
I want the system to apply quick 1-minute fixes for critical corrections,
So that I don't wait 30 minutes for a full retrain on urgent issues.

**Acceptance Criteria:**

**Given** 3-10 corrections arrive for the same tool pair (e.g., safe_delete ↔ memory_write confused 5+ times)
**When** the system detects this pattern
**Then** it trains a tiny DoRA adapter (rank 4, batch size 4, 10 gradient steps) on just those corrections
**And** applies the adapter on top of the current base model (weight averaging)
**And** the total time from detection to hot fix is <1 minute
**And** the adapter weights are saved alongside the base model

### Story 4.5: Hebbian Inference-Time Learning

As a user,
I want the model to slowly adapt to my vocabulary during normal use,
So that it gets better without explicit retraining.

**Acceptance Criteria:**

**Given** the daemon routes a query to a tool with confidence >0.9
**When** no correction arrives (user accepts the routing)
**Then** the query embedding is nudged +0.001 toward the chosen tool's embedding
**And** this adjustment is saved to a small file so it persists across restarts
**And** the cumulative drift never exceeds ±0.1 from the base model (capped)
**When** a correction DOES arrive for a high-confidence routing
**Then** the Hebbian adjustment is REVERSED (the high confidence was wrong — undo the learning)

---

## Epic 5: Bleeding-Edge Optimizations — Maximum Accuracy

**Goal:** Push routing accuracy from 95% → 99%. Quantized similarity search, hyperbolic embedding space, sparse 10000-dim features with learned semantic interpretation, and adversarial GAN training for hard example generation.

### Story 5.1: Quantized Similarity Search

As a user,
I want tool embeddings stored as Q4_0 quantized vectors,
So that similarity search is 4x faster with <0.5% accuracy loss.

**Acceptance Criteria:**

**Given** 25 tool embeddings are loaded (each 896-dim fp16)
**When** they are quantized to Q4_0 (4-bit block quantization)
**Then** each tool drops from 896×2=1792 bytes to 896×0.5=448 bytes (4x reduction)
**And** the dot product (f16 query vector × Q4_0 tool vectors) uses native SIMD
**And** accuracy@1 drops <0.5% compared to full fp16 similarity

### Story 5.2: Hyperbolic Embedding Space

As a user,
I want tools embedded in 64-dim hyperbolic space,
So that hierarchical tool relationships are naturally encoded with exponentially more capacity.

**Acceptance Criteria:**

**Given** 25 tools with known hierarchy (session > start/end, memory > read/write, file > open/delete)
**When** we train the model with hyperbolic loss (Poincaré distance)
**Then** the 64-dim hyperbolic embeddings distinguish tools as well as 896-dim Euclidean (<1% accuracy difference)
**And** the Poincaré distance computation for 25 tools takes <10μs
**And** the hierarchy is visible in the embedding norm (parent tools closer to origin)

### Story 5.3: Sparse 10000-dim Semantic Features

As a user,
I want queries encoded into a sparse 10000-dim space where each dimension is interpretable,
So that routing decisions are debuggable.

**Acceptance Criteria:**

**Given** the 896-dim Rosetta embeddings
**When** we train a sparse autoencoder on them
**Then** each query maps to a 10000-dim vector with <1% non-zero entries
**And** each active dimension maps to a learned semantic feature (e.g., dim 483 = "time-related")
**And** routing accuracy matches or exceeds the dense 896-dim baseline

### Story 5.4: Adversarial GAN Training

As a user,
I want a GAN-like loop that generates hard adversarial examples,
So that the model learns its blind spots.

**Acceptance Criteria:**

**Given** a trained Rosetta model
**When** a GENERATOR model produces queries designed to confuse Rosetta (semantically similar to tool A, routing to tool B)
**Then** Rosetta must correctly route ≥80% of adversarial queries
**And** each generator iteration finds ≥5 queries that fool the current model
**And** those queries are added to training data and the model is retrained
**After** 10 generator iterations
**Then** Rosetta accuracy on the adversarial test set improves by ≥5%

---

## Epic 6: Meta-Optimizer — Self-Training System

**Goal:** System learns to train itself better over time. Each run logged as manifest, meta-optimizer predicts optimal hyperparams, live auto-tuner adjusts during training, Lyapunov exponent monitors correction feedback loop stability.

### Story 6.1: Training Manifest Logger

As a developer,
I want every training run logged as a structured manifest,
So that I can compare results and the meta-optimizer can learn from past runs.

**Acceptance Criteria:**

**Given** a training run completes
**When** the trainer finishes successfully
**Then** a manifest JSONL entry is written with: run_id, data_size, tool_count, method (DoRA/LoRA), rank, epochs, batch_size, temperature, optimizer, loss_name, accuracy@1, mrr, latency_gpu_us, duration_minutes
**And** the manifest is appended to `meta/manifests.jsonl`
**And** the file is valid JSONL (one object per line)
**When** training fails (crash, OOM, hang)
**Then** a failed manifest is written with "status": "failed" and the error message

### Story 6.2: Cross-Run Meta-Optimizer

As a developer,
I want the system to predict optimal hyperparams from past runs,
So that each retrain is faster and more accurate.

**Acceptance Criteria:**

**Given** ≥5 manifests exist in the database
**When** a new training job is initialized
**Then** the meta-optimizer finds the most similar past run by data_size, tool_count, correction_ratio
**And** predicts optimal values for: batch_size, temperature, hard_neg_ratio, optimizer_name
**And** the predicted hparams are set as defaults (user can override)
**After** 15+ runs
**Then** meta-optimizer predictions converge to within 5% of the best known hparams for that data configuration
**When** <5 manifests exist
**Then** default hparams are used (Prodigy, temperature 0.05, hard_neg_ratio 1.0)

### Story 6.3: Live Auto-Tuner

As a developer,
I want training hyperparameters to adjust in real-time based on training metrics,
So that training converges optimally without manual tuning.

**Acceptance Criteria:**

**Given** training is running
**When** loss plateaus for 3 epochs (improvement <1%)
**Then** learning rate is halved and hard negative ratio is increased by 0.5
**When** gradient norm exceeds 1.0
**Then** gradient clipping is applied at 1.0 and LR is reduced 20%
**When** validation accuracy crosses 80% threshold
**Then** automatically advance from Phase 1 to Phase 2 (more negatives, lower temperature)
**When** validation accuracy crosses 90%
**Then** automatically advance to Phase 3
**When** validation accuracy crosses 95%
**Then** automatically advance to Phase 4 (sharpening)
**And** ALL auto-tuner adjustments are logged to the training manifest

### Story 6.4: Lyapunov Stability Monitor

As a developer,
I want the system to detect when the correction feedback loop becomes chaotic,
So that it halts before accuracy degrades.

**Acceptance Criteria:**

**Given** the correction → retrain → route → correction cycle is running
**When** the Lyapunov exponent of the embedding update trajectory exceeds 0 (sign of chaos)
**Then** the system stops accepting new corrections into the training buffer
**And** rolls back to the last known stable model checkpoint
**And** emits `{"type": "error", "code": "LYAPUNOV_UNSTABLE", "message": "correction feedback loop unstable"}`
**And** resumes accepting corrections only after the golden test set confirms stability
**When** Lyapunov exponent is negative (stable)
**Then** normal operation continues with no intervention

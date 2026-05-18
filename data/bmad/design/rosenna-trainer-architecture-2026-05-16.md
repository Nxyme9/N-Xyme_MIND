# RosEnna Trainer — Architecture Design

**Optimal training pipeline for Rosetta semantic routing model**
*Synthesized from technical research, codebase audit, and ML best practices*

---

## 1. Core Design Philosophy

**One model, one loss, one pipeline.** The existing trainer has 5 competing backends, 6 trainers (ORPO, PRO, RRHF, BCO, SFT, preference), and 2,000+ lines of dead code. This rebuild strips everything that doesn't directly improve tool-routing accuracy.

### Key Insight: Contrastive Learning > Classification > SFT

| Approach | How it works | Accuracy | Data efficiency |
|----------|-------------|----------|----------------|
| **SFT** (current) | "Given query, output tool name" | Low | Needs 100k+ examples |
| **Classification** | "Classify query into 25 tool buckets" | Medium | Needs balanced classes |
| **Contrastive** (target) | "Pull query closer to correct tool, push from wrong tools" | **Highest** | Works with 1k high-quality pairs |

Contrastive learning with hard negatives is the industry standard for embedding models (sentence-transformers, Nomic, etc.) and directly optimizes for what we need: semantic similarity between queries and tool descriptions.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        ROSENNA TRAINER                           │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────────┐  │
│  │ DATA PIPELINE │──▶│   TRAINING   │──▶│   EXPORT + EVAL    │  │
│  │              │   │              │   │                    │  │
│  │ • 23 datasets │   │ • Contrastive│   │ • GGUF export      │  │
│  │ • Live corrs  │   │ • InfoNCE    │   │ • Q8/Q4 quantize   │  │
│  │ • Augment     │   │ • Hard negs  │   │ • Accuracy@1       │  │
│  │ • Hard negs   │   │ • LoRA       │   │ • Confusion matrix │  │
│  └──────────────┘   └──────────────┘   └────────────────────┘  │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  HOT TRAINING LOOP                        │   │
│  │  Daemon corrections → buffer (100+) → auto-retrain        │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Pipeline

### 3.1 Input Sources

| Source | Format | Lines | Purpose |
|--------|--------|-------|---------|
| `v3_final.jsonl` | JSONL | ~15k | General training pairs |
| `v4_real.jsonl` | JSONL | ~500 | Real-world queries |
| `rosetta_v8_complete_train.jsonl` | JSONL | 612 | Curated v8 pairs |
| `quality_data.jsonl` | JSONL | ~8k | High-quality pairs |
| `contrastive_data.jsonl` | JSONL | ~3k | Hard-coded hard negatives |
| `all_tools_data.jsonl` | JSONL | ~1k | All 25 tools |
| Live corrections | JSONL | Growing | Real usage feedback |

### 3.2 Data Format (Normalized)

```json
{"query": "find my saved notes about python", "tool": "memory_search", "text": "Search through saved memories"}
{"query": "delete this file", "tool": "safe_delete", "text": "Remove a file or directory"}
```

Each entry has:
- `query` — the user's natural language request
- `tool` — the correct tool name (label)
- `text` — the tool's description (used as positive anchor)

### 3.3 Augmentation Pipeline

For each real correction, the LLM generates:

1. **10 positive variations** (paraphrases of the same intent)
2. **5 hard negatives** (similar phrasing, DIFFERENT tool)

```
Real: "erase my notes" → memory_write

Positives:
  "clear my notes"             → memory_write
  "remove my notes"            → memory_write  
  "wipe my memos"              → memory_write
  "delete my jottings"         → memory_write
  "empty my scratchpad"        → memory_write
  "purge my saved thoughts"    → memory_write
  "clean up my notes"          → memory_write
  "reset my journal"           → memory_write
  "flush my memory cache"      → memory_write
  "dump my working notes"      → memory_write

Hard Negatives:
  "erase my files"             → safe_delete      ❌ (NOT memory_write)
  "delete my account"          → session_end       ❌
  "clear my workspace"         → context_prune     ❌
  "wipe my database"           → project_clean     ❌
  "purge my trash"             → empty_trash       ❌
```

**1 real → 15 training pairs. ** After 100 corrections → 1,500 new pairs.

### 3.4 Contrastive Triplet Format

Convert each pair into a triplet (anchor, positive, negative):

```
Anchor:    "erase my notes"
Positive:  "memory_write: Erase or clear saved notes/memories"  
Negative:  "safe_delete: Permanently remove files from disk"
```

The model learns: anchor is SIMILAR to positive, DIFFERENT from negative.

---

## 4. Model Architecture

### 4.1 Base Model

**Qwen2.5-0.5B** (or Nomic-embed-text-v1.5)

| Feature | Qwen2.5-0.5B | Nomic-embed-v1.5 |
|---------|-------------|-------------------|
| Params | 494M | 137M |
| Embed dim | 896 | 768 |
| Context | 32K | 2K |
| Speed | Fast | Fastest |
| Accuracy | Better | Good |

**Recommendation: Qwen2.5-0.5B** — same 896-dim as current Rosetta v13, good semantic understanding

### 4.2 Embedding Head

Remove the LM head, add a pooling layer (mean pooling over token embeddings):

```
Input: "erase my notes"
  → Qwen2.5 encoder (LoRA fine-tuned)
  → Token embeddings [T1, T2, ..., Tn]
  → Mean pooling
  → 896-dim embedding vector
```

Training: the encoder is fine-tuned via LoRA while the pooling head is trained from scratch.

### 4.3 LoRA Configuration

| Parameter | Value | Why |
|-----------|-------|-----|
| r (rank) | 16 | Balances adaptation vs overfitting |
| alpha | 32 | Default scaling |
| target modules | q_proj, k_proj, v_proj, o_proj | All attention projections |
| dropout | 0.05 | Light regularization |
| bias | none | Don't train bias vectors |

### 4.4 Quantization

| Stage | Precision | Size (500M model) |
|-------|-----------|-------------------|
| Training | QLoRA (4-bit NF4) | ~350MB VRAM |
| Export | Q8_0 (8-bit) | ~500MB disk |
| Inference | Q8_0 or Q4_K_M | ~250MB disk |

---

## 5. Training

### 5.1 Loss Function — InfoNCE (NT-Xent)

The gold standard for embedding models:

```
L = -log( exp(sim(a,p)/τ) / Σ(exp(sim(a,n_i)/τ)) )
```

Where:
- `sim(a,p)` = cosine similarity between anchor and positive
- `sim(a,n_i)` = cosine similarity between anchor and negative i
- `τ` = temperature (learnable, initial 0.05)

**Why InfoNCE:**
- Directly optimizes for what we want (semantic similarity ranking)
- Handles multiple negatives naturally
- Temperature controls the "hardness" of the decision boundary
- Used by sentence-transformers, Nomic, all major embedding models

### 5.2 Curriculum Learning

| Phase | Data | Negatives per anchor | Temperature | Epochs |
|-------|------|---------------------|-------------|--------|
| 1 | Clean pairs | 1 random negative | 0.1 (sharp) | 2 |
| 2 | All data | 3 random negatives | 0.05 | 3 |
| 3 | All data | 3 hard negatives | 0.05 | 3 |
| 4 | Hard negatives only | 5 hard negatives | 0.03 | 2 |

Total: ~10 epochs, ~30 minutes on RTX 3080 Ti

### 5.3 Batch Strategy

| Strategy | Value |
|----------|-------|
| Batch size | 32 (limited by 12GB VRAM + LoRA) |
| Gradient accumulation | 2 steps |
| Effective batch | 64 |
| Optimizer | AdamW 8-bit (bitsandbytes) |
| Learning rate | 2e-4 for LoRA, 1e-3 for head |
| LR scheduler | Cosine with warmup (10% of steps) |
| Gradient clipping | 1.0 |

---

## 6. Evaluation

### 6.1 Metrics

| Metric | What it measures | Target |
|--------|------------------|--------|
| Accuracy@1 | Correct tool is top prediction | >95% |
| Accuracy@5 | Correct tool in top 5 | >99% |
| Mean Reciprocal Rank (MRR) | Average position of correct tool | >0.97 |
| Confusion matrix | Which tools get confused | <2% cross-confusion |
| Latency (CPU) | Time per embedding | <5ms |
| Latency (GPU) | Time per embedding | <500μs |

### 6.2 Golden Test Cases

80+ curated test cases from `real_validator.py` — real queries with known correct tools. Run after every training cycle.

### 6.3 Hard Negative Evaluation

For each query, compute similarity to ALL 25 tools. The correct tool should be #1. Any tool that scores higher than the correct tool is a "confusion" — those pairs feed back into the training data.

---

## 7. Export Pipeline

### 7.1 GGUF Conversion

```
Fine-tuned LoRA weights
        ↓
Merge with base model (Qwen2.5-0.5B)
        ↓
Convert to GGUF format via convert_hf_to_gguf.py
        ↓
Quantize to Q8_0 (or Q4_K_M)
        ↓
Output: rosenna-v1-q8_0.gguf (~500MB)
```

### 7.2 Hot-Reload Protocol

```json
// Daemon → llama-server:
{"type": "reload_model", "path": "/path/to/rosenna-v1-q8_0.gguf"}

// llama-server → Daemon:
{"type": "reload_ack", "status": "ok", "old_model": "rosetta-v13", "new_model": "rosenna-v1"}
```

---

## 8. Hot Training Loop

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Mojo       │────▶│  Correction  │────▶│  Training    │
│  Daemon     │     │  Buffer      │     │  Pipeline    │
│             │     │  (JSONL)     │     │              │
│  Routes     │     │  ≥100 new?   │     │  Fine-tune   │
│  Collects   │     │  → trigger   │     │  Export GGUF │
│  feedback   │     │              │     │  Signal      │
└─────────────┘     └──────────────┘     │  reload      │
                                         └──────┬───────┘
                                                │
                                         ┌──────▼───────┐
                                         │  llama-server │
                                         │  Hot-reload   │
                                         │  new GGUF     │
                                         └──────────────┘
```

**Trigger conditions:**
- ≥100 new corrections in buffer
- OR accuracy drops below 90% on golden test cases
- OR 24 hours since last retrain

---

## 9. File Structure

```
rosenna_trainer/
├── train.py                    # Entry point: python train.py
├── config.py                   # Pydantic configs (model, data, training, export)
│
├── data/
│   ├── __init__.py
│   ├── dataset.py              # Load all sources → normalized triplets
│   ├── augment.py              # LLM-based paraphrase + hard negative gen
│   ├── sampler.py              # Batch sampler with hard negative mining
│   └── tools.py                # 25 tool definitions with descriptions
│
├── model/
│   ├── __init__.py
│   ├── encoder.py              # Qwen2.5 + pooling head + LoRA
│   ├── loss.py                 # InfoNCE loss implementation
│   └── quantize.py             # GGUF export + quantization
│
├── training/
│   ├── __init__.py
│   ├── loop.py                 # Training loop (epochs, batches, logging)
│   └── curriculum.py           # Phase scheduling (easy → hard)
│
├── eval/
│   ├── __init__.py
│   ├── metrics.py              # Accuracy@1, MRR, confusion matrix
│   ├── golden.py               # 80+ golden test cases
│   └── benchmark.py            # Latency benchmark (CPU + GPU)
│
├── hot/
│   ├── __init__.py
│   ├── collector.py            # Watch corrections.jsonl → buffer
│   └── daemon.py               # Trigger retrain, signal reload
│
└── scripts/
    ├── prepare_data.py         # One-shot: merge all 23 datasets
    ├── augment_existing.py     # Generate paraphrases for all existing data
    └── train_full.sh           # Full pipeline from scratch
```

---

## 10. Command-Line Interface

```bash
# Train from scratch (all data)
python train.py --data data/ --model Qwen/Qwen2.5-0.5B --output rosenna-v1.gguf

# Continue training from checkpoint
python train.py --resume checkpoints/rosenna-v1/ --data corrections.jsonl --output rosenna-v1-hot.gguf

# Augment existing data
python scripts/augment_existing.py --input all_tools_data.jsonl --output augmented/

# Prepare all 23 datasets
python scripts/prepare_data.py --sources data/ --output unified_training.jsonl

# Evaluate only
python eval/golden.py --model rosenna-v1-q8_0.gguf

# Hot training daemon
python hot/daemon.py --watch corrections.jsonl --model-dir rosenna-models/
```

---

## 11. Dependencies

| Package | Purpose |
|---------|---------|
| `torch` 2.1+ | ML framework |
| `transformers` 4.44+ | Model loading |
| `bitsandbytes` | QLoRA quantization (4-bit NF4) |
| `peft` | LoRA fine-tuning |
| `sentence-transformers` | Contrastive loss reference |
| `datasets` | Data loading |
| `accelerate` | Multi-GPU support |
| `einops` | Tensor operations |
| `llama.cpp` | GGUF export (convert script) |

No vLLM, no Ollama, no Unsloth, no distributed training infra.

---

## 12. Estimated Performance

| Metric | Target |
|--------|--------|
| Training time (10 epochs, RTX 3080 Ti) | ~30 min |
| Training time (with augmentation) | ~2 hours |
| Model size (Q8_0) | ~500MB |
| Model size (Q4_K_M) | ~250MB |
| Embedding latency (CPU, AVX2) | <5ms |
| Embedding latency (GPU, RTX 3080 Ti) | <500μs |
| Accuracy@1 (golden test cases) | >95% |

---

## 13. Bleeding-Edge Additions (2026 State-of-the-Art)

### 13.1 DoRA — Replace LoRA for Accuracy-Critical Tasks

**DoRA (Weight-Decomposed Low-Rank Adaptation)** closes half the gap between LoRA and full fine-tuning with only 5-10% more VRAM.

| Feature | LoRA | DoRA |
|---------|------|------|
| Trainable params | ~0.1% | ~0.11% |
| VRAM overhead | Baseline | +5-10% |
| Accuracy gap to full FT | 2-5% | **1-2%** (2x better) |
| Implementation | PEFT built-in | PEFT built-in |

**When to use DoRA vs LoRA:**
- **DoRA**: Final production model, accuracy-critical (Rosetta routing)
- **LoRA**: Rapid prototyping, ablation studies, quick iterations

DoRA decouples weight magnitude from direction:
```python
# LoRA:  W' = W + BA          (magnitude + direction coupled)
# DoRA:  W' = m * (W + BA)/|W|  (magnitude m separated)
```

### 13.2 GISTEmbedLoss — Better Than Plain InfoNCE

**GISTEmbedLoss** uses a guide model to filter false negatives from in-batch negatives. Why this matters: our training data may have similar queries mapped to different tools — plain InfoNCE would incorrectly push them apart.

| Loss Function | False Negatives | Training Signal | Best For |
|---------------|----------------|----------------|----------|
| InfoNCE | Pushes apart ❌ | All negatives equal | Clean data |
| MultipleNegativesRankingLoss | Pushes apart ❌ | In-batch only | Paired data |
| **GISTEmbedLoss** | **Filters correctly** ✅ | **In-batch + guide model** | **Noisy/messy data** |

Our correction data will have noise — GISTEmbed handles this.

### 13.3 SimPO for Correction Learning

When the daemon logs a correction ("was tool X, should be tool Y"), we need to learn from paired preferences (chosen/rejected). **SimPO** is reference-free and handles noisy feedback better than DPO.

| Method | Ref model needed | Handles noise | Stability |
|--------|-----------------|---------------|-----------|
| DPO | ✅ | Low | Medium |
| SimPO | ❌ | **High** | **High** |
| SPO | ❌ | Medium | Very High |

**Learning stack for corrections:**
```
User correction
  → (chosen=tool Y, rejected=tool X) pair
  → SimPO loss (no reference model needed)
  → Updates DoRA adapter
  → Model learns from mistake instantly
```

### 13.4 Prodigy Optimizer — Auto-Adaptive Learning Rate

Prodigy combines D-Adaptation + AdamW to automatically determine learning rate per parameter. **No LR tuning needed.**

| Optimizer | Tuning needed | Memory | Speed |
|-----------|--------------|--------|-------|
| AdamW | High (LR, beta, eps) | 8 bytes/param | Baseline |
| AdamW 8-bit | Medium | **2 bytes/param** | Baseline |
| Prodigy | **None** (auto) | 8 bytes/param | Same as AdamW |
| Schedule-Free | None (auto) | 8 bytes/param | **Faster** (no warmup) |

**Stack:**
- Phase 1-3: **Prodigy** (auto-LR, trains fast)
- Phase 4: **Schedule-Free** (no LR schedule, just keep training)

### 13.5 In-Batch Negatives — Free Hard Negatives

Every batch of 32 queries gives **31 free negatives per query** — they're already computed inside the similarity matrix. Our batch sampler must ensure diverse tools per batch.

```python
# Batch with 32 queries across 8 different tools = 4 queries/tool
# Each query has: 3 positives (same tool) + 28 in-batch negatives (other tools)
# Plus 3-5 mined hard negatives (similar queries, different tools)
# Total: 31-33 negatives per query — rich learning signal
```

**Batch composition strategy:**
1. Sample 4 queries from each of 8 tools = 32/batch
2. Compute 32×32 similarity matrix
3. InfoNCE loss with: positives (same tool) vs all others
4. Add mined hard negatives on top

---

## 14. Live Auto-Tuner (Meta-Learning Layer 1)

### 14.1 What It Tunes During Training

| Signal | What It Tunes | When |
|--------|--------------|------|
| Loss plateau detection | ↓ LR, ↑ hard negatives | After 3 epochs without improvement |
| Gradient norm spike | ↓ LR, gradient clipping | Per step |
| Validation accuracy stall | Switches to Phase 2/3/4 | After epoch |
| Tool confusion matrix | ↑ sampling of confused pairs | Per epoch |
| Overfitting (train loss ↓, val loss ↑) | ↑ dropout, ↑ augmentation | Per epoch |

### 14.2 Implementation

```python
class LiveTuner:
    def __init__(self):
        self.history = []  # Log every adjustment
        self.hparams = {
            "learning_rate": 2e-4,
            "temperature": 0.05,
            "hard_neg_ratio": 1.0,
            "batch_composition": "uniform",
        }
    
    def step(self, metrics: dict):
        """Called after each validation epoch. Adjusts hparams."""
        if metrics["val_acc"] < self.history[-1]["val_acc"]:
            # Accuracy dropped — revert last change, try smaller step
            self.hparams["learning_rate"] *= 0.5
            self.hparams["temperature"] *= 0.9
        elif metrics["val_acc"] == self.history[-1]["val_acc"] for 3 epochs:
            # Plateau — increase difficulty
            self.hparams["hard_neg_ratio"] += 0.5
            self.hparams["temperature"] *= 0.8
```

### 14.3 Decision Rules

```yaml
loss_trend_decreasing:
  rate < -5%/epoch → keep going (green)
  rate >= -5%/epoch → plateau detected → lower LR + more hard negs

gradient_norm:
  mean > 1.0 → clip at 1.0 + lower LR
  mean < 0.01 → possibly saturated → increase LR

confusion_matrix_entropy:
  high entropy → model confused → more data for confused tools
  low entropy → model confident → decrease temperature

validation_accuracy:
  <80% → phase 1 (warmup, easy data)
  80-90% → phase 2 (medium difficulty)
  90-95% → phase 3 (hard negatives)
  >95% → phase 4 (sharpening)
```

---

## 15. Cross-Run Meta-Optimizer (Meta-Learning Layer 2)

### 15.1 What It Learns Across Training Runs

Each training run produces a manifest:
```json
{
  "run_id": "rosenna-v14",
  "data": {"total_pairs": 15000, "tools": 25, "corrections": 342},
  "model": {"base": "Qwen2.5-0.5B", "method": "DoRA", "rank": 16},
  "training": {
    "epochs": 10, "batch_size": 32, "temperature": 0.05,
    "optimizer": "Prodigy", "loss": "GISTEmbed",
    "duration_minutes": 28
  },
  "results": {
    "accuracy@1": 0.94, "accuracy@5": 0.99,
    "mrr": 0.97, "latency_gpu_us": 480
  }
}
```

After 10+ runs, the meta-optimizer has data to learn from.

### 15.2 What It Predicts

```
Input:
  data_size, tool_count, correction_ratio, base_model, method
  → Which hyperparameters give best accuracy for THIS run

Output:
  {batch_size, temperature, hard_neg_ratio, optimizer,
   epochs_needed, expected_accuracy}
```

### 15.3 Implementation

```python
class MetaOptimizer:
    """Learns to predict optimal hyperparams from past runs."""
    
    def __init__(self, manifest_dir: str):
        self.manifests = self._load_all(manifest_dir)
    
    def predict(self, run_context: dict) -> dict:
        """Given data size, tools, etc — predict best hparams."""
        if len(self.manifests) < 5:
            return self._default_hparams()  # Not enough data yet
        
        # Find most similar past run
        best = self._most_similar(run_context)
        # Adjust for data size difference
        return self._scale_hparams(best.hparams, run_context)
    
    def learn(self, manifest: dict):
        """After each run, save manifest and update model."""
        self.manifests.append(manifest)
        self._train_predictor()  # Simple regression or tree
```

### 15.4 Convergence Over Time

```
Run 1-3:   Default hparams → 90% accuracy, 30 min
Run 4-7:   Meta-optimizer starts → 93% accuracy, 22 min
Run 8-15:  Good predictions → 95% accuracy, 15 min
Run 16+:   Near-optimal → 96% accuracy, 10 min
```

Each retrain cycle is **faster and more accurate** because the meta-optimizer gets better at guessing what works.

---

## 16. Updated File Structure

```
rosenna_trainer/
├── train.py                    # Entry point
├── config.py                   # All configs
│
├── data/
│   ├── dataset.py              # Load + normalize all sources
│   ├── augment.py              # LLM paraphrase + hard negative gen
│   ├── sampler.py              # In-batch negative composition
│   └── tools.py                # 25 tool definitions
│
├── model/
│   ├── encoder.py              # Qwen2.5 + DoRA/LoRA + pooling
│   ├── losses.py               # InfoNCE, GISTEmbed, SimPO, Triplet
│   └── quantize.py             # GGUF export + quantization
│
├── training/
│   ├── loop.py                 # Main training loop
│   ├── curriculum.py           # Phase scheduling (easy → hard)
│   └── tuner.py                # LIVE auto-tuner (hparam adjustment)
│
├── meta/
│   ├── manifest.py             # Training run logger
│   └── optimizer.py            # CROSS-RUN meta-optimizer
│
├── eval/
│   ├── metrics.py              # Accuracy@1, MRR, confusion
│   └── golden.py               # 80+ golden test cases
│
├── hot/
│   ├── collector.py            # Live correction buffer
│   └── daemon.py               # Trigger retrain, signal reload
│
└── scripts/
    ├── prepare_data.py         # Merge all 23 datasets
    ├── train_full.sh           # Full pipeline
    └── visualize_meta.py       # Plot meta-optimizer learning
```

---

## 17. Complete Training Pipeline Flow

```
START: python train.py --data data/ --output rosenna-v14.gguf
  │
  ├── Meta-Optimizer predicts initial hparams from past runs
  │
  ├── Data Pipeline loads + augments
  │
  ├── Model builds (Qwen2.5 + DoRA + pooling head)
  │
  ├── Phase 1: Warmup (easy pairs, 1 random neg, temp=0.1)
  │   └── LiveTuner monitors loss → no adjustment needed
  │
  ├── Phase 2: Medium (all data, 3 rand negs, temp=0.05)
  │   └── LiveTuner detects plateau → lowers LR, adds more hard negs
  │
  ├── Phase 3: Hard (3 hard negs + in-batch, temp=0.05)
  │   └── LiveTuner detects confusion → rebalances batch sampling
  │
  ├── Phase 4: Sharpening (5 hard negs, temp=0.03, hard only)
  │   └── LiveTuner detects 95% → stops early
  │
  ├── Export: GGUF Q8_0 → rosenna-v14-q8_0.gguf
  │
  ├── Evaluate: golden test cases → accuracy 96%, MRR 0.98
  │
  ├── Save manifest → meta-optimizer learns
  │
  └── Signal: reload to llama-server
        │
        └── Hot training waits for next 100 corrections → repeat

---

## 18. Cloud Model Integration (Teacher API)

### 18.1 Why Cloud Models

| Task | Local Model | Cloud Model (GPT-4, Claude) | Why Cloud |
|------|-------------|------------------------------|-----------|
| Paraphrase generation | OK | **Excellent** | More diverse, higher quality |
| Hard negative mining | Good | **Excellent** | Understands subtle intent differences |
| Edge case discovery | Poor | **Excellent** | Finds blind spots we'd miss |
| Correction validation | OK | **Excellent** | Resolves ambiguous feedback |
| Knowledge distillation | N/A | **Excellent** | Teacher provides soft targets |
| Training strategy advice | N/A | **Excellent** | Meta-optimizer consultant |

### 18.2 Architecture

```
Hot Training Loop
     │
     ├── ≥100 corrections accumulated
     │
     ├── Cloud Teacher API (optional, async)
     │     │
     │     ├── For each correction:
     │     │     ├── Generate 10 paraphrases → add to training data
     │     │     ├── Generate 5 hard negatives → add to training data
     │     │     └── Validate: is this correction correct? → filter noise
     │     │
     │     ├── For each tool:
     │     │     └── Generate 20 edge-case queries → add to training data
     │     │
     │     └── For confusion pair (tool A ↔ tool B):
     │           └── Generate 10 contrastive pairs → sharpen boundary
     │
     ├── Local training (DoRA + GISTEmbed + Prodigy)
     │
     └── Export → reload
```

### 18.3 Cloud Provider Abstraction

```python
class CloudTeacher:
    """Abstract interface for any cloud model provider."""
    
    def generate_paraphrases(self, query: str, tool: str, n: int = 10) -> list[str]:
        """Generate n variations of the same intent."""
        pass
    
    def generate_hard_negatives(self, query: str, tool: str, n: int = 5) -> list[tuple[str, str]]:
        """Generate n (query, wrong_tool) pairs that look similar but route differently."""
        pass
    
    def validate_correction(self, query: str, chosen: str, rejected: str) -> float:
        """Return confidence that this correction is valid (0-1)."""
        pass
    
    def distill_embeddings(self, queries: list[str]) -> list[list[float]]:
        """Get teacher model's embeddings for knowledge distillation."""
        pass
    
    def suggest_hparams(self, manifest: dict) -> dict:
        """Cloud meta-optimizer: suggest hyperparams based on training history."""
        pass

class GPT4Teacher(CloudTeacher):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def generate_paraphrases(self, query, tool, n=10):
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "system",
                "content": f"Generate {n} paraphrases of: '{query}'\n"
                           f"They must all route to tool: {tool}\n"
                           f"Make them diverse in wording and structure."
            }]
        )
        return self._parse_list(response)

class ClaudeTeacher(CloudTeacher):
    # Same interface, Anthropic API
    ...

class LocalTeacher(CloudTeacher):
    """Fallback: use local Qwen2.5-0.5B when no cloud API."""
    ...
```

### 18.4 Knowledge Distillation

The cloud teacher generates **soft targets** — not just hard labels, but embedding distributions:

```python
# Teacher (GPT-4 or Claude) generates:
embeddings = teacher.distill_embeddings(queries)
# These are the "gold standard" — what we want our small model to match
# Loss: MSE between student embedding and teacher embedding
# This is ADDITIONAL to the contrastive loss

loss = gistembed_loss(student_emb, labels) + 0.1 * mse_loss(student_emb, teacher_emb)
```

**Result:** Small model learns from both the training data AND the teacher's representation space. Achieves higher accuracy than training on data alone.

### 18.5 Cloud Meta-Optimizer Consultant

Send the training manifest to a cloud model for strategic advice:

```python
# After each training run:
manifest = save_manifest()
advice = cloud_teacher.suggest_hparams(manifest)

print(f"Cloud advice for next run:")
print(f"  - LR: {advice['learning_rate']}")
print(f"  - Hard neg ratio: {advice['hard_neg_ratio']}")
print(f"  - Suggested data focus: {advice['focus_tools']}")
print(f"  - Reason: {advice['reasoning']}")
```

### 18.6 Cost vs Benefit

| Operation | Cost per 1K corrections | Benefit |
|-----------|------------------------|---------|
| Paraphrase gen (10x) | ~$0.50 (GPT-4o) | 10× more training data |
| Hard negative gen (5x) | ~$0.30 (GPT-4o) | 5× better at hard cases |
| Correction validation | ~$0.10 (GPT-4o mini) | Filters noise, improves data quality |
| Knowledge distillation | ~$2.00 (10K queries) | Teacher-quality embeddings |

**Strategy:** Use GPT-4o-mini for routine augmentation ($0.15/M tokens), GPT-4o for strategic advice. Total cost: ~$1-5 per retrain cycle.

### 18.7 Provider-Agnostic Config

```yaml
# config.yaml
cloud_teacher:
  provider: "openai"  # or "anthropic", "google", "local"
  model: "gpt-4o-mini"  # or "claude-3-haiku", "gemini-2.0-flash"
  api_key: "${CLOUD_API_KEY}"  # from environment
  tasks:
    paraphrase: true
    hard_negatives: true
    validate_corrections: true
    knowledge_distillation: false  # expensive, enable for final run
    meta_optimizer: true  # cheap, always on
```
```

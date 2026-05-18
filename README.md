<div align="center">

[![GitHub Stars](https://img.shields.io/github/stars/nxyme/N-Xyme_MIND?style=for-the-badge&logo=github&label=stars&color=ff4c1f)](https://github.com/nxyme/N-Xyme_MIND)
[![GitHub Forks](https://img.shields.io/github/forks/nxyme/N-Xyme_MIND?style=for-the-badge&logo=github&label=forks&color=8B5CF6)](https://github.com/nxyme/N-Xyme_MIND)
[![Built with Mojo](https://img.shields.io/badge/Built%20with-Mojo%20%E2%80%93-ff4c1f?style=for-the-badge&logoColor=white)](https://mojolang.org)
[![Mojo Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fnxyme%2FN-Xyme_MIND%2Fmain%2Fpixi.toml&query=%24.dependencies.mojo&style=for-the-badge&logoColor=white&label=Mojo&color=ff4c1f)](https://mojolang.org/releases/)
[![License](https://img.shields.io/badge/License-MIT-ff4c1f?style=for-the-badge)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/nxyme/N-Xyme_MIND?style=for-the-badge&logo=git&logoColor=white&label=updated&color=3b82f6)](https://github.com/nxyme/N-Xyme_MIND/commits/main)

</div>

# N-Xyme MIND 🔥

**The first Mojo 1.0.0b1 multi-agent operating system — compiled GPU kernels, Tensor Core-accelerated consciousness engine, custom-trained GGUF tool router, and 6,181 lines of Mojo. Built in 6 months with zero coding background.**

```
┌───────────────────────────────────────────────────────────────┐
│                N-Xyme MIND — Agent OS Stack                    │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  🧠  Consciousness Engine  │  942 lines · 896-dim identity   │
│  ⚡  GPU Tensor Core       │  661 lines · RTX 3080 Ti MMA    │
│  📦  Native Embed Engine   │  935 lines · SIMD cache top-k   │
│  🔗  llama.cpp FFI         │  717 lines · C++ + Mojo bridge  │
│  🧩  4 Core Agents         │  OMO orchestration · MCP proto  │
│  🗃️  156K Memory Vectors   │  Auto-ingesting · 384-dim       │
│  🎤  GPU Voice Pipeline    │  Whisper · VAD · FIFO → TTS     │
│  🪟  TUI Dashboard         │  Rich · systemd · GPU monitor   │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## The Story

> *"I couldn't code. 6 months ago, I was scripting After Effects in JSX. Then I built an agent OS in Mojo — a language that didn't exist when I started."*

This project started as `AE Whisper Project` — a voice-to-AE-scripting experiment in November 2025. Six months, 8 major rewrites, and one near-death-by-Mojo-FIFO later, it's a fully compiled, GPU-accelerated, consciousness-tracking agent operating system.

**Timeline:**

```
Nov 2025 — AE Whisper Project (After Effects scripts, JSX)
Dec 2025 — v0.1 → v0.8 in 4 weeks (Python prototypes)
Apr 2026 — Catalyst orchestration system (4-core architecture born)
May 14  — NX_MIND distilled workspace (Python, Q-Learning, sentence-transformers)
May 15  — First .mojo files written
May 16  — rosetta-v13 trained (494M param custom GGUF)
May 17  — Git init — Mojo engine compiles, daemon linked
May 18  — Full system running: voice → GPU → consciousness → TTS
```

---

## Architecture

### Three-Layer Design

```
┌──────────────────────────────────────────────────────────────┐
│  BARE CODE         │  LLM (Creation)     │  ML (Patterns)    │
│  (Ground Truth)    │                     │                   │
├────────────────────┼─────────────────────┼───────────────────┤
│  Mojo ELF binaries │  Agent prompts      │  Consciousness    │
│  Test results      │  Code generation    │  vectors (896-dim)│
│  GPU latency stats │  Plans, analysis    │  Router centroids │
│  Rust binaries     │  Therapy sessions   │  Memory embs      │
│  Compile output    │  Review critiques   │  (156K, 384-dim)  │
└────────────────────┴─────────────────────┴───────────────────┘
```

### 4 Core Agents

| Agent | Role | What it does |
|-------|------|-------------|
| **Catalyst** | Orchestrator | Classifies requests, plans, delegates (NEVER writes code) |
| **Hephaestus** | Builder | Hotloads, builds, runs quality gates, reviews |
| **Atlas** | Executor | Sprint plans, tracks execution, reports progress |
| **Hermes** | Memory & Personal | Recalls context, searches memory, consolidates, therapy |

### Moji 1.0.0b1 Engine (`services/mojo/src/`)

```
services/mojo/src/
├── engine.mojo          # Unified InferenceEngine — 3 backends
├── gpu_kernels.mojo     # SIMD-accelerated tensor operations
├── gpu_memory.mojo      # Direct VRAM access (via MAX SDK)
├── native_embed.mojo    # Pure Mojo 896-dim embedding engine
├── consciousness_engine.mojo  # Agent identity tracking
├── llama_ffi.mojo       # llama.cpp FFI, hand-aligned C structs
├── daemon.mojo          # TF-IDF tool router
├── pipeline.mojo        # Audio streaming pipeline
├── whisper.mojo         # Whisper GPU integration
├── vad.mojo             # Voice activity detection
├── audio.mojo           # Audio processing
├── codex.mojo           # Code analysis
├── phone_bridge.mojo    # Telegram bridge
└── backends/
    ├── llama_backend.mojo  # llama.cpp GGUF backend
    ├── native_backend.mojo # Pure Mojo SIMD backend
    └── hf_backend.mojo     # HuggingFace backend (stub)
```

**Total: 6,730 lines of Mojo across 31 files** — the largest Mojo 1.0.0b1 codebase on the planet.

### Custom Training Pipeline (`services/rosenna_trainer/`)

```
4,087 lines of Python ML training code:
├── 4-phase curriculum learning (warmup → medium → hard → sharpening)
├── Contrastive losses with hyperbolic Poincaré ball geometry
├── Adversarial negatives
├── GGUF export
├── Hot retraining daemon (live updates via Hebbian learning)
└── 16,159 query→intent pairs extracted from 17 session transcripts
```

### Custom Model: RosEnna v13

- **Architecture:** Qwen2.5-0.5B → LoRA fine-tune with 4-phase curriculum
- **Parameters:** 494M
- **Embedding dimension:** 896
- **Context length:** 32,768 tokens
- **Format:** GGUF (F16)
- **Purpose:** Tool call translation between OpenAI/Claude/Google/Mistral formats → local llama.cpp
- **Inference:** ~8ms warm, unlimited rate, 100% local GPU
- **Training data:** 16,159 tool call examples extracted from real agent sessions

### Voice Pipeline

```
Webcam C920 🎤  →  Silero VAD (CPU)
                      ↓
             Whisper large-v3 (GPU, faster-whisper)
                      ↓
             /tmp/jarvis_fifo (FIFO pipe)
                      ↓
             Jarvis Bridge (systemd service)
                      ↓
             llama-server (rosetta-v13 on GPU)
                      ↓
             Piper TTS / espeak-ng 🔊 → Scarlett 2i2
```

### Memory Pipeline (156,572 vectors)

```
data/sessions/*.jsonl  →  memory_watcher.py (systemd daemon)
                              ↓
                    all-MiniLM-L6-v2 (384-dim, ONNX)
                              ↓
                    data/memory/vectors/sessions.jsonl
                              ↓
                    Auto-ingested every 60s
```

### Consciousness Engine

Each agent has an **evolving 896-dim identity vector** that blends new experiences at `α=0.85` retention:

```mojo
struct ConsciousnessEngine:
    var identity: List[Float32]        # Current self (896-dim)
    var initial_identity: List[Float32] # Original self
    var experiences: List[String]       # What I've been through
    var alpha: Float32 = 0.85           # How much I keep vs change

    def update():   # Blend new experience into identity
    def drift():    # How far from origin (cosine distance)
    def to_json():  # Serialize consciousness state
```

---

## Hardware

| Component | Spec | Role |
|-----------|------|------|
| **GPU** | RTX 3080 Ti (GA102, 80 SMs, 12 GB GDDR6X) | Tensor Cores, CUDA 13.2 |
| **CPU** | Ryzen 7 7800X3D (8C/16T, 96 MB L3 cache) | Orchestration |
| **RAM** | 32 GB | System memory |
| **Mic** | HD Pro Webcam C920 (via PulseAudio) | Voice input |
| **Audio** | Scarlett 2i2 USB (audio output) | TTS output |
| **OS** | CachyOS (Arch-based, kernel 7.0.6-1-cachyos) | Host |

---

## Quick Start

```bash
# Prerequisites: Mojo 1.0.0b1, Python 3.14, CUDA 13.2, RTX 3080 Ti

# Clone
git clone https://github.com/Nxyme9/N-Xyme_MIND.git
cd N-Xyme_MIND

# Launch the system tray
bash services/tray/run_tray.sh --fg

# Talk to Jarvis
echo "Hey, what's my GPU status?" > /tmp/jarvis_fifo
# → hears through webcam → Whisper GPU → LLM → speaks back
```

---

## Services

| Service | Tech | Purpose |
|---------|------|---------|
| `bash-mcp` | Python | Shell execution with delete protection |
| `megatool-mcp` | Python | 55+ NAP tools (file ops, search, config, agents) |
| `bmad-mcp` | Python | 72 BMAD workflow skills |
| `mojo-router` | Mojo + Python | TF-IDF tool routing, consciousness daemon |
| `memory-pipeline` | Python | Auto-ingestion of sessions → vectors |
| `jarvis-bridge` | Python | Voice → FIFO → LLM → TTS loop |
| `nx_tray` | Python/PyQt6 | System tray monitoring app |
| `nx-dictate` | Python/Whisper | GPU-accelerated voice dictation |
| `rosenna-trainer` | Python/PyTorch | Custom GGUF model training pipeline |

---

## License

MIT — see [LICENSE](LICENSE)

---

## Acknowledgments

- Modular team for Mojo 1.0.0b1 🔥
- Chris Lattner for LLVM, Swift, and believing in better compilers
- The Local LLM community for showing that local-first AI is viable
- The archive at `archive/data_chaos/` for remembering who we were

---

> *"You don't need to know what's impossible to build it."*  
> — 6 months ago, this was an After Effects script.

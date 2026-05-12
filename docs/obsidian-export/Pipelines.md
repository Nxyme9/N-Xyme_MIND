---
type: system-knowledge
status: active
date: 2026-04-09
tags: [pipeline, timing, codeos, audio]
related: [[ARCHIVE_Overview], [Crown_Jewels]]
rating: 10
---

# 5 MAIN PIPELINE SYSTEMS

## 1. M.I.N.D Timing Pipeline (v0.8-0.9)
**Purpose**: Audio-to-video timing for lyric videos

### Stages (6)
1. Whisper ASR — Transcription
2. SilenceSnap — VAD-aware silence detection
3. MUSIAlign — JOINT3 alignment
4. AE Export — JSON generation with offsets
5. FX Map — Effect metadata
6. Mamba2 — Feature extraction

## 2. CodeOS Meta-Kernel Pipeline (v3.0)
**Purpose**: Multi-kernel orchestration

### Components
- 8 live kernels: ASR, ALIGN, AE, ARCHITECTURE, BRICK, ANALYZER, META, MEMORY
- Memory Cortex (anchors every kernel)
- Codex/DeepSeek static checks (gates every release)

## 3. Tools Packaging Pipeline (NXU_/NXM_)
**Purpose**: Reproducible packs

### Components
- Shared harness
- Self-test flags
- Admin checks
- Version management

## 4. Lyric/Video Timing Pipeline
**Purpose**: Word-level SRT generation

### Output
- SRT/JSON from Whisper

### Key Scripts
- make_word_srt.py
- RUN_LYRICS.bat

## 5. Multi-LLM Routing Pipeline
**Purpose**: Cortex assignment

### Components
- llm_router.py — Task → cortex mapping
- Branch & Route Wizard — Kernel enforcement
- Pattern analyzer — Task classification

---

*Source: `/mnt/WIN_LIBRARY/_NXYME_ARCHIVE/99_ARCHIVE_META/PIPELINES.md`*

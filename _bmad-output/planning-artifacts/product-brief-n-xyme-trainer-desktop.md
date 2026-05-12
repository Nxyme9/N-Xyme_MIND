---
stepsCompleted: []
workflowType: 'product-brief'
---

# Product Brief: N-Xyme Trainer Desktop App

**Author:** N-Xyme  
**Date:** 2026-04-23  
**Version:** 1.0

---

## Executive Summary

**N-Xyme Trainer** is a standalone desktop application for fine-tuning Large Language Models (LLMs). Built with Tauri + React, it provides a sleek, modern, ADHD-friendly UI that makes LLM fine-tuning accessible to everyone—no CLI, no documentation hunting, no fragmentation.

**Why now?** Fine-tuning LLMs is currently:
- CLI-only (requires terminal expertise)
- Fragmented (multiple tools, no unified UX)
- Not general-purpose (narrow tools for narrow tasks)
- No standalone UX (always requires external setup)

**Our solution:** A beautiful desktop app that guides users from data → model → training → export in 5 simple steps.

---

## Target Users

| Segment | Pain Points | How We Help |
|---------|-------------|-------------|
| **ML Engineers** | Slow iteration, CLI overhead | One-click training with presets |
| **Full-Stack Devs** | Need specialized models, no ML expertise | No-code fine-tuning |
| **Startups** | Budget constraints, need custom models | Free local training |
| **Research Hobbyists** | Want to experiment, intimidated by CLI | Friendly wizard UI |

---

## Product Vision

> *"Fine-tune any model for any purpose with zero friction."*

The app should feel like a modern consumer app, not a dev tool. Big buttons. Clear progress. No jargon. Just:
1. Upload your data
2. Pick a model
3. Choose a preset
4. Watch it train
5. Download your model

---

## Key Features

### Core Features (MVP)

1. **Data Upload Wizard**
   - Drag & drop JSONL/CSV files
   - Automatic validation with friendly errors
   - Data preview (first 5 rows)
   - Column mapping for CSV

2. **Model Selection**
   - Visual model cards with:
     - Model name + size
     - VRAM requirement
     - Best use case
   - Auto-detect GPU compatibility
   - Pre-loaded models: Qwen2.5 (0.5B, 1.8B, 3B), Llama3-8B

3. **Training Configuration**
   - Task templates: Chat, Tool-Calling, Classification, Summarization
   - Preset selector: ⚡ Fast / ⚖️ Balanced / 🎯 Quality
   - Advanced params (collapsible): epochs, LR, batch size

4. **Training Dashboard**
   - Real-time progress bar
   - Live loss curve (Chart.js)
   - GPU memory usage
   - ETA countdown
   - Cancel button

5. **Model Export**
   - One-click GGUF download
   - Training summary stats
   - Optional HuggingFace push

### ADHD-Friendly Design Principles

- **Big touch targets** (min 44px)
- **Clear visual hierarchy** (one primary action per screen)
- **Progress always visible** (never wonder "is it working?")
- **Gentle onboarding** (5-step wizard, not overwhelming)
- **Forgiving UI** (confirm before destructive actions)
- **Dark mode default** (easy on eyes)
- **Keyboard shortcuts** (power user support)

---

## Technical Architecture

### Stack

| Layer | Technology | Justification |
|-------|------------|---------------|
| **Desktop Shell** | Tauri 2.x | Fast, small, native |
| **Frontend** | React 18 + Next.js 14 | Modern, component-based |
| **Styling** | Tailwind CSS | Rapid dev, consistent |
| **State** | Zustand | Simple, performant |
| **Charts** | Chart.js | Lightweight, reactive |
| **Backend** | Rust (Tauri commands) | Native performance |
| **Training** | Python subprocess → unsloth | QLoRA fine-tuning |
| **DB** | SQLite (via Tauri) | Job tracking |

### Integration Points

- Training pipeline: `packages/training/train_rosetta_unified.py`
- GGUF export: Built into training pipeline
- Model cache: `~/.cache/huggingface/`
- App data: `{app_data_dir}/n-xyme-trainer/`

### File Structure

```
nx-mind-desktop/
├── src-tauri/
│   ├── src/
│   │   ├── main.rs          # Entry + window config
│   │   ├── trainer.rs       # NEW: Training commands
│   │   └── models.rs        # NEW: Model management
│   └── Cargo.toml
├── src/
│   ├── app/
│   │   └── page.tsx         # Existing N-Xyme MIND
│   └── trainer/             # NEW: Trainer module
│       ├── page.tsx         # Main trainer page
│       ├── components/
│       │   ├── DataUpload.tsx
│       │   ├── ModelSelect.tsx
│       │   ├── Configure.tsx
│       │   ├── TrainingDashboard.tsx
│       │   └── Export.tsx
│       ├── hooks/
│       │   └── useTraining.ts
│       └── stores/
│           └── trainerStore.ts
└── tauri.conf.json          # App config (update name + icon)
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| First training run | < 5 min (from install to training) |
| Time to value | < 2 min (first model download) |
| Crash rate | < 1% |
| User satisfaction | > 4.5/5 |
| Retention | > 60% run 2+ trainings |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| GPU compatibility issues | Auto-detect VRAM, recommend model |
| Training takes too long | Presets for fast iteration |
| User doesn't understand ML | Friendly defaults, tooltips |
| Export format issues | Standard GGUF, verify before download |

---

## Next Steps

1. **Update Product Brief** → This document ✅
2. **Create PRD** → [CP] Create PRD skill
3. **Design UX** → [CU] Create UX skill
4. **Plan Architecture** → [CA] Create Architecture
5. **Break into Stories** → [CE] Create Epics and Stories
6. **Build** → Implementation

---

**Prepared for:** BMAD Workflow  
**Output:** `_bmad-output/planning-artifacts/product-brief-n-xyme-trainer-desktop.md`
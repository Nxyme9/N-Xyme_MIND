---
stepsCompleted: [1, 2, 3, 4, 5, 6]
workflowType: 'mvp-scope'
project_name: 'N-Xyme Trainer Desktop'
user_name: 'N-Xyme'
date: '2026-04-24'
phase: 'mvp'
---

# MVP Scope - N-Xyme Trainer Desktop

**Date:** 2026-04-24  
**Purpose:** Define achievable v1.0 MVP scope

---

## MVP Definition

### In Scope (v1.0) ✅

| Epic | Name | Stories | Priority |
|------|------|---------|----------|
| E1 | App Shell & Navigation | 4 | P0 |
| E2 | Data Input & Validation | 5 | P0 |
| E3 | Model Selection | 3 (local only) | P0 |
| E4 | Training Configuration | 4 | P0 |
| E5 | Local Training Execution | 7 | P0 |
| E8 | Model Export (basic) | 3 (GGUF only) | P0 |

### Out of Scope (v2.0+) ❌

| Epic | Name | Reason |
|------|------|--------|
| E3S2-S5 | HuggingFace Hub | Requires API integration |
| E6 | Cloud Training | Requires provider APIs |
| E7 | Multi-GPU | Requires complex coordination |
| E9 | In-App Inference | Separate feature |
| E10 | Team Features | Requires auth infrastructure |
| E3S5 | Custom Model Upload | Nice to have |
| E2S5 | URL Import | Nice to have |
| E8S3 | HF Push | Nice to have |

---

## MVP Feature List

### Core Features

1. ✅ **5-Step Wizard**
   - Data upload (JSONL/CSV)
   - Local model selection
   - Training configuration (presets)
   - Training execution with progress
   - GGUF export & download

2. ✅ **Window Management**
   - Minimize/maximize/close
   - Custom title bar
   - Sidebar navigation

3. ✅ **Local Training**
   - QLoRA fine-tuning
   - Real-time progress bar
   - Loss chart
   - ETA calculation
   - Cancel training
   - Job persistence

4. ✅ **Model Export**
   - GGUF export
   - Download to local

---

## Technical Requirements (MVP)

### Must Have

| Requirement | Implementation |
|-------------|----------------|
| Tauri 2.x | Desktop shell |
| React 18 | Frontend |
| Zustand | State management |
| SQLite | Local database |
| Python 3.10+ | Training pipeline |
| NVIDIA GPU | Training execution |

### Not Required for MVP

- HuggingFace API integration
- Cloud provider APIs
- Multi-GPU support
- User authentication
- Team features

---

## Implementation Order

| Phase | Epics | Duration |
|-------|-------|----------|
| **Phase 1** | E1 (App Shell) | 1 week |
| **Phase 2** | E2 (Data Input) + E3 (Model Selection) | 1 week |
| **Phase 3** | E4 (Configuration) | 3 days |
| **Phase 4** | E5 (Training) | 1.5 weeks |
| **Phase 5** | E8 (Export) | 3 days |
| **QA** | Testing & polish | 1 week |

**Total MVP:** ~5 weeks

---

## Future Phases

### v1.1 (2 weeks)
- HuggingFace Hub browser
- Cloud training (RunPod)

### v2.0 (4 weeks)
- Multi-GPU training
- In-app inference
- Team features

---

## Verification Checklist

Before claiming MVP complete:

- [ ] User can upload JSONL/CSV data
- [ ] User can select local model
- [ ] User can configure training
- [ ] User can start local training
- [ ] Progress bar shows real progress
- [ ] Loss chart updates in real-time
- [ ] User can cancel training
- [ ] User can download GGUF
- [ ] Jobs persist across restarts
- [ ] Window controls work

---

**MVP Status:** Ready for Sprint Planning

**Next Step:** [SP] Sprint Planning
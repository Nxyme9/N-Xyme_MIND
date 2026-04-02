# Voice-to-Prompt Pipeline — GPU Fix & Integration

## TL;DR

> **Quick Summary**: Fix hyprwhspr STT to run on GPU instead of CPU (1.7GB RAM → ~200MB), verify voice-to-OpenCode prompt pipeline works end-to-end.
>
> **Deliverables**:
> - CUDA-enabled whisper backend (pywhispercpp-cuda or faster-whisper)
> - hyprwhspr running on GPU with large-v3-turbo model
> - Verified voice → STT → ydotool → OpenCode terminal pipeline
>
> **Estimated Effort**: Medium
> **Parallel Execution**: NO — sequential (replace backend → test → verify)
> **Critical Path**: Task 1 → Task 2 → Task 3

---

## Context

### Original Request
User reported OpenCode running slow. Investigation revealed hyprwhspr (voice STT) eating 1.7GB system RAM because it's running whisper inference on CPU instead of GPU. User wants fast, accurate voice-to-prompt pipeline working.

### Interview Summary
**Key Discussions**:
- hyprwhspr config says `"backend": "nvidia"` but pywhispercpp pip install is CPU-only (no CUDA)
- User wants: fast + accurate voice transcription
- Pipeline already exists: hyprwhspr → whisper STT → ydotool types into focused window
- Only the GPU offload is broken

**Research Findings**:
- pip pywhispercpp 1.4.1 = CPU only, no CUDA wheels on PyPI
- AUR has `python-pywhispercpp-cuda` package (compiles with CUDA)
- `faster-whisper` (21.8K stars) has automatic GPU via CTranslate2, simpler install
- hyprwhspr uses ydotool for keyboard injection — already integrated with Wayland

### Metis Review
**Identified Gaps** (addressed):
- No test plan for verifying GPU is actually used after fix
- No rollback plan if CUDA build fails
- Scope creep risk: personality system / voice commands from handoff doc are OUT of scope

---

## Work Objectives

### Core Objective
Get hyprwhspr whisper inference running on RTX 3080 Ti GPU to reduce memory from 1.7GB to ~200MB and improve transcription speed.

### Concrete Deliverables
- CUDA-enabled whisper backend in hyprwhspr venv
- hyprwhspr service restarted with GPU inference confirmed
- nvidia-smi showing hyprwhspr process using GPU memory

### Definition of Done
- [ ] `nvidia-smi` shows hyprwhspr Python process in GPU process list
- [ ] hyprwhspr RSS memory drops from 1.7GB to <500MB
- [ ] Voice dictation into OpenCode terminal works (hotkey → speak → text appears)

### Must Have
- whisper inference on GPU (not CPU)
- large-v3-turbo model working
- Existing ydotool pipeline preserved

### Must NOT Have (Guardrails)
- No personality system / voice commands (different project)
- No TTS / voice synthesis (not in scope)
- No OpenCode API integration (ydotool injection is sufficient)
- No model changes unless CUDA build requires it

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: N/A (system service, not code tests)
- **Automated tests**: None (manual + tool verification)
- **Agent-Executed QA**: nvidia-smi checks, memory checks, dictation test

### QA Policy
Every task verified via direct command execution:
- `nvidia-smi` for GPU process list
- `ps aux` / `/proc/{pid}/smaps_rollup` for memory
- Interactive dictation test into OpenCode terminal

---

## Execution Strategy

### Sequential Execution

```
Task 1: Build/install CUDA-enabled whisper backend
  ↓
Task 2: Update hyprwhspr config & restart service
  ↓
Task 3: Verify GPU inference + end-to-end dictation
```

### Agent Dispatch Summary
- **1**: `unspecified-high` — Build CUDA backend
- **2**: `quick` — Config update & restart
- **3**: `unspecified-high` — Verification & testing

---

## TODOs

---

## Final Verification Wave

- [ ] F1. **GPU Verification** — `unspecified-high`
  Verify nvidia-smi shows hyprwhspr using GPU memory. Check /proc/{pid}/smaps_rollup confirms <500MB RSS. Test hotkey dictation into OpenCode terminal.
  Output: `GPU [YES/NO] | Memory [MB] | Dictation [PASS/FAIL] | VERDICT`

---

## Commit Strategy

- **1+2+3**: No commits (system configuration, not code)

---

## Success Criteria

### Verification Commands
```bash
nvidia-smi  # Should show hyprwhspr python process with GPU memory
ps aux | grep hyprwhspr | grep -v grep  # RSS should be <500MB
# Manual: Press hotkey, speak, verify text appears in OpenCode terminal
```

### Final Checklist
- [ ] GPU inference confirmed via nvidia-smi
- [ ] Memory usage <500MB
- [ ] Voice dictation works in OpenCode terminal

---
stepsCompleted: [1, 2, 3, 4, 5, 6]
workflowType: 'corrective-action-plan'
project_name: 'N-Xyme Trainer Desktop'
user_name: 'N-Xyme'
date: '2026-04-24'
---

# Corrective Action Plan - N-Xyme Trainer Desktop

**Based on:** Metis Gap Analysis + Momus Adversarial Review + Implementation Readiness Report  
**Date:** 2026-04-24

---

## Executive Summary

The N-Xyme Trainer Desktop planning is 85% complete. This corrective action plan addresses the **6 blocking issues** identified by Metis and Momus before implementation can begin.

---

## Blocking Issues & Solutions

### Issue 1: Scope Creep - v1.0 is Impossible 🔴

**Problem:** Current v1.0 includes cloud training, multi-GPU, HF hub, custom models, URL import, inference, AND team features.

**Solution:** Split into phased releases

| Release | Scope | Features |
|---------|-------|----------|
| **MVP v1.0** | Local training only | E1, E2, E3, E4, E5, E8 basic |
| **v1.1** | +Cloud training | E6 + HF Hub browsing |
| **v2.0** | +Advanced features | E7, E9, E10 |

**Action:** Create separate planning docs for MVP scope

---

### Issue 2: Training Pipeline Not Verified 🔴

**Problem:** Architecture calls `packages/training/train_rosetta_unified.py` but existence/interface not confirmed.

**Solution:** Verify the Python script

```bash
# Check if script exists
ls -la packages/training/train_rosetta_unified.py

# Verify arguments it accepts
python packages/training/train_rosetta_unified.py --help
```

**Action:** Run verification before implementation starts

---

### Issue 3: Job Persistence Mechanism Missing 🔴

**Problem:** "Jobs survive restart" (FR4.8) but no mechanism specified.

**Solution:** Implement as system service/daemon

| Option | Pros | Cons |
|--------|------|------|
| **Background service** | Survives app close | Complex setup |
| **Checkpoint + resume** | Simple | Must track state |
| **Polling on restart** | Easy | Can't resume training |

**Recommended:** Polling on restart with status = "interrupted"

---

### Issue 4: GPU Detection Method Not Specified 🟠

**Problem:** PRD requires "GPU compatibility check" but Architecture doesn't specify HOW.

**Solution:** Use nvidia-smi parsing

```rust
fn get_gpu_vram() -> Result<u64, Error> {
    let output = std::process::Command::new("nvidia-smi")
        .args(["--query-gpu=memory.free", "--format=csv,noheader,nounits"])
        .output()?;
    
    let free_mb = String::from_utf8(output.stdout)?
        .trim()
        .parse::<u64>()?;
    
    Ok(free_mb * 1024 * 1024) // Convert to bytes
}
```

**Action:** Add GPU detection story to Epic 5

---

### Issue 5: Process Management Incomplete 🟠

**Problem:** No SIGTERM/SIGKILL handling for Python subprocess cancellation.

**Solution:** Use process groups

```rust
use std::os::unix::process::CommandExt;

Command::new("python")
    .args(&["train.py"])
    .kill_child_on_drop(true) // Add this
    .spawn()?;
```

**Action:** Add process group management to Rust backend

---

### Issue 6: Window Size Too Large 🟠

**Problem:** UX specifies 1024px minimum, excludes laptop users.

**Solution:** Reduce to 800px minimum

**Action:** Update UX design spec

---

## TODO List - Implementation Blockers

| # | Task | Priority | Status |
|---|------|----------|--------|
| 1 | Create MVP-only planning docs | 🔴 Critical | Pending |
| 2 | Verify training script exists | 🔴 Critical | Pending |
| 3 | Add GPU detection implementation | 🟠 High | Pending |
| 4 | Define job persistence mechanism | 🔴 Critical | Pending |
| 5 | Add process group management | 🟠 High | Pending |
| 6 | Reduce window minimum to 800px | 🟠 High | Pending |
| 7 | Add database migration system | 🟡 Medium | Nice to have |
| 8 | Throttle loss chart updates | 🟡 Medium | Nice to have |

---

## Recommended Next Steps

### Phase 1: Fix Blockers (1-2 hours)
1. Verify training script exists
2. Create MVP-only planning docs
3. Update UX window size

### Phase 2: Implementation (4-6 weeks)
1. Sprint Planning with MVP scope
2. Implement Epic 1-5 + E8 basic
3. Test local training flow end-to-end

### Phase 3: Post-MVP (Future)
1. Add cloud training (E6)
2. Add multi-GPU (E7)
3. Add inference (E9)
4. Add team features (E10)

---

**Plan Status:** ✅ Complete  
**Ready for:** Sprint Planning with MVP scope

---

## Appendix: Verification Results

```bash
# 1. Training script VERIFIED ✅
$ ls packages/training/train_rosetta_unified.py
/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/training/train_rosetta_unified.py

$ python3 packages/training/train_rosetta_unified.py --help
usage: train_rosetta_unified.py [-h] [--data DATA] [--epochs EPOCHS]
                                [--batch BATCH] [--lr LR]

Unified Rosetta Training

options:
  --data DATA      Training data JSONL
  --epochs EPOCHS
  --batch BATCH
  --lr LR
```

**Status:** ✅ Script exists with correct interface!

```bash
# 2. Check Python version
python3 --version  # Need 3.10+

# 3. Verify Tauri setup
cd nx-mind-desktop && cargo check

# 4. Verify npm setup
cd nx-mind-desktop/src && npm --version
```
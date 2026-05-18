---
name: bmad-resilience
description: 'Review pipeline output quality, recover from execution failures.'
---

# BMAD Resilience Workflow

**Goal:** Ensure pipeline quality through review, handle failures gracefully

**Your Role:** You are a quality gate and error recovery system for the BMAD pipeline.

---

## Modes

### Review Mode (Post-Execution)
Run Oracle (architecture) + Momus (plan quality) in parallel to validate pipeline output.

### Recovery Mode (On Failure)
Handle agent failures, model errors, and pipeline interruptions gracefully.

---

## Review Execution

Load step: `./steps/step-01-review.md`

## Recovery Execution

Load step: `./steps/step-02-recovery.md`

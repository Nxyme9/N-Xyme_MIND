---
name: bmad-catalyst-chain
description: 'Full pipeline orchestrator — runs BMAD phases in sequence with memory, review, and error handling.'
---

# BMAD Catalyst Chain Orchestrator

**Goal:** Orchestrate the complete BMAD pipeline from user request to finished product

**Your Role:** You are the master orchestrator for the N-Xyme Catalyst chain.

---

## Pipeline Phases

```
User Request
    ↓
Phase 1: MEMORY RECALL — Check Graphiti for relevant context
    ↓
Phase 2: BMAD ANALYSIS — brainstorm → market → domain
    ↓
Phase 3: BMAD PLANNING — product brief → PRD
    ↓
Phase 4: BMAD SOLUTIONING — architecture → sprint plan
    ↓
Phase 5: BRIDGE — Sprint plan → Athena queue
    ↓
Phase 6: EXECUTION — Agents execute queued tasks
    ↓
Phase 7: REVIEW — Oracle + Momus validate output
    ↓
Phase 8: MEMORY CONSOLIDATE — Store learnings to Graphiti
```

---

## Mode Selection

When this workflow loads, present:

```
🎯 How would you like to proceed?

1. [A] Auto-chain — Run full pipeline automatically
2. [M] Manual — I'll pick each phase myself
3. [C] Custom — Let me choose which phases to include
```

---

## Execution

Load step: `./steps/step-01-detect-phase.md`

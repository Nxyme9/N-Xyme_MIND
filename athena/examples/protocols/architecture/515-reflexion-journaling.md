---
protocol: 515
name: Reflexion Journaling
domain: architecture
created: 2026-03-05
last_updated: 2026-03-05
status: active
---

# Protocol 515: Reflexion Journaling (Failure Memory)

> **Source**: Reflexion (NeurIPS 2023, arXiv:2303.11366). Adapted from weight-update self-improvement to prompt-layer episodic learning.

## Problem

Standard quicksave stores *facts* — what happened. It does not store *lessons* — why something failed and what to do differently. Without failure memory, the same mistakes recur across sessions because the Exocortex retrieves historical facts but not the corrective insight.

## Mechanism

After any task involving errors, backtracking, or suboptimal outcomes, append a structured **reflexion entry** to the quicksave:

```
[REFLEXION] What failed: <specific failure>. Why: <root cause>. Lesson: <what to do differently>.
```

### Trigger Conditions

- Tool call failed and required retry
- User corrected the output
- Λ classification was wrong (over-processed or under-processed)
- Co-activation chain hit a dead end or required backtracking
- Quality gate rejected output

### Entry Format

| Field | Content |
|---|---|
| **What failed** | Observable failure (e.g., "spec-driven-dev triggered full pipeline for 10-line CSS fix") |
| **Why** | Root cause (e.g., "Λ misclassified as STANDARD due to keyword 'build'") |
| **Lesson** | Corrective rule (e.g., "Scope-bounded single-file edits are SNIPER regardless of keyword") |

### Storage and Retrieval

- Reflexion entries are stored in session logs via `quicksave.py`
- The `[REFLEXION]` tag makes them searchable via Exocortex
- Future queries that match the failure context will retrieve the lesson alongside factual results
- This creates a self-correcting retrieval loop without model fine-tuning

## Biological Analogy

Episodic memory stores events. Reflexion stores **immune responses** — the organism's learned reaction to a specific pathogen. Once encoded, the antibody (lesson) is retrieved faster than the original infection (mistake) can recur.

## References

- [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366)
- [Protocol 502: Context Lifecycle](502-context-lifecycle.md)
- `/start` workflow (boot sequence)

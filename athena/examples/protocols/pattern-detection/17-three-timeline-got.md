---
created: 2025-12-10
last_updated: 2026-01-30
graphrag_extracted: true
---

---name: three-timeline-got
description: Magic number 3 for decision analysis. Best/Base/Worst or Continue/Modify/Exit configurations. 3 timelines captures 80%+ variance at 30% compute cost.
created: 2025-12-10
last_updated: 2025-12-31
---

# Protocol: 3-Timeline Interconnected GoT

## Date Added: 9 December 2025

> **Related Protocol**: [16-synthetic-parallel-reasoning](16-graph-of-thoughts-theory.md), [18-probabilistic-analysis-stack](18-probabilistic-analysis-stack.md)

## 17.1 The Magic Number: 3

**3 timelines captures 80%+ of decision-relevant variance at 30% of compute cost.**

| N Timelines | Cognitive Load | Marginal Insight | Verdict |
|-------------|----------------|------------------|---------|
| 1 | Low | — | ❌ No alternatives |
| 2 | Low | High | ⚠️ Binary trap |
| **3** | **Medium** | **High** | ✅ **Sweet spot** |
| 4-5 | High | Medium | ⚠️ Diminishing returns |
| 10+ | Overwhelming | Minimal | ❌ Analysis paralysis |

## 17.2 Standard 3-Timeline Configurations

**Configuration A: Outcome-Based**

| Timeline | Covers |
|----------|--------|
| PATH A | Best case / Optimistic / Upward ⬆️ |
| PATH B | Base case / Modal / Most likely ↔️ |
| PATH C | Worst case / Pessimistic / Downward ⬇️ |

**Configuration B: Action-Based**

| Timeline | Covers |
|----------|--------|
| PATH A | Continue current trajectory |
| PATH B | Modify (pivot, adjust) |
| PATH C | Exit (abandon, cut losses) |

**Configuration C: Reality-Based**

| Timeline | Covers |
|----------|--------|
| PATH A | De Jure (what "should" happen) |
| PATH B | De Facto (what WILL likely happen) |
| PATH C | Black Swan (low-prob high-impact) |

## 17.3 Proper Interconnection Structure

Nodes are NOT linear. They are interconnected:

```
                    [T0: DECISION POINT]
                              │
           ┌──────────────────┼──────────────────┐
           ▼                  ▼                  ▼
        [PATH A]           [PATH B]           [PATH C]
           │                  │                  │
           │◄─────── A affects B's ────────────►│
           │         base rate                   │
           ▼                  ▼                  ▼
      ┌─────────┐       ┌─────────┐        ┌─────────┐
      │ NODE A1 │◄─────►│ NODE B1 │◄──────►│ NODE C1 │
      └────┬────┘       └────┬────┘        └────┬────┘
           │                  │                  │
           └──────────────────┼──────────────────┘
                              ▼
                    ┌─────────────────┐
                    │ SHARED CONSEQ.  │
                    │ (e.g., Capital) │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ FEEDBACK TO T0  │
                    │ (Updates priors)│
                    └─────────────────┘
```

| Interconnection Type | Example |
|---------------------|---------|
| Cross-timeline causal | Choosing A changes the base rate of B working |
| Shared consequence nodes | All 3 paths affect reputation; all 3 affect capital |
| Feedback loops | Outcome at T+1 updates probability estimates at T0 |
| Conditional dependencies | C only becomes viable IF A fails first |
| Mutual exclusion | Choosing A closes off certain branches of C |

## 17.4 Standing Default

**For most life decisions**: 3 timelines, fully interconnected, is the default.

---

## References

- [Protocol 38: Synthetic Deep Think](../decision/_archived/38-synthetic-deep-think.md) — References this protocol

---

## Tagging

#protocol #framework #process #17-three-timeline-got

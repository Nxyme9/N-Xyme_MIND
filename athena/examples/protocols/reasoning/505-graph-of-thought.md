---
created: 2026-03-04
last_updated: 2026-03-04
cluster: 15
---

# Protocol 505: Graph of Thought (Non-Linear Solution Exploration)

> **Status**: ACTIVE  
> **Priority**: ⭐⭐⭐  
> **Principle**: Real problem-solving is not linear (A→B→C). It's a directed acyclic graph with branching, pruning, and merging.

---

## Core Concept

**Chain of Thought (CoT)**: Linear. One path. No backtracking. Fails on complex problems because it commits too early.

**Tree of Thought (ToT)**: Branching. Multiple paths. But evaluates each branch independently — misses cross-pollination.

**Graph of Thought (GoT)**: Branching + Merging + Pruning. Explores multiple paths, allows partial solutions from different branches to combine, and kills dead ends early.

```
         [Problem Definition]
              /    |    \
            /      |      \
         [B₁]    [B₂]    [B₃]     ← BRANCH (diverge)
          |        |     ✗ dead     ← PRUNE  (kill B₃)
         [B₁']   [B₂']             ← DEVELOP (deepen)
           \      /
            \    /
         [MERGE: B₁'+B₂']          ← MERGE  (combine insights)
              |
         [Solution Candidate]
              |
         [STRESS TEST]              ← Validate via Red Team (#8)
              |
         [Final Solution]
```

---

## Execution Protocol

### Phase 1: BRANCH (Diverge)

Generate **minimum 3, maximum 5** independent solution paths from the locked Problem Statement (P504 output).

```
For each branch:
├─ ID:         B₁, B₂, ..., Bₙ
├─ Approach:   [one-sentence description]
├─ Mechanism:  [how it solves the root cause]
├─ Assumption: [what must be true for this to work]
├─ Risk:       [primary failure mode]
└─ Cost:       [time/money/complexity estimate]

Branching Rules:
├─ At least 1 branch must be "conventional" (standard solution)
├─ At least 1 branch must be "contrarian" (inverts a constraint)
├─ At least 1 branch must be "first principles" (builds from scratch)
└─ Branches must be meaningfully different, not parameter variations
```

### Phase 2: PRUNE (Kill Early)

Eliminate branches that fail a **kill criteria check** before investing further development effort.

```
Kill Criteria (any single failure = prune):
├─ Violates a hard constraint from P504 Gate 2
├─ Core assumption is demonstrably false
├─ Cost exceeds 3x the next cheapest viable branch
├─ Requires a dependency that doesn't exist and can't be built in time
└─ Has been tried before and failed for structural (not execution) reasons

Surviving Branches: [list]
Pruned Branches:    [list + reason]

Rule: Never prune below 2 surviving branches. If pruning leaves <2,
      generate new branches before continuing.
```

### Phase 3: DEVELOP (Deepen)

For each surviving branch, develop the solution to **second-order detail** — enough to identify integration points and failure modes, not enough to build a full implementation.

```
For each surviving branch:
├─ Step-by-step mechanism (5-10 steps)
├─ Dependencies (what needs to exist first)
├─ Failure modes (top 3)
├─ Reversibility score [1-5] (1=irreversible, 5=fully reversible)
└─ Partial insights (what's useful even if this branch fails?)
```

### Phase 4: MERGE (Cross-Pollinate)

The key differentiator of GoT. Check if partial solutions from different branches can be combined into a stronger composite solution.

```
Merge Check:
├─ Do any branches solve different sub-problems?
│   → Combine: B₁ solves sub-problem A, B₂ solves sub-problem B
├─ Do any branches share a common insight?
│   → Extract: The shared insight is likely a structural truth
├─ Can the risk mitigation of one branch protect another?
│   → Hedge: Use B₂'s approach as a fallback for B₁'s failure mode
└─ Is there a phased approach? (B₁ first, then B₂ if B₁ validates?)
    → Sequence: Reduces commitment risk

Output: Either a merged solution OR the single strongest branch
        with documented reasons why merging was rejected.
```

### Phase 5: SELECT + VALIDATE

```
Final Solution Selection:
├─ Solution:     [merged or single branch]
├─ Confidence:   [1-10 with justification]
├─ Key Risk:     [single biggest failure mode]
├─ Contingency:  [what to do if it fails — which pruned branch to revive]
└─ Exit Criteria:[measurable signal that this is working / not working]

Validation: Route to Red Team Review (Cluster #8) if Λ > 20.
```

---

## Output Format

```
PROBLEM:  [from P504]
BRANCHES: [B₁, B₂, B₃, ...]
PRUNED:   [Bₙ — reason]
DEVELOPED:[B₁', B₂']
MERGED:   [B₁' ⊕ B₂' or "No merge — B₁' dominates"]
SOLUTION: [final recommendation]
CONTINGENCY: [fallback path]
```

---

## When to Use GoT vs CoT

| Scenario | Use |
|---|---|
| Single clear answer exists | CoT (linear) |
| Multiple viable approaches, unclear winner | **GoT** |
| Time pressure < 5 min | CoT (no time to branch) |
| Irreversible decision | **GoT** (explore before committing) |
| Technical implementation | CoT (sequential by nature) |
| Strategy / architecture / life decisions | **GoT** |

---

## Co-Activation

- **Upstream**: P504 (Problem Framing) provides the locked Problem Statement
- **Downstream**: P506 (GTO Execution Plan) converts the selected solution into an action plan
- **Lateral**: Red Team Review (Cluster #8) validates at Phase 5
- **Cluster**: #15 Problem-Solving Engine

---

## Cross-References

- [Protocol 504: Problem Framing](504-problem-framing.md)
- [Protocol 506: GTO Execution Plan](506-gto-execution-plan.md)
- [Protocol 115: First Principles Deconstruction](../decision/115-first-principles-deconstruction.md)

---

## Tagging

# protocol #reasoning #problem-solving #graph-of-thought #branching #exploration

---
created: 2026-03-04
last_updated: 2026-03-04
cluster: 15
---

# Protocol 506: GTO Execution Plan (Game-Theory Optimal Sequencing)

> **Status**: ACTIVE  
> **Priority**: ⭐⭐⭐  
> **Principle**: The order you execute steps matters as much as the steps themselves. Sequence for maximum optionality; commit irreversibly last.

---

## Core Axiom

A solution is not a plan. A plan is a **sequenced, dependency-aware, risk-ordered set of actions** with explicit kill criteria and contingency paths. GTO execution minimizes regret under uncertainty.

---

## 4-Phase Execution Architecture

### Phase 1: Dependency DAG (Directed Acyclic Graph)

Map every action as a node. Draw edges for "must happen before" relationships.

```
Action Mapping:
├─ A₁: [action] → depends on: [nothing / A₀]
├─ A₂: [action] → depends on: [A₁]
├─ A₃: [action] → depends on: [A₁]  (parallel with A₂)
├─ A₄: [action] → depends on: [A₂, A₃]  (convergence point)
└─ A₅: [action] → depends on: [A₄]

Parallelism Detection:
├─ Independent actions (no shared dependencies) → Execute in parallel
├─ Convergence points → These are your bottlenecks. Staff/resource them.
└─ Serial chains → These set your minimum timeline. Cannot be compressed.

Output: DAG diagram + Critical Path (longest serial chain = minimum time)
```

### Phase 2: Reversibility Scoring

Score every action on a 1-5 reversibility scale. **Execute reversible actions first, irreversible actions last.**

```
Reversibility Scale:
├─ 5: Fully reversible, zero cost (e.g., writing a doc, branching code)
├─ 4: Reversible with minor cost (e.g., refactoring, repricing)
├─ 3: Reversible with significant cost (e.g., hire/fire, contract renegotiation)
├─ 2: Partially irreversible (e.g., public announcement, shipping a product)
└─ 1: Fully irreversible (e.g., legal filing, burning a relationship, spending capital)

Sequencing Rule:
├─ Score 5-4: Execute FIRST (gather information, low commitment)
├─ Score 3:   Execute MIDDLE (after validation from early actions)
├─ Score 2-1: Execute LAST (only after maximum information gathered)
└─ NEVER execute a Score 1 action without explicit validation gate

Exception: If a Score 1 action is on the critical path and has a hard deadline,
           it must be executed — but with maximum prior validation.
```

### Phase 3: Kill Criteria & Contingency

For each major action, define the signal that means "this isn't working — abort."

```
For each action on the critical path:
├─ Success Signal:  [measurable indicator it's working]
├─ Kill Signal:     [measurable indicator it's failing]
├─ Kill Threshold:  [specific number/date/event that triggers abort]
├─ Contingency:     [what to do if killed — which branch from P505 to revive]
└─ Sunk Cost:       [what's lost if killed at this point]

Rule: The kill threshold must be defined BEFORE execution begins.
      Defining it during execution invites rationalisation bias.

GTO Principle: A plan without kill criteria is a hope, not a strategy.
```

### Phase 4: Execution Schedule

Combine the DAG + Reversibility + Kill Criteria into a sequenced timeline.

```
Execution Schedule (Template):

Phase 1 — Reconnaissance (Reversibility 5-4):
├─ A₁: [action] — by [date] — success: [signal] — kill: [signal]
├─ A₃: [action] — by [date] — success: [signal] — kill: [signal]
└─ Gate 1: Review results. Continue / Pivot / Abort.

Phase 2 — Commitment (Reversibility 3):
├─ A₂: [action] — by [date] — success: [signal] — kill: [signal]
├─ A₄: [action] — by [date] — success: [signal] — kill: [signal]
└─ Gate 2: Review results. Continue / Pivot / Abort.

Phase 3 — Irreversible Execution (Reversibility 2-1):
├─ A₅: [action] — by [date] — success: [signal] — kill: [signal]
└─ Post-Execution Review: Compare actual vs predicted outcomes.

Total Timeline: [X days/weeks]
Critical Path:  [A₁ → A₂ → A₄ → A₅]
Parallel Track: [A₃ runs alongside A₂]
Resource Bottleneck: [identify]
```

---

## GTO Principles (Immutable)

| # | Principle | Rationale |
|---|---|---|
| 1 | **Reversible first, irreversible last** | Maximizes optionality; gathers info before committing |
| 2 | **Define kill criteria before starting** | Prevents sunk cost fallacy and rationalisation bias |
| 3 | **Parallel when possible, serial when necessary** | Minimizes timeline without creating dependency risk |
| 4 | **Gate reviews between phases** | Prevents cascading commitment to a failing plan |
| 5 | **Contingency for every critical-path action** | No single point of failure without a fallback |
| 6 | **Measure outcomes, not activity** | "We did 12 tasks" means nothing. "We hit 3/4 success signals" means everything |

---

## Output Format

```
SOLUTION:      [from P505]
DAG:           [dependency graph]
CRITICAL PATH: [longest serial chain]
TIMELINE:      [total estimated duration]

PHASE 1 (Recon):
  [actions, dates, signals]
  → GATE 1

PHASE 2 (Commit):
  [actions, dates, signals]
  → GATE 2

PHASE 3 (Execute):
  [actions, dates, signals]
  → POST-MORTEM

KILL CRITERIA:  [per critical action]
CONTINGENCY:    [fallback paths]
```

---

## Co-Activation

- **Upstream**: P505 (Graph of Thought) provides the selected solution
- **Downstream**: Direct execution / Build Lifecycle (Cluster #13) for implementation
- **Cluster**: #15 Problem-Solving Engine

---

## Cross-References

- [Protocol 504: Problem Framing](504-problem-framing.md)
- [Protocol 505: Graph of Thought](505-graph-of-thought.md)
- [Protocol 115: First Principles Deconstruction](../decision/115-first-principles-deconstruction.md)
- [Red Team Review](../../skills/research/synthetic-parallel-reasoning/SKILL.md)

---

## Tagging

# protocol #reasoning #problem-solving #execution #gto #sequencing #planning

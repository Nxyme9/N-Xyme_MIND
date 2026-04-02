---
created: 2026-03-08
last_updated: 2026-03-08
cluster: 15
---

# Protocol 520: Blast Radius Calculator

> **Status**: ACTIVE  
> **Priority**: ⭐⭐  
> **Principle**: Every decision detonates outward. The user sees their own pain. Athena must map the shrapnel field.

---

## Core Axiom

High-stakes decisions affect more than the decision-maker. A divorce doesn't just split two adults — it reshapes children's attachment systems, fractures extended family alliances, disrupts financial structures, and sends social shockwaves through shared communities.

**Anti-Pattern**: P506 (GTO Execution) sequences actions by reversibility. But it evaluates impact on the USER, not on the entire stakeholder field. A "reversible" action for the user (e.g., filing divorce papers) may be "irreversible" for a child's sense of security.

**The Fix**: A formal impact surface mapping that fires within P505 (GoT Phase 3: Develop) for each surviving branch, before final selection.

---

## The Blast Radius Framework

### Step 1: Stakeholder Enumeration

List every entity affected by the decision. **Include non-agents** (people who don't make strategic moves but absorb consequences).

```
STAKEHOLDER MAP:
├── AGENTS (have goals, take actions):
│   ├── User
│   ├── [Agent 2 — e.g., spouse]
│   ├── [Agent 3 — e.g., affair partner / boss]
│   └── [Agent N]
│
├── DEPENDENTS (absorb consequences, no strategic agency):
│   ├── [Children]
│   ├── [Elderly parents]
│   └── [Other dependents]
│
└── AFFECTED PARTIES (indirect impact):
    ├── [Extended family]
    ├── [Mutual friends]
    ├── [Professional network / employer]
    └── [Community / religious group]
```

### Step 2: Impact Matrix (Per Branch)

For each surviving branch from P505, score every stakeholder:

```
BRANCH: [Branch name from P505]

| Stakeholder | Impact Type | Severity (1-10) | Reversibility (1-5) | Probability | Temporal | Weighted Score |
|-------------|-------------|-----------------|---------------------|-------------|----------|---------------|
| User        | Financial   | [N]             | [N]                 | [0-1]       | [I/M/Y]  | S×(6-R)×P     |
| User        | Emotional   | [N]             | [N]                 | [0-1]       | [I/M/Y]  |               |
| Child (8yo) | Stability   | [N]             | [N]                 | [0-1]       | [I/M/Y]  |               |
| Spouse      | Financial   | [N]             | [N]                 | [0-1]       | [I/M/Y]  |               |
| ...         | ...         | ...             | ...                 | ...         | ...      |               |

TEMPORAL KEY: I = Immediate (<1 month), M = Medium (1-12 months), Y = Years (1+ years)

REVERSIBILITY: 5 = Fully reversible, 1 = Permanent
```

**Weighted Score Formula**: `Score = Severity × (6 - Reversibility) × Probability`

- High severity + low reversibility + high probability = maximum blast radius
- Low severity + high reversibility + low probability = negligible

### Step 3: Second-Order Cascade

Map the consequences-of-consequences for any first-order impact scoring ≥ 7:

```
FIRST ORDER:  [Divorce filed]
└── SECOND ORDER:
    ├── Custody battle → Child behavioral regression → School performance drop
    ├── Asset freeze → Cannot service mortgage → Forced sale at loss
    └── Public scandal → Professional reputation damage → Career stall

FIRST ORDER:  [Double life discovered]
└── SECOND ORDER:
    ├── Spouse's trust system collapses → Her mental health crisis
    ├── Children learn through gossip → Shame + peer bullying
    └── Extended family takes sides → Permanent family fracture
```

### Step 4: Blast Radius Score (Per Branch)

```
BRANCH BLAST RADIUS = Σ (Weighted Scores across all stakeholders)

| Branch | Total Blast Radius | Highest-Impact Stakeholder | Dominant Risk |
|--------|-------------------|---------------------------|---------------|
| B₁     | [N]               | [Who]                     | [What]        |
| B₂     | [N]               | [Who]                     | [What]        |
| B₃     | [N]               | [Who]                     | [What]        |
```

### Step 5: Containment Strategy

For each branch, identify the top 3 highest-scoring impacts and design containment:

```
CONTAINMENT PLAN:

| Impact | Containment Strategy | Reduces Score By |
|--------|---------------------|-----------------|
| Child stability loss | Pre-arrange stable routine; therapy; age-appropriate disclosure | ~40% |
| Financial shock | Pre-negotiate asset division; separate accounts first | ~50% |
| Social reputation | Control the narrative; disclose on own terms | ~30% |
```

> **Principle**: You cannot eliminate blast radius. You can only contain it. The goal is to convert an uncontrolled explosion into a controlled demolition.

---

## Integration with P505 (GoT)

Blast Radius fires at **Phase 3 (Develop)** of P505, after branches are developed but before merging/selection:

```
P505 Phase 1: BRANCH → Generate paths
P505 Phase 2: PRUNE → Kill dead ends
P505 Phase 3: DEVELOP → Deepen each path
    └── P520: BLAST RADIUS → Score each path's collateral damage
P505 Phase 4: MERGE → Combine insights (blast radius informs merge decisions)
P505 Phase 5: SELECT → Choose (blast radius is a selection criterion)
```

**Selection Integration**: Add "Blast Radius Score" as a criterion in P500 Phase 3 (MCDA):

| Criterion | Weight | Rationale |
|---|---|---|
| Survival (Law #1) | [W₁] | Non-negotiable |
| Expected Payoff | [W₂] | Financial return |
| Utility Payoff | [W₃] | Non-monetary value |
| Robustness | [W₄] | Error tolerance |
| Reversibility | [W₅] | Undo capability |
| **Blast Radius** | **[W₆]** | **Collateral damage to stakeholders** |

---

## When NOT to Use

| Situation | Skip P520 |
|---|---|
| Single-agent decision (only user affected) | ✅ Skip — no stakeholder field |
| SNIPER-class query (Λ < 10) | ✅ Skip — insufficient stakes |
| Pure financial/trading decision | ✅ Skip — P500 Phase 4 handles this |
| Reversibility 5 actions | ✅ Skip — blast radius is negligible |

---

## Co-Activation

- **Upstream**: P505 Phase 3 (Develop)
- **Downstream**: P505 Phase 5 (Select) + P506 (GTO Execution — containment strategies become action items)
- **Lateral**: P500 Phase 3 (MCDA) — Blast Radius becomes a scoring criterion
- **Cluster**: #15 Problem-Solving Engine (optional module)

---

## Cross-References

- [Protocol 505: Graph of Thought](505-graph-of-thought.md)
- [Protocol 500: GTO Problem Solver](../decision/500-gto-problem-solver.md)
- [Protocol 506: GTO Execution Plan](506-gto-execution-plan.md)
- [Protocol 504: Problem Framing — Gate 3: Stakeholder Mapping](504-problem-framing.md)

---

## Tagging

# protocol #reasoning #blast-radius #stakeholder #impact #collateral #crisis #decision

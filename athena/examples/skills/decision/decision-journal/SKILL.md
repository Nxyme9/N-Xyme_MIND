---
name: decision-journal
description: "Unified decision lifecycle: Pre-decision logging, post-decision review, failure classification, and calibration tracking. Absorbs: post-mortem-engine."
argument-hint: "log decision | review decisions | calibration check | post mortem | what went wrong | failure analysis"
allowed-tools:
  - Write
  - Read
auto-invoke: false
model: default
---

# Decision Engine (Journal + Post-Mortem)

> **Absorbs**: `post-mortem-engine`

Complete decision lifecycle in one skill: record decisions BEFORE outcomes are known, review them AFTER, classify failures objectively, and track calibration over time.

## Triggers

"I've decided to", "logging a decision", "was that a good decision", "calibration", "what went wrong", "post mortem", "failure analysis", "AAR", "I screwed up"

---

## Part 1: Pre-Decision Entry (BEFORE outcome)

```markdown
## Decision Entry: [YYYY-MM-DD HH:MM]

### The Decision
[What am I deciding to do?]

### The Alternatives
1. [Alternative A and why I rejected it]
2. [Alternative B and why I rejected it]

### My Confidence
[X]% confident this is the right call.

### Key Assumptions (numbered)
1. [Assumption 1]
2. [Assumption 2]

### What Would Change My Mind
[Specific observable evidence that would make me reverse]

### Expected Outcome
- Best case: [description] (probability: X%)
- Most likely: [description] (probability: X%)
- Worst case: [description] (probability: X%)

### Decision Class
- [ ] Reversible (Type 2 — decide fast, adjust later)
- [ ] Irreversible (Type 1 — decide carefully, no undo)
```

---

## Part 2: Post-Decision Review (30-90 days later)

```markdown
## Review: [Original Decision Date]

### Actual Outcome
[What actually happened?]

### Assumptions Audit
1. [Assumption 1]: [Correct / Wrong / Partially correct]
2. [Assumption 2]: [Correct / Wrong / Partially correct]

### Calibration
- Stated confidence: X%
- Would I make the same decision with same info? [Yes / No]
- Outcome due to: [good decision / luck / bad decision / bad luck]
```

---

## Part 3: Post-Mortem (When Things Go Wrong)

### Phase 1: Just the Facts (No Interpretation)

Timeline of observable events only. No opinions, no "I should have."

### Phase 2: Root Cause (The 5 Whys)

```
1. Why did [outcome] happen? → Because [cause 1]
2. Why? → Because [cause 2]
3. Why? → Because [cause 3]
4. Why? → Because [cause 4]
5. Why? → Because [ROOT CAUSE]
```

### Phase 3: Classification

| Category | Question |
|:---------|:---------|
| **Process Failure** | Followed system, it failed → Update system |
| **Execution Failure** | Deviated from system → Discipline issue |
| **Information Failure** | Critical info unavailable → Update model, not system |
| **Luck Failure** | Within expected failure rate → Change NOTHING |

> **Critical Rule**: Luck failures do NOT get process changes. At 60% WR, 40% of trades WILL fail. Changing your process after a luck failure is the #1 way to destroy a working edge.

### Output

```
Post-Mortem Report: [Event]
─────────────────────────────
Root Cause: [One sentence]
Classification: [PROCESS / EXECUTION / INFORMATION / LUCK]
Required Changes: [Specific actions or "NONE — within expected parameters"]
```

---

## Calibration Tracking

Over 20+ reviewed decisions:

| Stated Confidence | Actual Correct % | Calibration |
|:--|:--|:--|
| 90% | XX% | [Over / Under / Well-calibrated] |
| 70% | XX% | [Over / Under / Well-calibrated] |
| 50% | XX% | [Over / Under / Well-calibrated] |

**Storage**: `.context/memories/decision_journal/`

## Integration

- Triggers `trading-risk-gate` on Type 1 (irreversible) decisions
- Feeds into `trade-journal-analyzer` for trading decisions
- Triggers `circuit-breaker` if process failures are recurring

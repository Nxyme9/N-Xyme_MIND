---
created: 2026-03-04
last_updated: 2026-03-04
---

# Protocol 508: Intent Classifier (The Nervous System)

> **Status**: ACTIVE  
> **Priority**: ⭐⭐⭐⭐  
> **Principle**: The nervous system doesn't ask the stomach what to do. It classifies the signal and dispatches to the correct organ system. Athena does the same.

---

## Core Function

The Intent Classifier is the top-down dispatch mechanism. It reads a user query, classifies the **human need archetype** (not the keyword), and routes to the correct Cognitive System.

**Why this matters:** Keyword-based cluster routing (bottom-up) is reactive and fragile. A query like *"Should I annul my marriage?"* would trigger Strategic Reasoning (#9) on the keyword "should I" — but it needs the *entire Life Decision System* (5 clusters, sequenced). Intent Classification solves this by routing at the System level first, then cascading down.

---

## Classification Framework

### Step 1: Detect the Human Need Archetype

Every user query maps to one of 8 need archetypes. Classify by **intent**, not **keywords**.

```text
ARCHETYPE DETECTION:

Q1: Is there an immediate threat of ruin (financial, reputational, legal, physical, psychological)?
    → YES: SURVIVAL SYSTEM 🛡️ (Priority override — always fires first)
    → NO:  Continue to Q2

Q2: Is this an irreversible personal/life decision?
    → YES: LIFE DECISION SYSTEM 🫀
    → NO:  Continue to Q3

Q3: Does this involve deploying capital or managing financial risk?
    → YES: TRADING SYSTEM 📈
    → NO:  Continue to Q4

Q4: Is this about navigating interpersonal dynamics, relationships, or conflict?
    → YES: SOCIAL SYSTEM 🤝
    → NO:  Continue to Q5

Q5: Is this a concrete build/create/ship task?
    → YES: EXECUTION SYSTEM ⚙️
    → NO:  Continue to Q6

Q6: Is this about growth, distribution, marketing, or audience acquisition?
    → YES: GROWTH SYSTEM 📣
    → NO:  Continue to Q7

Q7: Is this about understanding, learning, or synthesizing knowledge?
    → YES: LEARNING SYSTEM 📖
           Sub-classify: Is the intent DIVERGENT (generate possibilities, brainstorm,
           ideate, explore options) or CONVERGENT (understand, explain, analyze)?
           → DIVERGENT: Learning System in IDEATION mode (widen before narrowing)
           → CONVERGENT: Learning System in ANALYSIS mode (default)
    → NO:  Continue to Q8

Q8: Is this about system maintenance, health checks, or routine upkeep?
    → YES: MAINTENANCE SYSTEM 🔄
    → NO:  SINGLE-CLUSTER routing (default to keyword-based cluster matching)
```

### Step 2: Confirm or Override

```text
CONFIDENCE CHECK:

After archetype detection, verify:
├─ Does the query CLEARLY map to ONE archetype? → Dispatch immediately
├─ Does the query span MULTIPLE archetypes?     → Route to dominant archetype,
│                                                  flag secondary for downstream handoff
└─ Is the query too vague to classify?          → Default to Problem-Solving (#15) standalone
                                                  P504 will clarify the problem, THEN re-classify
```

---

## Signal Detection Patterns

### Survival System 🛡️ (Always Priority 1)

```text
HIGH-CONFIDENCE SIGNALS:
├─ "I'm going broke / I lost everything / account blown"
├─ "Emergency / urgent / crisis / panic"
├─ "System is down / everything is broken"
├─ Financial ruin indicators (margin call, negative equity, zero runway)
├─ Emotional ruin indicators (suicidal ideation, total despair, crisis language)
└─ Operational ruin indicators (legal threat, data breach, public exposure)

ESCALATION TRIGGER:
Any cluster detecting >5% ruin probability → AUTO-ESCALATE to Survival System
regardless of current active system.
```

### Life Decision System 🫀

```text
HIGH-CONFIDENCE SIGNALS:
├─ "Should I [irreversible action]?" (quit, divorce, terminate, move countries, drop out)
├─ Relationship decisions (marriage, breakup, children, family conflict)
├─ Career pivots (quit job, change industry, start business)
├─ Identity decisions (come out, confront someone, set permanent boundary)
├─ Health decisions (surgery, treatment choice, pregnancy)
└─ Legal/contractual commitments (sign contract, file lawsuit, agree to terms)

KEY DISCRIMINATOR:
If the action is REVERSIBLE → Execution System, not Life Decision.
If the action is IRREVERSIBLE or HIGH-COST-TO-REVERSE → Life Decision System.
```

### Trading System 📈

```text
HIGH-CONFIDENCE SIGNALS:
├─ "Should I take this trade / enter this position?"
├─ "How much should I size / risk?"
├─ "Review my P&L / what went wrong with this trade?"
├─ Asset class references (forex, crypto, stocks, options, futures)
├─ Trading terminology (stop-loss, take-profit, Kelly, drawdown, position)
└─ Gambling/betting contexts (poker, blackjack, sports betting — same risk math)
```

### Execution System ⚙️

```text
HIGH-CONFIDENCE SIGNALS:
├─ "Build / create / implement / code / ship / develop / refactor"
├─ "Execute the assignment / finish the project / deploy"
├─ Specific deliverable references (landing page, API, report, presentation)
├─ Technical implementation language (database, frontend, backend, API, schema)
└─ Workflow execution (step-by-step, SOP, pipeline)

KEY DISCRIMINATOR:
Clear, concrete deliverable = Execution System.
Vague "I need to do something" = Problem-Solving (#15) first, then re-classify.
```

### Growth System 📣

```text
HIGH-CONFIDENCE SIGNALS:
├─ "Launch / grow / market / distribute / promote / SEO / brand"
├─ "How do I get more users / customers / traffic / leads?"
├─ Marketing channel references (Reddit, Google Ads, Meta, SEO, content)
├─ Competitive analysis, positioning, GTM strategy
└─ Audience building, community, distribution
```

### Social System 🤝

```text
HIGH-CONFIDENCE SIGNALS:
├─ "How do I handle this person / situation?"
├─ "My [relationship] is [conflict]"
├─ Interpersonal conflict (co-worker, partner, friend, family, client)
├─ Communication strategy ("what should I say?", "how do I respond?")
├─ Boundary setting, confrontation planning
└─ Power dynamics, status negotiation, social positioning

KEY DISCRIMINATOR:
If the relationship action is IRREVERSIBLE (divorce, disown, fire) → Life Decision System.
If navigating an ongoing dynamic → Social System.
```

### Learning System 📖

```text
HIGH-CONFIDENCE SIGNALS:
├─ "Teach me / explain / what is / how does X work?"
├─ "What's the math behind / theory of / science of?"
├─ Conceptual exploration (no deliverable, no decision, pure understanding)
├─ "Analyze this concept / break this down"
└─ Cross-domain synthesis ("how does X relate to Y?")

IDEATION MODE SIGNALS (DIVERGENT):
├─ "What business should I start?" / "Give me 10 ways to..."
├─ "Brainstorm approaches to..." / "What if we did X differently?"
├─ "What are my options?" / "Explore possibilities for..."
└─ Open-ended generation requests (no single correct answer)

KEY DISCRIMINATOR:
If the user wants to UNDERSTAND something → Learning System (CONVERGENT).
If the user wants to GENERATE possibilities → Learning System (DIVERGENT/IDEATION).
If the user wants to DO something with the knowledge → Execution or Life Decision.

IDEATION MODE BEHAVIOR:
Phase 1 (Research) stays the same. Phase 2 (Reason) generates breadth BEFORE
converging. Phase 3 (Frame/P504) is DEFERRED until sufficient options exist.
Phase 4 (QA) stress-tests the option set, not a single answer.
```

### Maintenance System 🔄

```text
HIGH-CONFIDENCE SIGNALS:
├─ "/diagnose", "/audit", "/end", "/check", "/save"
├─ "Run health check / verify system / compact context"
├─ Session management (close, archive, checkpoint)
├─ Repository maintenance (sync, push, clean up)
└─ Routine operational commands (no crisis, no build)

KEY DISCRIMINATOR:
If there's a crisis → Survival System, not Maintenance.
If it's routine upkeep → Maintenance System.
```

---

## Dispatch Protocol

```text
DISPATCH SEQUENCE:

1. CLASSIFY: Run archetype detection (Q1-Q8)
2. CONFIRM:  Confidence check (single vs. multi vs. vague)
3. ANNOUNCE: Λ-based announcement rules:
             - Λ < 10 (SNIPER):   Silent. No announcement. No system classification.
             - Λ 10-30 (STANDARD): Silent unless user explicitly asks.
             - Λ > 30 (ULTRA):     Announce system classification.
             Default is STEALTH — just become smarter. Do not narrate routing.
4. SEQUENCE: Fire clusters in the prescribed order from P507
5. GATE:     After each phase, implicit go/no-go before next phase
6. HANDOFF:  If cross-system component detected, re-classify that component

SILENT MODE:
For SNIPER-level queries (Λ < 10), skip system-level classification entirely.
Route directly to single-cluster keyword matching.
System-level classification activates only for STANDARD (Λ 10-30) and ULTRA (Λ > 30).
```

---

## Re-Classification Triggers

During execution, a system may need to hand off to a different system:

```text
HANDOFF TRIGGERS:
├─ Life Decision + financial component → Trading System (sub-problem)
├─ Execution + repeated failure → Survival System (circuit breaker)
├─ Trading + emotional language → Survival → Social → Inner Work
├─ Growth + no product-market fit → Life Decision (pivot)
├─ Social + irreversible action → Life Decision System
├─ Learning + actionable insight → Execution System (implement it)
├─ Maintenance + critical failure → Survival System (auto-escalate)
└─ Any system + ruin signal → IMMEDIATE override → Survival System

PROTOCOL:
1. Current system PAUSES (does not terminate)
2. P508 re-classifies the sub-problem
3. Target system handles the sub-problem
4. Control returns to original system with new context
```

---

## Integration Points

| Component | How P508 Integrates |
|---|---|
| `/start` Phase 2.5 | Intent Classification runs BEFORE cluster keyword matching |
| `CLUSTER_INDEX.md` | Systems section sits ABOVE cluster section (higher abstraction) |
| Law #6 (Λ Score) | Λ < 10 bypasses system classification; Λ ≥ 10 triggers it |
| P504 Problem Framing | Default fallback when classification is ambiguous |
| Survival System | Has interrupt privilege — can pre-empt any active system |

---

## Cross-References

- [Protocol 507: Cognitive Systems Architecture](507-cognitive-systems.md)
- [Protocol 503: Cognitive Clusters](503-cognitive-clusters.md)
- CLUSTER_INDEX.md (see your workspace's `.agent/CLUSTER_INDEX.md`)

---

## Tagging

# protocol #architecture #intent-classifier #dispatch #nervous-system #routing

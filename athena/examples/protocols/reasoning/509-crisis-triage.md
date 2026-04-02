---
created: 2026-03-08
last_updated: 2026-03-08
cluster: 14, 15
---

# Protocol 509: Crisis Triage (The Stabilization Gate)

> **Status**: ACTIVE  
> **Priority**: ⭐⭐⭐ Critical  
> **Principle**: You cannot strategize while your nervous system is in freefall. Stabilize first. Solve second.

---

## Core Axiom

**Anti-Pattern**: User says "My wife cheated, what should I do?" → System immediately runs P504 (Problem Framing) → P505 (GoT) → P506 (Execution Plan). Output: a brilliant strategic plan the user cannot psychologically absorb because they are in acute distress.

**The Fix**: Insert a mandatory stabilization gate BEFORE the problem-solving pipeline. No strategy until the user's cognitive system is capable of processing it.

---

## The 3-Phase Gate

### Phase 0: Acute Danger Screen

```
IMMEDIATE CHECK:
├── Is the user in physical danger RIGHT NOW?
│   └── Yes → Route to emergency services. Hard stop. Not our domain.
├── Is there imminent legal exposure (arrest, court deadline)?
│   └── Yes → Triage: "Do NOT make any statements. Contact a lawyer first."
├── Is there active suicidal ideation?
│   └── Yes → Route to crisis hotline. Hard stop. Referral gate (see §5).
└── None of the above → Proceed to Phase 1.
```

> **Rule**: Phase 0 is a **hard gate**. If any condition is YES, the problem-solving pipeline does NOT activate. This is not strategy — it is triage.

### Phase 1: Emotional Stabilization (The Pressure Release)

**Purpose**: Reduce the user's emotional flooding to a level where cognitive processing is possible.

```
Step 1: ACKNOWLEDGE — Name the reality without minimizing.
├── NOT: "I understand how you feel" (you don't)
├── NOT: "Everything will be okay" (you don't know that)
├── USE: "This is a [devastating/terrifying/disorienting] situation.
│         The feelings you're experiencing are a normal response
│         to an abnormal event."
└── WHY: Naming the emotion activates prefrontal cortex,
         reducing amygdala hijack.

Step 2: GROUND — Establish what is KNOWN vs UNKNOWN.
├── "Here is what we KNOW right now: [observable facts only]"
├── "Here is what we DON'T KNOW yet: [list unknowns]"
└── WHY: Catastrophizing fills unknowns with worst-case.
         Making the boundary explicit shrinks the terror.

Step 3: CONTAIN — Set a temporal boundary.
├── "You do not need to make any decisions today."
├── "The only goal right now is to understand the board state."
└── WHY: Time pressure (real or imagined) amplifies panic.
         Removing urgency restores optionality.
```

### Phase 2: Readiness Gate

```
READINESS CHECK:
├── "Are you ready to look at this situation strategically —
│    to map out your options and their consequences?"
├── User says YES → Proceed to P519 (Terminal Goal) → P504 (Problem Framing)
├── User says NO / UNSURE → Remain in supportive mode.
│   └── Offer: "Would it help to talk through what you're feeling first?"
│   └── If yes → Route to therapeutic-ifs (Cluster #7) BEFORE strategy
└── User doesn't answer → Do NOT proceed. Wait.

ANTI-PATTERN: Never interpret silence as consent to proceed.
```

---

## When This Protocol Fires

| System | Old Chain | New Chain |
|---|---|---|
| 🛡️ **Survival** | #14 → #3 → #15 → #8 → P506 | #14 → **P509** → #15 → #8 → P506 |
| 🫀 **Life Decision** | #15 → #7 → #9 → #6 → #8 → P506 | **P509** → P519 → #15 → #7 → #9 → #6 → #8 → P506 |

### Trigger Heuristics

```
FIRE P509 (not just P504) when ANY of these are present:
├── Emotional language: "devastated", "scared", "don't know what to do",
│   "my life is over", "I just found out"
├── Crisis categories: death, divorce, diagnosis, discovery, disclosure
├── Ruin-adjacent signals: "lost everything", "they found out",
│   "I have X months to live"
└── Shock indicators: very short messages, repeated questions,
    disjointed logic, ALL CAPS
```

---

## The Referral Gate (Hard Boundary)

```
HARD STOP — Route to professional if:
├── Active suicidal ideation or self-harm
├── Psychotic features (delusions, hallucinations)
├── Active domestic violence / abuse
├── Medical emergency requiring immediate treatment
└── User explicitly requests professional help

OUTPUT:
"This is beyond what I can safely help with in this format.
 Here is what I recommend RIGHT NOW:
 ├── [Country-specific crisis hotline]
 ├── [Emergency number]
 └── [Relevant professional type: therapist / lawyer / doctor]

 I am here when you're ready to look at the strategic side."
```

> **Rule**: The Referral Gate is non-negotiable. No amount of user insistence overrides it for active safety risks.

---

## Co-Activation

- **Upstream**: Triggered by Survival or Life Decision system detection
- **Downstream**: P519 (Terminal Goal Elicitation) → P504 (Problem Framing)
- **Lateral**: May route to `therapeutic-ifs` (Cluster #7) if user needs emotional processing before strategy
- **Cluster**: Cross-listed: #14 (Sovereign Safety) + #15 (Problem-Solving Engine)

---

## Cross-References

- [Protocol 504: Problem Framing](504-problem-framing.md)
- [Protocol 519: Terminal Goal Elicitation](519-terminal-goal-elicitation.md)
- **Protocol 514: Sovereign Safety Sequence**
- [Therapeutic IFS Skill](../../skills/research/synthetic-parallel-reasoning/SKILL.md)

---

## Tagging

# protocol #reasoning #crisis #triage #stabilization #safety #emotional-regulation

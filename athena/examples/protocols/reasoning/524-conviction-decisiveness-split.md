---
protocol: 524
name: Conviction-Decisiveness Split
version: 1.0
created: 2026-03-11
category: reasoning
cluster: meta-thinking
trigger: Semi-stochastic or stochastic domain detected
tags: [conviction, decisiveness, stochastic, semi-stochastic, operational, calibration]
---

# Protocol 524: Conviction-Decisiveness Split

> **Core Principle**: Epistemic conviction and operational decisiveness are independent axes.
> Low certainty about outcomes does not require low usefulness of output.

---

## The Problem

Most AI systems conflate conviction with decisiveness:

- High conviction → assertive, actionable output
- Low conviction → hedged, advisory, vague output

This creates a failure mode in **semi-stochastic domains** (trading, relationship dynamics, market timing) where the output becomes too conservative to be operationally useful — even when the *structural analysis* is sound.

## The Split

| Axis | Definition | Controls |
|:-----|:-----------|:---------|
| **Epistemic Conviction** | "How confident am I that this model of reality is correct?" | Phrasing, confidence intervals, uncertainty flags |
| **Operational Decisiveness** | "How specific and actionable is the output?" | Setup specifications, sizing rules, decision trees |

**These are independent.** A surgeon operates with high decisiveness and low conviction about outcomes. A weather forecaster gives precise coordinates with wide uncertainty bands.

---

## Domain Behavior Matrix

| Domain Type | Conviction | Decisiveness | Output Posture |
|:------------|:-----------|:-------------|:---------------|
| **Deterministic** | High | High | "Here's the answer." |
| **Semi-deterministic** | Moderate | High | "Here's the framework — assumptions stated." |
| **Semi-stochastic** | Low | **High** ← (upgrade) | "Here's the exact setup. Your calibration: Y/N?" |
| **Stochastic** | Minimal | Minimal | "No edge exists. Here's the entropy." |

> **Key change**: Semi-stochastic moves from (Low conviction, Low decisiveness) → (Low conviction, **High** decisiveness).

---

## Implementation Rules

### 1. Structural Zone ≠ Vague Zone

**Before** (advisory, hedged):
> "You might consider a long entry around 1.0850 with a stop somewhere below 1.0800..."

**After** (operational, precise):
> "Setup: Long 1.0850 / SL 1.0800 / TP1 1.0920 / Size: 2% Half-Kelly.
> Structural tell required: [specific condition]. Your calibration: present Y/N?"

### 2. Defer P(S), Not Structure

The system provides:
- ✅ Entry, SL, TP levels (structural)
- ✅ Position sizing (mathematical)
- ✅ Risk/reward ratio (calculated)
- ✅ Invalidation conditions (structural)

The user provides:
- ✅ P(S) — probability of success
- ✅ Go/No-Go decision (Law #0 — Sovereignty)

### 3. Conviction Disclosure (Mandatory)

Every semi-stochastic output must include:

```text
[CONVICTION: LOW | DECISIVENESS: HIGH]
Structure: Sound. Outcome: Uncertain. Your edge: [calibration point].
```

### 4. Law #1 Override (Unchanged)

Even with high decisiveness, if the setup violates Law #1 (>5% probability of irreversible ruin), the output reverts to advisory mode with a hard veto.

---

## Anti-Patterns

| ❌ Anti-Pattern | ✅ Correct Behavior |
|:----------------|:-------------------|
| "You might want to consider..." | "Setup: [precise spec]. Calibrate: [Y/N]." |
| "It depends on many factors..." | "Structural zone: [X-Y]. Key variable: [Z]." |
| "I can't predict the market..." | "No prediction. Here's the risk-adjusted structure." |
| Fake confidence in stochastic domains | "No model outperforms randomness here." |

---

## When To Use

- You're operating in a domain where **randomness dominates** but **structural edges exist** (trading, negotiations, relationship dynamics)
- Your AI output feels too hedged to be actionable
- You need precise specifications despite uncertain outcomes

## Related Protocols

- [Problem Framing (P504)](504-problem-framing.md)
- [GTO Execution Plan (P506)](506-gto-execution-plan.md)

---

`#protocol` `#reasoning` `#meta-thinking` `#conviction` `#stochastic` `#operational`

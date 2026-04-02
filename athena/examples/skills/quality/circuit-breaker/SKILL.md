---
name: circuit-breaker
description: Mandatory systemic pause when cumulative red flags exceed threshold. Forces disengagement across Trading, Spending, Relationships, Work, and Energy domains.
argument-hint: "stop | pause | circuit breaker | drawdown | losing streak"
auto-invoke: true
model: default
---

# Circuit Breaker (Systemic Pause)

When cumulative damage exceeds threshold, the system forces a pause — regardless of the operator's desire to continue. Individual red flags are survivable; cumulative damage is not.

## Triggers

"losing streak", "can't stop", "one more try", "sunk cost", "drawdown", "burned out", "3 in a row", "keep going"

## Core Mechanics

1. Track cumulative red flags per domain.
2. Trigger forced protocol when threshold is reached.
3. Execute: STOP → PAUSE (24h min) → AAR → DIAGNOSE → VERDICT.

## Threshold Table

| Domain | Red Flag Unit | Trigger |
|--------|--------------|---------|
| Trading | 1R loss | 5R cumulative |
| Spending | Budget breach | 3 in one month |
| Relationships | Unreciprocated bid | 3 consecutive |
| Work | Missed deadline | 2 in one sprint |
| Energy | Sleep debt night | 3 consecutive |

## Post-Breaker Protocol

- Statistical noise → Resume at reduced intensity
- Systemic failure → Major adjustment before resuming
- Edge degradation → Exit domain
- 2 consecutive triggers → Full stop, external review required

## Reference Paths

- `.agent/skills/protocols/safety/48-circuit-breaker-systemic.md`

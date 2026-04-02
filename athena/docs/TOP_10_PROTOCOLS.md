# Top 10 Protocols (MCDA Ranked)

> **Last Updated**: 18 March 2026  
> **Methodology**: Weighted MCDA + Pairwise Validation  
> **Total Protocols Evaluated**: 108 (Full Athena Library)

These are the 10 most impactful protocols from the Athena framework, ranked by their ability to improve AI reasoning and user outcomes across any domain.

---

## MCDA Methodology

### Criteria Weights (AHP-Derived)

Weights were determined using **Analytic Hierarchy Process (AHP)** pairwise comparisons based on the question: *"For a new AI user, which criterion matters most for immediate impact?"*

| Criterion | Weight | Rationale |
|-----------|--------|-----------|
| **Ruin Prevention** | 35% | Law #1: Survival > Everything. Protocols that prevent catastrophic failure are non-negotiable. |
| **Applicability** | 30% | Daily usage compounds. A protocol used 100x/year beats one used 2x/year. |
| **Portability** | 20% | Protocols that work in ChatGPT/Claude/Gemini without Athena have broader reach. |
| **Depth** | 15% | Universal principles > narrow tactics, but depth without usage = theory. |

> **Why not equal weights?** Equal weights assume all criteria are equally important. In reality, preventing ruin (35%) matters more than portability (20%) because a portable protocol that causes ruin is still bad.

### Scoring Scale

| Score | Meaning |
|-------|---------|
| **5** | Best-in-class (top 5% of all protocols) |
| **4** | Strong (top 20%) |
| **3** | Good (average) |
| **2** | Below average |
| **1** | Weak / narrow use case |

---

## The Rankings

| Rank | Protocol | Weighted Score | Category |
|------|----------|----------------|----------|
| **1** | [Protocol 001: Law of Ruin](examples/protocols/safety/001-law-of-ruin.md) | **4.85** | Safety |
| **2** | [Protocol 193: Ergodicity Check](examples/protocols/decision/193-ergodicity-check.md) | **4.70** | Decision |
| **3** | [Protocol 75: Synthetic Parallel Reasoning](examples/protocols/decision/75-synthetic-parallel-reasoning.md) | **4.50** | Decision |
| **4** | [Protocol 140: Base Rate Audit](examples/protocols/decision/_archived/140-base-rate-audit.md) | **4.35** | Decision |
| **5** | [Protocol 28: 3-Second Override](examples/protocols/engineering/28-three-second-override.md) | **4.20** | Engineering |
| **6** | [Protocol 115: First Principles Deconstruction](examples/protocols/decision/115-first-principles-deconstruction.md) | **4.10** | Decision |
| **7** | [Protocol 48: Circuit Breaker (Systemic Pause)](examples/protocols/safety/48-circuit-breaker-systemic.md) | **4.05** | Safety |
| **8** | [Protocol 52: Deep Research Loop](examples/protocols/research/52-deep-research-loop.md) | **4.00** | Research |
| **9** | [Protocol 141: Claim Atomization Audit](examples/protocols/verification/141-claim-atomization-audit.md) | **3.95** | Verification |
| **10** | [Protocol 49: Efficiency vs Robustness Trade-off](examples/protocols/decision/49-efficiency-robustness-tradeoff.md) | **3.85** | Decision |

---

## Detailed Scoring Matrix

| Protocol | Ruin Prevention (35%) | Applicability (30%) | Portability (20%) | Depth (15%) | **Weighted Total** |
|----------|:--------------------:|:------------------:|:----------------:|:-----------:|:------------------:|
| **001: Law of Ruin** | 5 | 5 | 5 | 4 | **4.85** |
| **193: Ergodicity Check** | 5 | 4 | 5 | 5 | **4.70** |
| **75: Synthetic Parallel** | 5 | 4 | 4 | 5 | **4.50** |
| **140: Base Rate Audit** | 4 | 5 | 5 | 3 | **4.35** |
| **28: 3-Second Override** | 5 | 4 | 4 | 3 | **4.20** |
| **115: First Principles** | 3 | 5 | 4 | 5 | **4.10** |
| **48: Circuit Breaker** | 5 | 3 | 4 | 4 | **4.05** |
| **52: Deep Research Loop** | 4 | 4 | 4 | 4 | **4.00** |
| **141: Claim Atomization** | 4 | 4 | 3 | 5 | **3.95** |
| **49: Efficiency-Robustness** | 3 | 4 | 5 | 4 | **3.85** |

### Calculation Example (Protocol 001)

```
Score = (5 × 0.35) + (5 × 0.30) + (5 × 0.20) + (4 × 0.15)
      = 1.75 + 1.50 + 1.00 + 0.60
      = 4.85
```

---

## Pairwise Validation (Key Matchups)

### 193 vs 75 (Ergodicity Check vs Synthetic Parallel Reasoning)

| Dimension | Protocol 193 | Protocol 75 | Winner |
|-----------|--------------|-------------|--------|
| **Ruin Prevention** | Mathematical proof of ruin certainty | Multi-track catches blind spots | **193** |
| **Daily Usage** | Any repeated risk pattern | Complex decisions only | **193** |
| **Depth** | Physics-level (ensemble vs time avg) | 4-track meta-architecture | **Tie** |
| **Portability** | Simple checklist, any model | Requires cognitive overhead | **193** |

**Verdict**: Protocol 193 edges out 75. The ergodicity distinction is a more fundamental insight — it explains *why* ruin occurs mathematically. Protocol 75 is a powerful *vehicle* for reasoning, but 193 provides the *physics* that governs whether your reasoning even matters.

### 28 vs 48 (3-Second Override vs Circuit Breaker Systemic)

| Dimension | Protocol 28 | Protocol 48 | Winner |
|-----------|-------------|-------------|--------|
| **Ruin Prevention** | Stops single bad impulse (micro) | Stops cumulative damage cascade (macro) | **Tie** |
| **Daily Usage** | Any intuition violation | Threshold-triggered (less frequent) | **28** |
| **Depth** | Single heuristic (gut check) | Multi-domain threshold architecture | **48** |
| **Portability** | Universal (life, trading, coding) | Universal (but requires tracking) | **28** |

**Verdict**: Protocol 28 ranks higher because it fires more often and requires zero infrastructure. Protocol 48 is the necessary *extension* — the macro-level kill switch when individual 3-Second Overrides are ignored. Together, they form a complete stop-loss stack (micro + macro).

### 141 vs 49 (Claim Atomization vs Efficiency-Robustness)

| Dimension | Protocol 141 | Protocol 49 | Winner |
|-----------|-------------|-------------|--------|
| **Ruin Prevention** | Catches hallucinations pre-delivery | Prevents "magical thinking" (optimization traps) | **Tie** |
| **Daily Usage** | External deliverables only | Any optimization decision | **49** |
| **Depth** | 4-phase structured audit | Pareto frontier theory + multi-domain | **49** |
| **Portability** | Copy-paste ready | Copy-paste ready | **Tie** |

**Verdict**: Close call. Protocol 141 edges 49 on *precision* (it catches specific errors before they ship). Protocol 49 wins on *breadth* (it applies to career, trading, relationships, and engineering). Ranked 141 > 49 because the hallucination risk it prevents is a higher-severity failure mode.

---

## Sensitivity Analysis

*Does the ranking change if we adjust weights?*

| Scenario | Weight Shift | New #1 | Notable Change |
|----------|--------------|--------|----------------|
| **Risk-averse** (+10% Ruin) | Ruin: 45%, Applicability: 25% | Protocol 001 | 48 rises to #6 |
| **Practical focus** (+10% Applicability) | Applicability: 40%, Depth: 10% | Protocol 001 | 28 rises to #3 |
| **Theorist** (+10% Depth) | Depth: 25%, Ruin: 30% | Protocol 193 | **193 becomes #1** |
| **Portability-first** (+10% Portability) | Portability: 30%, Ruin: 30% | Protocol 001 | 49 rises to #7 |

**Conclusion**: Rankings are robust. Protocol 001 dominates across most weight scenarios. Only in a "Theorist" scenario (25% Depth weight) does Protocol 193 overtake it — which is actually defensible, since ergodicity is the *mathematical foundation* of Law of Ruin.

- **Safety-first users** → Protocol 001 (the foundational law)
- **Analysts/Decision-makers** → Protocol 193 (ensemble vs time average)
- **Engineers** → Protocol 28 (the universal panic button)
- **Generalists/Beginners** → Protocol 140 (simple, powerful heuristic)

---

## How to Use These Protocols

### For ChatGPT / Claude / Gemini Users

1. **Copy** the protocol markdown file.
2. **Paste** into your conversation as system instructions or context.
3. The AI will adopt the reasoning framework immediately.

### For Athena Users

These protocols are already loaded via `SKILL_INDEX.md`. Invoke by name:

- `/think` → Triggers Protocol 75
- `/research` → Triggers Protocol 52

---

## Changes from Previous Version

| Item | Old Ranking | New Ranking | Reason |
|------|-------------|-------------|--------|
| **193: Ergodicity Check** | #3 | **#2** | Mathematically more fundamental than 75. The physics > the vehicle. |
| **75: Synthetic Parallel** | #2 | **#3** | Still best-in-class reasoning architecture. Portability reduced to 4 (requires practice). |
| **28: 3-Second Override** | #7 | **#5** | Previously penalized on Depth (2→3). A circuit breaker doesn't need depth; it needs speed. |
| **48: Circuit Breaker** | Unranked | **#7** | The macro-level complement to Protocol 28. Prevents cumulative damage cascades across all domains. |
| **49: Efficiency-Robustness** | Unranked | **#10** | The Pareto frontier framework eliminates "magical thinking." Applies to trading, career, relationships. |
| **44: Micro-Commit** | #8 | **Removed** | Valuable but narrow (coding-specific). Displaced by more universal protocols. |
| **96: Latency Indicator** | #10 | **Removed** | UX signal, not a reasoning protocol. Doesn't improve the quality of decisions — only reports effort. |

### Honorable Mentions (Protocols #11-15)

| Protocol | Score | Why It Narrowly Missed |
|----------|-------|----------------------|
| **330: Economic Expected Value (EEV)** | 3.95 | Unified utility framework (Friedman-Savage). Merged from former Protocol 331. Consider for re-ranking. |
| **44: Micro-Commit** | 3.90 | Excellent engineering discipline, but coding-specific (Portability: 3). |
| **68: Anti-Karason** | 3.85 | Critical self-deception detector, but lower daily usage (Applicability: 3). |
| **104: Seymour Skeptic** | 3.80 | Strong adversarial safety layer. Narrower trigger conditions than ranked protocols. |
| **107: Spec-Driven Development** | 3.75 | Best coding workflow protocol, but engineering-specific. |

---

## Cross-References

- [Full Protocol Library](../examples/protocols/) — All 108 protocols
- [Architecture Overview](./ARCHITECTURE.md) — System design
- [Getting Started](./GETTING_STARTED.md) — Setup guide

# CS-005: The Min-Max Purchasing Framework

> **Domain**: Decision Making (Consumer Purchases)
> **Protocols Used**: [Protocol 500 (GTO Problem Solver)](../protocols/decision/500-gto-problem-solver.md), [Protocol 330 (EEV)](../protocols/decision/330-economic-expected-value.md)

## The Scenario

A user needed a flagship smartphone. The latest generation (Galaxy S26 Ultra) had just launched at full MSRP. The previous generation (Galaxy S24 Ultra) was functionally identical for daily use — same processor class, same camera system, same software update runway (7 years).

**The question**: Buy the latest at full price, buy the cheapest option available, or find a third path?

## The Three Buying Modes

Most people operate in one of two modes. Both are suboptimal.

| Mode | Optimises For | Failure Pattern |
|------|--------------|-----------------|
| **Prestige Buyer** | Max price, max status | Overpays for signal. The delta between MSRP and resale is pure ego tax. |
| **Cheapskate Buyer** | Min cost, period | False economy — buys inferior utility class, replaces sooner. Total cost of ownership is *higher*. |
| **Min-Max Buyer** | Min cost **×** Max value | Waits for the right moment, buys the right tier, captures 3x+ value multiplier. |

**The principle**: Min-max is not "cheap." Cheap minimises the *numerator* (price). Min-max maximises the *ratio* (value ÷ price).

## The Execution

The user bought a Galaxy S24 Ultra (256GB) on the secondary market — 2 weeks after the S26 Ultra launched.

| Component | Value |
|-----------|-------|
| S24 Ultra 256GB (MSRP) | $1,928 |
| Manufacturer warranty (13 months remaining) | ~$105-150 |
| 2× premium cases included | ~$40-65 |
| **Total bundle value** | **~$2,073-$2,143** |
| **Price paid** | **$650** |
| **Discount vs MSRP** | **66.3%** |
| **Value multiplier** | **~3.3x** |

The user paid **1/3 of MSRP** for a like-new device with accessories and warranty coverage.

## The Mechanism: Depreciation Inversion

When a new generation launches, sellers upgrading to the latest model dump the previous generation at fire-sale prices. The critical insight:

- **Utility curve**: barely moves between generations (S24 Ultra → S26 Ultra is a ~10-15% improvement in benchmarks, imperceptible in daily use).
- **Price curve**: crashes 50-70% on the secondary market within 2-4 weeks of the new launch.

The gap between these two curves is where min-max value lives.

```
Utility:  ████████████████████░░  (S24 Ultra: 90% of S26)
Price:    ██████░░░░░░░░░░░░░░░░  (S24 Used: 34% of S26 MSRP)
                    ↑
            Min-Max value gap
```

## Risk Mitigation Checklist

The user wasn't just buying cheap — they were **bounding downside risk**:

1. ✅ Ran hardware diagnostics (Samsung's `*#0*#` service menu) — all tests passing
2. ✅ Verified manufacturer warranty coverage (13 months remaining) — cosmetic defect is fixable
3. ✅ Checked seller reputation (5.0 rating, 46 reviews, 12 years on platform)
4. ✅ Confirmed accessories (original box, cable, 2 cases, screen protectors)
5. ✅ Cosmetic-only defect (single dead pixel) — does not affect utility

## Generalisation

The Depreciation Inversion pattern applies to any depreciating asset with generational cycles:

| Asset Class | Min-Max Strategy | Typical Savings |
|-------------|-----------------|-----------------|
| **Smartphones** | Buy N-1 generation at launch of N | 50-70% |
| **Laptops** | Buy 12-18 months after launch (used, at depreciation floor) | 40-60% |
| **Cars** | Buy 2-3 years old at the steepest depreciation point | 30-50% |
| **Cameras** | Buy previous generation body at new model launch | 40-60% |

## The EEV Angle

Why this is a **Level 2 (EEV)** decision, not Level 1 (MEV):

- **MEV** says: "Don't buy a phone at all — the cheapest option is no phone."
- **EEV** says: "You need a flagship for work (camera quality, S-Pen for notes, multitasking). The question is *how* to acquire that utility at the lowest real cost."

The utility function is personal. A photographer might genuinely need the S26's updated sensor. For most professionals, the S24 Ultra delivers 95%+ of the same utility at 34% of the price.

## One-Liner

> **Don't minimise price. Don't maximise prestige. Maximise the ratio.**

---

> **Related**: [Protocol 330 (EEV)](../protocols/decision/330-economic-expected-value.md) · [Protocol 500 (GTO)](../protocols/decision/500-gto-problem-solver.md) · [Use Cases](../../docs/USE_CASES.md)

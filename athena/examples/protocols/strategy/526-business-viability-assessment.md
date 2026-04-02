---
protocol: 526
title: Business Viability Assessment (The 3-Layer Stack)
category: strategy
version: 1.0
created: 2026-03-13
dependencies: [162, 511, 330]
---

# Protocol 526: Business Viability Assessment

> **Purpose**: Pre-qualify business models and client ventures using a fixed 3-layer diagnostic sequence. Prevents investing time in structurally unviable businesses.

---

## The Problem

Most business failures aren't caused by bad products — they're caused by broken economics that were never tested. Entrepreneurs (and the consultants who serve them) skip straight from "idea" to "execution" without validating whether the underlying structure can sustain a business.

The 3-Layer Stack forces the diagnostic sequence that kills fantasy businesses in 5 minutes.

---

## The Stack (Fixed Sequence)

```
Layer 1: BMC (Architecture)     → "What exists?"
Layer 2: Four Fits (Physics)    → "Does it hold?"
Layer 3: Pro Forma P&L (Reality) → "Does it print?"
```

### Why This Order?

The sequence is non-negotiable because each layer's output feeds the next:

1. **BMC** maps what the business *claims* to be (revenue streams, cost structure, channels, segments)
2. **Four Fits** tests whether those claims are *structurally coherent* (does the product fit the market? does the channel fit the product? does the model fit the channel?)
3. **Pro Forma** translates the surviving structure into *cash flow* — the ultimate reality check

Skipping to Layer 3 without Layers 1-2 produces garbage-in-garbage-out financials. Beautiful spreadsheets built on unvalidated assumptions.

---

## Layer 1: Business Model Canvas (Architecture)

Map all 9 BMC blocks. The goal isn't creativity — it's **inventory**. What does this business actually consist of?

| Block | Key Question |
|:------|:-------------|
| Customer Segments | Who pays? (Not who uses — who *pays*) |
| Value Proposition | What pain are you killing? What gain are you creating? |
| Channels | How does the customer find you and receive the product? |
| Customer Relationships | Self-serve? Personal? Community? |
| Revenue Streams | One-time? Recurring? Usage-based? |
| Key Resources | What must you have? (IP, equipment, people, capital) |
| Key Activities | What must you do? (Production, logistics, platform management) |
| Key Partnerships | Who else is in the value chain? (Suppliers, landlords, platforms) |
| Cost Structure | Fixed costs? Variable costs? Cost-driven or value-driven? |

**Output**: A structural map. Not a pitch deck — a blueprint.

---

## Layer 2: Four Fits (Physics)

> Source: Brian Balfour (2016), "Four Fits" framework.

All four fits must hold simultaneously. A business with 3/4 fits will fail — just slower.

| Fit | Test | Failure Mode |
|:----|:-----|:-------------|
| **Market ↔ Product** | Does the product solve a real problem for a real market? | Great product nobody wants |
| **Product ↔ Channel** | Does the product distribute naturally through the chosen channel? | Right product, wrong shelf |
| **Channel ↔ Model** | Does the channel economics support the revenue model? | Paying $50 to acquire a $30 customer |
| **Model ↔ Market** | Does the market size support the revenue model at scale? | $10M TAM with $5M fixed costs |

### The Pre-Qualification Gate

| Score | Verdict |
|:------|:--------|
| 4/4 Fits | ✅ **PROCEED** to Layer 3 (Pro Forma) |
| 3/4 Fits | ⚠️ **FIX** the broken fit before proceeding |
| ≤2/4 Fits | ❌ **REJECT** — structurally unviable without redesign |

---

## Layer 3: Pro Forma P&L (Reality)

Build a simple 12-month projection. The goal is **kill speed** — not precision. You're testing whether the business *can* be profitable, not predicting exact numbers.

```
Revenue (Monthly)
  - COGS (Cost of Goods Sold)
  = Gross Profit
  - Operating Expenses (Rent, Payroll, Marketing, Tools)
  = Operating Profit (EBITDA proxy)
  - CapEx Amortization
  = Net Margin
```

### Key Metrics to Extract

| Metric | Threshold | Why |
|:-------|:----------|:----|
| Gross Margin | >50% (services), >30% (products) | Below this, scaling amplifies losses |
| Operating Margin | >20% | Below this, one bad month = negative |
| Breakeven Revenue | Calculate | "How much must I sell per month to survive?" |
| Cash Conversion Cycle | Calculate | "Do I get paid before or after I pay costs?" |

### The Final Gate

| Condition | Verdict |
|:----------|:--------|
| 4/4 Fits + >20% operating margin | ✅ **Take the client / Launch the venture** |
| 4/4 Fits + <20% margin | ⚠️ Cost restructuring needed |
| ≤2/4 Fits + <10% margin | ❌ **Walk away** |

---

## Empirical Validation

This stack has been applied across:

| Business | Four Fits Score | Pro Forma Result | Verdict |
|:---------|:---:|:---:|:---:|
| FnB (Hawker, Restaurant) | 1/4 | 13% margin, $23K/mo breakeven | ❌ Structurally hostile |
| Group Tuition (Zenith-style) | 4/4 | 87% gross, 75% EBITDA | ✅ SaaS-grade economics |
| Solo Web Design | 1/4 | Healthy margin but zero distribution | ❌ Without distribution redesign |
| Solo + AI Consulting | 3-4/4 | 85% operating margin | ✅ Viable at low volume |

---

## Anti-Patterns

- ❌ Building a Pro Forma without first mapping the BMC (garbage-in-garbage-out)
- ❌ Declaring viability based on product quality alone (Fit #1 only)
- ❌ Skipping Four Fits because "the food is good" / "the code is clean"
- ❌ Running this stack *after* committing capital (post-mortem vs pre-mortem)

---

## Related Protocols

- [Protocol 162: PMOD](162-product-market-operations-fit.md) — Complementary; P162 validates operational sequence, P526 validates economic viability
- [Protocol 511: Business Viability Trinity](511-business-viability-trinity.md) — Buyer × Demand × Niche (pre-filter); P526 is the deeper follow-up
- [Protocol 330: Economic Expected Value](../decision/330-economic-expected-value.md) — Use EEV to weight qualitative factors alongside the Pro Forma

---

## Tags

#protocol #strategy #business #viability #four-fits #bmc #pro-forma #client-qualification

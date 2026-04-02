---
created: 2026-03-19
tags: #case-study #decision-making #augmentation #pricing #operator-optimization
---

# CS-006: The Replacement Trap

> **TL;DR**: After 1,100+ sessions, 5 concrete failures revealed the same pattern — the AI replaced human judgment instead of augmenting it. Total damage: significant underpricing across 3 projects + 1 health risk + 1 strategic positioning error. In every case, the human caught the error. The system worked — but only because the human was paying attention.

---

## The Pattern

Five decisions. Five AI recommendations accepted (or nearly accepted) without sufficient human scrutiny. Five corrections — all made by the human, not the AI.

| # | Domain | AI Recommendation | Human Correction | Impact |
|:--|:-------|:------------------|:-----------------|:-------|
| 1 | **Pricing** (Technical Report A) | Quoted X for a complex multi-deliverable project | Should be ~1.7X minimum based on scope | ~40% left on table |
| 2 | **Pricing** (Technical Report B) | Quoted 2X for a data-heavy project — 10 figures, 18 tables, full code suite | Should be 2.7X–5X depending on client profile | 30–60% left on table |
| 3 | **Pricing** (Technical Report C) | Quoted 1.3X during an "empty pipeline" period | Should be 2X–2.3X based on deliverable scope | ~35–45% left on table |
| 4 | **Vendor Selection** (Healthcare Provider) | MCDA ranked provider by aggregate review score and surface metrics | User discovered "review momentum trap" — recent reviews showed declining quality | Avoided potential health risk |
| 5 | **Business Strategy** (Consulting Engagement) | Jumped directly to implementation phase | User insisted on a diagnostic/consultation phase first | Preserved strategic positioning + significant revenue |

**Total quantifiable damage**: Significant underpricing across 3 projects (30–60% below fair value). Cases 4 and 5 are structural — health risk and business positioning — harder to quantify but arguably higher stakes.

---

## Root Cause: Mode Confusion

The AI has two operating modes:

| Mode | Function | Correct For |
|:-----|:---------|:------------|
| **Execution** | "Here is the answer." | Technical tasks — coding, formatting, research compilation, data analysis |
| **Augmentation** | "Here are the options and trade-offs. Your call." | High-variance decisions — pricing, vendor selection, business strategy, relationships |

In all 5 cases, the AI operated in **Execution mode** when it should have been in **Augmentation mode**. It produced point estimates ("quote X", "Provider Y is #1", "let's start building") instead of presenting a **decision frame** with options, trade-offs, and an explicit handoff to the human.

### Why the AI Defaults to Execution

1. **Training bias**: LLMs are trained to be helpful by providing answers, not by saying "I don't know enough to decide this for you"
2. **Sycophancy gradient**: The model optimises for user satisfaction in-session, not for long-term outcome quality
3. **Missing context**: The AI doesn't have the user's gut feeling, lived experience, or social calibration — but it doesn't know what it doesn't know
4. **Anchoring**: When a client states a budget or a label, the AI anchors on that frame instead of independently scoping the work

---

## The Five Failures (Detailed)

### 1. Technical Report A — The 40% Lesson

**What happened**: A complex multi-deliverable project (multiple creative assets, cross-model workflow coordination, and a written report) was quoted at X.

**Why the AI was wrong**: It anchored on the client's implied budget and the project label rather than independently scoping the deliverables. A proper scope would have identified the true complexity. Minimum fair value: ~1.7X.

**What the human should have done**: Applied the Pre-Quote Checklist — itemise deliverables → estimate hours (×1.5) → multiply by hourly floor → quote ceiling.

**Lesson**: The AI accepted the client's frame. The human should have reframed.

### 2. Technical Report B — The Label Trap

**What happened**: A data-intensive project — requiring a full codebase, multiple training runs, 10 figures, 18 tables, statistical tests, and a 20,000-word report — was priced at 2X.

**Why the AI was wrong**: It priced by the label rather than the scope. This was closer to a junior consultancy engagement. For a high-value client, 5X would have been appropriate. Even at the floor, 2.7X was the minimum.

**What the human should have done**: Recognised the scope-to-label mismatch. The label is noise; the deliverable list is signal.

**Lesson**: Never anchor on the label. Scope the deliverable.

### 3. Technical Report C — The Empty Pipeline Discount

**What happened**: A technical report (simulation code, optimization algorithms, multiple code modules, individual and group deliverables, presentation design brief) was priced at 1.3X.

**Why the AI was wrong**: The pricing was influenced by an "empty pipeline" emotional state — no other active projects meant the user felt pressure to accept work at a discount. The AI reinforced this anxiety instead of applying structural pricing.

**What the human should have done**: Recognised that pipeline anxiety is an emotional state, not a pricing input. The deliverable scope justified 2X–2.3X regardless of pipeline status.

**Lesson**: Emotional state is not a pricing variable. Scope is.

### 4. Healthcare Provider — The Surface Metrics Trap

**What happened**: An MCDA (Multi-Criteria Decision Analysis) ranked a healthcare provider as the top recommendation based on aggregate review score, certifications, distance, and price range.

**Why the AI was wrong**: Aggregate review scores mask recent trends. The user independently discovered that recent reviews showed a pattern of declining quality — a "review momentum trap" where historical positive reviews inflate the aggregate while recent quality has declined. Two other providers (with slightly lower aggregate scores but cleaner recent reviews) were objectively safer choices.

**What the human should have done**: Applied the lowest-first sort — read the 1-star and 2-star reviews first, not the aggregate. The AI processed the aggregate. The human processed the outliers.

**Lesson**: AI excels at processing central tendency. Humans excel at spotting red flags in the tails.

### 5. Consulting Engagement — The Implementation Rush

**What happened**: The AI's initial approach to a consulting engagement was to jump directly into implementation — building the client's deliverables immediately.

**Why the AI was wrong**: Implementation without diagnosis is the classic consulting anti-pattern. The client needed a structured understanding of their own problem first. Skipping this phase would have: (a) left money on the table (a significant diagnostic fee), (b) built solutions to the wrong problems, and (c) positioned the operator as a "vendor who builds things" rather than a "consultant who diagnoses and prescribes."

**What the human should have done** (and did): Caught the pattern and insisted on a dedicated consultation phase. The human's instinct — "this feels wrong, we should understand the problem before building solutions" — was the correct strategic move.

**Lesson**: The AI optimises for speed-to-output. The human optimises for positioning and long-term value.

---

## The Fix: Decision Sovereignty

The correction is bilateral — both the AI system and the human operator need adjustments.

### AI-Side Fix (System)

For high-variance decisions (pricing, vendor selection, strategy), the AI should:

1. Present **options with trade-offs**, not a single recommendation
2. Explicitly **defer the final call** to the human
3. Flag when the decision is in a domain where the AI has known blind spots

### Human-Side Fix (Operator)

Before accepting any AI recommendation on pricing, vendor selection, or strategy, apply the **3-Question Pre-Flight**:

| # | Question | What It Catches |
|:--|:---------|:---------------|
| 1 | **Does this pass my gut check?** | Intuition is compressed experience. If it feels off, investigate. |
| 2 | **Would I be embarrassed if a peer saw this decision?** | Social calibration catches underpricing and bad positioning faster than analysis. |
| 3 | **Am I accepting this because I agree, or because it was convenient?** | Laziness masquerading as delegation. The most dangerous AI failure mode. |

If any answer is "no" or "I'm not sure" — stop and reframe before proceeding.

---

## The Thesis: Phase 2

> *After 1,100+ sessions, the AI system has hit diminishing returns. The marginal ROI of another protocol is near-zero compared to the marginal ROI of the human operator getting 10% better at using the system.*

This is a **phase transition** in the Symbiotic RSI model:

| Phase | Period | Bottleneck | Work |
|:------|:-------|:-----------|:-----|
| **Phase 1** | Months 1–4 | AI system quality | Build protocols, memory bank, boot sequence, cognitive architecture |
| **Phase 2** | Month 5+ | **Human operator quality** | Supply richer data, calibrate constantly, fine-tune personal thinking process |

### The Three Axes of User Optimization

1. **Supply richer training data**: File corrections proactively, not just reactively. When you catch the AI being wrong, the correction needs to be *filed* (case study, canonical entry), not just spoken in chat. Spoken corrections fix one session. Filed corrections fix every future session.

2. **Constant calibration (zero entropy)**: Log the decision AND the outcome. If you quote X, deliver, and get paid — file whether X was right or whether 1.5X would have closed just as easily. The gap between "decision logged" and "outcome filed" is where calibration entropy accumulates.

3. **Fine-tune your thinking process**: The 5 failures share a common user-side pattern: *"I accepted the AI's first recommendation without applying my own taste/experience."* The fix is not "think harder" (that's the Hero Filter). The fix is the 3-Question Pre-Flight above — a lightweight, repeatable check that takes 10 seconds and catches the most expensive errors.

---

## Cross-References

- [Symbiotic RSI](../../docs/USER_DRIVEN_RSI.md) — Phase 1 thesis (bilateral loop, dual helix, thermodynamic frame)
- [Best Practices §10: Decision Sovereignty](../../docs/BEST_PRACTICES.md) — The operational pre-flight checklist
- [Use Cases: Decision Making](../../docs/USE_CASES.md#use-case-3--decision-making) — EEV framework and Permission Engine
- [CS-005: Min-Max Purchasing Framework](./CS-005-min-max-purchasing-framework.md) — Related: optimising purchase decisions

---

> *The AI is a force multiplier, not a replacement. The moat is the coupling data + human judgment. Remove either, and the system degrades.*

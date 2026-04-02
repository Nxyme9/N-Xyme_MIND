---
name: Red-Team Review
description: Bias-aware adversarial review for any artifact before shipping. 5-phase QA protocol with severity-weighted findings.
created: 2026-02-27
auto-invoke: true
model: default
---

# 🔴 Red-Team Review

> **Philosophy**: Find what you both missed. Assume shared blind spots.

## 1. When to Use

Before shipping any significant artifact — blog post, code, protocol, proposal, design doc. Best used with a **different model** than the one that created the artifact.

## 2. The Prompt

Copy this prompt and paste the artifact to be reviewed where indicated:

```markdown
# RED-TEAM REVIEW

You are reviewing an artifact. Your job: Find what WE BOTH missed.

## THE ARTIFACT
<paste artifact here>

---

## PHASE 0: DECLARE YOUR PRIORS
Before reviewing, state:
1. What thesis does this artifact assume?
2. What would falsify that thesis?
3. What perspective is NOT represented?

## PHASE 1: ADVERSARIAL LENSES
Review through EACH perspective:

| Lens | Question |
|------|----------|
| **The Skeptic** | What would someone who disagrees say? |
| **The User** | Who is harmed or disadvantaged? |
| **The Regulator** | What legal/ethical exposure exists? |
| **The Cynic** | What hidden incentive might be driving this? |
| **The Future** | How does this look in 5 years? |

## PHASE 2: BIAS CHECKLIST
Flag if present:
- [ ] Sycophancy — Did I just validate the creator's view?
- [ ] Cherry-Picking — Is counter-evidence missing?
- [ ] False Precision — Are numbers unjustified?
- [ ] Complexity Bias — Is a simpler explanation ignored?

## PHASE 3: SEVERITY-WEIGHTED FINDINGS
- 🔴 CRITICAL: Immediate failure if shipped
- 🟠 HIGH: Significantly reduces value
- 🟡 MEDIUM: Missed upside
- 🟢 LOW: Polish

## PHASE 4: SCORE (0-100)
Your Score: [ ] / 100

## PHASE 5: UNCERTAINTY
"I am least confident about ___ because ___."
```

## 3. Rules

- Quote directly. No vague complaints.
- Steelman opposing views BEFORE critiquing.
- Empty sections are fine — don't invent issues.
- Every HIGH must have a fix achievable in ≤10 minutes.

---

# skill #quality-assurance #adversarial #review

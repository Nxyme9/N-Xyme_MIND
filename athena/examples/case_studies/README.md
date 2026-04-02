# Case Studies

> Real patterns documented by Athena users. Names and details anonymized.

Case studies are **formalized learnings** — each one captures a situation, what was tried, what worked, and the protocol that emerged from it. They are the raw material from which Athena's protocols are distilled.

## How Case Studies Work

Every time Athena encounters a meaningful pattern — a decision that went well, a mistake that taught something, a strategy that proved repeatable — it gets filed as a case study. Over time, these compound into institutional memory.

```text
Situation → Decision → Outcome → Pattern → Protocol
```

A mature Athena workspace (500+ sessions) may have 400+ case studies. The public repo ships with a curated starter set to demonstrate the format.

## Structure

Each case study follows a consistent format defined in the [case study template](../templates/case_study_template.md):

| Field | Purpose |
|:------|:--------|
| **Context** | What was the situation? |
| **Challenge** | What made this hard? |
| **Approach** | What did Athena recommend? Which protocols were used? |
| **Outcome** | What happened? |
| **Pattern** | What generalizable principle emerged? |
| **Tags** | For semantic search and retrieval |

## Starter Case Studies

| File | Domain | Pattern |
|:-----|:-------|:--------|
| [CS-001](CS-001-sunk-cost-career-pivot.md) | Decision / Career | Sunk cost fallacy in career decisions |
| [CS-002](CS-002-scope-creep-freelance.md) | Execution / Business | Scope creep in freelance projects |
| [CS-003](CS-003-confirmation-bias-research.md) | Research / Reasoning | Confirmation bias in research synthesis |
| [CS-004](CS-004-plea-bargain-diagnostic.md) | Decision / Legal | Non-ergodic plea bargain — diagnostic pipeline demo |

## Creating Your Own

Use the template:

```bash
cp examples/templates/case_study_template.md examples/case_studies/CS-XXX-your-title.md
```

Athena will automatically detect new case studies and index them. Over time, your case study library becomes a personal knowledge graph of lessons learned.

## Privacy Note

Case studies in the **public repo** are anonymized examples. In your **private workspace**, case studies may contain personal details — this is by design. Never push private case studies to a public repository.

---

# case-studies #memory #patterns #learning

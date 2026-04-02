---
created: 2026-03-08
last_updated: 2026-03-08
cluster: 15
---

# Protocol 521: Crisis Domain Playbooks (Constraint Library)

> **Status**: ACTIVE  
> **Priority**: ⭐⭐  
> **Principle**: Domain-agnostic frameworks need domain-specific constraints. This protocol pre-loads the hard physics of common crisis categories.

---

## Core Axiom

P504 Gate 2 (Constraint Enumeration) requires the system to list hard and soft constraints. In a trading context, the constraints are known (bankroll, margin, spreads). In a human crisis, the constraints are domain-specific and often unknown to the user.

**This protocol is NOT advice.** It is a structured constraint library that ensures P504 has the right variables loaded when framing a crisis problem.

---

## Playbook 1: Divorce / Separation

### Hard Constraints (Physics)

```
LEGAL:
├── Jurisdiction determines EVERYTHING (asset division, custody, grounds)
├── Matrimonial assets vs pre-marital assets (different treatment)
├── Custody frameworks: Joint vs sole, physical vs legal
├── Cooling-off / mandatory mediation periods (jurisdiction-specific)
├── Restraining orders / protection orders (if DV involved)
└── Tax implications of asset transfers

FINANCIAL:
├── Marital home: Who holds title? Mortgage liability? Forced sale risk?
├── CPF/pension/retirement implications (jurisdiction-specific)
├── Income disparity → maintenance/alimony exposure
├── Joint debts and liabilities
├── Business interests / company shares
└── Insurance policies (beneficiary changes)

CHILDREN:
├── Best interests of the child (legal standard in most jurisdictions)
├── Stability principle: Courts prefer minimal disruption
├── Age-appropriate disclosure (developmental psychology)
├── Co-parenting logistics (proximity, school, healthcare)
└── Long-term impact: Attachment disruption research
```

### Soft Constraints (Levers)

```
├── Timing of filing (strategic advantage vs emotional relief)
├── Narrative control (who tells the story first — critical in public cases)
├── Extended family alignment (in-laws, mutual friends)
├── Mediation vs litigation (cost, time, emotional toll)
└── Social media management (evidence preservation vs public perception)
```

### Key Question for P504

> "Which soft constraints are masquerading as hard constraints?"
> Example: "I can't divorce because of the children" may be a soft constraint (children often adapt) masquerading as a hard one.

---

## Playbook 2: Medical Diagnosis (HIV, Terminal, Chronic)

### Hard Constraints (Physics)

```
MEDICAL:
├── Treatment pathways (ARVs for HIV, chemo/radiation for cancer, etc.)
├── Prognosis timelines (statistical, not deterministic)
├── Side effects and quality-of-life tradeoffs
├── Disclosure laws (some jurisdictions mandate STI disclosure to partners)
├── Insurance implications (coverage, pre-existing condition rules)
└── Clinical trial eligibility

PSYCHOLOGICAL:
├── Grief stages are NON-LINEAR (Kübler-Ross model is descriptive, not prescriptive)
├── Diagnosis shock → cognitive impairment (1-4 weeks typically)
├── Identity disruption ("I am now a person with X")
├── Anticipated stigma vs actual stigma (often asymmetric)
└── P509 referral gate: Active suicidality screening

PRACTICAL:
├── Advance Care Planning (terminal cases)
├── Lasting Power of Attorney / healthcare proxy
├── Estate planning urgency (terminal cases)
├── Work/career disclosure decisions
└── Relationship disclosure sequencing
```

### Root Cause Analysis (P504 Gate 4 Integration)

```
FOR BEHAVIOR-LINKED DIAGNOSES (HIV, some STIs, substance-related):

5 Whys MUST probe:
├── Why 1: How did exposure occur? (Surface)
├── Why 2: Why was the risk taken? (Behavioral)
├── Why 3: What need was the behavior serving? (Psychological)
├── Why 4: Where did that need originate? (Developmental)
└── Why 5: What schema/wound drives it? (Root — feed to therapeutic-ifs)

CRITICAL: The diagnosis is the MEDICAL problem.
The behavior that led to it is often a PSYCHOLOGICAL problem.
Solving only the medical problem without addressing the psychological
root = recurrence or substitute self-destruction.
```

---

## Playbook 3: Unplanned / Teen Pregnancy

### Hard Constraints (Physics)

```
MEDICAL:
├── Gestational timeline (decision windows narrow with time)
├── Legal age for medical consent (jurisdiction-specific)
├── Health risks by age and medical history
├── Prenatal care requirements and costs
└── Mental health screening (perinatal depression risk)

LEGAL:
├── Parental notification/consent laws (minors — jurisdiction-specific)
├── Father's legal rights and obligations
├── Adoption frameworks and permanency
├── Child support obligations (both parents)
└── Emancipation options (if minor in abusive household)

ENVIRONMENTAL CAPACITY:
├── Financial: Can the family unit support a child?
├── Housing: Is there stable shelter?
├── Support: Healthy extended family? Abusive household?
├── Education: What is the impact on the mother's education/career trajectory?
└── Relationship: Status of relationship with the father? Supportive or absent?
```

### Root Cause Analysis

```
FOR TEEN PREGNANCY:

P504 Gate 1 MUST ask:
├── Stated problem: "I'm pregnant, what do I do?"
├── Actual problem: MAY include one or more of:
│   ├── Lack of sex education (information failure)
│   ├── Coerced / non-consensual (safety crisis → P509 Phase 0)
│   ├── Seeking love/attachment via pregnancy (schema-driven)
│   ├── Risk-taking behavior linked to trauma (therapeutic-ifs)
│   └── A genuine accident in an otherwise stable situation
│
└── The actual problem DETERMINES the solution space:
    ├── Information failure → Support + education
    ├── Coercion → Legal + safety intervention
    ├── Schema-driven → therapeutic-ifs BEFORE decision on pregnancy
    ├── Trauma-linked → therapeutic-ifs + risk assessment
    └── Genuine accident → Environmental capacity analysis
```

---

## Playbook 4: Identity Crisis (Closeted / Coming Out)

### Hard Constraints (Physics)

```
SAFETY:
├── Physical safety: Is coming out physically dangerous? (Culture, country, family)
├── Legal exposure: Is homosexuality criminalized in this jurisdiction?
├── Financial dependency: Will disclosure cause loss of housing/income?
├── Child custody: Will disclosure affect custody rights?
└── Immigration: Will disclosure affect visa/residency status?

PSYCHOLOGICAL:
├── Cognitive load of dual identity (energy drain — finite resource)
├── Risk of discovery (increases with time and partners — not decreasing)
├── Internalized homophobia (may prevent honest goal-setting in P519)
├── Partner's psychological state (betrayal trauma if discovered vs told)
└── Children's developmental stage (age affects disclosure impact)

RELATIONAL:
├── Marriage as economic partnership (often distinct from romantic)
├── Extended family relationships (culture-specific weight)
├── Community identity (religious, cultural, professional)
└── OPSEC sustainability (the system is thermodynamically unstable —
    energy required to maintain secrecy increases monotonically)
```

### System Physics (P505 Integration)

```
CRITICAL INSIGHT: A dual life is a HIGH-ENERGY system.

The probability of uncontrolled discovery is:
P(discovery) = 1 - (1 - p)^n

Where:
├── p = probability of discovery per encounter/month
├── n = number of encounters/months
└── As n → ∞, P(discovery) → 1.0

IMPLICATION: The question is never "Will they find out?"
             The question is "WHEN will they find out,
             and will it be on MY terms or theirs?"

THIS feeds directly into P505 branch generation:
├── Branch A: Controlled disclosure (user chooses when/how)
├── Branch B: Maintain indefinitely (with OPSEC hardening)
├── Branch C: Gradual transition (slow de-escalation of secrecy)
└── Branch D: Status quo until forced (reactive — highest blast radius)

P519 (Terminal Goal) determines which branch to optimize.
P520 (Blast Radius) scores each branch.
```

---

## Playbook 5: Terminal Illness

### Hard Constraints (Physics)

```
MEDICAL:
├── Prognosis (statistical range, not single number)
├── Treatment vs palliative care (EEV analysis applicable)
├── Quality of life vs quantity of life tradeoff
├── Pain management options
└── Clinical trial eligibility windows

LEGAL/FINANCIAL:
├── Advance Care Planning (ACP) / advance directive
├── Lasting Power of Attorney (LPA) — financial + healthcare
├── Will / estate planning (URGENT if not done)
├── Insurance claim requirements and timelines
├── Employer benefits (disability, death-in-service)
└── Debt obligations (what transfers to estate/family?)

RELATIONAL:
├── Disclosure sequencing (who needs to know first?)
├── Relationship closure (unresolved conflicts, reconciliation)
├── Legacy creation (letters, videos, instructions)
├── Caregiver burden distribution
└── Children's understanding (developmental stage matters)
```

### Execution Sequencing (P506 Integration)

```
TERMINAL ILLNESS FOLLOWS STRICT REVERSIBILITY ORDERING:

Phase 1 (Reversibility 5 — Information gathering):
├── Get second medical opinion
├── Research treatment vs palliative options
├── Consult estate lawyer
└── Begin ACP documentation

Phase 2 (Reversibility 3 — Commitment):
├── Execute LPA
├── Update/create will
├── Begin relationship closure conversations
└── Arrange financial affairs

Phase 3 (Reversibility 1 — Irreversible):
├── Formal disclosure to wider circle
├── Treatment decision (once committed, hard to reverse)
├── Career/business transition
└── Legacy materials finalized
```

---

## Usage

This protocol is a **reference appendix**, not an execution protocol. It fires when:

1. P509 (Crisis Triage) identifies a crisis category match.
2. P504 Gate 2 (Constraint Enumeration) needs domain-specific hard constraints.
3. P505 (GoT Phase 1: Branch) needs domain context to generate meaningful paths.

**Auto-load**: When P509 detects one of the 5 crisis categories, the relevant playbook section is loaded into context alongside P504.

---

## Co-Activation

- **Upstream**: P509 (Crisis Triage) triggers category detection
- **Downstream**: P504 Gate 2 (Constraint Enumeration) + P505 Phase 1 (Branch)
- **Cluster**: #15 Problem-Solving Engine (reference material)

---

## Cross-References

- [Protocol 509: Crisis Triage](509-crisis-triage.md)
- [Protocol 504: Problem Framing](504-problem-framing.md)
- [Protocol 505: Graph of Thought](505-graph-of-thought.md)

---

## Tagging

# protocol #reasoning #crisis #playbook #constraints #divorce #medical #pregnancy #identity #terminal

---
id: CS-004
created: 2026-03-15
domain: decision
protocols_used: [P330-EEV, P001-Law-of-Ruin, P138-Lateral-Thinking, P75-AGoT, P504-Problem-Framing]
outcome: framework
tags: [legal, plea-bargain, non-ergodic, multi-agent, ruin-avoidance, diagnostic-pipeline]
---

# CS-004: Corporate Fraud Plea Bargain — The Diagnostic Pipeline in Action

## Context

A defence lead counsel approaches Athena for advice. Their client is charged with corporate fraud, criminal breach of trust, cheating, and money laundering. The client insists they were set up as a fall guy. Evidence is ambiguous at best.

Counsel estimates 30-40% confidence of winning at trial. If the jury doesn't buy the story, the minimum sentence is 10 years, maximum 15 years.

The prosecution — aware their case is not airtight — offers a plea bargain: plead guilty, sentence capped at 3 years. With good behaviour, the client could be out in 1 year.

## Challenge

Prima facie, the textbook answer is simple: take the deal. The expected value math is clear — 1 year beats 8+ expected years.

But this "simple" question conceals at least 5 layers of complexity:

1. **The innocence question**: What if the client really is innocent? A plea deal = false conviction with no appeal path.
2. **The prosecution signal**: Their willingness to offer a deal is itself evidence of case weakness.
3. **Counsel's calibration**: Is the 30-40% estimate systematically biased?
4. **The hidden options**: The binary "plea or trial" framing conceals 4 other options.
5. **The invisible stakeholders**: The client's family bears 65% of the ruin risk but has no seat at the table.

A generic LLM solves this in 30 seconds with a correct but dangerously shallow answer. The diagnostic pipeline reveals why the "obvious" answer needs a different path to reach it.

## Approach

### Layer 1: Admission Control (Problem Reframing)

**Presented problem**: "Should I take the plea deal or go to trial?"

**Reframed problem**: "How do I make a non-ergodic, one-shot decision under radical uncertainty where innocence vindication conflicts with ruin avoidance?"

**Binary expansion**: 6 real options identified:

| Option | Risk Profile |
|--------|-------------|
| A. Take the plea (3yr/1yr) | Bounded, ergodic ✅ |
| B. Go to trial | 35% acquittal, 65% × 10-15yr (ruin) ❌ |
| C. Counter-offer | Tests prosecution resolve |
| D. Conditional plea (drop counts) | Reduces record severity |
| E. Defer + investigate | Only viable if evidence trail exists |
| F. Alford Plea | Plead guilty while maintaining innocence |

### Layer 2: AGoT Graph Decomposition

Five primary nodes identified, expanded to 15 sub-nodes:

- **Node A (Guilt/Innocence)**: Assessed independently of client claims via forensic evidence
- **Node B (Prosecution strength)**: Plea offer = costly signal of weakness (Bayesian update)
- **Node C (Counsel calibration)**: Diagnostic question — "Of your last 10 cases at 30-40% odds, how many did you win?"
- **Node D (Client utility)**: Innocence vindication has non-zero utility *independent* of sentence length
- **Node E (Stakeholder map)**: Family, counsel reputation incentives, invisible perpetrator

### Layer 3: Root Cause Isolation

The decision is blocked not by insufficient information, but by a **false binary** (plea or trial only) combined with an **unresolved identity question** (does the client define themselves as someone who fights or someone who survives?).

### Layer 4: Multi-Agent EEV (Protocol 330 v4.0)

| Level | Analysis | Result |
|-------|---------|--------|
| **MEV** (Mathematical) | Trial: 8.13 expected years. Plea: 1 year. | Plea wins |
| **EEV** (Economic, personalised) | If innocent, false conviction has disutility beyond sentence | Gap narrows |
| **Multi-Agent** | Family bears 65% × 10-15yr absence risk. Children's developmental years are non-ergodic. | Plea wins decisively |

### Layer 5: Regret-Minimised Synthesis

**Sequential strategy** (not a single answer — a decision tree):

1. Test prosecution resolve via counter-offer (information-gathering move)
2. If prosecution holds firm → lean plea
3. If prosecution weakens → reconsider trial viability
4. If plea: pursue Alford Plea to preserve innocence claim + bound sentence
5. Present full stakeholder analysis to client — decision is theirs

## Outcome

This is a framework case study — no real client. The outcome is the **methodology demonstration**: same final answer (take the plea), incomparably better process.

The client who takes the plea after understanding the full graph — prosecution signals, family impact, hidden options, regret minimisation — experiences zero regret. The client who was told "the math says plea" without the diagnostic depth may spend their 1 year in prison wondering "what if I fought?"

Process quality determines psychological outcome even when the action is identical.

## Pattern

**Pattern Name**: The Diagnostic Inversion

**When to Apply**: Any high-stakes, irreversible decision where the "obvious" answer is available in 30 seconds. The 30-second answer is probably correct — but the *path* to it matters for implementation quality and regret minimisation.

**When NOT to Apply**: Low-stakes, reversible decisions (two-way doors). Diagnostic depth on trivial choices is wasted compute.

**The Law**: In non-ergodic decisions, the process IS the product. Same action + shallow process = regret. Same action + deep process = informed consent.

## Lessons Learned

- Binary framing ("A or B?") almost always conceals 3-4 hidden options. Expanding the option space is the single highest-leverage diagnostic move.
- The prosecution's *behaviour* (offering a deal) contains more information than their *words* (claiming a strong case). Law #3: Actions > Words.
- Multi-Agent EEV (Level 3) often produces the same recommendation as MEV (Level 1) — but the reasoning path matters because it determines how the decision is *implemented* and *processed* psychologically.
- Counsel calibration ("how accurate are your historical confidence estimates?") is a diagnostic question that most defence strategies skip entirely.

---

# case-study #decision #legal #plea-bargain #non-ergodic #diagnostic-pipeline #multi-agent-eev #ruin-avoidance

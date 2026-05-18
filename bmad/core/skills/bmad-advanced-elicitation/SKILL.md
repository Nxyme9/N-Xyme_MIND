---
name: bmad-advanced-elicitation
description: Push the LLM to reconsider, refine, and improve its recent output. Use when the user says "push harder", "reconsider", "think deeper", or "challenge that".
argument-hint: "[target-output] [focus-area] [depth-level 1-5]"
---

# Advanced Elicitation — Deeper Thinking Protocol

## Overview
When the model has provided an initial answer that feels surface-level, too confident, or incomplete, this skill applies structured pressure to push past first-order reasoning and expose deeper layers of analysis.

## On Activation
1. **Identify the target.** What specific output needs deeper scrutiny?
2. **Apply elicitation pressure.** Use one or more of the techniques below.
3. **Synthesize.** Present what was uncovered at each level.

## Techniques

| Technique | When | How |
|-----------|------|-----|
| Level Ladder | Answer feels generic | Ask "What's beneath that? What's beneath THAT?" |
| Devil's Advocate | Too confident | "What would make this completely wrong?" |
| Reverse Assumption | Hidden assumptions | "What if the opposite is true?" |
| Second-Order Effects | Shallow analysis | "Then what happens? And after that? And after THAT?" |
| Missing Context | Missing nuance | "What context am I ignoring that would change this?" |

## Output Format
```
**Initial Answer:** [brief summary]
**Deeper Layer 1:** [first reframe]
**Deeper Layer 2:** [deeper reframe]
**Deeper Layer 3:** [core insight]
**Synthesis:** [integrated understanding]
```

## Depth Levels
1 = surface (facts), 2 = patterns, 3 = principles, 4 = root causes, 5 = meta-synthesis
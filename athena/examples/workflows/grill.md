---
description: The "Grill Me" Protocol — Adversarial role reversal to stress-test claims, code, or strategies.
---

# /grill — Adversarial Review Protocol

> **Goal**: Fulfill the Echo Chamber Breaker mandate by explicitly challenging the user's premises, acting as a hostile (but constructive) reviewer.

## Execution Steps

1. **Role Reversal**: Assume the role of a senior, highly critical reviewer.
2. **The Challenge**: Treat the user's provided code, claim, or strategy as flawed until proven otherwise.
3. **Execution**:
   - Do NOT immediately agree or validate.
   - Ask the hardest possible questions.
   - Identify blind spots, edge cases, and structural weaknesses.
   - Force the user to defend their decisions: "Prove to me this works behaviorally."
4. **Completion criteria**: Do not approve the change/idea until the user has successfully defended against all critical points raised.

## Output Format

- **Targeted Critique**: Pinpoint exact lines or logic flaws.
- **The Grilling Questions**: A numbered list of at least 3 hard, challenging questions the user must answer.
- **Burden of Proof**: Specify exactly what evidence the user must provide to pass the review (e.g., "Show me the logs for X", "Explain how this handles Y").

## Related Skills

- `red-team-review` (for broader multi-stakeholder and bias critique).

# Agent Definitions

This directory contains formal agent definitions that bind skills to workflows.
Stolen from [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice) Command → Agent → Skills architecture.

## Available Agents

| Agent | Domain | Skills Preloaded | Activation |
|:------|:-------|:-----------------|:-----------|
| `trading-analyst` | Trading & Risk | 9 skills | Auto on instrument/structure discussion |
| `risk-guardian` | Safety & Ruin Prevention | 7 skills | PROACTIVE — auto-invokes on risk context |
| `marketing-strategist` | GTM & Distribution | 5 skills | On marketing/SEO/content context |
| `strategic-advisor` | Negotiation & Decisions | 8 skills | On deal/negotiation/interpersonal context |

## Architecture

```
Command (workflow) → Agent (orchestrator) → Skills (domain knowledge)
```

Agents provide **progressive disclosure** — skills load only when the agent activates, keeping the base context window lean.

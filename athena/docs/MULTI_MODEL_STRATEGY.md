# Multi-Model Strategy Guide

> **Last Updated**: 10 March 2026

Athena is model-agnostic — your memory, protocols, and governance persist across any LLM. This means you can use **different models for different tasks** and get the best of each.

This guide provides a practical model routing strategy for users with access to multiple models (e.g., via [Antigravity](https://antigravity.google/), or by switching between IDEs).

---

## Recommended Models & Cost

Athena is **free and open source**. You only pay for your AI subscription. But to get the most out of Athena's structured reasoning, governance protocols, and multi-step workflows — **use frontier (SOTA) models**.

| Plan | Cost | What You Get |
|:-----|:-----|:-------------|
| Claude Pro / Google AI Pro | ~$20/mo | Full access to frontier models. Best value for most users. |
| Claude Max / Google AI Ultra | $200–250/mo | Extended usage limits for power users (8+ hrs/day). |

> [!IMPORTANT]
> **This is a long-term investment, not a cost.** Frontier models dramatically increase your output quality and consistency. Athena's protocols — governance, reasoning depth, structured workflows — are designed for models that can follow complex multi-step instructions. Smaller/free models may struggle to follow them consistently.

**Recommended frontier models for Athena:**

| Model | Strengths | Best Used For |
|:------|:---------|:-------------|
| **Claude Opus 4.6** | Deep reasoning, code quality, nuanced analysis | Coding, architecture, verification |
| **Gemini 3.1 Pro** | Broad knowledge, fast synthesis, strong planning | General work, research, planning |
| **Gemini 3 Flash** | Speed, low cost | Session management (`/start`, `/end`), quick lookups |
| **GPT-5.4 (High)** | Alternative perspective, good at creative tasks | Trilateral tiebreaker, creative work |

> [!TIP]
> **The cheapest path to full Athena capability is a single $20/mo subscription** (Claude Pro or Google AI Pro). You don't need multiple subscriptions — one frontier model handles everything. Multiple subs unlock the trilateral feedback loop for high-stakes decisions.

---

## Session Modes

Not every conversation needs the full Athena boot sequence. Match the mode to the task:

| Mode | Flow | When To Use | Overhead |
|:-----|:-----|:------------|:---------|
| **🟢 Lightweight** | Just chat → `/end` | General chat, brain dumps, idea capture, Q&A | ~0 tokens (no framework loaded) |
| **🔴 Full Boot** | `/start` → Work → `/end` | Coding, architecture, client work, trading, irreversible decisions | ~10K tokens (full cognitive stack) |
| **⚫ Deep Boot** | `/ultrastart` → Work → `/ultraend` | Complex multi-domain analysis, `/ultrathink`, architectural decisions | ~20K tokens (System-2 deep context) |

**The Decision Heuristic**: If you can summarize the goal in one sentence AND it doesn't touch code, money, or irreversible decisions → **Lightweight mode**.

> [!TIP]
> **Lightweight mode is ideal for brain dumps and casual ideation.** You get the raw model's performance without the 10K–20K token overhead of loading protocols and routing. When the conversation shifts to something complex, start a new session with `/start` or `/ultrastart`.

---

## The Framework Tax

Athena's structured protocols, cognitive routing, and session management are powerful — but they come at a cost: **every session loads 2K–20K tokens of system context** (depending on boot mode) before you type a single word.

This "framework tax" means:

| Effect | Impact |
|:-------|:-------|
| **Token burn** | 2K–20K tokens consumed on boot, reducing your effective session budget |
| **Model strain** | Weaker models struggle with the volume of system instructions |
| **Quota drain** | On subscription plans with rate limits, you're spending quota on overhead |

**The key insight**: The framework tax pays for itself on complex tasks (where governance, routing, and structured reasoning prevent costly mistakes). But it's pure waste on simple tasks.

| Task Type | Framework Tax Worth It? |
|:----------|:-----------------------|
| "What's the capital of France?" | ❌ No — use Lightweight mode |
| "Help me think through this idea" | ❌ No — brain dump mode, save the tokens |
| "Build the authentication system" | ✅ Yes — structured reasoning prevents rework |
| "Should I take this job offer?" | ✅ Yes — governance protocols catch blind spots |

> [!IMPORTANT]
> **Frontier models (Opus, Gemini Pro) follow Athena's instructions faithfully — which means they burn tokens faithfully too.** The more capable the model, the more important it is to route it efficiently. Don't pay frontier prices for lightweight tasks.

---

## The Routing Table

| Task Type | Recommended Tier | Why |
|:----------|:----------------|:----|
| **Session Management** (`/start`, `/end`, `/save`) | ⚡ Fast (e.g., Gemini Flash) | Mechanical execution, low reasoning needed. Save your premium tokens. |
| **Coding & Implementation** | 🔥 Frontier (e.g., Claude Opus, Gemini Pro) | Code quality scales directly with model capability. |
| **Planning & Architecture** | 🔥 Frontier | Design decisions compound — invest the best reasoning here. |
| **General Chat & Q&A** | 🧠 Strong (e.g., Gemini Pro) | Good enough for most queries. Toggle to Frontier for depth. |
| **Research & Deep Analysis** | 🔥 Frontier | Synthesis quality degrades significantly with weaker models. |
| **Creative & Brainstorming** | 🧠 Strong or 🔥 Frontier | Use Strong for volume generation, Frontier for quality refinement. |
| **Verification & Code Review** | 🔥 Frontier (different model) | Use a *different* model than the one that wrote the code. Fresh eyes catch more bugs. |
| **Quick Lookups & Formatting** | ⚡ Fast | Don't waste Frontier tokens on "reformat this table." |

---

## The Trilateral Feedback Loop

When two models disagree on a significant decision, bring in a third:

```
Model A (e.g., Gemini 3.1 Pro) →  Opinion 1
Model B (e.g., Claude Opus)    →  Opinion 2
                                    ↓
                              Conflict detected?
                                    ↓
Model C (e.g., GPT-5.4, Llama) →  Tiebreaker / Synthesis
```

**When to trigger**:

- Architecture decisions with long-term consequences
- Risk assessments where models disagree on severity
- Strategy choices where both options seem equally valid
- Any decision where the cost of being wrong is high

**When NOT to trigger**:

- Style preferences (just pick one)
- Low-stakes choices (not worth the tokens)
- When one model's answer is clearly more grounded

---

## Cost Optimization

The key insight: **most of your session is NOT frontier-level work.**

| Session Phase | % of Tokens | Model Tier | Cost Impact |
|:-------------|:-----------|:-----------|:------------|
| `/start` boot | ~5% | ⚡ Fast | Minimal |
| Exploration & chat | ~40% | 🧠 Strong | Moderate |
| Core reasoning & coding | ~40% | 🔥 Frontier | Highest |
| `/end` shutdown | ~5% | ⚡ Fast | Minimal |
| Verification | ~10% | 🔥 Frontier (alt) | Moderate |

By routing only the high-value 40% to Frontier models, you can cut effective costs by ~50% while maintaining output quality where it matters.

---

## Model Switching in Practice

### In Antigravity / Multi-Model IDEs

Most modern agentic IDEs let you switch models mid-session:

1. **Start your session** with a Fast model (`/start`, boot scripts)
2. **Switch to Frontier** when you hit complex work (coding, architecture, analysis)
3. **Switch back to Strong/Fast** for routine tasks (formatting, file ops, simple Q&A)
4. **End your session** with Fast (`/end`, shutdown scripts)

### Cross-IDE Validation

For the trilateral loop, you can also use different IDEs entirely:

1. **Primary IDE** (e.g., Antigravity with Gemini 3.1 Pro) — first opinion
2. **Secondary IDE** (e.g., Claude Code with Opus) — second opinion
3. **Tiebreaker** (e.g., ChatGPT, Copilot) — third opinion if needed

Athena's Markdown-based memory means all three IDEs can read the same context.

---

## The Orchestrator-Executor Pipeline

The most token-efficient workflow for high-stakes work: use a **Strong model for scoping** and an **Frontier model for execution only**.

```
Phase 1: SCOPE (Strong model — e.g., Gemini 3.1 Pro)
├── Run /start (load context)
├── Ingest client briefs, messy requirements
├── Output: Structured spec / implementation plan
└── Run /brief, /plan, or spec-driven-dev skill

Phase 2: EXECUTE (Frontier model — e.g., Claude Opus 4.6)
├── Receive the structured spec (not the raw mess)
├── Execute ONLY the complex 30% that needs deep reasoning
└── Output: Working code, final deliverable, strategic synthesis

Phase 3: VERIFY (Strong model — e.g., Gemini 3.1 Pro)
├── Run /audit or /check on the Frontier output
├── Use a DIFFERENT model to catch blind spots
└── Run /end (commit, log, push)
```

**Why this works:**

| Phase | Token Cost | Reasoning Needed | Model |
|:------|:-----------|:-----------------|:------|
| Scoping & planning | High (lots of reading) | Medium | Strong (cheap tokens) |
| Core execution | Medium (focused work) | **Maximum** | Frontier (worth the premium) |
| Verification & QA | Medium | Medium | Strong (fresh perspective) |

The Frontier model never sees the messy ideation phase — it only receives the final, structured spec. This keeps its context window clean and its output focused.

> [!TIP]
> **This pipeline typically cuts Frontier token usage by 50-70%** while maintaining output quality on the parts that matter. The Strong model handles the token-heavy reading; the Frontier model handles the reasoning-heavy execution.

---

## Anti-Patterns

| ❌ Don't | ✅ Do Instead |
|:---------|:-------------|
| Use Frontier for `/start` and `/end` | Use Strong/Fast — it's mechanical work |
| Use Frontier for brain dumps and ideation | Use Lightweight mode with a Strong model |
| Use Fast for architecture decisions | Use Frontier — design compounds |
| Use one model for everything | Route by task type |
| Run `/start` for a 5-minute question | Use Lightweight mode — skip the framework tax |
| Skip verification entirely | Use a different model to review critical code |
| Run trilateral loop on every question | Reserve it for high-stakes disagreements |
| Have Frontier read messy client briefs | Have Strong summarize first, pass the spec to Frontier |

---

## Quick Reference Card

```
Brain dumps, casual chat   →  🟢 Lightweight mode (no /start, just chat and /end)
/start, /end, /save        →  🧠 Strong (Gemini 3.1 Pro) or ⚡ Fast
Scoping, planning, briefs  →  🧠 Strong (Gemini 3.1 Pro)
Coding, web dev, apps      →  🔥 Frontier (Claude Opus / Gemini 3.1 Pro)
Planning, architecture     →  🔥 Frontier (never Fast)
General chat, Q&A          →  🧠 Strong (Gemini 3.1 Pro)
Research, deep analysis    →  🔥 Frontier
Verification, code review  →  🔥 Frontier (DIFFERENT model than author)
Conflict resolution        →  🌐 Trilateral Loop (3rd model as tiebreaker)
Quick lookups, formatting  →  ⚡ Fast
```

---

## Further Reading

- [TIPS.md](TIPS.md) — General tips for getting the most out of Athena
- [ARCHITECTURE.md](ARCHITECTURE.md) — How Athena's model-agnostic design works
- [BENCHMARKS.md](BENCHMARKS.md) — Token usage and performance data

---

> *The model is the engine. You choose which gear to drive in.*

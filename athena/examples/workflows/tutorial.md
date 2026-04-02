---
description: Guided first-session walkthrough for new Athena users
created: 2026-02-22
last_updated: 2026-02-22
---

# /tutorial — First-Session Guided Walkthrough

> **Duration**: ~20–30 min (with interview) · ~5 min (skipping interview)
> **When to use**: Your very first session with Athena.
> **Exit anytime**: Say "skip" to jump to the next stage, or "I'm done" to end the tutorial.

---

## How This Works

You are the pilot. Athena is your co-pilot. This tutorial walks you through everything you need to know to operate Athena effectively — and builds your personal profile along the way.

**The tutorial has 7 stages:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Stage 1 │ Welcome                    │  ~1 min   │  What is this?
│  Stage 2 │ The Core Loop              │  ~2 min   │  /start → Work → /end
│  Stage 3 │ Build Your Profile         │  ~15–25 min │  The Interview
│  Stage 4 │ Search Demo                │  ~2 min   │  See RAG in action
│  Stage 5 │ Save & Checkpoint          │  ~1 min   │  Quicksave
│  Stage 6 │ Key Commands               │  ~2 min   │  Your toolkit
│  Stage 7 │ Graduation                 │  ~30 sec  │  You're set
└─────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: Welcome

> **Goal**: Orient the user. Explain what they just cloned.

**Say to the user:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🎓 ATHENA TUTORIAL — Stage 1 of 7: Welcome
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Welcome to Project Athena.

You've just cloned an operating system for AI agents. Here's what's
already installed and ready to use:

  🧠 Core Identity     — A constitution with 6 operating laws
  📋 120+ Protocols    — Decision frameworks for reasoning, research, strategy
  ⚡ 49 Slash Commands — /start, /end, /think, /research, and more
  🔍 Hybrid RAG Search — 5-source retrieval that searches YOUR knowledge
  🔌 MCP Tool Server   — 9 tools exposable to any MCP-compatible IDE
  🛡️ Governance Layer  — 4 capability levels, 3 sensitivity tiers

All of this works out of the box. You can use it as-is, customize it,
or replace it entirely with your own configuration.

This tutorial will show you how everything fits together.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Type "next" to continue, or "skip" to jump ahead.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Stage 2: The Core Loop

> **Goal**: Teach the fundamental `/start` → Work → `/end` loop.

**Say to the user:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🎓 ATHENA TUTORIAL — Stage 2 of 7: The Core Loop
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Athena runs on one cycle:

  /start  →  Work  →  /end

Every time you close a session with /end, Athena saves what happened:
decisions made, insights generated, context accumulated.

Next time you /start, it loads that context back. Over time:

  Sessions 1–50:    Basic recall (name, project, preferences)
  Sessions 50–200:  Pattern recognition (anticipates your style)
  Sessions 200+:    Deep sync (thinks in YOUR frameworks)

The more sessions you run, the more Athena becomes *yours*.

Think of /start as "boot" and /end as "shutdown + save".
Skipping /end means losing that session's memory.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 You already ran /start to get here. ✅
 Type "next" to continue.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Stage 3: Build Your Profile (The Interview)

> **Goal**: Build the user's profile through an interactive interview.
> **Duration**: 15–25 minutes (the longest stage).
> **Skippable**: Yes — a generic profile template is already included.

**Say to the user:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🎓 ATHENA TUTORIAL — Stage 3 of 7: Build Your Profile
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Athena already ships with a working default profile. You can start
using it right now without changing anything.

But Athena gets dramatically better when it knows who YOU are.
This interview builds a personal profile — your goals, how you think,
what you're building, your blind spots.

This is a one-time investment (~15–25 min) that pays compound
returns across every future session.

  ✅ Everything stays on YOUR machine (local Markdown files)
  ✅ You can edit the profile anytime after
  ✅ You can skip this entirely and do it later

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Ready? Type "let's go" to start the interview.
 Or type "skip" to continue with the default profile.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Interview Execution

If the user proceeds, run the interview using the following rules. These are the same rules as `/brief interview` — embedded here so the tutorial is self-contained.

#### Interview Rules

| Rule | Description |
|------|-------------|
| **Max 10 questions per turn** | Don't overwhelm. Batch intelligently. |
| **Non-obvious questions only** | No "what color?" — ask what the user hasn't thought about. |
| **Iterate until satisfied** | No arbitrary cap. Keep asking until full clarity. |
| **User controls pace** | User can say "that's enough" or "ask me more" at any turn. |
| **No execution during interview** | Only ask + synthesize. Don't build yet. |

#### Question Categories

| Category | Example Questions |
|----------|-------------------|
| **Identity** | Name, location, languages, what should I call you? |
| **Professional** | Occupation, industry, role, what are you currently building? |
| **Technical** | Tech stack, tools, skill levels, preferred languages |
| **Goals** | Short-term (3 months), medium-term (1 year), long-term (5+ years) |
| **Decision Style** | Risk appetite, speed vs quality, analysis depth |
| **Communication** | Preferred tone (direct/formal/casual), verbosity preference |
| **Values** | Core principles, non-negotiables, ethical boundaries |
| **Strengths** | What you're excellent at, unique edges |
| **Weaknesses** | Blind spots, recurring mistakes, areas you want watched |
| **Life Context** | Anything else that helps Athena understand your full picture |

#### Interview Completion

When the interview is complete, generate the user profile and write it to `.context/memories/user_profile.md`. Then display:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ✅ Interview Complete
    Questions asked: XX | Turns: Y

 📄 Profile saved to: .context/memories/user_profile.md

 📋 Key Traits Captured:
    - [Trait 1]
    - [Trait 2]
    - [Trait 3]

 💡 You can edit this file anytime to refine your profile.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Type "next" to continue the tutorial.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Stage 4: Search Demo

> **Goal**: Show the user what RAG search looks like on their own data.

**Action**: Run a semantic search on something from the user's profile (or a generic query if they skipped the interview).

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🎓 ATHENA TUTORIAL — Stage 4 of 7: Search Demo
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Let me show you what Athena's memory looks like in action.

I'm going to search the knowledge base for something relevant to you.
Watch — this is the Exocortex (Athena's hybrid retrieval engine).
```

// turbo

**Execute**:

```bash
python3 examples/scripts/smart_search.py "<relevant query based on user profile>" --limit 3
```

**Then say**:

```
That's Athena searching across your entire knowledge base using
hybrid retrieval: keyword search + semantic embeddings + reranking.

Every session you run adds to this searchable memory.
After 100 sessions, this becomes your personal search engine.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Type "next" to continue.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Stage 5: Save & Checkpoint

> **Goal**: Teach quicksave / checkpointing.

**Say to the user:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🎓 ATHENA TUTORIAL — Stage 5 of 7: Save & Checkpoint
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Athena saves automatically during /end, but you can also
checkpoint mid-session anytime with /save.

Think of it like a game save — snapshot your progress so
nothing is lost if you need to stop unexpectedly.

Let me demo this now.
```

// turbo

**Execute**:

```bash
python3 scripts/quicksave.py "Tutorial checkpoint — first session"
```

**Then say**:

```
✅ Checkpoint saved.

Your session log is in: .context/memories/session_logs/

Each session produces a structured log with:
  • Key decisions made
  • Insights generated
  • Checkpoints (like the one we just created)

Over time, these logs become a searchable archive of your thinking.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Type "next" to continue.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Stage 6: Key Commands

> **Goal**: Give the user a reference card of the most useful commands.

**Say to the user:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🎓 ATHENA TUTORIAL — Stage 6 of 7: Your Toolkit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Here are the commands you'll use most:

  SESSION MANAGEMENT
  ─────────────────
  /start        Boot session, load context
  /end          Close session, save to memory
  /save         Mid-session checkpoint

  REASONING
  ─────────────────
  /think        Deep reasoning mode (important decisions)
  /ultrathink   Maximum depth (life-altering decisions)

  RESEARCH
  ─────────────────
  /search       Web search with citations
  /research     Exhaustive multi-source investigation

  PLANNING
  ─────────────────
  /brief        Clarify requirements before complex work
  /plan         Structured planning with pre-mortem

  UTILITY
  ─────────────────
  /vibe         Ship fast, iterate, 70% confidence
  /diagnose     Run workspace health check

You have 49 slash commands total. Full list:
→ docs/WORKFLOWS.md

Don't memorize them. Just know /start, /end, and /think for now.
The rest will come naturally.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Type "next" to continue.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Stage 7: Graduation

> **Goal**: Wrap up. Give the user confidence and clear next steps.

**Say to the user:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🎓 ATHENA TUTORIAL — Stage 7 of 7: Graduation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎉 You're set.

Here's what you now have:

  ✅ Athena is booted and operational
  ✅ Your profile is built (or the default is loaded)
  ✅ You've seen search, save, and the core loop in action
  ✅ You know the essential commands

WHAT TO DO NOW:
  • Just work. Talk to Athena like a colleague.
  • When you're done: type /end
  • Next session: type /start — Athena picks up where you left off.

NEXT STEPS (when you're ready):
  • Browse 120+ protocols:  examples/protocols/
  • Customize your identity: .framework/modules/Core_Identity.md
  • Add to your knowledge base: drop files in .context/memories/
  • Read the full docs: docs/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🚀 Your first session starts now. Go build something.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Tagging

# workflow #onboarding #tutorial #first-session #interview

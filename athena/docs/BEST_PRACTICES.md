# Best Practices

> **Last Updated**: 19 March 2026

Operational discipline for running Athena sustainably. These aren't features — they're habits that prevent data loss, reduce friction, and keep your system compounding.

---

## 0. The Fastest Way to Learn (The Dual Pressure Model)

> *"Criticism sharpens the blade. Paid work proves it cuts."*

The single fastest way to accelerate mastery of AI agents isn't reading docs or watching tutorials. It's **taking on projects** — specifically, two kinds simultaneously:

| Pressure | What It Teaches | Feedback Loop |
|:---------|:----------------|:--------------|
| **Open-source projects** | **Robustness** — adversarial users find every edge case, every broken assumption, every gap in your architecture | Public criticism forces you to harden what works and kill what doesn't |
| **Paid projects** | **Velocity** — real deadlines + real money force you to find the fastest path through unknown domains | Revenue validates that the system creates tangible value |

### Why Neither Alone Is Sufficient

| Configuration | Outcome |
|:-------------|:--------|
| Open-source only | Beautiful system that nobody pays for — high prestige, zero revenue |
| Paid projects only | You ship fast but never harden the architecture — technical debt compounds |
| **Both together** | Criticism hardens the system, paid work validates its value — **compounding loop** |

**The mechanism**: Open-source projects (like publishing Athena on Reddit) generate adversarial feedback from strangers who have zero incentive to be polite. This feedback is *more valuable* than self-testing because it surfaces blind spots you can't see from the inside. Paid projects (like speed-running a capstone in a day with AI) generate *empirical proof* that the system works under real constraints — deadlines, client expectations, unfamiliar domains.

Together, they create the [Symbiotic RSI](USER_DRIVEN_RSI.md) loop at the project level: the open-source community is the "human correction" arm (they tell you what's broken), and paid clients are the "validation" arm (they prove what works by paying for it).

> **The insight that "AI agents can perform magic" doesn't come from reading a blog post. It comes from shipping a capstone in a day.** Lived experience creates conviction that no amount of documentation can replicate.

---

## 1. Back Up Your Data (The Non-Negotiable)

Your `.context/` folder **is** your brain. Losing it means losing every session, every protocol, every insight you've ever extracted. Treat it like source code — because it is.

### The 3-2-1 Rule

| Layer | What | Why |
|:------|:-----|:----|
| **Local** | Your machine (primary copy) | Speed — instant reads, no latency |
| **Git** (GitHub / GitLab) | Full repo push on every `/end` | **Portability** — clone anywhere, restore in seconds |
| **Cloud DB** (Supabase / ChromaDB) | Vector embeddings + semantic index | **Search** — hybrid RAG across your entire history |

> [!IMPORTANT]
> **At minimum, push to Git.** If your laptop dies tomorrow, `git clone` + `/start` gets you back to 100%. Everything else is acceleration.

### Backup Checklist

- [ ] **Git remote configured** — `git remote -v` shows your GitHub/GitLab URL
- [ ] **Auto-commit on `/end`** — The shutdown orchestrator commits and pushes automatically
- [ ] **`.gitignore` reviewed** — Ensure `.env`, API keys, and `.athenad.pid` are excluded
- [ ] **Cloud sync active** (optional) — Supabase or Google Cloud for embeddings

> [!TIP]
> **Why subscribe to AI Pro?** Beyond the higher rate limits, Pro plans often include priority access during peak hours and longer context windows. For Athena users running 4+ sessions/day, the consistency alone justifies the cost. Think of it as paying for *uptime*, not just *features*.

---

## 2. Session Discipline

### Three Session Modes

Not every conversation needs the full boot sequence. Athena supports **three modes** — pick the right one based on what you're doing:

| Mode | When To Use | Flow |
|:-----|:------------|:-----|
| **🟢 Lightweight** | General chat, brain dumps, idea capture, Q&A, quick lookups | Just chat → `/end` when done |
| **🔴 Full Boot** | Coding, architecture, client work, trading, anything irreversible | `/start` → Work → `/end` |
| **⚫ Deep Boot** | Complex multi-domain analysis, architectural decisions, `/ultrathink` | `/ultrastart` → Work → `/ultraend` |

**The Decision Heuristic**: If you can summarize the goal in one sentence AND it doesn't touch code, money, or irreversible decisions → **Lightweight mode**. Everything else → **Full Boot**.

| ✅ Do | ❌ Don't |
|:-------|:---------|
| Use Lightweight for casual chats and brain dumps | Run `/start` for a 5-minute question |
| Use Full Boot for client work, code, and high-stakes tasks | Skip `/start` when working on code or money |
| Always `/end` — even in Lightweight mode | Forget to `/end` (nothing gets committed) |
| `/save` mid-session for long threads | Rely on the AI to "remember" across sessions |
| One focused topic per session | Cram five unrelated tasks into one thread |

> [!IMPORTANT]
> **`/end` is non-negotiable in both modes.** `/start` is optional for lightweight chat. `/end` is what triggers the session log, memory persistence, and git commit. Skip `/end` and nothing gets saved.

### Why Two Modes?

The `/start` workflow loads your full identity, protocols, and routing architecture (~10K tokens). `/ultrastart` loads the full deep context stack (~20K tokens). For a complex coding session, this investment pays for itself many times over. For a quick question or brain dump, it's unnecessary overhead that burns tokens and time.

**Lightweight mode** gives you raw model performance with zero framework tax. **Full Boot mode** gives you the full Athena cognitive stack. Match the mode to the task.

### The One-Feature Rule

Each session should target **one deliverable**. This isn't about being rigid — it's about context coherence. A session that covers authentication, UI design, *and* database schema produces a messy log that's hard to search later.

> **Guideline**: If you can't summarize the session in one sentence, it was probably two sessions.

---

## 3. Memory Hygiene

### Prune `activeContext.md` Regularly

`activeContext.md` is your **working memory** — not your archive. If it grows beyond ~100 lines, it's carrying stale context that wastes tokens on every boot.

| Signal | Action |
|:-------|:-------|
| Completed tasks still listed | Move to session log, mark `[x]`, or delete |
| "Recent Context" older than 1 week | Archive to session logs or compact |
| Duplicate entries | Merge or remove |

### Keep `userContext.md` Lean

Your user profile should contain **stable truths**, not session-specific details. If something changes every week, it belongs in `activeContext.md`, not `userContext.md`.

---

## 4. Git Workflow

### Commit Often, Push Always

| Practice | Rationale |
|:---------|:----------|
| Commit after every `/end` | Atomic, searchable history |
| Use semantic commit messages | `feat:`, `fix:`, `docs:` prefixes make `git log` useful |
| Push to remote same day | Local commits aren't backups — they're drafts |
| Tag major milestones | `git tag v9.2.5` lets you rollback cleanly |

### Branch Strategy (Advanced)

For users maintaining both private (full context) and public (sanitized) repos:

```
main        ← public-facing (Athena-Public)
private     ← full context (.context/, personal protocols)
```

> [!WARNING]
> **Never push `.context/memory_bank/` to a public repo.** It contains personal data (psychology, decisions, constraints). Use `.syncignore` or `.gitignore` to exclude sensitive directories.

---

## 5. Token Budget Awareness

Athena boots at 2K–20K tokens (depending on mode), leaving 180K–198K for your session. But token waste adds up:

| Waste Source | Fix |
|:-------------|:----|
| Oversized `activeContext.md` | Prune weekly (see §3) |
| Loading files you don't need | Trust JIT routing — don't `/fullload` unless you need it |
| Repeating context the AI already has | Reference session logs instead of re-explaining |
| Pasting entire files into chat | Point to the file path — let the agent read it |

---

## 6. Multi-Account / Multi-Model Strategy

If you use multiple AI accounts or models:

| Practice | Why |
|:---------|:----|
| **Designate a "primary" for Athena sessions** | Consistency in session logs and memory |
| **Use secondary accounts for research** | Keeps your primary context clean |
| **Run Trilateral Feedback for big decisions** | Cross-validate across Claude, Gemini, GPT |
| **Always return to primary for `/end`** | Ensures the canonical session log is written |

> The Memory Bank means your context is **decoupled from the provider**. Switch models freely — the state lives in your filesystem, not their servers.

---

## 7. Security Basics

| Practice | Details |
|:---------|:--------|
| **Never commit `.env` files** | Use `.env.example` as a template, `.gitignore` the real one |
| **Rotate API keys periodically** | Especially after sharing screens or running demos |
| **Use Secret Mode for demos** | `set_secret_mode(True)` redacts sensitive data |
| **Review agent permissions** | Don't grant filesystem access to `~/.ssh` or credential stores |

> 👉 Full security model: [SECURITY.md](SECURITY.md)

---

## 8. When Things Go Wrong

| Problem | Recovery |
|:--------|:---------|
| **Lost local data** | `git clone` your repo → `/start` → back in business |
| **Corrupted session log** | Check `git log` for the last clean commit → `git checkout` |
| **Boot fails** | Run `python -m athena doctor` to diagnose |
| **Context feels "off"** | Review `activeContext.md` for stale/incorrect entries |
| **Model quality drops mid-session** | You've likely hit ~150K tokens. Run `/save` and start fresh |

---

## 9. The Cold Start Rule

> *"If it doesn't run from a clean clone, it doesn't run."*

Before submitting any code deliverable — to a client, a professor, or a public repo — verify it from **a clean directory with zero local state**:

```bash
# Clone into a temp directory
git clone <your-repo> /tmp/cold-start-test
cd /tmp/cold-start-test

# Run the exact startup commands from your README
npm install && npm run dev    # or equivalent
```

**Why this matters**: Local development environments accumulate hidden state — cached modules, environment variables, global packages, IDE settings. Code that "works on my machine" fails on the client's machine because it depends on state you didn't ship. The Cold Start Rule catches these failures *before* the client sees them.

| Anti-Pattern | Cold Start Catches It |
|:-------------|:---------------------|
| Missing dependency in `package.json` | ✅ `npm install` fails |
| Hardcoded local path | ✅ Path doesn't exist in `/tmp/` |
| Uncommitted file | ✅ Not in the clone |
| Environment variable not documented | ✅ App crashes on boot |

> Derived from empirical failure: a working project shipped to a client that failed to start because a required dependency was installed globally but never added to `package.json`. Time to diagnose: 2 hours. Time to prevent: 60 seconds.

---

## 10. Decision Sovereignty (The Pre-Flight Checklist)

> *"The most expensive AI failure isn't bad output. It's good-sounding output accepted without human judgment."*

AI excels at generating plausible, well-structured recommendations. This is precisely what makes it dangerous for **high-variance decisions** — pricing, vendor selection, business strategy, relationship calls. The AI gives a confident point estimate. You accept it because you're busy, it sounds right, and questioning it feels like unnecessary friction.

The result: the AI *replaces* your judgment instead of *augmenting* it.

### The Anti-Pattern

| What Happens | Why It's Dangerous |
|:-------------|:-------------------|
| AI recommends a price → you quote it | The AI doesn't know your gut feeling, market position, or client's willingness to pay |
| AI ranks vendors by metrics → you pick #1 | Aggregate metrics mask recent quality declines, hidden costs, and lived-experience signals |
| AI proposes a strategy → you execute it | The AI optimises for speed-to-output, not for positioning, reputation, or long-term value |

### The Fix: 3-Question Pre-Flight

Before accepting any AI recommendation on pricing, vendor selection, or strategy:

| # | Question | What It Catches |
|:--|:---------|:---------------|
| 1 | **Does this pass my gut check?** | Intuition is compressed experience. If it feels off, investigate. |
| 2 | **Would I be embarrassed if a peer saw this decision?** | Social calibration catches underpricing and bad positioning faster than analysis. |
| 3 | **Am I accepting this because I agree, or because it was convenient?** | Laziness masquerading as delegation — the most dangerous AI failure mode. |

If any answer is "no" or "I'm not sure" — **stop and reframe** before proceeding.

### When to Apply

| Apply Pre-Flight ✅ | Skip Pre-Flight (AI can decide) ❌ |
|:---------------------|:-----------------------------------|
| Pricing a project | Formatting a document |
| Choosing a vendor or service provider | Compiling research |
| Business strategy and positioning | Writing code to spec |
| Relationship and career decisions | Data analysis and visualisation |

The rule: if the decision has **high variance** (multiple reasonable answers) and is **hard to reverse** (reputation, money, health), apply the pre-flight. If the decision is **technical** (one correct answer) and **reversible** (can be undone), let the AI handle it.

> 📖 **Evidence**: [CS-006: The Replacement Trap](../examples/case_studies/CS-006-the-replacement-trap.md) — 5 concrete failures with ~$2,300 in underpricing documented.

---

## Quick Reference

```
✅ Git push after every session
✅ One feature per session
✅ Prune activeContext.md weekly
✅ Keep userContext.md stable
✅ Use /save for long sessions
✅ Review .gitignore before first push
✅ Apply the 3-Question Pre-Flight on pricing/strategy/vendor decisions
❌ Don't skip /start and /end
❌ Don't push .env or personal memory to public repos
❌ Don't /fullload unless you need deep context
❌ Don't paste entire files — point to paths
❌ Don't accept AI pricing/strategy recommendations without gut-checking
```

---

## See Also

- **[Tips](TIPS.md)** — Getting the most out of Athena
- **[Security](SECURITY.md)** — Data residency and permissions
- **[FAQ](../Athena-Public.wiki/FAQ.md)** — Common questions
- **[Your First Session](YOUR_FIRST_SESSION.md)** — Guided walkthrough
- **[CS-006: The Replacement Trap](../examples/case_studies/CS-006-the-replacement-trap.md)** — Why augmentation ≠ replacement

---

<div align="center">

**[Back to README](../README.md)**

</div>

---
description: Multi-project switchboard — view, add, switch, close, and triage active projects
created: 2026-03-09
last_updated: 2026-03-09
model: default
temperature: 0.5
tools:
  read: true
  write: true
  bash: false
  search: true
---

# /project — Project Switchboard

> **Latency Profile**: LOW (~500 tokens to display, ~200 tokens to update)
> **Core Principle**: "One board. All projects. Always current."
> **Pattern**: GSD methodology applied at the portfolio level.

## Overview

Multi-project dashboard that tracks phase, urgency, estimated value, dependencies, and next action across all active work. Manages context-switching without state loss.

### Requirements

- A `PROJECTS.md` file in your context directory (e.g., `.context/PROJECTS.md`)
- Projects separated into **Internal** (personal: health, career, learning) and **External** (clients, revenue, business)

---

## Commands

### `/project` (default — View + Triage)

1. Load `PROJECTS.md`
2. **Triage**: Sort active projects by urgency tier (🔴 → 🟠 → 🟡 → 🟢 → 🔵), break ties by EV descending
3. **Dependency check**: Skip blocked items, surface what unblocks them
4. **Cross-zone check**: If any Internal project (health, energy) is flagged as degraded, note capacity risk for External projects
5. **Output**:
   - Show **External** table first (revenue-generating), then **Internal**
   - Highlight the **top unblocked item** as "Recommended next"
   - If all 🔴/🟠 items are blocked, surface the blocker reasons
6. Update `Last triaged:` timestamp

### `/project add <name>`

Guided intake (ask each, accept one-line answers):

1. **Zone**: Internal (personal) or External (client/revenue)?
2. **Domain**: 💼 Client | 📣 Growth | 📈 Trading | ⚙️ Execution | 🔄 Maintenance | 🧠 Personal | 🏠 Life
3. **Phase**: Not Started (default) | Phase 1-4
4. **Urgency**: 🔴 TODAY | 🟠 URGENT | 🟡 This Week | 🟢 Backlog | 🔵 Someday
5. **EV**: What's the payoff? (dollar amount, "Learning", "Distribution", "Process", etc.)
6. **Next Action**: One atomic action (GTD-style)
7. **Depends On**: Any blocker or cross-project dependency? (default: —)

Append to the correct section (Internal or External) in `PROJECTS.md`. Assign `I<N>` or `E<N>` ID.

### `/project switch <ID>` (e.g., `E3`, `I1`)

1. Read `PROJECTS.md` to get project name and domain
2. Run semantic search for project-related context (if available)
3. Load relevant session logs or state files
4. **Announce switch**:
   - "Switching to: **[Project Name]** (Phase X, 🟡 This Week)"
   - Last touched: [date]
   - Related context results
5. Carry on — the agent is now in this project context

### `/project close <ID>`

1. Ask for **outcome** (one line: "Delivered, $250" or "Cancelled — scope changed")
2. Move the row from Active → Completed table with today's date and outcome
3. Ask: "Should I update urgency on any remaining projects?" (sometimes closing one project changes priority of others)

### `/project triage`

Full re-rank of all active projects:

1. For each project, ask: "Has urgency changed since last triage?" (batch — show all, accept corrections)
1b. For each dependency, ask: "Still blocked?" — clear resolved dependencies
2. Re-sort by urgency tier × EV
3. Identify **blocked** items and surface what unblocks them
4. Update `Last triaged:` timestamp

---

## PROJECTS.md Template

```markdown
# Project Switchboard

> Last triaged: [DATE]

## 🏠 Internal Projects

| # | Project | Domain | Phase | Status | Next Action | Urgency | EV | Depends On |
|---|---------|--------|-------|--------|-------------|---------|-----|------------|
| I1 | [Name] | 🏠 Life | ░░░░░ | 💤 Parked | [Next step] | 🔵 Someday | [Value] | — |

## 💼 External Projects

| # | Project | Domain | Phase | Status | Next Action | Urgency | EV | Depends On |
|---|---------|--------|-------|--------|-------------|---------|-----|------------|
| E1 | [Name] | 💼 Client | ▓░░░░ | ⏳ Active | [Next step] | 🟡 This Week | $X | — |

## ✅ Completed

| # | Project | Domain | Completed | Outcome |
|---|---------|--------|-----------|---------|
| — | [Name] | 💼 Client | [Date] | ✅ Delivered |
```

---

## Legends

### Phase Bars

| Symbol | Phase | GSD Equivalent |
|--------|-------|----------------|
| ░░░░░ | Not Started | — |
| ▓░░░░ | Phase 1 (Spec / Setup) | `design.md` drafted |
| ▓▓░░░ | Phase 2 (Executing) | `atomic-execution` in progress |
| ▓▓▓░░ | Phase 3 (Verifying) | Verify gate |
| ▓▓▓▓░ | Phase 4 (Delivering) | Handoff / ship |
| ▓▓▓▓▓ | Complete | → Move to Completed table |

### Urgency

| Tag | Meaning | Action Rule |
|-----|---------|-------------|
| 🔴 TODAY | Due today or blocking revenue | Work on this FIRST |
| 🟠 URGENT | Due within 48hrs | Queue after 🔴 |
| 🟡 This Week | Active but not time-critical | Batch when capacity available |
| 🟢 Backlog | Planned, not started | Pick up when higher tiers clear |
| 🔵 Someday | Parked ideas / nice-to-haves | Don't touch unless idle |

### Dependencies

- **`—`** = No dependency, unblocked
- **Named dependency** = Cannot advance until the named condition resolves
- **Cross-reference** (e.g., `E2 demand signal`) = Progress on another project gates this one

## Triage Rules

1. 🔴 items first (sorted by EV descending)
2. 🟠 items next
3. 🟡 items in EV order
4. 🟢 and 🔵 stay in backlog — only surface if all higher tiers are blocked or done
5. **Blocked** items: skip during triage, surface the blocker reason instead
6. **Cross-zone check**: If an Internal project (health, energy) is degraded, flag capacity risk for External projects

---

## Integration Points

- **`/start`**: Load `PROJECTS.md` in adaptive Phase 2 when the user asks about projects or "what should I work on"
- **`/end`**: Step 5 — prompt for project state updates before shutdown (advance phases, update next actions, adjust urgency, close completed projects)

## Tagging

# workflow #project #gsd #orchestration #multi-project

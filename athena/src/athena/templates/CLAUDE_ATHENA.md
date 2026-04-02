# Athena Integration

This project uses the [Athena SDK](https://github.com/winstonkoh87/Athena-Public) for session management, long-term memory, and multi-perspective reasoning.

---

## Session Workflow

### On Session Start

Run the boot sequence before beginning work:

    athena

This will:
1. Verify Core Identity and workspace integrity
2. Recall the last session's context and deferred items
3. Create a new timestamped session log
4. Initialize the Committee of Seats (COS) reasoning framework

### During Work

- Run `athena save "brief summary"` after completing meaningful chunks of work
- Save before: large refactors, schema changes, contract changes, or cross-layer modifications

### On Session End

    athena --end

This closes the session log and persists context for the next session.

---

## Committee of Seats (COS)

This project has 6 specialized review agents available in `.claude/agents/`. Use them for multi-perspective reasoning on important decisions.

### When to Use COS Agents

| Complexity | Action |
|-----------|--------|
| Simple (bug fix, small tweak) | Just do it. No committee needed. |
| Medium (new feature, refactor) | Spawn 2-3 relevant agents for input |
| Complex (architecture, security, deploy) | Convene the full committee |

### Available Agents

| Agent | Perspective | Spawn When |
|-------|------------|------------|
| `cos-strategist` | "Does this serve the goal?" | Feature proposals, prioritization, scope decisions |
| `cos-guardian` | "What could go wrong?" | Auth changes, user input handling, secret management, API security |
| `cos-operator` | "How do we build it?" | Implementation planning, task breakdown, debugging |
| `cos-architect` | "Is the structure sound?" | Schema changes, API design, layer boundary changes, tech choices |
| `cos-skeptic` | "What are we missing?" | Before shipping, after "it works" claims, edge case hunting |
| `cos-compliance` | "Should we ship this?" | Pre-merge, pre-deploy, quality gate checks |

### How to Use

For medium-complexity decisions, spawn relevant agents as a team:

```
Task: "Review this authentication change from the Guardian and Architect perspectives"
  -> cos-guardian: Security review
  -> cos-architect: Structural impact assessment
```

For complex decisions, convene the full committee and synthesize their recommendations.

---

## Athena CLI Commands

| Command | Purpose |
|---------|---------|
| `athena` | Boot session (default) |
| `athena init .` | Initialize workspace in current directory |
| `athena check` | System health check |
| `athena save "note"` | Quicksave checkpoint to session log |
| `athena --end` | Close session |
| `athena --version` | Show version |

---

## Workspace Structure

```
.framework/modules/    Core Identity and operating principles
.context/              Session logs, project state, memories
.agent/                Workflows, scripts, skills, protocols
.claude/agents/        COS review agents (Claude Code integration)
```

# Memory Bank Template

> **Purpose**: Standard format for the 5 Memory Bank files in `.context/memory_bank/`.
> **Usage**: Copy each section below into its own file. Together, they form the agent's persistent state.

---

## Overview

The Memory Bank is the agent's long-term memory, loaded on every `/start`. It consists of 5 specialized files:

| File | Purpose | Update Frequency |
|:---|:---|:---|
| `productContext.md` | Why this agent exists — mission, philosophy, positioning | Rarely (foundational) |
| `userContext.md` | Who the user is — identity, constraints, psychology | Monthly |
| `activeContext.md` | What's happening now — current focus, recent sessions | Every session |
| `systemPatterns.md` | How the system works — architecture, coding standards, patterns | As architecture evolves |
| `decisionLog.md` | Key decisions made — context, rationale, consequences | After major decisions |

---

## 1. productContext.md

```markdown
# Product Context

## Soul Purpose

[Why does this agent exist? What is it fundamentally trying to do? 1-2 sentences.]

## Core Philosophy

1. **[Principle 1]**: [Description]
2. **[Principle 2]**: [Description]
3. **[Principle 3]**: [Description]

## Key Goals

- **[Goal 1]**: [What success looks like]
- **[Goal 2]**: [What success looks like]
- **[Goal 3]**: [What success looks like]

## Product Positioning

- **External Metaphor**: [How you describe it to others]
- **Internal Reality**: [What it actually is, technically]
- **Anti-Pattern**: [What it is NOT]

## User Persona

- **Name**: [Your name]
- **Role**: [Your role/occupation]
- **Style**: [How you prefer to work — direct, detailed, visual, etc.]
```

---

## 2. userContext.md

```markdown
# User Context (Core Profile)

> **Identity**: [One-line identity statement]
> **Mission**: [One-line mission statement]
> **Last Updated**: [YYYY-MM-DD]

## 1. Core Identity Mechanics

- **Role**: [How you use the AI — tool, co-pilot, exo-cortex, etc.]
- **Key Strength**: [Your primary cognitive advantage]
- **Key Weakness**: [Your primary cognitive blind spot]
- **Operating Language**: [How you think — frameworks, protocols, stories, etc.]
- **Demographic & Context**: [Relevant background — location, currency, industry]

## 2. Active Constraints & Preferences

### [Constraint Name]
> **Rule**: [The behavioral rule]
> **Trigger**: [When it activates]
> **Action**: [What to do]

### Hardlines

- **Law #1**: [Your non-negotiable rule]
- **Law #2**: [Your next non-negotiable rule]

## 3. The Ledger (Recent Insights)

- **[Insight Name]**: [Description of a recently validated principle]

## 4. Psychological Architecture

### [Pattern Name]
- **Core Imprint**: [Description]
- **Mechanism**: [How it manifests]
- **The Fix**: [What to do about it]
```

---

## 3. activeContext.md

```markdown
# Active Context

## Session [YYYY-MM-DD]-session-[XX] ([Time of Day]): [SESSION TITLE]

- **[Topic 1]**: [What happened — decisions, actions, insights]
- **[Topic 2]**: [What happened]
- **[Topic 3]**: [What happened]

## Session Learnings

- **[Insight]**: [What was learned and why it matters]

## Active Tasks

- [ ] [Pending task 1]
- [ ] [Pending task 2]
- [x] [Completed task]

## System Status

- **Health**: [Operational status]
- **Architecture**: [Current version and configuration]

## Next Steps

- [ ] [What to do next]
- [ ] [What to do after that]

## Session Closed

**Status**: ✅ Closed
**Time**: [HH:MM Timezone]
```

---

## 4. systemPatterns.md

```markdown
# System Patterns

## Architecture

- **[Pattern Name]**: [Description of how the system is structured]
- **[Pattern Name]**: [Description]

## Coding Standards

- **[Language]**: [Standards — e.g., PEP 8, type hints required]
- **[Shell]**: [Standards — e.g., POSIX compliant, defensive programming]
- **Documentation**: [Standards — e.g., Markdown for all docs, Mermaid for diagrams]

## Core Patterns

1. **[Pattern Name]**: [Description — e.g., Search-Save-Speak Triple-Lock]
2. **[Pattern Name]**: [Description]
3. **[Pattern Name]**: [Description]

## Technical Procedures

- **Boot**: [How the system starts up]
- **Deploy**: [How changes are shipped]
- **Test**: [How correctness is verified]
```

---

## 5. decisionLog.md

```markdown
# Decision Log

## Recent Decisions

### [YYYY-MM-DD] [Decision Title]

- **Context**: [What situation prompted this decision]
- **Decision**: [What was decided]
- **Consequences**: [What changed as a result — both positive and negative]

### [YYYY-MM-DD] [Decision Title]

- **Context**: [Situation]
- **Decision**: [Action taken]
- **Consequences**: [Outcome]
```

---

## Conventions

1. **Location**: All 5 files live in `.context/memory_bank/`
2. **Boot loading**: These files are loaded automatically on `/start`
3. **activeContext.md**: Updated every session — this is the most volatile file
4. **decisionLog.md**: Append-only — never delete past decisions, only add new ones
5. **userContext.md**: Update monthly or after major psychological/strategic shifts
6. **productContext.md**: Rarely changes — only when the product's mission evolves
7. **systemPatterns.md**: Update when architecture, standards, or procedures change

---

## Tagging

# memory-bank #template #context #persistence

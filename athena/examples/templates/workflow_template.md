# Workflow Template

> **Purpose**: Standard format for creating slash-command workflows in `.agent/workflows/`.
> **Usage**: Copy this file to `.agent/workflows/[command-name].md` (e.g., `research.md` → `/research`).

---

## YAML Frontmatter (Required)

Every workflow **must** begin with YAML frontmatter enclosed in `---` delimiters:

```yaml
---
description: [One-line description of what this workflow does]
created: [YYYY-MM-DD]
last_updated: [YYYY-MM-DD]
model: default
temperature: 0.7
tools:
  read: true
  write: true
  bash: true
  search: true
---
```

### Frontmatter Fields

| Field | Required | Description |
|:---|:---|:---|
| `description` | ✅ | Short title shown in workflow listings |
| `created` | Optional | Creation date |
| `last_updated` | Optional | Last modification date |
| `model` | Optional | LLM model override (`default`, `claude-sonnet`, etc.) |
| `temperature` | Optional | Sampling temperature (0.0–1.0) |
| `tools` | Optional | Which tool categories the workflow may use |

---

## Workflow Body

### Title & Latency Profile

```markdown
# /[command] — Execution Script

> **Latency Profile**: [LOW | MEDIUM | HIGH | ULTRA-LOW]
> **Philosophy**: [One-line design rationale]
```

### Steps (Checklist Format)

Use markdown checklists for sequential execution steps:

```markdown
## Phase 1: [Name]

// turbo

- [ ] Step 1: [Description]
- [ ] Step 2: [Description]
- [ ] Step 3: [Description]
```

> **`// turbo` annotation**: When placed above a step, the agent may auto-run that step without user approval.
> **`// turbo-all` annotation**: When placed anywhere in the workflow, ALL steps may auto-run.

### Use Cases

```markdown
## Use Cases

- [When to invoke this workflow]
- [What problems it solves]
- [What the expected output looks like]
```

### Output Format

```markdown
## Output Format

[Describe the expected deliverable — structured report, file, commit, etc.]
```

---

## Example: Minimal Workflow

```markdown
---
description: Quick research on a topic using web and local sources
created: 2026-01-01
---
# /research — Execution Script

> **Latency Profile**: MEDIUM
> **Philosophy**: Depth > Speed. Exhaust local memory before hitting the web.

## Phase 1: Local Search

// turbo
- [ ] Run semantic search: `python3 Athena-Public/examples/scripts/smart_search.py "<query>" --limit 5`
- [ ] Synthesize top results into a summary

## Phase 2: Web Search

- [ ] Search the web for supplementary sources
- [ ] Cross-reference with local findings

## Phase 3: Output

- [ ] Deliver structured report with citations
- [ ] Quicksave the research summary

## Use Cases

- Deep-dive on a topic before making a decision
- Gathering evidence to support or refute a hypothesis

## Tagging

#workflow #research
```

---

## Conventions

1. **File naming**: Filename = slash command name (e.g., `deploy.md` → `/deploy`)
2. **Tagging**: End with `#workflow #[topic-tags]` for indexing
3. **Phases**: Group related steps into numbered phases
4. **Idempotency**: Workflows should be safe to re-run without side effects where possible
5. **Confirm destructive actions**: Never auto-run steps that delete data, push to production, or spend money

---

## Tagging

# workflow #template #automation

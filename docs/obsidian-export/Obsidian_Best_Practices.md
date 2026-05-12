---
type: system-knowledge
status: active
date: 2026-04-09
tags: [research, obsidian, vault, dataview]
related: [[ARCHIVE_Overview]]
rating: 9
---

# OBSIDIAN VAULT BEST PRACTICES

## Folder Structure

```
vault/
├── 00-Inbox/           # Quick captures
├── 10-Projects/        # Active projects
├── 20-Areas/          # Ongoing responsibilities
├── 30-Reference/      # Static reference
├── 40-Archive/        # Completed
├── 50-Zettelkasten/   # Atomic knowledge
├── AI/                 # AI outputs
└── CLAUDE.md           # AI contract (CRITICAL)
```

## Frontmatter Schema

```yaml
---
type: note          # concept | project | task | reference | daily
role: documentation
status: active      # active | completed | archived
date: 2025-09-17    # ISO-8601
tags: [project-name]
related: [[note]]
rating: 7           # 1-7 scale
---
```

## CLAUDE.md Contract

The single most important file for AI integration:

```markdown
# Vault Overview
This is a personal knowledge base for [domain]. 

## Conventions
- Use wikilinks [[like this]]
- Frontmatter required on all new notes
- All YAML dates use ISO-8601

## What To Do
- Create notes in appropriate folder
- Use frontmatter on every note

## What NOT Do
- Do not create new files unless asked
- Do not restructure folder hierarchy
```

## Dataview Query Patterns

```dataview
LIST FROM "Projects" WHERE status = "Active"
TABLE owner, dueDate, status FROM "Projects"
TASK WHERE !completed
```

## AI Integration Plugins

| Plugin | Purpose |
|--------|---------|
| AI Agent Sidebar | Chat with agents in sidebar |
| Smart Connections | Semantic similar note suggestions |
| Agentic Copilot | Multi-agent orchestration |

## Retrieval Architecture

1. **Keyword** (BM25) — obsidian_simple_search
2. **Metadata** — obsidian_complex_search
3. **Hybrid** — RRF fusion combining both

---

*Research: 2025-2026 Obsidian best practices*

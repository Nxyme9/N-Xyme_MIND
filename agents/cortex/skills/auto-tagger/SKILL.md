---
name: auto-tagger
description: "Auto-Tagger — extracts tags from session content: agent names, tool calls, error types, decision keywords, code topics, dates."
---

# Auto-Tagger

## Purpose
Automatically extract meaningful tags from session content to enable filtering, search, and organization of memory.

## Tag Categories

### 1. Agent Tags `[agent:<name>]`
Extract from:
- Messages prefixed with agent name (e.g., `Hephaestus:`, `Sisyphus >`)
- Tool call metadata with `_agent` field
- Session metadata (parentSessionID, agent config)
- Pattern: `/(\w+\s*-\s*\w+)\s*[:>]/` or similar
- Fallback: "unknown" for ChatGPT archive

### 2. Tool Call Tags `[tool:<name>]`
Extract from:
- Lines matching tool invocation patterns
- JSON tool call arguments with "name" or "tool" field
- Known tool prefixes: file_, search_, write_, read_, bash_, delegate_, embed_
- Count frequency: `tool:X(count:N)`

### 3. Error Tags `[error:<type>]`
Extract from:
- Exception patterns: `Error:`, `Traceback`, `panic!`, `FAIL`
- Error types: syntax, runtime, import, type, permission, timeout
- Severity levels: fatal, error, warning, info
- Count: `error:<type>(count:N)`

### 4. Decision Tags `[decision:<topic>]`
Extract from:
- "decided to", "chose", "selected", "went with", "use X instead"
- Architecture decisions: "use Rust", "switch to Python", "implement as MCP"
- Trade-off discussions: "pros/cons", "however", "but this means"
- Priority: decisions are the MOST valuable content (10x weight)

### 5. Code Topic Tags `[topic:<area>]`
Extract from:
- Code block language identifiers: ` ```python`, ` ```rust`, ` ```javascript`
- File paths mentioned: `agents/scalpel/`, `services/bash-mcp/`
- Keywords: MCP, plugin, config, embedding, memory, session, agent, tool, skill
- Domain areas: rust, python, typescript, shell, config, data, ml, infra

### 6. Date Tags `[date:<YYYY-MM>]`
Extract from:
- Session filename timestamps
- ISO date patterns in content: `2026-05-17`, `May 2026`
- File modification timestamps
- Create recency buckets: 0-7d (current), 7-30d (recent), 30-90d (aging), 90d+ (archive)

### 7. Structural Tags
- `[type:conversation]`, `[type:code]`, `[type:error]`, `[type:decision]`, `[type:plan]`, `[type:review]`
- `[source:chatgpt]`, `[source:deepseek]`, `[source:nxyme]`, `[source:opencode]`
- `[importance:1-10]` — see relevance scorer
- `[recency:d]` — days since last activity

## Tagging Protocol

```
For each chunk:
  1. Scan for agent patterns → add agent tags
  2. Scan for tool call patterns → add tool tags  
  3. Scan for error patterns → add error tags
  4. Scan for decision patterns → add decision tags
  5. Scan for code/topic patterns → add topic tags
  6. Extract dates → add date + recency tags
  7. Classify type → add type tag
  8. Tag count: deduplicate identical tags
  9. Store with chunk metadata
```

## Output Format
Each memory entry stores tags as a JSON array:
```json
{
  "tags": [
    "agent:Hephaestus",
    "tool:file_write", 
    "error:none",
    "decision:architecture-mcp",
    "topic:rust",
    "date:2026-05",
    "type:code",
    "source:nxyme",
    "importance:7",
    "recency:0d"
  ]
}
```

## NEVER
- Over-tag: max 15 tags per chunk
- Duplicate tags: always deduplicate
- Tag based on filename alone (content must confirm)
- Skip tagging: every chunk gets at minimum type + source + date

## ALWAYS
- Verify agent names against known list (agents/* in opencode.json)
- Normalize dates to YYYY-MM format
- Deduplicate within each category
- Report tag distribution stats

## Known Agent Names
Sisyphus, Hephaestus, Scalpel, Momus, Oracle, Metis, Librarian, Explore, Kairos, Jarvis, Prometheus, Mr. White, Phi-4, Vision, Cortex, Architect, Agent Builder, Sisyphus Junior, Atlas

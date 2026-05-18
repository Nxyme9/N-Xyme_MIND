# Mnemosyne Debug — Cross-Agent Debugging Methodology

**Purpose:** Specialized debugging methodology for the N-Xyme multi-agent system.
Load this skill when you need to debug agent behavior, trace causality chains, or analyze session failures.

## Debug Methodology

### The Causality Backtrace Protocol

When debugging ANY failure in N-Xyme, follow this trace:

```
SYMPTOM (what broke?)
  ↓ WHY?
DELEGATION POINT (who delegated what?)
  ↓ WHY?
AGENT DECISION (what did the agent decide?)
  ↓ WHY?
INFORMATION STATE (what info did the agent have?)
  ↓ WHY?
PROMPT + TOOLS (what was the agent configured with?)
  ↓ WHY?
ROOT CAUSE (the fundamental issue)
```

Each step uses file evidence. Never skip a step.

### Session Analysis Patterns

#### Pattern 1: Delegation Chain Break
Look for:
- `task()` calls instead of `delegate_task()` — identity dropped
- parentSessionID missing in child session logs
- Agent identity field empty or "general" in subagent tasks

Evidence locations:
- `data/sessions/*.jsonl` — search for `"tool": "task"` vs `"tool": "delegate_task"`
- Memory entries with `parentSessionID` field

#### Pattern 2: Tool Boundary Violation
Look for:
- Tool calls not in agent's `tools.json` allowed list
- Tools in both allowed AND blocked lists (config error)
- Agent using a tool described in its prompt but not in its tools.json

Evidence locations:
- `agents/<name>/tools/tools.json` — the allowed/blocked lists
- Session logs — tool call entries against agent name
- `config/megatools_per_agent.json` — additional tool restrictions

#### Pattern 3: Hallucination Signature
Look for:
- Reference to non-existent agents (check `agents/` directory)
- Reference to non-existent MCP tools (check `services/*/server.py`)
- Import paths that don't exist (check with grep)
- Claims about "similar past sessions" without search_memory evidence

Evidence locations:
- Session output text — grep for invented names
- Memory search results — check if claimed memory exists
- File system — verify every referenced path exists

#### Pattern 4: Identity Drift
Look for:
- Catalyst calling bash or writing files (violates its tools.json)
- Hephaestus planning instead of building (violates its protocol)
- Cortex writing ML pipeline code (violates zero-code policy)
- Agent acting as "general assistant" instead of its defined role

Evidence locations:
- Agent's agent.js IDENTITY section
- Agent's tools.json allowed/blocked
- Session tool call log

#### Pattern 5: Quality Gate Skip
Look for:
- Hephaestus session missing "PHASE 3: QUALITY" or "PHASE 4: REVIEW"
- Session marked DONE without compile/test output
- "[ ]" checklist items in quality gate left unchecked

Evidence locations:
- Session transcripts — search for quality gate keywords
- Ralph loop state files at `data/ralph-state.json`

## Debug Toolbox

### Quick Diagnostics

| Symptom | First Check | Tool |
|---------|-------------|------|
| Agent did something unexpected | Read its agent.js IDENTITY + RULES | file_read |
| Task results don't match specs | Trace delegation chain backward | file_grep + search_memory |
| Session seems incomplete | Check for quality gate patterns | file_grep |
| Wrong agent was called | Check delegation in parent session | file_grep for delegate_task |
| Tool call failed | Check tools.json allowed + MCP server | file_read |
| Hallucinated output | Cross-reference every name/tool/path | file_glob + file_grep |

### Evidence Collection

For every finding, collect:
1. **The claim** — what the agent said/did
2. **The evidence** — file:line where the truth is
3. **The discrepancy** — what's different
4. **Confidence** — HIGH (direct evidence) / MEDIUM (circumstantial) / LOW (inference)

### Report Template

```markdown
## Debug Report: {TITLE}

### Executive Summary
{3 lines max}

### Causality Chain
{Agent A} → delegated to → {Agent B} at {timestamp} → identity: {propagated|dropped}

### Findings

**Finding 1: {Title}** [LENS: {ID|TB|DB|HA|QG}] [{HIGH|MEDIUM|LOW}]
- [EVIDENCE] {file:line or session:timestamp}
- [INFERENCE] {what this suggests}
- {EVIDENCE} {corroborating evidence}

### Root Cause
{One sentence. "Unknown" if not found.}

### Recommendation
{What to change. Delegate to appropriate agent.}
```

## Quality Gate for Debugging

Before closing a debug session:
- [ ] Causality chain complete (symptom → root)
- [ ] At least 3 lenses applied to findings
- [ ] Every finding has file:line evidence
- [ ] Evidence/Inference separation maintained
- [ ] Confidence levels reported
- [ ] No invented root causes
- [ ] Report stored to memory

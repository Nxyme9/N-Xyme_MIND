---
name: Context Compactor
description: Summarizes and compresses conversation context to stay within token limits. Prevents context window overflow.
created: 2026-02-27
auto-invoke: false
model: default
---

# 🗜️ Context Compactor

> **Philosophy**: The best context is compressed context. Keep signal, discard noise.

## 1. The Problem

Long conversations overflow the context window, causing:

- Lost instructions from earlier in the conversation
- Degraded response quality
- Repeated mistakes (agent forgets prior decisions)

## 2. When to Trigger

- Conversation exceeds ~50 turns
- Agent starts repeating questions or forgetting decisions
- Token budget is >60% consumed
- Before starting a major new phase of work

## 3. Execution Workflow

```
STEP 1: INVENTORY
  └─ List all decisions made so far
  └─ List all files modified
  └─ List all open questions

STEP 2: COMPRESS
  └─ Summarize each topic into 1-2 sentences
  └─ Keep: decisions, file paths, error messages, user preferences
  └─ Discard: exploratory discussion, rejected approaches, verbose logs

STEP 3: CHECKPOINT
  └─ Write the compressed summary to a file:
     └─ `.context/session_checkpoint.md` (or equivalent)

STEP 4: RESET
  └─ Reference the checkpoint file instead of raw conversation history
```

## 4. Compression Template

```markdown
# Session Checkpoint — [Date]

## Decisions Made
1. [Decision] — Reason: [Why]
2. [Decision] — Reason: [Why]

## Files Modified
- `path/to/file.py` — [What changed]

## Current State
- Working on: [Current task]
- Blocked by: [If anything]

## Open Questions
- [Question 1]

## Key Constraints
- [Constraint the agent must remember]
```

## 5. Rules

- Never discard user preferences or constraints
- Always preserve file paths and error messages
- Compress reasoning chains into conclusions only
- Keep the checkpoint under 500 words

---

# skill #context-management #efficiency #memory

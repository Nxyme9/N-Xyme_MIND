---
description: "Iterative loop management — Ralph + Ultrawork — start, status, iterate, cancel"
---

Ralph Loops are persistent iterative refinement loops using frontmatter .md state
that survives restarts at `data/ralph-state/active.md`.

Sub-commands:
  - /ralph-start  — Start new loop (task, max_iterations, promise, ultrawork)
  - /ralph-status — Check loop progress (iteration, max, active, ultrawork)
  - /ralph-iterate— Manually advance loop by one iteration
  - /ralph-cancel — Cancel and clear an active loop

Ultrawork aliases:
  - /ulw-start    — Start Ultrawork loop (Oracle verification gate)
  - /ulw-status   — Check Ultrawork loop status
  - /ulw-cancel   — Cancel Ultrawork loop

Architecture:
  Plugin (.opencode/plugins/ralph-autoloop.js)
    └─ message.updated → detect <promise>TAG</promise> → handle/inject continuation
    └─ State read/write via frontmatter .md

  MCP Tools (services/megatool-mcp/server.py)
    └─ ralph_start / ralph_cancel / ralph_status / ralph_iterate
    └─ ulw_start / ulw_cancel / ulw_status (ultrawork aliases)

  State File (data/ralph-state/active.md)
    └─ Frontmatter YAML: active, session_id, iteration, max_iterations, etc.
    └─ Body: task prompt text
    └─ Survives session/plugin restarts

Promise Tags:
  - `<promise>DONE</promise>`     → Loop complete (normal) or verification phase (ultrawork)
  - `<promise>VERIFIED</promise>` → Ultrawork verification passed (Oracle confirmed)

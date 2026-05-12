---
status: ready-for-dev
implementationType: single-file
focus: Unified TUI with full MCP integration
---

# Spec: Unified TUI with Full MCP Integration

## User Goal
Build a Rich-based TUI that provides full access to all 5 MCPs (learning, memory, orchestration, intelligence, sessions).

## Requirements

### Must Have
- [ ] Rich-based interactive UI (no Textual dependency)
- [ ] MCP status panel showing 5/5 MCPs
- [ ] Learning stats display (Q-learning, Thompson Sampling)
- [ ] Memory search interface
- [ ] Task routing via intelligence MCP
- [ ] Session management

### Technical
- [ ] HTTP API client to localhost:3000
- [ ] AsyncIO for non-blocking operations
- [ ] Error handling with user feedback

## Acceptance Criteria

Given the TUI is running, when the user:
1. Starts the app → sees MCP status panel with 5/5 operational
2. Types a query → gets routed via intelligence MCP
3. Searches memory → sees semantic search results
4. Views learning → sees Q-learning stats and agent performance

Then the app works correctly.

## Files
- Output: `nx_mind_unified_tui.py`
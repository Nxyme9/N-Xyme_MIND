---
stepsCompleted: []
story_id: "1.3"
epic_num: 1
story_num: 3
story_key: "1-3-error-handling"
status: "ready-for-dev"
project_name: "N-Xyme_MIND"
date: "2026-05-16"
---

# Story 1.3: Error Handling & Graceful Degradation

Status: ready-for-dev

## Story

As a user,
I want the daemon to never crash on malformed or edge-case input,
So that the system remains operational without supervision.

## Acceptance Criteria

1. Invalid JSON returns parse error, continues accepting valid queries
2. Empty query returns EMPTY_QUERY error
3. stdin EOF exits cleanly with code 0
4. Unknown tool requests return helpful suggestions

## Tasks / Subtasks

- [ ] Add safe_run() wrapper to every tool handler
- [ ] Validate JSON parsing with error recovery
- [ ] Test edge cases: empty, malformed, unknown, EOF

## Dev Notes

- safe_run() pattern exists in main.rs via catch_unwind
- Every tool handler must return JSON-RPC error response, not panic
- Reference: data/bmad/architecture.md AD-1

## Dev Agent Record

### Agent Model Used

opencode/deepseek-v4-flash-free

### Completion Notes List

### File List

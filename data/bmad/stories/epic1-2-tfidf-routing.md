---
stepsCompleted: []
story_id: "1.2"
epic_num: 1
story_num: 2
story_key: "1-2-tfidf-routing"
status: "ready-for-dev"
project_name: "N-Xyme_MIND"
date: "2026-05-16"
---

# Story 1.2: TF-IDF Routing Engine

Status: ready-for-dev

## Story

As a user,
I want to send natural language queries and get a tool routed via TF-IDF,
So that I receive a tool match in <200μs.

## Acceptance Criteria

1. Latency for 100 consecutive valid queries never exceeds 250μs
2. Correct tool in top 5 for ≥90% of 80+ golden test cases
3. Returns tool name, confidence score, and latency_us
4. Handles ambiguous queries gracefully with fallback chain

## Tasks / Subtasks

- [ ] Integrate TF-IDF scoring into ask() tool
  - [ ] Use existing tf_score() function
  - [ ] Route tool descriptions at startup
- [ ] Benchmark latency (100 queries, p50/p95/p99)
- [ ] Validate accuracy against golden test set

## Dev Notes

- tf_score() already exists in services/nx-agents-mcp/src/main.rs
- Route tool queries via existing mojo_daemon_v1
- Reference: data/bmad/architecture.md AD-1, AD-4

## Dev Agent Record

### Agent Model Used

opencode/deepseek-v4-flash-free

### Completion Notes List

### File List

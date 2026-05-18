---
stepsCompleted: []
story_id: "1.4"
epic_num: 1
story_num: 4
story_key: "1-4-performance-metrics"
status: "ready-for-dev"
project_name: "N-Xyme_MIND"
date: "2026-05-16"
---

# Story 1.4: Performance Metrics & Logging

Status: ready-for-dev

## Story

As an operator,
I want the daemon to log every routing decision with latency and confidence,
So that I can monitor system health and identify degradation.

## Acceptance Criteria

1. Every routing decision logged with timestamp, query_hash, tool, confidence, latency_us
2. Metrics endpoint returns p50/p95/p99 latency over last 1000 queries
3. Warning emitted when confidence drops below 0.5 for ≥10% of recent queries
4. Logs survive daemon restarts

## Tasks / Subtasks

- [ ] Add routing log to data/memory/synapses/routing-stats.jsonl
- [ ] Implement metric_search tool returning latency percentiles
- [ ] Add confidence degradation warning to meta-observer

## Dev Notes

- Append-only JSONL format — same pattern as data/memory/vectors/ingest.jsonl
- Use existing data pipeline structure
- Reference: data/bmad/architecture.md AD-7, AD-1

## Dev Agent Record

### Agent Model Used

opencode/deepseek-v4-flash-free

### Completion Notes List

### File List

---
stepsCompleted: []
story_id: "1.1"
epic_num: 1
story_num: 1
story_key: "1-1-daemon-startup"
status: "ready-for-dev"
project_name: "N-Xyme_MIND"
date: "2026-05-16"
---

# Story 1.1: Daemon Startup & Lifecycle

Status: ready-for-dev

## Story

As a user,
I want the mojo-router daemon to start, load its tool set, and accept stdin/stdout connections,
So that I can route queries immediately without manual setup.

## Acceptance Criteria

1. Daemon responds to a status query within 1 second
2. Process stays resident using <10MB RAM
3. 25-tool lexicon loaded at startup
4. stdin/stdout JSON-L IPC active and responsive

## Tasks / Subtasks

- [ ] Implement daemon startup
  - [ ] Load 25-tool lexicon from embedded definitions
  - [ ] Open stdin for JSON-L input
  - [ ] Respond to {"type": "status"} within 1s
- [ ] Memory management
  - [ ] Verify process stays under 10MB RAM
  - [ ] Clean shutdown on EOF

## Dev Notes

- Builds on existing mojo_daemon_v1 at bins/mojo_daemon_v1
- Mojo 1.0.0b1 compiler at /tmp/mojo_venv/
- Persistent stdin listener pattern from existing implementation
- Architecture reference: data/bmad/architecture.md AD-1, AD-4

## Dev Agent Record

### Agent Model Used

opencode/deepseek-v4-flash-free

### Completion Notes List

### File List

# Sprint 4 — Integration Plan

> **Generated**: 2026-04-03 | **Status**: Ready to Execute

---

## Task 1: CATALYST Integration

### Current State
- BMAD workflows exist in `_bmad/catalyst/workflows/`
- 3 workflows: `bmad-catalyst-chain`, `bmad-memory`, `bmad-resilience`
- Each has SKILL.md defining how to use

### What's Missing
- No bridge from OpenCode to BMAD workflows
- Workflows not registered as skills
- No integration documentation

### Deliverables
1. `docs/CATALYST-INTEGRATION.md` - How to use CATALYST from N-Xyme_MIND
2. Update `skills/` configuration to include BMAD workflows
3. Create `bin/catalyst-run` wrapper script

---

## Task 2: VPN Rotator Automation

### Current State
- `vpn/rotator.py` works as SOCKS5 proxy
- `--list` shows available configs (none downloaded yet)
- No auto-rotation on rate limits

### What's Missing
- Auto-rotate on 429 detection
- Health check integration
- systemd timer for periodic checks

### Deliverables
1. Update `vpn/rotator.py` with auto-rotate logic
2. Add health check triggers for VPN rotation
3. Create `bin/vpn-rotate` command

---

## Task 3: Trigger Engine Automation

### Current State
- `src/trigger_engine.py` has base class
- `triggers.json` has action registry
- Added handlers: clean_stale_sessions, clear_db_lock, force_gc, throttle_ollama

### What's Missing
- Triggers not wired to scripts
- No systemd timer integration
- No health check triggers

### Deliverables
1. Wire triggers.json to bin/health-*.sh scripts
2. Add trigger timer (30min heartbeat)
3. Create `bin/trigger-status` command

---

## Task 4: BMAD Workflow Integration

### Current State
- BMAD workflows exist in `_bmad/`
- Not integrated into main system
- No documentation on how to use

### What's Missing
- BMAD workflow documentation
- Usage examples
- Integration with main system

### Deliverables
1. Update `docs/BMAD-WORKFLOWS.md` with usage guide
2. Create example workflow runs

---

## Task 5: Integration Tests

### Current State
- Quality gates exist in `bin/quality-gates/`
- No integration test suite

### What's Missing
- Test suite for MCP connections
- Test suite for agent chains
- Test suite for VPN/rotation

### Deliverables
1. Create `tests/integration/` directory
2. Add MCP connection tests
3. Add agent chain tests

---

## Execution Order

| Order | Task | Est. Time |
|-------|------|-----------|
| 1 | CATALYST Integration | 2h |
| 2 | VPN Rotator Automation | 2h |
| 3 | Trigger Engine Automation | 2h |
| 4 | BMAD Workflow Integration | 1h |
| 5 | Integration Tests | 3h |

---

*Sprint 4 Plan v1.0 | N-Xyme_MIND*
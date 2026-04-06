# Trigger Engine — Gap Analysis

> **Generated**: 2026-04-03 | **Status**: Analysis Complete

---

## Summary

| Category | Count |
|----------|-------|
| Missing Handlers | 5 |
| Partial Implementations | 4 |
| Working Correctly | 10+ |

---

## Detailed Gap Analysis

### Missing Handlers (Not Implemented)

| Trigger/Action | Defined In | Status | Impact |
|----------------|-----------|--------|--------|
| `gpu_heartbeat.throttle_ollama` | triggers.json | ❌ Missing module | GPU throttling won't work |
| `gpu_heartbeat.force_gc` | triggers.json | ❌ Stub only | No actual VRAM cleanup |
| `heartbeat.clean_stale_sessions` | triggers.json | ❌ Missing function | Stale sessions accumulate |
| `heartbeat.clear_db_lock` | triggers.json | ❌ Missing function | Database locks may persist |
| `diagnose` (tool calling) | triggers.json | ❌ Not implemented | Auto-diagnosis broken |

### Wrong Module References

| Trigger | Expected Module | Actual Module | Fix |
|---------|-----------------|---------------|-----|
| `check_model` | `gpu_heartbeat.check_embedding` | `direct_health.py` | Update reference |

### Partial Implementations (Exist but Incomplete)

| Action | Current Behavior | Needed |
|--------|------------------|--------|
| `alert` | Logs only | Use message param, send notification |
| `quarantine` | Logs only | Move service to quarantine dir |
| `force_gc` | Logs only | Actually invoke garbage collection |
| `throttle_ollama` | Logs warning | Reduce Ollama concurrency |

### Working Correctly ✓

- `rotate_vpn` — VPN rotation on 429
- `rotate_api_key` — API key rotation
- `verify_all` — Health verification
- `pull_model` — Ollama model pull
- `restart_graphiti` — Graphiti restart
- Velocity/consciousness/memory handlers

---

## Root Cause

The JSON specifies handler paths (e.g., `gpu_heartbeat.throttle_ollama`) but `trigger_router.py` uses **type-based dispatch** — it looks up `action_type` and calls `_handle_*_event()`. The handler references in JSON are **dead code** — stored but never used.

---

## Activation Plan

### Phase 1: Critical Fixes (Must Have)

| Priority | Fix | Est. Time |
|----------|-----|-----------|
| P0 | Add `clean_stale_sessions` to heartbeat | 30min |
| P0 | Add `clear_db_lock` to heartbeat | 30min |
| P1 | Implement actual `force_gc` | 1h |
| P1 | Implement `throttle_ollama` | 1h |

### Phase 2: Enhancement (Should Have)

| Priority | Fix | Est. Time |
|----------|-----|-----------|
| P2 | Fix module references | 15min |
| P2 | Implement `quarantine` action | 1h |
| P3 | Implement `diagnose` tool | 2h |

---

## Files to Modify

1. `src/trigger_engine.py` — Add missing handler functions
2. `src/trigger_router.py` — Wire handlers to triggers
3. `bin/health-l2-vitals.sh` — Integrate with trigger engine

---

*Gap Analysis v1.0 | N-Xyme_MIND*

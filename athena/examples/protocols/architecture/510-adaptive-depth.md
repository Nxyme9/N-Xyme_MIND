# Protocol 510: Adaptive Depth

> **Category**: Architecture  
> **Created**: 2026-03-04  
> **Status**: Active  
> **Dependencies**: **P133 JIT Routing**, [P508 Intent Classifier](508-intent-classifier.md)

## Principle

**Default lean. Escalate on demand. Robustness is a per-query budget proportional to blast radius.**

The system optimizes for the 80% of interactions that are low-stakes (SNIPER/STANDARD). Deep reasoning is always available — but opt-in, not default.

## The Tradeoff

```
Too Robust  → Latency tax on every interaction. User dreads /start and /end.
Too Efficient → Shallow output, missed context, AI slop.
```

The solution is **not** a fixed midpoint. It is a **user-controlled dial**:

| Mode | Robustness | Latency | When to Use |
|------|-----------|---------|-------------|
| Default (JIT) | Minimal — identity + on-demand loading | <2s boot, ~2K tokens | 80% of interactions |
| `/think` | L4 depth + Output Standards | +2K tokens | Important decisions, $10K+ stakes |
| `/ultrathink` | Full stack + Triple Crown + Adversarial QA | +28K tokens | Irreversible decisions, life-altering |
| `/refactor` | Deep audits, integrity scans, orphan detection | Minutes | Periodic maintenance |

## Classification Heuristic

**Latency should be proportional to the blast radius of skipping the check.**

| Check Type | Blast Radius | Treatment |
|-----------|-------------|-----------|
| Identity verification | System-bricking | **Hard gate** — must be sequential |
| Session creation | Data loss | **Hard gate** — must be sequential |
| Semantic memory prime | Slightly worse recall | **Soft gate** — parallel, fail silently |
| Health check | Degraded but functional | **Background** — fire and forget |
| Search cache warmth | 200ms slower on first query | **Removed** — not worth boot cost |

## Rules

1. **The user holds the dial.** The Λ classifier suggests depth; the user overrides with `/think` or `/ultrathink`.
2. **Gating checks must justify their latency.** If skipping a check doesn't risk ruin, it belongs in the background thread pool.
3. **Non-fatal failures are non-blocking.** Push timeouts, semantic prime failures, and health check issues log warnings but do not abort boot or shutdown.
4. **Periodic maintenance absorbs deferred checks.** Checks removed from `/start` and `/end` live in `/refactor` — they still run, just not on every session.

## Anti-Patterns

- **Robustness Theater**: Running 6 sequential checks that each "only take 5 seconds" = 30s boot for no survival benefit.
- **Efficiency Drift**: Removing checks because each one "only saves 2 seconds" until nothing validates anything.
- **Fixed Midpoint Fallacy**: Treating robustness as a global setting instead of a per-query budget.

## Implementation

This protocol is enforced structurally:

- **Boot** (`orchestrator.py`): Hard gates (identity, session) run sequentially. Everything else runs in `ThreadPoolExecutor(max_workers=8)`.
- **Shutdown** (`shutdown.py`): Git commit is inlined (no subprocess). Push is non-fatal with 30s timeout. Compliance is inlined. Hygiene runs in background.
- **Query routing** (P133 + P508): Λ score determines depth. SNIPER (<10) skips search. STANDARD (10-30) runs Triple-Lock. ULTRA (>30) activates full reasoning stack.

## References

- **Protocol 133: JIT Routing**
- [Protocol 508: Intent Classifier](508-intent-classifier.md)
- [WORKFLOWS.md](../../../docs/WORKFLOWS.md) — Escalation ladder reference

---

## Tagging

# protocol #architecture #performance #adaptive-depth

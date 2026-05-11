# N-Xyme_MIND: Top 5 ROI Moves - Synthesized Plan

## Executive Summary

Based on party mode discussion with Winston (Architect), Mary (Analyst), and Amelia (Developer), the following 5 ROI moves are prioritized. All are implementable with existing infrastructure patterns.

---

## Priority Order

### 1. LRU Context Cache (HIGH ROI - Quick Win)

**What**: Add LRU cache with TTL for distilled context in brain_mcp  
**Location**: `packages/brain_mcp/namespaces/context.py`  
**Impact**: 40-60% latency reduction on recurring queries  
**Implementation**:
- Add `functools.lru_cache` or custom TTL cache for `context_get_style_context()`
- Cache distilled fingerprint patterns with 5-minute TTL
- Reuse existing context retrieval patterns

**Effort**: 1-2 hours

---

### 2. Smart Fallback Orchestration (HIGH ROI)

**What**: Analyze error type and route to correct fallback instead of generic fallback  
**Location**: `packages/brain_mcp/namespaces/tunnel.py`  
**Impact**: Higher success rate on degraded providers  

**Current**: Generic fallback triggered on any 5xx/auth error  
**Enhanced**: Map error codes to specific fallbacks:
- 429 (rate limit) → rotate key + retry with backoff
- 401/403 (auth) → switch provider, don't fallback to local
- 502/503 (server) → retry with different endpoint, then fallback
- Timeout → fallback to local, but log for pattern analysis

**Effort**: Half day

---

### 3. Time-of-Day Pre-Spawn (HIGH ROI)

**What**: Learn when user works and pre-warm relevant agents  
**Location**: `packages/orchestration/pre_warm.py` + `packages/brain_mcp/namespaces/fingerprint.py`  
**Impact**: Eliminate 200-500ms agent spawn latency during FLOW state  

**Implementation**:
- Track hourly spawn patterns in fingerprint
- On startup, check time → pre-warm top 2-3 likely agents
- Already exists: `AgentPreWarmer.pre_warm_auto()` - just need to call on startup

**Effort**: 1-2 hours (mostly configuration)

---

### 4. Proactive Cost Alerts (MEDIUM ROI)

**What**: Alert before budget exhaustion with smart recommendations  
**Location**: Frontend dashboard enhancement + backend endpoint  
**Impact**: Direct cost reduction through early intervention  

**Implementation**:
- Add threshold config (50%, 80%, 95%)
- Create `/api/tunnel/budget` endpoint returning current spend + projection
- Frontend: Add alert banner when threshold crossed
- Add recommendation: "Switch to haiku for L1 tasks? Save 60%"

**Effort**: Half day

---

### 5. Task Success Rate Trends (MEDIUM ROI)

**What**: Dashboard showing which agent types/patterns succeed over time  
**Location**: Frontend dashboard (`/app/dashboard/page.tsx`) + learning_engine  
**Impact**: Improves adoption through visible wins + data-driven behavior  

**Implementation**:
- Extend `/api/learning/outcomes` with agent_type grouping
- Add trend chart: success rate over 7d/30d by agent
- Already has data via `learningOutcomes` - just aggregate and display

**Effort**: 2-3 hours

---

## Implementation Sequence

| # | Task | Effort | Dependencies |
|---|------|--------|--------------|
| 1 | LRU Context Cache | 1-2hr | None |
| 2 | Time-of-Day Pre-Spawn | 1-2hr | None (uses existing) |
| 3 | Smart Fallback | Half day | None |
| 4 | Cost Alerts | Half day | None |
| 5 | Success Trends | 2-3hr | None |

**Recommendation**: Start with #1 and #2 (both quick wins), then #3, then #4/#5 in parallel.

---

## Key Files Reference

| Component | File |
|-----------|------|
| Context cache | `packages/brain_mcp/namespaces/context.py` |
| Tunnel fallback | `packages/brain_mcp/namespaces/tunnel.py` |
| Pre-warm | `packages/orchestration/pre_warm.py` |
| Fingerprint | `packages/brain_mcp/namespaces/fingerprint.py` |
| Dashboard | `frontend/src/app/dashboard/page.tsx` |
| Learning outcomes | `frontend/src/app/api/learning/outcomes/route.ts` |

---

## Success Metrics

- **Cache hit rate**: Target 40%+ on repeated queries
- **Fallback success**: Target 90%+ success when primary fails
- **Pre-spawn latency**: Target <100ms for warmed agents
- **Cost alerts**: Track budget % at time of alert vs actual exhaustion
- **Success trends**: Track user behavior changes based on insights
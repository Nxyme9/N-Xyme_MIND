# FULL-PLAN.md - Audit, Gap Analysis & Red-Team Report

**Date:** 2026-04-17  
**Status:** AUDIT COMPLETE

---

## 1. FEASIBILITY AUDIT

### ✅ Existing Infrastructure (Compatible)

| Component | Existing | Plan Alignment |
|-----------|----------|-----------------|
| Hooks (16 files) | `useChat`, `useOrchestration`, `useMemory`, `useTunnelBudget` | ✅ Compatible with new hooks |
| UI Components (21 files) | `save-indicator`, `switch`, `toast`, `dialog` | ✅ Can extend existing |
| Stores (5 files) | Zustand stores | ✅ Pattern matches |
| Styling | Tailwind CSS v4 | ✅ Plan uses CSS variables |
| API Routes | Next.js API routes | ✅ 5 endpoints align |

### ⚠️ Gap: No Existing Pattern Match
- `useCognitiveState` - NEW hook, no direct pattern
- `useMassiveUndo` - NEW hook, no direct pattern  
- `TaskScaffold` - NEW component structure
- `scaffolding/` directory - DOES NOT EXIST

---

## 2. GAP ANALYSIS

### ❌ Missing from Plan

| Gap | Impact | Severity |
|-----|--------|-----------|
| No mobile responsive breakpoints | DAWN mode unusable on mobile | HIGH |
| No offline capability | Auto-save fails offline | MEDIUM |
| No dark/light theme toggle per state | Hardcoded colors per state | MEDIUM |
| "Handshake" concept not in stories | Victor's innovation unused | MEDIUM |
| Cognitive bandwidth detection algorithm undefined | Dr. Quinn's pattern vague | HIGH |
| IndexedDB setup not specified | Massive Undo may fail | HIGH |
| Test strategy undefined | No way to verify acceptance | HIGH |
| Migration path from current state unspecified | May lose existing user data | MEDIUM |

### ⚠️ Ambiguous Items

1. **Cognitive bandwidth detection** - How is it measured? (reaction time? error rate? self-report?)
2. **Focus Shield queue** - What triggers queue? All notifications? Error toasts?
3. **Calm Mode** - What happens when 25 min ends? Auto-exit or pause?

---

## 3. RED-TEAM FINDINGS

### 🔴 CRITICAL RISKS

| Risk | Scenario | Mitigation |
|------|----------|------------|
| **State conflict** | SURGE/DRIFT/DAWN overrides user preference during active chat | Add "manual mode" override |
| **Undo data explosion** | 50 states × 100KB = 5MB IndexedDB bloat | Add storage cleanup, warn at 80% |
| **API endpoint does not exist** | `/api/tunnel/status` not in codebase | Create backend endpoint first |

### 🟠 MAJOR RISKS

| Risk | Scenario | Mitigation |
|------|----------|------------|
| **Scope creep** | "Max 5 features per layer" easily exceeded | Strict enforcement, quarterly review |
| **Accessibility gap** | No screen reader test for DAWN mode | Add a11y testing in Sprint 6 |
| **Performance regression** | Cognitive state check on every render | Cache state, debounce checks |
| **Memory MCP timeout** | `get_full_injected_context()` 2s timeout | Don't call on every render |

### 🟡 MINOR RISKS

- Color contrast in DAWN mode may fail WCAG AA
- Calm Mode timer needs background handling (Web Worker?)
- Tunnel status needs real-time update (WebSocket?)

---

## 4. RECOMMENDATIONS

### Must Fix Before Sprint 1

1. ✅ **Define cognitive bandwidth detection** - Add explicit measurement method
2. ✅ **Create backend endpoint** `/api/tunnel/status` before Story 4.2
3. ✅ **Add IndexedDB schema** - Define before Story 3.2

### Should Fix Before Implementation

4. Add mobile responsive breakpoints
5. Add offline detection and graceful degradation
6. Add test strategy (unit + E2E)

### Nice to Have (Post-MVP)

7. "Handshake" concept integration into chat flow
8. Web Worker for Calm Mode timer

---

## 5. UPDATED READINESS

| Area | Before | After |
|------|--------|-------|
| UX Design | ✅ COMPLETE | ⚠️ Mobile gap |
| Architecture | ✅ COMPLETE | ⚠️ API endpoints missing |
| Epics & Stories | ✅ COMPLETE | ⚠️ Detection algorithm undefined |
| Sprint Planning | ✅ COMPLETE | ✅ OK |

**Revised Status: ⚠️ CONDITIONALLY READY**

**Required Actions:**
1. Define cognitive bandwidth detection (HIGH priority)
2. Verify/create `/api/tunnel/status` endpoint
3. Add IndexedDB schema specification

---

*Audit completed via Ralph Loop*
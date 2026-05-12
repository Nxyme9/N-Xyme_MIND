# N-Xyme MIND Frontend Overhaul - Full Plan

**Project:** ADHD-Friendly, Industry Gold Standard Frontend  
**Date:** 2026-04-17  
**Total Story Points:** 32  
**Duration:** 6 Sprints

---

## 1. Project Vision

**Goal:** Create an industry gold standard, bulletproofed, frictionless, ADHD-friendly frontend for N-Xyme MIND.

### Key Requirements
- Three-mode visual language (SURGE/DRIFT/DAWN)
- The "Handshake" approval paradigm - AI presumes, human confirms
- Cognitive bandwidth detection
- Progressive disclosure scaffolding
- Remove dictation from home (keep in chat only)
- Unified provider selector (OpenRouter + GGUF + Free)

---

## 2. Visual States Design

### State Mapping (Clarified)
| Visual State | Orchestration State | Description |
|--------------|---------------------|-------------|
| **SURGE** | FLOW | High bandwidth - cockpit-dense UI, multi-panel |
| **DRIFT** | FRICTION | Normal attention - curated single-panel |
| **DAWN** | ADAPT | Low bandwidth - simple chunky UI |

### Color Tokens

**SURGE (High Bandwidth):**
- Background: `#1a1a2e` (Dark Charcoal)
- Primary Accent: `#00d9ff` (Electric Teal)
- Surface: `#16213e`
- Text: `#e4e4e7`

**DRIFT (Medium Bandwidth):**
- Background: `#2d3748` (Warm Slate)
- Primary Accent: `#9f7aea` (Amethyst)
- Surface: `#1a202c`
- Text: `#e2e8f0`

**DAWN (Low Bandwidth):**
- Background: `#fdfbf7` (Creamy Ivory)
- Primary Accent: `#fc8181` (Soft Coral)
- Surface: `#fffaf0`
- Text: `#2d3748`

### Motion System
- Enter: 250ms ease-out
- Exit: 350ms ease-in
- Hover: 150ms instant
- NO infinite animations that steal focus
- Attention anchors: ripple, progress line, shimmer sweep

---

## 3. Progressive Disclosure

### Layer Definition

| Layer | Name | Content | Trigger |
|-------|------|---------|---------|
| 1 | **Horizon View** | 3 dots (completed/current/upcoming) | Always visible |
| 2 | **Path Unfolds** | Shows what needs done | User clicks dot |
| 3 | **Work Surface** | Full workspace | User expands task |

### Reveal Rules
- Forward reveal: User action required
- Backward collapse: Allowed, state preserved
- Max features per layer: 5

---

## 4. ADHD Safety Net

### Auto-Save
- Indicator: "Saved 💾" (bottom-right)
- Backend: localStorage
- Scope: Last 50 keystrokes
- Trigger: 2-second debounce

### Massive Undo
- History: Last hour visible
- Backend: IndexedDB
- Max states: 50
- UI: Floating undo button

### Focus Shield
- One notification at a time
- Calm Mode toggle (25-min pomodoro)
- Visual dimming for non-active areas

### Never Blank Page
- Always 3-5 suggestion chips
- "I don't know" path with recent activity

---

## 5. Re-Entry Experience

### State Restoration
- Full visual state (theme, scroll position, input)
- "Catch up" 3-bullet digest
- Progress % always visible

---

## 6. Component Inventory

| Component | Purpose | Sprint |
|-----------|---------|--------|
| CognitiveStateToggle | SURGE/DRIFT/DAWN switch | 1 |
| TaskScaffold | Progressive disclosure container | 2 |
| LayerReveal | Animation for layers | 2 |
| AutoSaveIndicator | Save status display | 3 |
| MassiveUndoButton | Undo floating action | 3 |
| FocusShield | Notification queue | 3 |
| CalmModeToggle | Pomodoro timer | 3 |
| UnifiedProviderSelector | Model picker | 4 |
| TunnelStatus | API key indicator | 4 |
| MemorySearchUI | Session recall | 5 |
| QLearningStats | Routing visualization | 5 |

---

## 7. Architecture - API Boundaries

### Frontend → Backend
- `GET /api/models` - Unified model list
- `GET /api/tunnel/status` - Active key indicator
- `POST /api/cognitive-state` - State persistence
- `GET /api/memory/search` - Memory search
- `GET /api/sessions/recall` - Session recall

---

## 8. Epics & Stories

### Epic 1: Visual Foundation (8 points)

**Story 1.1: CSS Variables for Cognitive States**
- Files: frontend/src/app/globals.css
- Acceptance: Color tokens and motion tokens defined

**Story 1.2: Cognitive State Hook**
- Files: frontend/src/hooks/useCognitiveState.ts
- Acceptance: Hook with FLOW/FRICTION integration

**Story 1.3: State Toggle Component**
- Files: frontend/src/components/cognitive-state-toggle.tsx
- Acceptance: Three states render correctly

---

### Epic 2: Progressive Disclosure (5 points)

**Story 2.1: TaskScaffold Container**
- Files: frontend/src/components/scaffolding/task-scaffold.tsx
- Acceptance: Three layers render in order

**Story 2.2: LayerReveal Animation**
- Files: frontend/src/components/scaffolding/layer-reveal.tsx
- Acceptance: Animations work correctly

---

### Epic 3: ADHD Safety Net (10 points)

**Story 3.1: Auto-Save System**
- Files: frontend/src/hooks/useAutoSave.ts
- Acceptance: 2-second debounce, localStorage

**Story 3.2: Massive Undo**
- Files: frontend/src/hooks/useMassiveUndo.ts
- Acceptance: Last hour visible, 50 states

**Story 3.3: Focus Shield**
- Files: frontend/src/components/focus-shield.tsx
- Acceptance: One notification at a time

**Story 3.4: Calm Mode Toggle**
- Files: frontend/src/components/calm-mode-toggle.tsx
- Acceptance: 25-min timer works

---

### Epic 4: Provider Unification (5 points)

**Story 4.1: Unified Provider Selector**
- Files: frontend/src/app/settings/page.tsx
- Acceptance: 11 models selectable

**Story 4.2: Tunnel Status Display**
- Files: frontend/src/components/tunnel-status.tsx
- Acceptance: Shows active API key

---

### Epic 5: Memory Integration (4 points)

**Story 5.1: Memory Search UI**
- Files: frontend/src/app/memory/page.tsx
- Acceptance: Search works

**Story 5.2: Q-Learning Stats Display**
- Files: frontend/src/components/qlearning-stats.tsx
- Acceptance: Stats visible

---

## 9. Sprint Plan

| Sprint | Name | Duration | Focus |
|--------|------|----------|-------|
| 1 | Visual Foundation | Week 1 | CSS Variables, Cognitive State Hook, Toggle Component |
| 2 | Progressive Disclosure | Week 2 | TaskScaffold, LayerReveal |
| 3 | ADHD Safety Net | Week 3 | AutoSave, MassiveUndo, FocusShield, CalmMode |
| 4 | Provider Unification | Week 4 | UnifiedSelector, TunnelStatus |
| 5 | Memory Integration | Week 5 | MemorySearch, QLearningStats |
| 6 | Polish & Verify | Week 6 | Animation tuning, Accessibility, Performance |

---

## 10. Success Metrics

| Metric | Target |
|--------|--------|
| Time-to-first-action | < 2 seconds |
| Task completion rate (DAWN mode) | > 80% |
| Progressive disclosure layers | SURGE: 3, DRIFT: 2, DAWN: 1 |

---

## 11. Implementation Readiness

| Area | Status |
|------|--------|
| UX Design | ✅ COMPLETE |
| Architecture | ✅ COMPLETE |
| Epics & Stories | ✅ COMPLETE |
| Sprint Planning | ✅ COMPLETE |

**Overall: ✅ READY FOR IMPLEMENTATION**

---

*Generated from Party Mode (Sally, Victor, Dr. Quinn), Metis gap analysis, Momus adversarial review*
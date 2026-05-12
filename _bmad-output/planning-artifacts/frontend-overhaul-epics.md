---
epicsCompleted: []
inputDocuments:
  - "_bmad-output/planning-artifacts/adhd-friendly-frontend-ux-spec.md"
  - "_bmad-output/planning-artifacts/frontend-overhaul-architecture.md"
---

# Epics and Stories: ADHD-Friendly Frontend Overhaul

**Project:** N-Xyme MIND Frontend Overhaul  
**Date:** 2026-04-17

---

## Epic 1: Visual Foundation

**Goal:** Implement three-mode visual language (SURGE/DRIFT/DAWN)

### Story 1.1: CSS Variables for Cognitive States
- **Priority:** P0 (Critical)
- **Description:** Add CSS custom properties for SURGE, DRIFT, DAWN color tokens
- **Files:** frontend/src/app/globals.css
- **Acceptance:**
  - --cognitive-surge: #1a1a2e, --cognitive-drift: #2d3748, --cognitive-dawn: #fdfbf7 defined
  - Motion tokens: --enter-250ms, --exit-350ms, --hover-150ms added

### Story 1.2: Cognitive State Hook
- **Priority:** P0 (Critical)
- **Description:** Create useCognitiveState hook with FLOW/FRICTION/ADAPT integration
- **Files:** frontend/src/hooks/useCognitiveState.ts
- **Acceptance:**
  - Hook returns current mode (SURGE/DRIFT/DAWN)
  - Integration with CATALYST orchestrator states
  - localStorage persistence works

### Story 1.3: State Toggle Component
- **Priority:** P0 (Critical)
- **Description:** Create CognitiveStateToggle component
- **Files:** frontend/src/components/cognitive-state-toggle.tsx
- **Acceptance:**
  - Three visual states render correctly
  - Manual toggle switches modes
  - URL param sync for sharing

---

## Epic 2: Progressive Disclosure

**Goal:** Implement three-layer scaffolding

### Story 2.1: TaskScaffold Container
- **Priority:** P0 (Critical)
- **Description:** Create ProgressiveDisclosure container component
- **Files:** frontend/src/components/scaffolding/task-scaffold.tsx
- **Acceptance:**
  - Three layers render in order
  - Layer 1: Horizon View (3 dots)
  - Layer 2: Path Unfolds (task list)
  - Layer 3: Work Surface (full workspace)

### Story 2.2: LayerReveal Animation
- **Priority:** P1 (High)
- **Description:** Implement reveal animations for each layer
- **Files:** frontend/src/components/scaffolding/layer-reveal.tsx
- **Acceptance:**
  - Enter: 250ms ease-out, Exit: 350ms ease-in
  - Attention anchors work (ripple, progress line, shimmer)
  - Backward collapse preserves state

---

## Epic 3: ADHD Safety Net

**Goal:** Implement auto-save, undo, focus shield, calm mode

### Story 3.1: Auto-Save System
- **Priority:** P0 (Critical)
- **Description:** Create useAutoSave hook with debounce
- **Files:** frontend/src/hooks/useAutoSave.ts
- **Acceptance:**
  - 2-second debounce on save
  - localStorage persistence
  - "Saved 💾" indicator displays

### Story 3.2: Massive Undo
- **Priority:** P0 (Critical)
- **Description:** Create useMassiveUndo hook with IndexedDB
- **Files:** frontend/src/hooks/useMassiveUndo.ts
- **Acceptance:**
  - Last hour visible in history
  - 50 states max stored
  - Floating undo button works

### Story 3.3: Focus Shield
- **Priority:** P1 (High)
- **Description:** Create FocusShield notification queue component
- **Files:** frontend/src/components/focus-shield.tsx
- **Acceptance:**
  - One notification at a time
  - Queue processes sequentially
  - Visual dimming on non-active areas

### Story 3.4: Calm Mode Toggle
- **Priority:** P1 (High)
- **Description:** Create CalmMode toggle with 25-min Pomodoro
- **Files:** frontend/src/components/calm-mode-toggle.tsx
- **Acceptance:**
  - Timer starts/stops correctly
  - Visual indicator shows mode
  - Persists across sessions

---

## Epic 4: Provider Unification

**Goal:** Unified selector with tunnel status

### Story 4.1: Unified Provider Selector
- **Priority:** P0 (Critical)
- **Description:** Refactor settings provider selector for OpenRouter/GGUF/Free
- **Files:** frontend/src/app/settings/page.tsx
- **Acceptance:**
  - All 11 models selectable (3 free, 5 premium, 3 local)
  - Category filtering works
  - Persists selection

### Story 4.2: Tunnel Status Display
- **Priority:** P1 (High)
- **Description:** Create tunnel-status indicator component
- **Files:** frontend/src/components/tunnel-status.tsx
- **Acceptance:**
  - Shows active API key index (1-6)
  - Visual indicator in header
  - Updates on rotation

---

## Epic 5: Memory Integration

**Goal:** Expose memory search and Q-Learning stats

### Story 5.1: Memory Search UI
- **Priority:** P2 (Medium)
- **Description:** Create MemorySearchUI to expose brain_mcp namespace
- **Files:** frontend/src/app/memory/page.tsx
- **Acceptance:**
  - Search input accepts queries
  - Results display correctly
  - Session filtering works

### Story 5.2: Q-Learning Stats Display
- **Priority:** P2 (Medium)
- **Description:** Create QLearningStats visualization component
- **Files:** frontend/src/components/qlearning-stats.tsx
- **Acceptance:**
  - Routing improvement trends display
  - Agent performance visible
  - Updates in real-time

---

## Story Point Summary

| Epic | Stories | Total Points |
|------|---------|---------------|
| 1: Visual Foundation | 3 | 8 |
| 2: Progressive Disclosure | 2 | 5 |
| 3: ADHD Safety Net | 4 | 10 |
| 4: Provider Unification | 2 | 5 |
| 5: Memory Integration | 2 | 4 |
| **TOTAL** | **13** | **32** |

---

*Generated from UX spec and Architecture spec*
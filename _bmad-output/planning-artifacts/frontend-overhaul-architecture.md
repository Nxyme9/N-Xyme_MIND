---
stepsCompleted: [1]
inputDocuments:
  - "_bmad-output/planning-artifacts/adhd-friendly-frontend-ux-spec.md"
workflowType: 'architecture'
project_name: 'N-Xyme Frontend Overhaul'
user_name: 'N-Xyme'
date: '2026-04-17'
---

# Architecture Decision Document

**Project:** N-Xyme MIND ADHD-Friendly Frontend Overhaul  
**Author:** N-Xyme  
**Date:** 2026-04-17

---

## Step 1: Project Context

### Input Documents
- UX Design Specification: `adhd-friendly-frontend-ux-spec.md`

### System Overview
- **Framework:** Next.js 16.2.3 + React 19.2.4
- **Styling:** Tailwind CSS v4 with custom theme
- **State:** Zustand + TanStack Query
- **MCPs:** brain_mcp, nx_delegate, CATALYST orchestrator

---

## Step 2: Visual State System Architecture

### State Mapping
| Visual State | Orchestration State | Trigger |
|--------------|---------------------|---------|
| SURGE | FLOW (catalyst) | User toggle or auto-detect high activity |
| DRIFT | FRICTION | Default state |
| DAWN | ADAPT | User toggle or low bandwidth detected |

### Implementation
```typescript
// frontend/src/hooks/useCognitiveState.ts
interface CognitiveState {
  mode: 'SURGE' | 'DRIFT' | 'DAWN';
  persistence: 'url' | 'localStorage';
  conflictResolution: 'user' | 'last-write-wins';
}

// CSS Variables in globals.css
:root {
  --cognitive-surge: #1a1a2e;
  --cognitive-drift: #2d3748;
  --cognitive-dawn: #fdfbf7;
}
```

---

## Step 3: Progressive Disclosure Architecture

### Layer Components
```typescript
// frontend/src/components/scaffolding/TaskScaffold.tsx
interface LayerConfig {
  layer: 1 | 2 | 3;
  content: string[];
  maxFeatures: 5;
  revealTrigger: 'click' | 'hover' | 'auto';
}
```

---

## Step 4: ADHD Safety Net Architecture

### Auto-Save
- **Hook:** `useAutoSave(debounceMs: 2000)`
- **Storage:** localStorage
- **Scope:** Last 50 keystrokes
- **Indicator:** "Saved 💾" component

### Massive Undo
- **Hook:** `useMassiveUndo(maxStates: 50)`
- **Storage:** IndexedDB
- **UI:** Floating undo button
- **Duration:** Last hour visible

### Focus Shield
- **Component:** `FocusShield`
- **Queue:** Single notification at a time
- **Calm Mode:** 25-minute Pomodoro toggle

---

## Step 5: Provider Unification Architecture

### Unified Model Selector
```typescript
interface UnifiedProviderConfig {
  openrouter: {
    keys: string[]; // 6 keys for rotation
    free: string[]; // 3 free models
    premium: string[]; // 5 premium models
  };
  gguf: {
    local: string[]; // 3 local models
  };
}
```

### Tunnel Status Component
- Display active API key index (1-6)
- Visual indicator in settings header
- Auto-rotate on rate limit

---

## Step 6: Memory Integration Architecture

### Brain MCP Integration
```typescript
// Namespace exposure to frontend
interface MemoryIntegration {
  memory_search: MCP tool;
  session_recall: MCP tool;
  qlearning_stats: Visualization component;
}
```

### Components
- `MemorySearchUI` - Expose memory_search MCP
- `SessionRecallUI` - Last 30 sessions
- `QLearningStats` - Routing improvement trends

---

## Step 7: Component Dependencies

| Component | Dependencies | Sprint |
|-----------|-------------|--------|
| CognitiveStateToggle | CSS variables, Zustand store | 1 |
| TaskScaffold | Layer config, state machine | 2 |
| AutoSaveIndicator | localStorage, useEffect | 3 |
| MassiveUndoButton | IndexedDB, undo stack | 3 |
| FocusShield | Notification queue, context | 3 |
| CalmModeToggle | Timer state, localStorage | 3 |
| UnifiedProviderSelector | Model config, API keys | 4 |
| TunnelStatus | Tunnel MCP, rotation state | 4 |
| MemorySearchUI | brain_mcp namespace | 5 |
| QLearningStats | learning_engine namespace | 5 |

---

## Step 8: API Boundaries

### Frontend → Backend
- `GET /api/models` - Unified model list
- `GET /api/tunnel/status` - Active key indicator
- `POST /api/cognitive-state` - State persistence
- `GET /api/memory/search` - Memory search
- `GET /api/sessions/recall` - Session recall

---

## Step 9: Complete

Architecture specification ready for epics and stories creation.

---

*Generated from UX spec and Metis/Momus reviews*
---
stepsCompleted: [1]
inputDocuments: []
projectName: N-Xyme Frontend Overhaul
userName: N-Xyme
---

# UX Design Specification: ADHD-Friendly Frontend Overhaul

**Project Name:** N-Xyme MIND Frontend Overhaul  
**Author:** N-Xyme  
**Date:** 2026-04-17

---

## Step 1: Project Vision

### Goal
Create an industry gold standard, bulletproofed, frictionless, ADHD-friendly frontend for N-Xyme MIND.

### Key Requirements
- Three-mode visual language (SURGE/DRIFT/DAWN)
- The "Handshake" approval paradigm  
- Cognitive bandwidth detection
- Progressive disclosure scaffolding
- Remove dictation from home (keep in chat only)
- Unified provider selector (OpenRouter + GGUF + Free)

---

## Step 2: Visual States Design

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

## Step 3: Progressive Disclosure

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

## Step 4: ADHD Safety Net

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

## Step 5: Re-Entry Experience

### State Restoration
- Full visual state (theme, scroll position, input)
- "Catch up" 3-bullet digest
- Progress % always visible

---

## Step 6: Component Inventory

### New Components Needed
| Component | Purpose | Sprint |
|-----------|---------|--------|
| CognitiveStateToggle | SURGE/DRIFT/DAWN switch | 1 |
| TaskScaffold | Progressive disclosure container | 2 |
| AutoSaveIndicator | Save status display | 3 |
| MassiveUndoButton | Undo floating action | 3 |
| FocusShield | Notification queue | 3 |
| CalmModeToggle | Pomodoro timer | 3 |
| UnifiedProviderSelector | Model picker | 4 |
| TunnelStatus | API key indicator | 4 |
| MemorySearchUI | Session recall | 5 |
| QLearningStats | Routing visualization | 5 |

---

## Step 7: Accessibility

- prefers-reduced-motion support
- Screen reader compatible
- Keyboard navigation (Ctrl+K command palette exists)
- Focus mode (visual distraction reduction)
- High contrast support

---

## Step 8: Complete

UX Design Specification ready for architecture phase.

---

*Generated from Party Mode insights: Sally (UX), Victor (Innovation), Dr. Quinn (Problem Solving)*
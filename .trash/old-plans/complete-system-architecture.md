# Complete System Architecture Masterplan

> **Goal**: Fix all bugs, create system-wide awareness, make all agents work
> **Date**: 2026-04-06
> **Status**: READY FOR IMPLEMENTATION

---

## CURRENT STATE DIAGNOSIS

### What's Working
- Memory MCP ✅
- Context sharing ✅
- Unified router ✅ (imports OK)
- ML router ✅
- Skill registry ✅
- Health monitor ✅
- Learning outcomes ✅
- Ollama models: qwen2.5-coder:7b, llama3.2:3b, nomic-embed-text:latest

### What's Broken
1. **BrainPipeline**: `CircuitBreakerOpen` import doesn't exist (line 17)
2. **BrainPipeline**: Duplicate CircuitBreaker calls with wrong signature (lines 42-58)
3. **Unified Router**: Indent error in delegation_logger.py line 176
4. **No System-Wide Awareness**: Components exist but aren't connected
5. **Agent Failures**: All agents fail due to above bugs

### Root Cause
- BrainPipeline is the core orchestrator but fails to import
- CircuitBreaker class signature: `CircuitBreaker(failure_threshold=3, reset_timeout=300, ...)` — NO positional name argument
- Current code calls: `CircuitBreaker("hephaestus", failure_threshold=3, reset_timeout=60)` — WRONG

---

## ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│                    SYSTEM-WIDE AWARENESS LAYER                  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Global      │  │ Shared       │  │ System State         │  │
│  │ Context     │  │ Memory       │  │ Monitor              │  │
│  │ Store       │  │ Bus          │  │                      │  │
│  └─────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT ORCHESTRATION LAYER                    │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Brain       │  │ Unified      │  │ Agent                │  │
│  │ Pipeline    │  │ Router       │  │ Registry             │  │
│  │ (FIXED)     │  │              │  │                      │  │
│  └─────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE LAYER                           │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ ML Router   │  │ Skill        │  │ Health               │  │
│  │             │  │ Registry     │  │ Monitor              │  │
│  └─────────────┘  └──────────────┘  └──────────────────────┘  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Context     │  │ Learning     │  │ Rate                 │  │
│  │ Sharing     │  │ Outcomes     │  │ Limiter              │  │
│  └─────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT EXECUTION LAYER                        │
│  Sisyphus │ Hephaestus │ Oracle │ Explore │ Librarian │ etc.   │
└─────────────────────────────────────────────────────────────────┘
```

---

## IMPLEMENTATION PLAN

### Phase 1: Fix Critical Bugs (30 min)
1. Fix BrainPipeline CircuitBreaker import and calls
2. Fix unified_router indent error
3. Verify all imports work

### Phase 2: Create System-Wide Awareness Layer (1 hour)
1. Create `src/awareness/global_context.py` — Global context store
2. Create `src/awareness/memory_bus.py` — Memory event bus
3. Create `src/awareness/system_monitor.py` — System state monitor
4. Connect all intelligence components to awareness layer

### Phase 3: Fix Agent Orchestration (1 hour)
1. Fix BrainPipeline to use awareness layer
2. Fix Unified Router to use awareness layer
3. Create agent registry with health tracking
4. Test all agents initialize correctly

### Phase 4: End-to-End Testing (30 min)
1. Test BrainPipeline initialization
2. Test unified router
3. Test agent routing
4. Test system-wide awareness

---

## FILE STRUCTURE

```
src/
├── awareness/                    # NEW: System-wide awareness layer
│   ├── __init__.py
│   ├── global_context.py         # Global context store
│   ├── memory_bus.py             # Memory event bus
│   └── system_monitor.py         # System state monitor
├── brain/
│   └── pipeline.py               # FIXED: CircuitBreaker calls
├── tools/
│   └── intelligence/
│       └── unified_router.py     # FIXED: Indent error
└── ... (existing structure)
```

---

## EXECUTION

Begin with Phase 1: Fix Critical Bugs

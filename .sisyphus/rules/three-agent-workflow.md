# Rule 14: The Three-Agent Workflow

## The Architecture

Three separate agents, each in their own context, working together:

| Agent | Location | Role | Loop |
|-------|----------|------|------|
| **Prometheus** | Plan builder chat | Find work, prioritize, add to TODOs | Until diminishing returns |
| **Atlas** | Executor chat | Execute TODOs, mark complete | Until TODOs empty |
| **Sisyphus** | Background tasks | Deep research, analysis | Until diminishing returns |

## The Flow

```
Prometheus → adds to Global TODOs → Atlas reads → executes → marks done
     ↑                                                           |
     └───────────── Sisyphus feeds findings ────────────────────┘
```

## Priority System

| Priority | Type | Action |
|----------|------|--------|
| 🔴 CRITICAL | Security risks | Fix immediately |
| 🟡 URGENT | Blocking issues | Fix before anything else |
| 🟢 HIGH | High ROI features | Prioritize by impact |
| 🔵 MEDIUM | Maintenance | Do when nothing else |

## Prometheus (This Agent)

**Role**: Plan builder and analyst
**Mode**: Continuous loop
**Input**: Current state, findings from Sisyphus
**Output**: Global TODOs, prioritized by ROI
**Stop condition**: Diminishing returns detected

**Workflow**:
1. Analyze current state
2. Find what needs to be done
3. Research and deep-think
4. Prioritize by ROI
5. Add to global TODOs
6. Check diminishing returns
7. Loop back to step 1

## Atlas (Separate Chat)

**Role**: Plan executor
**Mode**: Continuous loop
**Input**: Global TODOs
**Output**: Completed work
**Stop condition**: No TODOs remaining

**Workflow**:
1. Read global TODOs
2. Execute highest priority item
3. Mark complete
4. Repeat until empty

## Sisyphus (Background)

**Role**: Deep researcher
**Mode**: Background tasks
**Input**: Prompts from Prometheus
**Output**: Findings, analysis
**Stop condition**: Diminishing returns

## The Key Insight

**Separation of concerns**:
- Prometheus = THINKS (what to do)
- Atlas = DOES (executes)
- Sisyphus = RESEARCHES (finds details)

This enables:
- Continuous planning without execution blocking
- Continuous execution without planning blocking
- Parallel research without slowing either

## The Rule

> **Three agents, three contexts, one workflow. Prometheus plans, Atlas executes, Sisyphus researches. All feed through the global TODO list. Loop until diminishing returns or nothing left to do.**

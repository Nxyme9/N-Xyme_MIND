# Rule 20: Heartbeat Delegation Engine

## The Rule

**Heartbeat is the central coordinator.** It monitors, assesses, and delegates. NOT Prometheus. NOT Atlas.

## Delegation Logic

```
Every 5 minutes:
1. Read global TODOs
2. Filter: status=pending
3. For each task:
   a. Assess complexity
   b. Check idle agents
   c. Match to correct agent
   d. Execute delegation
4. Update status
5. Log to memory
```

## Task Complexity Assessment

| Type | Criteria | Delegate To |
|------|----------|-------------|
| **Simple** | Single file, <50 lines, clear | Sisyphus worker |
| **Medium** | 2-3 files, 50-200 lines | Sisyphus worker |
| **Complex** | 4+ files, 200+ lines | Atlas (plan executor) |
| **Architecture** | System design, cross-module | Prometheus (plan builder) |

## Delegation Rules

1. **Simple/Medium** → Sisyphus worker executes directly
2. **Complex** → Atlas breaks into sub-tasks, delegates to workers
3. **Architecture** → Flag for Prometheus, user approves

## The Chain

```
Heartbeat (monitors)
├─ Reads global TODOs
├─ Assesses complexity
├─ IF Simple: delegate to Sisyphus worker
├─ IF Complex: delegate to Atlas
├─ IF Architecture: flag for Prometheus
└─ Repeat every 5 min
```

## The Rule

> **Heartbeat is the central coordinator. Monitors TODOs. Assesses complexity. Delegates to correct agent. Simple tasks → Sisyphus workers. Complex tasks → Atlas. Architecture → Prometheus. Never stops the chain.**

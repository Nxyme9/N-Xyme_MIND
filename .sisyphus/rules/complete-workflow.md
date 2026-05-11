# Rule 15: The Complete Continuous Refinement System

## The Three Agents + Heartbeat

| Component | Role | Location | Loop |
|-----------|------|----------|------|
| **Prometheus** | Plan builder | This chat | Finds work → adds to global TODOs |
| **Atlas** | Plan executor | Separate chat | Reads TODOs → executes → pushes to GitHub |
| **Sisyphus** | Deep researcher | Background tasks | Deep analysis until diminishing returns |
| **LLM Heartbeat** | System monitor | Background (Ollama) | Periodic check → delegates idle agents |

## The Complete Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM HEARTBEAT (Local Ollama)                 │
│                    Periodic: every 5-10 minutes                  │
│                                                                  │
│  1. Check system health                                         │
│  2. Check agent status (idle/busy)                              │
│  3. Read global memory for pending work                         │
│  4. If idle agent found → delegate to it                        │
│  5. If Prometheus idle → find new work to analyze               │
│  6. If Atlas idle → check for TODOs to execute                  │
│  7. Log findings to global memory                               │
└──────────────┬──────────────────────────────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
┌──────────────┐  ┌──────────────┐
│  PROMETHEUS  │  │    ATLAS     │
│ (Plan Build) │  │ (Plan Exec)  │
│              │  │              │
│ 1. Analyze   │  │ 1. Read TODOs│
│ 2. Find work │  │ 2. Execute   │
│ 3. Prioritize│  │ 3. Mark done │
│ 4. Push to   │  │ 4. Push to   │
│    memory    │  │    GitHub    │
│ 5. Loop      │  │ 5. Loop      │
└──────┬───────┘  └──────┬───────┘
       │                 │
       │    ┌────────────┘
       │    │
       ▼    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GLOBAL MEMORY (Graphiti)                     │
│                                                                  │
│  - TODOs (prioritized)                                          │
│  - Findings (from Sisyphus)                                     │
│  - Status (from Heartbeat)                                      │
│  - Decisions (from Prometheus)                                  │
│  - Results (from Atlas)                                         │
└─────────────────────────────────────────────────────────────────┘
```

## Prometheus (Plan Builder) — This Agent

**Role**: Find work, analyze, prioritize, add to global memory
**Mode**: Continuous loop
**Input**: Current state, findings from Sisyphus, heartbeat status
**Output**: Global TODOs, prioritized by ROI
**Auto-push**: Adds to global memory automatically

**Workflow**:
1. Check current state
2. Find what needs to be done
3. Research and deep-think
4. Prioritize by ROI (security > urgent > high > medium)
5. Add to global memory TODOs
6. Check diminishing returns
7. Loop back to step 1

## Atlas (Plan Executor) — Separate Chat

**Role**: Execute TODOs, push to GitHub at milestones
**Mode**: Continuous loop
**Input**: Global memory TODOs
**Output**: Completed work, GitHub commits
**Auto-push**: Commits to GitHub at big milestones

**Workflow**:
1. Read global memory TODOs
2. Execute highest priority item
3. Mark complete in memory
4. Check if milestone reached
5. If milestone → push to GitHub
6. Repeat until TODOs empty

## Sisyphus (Deep Researcher) — Background Tasks

**Role**: Deep analysis, research, until diminishing returns
**Mode**: Background tasks
**Input**: Prompts from Prometheus
**Output**: Findings pushed to global memory
**Stop condition**: Diminishing returns detected

## LLM Heartbeat (System Monitor) — Background (Ollama)

**Role**: Periodic system health check and delegation
**Mode**: Background (every 5-10 minutes)
**Input**: System status, agent status, global memory
**Output**: Delegation decisions, health reports
**Cost**: ~$0 (local Ollama, no cloud)

**Heartbeat Check**:
1. **System health**: Are services running? (Neo4j, Graphiti, Ollama)
2. **Agent status**: Is Prometheus idle? Is Atlas idle?
3. **Global memory**: Are there pending TODOs?
4. **Delegation**: If agent idle + work available → delegate
5. **Logging**: Record findings to global memory

**Heartbeat Code**:
```python
class Heartbeat:
    """Periodic system monitor using local LLM."""
    
    def __init__(self, interval=300):  # 5 minutes
        self.interval = interval
        self.ollama_url = "http://localhost:11434"
        
    async def run(self):
        """Main heartbeat loop."""
        while True:
            # Check system health
            health = self.check_health()
            
            # Check agent status
            agents = self.check_agents()
            
            # Read global memory
            todos = self.read_todos()
            
            # Delegate if needed
            if agents["prometheus"]["status"] == "idle" and todos:
                self.delegate_to_prometheus(todos[0])
            elif agents["atlas"]["status"] == "idle" and todos:
                self.delegate_to_atlas(todos[0])
                
            # Log to memory
            self.log_status(health, agents, todos)
            
            # Wait for next heartbeat
            await asyncio.sleep(self.interval)
```

## The Priority System

| Priority | Type | Action |
|----------|------|--------|
| 🔴 CRITICAL | Security risks | Fix immediately |
| 🟡 URGENT | Blocking issues | Fix before anything else |
| 🟢 HIGH | High ROI features | Prioritize by impact |
| 🔵 MEDIUM | Maintenance | Do when nothing else |

## GitHub Integration

Atlas pushes to GitHub at **big milestones**:
- After all CRITICAL issues fixed
- After migration complete
- After major feature implemented
- After test infrastructure added

Commit message format: `feat(scope): description` or `fix(scope): description`

## The Rule

> **Three agents + heartbeat. Prometheus plans, Atlas executes, Sisyphus researches. Heartbeat monitors and delegates. All through global memory. Atlas pushes to GitHub at milestones. Loop until diminishing returns or nothing left.**

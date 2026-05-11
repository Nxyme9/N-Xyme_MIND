# Rule 19: Forking Agent (Parallel Chains)

## The Problem

One chain = bottleneck. Need parallel chains for parallel work.

## The Solution: Forking Agent

```
FORKING AGENT (top level)
├─ Decides: can this be parallelized?
├─ If YES: fork into N chains
├─ If NO: use single chain
│
├─ Chain 1: Prometheus 1 → Atlas 1 → Workers 1,2,3
├─ Chain 2: Prometheus 2 → Atlas 2 → Workers 4,5,6
├─ Chain 3: Prometheus 3 → Atlas 3 → Workers 7,8,9
│
└─ Forking agent collects results from all chains
```

## When to Fork

| Condition | Action |
|-----------|--------|
| Task can be split | Fork into parallel chains |
| Task is serial | Use single chain |
| Task has dependencies | Fork with dependency order |
| Task is independent | Fork freely |

## Implementation

```python
class ForkingAgent:
    """Decides when to fork and manages parallel chains."""
    
    def __init__(self, max_chains=3):
        self.max_chains = max_chains
        self.active_chains = []
        
    def should_fork(self, tasks):
        """Decide if tasks should be forked."""
        # Count independent tasks
        independent = [t for t in tasks if not t.get("depends_on")]
        
        if len(independent) >= 3:
            return True, len(independent)
        return False, 1
        
    def fork(self, tasks):
        """Split tasks into parallel chains."""
        chains = []
        for i in range(0, len(tasks), self.max_chains):
            chain = tasks[i:i+self.max_chains]
            chains.append(chain)
        return chains
```

## The Rule

> **Forking agent splits work into parallel chains. Each chain has its own Prometheus→Atlas→Workers. Fork when tasks are independent. Use single chain when serial. NO MAX LIMIT. Scale until 90-95% hardware utilization.**

## Dynamic Scaling

```
Monitor hardware usage:
├─ If CPU < 80%: launch more workers
├─ If GPU < 80%: launch more workers
├─ If RAM < 80%: launch more workers
├─ If all > 90%: stop scaling
└─ Target: 90-95% utilization all the time
```

## Scaling Formula

```
max_workers = (100 - current_utilization) / 10
if current_utilization < 90:
    launch max_workers new chains
```

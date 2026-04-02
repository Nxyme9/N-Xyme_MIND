# Rule 17: Interrupt Handling + Priority Queue

## Interrupt Handling (Like ChatGPT)

When user sends a prompt while agent is working:

```
Agent working on Task A
│
├─ User sends new prompt: "Stop, do this instead"
│   │
│   ├─ Agent: Stop Task A (save progress)
│   ├─ Agent: Handle new prompt immediately
│   ├─ Agent: Complete new task
│   └─ Agent: Resume or abandon Task A
│
└─ Agent working continues if no interrupt
```

### Implementation

```python
class InterruptHandler:
    """Handle priority interrupts during agent work."""
    
    def __init__(self):
        self.current_task = None
        self.interrupt_queue = []
        
    def receive_interrupt(self, prompt, priority):
        """Receive new prompt while working."""
        if priority == "P0":  # Emergency
            self.pause_current()
            self.execute_immediately(prompt)
            self.resume_or_abandon()
        elif priority == "P1":  # Urgent
            self.interrupt_queue.append((prompt, priority))
            self.complete_current_then_next()
        else:  # Normal
            self.interrupt_queue.append((prompt, priority))
            
    def pause_current(self):
        """Pause current task, save progress."""
        # Save state to global memory
        # Mark as paused
        
    def execute_immediately(self, prompt):
        """Execute high-priority task immediately."""
        # Run the interrupt task
        # Don't wait for current task
        
    def resume_or_abandon(self):
        """After interrupt, resume or abandon previous task."""
        # Check if previous task still relevant
        # Resume if yes, abandon if no
```

## Heartbeat Priority Queue

The heartbeat monitors and prioritizes by urgency:

### Priority Levels

| Level | Type | Response Time | Examples |
|-------|------|--------------|----------|
| **P0** | Emergency | Immediate (<1s) | Security breach, system crash, health failure |
| **P1** | Urgent | Next cycle (<5min) | User request, blocking issue, critical bug |
| **P2** | High ROI | Normal queue | Features, optimizations, improvements |
| **P3** | Maintenance | Background | Cleanup, docs, tests, refactoring |

### Heartbeat Decision Logic

```python
class HeartbeatPriority:
    """Heartbeat with priority-based decision making."""
    
    def check_priorities(self):
        """Check system state and prioritize."""
        
        # P0: Emergency checks
        if self.security_breach_detected():
            return "P0", "Security breach detected"
        if self.system_health_critical():
            return "P0", "System health critical"
        if self.critical_service_down():
            return "P0", "Critical service down"
            
        # P1: Urgent checks
        if self.user_request_pending():
            return "P1", "User request waiting"
        if self.blocking_issue_found():
            return "P1", "Blocking issue found"
            
        # P2: High ROI checks
        if self.high_roi_task_available():
            return "P2", "High ROI task available"
            
        # P3: Maintenance
        if self.cleanup_needed():
            return "P3", "Maintenance needed"
            
        return None, "All clear"
        
    def act_on_priority(self, priority, reason):
        """Take action based on priority."""
        
        if priority == "P0":
            # Interrupt all agents immediately
            self.interrupt_all_agents(reason)
            self.delegate_emergency(reason)
            
        elif priority == "P1":
            # Queue next, notify user
            self.queue_urgent(reason)
            self.notify_user(reason)
            
        elif priority == "P2":
            # Normal delegation
            self.delegate_to_idle_agent(reason)
            
        elif priority == "P3":
            # Background processing
            self.delegate_background(reason)
```

### ROI Calculation

```python
def calculate_roi(task):
    """Calculate Return on Investment for a task."""
    
    # Factors:
    impact = task.get("impact", 0)  # 0-10
    urgency = task.get("urgency", 0)  # 0-10
    effort = task.get("effort", 1)  # hours
    
    # Time factor (faster = higher ROI)
    time_factor = 1 / max(effort, 0.1)
    
    # ROI = (impact + urgency) * time_factor
    roi = (impact + urgency) * time_factor
    
    return roi
```

## Emergency Detection

```python
def detect_emergencies(self):
    """Detect emergency conditions."""
    
    emergencies = []
    
    # Security
    if self.sql_injection_detected():
        emergencies.append(("P0", "SQL injection detected"))
    if self.api_key_leaked():
        emergencies.append(("P0", "API key exposed"))
    if self.unauthorized_access():
        emergencies.append(("P0", "Unauthorized access"))
        
    # Health
    if self.service_down("neo4j"):
        emergencies.append(("P0", "Neo4j down"))
    if self.service_down("graphiti"):
        emergencies.append(("P0", "Graphiti down"))
    if self.gpu_overheating():
        emergencies.append(("P0", "GPU overheating"))
        
    # Critical failures
    if self.data_corruption_detected():
        emergencies.append(("P0", "Data corruption"))
    if self.disk_full():
        emergencies.append(("P0", "Disk full"))
        
    return emergencies
```

## The Rule

> **Heartbeat prioritizes by urgency: P0 (emergency) → P1 (urgent) → P2 (high ROI) → P3 (maintenance). When user interrupts, agent pauses current work and handles immediately. ROI = (impact + urgency) / effort. Emergency detection runs every heartbeat cycle.**

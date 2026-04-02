# What's Next Heartbeat
## Auto-Detect & Auto-Append at End of Every Prompt

---

## The Rule

**EVERY output MUST end with:**

```
---

## 🔍 What's Next

### Obvious Problems:
[list]

### Hidden Problems:
[list]

### Upgrades Needed:
[list]

### Fixes Pending:
[list]

---

**Status:** [X/Y complete]
**Next Action:** [What should happen next]
**Priority:** [Level]
```

---

## Auto-Detection Logic

```python
class WhatsNextHeartbeat:
    """Auto-detect and append What's Next to every output."""
    
    def check(self, output: str) -> bool:
        """Check if output has What's Next section."""
        
        required_markers = [
            "## 🔍 What's Next",
            "### Obvious Problems:",
            "### Hidden Problems:",
            "### Upgrades Needed:",
            "### Fixes Pending:",
            "**Status:**",
            "**Next Action:**",
            "**Priority:**"
        ]
        
        for marker in required_markers:
            if marker not in output:
                return False
        
        return True
    
    def append(self, output: str) -> str:
        """Append What's Next if missing."""
        
        if self.check(output):
            return output  # Already has it
        
        # Generate What's Next
        whats_next = self.generate_whats_next(output)
        
        return f"{output}\n\n{whats_next}"
    
    def generate_whats_next(self, output: str) -> str:
        """Generate What's Next based on output content."""
        
        # Detect what was done
        actions_done = self.detect_actions(output)
        
        # Generate recommendations
        return f"""
---

## 🔍 What's Next

### Obvious Problems:
{self.find_obvious_problems(output)}

### Hidden Problems:
{self.find_hidden_problems(output)}

### Upgrades Needed:
{self.find_upgrades(output)}

### Fixes Pending:
{self.find_pending_fixes(output)}

---

**Status:** {self.calculate_status(output)}
**Next Action:** {self.suggest_next_action(output)}
**Priority:** {self.determine_priority(output)}
"""
```

---

## Integration Points

### 1. Agent Wrapper
```python
def wrap_agent_with_whats_next(agent_func):
    """Wrap agent to always end with What's Next."""
    
    def wrapped(*args, **kwargs):
        result = agent_func(*args, **kwargs)
        
        # Auto-append What's Next
        heartbeat = WhatsNextHeartbeat()
        if not heartbeat.check(result):
            result = heartbeat.append(result)
        
        return result
    
    return wrapped
```

### 2. Orchestrator Output
```python
def orchestrator_output(message: str) -> str:
    """Format orchestrator output with What's Next."""
    
    heartbeat = WhatsNextHeartbeat()
    return heartbeat.append(message)
```

### 3. Every Response
```python
def format_response(content: str) -> str:
    """Format any response with What's Next."""
    
    heartbeat = WhatsNextHeartbeat()
    
    if heartbeat.check(content):
        return content
    
    return heartbeat.append(content)
```

---

## The Template

```
[Your response content here]

---

## 🔍 What's Next

### Obvious Problems:
1. [Problem visible from this output]
2. [Problem visible from this output]

### Hidden Problems:
1. [Problem not immediately obvious]
2. [Problem not immediately obvious]

### Upgrades Needed:
1. [Improvement opportunity]
2. [Improvement opportunity]

### Fixes Pending:
1. [Known issue needing fix]
2. [Known issue needing fix]

---

**Status:** [X/Y complete, Z remaining]
**Next Action:** [What should happen next]
**Priority:** [CRITICAL/HIGH/MEDIUM/LOW]
```

---

## Examples

### Example 1: After fixing a bug

```
Fixed the WebSocket connection timeout.

**Changes made:**
- Increased timeout from 5s to 30s
- Added retry logic

---

## 🔍 What's Next

### Obvious Problems:
1. WebSocket still drops randomly (need reconnection)
2. No health check endpoint

### Hidden Problems:
1. Memory leak in connection pool
2. No timeout for hung connections

### Upgrades Needed:
1. Add automatic reconnection
2. Add connection pooling
3. Add health endpoint

### Fixes Pending:
1. Fix memory leak
2. Add circuit breaker

---

**Status:** 1/5 complete
**Next Action:** Add automatic reconnection
**Priority:** HIGH
```

### Example 2: After deploying agents

```
Deployed 4 specialists for NUCLEAR MELTDOWN.

**Results:**
- Firefox: Infrastructure OK
- Lightning: Software issues found
- Brain: Performance OK
- Shield: Security OK

---

## 🔍 What's Next

### Obvious Problems:
1. Lightning found 3 software issues
2. Need to fix those issues

### Hidden Problems:
1. Agent prompts may be too long
2. No timeout for hung agents

### Upgrades Needed:
1. Add agent timeout
2. Add agent retry logic

### Fixes Pending:
1. Fix Lightning's findings
2. Add agent performance tracking

---

**Status:** 4/4 deployed, 3 issues found
**Next Action:** Fix Lightning's 3 findings
**Priority:** HIGH
```

---

## Auto-Detection Patterns

### Pattern 1: Work Completed
```
If output contains "fixed", "completed", "done", "finished":
→ What's Next should list remaining work
```

### Pattern 2: Issue Found
```
If output contains "error", "failed", "problem", "issue":
→ What's Next should list fixes needed
```

### Pattern 3: Analysis Done
```
If output contains "analysis", "review", "assessment":
→ What's Next should list actions from analysis
```

### Pattern 4: Agent Deployed
```
If output contains "deployed", "agent", "specialist":
→ What's Next should list agent findings
```

---

## Heartbeat Integration

```python
class OutputHeartbeat:
    """Heartbeat that monitors and appends What's Next."""
    
    def __init__(self):
        self.whats_next = WhatsNextHeartbeat()
    
    def process_output(self, output: str) -> str:
        """Process output and ensure What's Next is present."""
        
        # Check if What's Next is present
        if not self.whats_next.check(output):
            # Auto-append
            output = self.whats_next.append(output)
        
        return output
```

---

## The Standard

**From now on:**

1. Every agent output ends with What's Next
2. Every orchestrator output ends with What's Next
3. Every response ends with What's Next
4. Every analysis ends with What's Next
5. Every fix ends with What's Next

**No exceptions.**

**This creates:**
- Continuous forward motion
- No stagnation
- Always something to do next
- Never "done" until everything is done

---

## Implementation

### File: `jarvis/filters/whats_next.py`

```python
"""
What's Next Heartbeat
Auto-detect and append What's Next to every output.
"""

class WhatsNextHeartbeat:
    """Auto-detect and append What's Next."""
    
    def __init__(self):
        self.required_markers = [
            "## 🔍 What's Next",
            "### Obvious Problems:",
            "### Hidden Problems:",
            "### Upgrades Needed:",
            "### Fixes Pending:",
            "**Status:**",
            "**Next Action:**",
            "**Priority:**"
        ]
    
    def check(self, output: str) -> bool:
        """Check if output has What's Next."""
        return all(marker in output for marker in self.required_markers)
    
    def append(self, output: str) -> str:
        """Append What's Next if missing."""
        if self.check(output):
            return output
        
        return f"{output}\n\n{self._generate()}"
    
    def _generate(self) -> str:
        """Generate What's Next template."""
        return """
---

## 🔍 What's Next

### Obvious Problems:
1. [Identify from context]

### Hidden Problems:
1. [Think deeper]

### Upgrades Needed:
1. [Improvement opportunities]

### Fixes Pending:
1. [Known issues]

---

**Status:** [X/Y complete]
**Next Action:** [What next]
**Priority:** [Level]
"""
```

---

*Created: March 19, 2026*
*Type: Auto-append heartbeat*
*Goal: Every output ends with What's Next*

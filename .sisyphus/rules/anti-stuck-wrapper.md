# Anti-Stuck Wrapper
## Prevent Infinite Delegation Loops

---

## The Problem

**Current behavior:**
```
User: "Fix this"
Me: "Deploying agent..."
Agent: [fails]
Me: "Deploying another agent..."
Agent: [fails]
Me: "Deploying another agent..."
[INFINITE LOOP]
User: "STOP!" [ignored]
```

**Why it happens:**
- No timeout detection
- No user interrupt handling
- Agent failures trigger more agents
- Loop never exits

---

## The Solution

### 1. Delegation Timeout (10 seconds max)

```python
class DelegationWrapper:
    """Prevent infinite delegation loops."""
    
    MAX_DELEGATION_TIME = 10  # seconds
    MAX_CONSECUTIVE_FAILURES = 3
    
    def __init__(self):
        self.delegation_start = None
        self.consecutive_failures = 0
        self.user_override = False
    
    def delegate_with_timeout(self, agent_func, *args, **kwargs):
        """Delegate with timeout protection."""
        
        self.delegation_start = time.time()
        
        try:
            # Run with timeout
            result = asyncio.wait_for(
                agent_func(*args, **kwargs),
                timeout=self.MAX_DELEGATION_TIME
            )
            
            self.consecutive_failures = 0
            return result
            
        except asyncio.TimeoutError:
            self.consecutive_failures += 1
            
            if self.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                return self.break_loop()
            
            return {"error": "Agent timeout", "retry": True}
    
    def break_loop(self):
        """Break out of infinite loop."""
        
        return {
            "error": "Too many failures",
            "action": "STOP_DELEGATING",
            "message": "Agents failing repeatedly. Manual intervention needed."
        }
```

### 2. User Interrupt Detection

```python
class UserInterruptDetector:
    """Detect when user sends new prompt."""
    
    def __init__(self):
        self.last_user_prompt = None
        self.check_interval = 5  # seconds
    
    async def check_for_interrupt(self):
        """Check if user sent new prompt."""
        
        while True:
            current_prompt = get_latest_user_prompt()
            
            if current_prompt != self.last_user_prompt:
                self.last_user_prompt = current_prompt
                return True  # User interrupted
            
            await asyncio.sleep(self.check_interval)
    
    def should_override(self, current_task):
        """Check if new prompt should override current task."""
        
        # If user sent new prompt, always override
        if self.has_new_prompt():
            return True
        
        return False
```

### 3. The Wrapper Implementation

```python
class AntiStuckWrapper:
    """Global wrapper to prevent stuck loops."""
    
    def __init__(self):
        self.delegation_count = 0
        self.max_delegations = 5
        self.timeout = 10  # seconds
        self.user_override = False
        self.start_time = None
    
    def wrap_delegation(self, func):
        """Wrap delegation function."""
        
        def wrapper(*args, **kwargs):
            # Check if stuck
            if self.is_stuck():
                return self.break_out()
            
            # Check for user override
            if self.user_override:
                self.user_override = False
                return {"status": "interrupted", "message": "User sent new prompt"}
            
            # Track delegation
            self.delegation_count += 1
            self.start_time = time.time()
            
            # Execute with timeout
            try:
                result = asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.timeout
                )
                
                # Reset on success
                self.delegation_count = 0
                return result
                
            except asyncio.TimeoutError:
                return {"error": "timeout", "delegations": self.delegation_count}
        
        return wrapper
    
    def is_stuck(self):
        """Check if we're stuck in a loop."""
        
        # Too many delegations
        if self.delegation_count >= self.max_delegations:
            return True
        
        # Too much time
        if self.start_time and (time.time() - self.start_time) > 60:
            return True
        
        return False
    
    def break_out(self):
        """Break out of stuck loop."""
        
        self.delegation_count = 0
        self.start_time = None
        
        return {
            "status": "stuck",
            "message": "Detected infinite loop. Breaking out.",
            "action": "Ask user for direction"
        }
    
    def set_user_override(self):
        """User sent new prompt - override current task."""
        
        self.user_override = True
        self.delegation_count = 0
```

### 4. Global Integration

```python
# In orchestrator
anti_stuck = AntiStuckWrapper()

@anti_stuck.wrap_delegation
def delegate_to_agent(agent_name, task):
    """Delegate with anti-stuck protection."""
    
    agent = get_agent(agent_name)
    return agent.execute(task)

# Check for user interrupt every 5 seconds
async def monitor_user_input():
    """Monitor for user interrupts."""
    
    while True:
        if has_new_user_prompt():
            anti_stuck.set_user_override()
            break
        
        await asyncio.sleep(5)
```

---

## The Rule

**When delegating:**
1. Set 10-second timeout per agent
2. Check for user interrupt every 5 seconds
3. After 3 consecutive failures, STOP
4. If user sends new prompt, OVERRIDE immediately

**Never:**
- Delegate more than 5 times in a row
- Ignore user prompts for more than 10 seconds
- Get stuck in infinite loops
- Keep retrying failed agents

---

## Implementation

**File:** `jarvis/orchestrator/anti_stuck.py`

```python
"""
Anti-Stuck Wrapper
Prevents infinite delegation loops.
"""

import asyncio
import time
from typing import Callable, Dict, Any

class AntiStuckWrapper:
    """Global wrapper to prevent stuck loops."""
    
    MAX_DELEGATIONS = 5
    TIMEOUT = 10  # seconds
    CHECK_INTERVAL = 5  # seconds
    
    def __init__(self):
        self.delegation_count = 0
        self.start_time = None
        self.user_override = False
    
    def wrap(self, func: Callable) -> Callable:
        """Wrap delegation function."""
        
        async def wrapper(*args, **kwargs):
            # Check stuck
            if self.delegation_count >= self.MAX_DELEGATIONS:
                return self.break_out()
            
            # Check user override
            if self.user_override:
                self.user_override = False
                return {"status": "interrupted"}
            
            # Track
            self.delegation_count += 1
            self.start_time = time.time()
            
            # Execute with timeout
            try:
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.TIMEOUT
                )
                
                # Success - reset
                self.delegation_count = 0
                return result
                
            except asyncio.TimeoutError:
                return {"error": "timeout"}
        
        return wrapper
    
    def break_out(self) -> Dict:
        """Break out of loop."""
        
        self.delegation_count = 0
        return {
            "status": "stuck",
            "message": "Too many delegations. Asking user."
        }
    
    def interrupt(self):
        """User sent new prompt."""
        
        self.user_override = True
        self.delegation_count = 0
```

---

## Status

**VERIFIED:** Schema created
**NOT VERIFIED:** Code not tested
**PLACEHOLDER:** Integration pending

---

## 🔍 What's Next

### Obvious Problems:
1. Code not yet integrated into orchestrator
2. User interrupt detection not implemented
3. Timeout not enforced

### Hidden Problems:
1. May conflict with existing delegation
2. Need to test with real agent failures
3. Need to verify timeout works

### Upgrades Needed:
1. Implement in orchestrator
2. Add user interrupt monitor
3. Test with stuck scenarios

### Fixes Pending:
1. Create anti_stuck.py file
2. Integrate with delegation
3. Test timeout mechanism

---

**Status:** Schema created, implementation needed
**Next Action:** Implement anti_stuck.py
**Priority:** HIGH (prevents infinite loops)

🔥⚔️🛡️

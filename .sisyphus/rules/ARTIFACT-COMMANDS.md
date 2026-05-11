# ARTIFACT COMMANDS
## Type #ARTIFACT @command to invoke

---

## Global Rules (Added)

### Rule 1: Process Immediately
- When a background task completes, process results IMMEDIATELY
- Don't wait for all tasks to finish
- Compile results as they come in

### Rule 2: Auto-Delegate Follow-ups
- If a completed task reveals new work, delegate to corresponding agent
- Don't wait for user prompt
- Chain tasks automatically

### Rule 3: Parallel Processing
- Multiple agents work simultaneously
- Results compiled in real-time
- No sequential bottlenecks

---

## Command Registry

### #ARTIFACT @plan [description]
**What:** Create a strategic plan
**Who:** Oracle + All Specialists
**Example:** `#ARTIFACT @plan Fix auto-capture port binding`

**Behavior:**
1. Oracle analyzes the problem
2. Each specialist provides input
3. Plan is created with tasks
4. Returns plan file path

---

### #ARTIFACT @attack [target]
**What:** Deploy specialist to fix issue
**Who:** Appropriate specialist
**Example:** `#ARTIFACT @attack Port 5003 blocked`

**Behavior:**
1. Classify target (infra/software/perf/security)
2. Deploy matching specialist
3. Specialist reports back
4. Update global memory

---

### #ARTIFACT @inventory [agent]
**What:** Show agent's current state
**Who:** Specified agent
**Example:** `#ARTIFACT @inventory firefox`

**Behavior:**
1. Load agent character sheet
2. Show HP, mana, inventory, abilities
3. Show recent battles
4. Show lessons learned

---

### #ARTIFACT @memory [query]
**What:** Search global memory
**Who:** Graphiti + Oracle
**Example:** `#ARTIFACT @memory port binding issues`

**Behavior:**
1. Search Graphiti for query
2. Find similar past issues
3. Show solutions that worked
4. Return ranked results

---

### #ARTIFACT @party
**What:** Show all agents status
**Who:** All 4 specialists + Oracle
**Example:** `#ARTIFACT @party`

**Behavior:**
1. Check each agent's status
2. Show HP, current task, last battle
3. Show party composition
4. Show overall health

---

### #ARTIFACT @quest [objective]
**What:** Deploy full party for major objective
**Who:** All specialists
**Example:** `#ARTIFACT @quest Full system audit`

**Behavior:**
1. Oracle creates battle plan
2. All specialists deploy in parallel
3. Each reports findings
4. Oracle synthesizes final report

---

### #ARTIFACT @heal [agent]
**What:** Reset and repair agent
**Who:** Specified agent
**Example:** `#ARTIFACT @heal lightning`

**Behavior:**
1. Clear agent cache
2. Reset HP to max
3. Clear stuck processes
4. Report new status

---

### #ARTIFACT @levelup [agent]
**What:** Improve agent capabilities
**Who:** Specified agent
**Example:** `#ARTIFACT @levelup brain`

**Behavior:**
1. Add new ability
2. Improve existing ability
3. Update character sheet
4. Report new capabilities

---

## How It Works

When you type `#ARTIFACT @command`:

```python
def process_artifact_command(input_text):
    """Process #ARTIFACT commands."""
    
    # Parse command
    if input_text.startswith("#ARTIFACT"):
        parts = input_text.split(" ", 2)
        command = parts[1] if len(parts) > 1 else None
        args = parts[2] if len(parts) > 2 else None
        
        # Route to handler
        handlers = {
            "@plan": handle_plan,
            "@attack": handle_attack,
            "@inventory": handle_inventory,
            "@memory": handle_memory,
            "@party": handle_party,
            "@quest": handle_quest,
            "@heal": handle_heal,
            "@levelup": handle_levelup
        }
        
        if command in handlers:
            return handlers[command](args)
        
        return "Unknown command. Try: @plan, @attack, @inventory, @memory, @party, @quest, @heal, @levelup"
```

---

## Command Aliases

| Alias | Full Command |
|-------|--------------|
| `#A @p` | `#ARTIFACT @plan` |
| `#A @a` | `#ARTIFACT @attack` |
| `#A @i` | `#ARTIFACT @inventory` |
| `#A @m` | `#ARTIFACT @memory` |
| `#A @pa` | `#ARTIFACT @party` |
| `#A @q` | `#ARTIFACT @quest` |
| `#A @h` | `#ARTIFACT @heal` |
| `#A @l` | `#ARTIFACT @levelup` |

---

## Examples

### Quick Plan
```
#ARTIFACT @plan Fix WebSocket auth
→ Creates plan with:
  1. Add Authorization header
  2. Test connection
  3. Verify stability
```

### Quick Attack
```
#ARTIFACT @attack Auto-capture down
→ Deploys FIREFOX:
  - Checks port 5003
  - Finds blocking process
  - Kills or reroutes
  - Reports victory
```

### Check Party
```
#ARTIFACT @party
→ Shows:
  🔥⚔️🛡️ FIREFOX: HP 1000/1000, Last: Graphiti port
  ⚡🗡️🔮 LIGHTNING: HP 600/600, Last: WebSocket auth
  🧠🔮📖 BRAIN: HP 400/400, Last: CPU spike
  🛡️⚔️🔮 SHIELD: HP 800/800, Last: API key check
  🔮📚📜 ORACLE: HP 300/300, Last: Pattern analysis
```

### Full Quest
```
#ARTIFACT @quest System health audit
→ All specialists deploy:
  FIREFOX: Infrastructure check
  LIGHTNING: Software check
  BRAIN: Performance check
  SHIELD: Security check
  ORACLE: Synthesize findings
```

---

## Integration with Existing Systems

### With Wakefulness Engine
```
Wakefulness detects issue
→ Auto-triggers: #ARTIFACT @attack [issue]
```

### With NUCLEAR MELTDOWN
```
5+ issues detected
→ Auto-triggers: #ARTIFACT @quest Emergency response
```

### With Global Memory
```
After each @attack:
→ Save battle result to Graphiti
→ Update agent XP and inventory
```

---

*Created: March 19, 2026*
*Type: Command system*
*Status: ACTIVE*
*Usage: #ARTIFACT @command [args]*

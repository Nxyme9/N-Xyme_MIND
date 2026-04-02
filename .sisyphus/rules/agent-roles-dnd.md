# Agent Roles - D&D Style
## Each Agent is a Character with Inventory, Memory, and Role

---

## The Party (4 Specialists)

### 🔥 FIREFOX - The Warrior (Tank)
**Class:** Warrior
**Role:** Infrastructure Guardian
**HP:** 1000 (High endurance)
**Mana:** 100 (Low magic)

**Inventory:**
```
⚔️  Sword of Service Restarts
🛡️ Shield of Port Protection
🧪 Potion of Disk Cleanup
📜 Scroll of Network Diagnostics
🔧 Wrench of Process Management
```

**Abilities:**
- Service Bash: Kill hung processes
- Port Guard: Block unauthorized ports
- Disk Purge: Clean temp files
- Network Shield: Protect connections

**Memory:**
- Last battle: Graphiti port 8001
- Known enemies: Zombie processes, full disks
- Victory conditions: All services running

**Symbol:** 🔥⚔️🛡️

---

### ⚡ LIGHTNING - The Rogue (DPS)
**Class:** Rogue
**Role:** Software Assassin
**HP:** 600 (Medium endurance)
**Mana:** 300 (High magic)

**Inventory:**
```
🗡️ Dagger of Debugging
🧪 Poison of Error Injection
🗝️ Key of Config Parsing
🔮 Crystal of API Testing
📜 Scroll of Dependency Checks
```

**Abilities:**
- Quick Fix: Rapid code patches
- Config Decode: Parse any config file
- API Stab: Test endpoints fast
- Dependency Scan: Find missing packages

**Memory:**
- Last battle: WebSocket auth
- Known enemies: Invalid JSON, missing imports
- Victory conditions: All code working

**Symbol:** ⚡🗡️🔮

---

### 🧠 BRAIN - The Mage (Support)
**Class:** Mage
**Role:** Performance Sorcerer
**HP:** 400 (Low endurance)
**Mana:** 500 (Very high magic)

**Inventory:**
```
🔮 Orb of CPU Sight
📖 Tome of Memory Wisdom
⚗️ Elixir of GPU Boost
🧪 Potion of Network Latency
📜 Scroll of Optimization
```

**Abilities:**
- Resource Vision: See all metrics
- Memory Spell: Detect leaks
- GPU Boost: Optimize VRAM usage
- Network Warp: Reduce latency

**Memory:**
- Last battle: CPU spikes
- Known enemies: Memory leaks, VRAM overflow
- Victory conditions: All resources balanced

**Symbol:** 🧠🔮📖

---

### 🛡️ SHIELD - The Paladin (Healer)
**Class:** Paladin
**Role:** Security Guardian
**HP:** 800 (High endurance)
**Mana:** 200 (Medium magic)

**Inventory:**
```
🛡️ Shield of Authentication
⚔️ Sword of Permission Check
🧪 Potion of Key Rotation
📜 Scroll of Audit Log
🔮 Crystal of Threat Detection
```

**Abilities:**
- Auth Guard: Protect API keys
- Permission Check: Verify access rights
- Key Rotation: Refresh expired tokens
- Audit Vision: See all security events

**Memory:**
- Last battle: API key validation
- Known enemies: Expired tokens, permission denied
- Victory conditions: All access secured

**Symbol:** 🛡️⚔️🔮

---

## The Oracle (Non-Combat)

### 🔮 ORACLE - The Sage (Advisor)
**Class:** Sage
**Role:** High-Reasoning Advisor
**HP:** 300 (Low endurance)
**Mana:** 1000 (Maximum magic)

**Inventory:**
```
📚 Library of All Knowledge
🔮 Crystal Ball of Prediction
📜 Scroll of Pattern Recognition
🧪 Elixir of Deep Insight
🗝️ Key of Root Cause
```

**Abilities:**
- Pattern Vision: See across all domains
- Root Cause: Find deepest cause
- Prediction: Forecast outcomes
- Synthesis: Combine all inputs

**Memory:**
- All battles ever fought
- All patterns ever seen
- All solutions ever tried

**Symbol:** 🔮📚📜

---

## Global Memory System

### Character Sheet Format

```yaml
character:
  name: FIREFOX
  class: Warrior
  level: 42
  hp: 1000/1000
  mana: 100/100
  xp: 15000
  
inventory:
  - Sword of Service Restarts
  - Shield of Port Protection
  - Potion of Disk Cleanup
  
abilities:
  - Service Bash (Level 3)
  - Port Guard (Level 2)
  - Disk Purge (Level 4)
  
memory:
  battles_fought: 150
  victories: 142
  defeats: 8
  lessons_learned: 47
  
stats:
  strength: 90
  intelligence: 40
  wisdom: 60
  dexterity: 50
  constitution: 85
  charisma: 30
```

---

## ARTIFACT Commands

When you type `#ARTIFACT` followed by a command:

### @plan - Create a plan
```
#ARTIFACT @plan [description]
→ Generates a plan using Oracle + all specialists
```

### @attack - Deploy specialist
```
#ARTIFACT @attack [target]
→ Deploys appropriate specialist to fix issue
```

### @inventory - Check agent status
```
#ARTIFACT @inventory [agent]
→ Shows agent's current inventory and stats
```

### @memory - Recall past battles
```
#ARTIFACT @memory [query]
→ Searches global memory for similar issues
```

### @party - Show all agents
```
#ARTIFACT @party
→ Shows status of all 4 specialists + Oracle
```

### @quest - Start a quest
```
#ARTIFACT @quest [objective]
→ Deploys full party to achieve objective
```

### @heal - Repair agent
```
#ARTIFACT @heal [agent]
→ Resets agent, clears cache, restores HP
```

### @levelup - Improve agent
```
#ARTIFACT @levelup [agent]
→ Adds new ability or improves existing
```

---

## Implementation

```python
class AgentCharacter:
    """D&D-style agent with inventory and memory."""
    
    def __init__(self, name, agent_class, role):
        self.name = name
        self.agent_class = agent_class
        self.role = role
        self.level = 1
        self.hp = 1000
        self.mana = 100
        self.xp = 0
        self.inventory = []
        self.abilities = []
        self.memory = {
            "battles_fought": 0,
            "victories": 0,
            "defeats": 0,
            "lessons_learned": []
        }
    
    def attack(self, target):
        """Deploy agent to fix issue."""
        result = self.fight(target)
        self.gain_xp(result.xp_gained)
        self.remember(result.lesson)
        return result
    
    def remember(self, lesson):
        """Add to global memory."""
        self.memory["lessons_learned"].append(lesson)
        graphiti.add_episode(f"{self.name} learned: {lesson}")
```

---

## The Party Composition

```
┌─────────────────────────────────────────────────────────┐
│              THE PARTY                                   │
│                                                         │
│  🔥⚔️🛡️ FIREFOX          ⚡🗡️🔮 LIGHTNING        │
│  Warrior                  Rogue                        │
│  Tank                     DPS                          │
│  HP: 1000                 HP: 600                      │
│                                                         │
│  🧠🔮📖 BRAIN            🛡️⚔️🔮 SHIELD            │
│  Mage                     Paladin                      │
│  Support                  Healer                       │
│  HP: 400                  HP: 800                      │
│                                                         │
│  🔮📚📜 ORACLE                                        │
│  Sage                                                   │
│  Advisor                                                │
│  HP: 300                                                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

*Created: March 19, 2026*
*Type: D&D Agent Schema*
*Status: ACTIVE*
*Party Level: 42*

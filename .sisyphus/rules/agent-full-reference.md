# Agent Full Reference
## Tags, Prompts, and Simple Explanations

---

## AGENT 1: FIREFOX (Infrastructure)

### Tags
```
#firefox          - This agent's ID
#infrastructure   - Hardware, services, connectivity
#hardware         - Physical components
#services         - Running services (Ollama, Graphiti, etc)
#network          - Internet, VPN, ports
#disk             - Storage, files, permissions
#critical         - System completely down
#high             - Major impact
#ollama           - Ollama service specifically
#graphiti         - Graphiti memory service
#neo4j            - Neo4j database
#crash            - Process died
#timeout          - Took too long
#overflow         - Resource exceeded limit
```

### Prompt
```
You are FIREFOX, the Infrastructure Specialist.
Your job: Fix infrastructure failures immediately.

CURRENT EMERGENCY:
{emergency_description}

YOUR SPECIALTY:
- Ollama/Graphiti/Neo4j services
- Network connectivity
- Disk space and I/O
- Process management
- System resources

YOUR LEARNED PATTERNS:
{learned_patterns}

RESPOND WITH:
1. Root cause (1 sentence)
2. Immediate fix (exact commands)
3. Prevention (what to check next time)

BE FAST. BE SPECIFIC. BE DECISIVE.
```

### Simple Explanation
FIREFOX is your **emergency plumber**. When pipes burst (services crash, disk fills, network dies), FIREFOX knows exactly which valve to turn. Doesn't analyze why the pipe burst - just fixes it NOW.

---

## AGENT 2: LIGHTNING (Software)

### Tags
```
#lightning        - This agent's ID
#software         - Code, configuration
#code             - Programming errors
#config           - Configuration files
#dependencies     - Python packages, modules
#api              - API endpoints
#websocket        - WebSocket connections
#agent-loop       - Main agent loop
#import           - Import errors
#module           - Module not found
#corruption       - File/data corruption
#misconfiguration - Wrong settings
```

### Prompt
```
You are LIGHTNING, the Software Specialist.
Your job: Fix software failures immediately.

CURRENT EMERGENCY:
{emergency_description}

YOUR SPECIALTY:
- Agent loop and orchestration
- API endpoints and WebSocket
- Configuration files
- Python dependencies
- Import and module errors

YOUR LEARNED PATTERNS:
{learned_patterns}

RESPOND WITH:
1. Root cause (1 sentence)
2. Immediate fix (exact code/commands)
3. Prevention (what to test next time)

BE FAST. BE SPECIFIC. BE DECISIVE.
```

### Simple Explanation
LIGHTNING is your **emergency electrician**. When wires cross (code breaks, configs wrong, imports fail), LIGHTNING knows exactly which wire to reconnect. Doesn't redesign the circuit - just restores power NOW.

---

## AGENT 3: BRAIN (Performance)

### Tags
```
#brain            - This agent's ID
#performance      - Speed, efficiency
#cpu              - CPU usage
#memory           - RAM usage
#gpu              - GPU/VRAM usage
#disk-io          - Disk read/write speed
#network          - Network latency
#optimization     - Making things faster
#bottleneck       - What's slowing things down
#slow             - Takes too long
#latency          - Delay
#high             - Resource at 80%+
#critical         - Resource at 95%+
```

### Prompt
```
You are BRAIN, the Performance Specialist.
Your job: Fix performance failures immediately.

CURRENT EMERGENCY:
{emergency_description}

YOUR SPECIALTY:
- CPU optimization
- Memory management
- Disk I/O bottlenecks
- Network latency
- Process prioritization

YOUR LEARNED PATTERNS:
{learned_patterns}

RESPOND WITH:
1. Root cause (1 sentence)
2. Immediate fix (exact commands)
3. Prevention (what to monitor next time)

BE FAST. BE SPECIFIC. BE DECISIVE.
```

### Simple Explanation
BRAIN is your **emergency doctor**. When body parts fail (CPU maxed, memory full, disk slow), BRAIN knows exactly which organ needs attention. Doesn't perform surgery - just stabilizes the patient NOW.

---

## AGENT 4: SHIELD (Security)

### Tags
```
#shield           - This agent's ID
#security         - Safety, protection
#api-keys         - API authentication keys
#permissions      - File/process permissions
#auth             - Authentication
#tokens           - Session tokens
#denied           - Access denied
#compromised      - Security breach
#expired          - Token/key expired
#network          - Network security
#firewall         - Firewall rules
```

### Prompt
```
You are SHIELD, the Security Specialist.
Your job: Fix security failures immediately.

CURRENT EMERGENCY:
{emergency_description}

YOUR SPECIALTY:
- API key management
- File permissions
- Authentication tokens
- Network security
- Access control

YOUR LEARNED PATTERNS:
{learned_patterns}

RESPOND WITH:
1. Root cause (1 sentence)
2. Immediate fix (exact commands)
3. Prevention (what to audit next time)

BE FAST. BE SPECIFIC. BE DECISIVE.
```

### Simple Explanation
SHIELD is your **emergency security guard**. When locks break (keys invalid, permissions wrong, auth fails), SHIELD knows exactly which lock to replace. Doesn't redesign security - just restores access NOW.

---

## TAG MEANINGS (Simple)

### By Specialist
```
#firefox   = Infrastructure specialist
#lightning = Software specialist
#brain     = Performance specialist
#shield    = Security specialist
```

### By Severity
```
#critical = System completely DOWN
#high     = Major BROKEN functionality
#medium   = Minor BROKEN functionality
#low      = Cosmetic BROKEN functionality
```

### By Component
```
#ollama    = Ollama service (AI models)
#graphiti  = Graphiti service (memory)
#neo4j     = Neo4j database
#api       = API server (port 8088)
#websocket = WebSocket connections
#config    = Configuration files
#disk      = Storage/files
#network   = Internet/connectivity
#cpu       = CPU usage
#memory    = RAM usage
#gpu       = GPU/VRAM usage
```

### By Problem Type
```
#crash           = Process DIED
#timeout         = Took TOO LONG
#corruption      = Data BROKEN
#overflow        = Resource EXCEEDED
#conflict        = Two things FIGHTING
#misconfiguration = Settings WRONG
```

---

## WHEN TO USE EACH AGENT

### Use FIREFOX when:
- Service won't start
- Disk is full
- Network is down
- Process is hung
- Port is blocked

### Use LIGHTNING when:
- Code throws error
- Config file wrong
- Import fails
- API returns 500
- WebSocket disconnects

### Use BRAIN when:
- CPU at 100%
- Memory full
- Disk slow
- Network laggy
- Everything slow

### Use SHIELD when:
- API key invalid
- Permission denied
- Auth token expired
- Access blocked
- Security alert

---

## LEARNING WORKFLOWS

### Firefox Workflows
```
workflow_001: Ollama Recovery
  Steps: Check process → Check VRAM → Kill if hung → Restart → Verify
  Tags: #firefox #ollama #vram #crash

workflow_002: Disk Space Recovery
  Steps: Check usage → Find large files → Clean temp → Verify
  Tags: #firefox #disk #overflow

workflow_003: Network Recovery
  Steps: Check connectivity → Restart adapter → Verify
  Tags: #firefox #network #timeout
```

### Lightning Workflows
```
workflow_004: Config Fix
  Steps: Read config → Validate JSON → Fix errors → Reload
  Tags: #lightning #config #corruption

workflow_005: Import Fix
  Steps: Check module → Install if missing → Verify import
  Tags: #lightning #import #module

workflow_006: API Fix
  Steps: Check endpoint → Check auth → Check logs → Fix
  Tags: #lightning #api #timeout
```

### Brain Workflows
```
workflow_007: CPU Fix
  Steps: Check processes → Kill heavy ones → Verify
  Tags: #brain #cpu #high

workflow_008: Memory Fix
  Steps: Check usage → Clear cache → Verify
  Tags: #brain #memory #overflow

workflow_009: GPU Fix
  Steps: Check VRAM → Unload models → Verify
  Tags: #brain #gpu #overflow
```

### Shield Workflows
```
workflow_010: API Key Fix
  Steps: Check key → Regenerate if expired → Update config → Verify
  Tags: #shield #api-keys #expired

workflow_011: Permission Fix
  Steps: Check permissions → Fix if wrong → Verify
  Tags: #shield #permissions #denied

workflow_012: Auth Fix
  Steps: Check token → Refresh if expired → Verify
  Tags: #shield #auth #expired
```

---

## PATTERN RECALL

When you see an issue 3+ times:

```
"This matches pattern_042 from 3 days ago"
"FIREFOX fixed it with: ollama serve"
"Deploying FIREFOX with learned workflow..."
```

Pattern confidence increases with each successful fix:
- 1st fix: 60% confidence
- 2nd fix: 75% confidence
- 3rd fix: 90% confidence
- 4th+ fix: 95% confidence

---

## COMMANDS

### Trigger NUCLEAR MELTDOWN
```
You: "NUCLEAR MELTDOWN"
System: Deploying all 4 specialists...
```

### Trigger Specific Specialist
```
You: "NUCLEAR MELTDOWN - Firefox only"
System: Deploying FIREFOX specialist...
```

### Trigger with Symptoms
```
You: "NUCLEAR MELTDOWN - Ollama crashed, VRAM 100%"
System: Deploying FIREFOX + BRAIN specialists...
```

### Recall Pattern
```
You: "Have we seen this before?"
System: Pattern pattern_042 matches (95% confidence)
System: FIREFOX fixed it 3 days ago with: ollama serve
```

---

## SUMMARY

**4 Specialists:**
- 🔥 FIREFOX = Infrastructure (fixes hardware/services)
- ⚡ LIGHTNING = Software (fixes code/config)
- 🧠 BRAIN = Performance (fixes speed/resources)
- 🛡️ SHIELD = Security (fixes keys/permissions)

**Tag System:**
- Specialist tags identify who handles what
- Severity tags show how bad it is
- Component tags show what's broken
- Problem tags show what type of failure

**Learning System:**
- Each specialist learns from incidents
- Builds patterns and workflows
- Can be recalled for similar issues
- Gets smarter with every fix

**Command:**
- "NUCLEAR MELTDOWN" = Deploy specialists
- System auto-selects who to deploy
- Specialists diagnose and fix
- Learning is registered automatically

---

*Reference created: March 19, 2026*
*Status: ACTIVE*
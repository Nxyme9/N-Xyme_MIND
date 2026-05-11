# NUCLEAR MELTDOWN Protocol
## Specialized Emergency Response Team

---

## Trigger Command

**"NUCLEAR MELTDOWN"**

When you say this command, 4 specialized agents deploy immediately.

---

## The Specialist Team

### 🔥 FIREFOX (Infrastructure Specialist)
**Role:** Fix infrastructure failures (Ollama, Graphiti, Network, Disk)
**Specialty:** Hardware, services, connectivity
**Learning:** Builds knowledge of infrastructure patterns
**Tags:** `#infrastructure` `#hardware` `#services` `#network` `#disk`

**Prompt Template:**
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

### ⚡ LIGHTNING (Software Specialist)
**Role:** Fix software failures (Agent Loop, API, Config, Dependencies)
**Specialty:** Code, configuration, integrations
**Learning:** Builds knowledge of software patterns
**Tags:** `#software` `#code` `#config` `#dependencies` `#api`

**Prompt Template:**
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

### 🧠 BRAIN (Performance Specialist)
**Role:** Fix performance failures (CPU, Memory, Disk I/O, Network)
**Specialty:** Optimization, resource management, bottlenecks
**Learning:** Builds knowledge of performance patterns
**Tags:** `#performance` `#cpu` `#memory` `#disk-io` `#network` `#optimization`

**Prompt Template:**
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

### 🛡️ SHIELD (Security Specialist)
**Role:** Fix security failures (API Keys, Permissions, Auth, Network)
**Specialty:** Security, authentication, access control
**Learning:** Builds knowledge of security patterns
**Tags:** `#security` `#api-keys` `#permissions` `#auth` `#network`

**Prompt Template:**
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

---

## Knowledge Base Structure

### Per-Specialist Learning

Each specialist maintains their own knowledge base:

```
data/specialists/
├── firefox/
│   ├── patterns.json          # Learned patterns
│   ├── incidents.json         # Past incidents
│   ├── solutions.json         # Proven solutions
│   └── tags.json              # Tag index
├── lightning/
│   ├── patterns.json
│   ├── incidents.json
│   ├── solutions.json
│   └── tags.json
├── brain/
│   ├── patterns.json
│   ├── incidents.json
│   ├── solutions.json
│   └── tags.json
└── shield/
    ├── patterns.json
    ├── incidents.json
    ├── solutions.json
    └── tags.json
```

### Pattern Format
```json
{
  "id": "pattern_001",
  "specialist": "firefox",
  "category": "infrastructure",
  "tags": ["#ollama", "#vram", "#crash"],
  "symptoms": ["Ollama process not responding", "VRAM at 100%"],
  "root_cause": "Multiple models loaded simultaneously exceeding VRAM",
  "solution": "Unload unused models, set max_models=2",
  "prevention": "Monitor VRAM usage, limit concurrent models",
  "confidence": 0.95,
  "incidents_seen": 5,
  "last_seen": "2026-03-19T03:00:00Z"
}
```

### Incident Format
```json
{
  "id": "incident_042",
  "timestamp": "2026-03-19T03:00:00Z",
  "specialist": "firefox",
  "emergency": "Ollama crashed due to VRAM overflow",
  "symptoms": ["Process not responding", "VRAM 100%", "API timeout"],
  "diagnosis": "llava:7b + qwen2.5-coder loaded simultaneously",
  "fix_applied": "pkill ollama && ollama serve",
  "time_to_fix": 15,
  "success": true,
  "tags": ["#ollama", "#vram", "#crash", "#infrastructure"],
  "learned_pattern": "pattern_001"
}
```

---

## NUCLEAR MELTDOWN Trigger Flow

### When You Say "NUCLEAR MELTDOWN":

```
1. SYSTEM DETECTS command "NUCLEAR MELTDOWN"
2. SYSTEM CAPTURES current error/symptoms
3. SYSTEM CLASSIFIES emergency type
4. SYSTEM SELECTS appropriate specialist(s)
5. SYSTEM LOADS specialist's learned patterns
6. SYSTEM DEPLOY specialist with emergency context
7. SPECIALIST RESPONDS with diagnosis + fix
8. SYSTEM REGISTERS incident + learning
9. SYSTEM UPDATES specialist's knowledge base
10. SYSTEM REPORTS results to you
```

### Classification Logic

```python
def classify_emergency(symptoms: str) -> List[str]:
    """Determine which specialist(s) to deploy."""
    
    specialists = []
    
    # Infrastructure keywords
    if any(word in symptoms.lower() for word in 
           ["ollama", "graphiti", "neo4j", "network", "disk", "service", "process"]):
        specialists.append("firefox")
    
    # Software keywords
    if any(word in symptoms.lower() for word in 
           ["agent", "api", "config", "import", "module", "code", "error"]):
        specialists.append("lightning")
    
    # Performance keywords
    if any(word in symptoms.lower() for word in 
           ["cpu", "memory", "slow", "timeout", "latency", "bottleneck"]):
        specialists.append("brain")
    
    # Security keywords
    if any(word in symptoms.lower() for word in 
           ["key", "permission", "auth", "denied", "security", "token"]):
        specialists.append("shield")
    
    # Default: deploy all if unclear
    if not specialists:
        specialists = ["firefox", "lightning", "brain", "shield"]
    
    return specialists
```

---

## Learning & Growth

### Automatic Learning Process

After each NUCLEAR MELTDOWN:

1. **Pattern Detection**
   - Compare symptoms to known patterns
   - If match found: Update pattern confidence
   - If no match: Create new pattern

2. **Solution Validation**
   - Did the fix work?
   - How long did it take?
   - What was the confidence?

3. **Knowledge Update**
   - Add incident to history
   - Update pattern statistics
   - Refine tags and categories

4. **Cross-Specialist Learning**
   - Share patterns between specialists
   - Identify multi-domain issues
   - Build team coordination

### Growth Metrics

```python
@dataclass
class SpecialistMetrics:
    specialist: str
    total_incidents: int
    successful_fixes: int
    avg_fix_time: float
    patterns_learned: int
    confidence_score: float
    tags_mastered: List[str]
    
    @property
    def expertise_level(self) -> str:
        if self.confidence_score >= 0.9:
            return "MASTER"
        elif self.confidence_score >= 0.7:
            return "EXPERT"
        elif self.confidence_score >= 0.5:
            return "SKILLED"
        else:
            return "NOVICE"
```

---

## Recall System

### When Facing Persistent Issues

If you see the same issue 3+ times:

```
SYSTEM: "This issue matches pattern_042 from 3 days ago."
SYSTEM: "FIREFOX specialist fixed it with: [solution]"
SYSTEM: "Want me to deploy FIREFOX again?"
```

### Pattern Recall Query

```python
def recall_specialist(issue: str) -> Optional[Specialist]:
    """Find specialist who has solved similar issues."""
    
    # Search patterns by similarity
    similar_patterns = search_patterns(issue, limit=3)
    
    if similar_patterns:
        best_match = similar_patterns[0]
        specialist = load_specialist(best_match.specialist)
        
        return {
            "specialist": specialist.name,
            "confidence": best_match.confidence,
            "past_solution": best_match.solution,
            "incidents_seen": best_match.incidents_seen,
            "last_success": best_match.last_seen
        }
    
    return None
```

---

## Tag System

### Tag Categories

**By Specialist:**
- `#firefox` - Infrastructure
- `#lightning` - Software
- `#brain` - Performance
- `#shield` - Security

**By Severity:**
- `#critical` - System down
- `#high` - Major impact
- `#medium` - Moderate impact
- `#low` - Minor issue

**By Component:**
- `#ollama` - Ollama service
- `#graphiti` - Graphiti memory
- `#neo4j` - Neo4j database
- `#api` - API server
- `#websocket` - WebSocket
- `#config` - Configuration
- `#disk` - Disk/storage
- `#network` - Network
- `#cpu` - CPU
- `#memory` - Memory/RAM
- `#gpu` - GPU/VRAM

**By Pattern:**
- `#crash` - Process crash
- `#timeout` - Timeout error
- `#corruption` - Data corruption
- `#overflow` - Resource overflow
- `#conflict` - Resource conflict
- `#misconfiguration` - Wrong config

### Tag Index

Each specialist maintains a tag index:

```json
{
  "#ollama": {
    "specialist": "firefox",
    "pattern_count": 5,
    "incidents": 12,
    "success_rate": 0.92,
    "common_causes": ["VRAM overflow", "model corruption", "API timeout"]
  }
}
```

---

## Condensed Learning Workflows

### Workflow Format

```json
{
  "id": "workflow_001",
  "specialist": "firefox",
  "name": "Ollama Recovery",
  "triggers": ["Ollama not responding", "VRAM 100%"],
  "steps": [
    {
      "order": 1,
      "action": "Check if process is running",
      "command": "tasklist | findstr ollama",
      "expected": "ollama.exe"
    },
    {
      "order": 2,
      "action": "Check VRAM usage",
      "command": "nvidia-smi --query-gpu=memory.used --format=csv",
      "expected": "< 10000 MiB"
    },
    {
      "order": 3,
      "action": "Kill process if hung",
      "command": "taskkill /F /IM ollama.exe",
      "expected": "SUCCESS"
    },
    {
      "order": 4,
      "action": "Restart service",
      "command": "ollama serve",
      "expected": "listening on 11434"
    },
    {
      "order": 5,
      "action": "Verify health",
      "command": "curl http://localhost:11434/api/tags",
      "expected": "200 OK"
    }
  ],
  "avg_time_seconds": 30,
  "success_rate": 0.95,
  "learned_from": ["incident_042", "incident_087", "incident_156"]
}
```

### Workflow Recall

When a known issue appears:

```
SYSTEM: "This matches workflow_001: Ollama Recovery"
SYSTEM: "5 steps, avg 30 seconds, 95% success rate"
SYSTEM: "Deploying FIREFOX with this workflow..."
```

---

## Integration with Global Memory

### Graphiti Episodes

Each NUCLEAR MELTDOWN creates episodes:

```json
{
  "method": "graphiti_add_episode",
  "params": {
    "text": "NUCLEAR MELTDOWN: Ollama crashed. FIREFOX diagnosed VRAM overflow. Fixed in 15s. Pattern: pattern_001.",
    "metadata": {
      "type": "nuclear_meltdown",
      "specialist": "firefox",
      "incident_id": "incident_042",
      "pattern_id": "pattern_001",
      "tags": ["#nuclear_meltdown", "#firefox", "#ollama", "#vram"],
      "success": true,
      "fix_time_seconds": 15
    }
  }
}
```

### Search Recall

When you ask "Have we seen this before?":

```
Graphiti search: "Ollama crash VRAM"
Results:
1. Pattern pattern_001 (confidence: 0.95, seen 5 times)
2. Incident incident_042 (15s fix, 3 days ago)
3. Workflow workflow_001 (5 steps, 95% success)
```

---

## Starting NUCLEAR MELTDOWN

### Command
```
You: "NUCLEAR MELTDOWN - Ollama crashed"
System: Deploying FIREFOX specialist...
FIREFOX: [diagnosis + fix]
System: Registered incident_043. Pattern updated.
```

### With Specific Symptoms
```
You: "NUCLEAR MELTDOWN - API returning 500 errors"
System: Deploying LIGHTNING specialist...
LIGHTNING: [diagnosis + fix]
System: Registered incident_044. Pattern updated.
```

### Multiple Specialists
```
You: "NUCLEAR MELTDOWN - Everything is slow"
System: Deploying FIREFOX + BRAIN specialists...
FIREFOX: [infrastructure diagnosis]
BRAIN: [performance diagnosis]
System: Registered incident_045. Patterns updated.
```

---

## Summary

**Say "NUCLEAR MELTDOWN" → 4 specialists deploy**

Each specialist:
- Has their own expertise domain
- Learns from every incident
- Builds pattern knowledge
- Creates condensed workflows
- Can be recalled for similar issues

The team grows smarter with every meltdown.

---

*Protocol created: March 19, 2026*
*Status: ACTIVE*
*Command: NUCLEAR MELTDOWN*

# N-Xyme MIND — Master Delegation Chain of Command v2.0
**Production specification for routing decisions across all agents.**

---

## 1. THE 5 CORE AGENTS

| # | Agent | Role | Model | Session | Protocol |
|---|-------|------|-------|---------|----------|
| 1 | **Catalyst** | Orchestrator | deepseek-v4 (1M ctx) | Permanent daemon | Classify → Research → Plan → Validate → Delegate |
| 2 | **Hephaestus** | Builder | deepseek-v4 (1M ctx) | Permanent daemon | Hotload → Build → Quality → Review |
| 3 | **Atlas** | Plan Executor | deepseek-v4 (1M ctx) | Permanent daemon | Sprint Plan → Track → Execute → Report |
| 4 | **Hermes** | Memory & Personal | deepseek-v4 (1M ctx) | Permanent daemon | Recall → Search → Consolidate → Support |
| 5 | **Mnemosyne** | Debugger & Knowledge | deepseek-v4 (1M ctx) | Permanent daemon | Trace → Reconstruct → Analyze → Report |

## 2. REGISTERED SUBAGENTS (spawnable on demand)

| Agent | Model | Role | Tools |
|-------|-------|------|-------|
| Prometheus - Planner | deepseek-v4 | Strategic planning | Read, memory, delegate |
| Explore - Search | minimax-m2.5 | Codebase search | grep, glob, read, search_code |
| Librarian - Research | deepseek-v4 | External web research | web_search, web_fetch |
| Momus - Critic | deepseek-v4 | Adversarial review | code_review, memory_search, code_search |
| Metis - Consultant | minimax-m2.5 | Assumption surfacing | Read, memory, search |
| Oracle - Architecture | deepseek-v4 | Architecture analysis | code_search, code_review, memory_search |
| Phi-4 Reasoner | ring-2.6-1t | Deep multi-step reasoning | Full read, memory, delegate |
| Scalpel - Code Dissector | qwen3.6-plus | Code decomposition | Read, search |
| Sisyphus Junior - Code Writer | minimax-m2.5 | Quick code edits | Write, edit, bash |
| Cortex - Memory & Knowledge | deepseek-v4 | Memory pipeline | Memory ops, embed |
| Jarvis - Personal Assistant | minimax-m2.5 | General assistance | Read, memory, delegate |
| Kairos - Personal Therapist | minimax-m2.5 | Therapy protocol | Memory, read, ask |
| Mr. White - Chemistry | deepseek-v4 | Chemistry lab | Read, write, bash |
| Vision Analyst | qwen3.6-plus | Image analysis | Read images, describe |
| Master Debugger | deepseek-v4 | System diagnostics | Process scan, service check |
| Red Team | deepseek-v4 | Security/quality audit | Full read, review, memory |
| System Architect | deepseek-v4 | Architecture mapping | Full read, project_map |
| Agent Builder | deepseek-v4 | Meta-agent creation | Full file ops, config, register |

## 3. MASTER ROUTING TREE

```
INCOMING REQUEST
│
├── Catalyst (entry — always first)
│   │
│   ├── PHASE 0: Adaptive Router
│   │   ├── crucible: estimate complexity (SIMPLE|MEDIUM|COMPLEX|UNKNOWN)
│   │   ├── alembic: score confidence (0-100%)
│   │   └── select pipeline:
│   │       SIMPLE+≥90% → Sisyphus Junior (no verify)
│   │       SIMPLE+70-89% → Sisyphus Junior (verify gate)
│   │       SIMPLE+50-69% → ESCALATE to Hephaestus
│   │       MEDIUM+≥70% → Hephaestus (skip verify if ≥90%)
│   │       MEDIUM+50-69% → Oracle → Hephaestus
│   │       COMPLEX+≥90% → Hephaestus (auto derisk)
│   │       COMPLEX+50-89% → Oracle → Hephaestus (verify)
│   │       UNKNOWN → Explore/Librarian → reroute
│   │       Any+<30% → STOP + user report
│   │
│   ├── [QUICK] → answer directly from memory
│   │
│   ├── [PLAN] → PHASE 2→3→4→5
│   │   ├── RESEARCH (PHASE 2):
│   │   │   ├── External → delegate_task("Librarian - Research", topic)
│   │   │   ├── Deep reasoning → delegate_task("Phi-4 Reasoner", problem)
│   │   │   └── Code patterns → delegate_task("Explore - Search", pattern)
│   │   ├── ARCHITECTURE (PHASE 3):
│   │   │   ├── System design → delegate_task("Oracle - Architecture", spec)
│   │   │   ├── Detailed plan → delegate_task("Prometheus - Planner", goal)
│   │   │   └── Assumptions → delegate_task("Metis - Consultant", decision)
│   │   ├── VALIDATE (PHASE 4):
│   │   │   ├── Adversarial review → delegate_task("Momus - Critic", plan)
│   │   │   ├── Build agent → delegate_task("Agent Builder", spec)
│   │   │   └── Security audit → delegate_task("Red Team", target)
│   │   └── DELEGATE (PHASE 5):
│   │       ├── Code execution → delegate_task("Hephaestus - Builder", spec)
│   │       ├── Execution tracking → delegate_task("Atlas - Plan Executor", plan)
│   │       └── Memory/knowledge → delegate_task("Hermes - Memory & Personal", task)
│   │
│   ├── [CODE] → delegate_task("Hephaestus - Builder", spec)
│   │   ├── Hephaestus PHASE 1: Complex → skill("Scalpel") or delegate "Scalpel - Code Dissector"
│   │   ├── Hephaestus PHASE 2: Simple → skill("Sisyphus Junior")
│   │   ├── Hephaestus PHASE 2: Chemistry → skill("Mr. White")
│   │   └── Hephaestus PHASE 4: Review → delegate_task("Momus - Critic", code)
│   │
│   ├── [TRACK] → delegate_task("Atlas - Plan Executor", plan)
│   │   ├── Atlas → skill("bmad-create-story") → skill("bmad-dev-story")
│   │   ├── Atlas → delegate_task("Hephaestus - Builder", story)
│   │   ├── Atlas → delegate_task("Phi-4 Reasoner", deps)
│   │   └── Atlas → skill("bmad-sprint-status") → skill("bmad-retrospective")
│   │
│   ├── [MEMORY] → delegate_task("Hermes - Memory & Personal", query)
│   │   ├── Hermes → skill("bmad-memory-recall")
│   │   ├── Hermes → skill("bmad-memory-consolidate")
│   │   └── Hermes → skill("memory-ingestion") / skill("auto-tagger")
│   │
│   ├── [THERAPY] → delegate_task("Hermes - Memory & Personal", msg)
│   │   └── Hermes → skill("Kairos") → skill("nx-kairos-therapy")
│   │
│   ├── [RESEARCH] → delegate_task("Librarian - Research", topic)
│   │   └── Deep → delegate_task("Phi-4 Reasoner", problem)
│   │
│   ├── [DEBUG] → delegate_task("Mnemosyne - Debugger", symptom)
│   │   ├── Mnemosyne → skill("mnemosyne-debug") → 5-lens analysis
│   │   ├── Process health → delegate_task("Master Debugger", symptom)
│   │   └── Security → delegate_task("Red Team", target)
│   │
│   ├── [PERSONAL] → delegate_task("Hermes - Memory & Personal", query)
│   │   └── Hermes → skill("Jarvis")
│   │
│   └── [UNKNOWN] → skill("bmad-help") → classify or ask user
│
├── Hephaestus (delegated to for code)
│   ├── Complex dissection → skill("Scalpel") or delegate "Scalpel - Code Dissector"
│   ├── Quick edits → skill("Sisyphus Junior")
│   ├── Safety checks → delegate_task("Momus - Critic", code)
│   └── Architecture → delegate_task("Oracle - Architecture", pattern)
│
├── Atlas (delegated to for tracking)
│   ├── Code stories → delegate_task("Hephaestus - Builder", story)
│   ├── Research → delegate_task("Librarian - Research", topic)
│   ├── Dependencies → delegate_task("Phi-4 Reasoner", problem)
│   └── Code search → delegate_task("Explore - Search", pattern)
│
├── Hermes (delegated to for memory/knowledge)
│   ├── Web research → delegate_task("Librarian - Research", topic)
│   ├── Deep reasoning → delegate_task("Phi-4 Reasoner", question)
│   ├── Code search → delegate_task("Explore - Search", pattern)
│   ├── Architecture → delegate_task("Oracle - Architecture", system)
│   └── Image analysis → delegate_task("Vision Analyst", image)
│
└── Mnemosyne (delegated to for debug/diagnose)
    ├── Fix implementation → delegate_task("Hephaestus - Builder", fix)
    ├── Code review evidence → delegate_task("Momus - Critic", code)
    └── Historical context → delegate_task("Hermes - Memory & Personal", recall)
```

## 4. DELEGATION FORMAT TEMPLATES

### Catalyst → Hephaestus (Code Task)
```
delegate_task("Hephaestus - Builder", "TASK: {description}
FILES:
- {path} — {requirements}
CRITERIA:
- {verifiable outcome 1}
- {verifiable outcome 2}
CONTEXT:
- {references, patterns to follow, files to read first}
CONSTRAINTS:
- {boundaries: what NOT to do}")
```

### Catalyst → Atlas (Execution/Tracking)
```
delegate_task("Atlas - Plan Executor", "PLAN: {name}
TASKS:
- [ ] {task 1} — {description}
- [ ] {task 2} — {description}
DEPS:
- {task 1} → {task 2}
CRITERIA:
- {done when: condition}")
```

### Catalyst → Hermes (Memory/Knowledge)
```
delegate_task("Hermes - Memory & Personal", "RECALL: {topic/question}
CONTEXT: {what we already know}
FORMAT: {summary with sources / full recall}")
```

### Catalyst → Hermes (Therapy)
```
delegate_task("Hermes - Memory & Personal", "THERAPY: {user message}
SESSION: {continuity context if any}")
```

### Catalyst → Mnemosyne (Debug)
```
delegate_task("Mnemosyne - Debugger", "DEBUG: {symptom description}
SCOPE: {affected agents / time window / session IDs}
SEVERITY: {critical | high | medium | low}")
```

### Any → Librarian (External Research)
```
delegate_task("Librarian - Research", "RESEARCH: {topic}
SCOPE: {domain / technology / market}
DEPTH: {quick · 1-2 sources | deep · 3-5 sources | exhaustive}")
```

### Any → Momus (Adversarial Review)
```
delegate_task("Momus - Critic", "REVIEW: {what to review}
TYPE: {plan | code | config | architecture}
LENSES: {all | specific lenses}
CONTEXT: {what to check against}")
```

## 5. TIMEOUT THRESHOLDS

| Agent | Default | Hard Limit | Retry | Fallback After |
|-------|---------|------------|-------|----------------|
| Hephaestus | 300s | 600s | 2 | 3rd → user report |
| Atlas | 120s | 300s | 2 | 3rd → Catalyst manual |
| Hermes | 120s | 300s | 2 | 3rd → Cortex |
| Mnemosyne | 180s | 300s | 2 | 3rd → Master Debugger |
| Librarian | 120s | 300s | 1 | 2nd → cached memory |
| Oracle | 180s | 300s | 1 | 2nd → System Architect |
| Phi-4 Reasoner | 300s | 600s | 1 | 2nd → Oracle |
| Momus | 120s | 300s | 1 | 2nd → Red Team |
| Prometheus | 180s | 300s | 1 | 2nd → Catalyst manual |
| Explore | 60s | 180s | 1 | 2nd → manual grep |
| Scalpel | 180s | 300s | 1 | 2nd → Explore |
| Sisyphus Junior | 60s | 120s | 0 | → Hephaestus |
| Vision Analyst | 120s | 240s | 1 | 2nd → Hermes describes |
| Metis | 120s | 240s | 1 | 2nd → skip |
| Red Team | 300s | 600s | 1 | 2nd → accept risk |
| Agent Builder | 300s | 600s | 1 | 2nd → partial build report |

## 6. FALLBACK CHAINS (complete)

| Target Agent | Fallback 1 | Fallback 2 | Escalation |
|-------------|-----------|------------|------------|
| **Hephaestus** | Scalpel (analysis only) | Sisyphus Junior (simple edits) | User report |
| **Atlas** | Catalyst (manual tracking) | Direct answer to user | N/A |
| **Hermes** | Cortex (memory ops only) | Direct answer (no memory) | N/A |
| **Mnemosyne** | Master Debugger (system check) | Red Team (security audit) | "Inconclusive" |
| **Librarian** | Direct web_fetch from caller | Cached memory results | "Insufficient sources" |
| **Oracle** | System Architect (broad map) | Explore + caller synthesis | "Analysis partial" |
| **Phi-4 Reasoner** | Oracle (shallower analysis) | Catalyst manual reasoning | "Cannot solve" |
| **Momus** | Red Team (security review) | Self-review by caller | Accept residual risk |
| **Prometheus** | Catalyst manual plan | User-provided plan | "Plan not generated" |
| **Explore** | Direct file_grep by caller | Manual file_glob | N/A |
| **Scalpel** | Explore (pattern search) | Direct read by Hephaestus | Hephaestus manual analysis |
| **Sisyphus Junior** | Hephaestus (takes over) | Scalpel (analysis, then build) | Hephaestus manual |
| **Kairos** | Hermes (support, no therapy) | Jarvis (general assistance) | Crisis protocol → professional |
| **Vision Analyst** | Hermes describes image | N/A | "Cannot analyze" |
| **Agent Builder** | Manual template + write | Partial registration | Report incomplete |

## 7. HARD BOUNDARIES

| Agent | NEVER Does | Why | What Instead |
|-------|-----------|-----|-------------|
| **Catalyst** | Write code, bash, file edit, therapy | tools.json + plugin enforcement | Delegate to specialist |
| **Hephaestus** | Therapy, planning, research, architecture analysis | Identity rule + missing tools | Delegate up/out |
| **Atlas** | Write code, therapy, external research | Identity rule + missing tools | Delegate to Hephaestus/Librarian |
| **Hermes** | Write code, bash, file delete, code review | Identity rule + no write tools | Delegate to Hephaestus/Momus |
| **Mnemosyne** | Write code, modify agents, therapy, bash | Identity rule + no write tools | Delegate to Hephaestus |

## 8. PROTOCOL ENFORCEMENT

### 8.1 Mandatory Audit Trail
After EVERY delegation, write to memory:
```
write_memory("delegation:{session_id}:{from}→{to}", {
  from: "Catalyst",
  to: "Hephaestus - Builder",
  task: "TASK: ...",
  tool: "delegate_task" | "call_omo_agent",
  timeout_seconds: 300,
  status: "success" | "timeout" | "error" | "fallback",
  duration_ms: 45231,
  fallback_used: null | "Sisyphus Junior",
  result_summary: "3 files written, tests pass",
  errors: []
})
```

### 8.2 Validation Checklist (run after every delegate_task returns)
```
[✅]  delegate_task was used (not task())
[✅]  Target agent name matches EXACT opencode.json entry
[✅]  Task string had TASK:, FILES:, CRITERIA: sections
[✅]  Response received within timeout
[✅]  Response is valid (not error/malformed)
[✅]  Result verified against delegation criteria
[✅]  Memory written: delegation:{id}
```

### 8.3 Violation Severity Levels

| Level | Example | Response |
|-------|---------|----------|
| **CRITICAL** | `task()` used, identity drift, tool boundary violation | ABORT → Mnemosyne debug → Red Team audit → user report |
| **HIGH** | Quality gate skipped, delegation to wrong agent | PAUSE → Mnemosyne debug → fix before proceeding |
| **MEDIUM** | Minor protocol deviation, missing audit trail | LOG → continue → flag in session report |

### 8.4 The 5 Delegation Commandments
1. **Catalyst is entry point.** No agent delegates directly to user or spawns independent sessions.
2. **One blocking delegate per agent at a time.** No parallel `delegate_task` to same agent.
3. **Verify AFTER delegation, not before.** Trust but verify.
4. **Max 3 delegation hops.** Catalyst→Atlas→Hephaestus→Momus = max. Break longer chains.
5. **Audit EVERY delegation.** `write_memory("delegation:{id}", ...)` mandatory.

## 9. DELEGATION TOOL SELECTION

| Tool | Blocking | Identity | When to Use |
|------|----------|----------|-------------|
| `delegate_task` | ✅ Yes | ✅ Propagates | **ALWAYS prefer this.** Need result before continuing. |
| `call_omo_agent` | ❌ No | ✅ Propagates | Fire-and-forget: parallel sub-tasks, logging, notifications. |
| `task()` | ❌ No | ❌ Drops identity | **NEVER USE.** Loses parentSessionID and agent identity. |

## 10. QUICK REFERENCE: ROUTING BY REQUEST TYPE

```
User says "build X"         → [CODE]    → Hephaestus
User says "plan Y"          → [PLAN]    → Research → Architecture → Validate → Delegate
User says "track Z"         → [TRACK]   → Atlas
User says "remember..."     → [MEMORY]  → Hermes
User says "I feel..."       → [THERAPY] → Hermes → Kairos
User says "research..."     → [RESEARCH]→ Librarian
User says "why did X break" → [DEBUG]   → Mnemosyne
User says "help me with..." → [PERSONAL]→ Hermes → Jarvis
User asks a question        → [QUICK]   → answer directly
User says "build an agent"  → [PLAN]    → Agent Builder
User says "review this"     → [PLAN]    → Momus
User says "architecture?"   → [PLAN]    → Oracle
```

## 11. SELF-CORRECTION: WHAT TO DO WHEN DELEGATION FAILS

```
IF timeout:
  1. Retry with exponential backoff (5s → 15s → 30s → 60s)
  2. After 3 retries → use fallback from chain
  3. Log: write_memory("delegation:{id}:fallback", {reason, fallback_used})

IF error response:
  1. Read error details
  2. If fixable → re-delegate with error context
  3. If not fixable → use fallback chain
  4. Log: write_memory("delegation:{id}:error", {error, action_taken})

IF result doesn't meet criteria:
  1. Re-delegate with specific failure feedback (max 2 retries)
  2. If still failing → escalate to fallback
  3. Log: write_memory("delegation:{id}:validation_failure", {criteria_not_met})
```

# N-Xyme MIND — OMO-Based Master Plan

**Date:** 2026-05-18
**Scope:** Orchestration architecture redesign using OMO backbone
**Goal:** Simplify from 19 agents → 4 agents + 2 sub-agents under OMO orchestration

---

## 1. Architecture Overview

### The Core Insight

OMO (Open Multi-Agent Orchestration) replaces the custom Catalyst orchestrator. OMO provides: adaptive routing, identity propagation, fractal delegation, confidence gates, and memory persistence — all **built into the plugin layer** rather than encoded in agent prompts. This is the key architectural shift: routing logic lives in `ralph-autoloop.js` (the OMO plugin), not in `sisyphus/agent.js`.

The 4+2 agent model sits under OMO as **workers**, not orchestrators:

```
                      ┌─────────────────────────┐
                      │         OMO              │
                      │  (ralph-autoloop.js)     │
                      │  Adaptive router,        │
                      │  confidence gates,       │
                      │  delegation, audit       │
                      └──────────┬──────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
   ┌─────────────┐      ┌──────────────┐      ┌──────────────┐
   │  Builder     │      │  Tracker     │      │  Hermes      │
   │ (Hephaestus) │      │  (Atlas)     │      │  (Memory)    │
   │  Code only   │      │  Plan exec   │      │  Knowledge   │
   └──────┬───────┘      └──────┬───────┘      └──────┬───────┘
          │                     │                      │
          ▼                     ▼                      ▼
   ┌─────────────┐      ┌──────────────┐      ┌──────────────┐
   │  Weaver     │      │  Compactor   │      │  Mnemosyne   │
   │ (Sub-agent) │      │  (Sub-agent) │      │  (Debugger)  │
   └─────────────┘      └──────────────┘      └──────────────┘
```

### What OMO Provides (and what we keep from current infra)

| OMO Feature | Current Implementation | Status |
|-------------|----------------------|--------|
| Adaptive routing | `adaptive-router` skill | ✅ Keep as skill OMO loads |
| Identity propagation | `nx-plugin.js` _agent injection | ✅ Keep (already done) |
| Session registry | `session-registry.js` | ✅ Keep |
| Fractal delegation | `delegate_task` / `call_omo_agent` | ✅ Keep (provided by ralph-autoloop) |
| Confidence gates | `confidence-gate` skill | ✅ Keep as skill |
| Quality verification | Per-agent quality gates in prompts | ✅ Keep |
| Memory persistence | Embeddings → holographic memory | ✅ Keep |
| Tool gating | `no-code-sisyphus.js` + tools.json | ✅ Keep |

### What Changes

| Current | New | Reason |
|---------|-----|--------|
| Catalyst as orchestrator agent | OMO as routing layer (plugin level) | Routing is infrastructure, not agent behavior |
| 19 agents in config | 6 agents (4 main + 2 sub) | Cognitive load, config drift, identity loss |
| Agent prompts contain routing logic | Agent prompts only contain domain protocol | Separation of concerns |
| Manual delegation routing | OMO adaptive router decides pipeline | Confidence-based optimization |
| 2 config files | Single `opencode.json` (nx_agents.json deprecated for custom keys) | Simpler sync |

---

## 2. Agent Definitions

### 2.1 Builder (Hephaestus) — Main Agent

**Role:** Pure implementation. Writes code. Nothing else.

**Model:** `deepseek-v4-flash-free` (1M context)

**Protocol:** `Hotload → Build → Quality → Review`
- PHASE 0: Structured CoT (nx-hephaestus-hotload)
- PHASE 1: Build (parallel file writes)
- PHASE 2: Quality gates (fmt → lint → test)
- PHASE 3: Self-review + optional review by sub-agents

**Skills it loads:**
- `nx-hephaestus-hotload` — Structured CoT before ANY code
- `nx-hephaestus-build` — Parallel file writing
- `nx-hephaestus-quality-gates` — fmt, lint, test, audit
- `bmad-code-review` — Adversarial code review
- (Conditional) `Scalpel` — Code decomposition for complex codebases
- (Conditional) `Sisyphus Junior` — Simple quick edits (uses minimax model)
- (Conditional) `Mr. White` — Chemistry lab safety

**Never:** Plans, tracks, researches, talks to users, does therapy.
**Tools:** All file write/edit/read, bash, search, delegate_task, memory_write.

### 2.2 Tracker (Atlas) — Main Agent

**Role:** Plan execution and progress tracking. The project manager.

**Model:** `deepseek-v4-flash-free` (1M context)

**Protocol:** `Load → Analyze → Execute → Track → Report`
- PHASE 1: Load plan (from OMO or user)
- PHASE 2: Analyze dependencies, group independent tasks
- PHASE 3: Execute each task via delegate_task
- PHASE 4: Track every task status in memory
- PHASE 5: Report progress (every 3 tasks or on query)

**Skills it loads:**
- `bmad-sprint-planning` — Parse epics into sprint plan
- `bmad-sprint-status` — Status reports
- `bmad-dev-story` — Story-level execution flow
- `nx-masterplan-track` — Cross-workstream tracking
- `bmad-retrospective` — Post-epic review

**Never:** Writes code, does therapy, researches externally (delegates those).
**Tools:** delegate_task, read/search, memory, no write/edit.

### 2.3 Hermes — Main Agent

**Role:** Memory, knowledge, personal support. The librarian + therapist.

**Model:** `deepseek-v4-flash-free` (1M context)

**Protocol:** `Recall → Search → Consolidate → Support`
- PHASE 1: Memory recall (check what's known before responding)
- PHASE 2: Multi-source search (memory, web, codebase)
- PHASE 3: Consolidate learnings after interaction
- PHASE 4: Support (answer, therapy, research synthesis)

**Skills it loads:**
- `bmad-memory-recall` — Context recall
- `bmad-memory-consolidate` — Save to memory
- `search-orchestrator` — Multi-filter search
- `memory-ingestion` → `auto-tagger` → `relevance-scorer` (Cortex pipeline)
- (Conditional) `Kairos` — Therapy protocol
- (Conditional) `Librarian` — External web research
- (Conditional) `Jarvis` — Personal assistance
- (Conditional) `Phi-4 Reasoner` — Deep reasoning (delegate_task)
- (Conditional) `Vision Analyst` — Image analysis (delegate_task)

**Never:** Writes code, executes build commands, plans sprints.
**Tools:** Memory operations, file read, web search, delegate_task, no write/edit.

### 2.4 Weaver — Sub-Agent

**Role:** Skill synthesis + prompt engineering + architecture analysis. Replaces Oracle, Phi-4 Reasoner, and Agent Builder as separate agents. One "deep thinker" sub-agent.

**Model:** `ring-2.6-1t-free` (262K context — best for reasoning)

**Protocol:** `Analyze → Synthesize → Recommend`
- PHASE 1: Deep analysis (architecture, prompt structure, code design)
- PHASE 2: Cross-domain synthesis (combine code + memory + research)
- PHASE 3: Output structured recommendations

**Skills it loads:**
- `bmad-create-architecture` — Solution architecture
- `prompt-engineer` — Prompt structure analysis
- `agent-builder` — Meta-agent creation
- `orchestration-learner` — Pattern learning
- (via delegate) `Phi-4 Reasoner` — Deep multi-step reasoning

**Never:** Writes production code, modifies agents directly, executes builds.
**Tools:** Read, search, memory read/write, delegate_task to Builder. **Read-only + prompt output.**

### 2.5 Compactor — Sub-Agent

**Role:** Memory maintenance. Runs periodically (not on-demand). Handles dedup, compaction, health monitoring.

**Model:** `deepseek-v4-flash-free`

**Protocol:** `Health → Dedup → Compact → Report`
- Runs every N sessions or on explicit request
- Checks memory health (coverage, freshness, gaps)
- Runs semantic dedup (cosine > 0.95)
- Clusters and compacts vectors
- Reports memory health dashboard

**Skills it loads:**
- `memory-health-monitor` — Dashboard
- `semantic-dedup` — Near-duplicate detection
- `memory-compactor` — Vector clustering
- `relevance-scorer` — Quality scoring

### 2.6 Mnemosyne — Sub-Agent (Read-Only Forensics)

**Role:** Cross-agent debugger and forensic analyzer. Traces causality across the system.

**Model:** `deepseek-v4-flash-free`

**Protocol:** `Trace → Reconstruct → Analyze → Report`
- Traces backward causality (what led to this state?)
- Reconstructs agent state at failure point
- Analyzes through 5 lenses: Identity Drift, Tool Boundary, Delegation Break, Hallucination, Quality Gate Skip
- Outputs structured DEBUG REPORT

**Skills it loads:**
- `mnemosyne-debug` — Full debug methodology
- `search-orchestrator` — Memory search
- (via delegate) `Momus` — Adversarial review

**Never:** Writes code, modifies agents, edits files, executes bash.
**Tools:** Read-only file ops, search, memory read/write (reports only), delegate_task to Builder for fixes.

---

## 3. OMO Modifications for N-Xyme

### 3.1 What OMO Needs

The stock OMO pattern provides:
- Ralph Loop (iteration engine) — already in `ralph-autoloop.js` ✅
- `delegate_task` (blocking) — already implemented ✅
- `call_omo_agent` (fire-and-forget) — already implemented ✅
- Confidence gates — provided by `confidence-gate` skill ✅
- Adaptive routing — provided by `adaptive-router` skill ✅

### 3.2 What We Add

**1. N-Xyme Identity Enrichment**

The `nx-plugin.js` already injects `_agent` into every tool call. But OMO's ralph-autoloop doesn't use it for routing decisions yet. We add:

```
// In ralph-autoloop.js, add a routing layer before delegation:
function routeTask(task, confidence, complexity, history) {
  // Load adaptive-router skill to select pipeline
  // Returns: { agent, pipeline, verifyRequired }
}
```

**2. Tool Telemetry Integration**

The `tool-telemetry.js` lib records success/failure per agent+tool. OMO should read this when making routing decisions:

```
// In OMO's confidence gate, include telemetry signal:
effectiveConfidence = baseConfidence * (1 - failureRatePenalty(agent, taskCategory))
```

**3. Session Registry for Chain-of-Delagation Tracing**

The `session-registry.js` already tracks `parentID → childID` chains. OMO should write to this for EVERY delegation so we can trace the full chain:

```
registry.register(childSessionID, {
  agent: targetAgent,
  title: `[sync] ${targetAgent}: ${task}`,
  parentID: parentSessionID
})
```

(This already happens — we just verify it's universal.)

### 3.3 OMO Configuration (New)

```json
{
  "omo": {
    "adaptive_routing": {
      "enabled": true,
      "default_model": "opencode/deepseek-v4-flash-free",
      "confidence_thresholds": {
        "stop": 0.30,
        "explore": 0.50,
        "direct": 0.70,
        "skip_verify": 0.90
      },
      "max_delegation_hops": 3,
      "catalyst_enabled": true
    },
    "models": {
      "default": "opencode/deepseek-v4-flash-free",
      "cheap": "opencode/minimax-m2.5-free",
      "reasoning": "opencode/ring-2.6-1t-free",
      "vision": "opencode/qwen3.6-plus-free"
    },
    "memory": {
      "recall_on_start": true,
      "consolidate_on_complete": true,
      "max_inject_tokens": 0.15
    }
  }
}
```

### 3.4 The Routing Table

OMO uses this decision matrix (loaded from `adaptive-router` skill):

| Complexity | Confidence < 30% | 30-49% | 50-69% | 70-89% | ≥ 90% |
|-----------|-------------------|--------|--------|--------|-------|
| SIMPLE | Explore | SisyphusJr+verify | SisyphusJr+verify | SisyphusJr | SisyphusJr(parallel) |
| MEDIUM | Explore | Oracle→Builder | Builder+verify | Builder | Builder(skip verify) |
| COMPLEX | STOP | Explore→Oracle→Builder | Oracle→Builder+verify | Oracle→Builder | Builder+parallel |
| UNKNOWN | Explore+user | Explore+Oracle | Explore→reroute | Explore→reroute | Reroute SIMPLE |

---

## 4. Prompt Engineering Standards

### 4.1 Universal Agent.js Template

Every agent.js follows this exact structure:

```
export default {
  name: "<Agent Name>",
  mode: "<primary|subagent>",
  model: "opencode/<model-id>",
  description: "<ONE LINE ROLE STATEMENT>",
  skills: ["<skills loaded automatically>"],
  prompt: `
══╡ IDENTITY ╞═══════════════════════════════════
You are <NAME> — <ROLE>.
You <DO THIS>. You NEVER <THAT>.

══╡ CORE PROTOCOL — N PHASES ╞══════════════════
PHASE 1: <NAME>
- <step>
- <step>

PHASE 2: <NAME>
...

══╡ SKILL POOL ╞═════════════════════════════════
Skills you load on demand:
- "<skill>" → <what it does>

══╡ TOOLS ╞══════════════════════════════════════
- <tool> — <what it does>

══╡ DELEGATION ╞═════════════════════════════════
<what> → agent("<Agent Name>", <task format>)
<what> → delegate_task("<Agent Name>", ...)

══╡ HARD RULES ╞═════════════════════════════════
1. NO <forbidden thing>

══╡ ANTI-HALLUCINATION ╞═════════════════════════
See data/anti-hallucination-rules.md

══╡ QUALITY GATE ╞═══════════════════════════════
Before declaring done:
[ ] Check 1
[ ] Check 2
`
}
```

### 4.2 6-Band Specification for Delegation Tasks

Every `delegate_task` call uses this structure:

```
TASK: {description}
FILES:
- {path} — {requirements}
CRITERIA:
- {testable outcome}
CONTEXT:
- {prior work, patterns, constraints}
MUST DO:
- {critical requirements}
MUST NOT DO:
- {boundaries}
```

### 4.3 Anti-Hallucination Rules (Injected at Top of Every Prompt)

1. **READ BEFORE WRITE** — never write/edit a file you haven't read this session
2. **NO INVENTED TOOLS** — verify every tool name exists in MCP servers
3. **GREP BEFORE IMPORT** — verify every module/function exists
4. **CITE SOURCES** — reference file:line when possible
5. **FLAG UNCERTAINTY** — "high confidence" / "medium" / "speculative"
6. **RUN BEFORE DECLARING** — "this should work" is NOT evidence

### 4.4 Quality Gate Checklist (Bottom of Every Prompt)

Before declaring done:
- [ ] All files read before written
- [ ] Code compiles/builds clean (if applicable)
- [ ] Tests pass
- [ ] No invented APIs
- [ ] Memory written with results
- [ ] Delegation audit trail written

---

## 5. ML / Learning Pipeline

### 5.1 Vector Pipeline

```
Session Transcript (.jsonl)
    │
    ▼
Memory Ingestion (memory-ingestion skill)
    ├── Filter garbage (system messages, error noise)
    ├── Chunk intelligently (by topic boundary)
    ├── Tag (auto-tagger: agent, date, type, topics)
    └── Score relevance (relevance-scorer: decisions > code > errors)
    │
    ▼
Embedding (ONNX bridge → all-MiniLM-L6-v2)
    │
    ▼
Vector Store (data/memory/vectors/sessions.jsonl)
    │
    ▼
Holographic Memory Index (data/memory/holographic-memory.json)
    └── Used by nx-plugin.js for context injection on session start
```

### 5.2 Relevance Scoring Weights

| Content Type | Weight | Example |
|-------------|--------|---------|
| Decisions | 10x | "We chose React over Vue because..." |
| Code | 5x | Function implementations, patterns |
| Errors | 3x | "This failed because..." |
| Tool calls | 1x | "Used delegate_task to Hermes" |
| System | 0.1x | Timestamps, metadata |

### 5.3 Semantic Dedup Strategy

- **Threshold:** Cosine similarity > 0.95 = duplicate
- **Resolution:** Keep highest-quality version (by relevance score)
- **Trigger:** Run after every 50 new vectors OR weekly
- **Owner:** Compactor sub-agent

### 5.4 Memory Health Dashboard

Tracked by Compactor sub-agent:

```
Total vectors: {N}
Agents covered: {list}
Freshness: {last consolidation}
Coverage gaps: {agents with <10 vectors}
Search success rate: {X%}
```

### 5.5 Learning Loop

The system learns from past runs via:

1. **De-escalation tokens** (adaptive-router) — "This SIMPLE task succeeded 3x, skip verify next time"
2. **Catalyst level** — System-wide confidence accelerates pipelines
3. **Telemetry** — tool-telemetry.js tracks success/failure per agent+tool → feeds confidence scores
4. **Holographic memory** — nx-plugin.js injects relevant past context automatically

### 5.6 What 156K Vectors Enable

With 156K existing vectors, the system can:
- Recall past decisions about architecture ("last time we chose...")
- Surface similar bug fixes ("this error pattern matches...")
- Provide context for code generation ("the existing pattern for this is...")
- Detect repeated failures ("this agent has failed at this task type before")

---

## 6. Skills & Workflow Map

### 6.1 BMAD → OpenCode → OMO Mapping

| BMAD Workflow | OpenCode Skill | OMO Integration |
|--------------|---------------|-----------------|
| `bmad-build` (stories, quick dev) | → Loaded by Builder as `bmad-code-review` | OMO routes code tasks to Builder |
| `bmad-plan` (PRD, UX, architecture) | → Loaded by Weaver as `bmad-create-architecture` | OMO routes planning to Weaver → Builder |
| `bmad-review` (code review, adversarial) | → Loaded by Builder/Mnemosyne as needed | Review happens after build phase |
| `bmad-meta` (help, memory, sprint) | → Distributed across Hermes + Tracker | OMO routes meta queries by type |
| `bmad-research` (domain, market, tech) | → Loaded by Hermes as `Librarian` / `Phi-4` | OMO routes research to Hermes |
| `bmad-test` (frameworks, ATDD, CI) | → Loaded by Builder on demand | Post-build quality gate |
| `bmad-memory-consolidate` | → Loaded by Hermes | OMO triggers after every session |
| `bmad-memory-recall` | → Loaded by Hermes | OMO triggers on session start |
| `bmad-catalyst-orchestration` | → **Replaced by OMO routing** | OMO's adaptive router handles this |

### 6.2 When to Use What

| Pattern | Tool/Mechanism | When |
|---------|---------------|------|
| **Blocking delegation** | `delegate_task(agent, task, timeout)` | Need result before continuing. ALWAYS prefer this for sequential work. |
| **Fire-and-forget** | `call_omo_agent(agent, task)` | Parallel independent work, logging, notifications. Result optional. |
| **Ralph Loop** | ralph-autoloop `<promise>DONE</promise>` | Iterative tasks that need refinement. Best for code generation, research synthesis. |
| **BMAD Workflow** | `skill("<bmad-workflow>")` → follow steps | Structured multi-phase processes (PRD creation, sprint planning, architecture). |
| **Load Skill** | `skill("<skill-name>")` | Get domain-specific instructions. You follow the skill. |
| **Direct answer** | (none) | Quick questions, status checks, simple recall. |

### 6.3 Skill Loading by Agent

| Agent | Automatically Loaded | Conditionally Loaded |
|-------|---------------------|---------------------|
| OMO (routing) | `adaptive-router`, `confidence-gate` | `bmad-help` (if uncertain) |
| Builder | `nx-hephaestus-hotload`, `nx-hephaestus-build`, `nx-hephaestus-quality-gates`, `bmad-code-review` | `scalpel`, `sisyphus-junior`, `mr-white` |
| Tracker | `bmad-sprint-planning`, `bmad-sprint-status`, `nx-masterplan-track` | `bmad-dev-story`, `bmad-retrospective`, `bmad-create-story` |
| Hermes | `bmad-memory-recall`, `bmad-memory-consolidate`, `search-orchestrator` | `kairos`, `librarian`, `jarvis`, `phi-4-reasoner`, `vision-analyst`, cortex skills |
| Weaver | `bmad-create-architecture`, `prompt-engineer`, `agent-builder` | `orchestration-learner`, `phi-4-reasoner` |
| Compactor | `memory-health-monitor`, `semantic-dedup`, `memory-compactor` | `relevance-scorer` |
| Mnemosyne | `mnemosyne-debug`, `search-orchestrator` | `mommus` (via delegate) |

### 6.4 OMO Plugin Hooks Integration

| Hook | Plugin | What It Does |
|------|--------|-------------|
| `session.created` | nx-plugin | Injects _agent identity, holographic memory, dictation catch-up |
| `session.created` | ralph-autoloop | Registers session in registry, starts Ralph Loop if active |
| `tool.execute.before` | nx-plugin | Injects _agent into output.args for MCP servers |
| `tool.execute.before` | no-code-sisyphus | Enforces tools.json per agent (allowed/blocked/scoped) |
| `tool.execute.after` | nx-plugin | Logs BMAD keyword suggestions, telemetry |
| `tool.execute.after` | no-code-sisyphus | Logs audit trail, delete-bypass detection |
| `message.updated` | ralph-autoloop | Main loop tick — checks for promise tags, injects continuation |
| `experimental.session.compacting` | ralph-autoloop | Preserves loop state across compactions |
| `experimental.session.compacting` | nx-plugin | Injects persistent context (ROOT.md) |

---

## 7. Model Selection Guide

### 7.1 Model Capabilities

| Model | Context | Output | Cost Tier | Best For |
|-------|---------|--------|-----------|----------|
| `deepseek-v4-flash-free` | 1,048,576 | 384,000 | Free | Default: orchestration, building, memory, tracking |
| `minimax-m2.5-free` | 204,800 | 65,536 | Free (cheaper) | Simple edits, therapy, personal assistant, quick queries |
| `qwen3.6-plus-free` | 1,048,576 | 65,536 | Free | Vision analysis, code dissection (Scalpel) |
| `ring-2.6-1t-free` | 262,144 | 65,536 | Free | Deep reasoning, architecture analysis, prompt engineering |
| `trinity-large-preview-free` | 131,072 | 32,768 | Free | Experimental, fallback only |

### 7.2 Routing Rules

| Task Type | Primary Model | Fallback | Why |
|-----------|--------------|----------|-----|
| Code generation | deepseek-v4 | qwen3.6 | Deepseek has 384K output = can generate large files |
| Simple edit (< 5 lines) | minimax | deepseek | Cheaper, fast for trivial changes |
| Memory recall | deepseek-v4 | minimax | Deepseek context window can hold more memory |
| Therapy session | minimax | deepseek | Kairos protocol is interactive, not context-heavy |
| Deep reasoning (5+ steps) | ring-2.6 | deepseek-v4 | Ring-2.6 is spec'd for reasoning tasks |
| Image analysis | qwen3.6 | deepseek-v4 | Qwen has vision capabilities |
| Sprint tracking | deepseek-v4 | minimax | Needs context of full sprint plan |
| Architecture analysis | ring-2.6 | deepseek-v4 | Ring's deep reasoning for trade-off analysis |
| Prompt engineering | ring-2.6 | deepseek-v4 | Prompt structure needs careful reasoning |
| Memory compaction | deepseek-v4 | minimax | Batch processing needs context |

### 7.3 Catalyst-Driven Model Selection

As the Catalyst level increases, cheaper models are used where safe:

- **Level 0 (Cold):** All tasks use per-matrix model
- **Level 2 (Hot):** SIMPLE tasks use minimax instead of deepseek
- **Level 3 (Catalyzed):** MEDIUM tasks can use minimax
- **Level 4 (Critical Mass):** All tasks use cheapest safe model

---

## 8. Resource Bounds

### 8.1 Token Budgets

| Resource | Budget | Enforcement |
|----------|--------|-------------|
| Max context per agent | 1,048,576 tokens | Model limit (deepseek) |
| Context injection | 15% of budget max | nx-plugin.js |
| Ralph Loop iterations | 100 max default | ralph-autoloop (configurable) |
| Delegation timeout | 120s default (configurable per call) | delegate_task implementation |
| Fire-and-forget TTL | No timeout (background) | call_omo_agent |
| Max delegation hops | 3 | AGENTS.md rule + OMO enforcement |

### 8.2 Context Window Management

```
TOKEN BUDGET PER AGENT:
┌──────────────────────────────────────────────┐
│  SYSTEM PROMPT (agent.js)       ~2,000 tok   │
│  PLUGIN INJECTIONS              ~1,000 tok   │
│  HOLOGRAPHIC MEMORY              ~15% of      │
│    (nx-plugin context)           budget max   │
│  CONVERSATION HISTORY           remainder     │
│  TOOL OUTPUTS                   variable ──→  │
│                                    triggers   │
│                                    compaction │
│  COMPACTION RESERVE             10,000 tok    │
│    (auto-triggered)                           │
└──────────────────────────────────────────────┘
```

Compaction auto-triggers at 10K reserved tokens remaining.

### 8.3 Delegation Limits

| Constraint | Value | Enforced By |
|------------|-------|-------------|
| Max agents per session | 6 (4 main + 2 sub) | Config definition |
| Max blocking delegates per agent | 1 at a time | AGENTS.md rule |
| Max delegation chain depth | 3 hops | AGENTS.md rule + OMO enforcement |
| Max retries per task | 2 per agent, then escalate | Adaptive-router protocol |
| Timeout: simple task | 60s | delegate_task default |
| Timeout: complex task | 300s | delegate_task config |
| Timeout: research/debug | 180s | delegate_task config |

---

## 9. Quality Gates

### 9.1 Types of Gates

| Gate | Applies To | When | Enforcer |
|------|-----------|------|----------|
| **Identity gate** | All agents | Every response | Agent prompt (IDENTITY section) |
| **Read-before-write gate** | Builder | Every file write | no-code-sisyphus.js (audit log) + prompt rule |
| **Tool boundary gate** | All agents | Every tool call | no-code-sisyphus.js (tools.json enforcement) |
| **Quality gate** | Builder | After every build | nx-hephaestus-quality-gates (fmt→lint→test→audit) |
| **Review gate** | Builder | Complex builds | bmad-code-review (self) / Momus (delegate) |
| **Verification gate** | OMO | After every delegation | OMO adaptive-router checks result |
| **Memory gate** | Hermes | After every interaction | bmad-memory-consolidate |
| **Anti-hallucination gate** | All agents | Every response | Prompt rules |
| **Delegation audit gate** | All agents | Every delegation | write_memory("delegation:{id}", ...) |
| **Compaction gate** | Compactor | Periodic | Triggers at 10K reserved tokens |

### 9.2 Quality Gate Flow

```
EVERY OUTPUT PASSES THROUGH:

  1. IDENTITY CHECK
     [ ] Am I acting as my assigned agent?
     [ ] Am I doing only what my role allows?
     [ ] Did I check my IDENTITY section before responding?

  2. TOOL CHECK
     [ ] Are all tools I'm about to use in my tools.json?
     [ ] Did I verify the tool exists before calling it?
     [ ] Did I read the file before writing to it?

  3. HALLUCINATION CHECK
     [ ] Did I invent any tool names, API calls, or imports?
     [ ] Can I cite a source for every claim?
     [ ] Have I flagged any uncertainty?

  4. DELEGATION CHECK (if delegating)
     [ ] Did I use delegate_task (blocking) or call_omo_agent (fire-and-forget)?
     [ ] Did I include TASK + FILES + CRITERIA + CONTEXT?
     [ ] Did I record the delegation in memory?

  5. COMPLETION CHECK
     [ ] Did I run the code (if I built something)?
     [ ] Did the tests pass (if applicable)?
     [ ] Did I consolidate to memory?
     [ ] Did I report results?
```

### 9.3 Escalation Path When Gates Fail

```
GATE FAILURE → record in telemetry
    │
    ▼
┌─────────────────────────────────────────────┐
│ RETRY COUNT PER AGENT ≤ 2?                  │
│ YES → Retry with error context added         │
│ NO  → Escalate to next agent in chain       │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│ ESCALATION DEPTH ≤ 3?                        │
│ YES → Route to higher-capability agent       │
│        (SisyphusJr → Builder → Weaver)       │
│ NO  → STOP + user report with full chain     │
└─────────────────────────────────────────────┘
```

---

## Appendix: Migration Checklist

### Phase 1 — Config Simplification
- [ ] Remove 13 subagents from `opencode.json` agent list (keep as skill files)
- [ ] Update `opencode.json` to only 6 agents (4 main + 2 sub)
- [ ] Update `AGENTS.md` to reflect 4+2 structure
- [ ] Remove `nx_agents.json` or deprecate to only custom session keys
- [ ] Run `config_validate` + `sync_nx_config`

### Phase 2 — OMO Plugin Tuning
- [ ] Add adaptive routing to ralph-autoloop's routing layer
- [ ] Verify _agent injection covers all MCP servers
- [ ] Add tool telemetry data to confidence scoring
- [ ] Verify session-registry captures all delegations

### Phase 3 — Agent Prompt Updates
- [ ] Simplify Builder prompt (remove routing logic, keep build protocol)
- [ ] Simplify Tracker prompt (remove routing logic, keep track protocol)
- [ ] Simplify Hermes prompt (remove routing logic, keep memory protocol)
- [ ] Create Weaver agent.js (deep thinking + prompt engineering)
- [ ] Create Compactor agent.js (memory maintenance only)

### Phase 4 — Verification
- [ ] Test delegation: OMO → Builder → code output
- [ ] Test delegation: OMO → Tracker → plan execution
- [ ] Test delegation: OMO → Hermes → memory recall
- [ ] Test delegation: OMO → Weaver → architecture analysis
- [ ] Test delegation: OMO → Compactor → memory health
- [ ] Test delegation: OMO → Mnemosyne → debug report
- [ ] Test Ralph Loop with Builder
- [ ] Test adaptive router with confidence scoring
- [ ] Test holographic memory injection on session start
- [ ] Test tool gating for all 6 agents

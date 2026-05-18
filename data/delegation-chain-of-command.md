# N-Xyme MIND — Master Delegation Chain of Command

**Version:** 1.0  
**Design Authority:** Agent Builder (Meta-Agent Design)  
**Last Updated:** 2026-05-18  
**Status:** Ratified — ready for Catalyst routing implementation

---

## TABLE OF CONTENTS

1. [The 5 Core Agents](#1-the-5-core-agents)
2. [Complete Delegation Routing Tree](#2-complete-delegation-routing-tree)
3. [Delegation Decision Matrix](#3-delegation-decision-matrix)
4. [Escalation & Fallback Rules](#4-escalation--fallback-rules)
5. [Boundary Definitions](#5-boundary-definitions)
6. [Overlap Resolution](#6-overlap-resolution)
7. [Protocol Enforcement](#7-protocol-enforcement)
8. [Mnemosyne Integration](#8-mnemosyne-integration)
9. [Agent.js Routing Templates](#9-agentjs-routing-templates)
10. [AGENTS.md Update Block](#10-agentsmd-update-block)

---

## 1. THE 5 CORE AGENTS

### Agent Identity Table

| # | Agent | System Name | Mode | Role | Protocol | Entry By |
|---|-------|-------------|------|------|----------|----------|
| 1 | **Catalyst** | `Catalyst` | primary | Orchestrator | Classify → Research → Plan → Validate → Delegate | User (entry point) |
| 2 | **Hephaestus** | `Hephaestus - Builder` | primary | Builder | Hotload → Build → Quality → Review | Catalyst, Atlas |
| 3 | **Atlas** | `Atlas - Plan Executor` | primary | Plan Executor | Sprint Plan → Analyze → Execute → Track → Report | Catalyst |
| 4 | **Hermes** | `Hermes - Memory & Personal` | primary | Personal & Therapy | Recall → Search → Consolidate → Support | Catalyst, any agent |
| 5 | **Mnemosyne** | `Mnemosyne - Memory & Knowledge` | primary | Memory Infrastructure | Assess → Query → Retrieve → Consolidate | Catalyst, Hermes, any agent |

### Key Architectural Decision: Hermes vs Mnemosyne Split

**Hermes** = PERSONAL LAYER. Faces the human. Therapy, personal assistance, personal memory recall ("what did we talk about last session?"). Thin layer that delegates to Kairos/Jarvis for depth.

**Mnemosyne** = INFRASTRUCTURE LAYER. Faces the system. Context queries for task execution, embedding operations, memory pipeline management, knowledge retrieval for other agents. Thick layer that operates Cortex skills.

**Rule of thumb:**
- "What does the user need?" → Hermes
- "What does the system need?" → Mnemosyne
- "Is this about a person's feelings?" → Hermes
- "Is this about data retrieval for a task?" → Mnemosyne

---

## 2. COMPLETE DELEGATION ROUTING TREE

```
INCOMING REQUEST (any entry point)
│
├── [UNCLASSIFIED] ─→ Catalyst (Phase 1: CLASSIFY)
│
├── Catalyst CLASSIFICATION
│   │
│   ├── [quick]
│   │   └── Answer directly. No delegation.
│   │
│   ├── [plan]
│   │   ├── Catalyst Phase 2: Research
│   │   │   ├── If external web info needed → Librarian
│   │   │   ├── If code patterns needed   → Explore
│   │   │   └── If deep reasoning needed   → Phi-4 Reasoner
│   │   ├── Catalyst Phase 3: Plan
│   │   │   ├── If complex plan needed     → Prometheus
│   │   │   ├── If assumptions unclear     → Metis
│   │   │   └── If architecture needed     → Oracle
│   │   ├── Catalyst Phase 4: Validate
│   │   │   └── Momus (adversarial review)
│   │   └── Catalyst Phase 5: Delegate
│   │       ├── Code execution     → Atlas (track) → Hephaestus (build)
│   │       └── Pure plan (no code) → Atlas (track)
│   │
│   ├── [code]
│   │   ├── SIMPLE change (< 50 lines, single file)
│   │   │   └── Hephaestus → Sisyphus Junior skill
│   │   ├── COMPLEX build (multi-file, new features)
│   │   │   ├── Hephaestus
│   │   │   │   ├── If codebase unfamiliar → Scalpel (dissect first)
│   │   │   │   ├── If chemistry domain     → Mr. White
│   │   │   │   ├── If architecture unclear → Oracle
│   │   │   │   └── Before completing       → Momus (review)
│   │   │   └── Hephaestus returns code + quality gate report
│   │   └── CRITICAL system (infrastructure, security)
│   │       ├── Oracle (architecture analysis)
│   │       ├── Hephaestus (build)
│   │       ├── Momus (adversarial review)
│   │       └── Red Team (security audit)
│   │
│   ├── [track]
│   │   ├── Create/load plan → Atlas
│   │   ├── Execute stories  → Atlas → Hephaestus (code)
│   │   └── Review           → Atlas → Momus
│   │
│   ├── [memory_query]  ← System memory (not personal)
│   │   ├── Context for task → Mnemosyne
│   │   │   ├── Simple recall → direct
│   │   │   ├── Deep search   → search-orchestrator skill
│   │   │   └── Session ingest → Cortex memory pipeline
│   │   └── If personal context → reframe as [personal] → Hermes
│   │
│   ├── [personal]
│   │   ├── General assistance   → Hermes → Jarvis skill
│   │   ├── Therapy              → Hermes → Kairos skill
│   │   ├── Personal memory      → Hermes → search-orchestrator
│   │   └── If needs system data → Hermes → Mnemosyne (query)
│   │
│   ├── [research]
│   │   ├── Web/domain/market    → Librarian
│   │   ├── Technical deep dive  → Librarian + Phi-4 Reasoner
│   │   ├── Codebase research    → Explore
│   │   └── Visual analysis      → Vision Analyst
│   │
│   ├── [debug]  ← System diagnostics
│   │   ├── Session causality    → Mnemosyne (debug lenses)
│   │   ├── Process/service      → Master Debugger
│   │   └── Security audit       → Red Team
│   │
│   ├── [therapy]
│   │   └── Hermes → Kairos skill (therapy protocol)
│   │
│   └── [build_agent]
│       └── Agent Builder (meta-agent creation)
│
├── SUB-AGENT DELEGATION
│   │
│   ├── Hephaestus delegates TO:
│   │   ├── Scalpel    (code dissection)
│   │   ├── Sisyphus Junior (quick edits)
│   │   ├── Mr. White  (chemistry)
│   │   ├── Momus      (code review)
│   │   ├── Oracle     (architecture analysis)
│   │   ├── Explore    (code pattern search)
│   │   └── Mnemosyne  (save/recall build context)
│   │
│   ├── Atlas delegates TO:
│   │   ├── Hephaestus (code execution)
│   │   ├── Explore    (code search for context)
│   │   ├── Librarian  (external research for stories)
│   │   ├── Phi-4 Reasoner (deep reasoning for blockers)
│   │   ├── Momus      (plan review)
│   │   ├── Mnemosyne  (save/recall plan state)
│   │   └── Hermes     (personal context needed)
│   │
│   ├── Hermes delegates TO:
│   │   ├── Kairos     (therapy — load skill first, delegate if heavy)
│   │   ├── Jarvis     (personal assistance — load skill)
│   │   ├── Mnemosyne  (any system memory query)
│   │   ├── Librarian  (external research)
│   │   ├── Phi-4 Reasoner (deep reasoning)
│   │   ├── Vision     (image analysis)
│   │   ├── Explore    (codebase search)
│   │   └── Hephaestus (never — Hermes doesn't need code)
│   │
│   ├── Mnemosyne delegates TO:
│   │   ├── Cortex skills (memory-ingestion, auto-tagger, dedup, compactor)
│   │   │   Note: These are skills loaded in-process, not separate agents
│   │   ├── Explore    (codebase search for memory tagging context)
│   │   ├── search-orchestrator (multi-filter search — skill)
│   │   ├── Oracle     (architecture analysis)
│   │   ├── Hephaestus (memory pipeline code changes — rare)
│   │   └── Momus      (memory pipeline design review — rare)
│   │
│   └── Any agent → Mnemosyne
│       └── Context query: "QUERY: <topic>" → {confidence, sources, summary, gaps}
```

---

## 3. DELEGATION DECISION MATRIX

### 3.1 Catalyst → All Agents

| From | To | When (Trigger) | Delegation Format | Expected Response | Timeout |
|------|----|----------------|-------------------|-------------------|---------|
| Catalyst | Hephaestus | `[code]` task, or plan with code execution | `delegate_task("Hephaestus - Builder", "Implement: {description} FILES: {paths} CRITERIA: {testable} CONTEXT: {patterns}")` | `{success: bool, files: string[], quality_report: {fmt, lint, test, audit}}` | 180s |
| Catalyst | Atlas | `[track]` task, or plan that needs tracking | `delegate_task("Atlas - Plan Executor", "Execute plan: {plan_name} TASKS: {list} DEPENDENCIES: {graph}")` | `{status: "complete"|"partial"|"failed", tasks: {id, status, result}, blockers: string[], summary: string}` | 300s |
| Catalyst | Hermes | `[personal]` or `[therapy]` or personal memory | `delegate_task("Hermes - Memory & Personal", "{query_type}: {details}")` | Therapeutic or personal response + consolidated memory entry | 120s |
| Catalyst | Mnemosyne | `[memory_query]` — system context retrieval | `delegate_task("Mnemosyne - Memory & Knowledge", "QUERY: {topic} CONTEXT: {task description} DEPTH: {quick|deep}")` | `{confidence: float, sources: [{id, agent, date, snippet}], summary: string, gaps: string[]}` | 60s (quick), 180s (deep) |
| Catalyst | Librarian | External research needed | `call_omo_agent("Librarian - Research", "Research: {question} DEPTH: {quick|deep}")` | Research brief with findings, sources, uncertainty flags | 120s |
| Catalyst | Explore | Codebase pattern search | `call_omo_agent("Explore - Search", "Find: {pattern} in {path}")` | Ranked file list with summaries | 60s |
| Catalyst | Phi-4 Reasoner | Deep multi-step reasoning | `call_omo_agent("Phi-4 Reasoner", "Reason: {problem} CONTEXT: {relevant facts}")` | Structured reasoning chain → conclusion | 180s |
| Catalyst | Prometheus | Complex plan generation | `call_omo_agent("Prometheus - Planner", "Plan: {objective} CONSTRAINTS: {list} PRIOR_ARTIFACTS: {refs}")` | Structured plan with tasks, deps, estimates | 120s |
| Catalyst | Metis | Assumption surfacing | `call_omo_agent("Metis - Consultant", "Surface assumptions for: {plan/task}")` | Assumption list with risk levels | 60s |
| Catalyst | Momus | Adversarial review | `call_omo_agent("Momus - Critic", "Review: {plan/code} against: {criteria}")` | Findings report with severity, evidence, recommendations | 120s |
| Catalyst | Oracle | Architecture analysis | `call_omo_agent("Oracle - Architecture", "Analyze: {component/design} CONTEXT: {current state}")` | Architecture assessment with trade-offs | 120s |
| Catalyst | Agent Builder | New agent creation | `call_omo_agent("Agent Builder", "Build agent for: {description}")` | New agent.js + tools.json + registration | 180s |
| Catalyst | Vision Analyst | Image/screenshot analysis | `call_omo_agent("Vision Analyst", "Analyze: {image_path} QUESTION: {what to look for}")` | Visual analysis report | 120s |
| Catalyst | Master Debugger | Process/service diagnostics | `call_omo_agent("Master Debugger", "Debug: {symptom} SCOPE: {process/service}")` | Diagnostic report + fix or escalation | 120s |
| Catalyst | Red Team | Security/quality audit | `call_omo_agent("Red Team", "Audit: {target} LENSES: {list}")` | CVE-style findings report | 180s |

### 3.2 Hephaestus → Sub-agents

| From | To | When (Trigger) | Format | Response |
|------|----|----------------|--------|----------|
| Hephaestus | Scalpel | Codebase unfamiliar or complex | `delegate_task("Scalpel - Code Dissector", "Dissect: {path} FOCUS: {what to understand}")` | Decomposition map: files, classes, data flow, patterns |
| Hephaestus | Sisyphus Junior | Simple edit (< 50 lines, single file) | Load skill `Sisyphus Junior` pattern | Fast edit + verify |
| Hephaestus | Mr. White | Chemistry domain task | Load skill `Mr. White` | Safety-first lab procedure |
| Hephaestus | Momus | Critical system code review | `call_omo_agent("Momus - Critic", "Review code: {paths} against quality criteria")` | Adversarial review findings |
| Hephaestus | Oracle | Architecture uncertainty | `delegate_task("Oracle - Architecture", "Analyze architecture of: {description}")` | Architecture assessment |
| Hephaestus | Explore | Need code pattern examples | `call_omo_agent("Explore - Search", "Find: {pattern} in codebase")` | Pattern examples with file paths |
| Hephaestus | Mnemosyne | Save/recall build context | `call_omo_agent("Mnemosyne - Memory & Knowledge", "SAVE: {build_key}={build_state}" or "RECALL: {build_key}")` | Confirmation or stored context |

### 3.3 Atlas → Sub-agents

| From | To | When (Trigger) | Format | Response |
|------|----|----------------|--------|----------|
| Atlas | Hephaestus | Story code execution | `delegate_task("Hephaestus - Builder", "Story: {story_id} TASK: {from_story_file} CONTEXT: {plan}")` | Code + quality gate |
| Atlas | Explore | Codebase context for story | `call_omo_agent("Explore - Search", "Find: {pattern} for {story_context}")` | Ranked file results |
| Atlas | Librarian | External info for story | `call_omo_agent("Librarian - Research", "Research: {question} for story {story_id}")` | Research brief |
| Atlas | Phi-4 Reasoner | Complex blocker resolution | `call_omo_agent("Phi-4 Reasoner", "Solve: {blocker} CONTEXT: {plan_state}")` | Reasoning chain → solution |
| Atlas | Momus | Plan/story quality review | `call_omo_agent("Momus - Critic", "Review: {plan/story} for gaps and risks")` | Findings report |
| Atlas | Mnemosyne | Save/recall plan state | `call_omo_agent("Mnemosyne - Memory & Knowledge", "SAVE: atlas:plan:{name}:{key}={value}" or "RECALL: atlas:plan:{name}")` | Confirmation or stored state |

### 3.4 Hermes → Sub-agents

| From | To | When (Trigger) | Format | Response |
|------|----|----------------|--------|----------|
| Hermes | Kairos | Therapy session | Load skill `Kairos` → follow protocol. If heavy: `delegate_task("Kairos - Personal Therapist", patient_context)` | Therapeutic conversation |
| Hermes | Jarvis | General personal assistance | Load skill `Jarvis` pattern | Personal assistant response |
| Hermes | Mnemosyne | Need system memory (not personal) | `delegate_task("Mnemosyne - Memory & Knowledge", "QUERY: {topic} FOR: {user_context}")` | Structured context response |
| Hermes | Librarian | Research needed in support | `call_omo_agent("Librarian - Research", "Research: {question}")` | Research brief |
| Hermes | Phi-4 Reasoner | Complex reasoning for user | `call_omo_agent("Phi-4 Reasoner", "Reason: {user_question}")` | Reasoning output |
| Hermes | Vision | User shares image | `call_omo_agent("Vision Analyst", "Analyze: {path}")` | Visual analysis |
| Hermes | Explore | Codebase question from user | `call_omo_agent("Explore - Search", "Find: {pattern}")` | Search results |

### 3.5 Mnemosyne → Sub-agents

| From | To | When (Trigger) | Format | Response |
|------|----|----------------|--------|----------|
| Mnemosyne | — | `[query]` — context retrieval | Direct search_memory + embed_similarity | `{confidence, sources, summary, gaps}` |
| Mnemosyne | — | `[ingest]` — session processing | Load Cortex skills (ingestion → tag → score → dedup → compact) | Pipeline report |
| Mnemosyne | — | `[debug]` — causality tracing | Follow Mnemosyne debug 5-phase protocol | Structured debug report |
| Mnemosyne | Explore | Need code context for memory tagging | `call_omo_agent("Explore - Search", "Find: {topic} patterns in codebase")` | Pattern list |
| Mnemosyne | Oracle | Memory architecture review | `call_omo_agent("Oracle - Architecture", "Review memory architecture: {design}")` | Architecture assessment |
| Mnemosyne | Hephaestus | Memory pipeline code change (rare) | `delegate_task("Hephaestus - Builder", "Memory pipeline change: {spec}")` | Code + quality |
| Mnemosyne | Momus | Pipeline design review (rare) | `call_omo_agent("Momus - Critic", "Review memory pipeline: {design}")` | Review findings |

---

## 4. ESCALATION & FALLBACK RULES

### 4.1 Timeout Thresholds

| Agent Type | Soft Timeout | Hard Timeout | Action on Soft Timeout | Action on Hard Timeout |
|------------|-------------|-------------|----------------------|----------------------|
| Hephaestus | 120s | 300s | Send "status?" query | Escalate to Catalyst → retry or route to Atlas for tracking |
| Atlas | 180s | 600s | Send "progress?" query | Mark plan as blocked, report to Catalyst |
| Hermes | 60s | 180s | Send "still there?" | Escalate to Catalyst, route personal needs to alternative |
| Mnemosyne (quick) | 30s | 120s | Retry query with simpler scope | Fall back to agent's own memory_search |
| Mnemosyne (deep) | 120s | 300s | Check progress | Return partial results with gaps noted |
| Librarian | 60s | 180s | Narrow query | Return best-effort results |
| Phi-4 Reasoner | 120s | 300s | Request interim | Return partial chain |
| Scalpel | 60s | 180s | Request focus area | Return partial decomposition |
| Momus | 60s | 180s | Request lens focus | Return partial findings |

### 4.2 Escalation Chain

```
FAILURE AT ANY AGENT
│
├── [self-heal] Agent retries with:
│   ├── Reduced scope (narrow the query)
│   ├── Different approach (switch skill)
│   └── Error context added (include failure reason)
│
├── [max 2 retries exhausted] → Escalate to delegator
│   ├── Delegator receives: {error, attempts, recommendation}
│   ├── Delegator decides:
│   │   ├── Route to different agent
│   │   ├── Reduce scope and retry
│   │   ├── Delegate to Oracle for analysis
│   │   └── Report as blocked to user
│   └── If delegator is also stuck → escalate further up chain
│
└── [Catalyst escalation] Ultimate fallback:
    ├── Can decompose differently
    ├── Can route to Atlas for structured tracking
    ├── Can route to Hermes for user communication
    ├── Can route to Mnemosyne for diagnostic
    └── Can report "cannot complete" to user with diagnostic
```

### 4.3 Fallback Routes Matrix

| Intent | Primary | Fallback 1 | Fallback 2 | Fallback 3 |
|--------|---------|------------|------------|------------|
| Code - Simple | Hephaestus → Sisyphus Junior | Hephaestus (direct) | N/A | N/A |
| Code - Complex | Hephaestus → Scalpel | Hephaestus (direct) | Oracle → Hephaestus | Catalyst reports blocked |
| Code - Critical | Oracle → Hephaestus → Momus → Red Team | Hephaestus → Momus | Atlas track | User escalation |
| Memory Query (system) | Mnemosyne | Caller's direct memory_search | Caller's direct search_memory | N/A |
| Memory Query (personal) | Hermes | Mnemosyne (filtered) | Caller's direct search_memory | N/A |
| Therapy | Hermes → Kairos | Hermes (direct support) | Mnemosyne (recall past sessions) | N/A |
| Plan | Catalyst → Prometheus → Momus | Catalyst (direct) | Atlas (track from scratch) | N/A |
| Research (web) | Librarian | Phi-4 Reasoner (reasoning) | Hermes → Mnemosyne (past research) | N/A |
| Research (code) | Explore | Hephaestus (code reading) | Scalpel (dissection) | N/A |
| Architecture | Oracle | Mnemosyne (past decisions) | Explore (code patterns) | N/A |
| Debug (session) | Mnemosyne | Master Debugger | Red Team | N/A |
| Debug (process) | Master Debugger | Bash MCP direct | N/A | N/A |

### 4.4 Agent Unavailability Protocol

```
PRIMARY AGENT UNAVAILABLE (busy, stuck, crashed)

1. ✓ Immediate check: Is agent in permanent_sessions? 
   - If yes, it should always be available (daemon mode)
   - If no response, assume crashed → escalate

2. ✓ Queue discipline:
   - One task at a time per agent (NO parallel overload per agent)
   - If agent is busy: wait max 30s, then use fallback
   - Exception: call_omo_agent allows parallel (fire-and-forget OK)

3. ✓ Cascade escalation:
   delegate_task timeout → {max 2 retries} → fallback route → 
   Catalyst reclassify → user report
```

---

## 5. BOUNDARY DEFINITIONS

### 5.1 What Each Agent NEVER Does

| Agent | NEVER | Because |
|-------|-------|---------|
| **Catalyst** | Writes code, edits files, executes bash | Tools.json blocks it + no-code-sisyphus plugin |
| **Hephaestus** | Plans projects, tracks progress, does therapy | Its identity is Builder, not Planner |
| **Atlas** | Writes production code (except config/story files) | Its identity is Tracker, not Builder |
| **Hermes** | Writes code, executes build commands, does infrastructure | Its domain is personal, not system |
| **Mnemosyne** | Writes code, does therapy, gives personal advice | Its domain is memory infrastructure, not human interaction |
| **Librarian** | Writes code, modifies config, runs commands | Read-only research agent |
| **Phi-4 Reasoner** | Produces actions — reasoning only | Pure reasoning engine |
| **Momus** | Defends decisions — only critiques | Adversarial by design |
| **Oracle** | Writes code — analysis only | Read-only architecture consultant |
| **Scalpel** | Writes code — dissects only | Diagnostic tool |
| **Sisyphus Junior** | Plans, tracks, analyzes — edits only | Fast code writer |
| **Metis** | Decides — only surfaces what's unstated | Assumption revealer |
| **Prometheus** | Executes — only plans | Pure planner |
| **Kairos** | Diagnoses medically — describes patterns only | Safety constraint |
| **Jarvis** | System operations — personal assistance only | Personal domain |
| **Mr. White** | Non-chemistry work | Domain specialist |
| **Vision Analyst** | Text analysis — images only | Visual modality |
| **Master Debugger** | Fixes without diagnosis — debug-first | Fixes are Hephaestus domain |
| **Red Team** | Constructive feedback — adversarial only | Security/quality auditor |
| **Agent Builder** | Builds end-user code — meta only | Meta-agent, never user-code |

### 5.2 Tool Boundary Summary

| Tool Category | Catalyst | Hephaestus | Atlas | Hermes | Mnemosyne |
|---------------|----------|------------|-------|--------|-----------|
| file_read/grep/glob | ✓ Read-only | ✓ Full | ✓ Read-only | ✓ Read-only | ✓ Read-only |
| file_write/edit | ✗ BLOCKED | ✓ Full | ✗ Config only | ✗ BLOCKED | ✗ BLOCKED |
| bash | ✗ BLOCKED | ✓ Build/test | ✗ BLOCKED | ✗ BLOCKED | ✗ BLOCKED |
| memory ops | ✓ search/read | ✓ search/read/write | ✓ search/read/write | ✓ Full | ✓ Full |
| delegate_task | ✓ Primary user | ✓ To skills | ✓ To skills | ✓ To skills | ✓ To skills |
| call_omo_agent | ✓ Fire-and-forget | ✓ Background | ✓ Background | ✓ Background | ✓ Background |
| web_search/fetch | ✗ Blocked | ✗ Blocked | ✗ Blocked | ✓ Via Librarian | ✓ Via Librarian |
| embed_text/similarity | ✓ | ✓ | ✓ | ✓ | ✓ Primary |
| review_code | ✓ (notify only) | ✓ Full | ✓ | ✓ | ✓ |
| safe_delete | ✗ BLOCKED | ✓ Primary user | ✗ BLOCKED | ✗ BLOCKED | ✗ BLOCKED |

---

## 6. OVERLAP RESOLUTION

### 6.1 Hermes vs Mnemosyne (Memory)

**The Critical Distinction:**

| Dimension | Hermes | Mnemosyne |
|-----------|--------|-----------|
| **Consumer** | The human user | Other agents + system |
| **Query flavor** | "What did I say about X?" | "What does the system know about X?" |
| **Response style** | Conversational, supportive | Structured, with confidence & sources |
| **Storage target** | Personal context (user preferences, mood, history) | System context (decisions, code patterns, architecture) |
| **Therapy** | ✓ Kairos protocol | ✗ Never |
| **Embedding ops** | If needed, pass to Mnemosyne | ✓ Primary capability |
| **Batch ingestion** | ✗ Never | ✓ Cortex pipeline |

**Resolution Rule:**
```
IF query contains personal pronouns ("I", "my", "me", "my feelings")
  OR query is emotionally framed ("I'm feeling", "I need help with")
  → ROUTE to Hermes

ELSE IF query is about system state ("what was decided about X",
  "find the architecture for Y", "recall context for task Z")
  → ROUTE to Mnemosyne

ELSE IF query is ambiguous → DEFAULT to Mnemosyne for structured facts,
  then route personal follow-ups to Hermes
```

### 6.2 Librarian vs Phi-4 Reasoner (Research)

| Dimension | Librarian | Phi-4 Reasoner |
|-----------|-----------|----------------|
| **Data source** | Web search, web fetch, external docs | Internal reasoning (model weights) |
| **Best for** | Finding external facts, docs, tutorials | Multi-step logic, math, analysis |
| **Output** | Research brief with sources | Reasoning chain → conclusion |
| **Model** | deepseek-v4-flash-free | ring-2.6-1t-free (specialized) |
| **When to use** | "What does the web say about X?" | "Work through this logic problem" |

**Resolution Rule:**
```
IF task requires EXTERNAL INFORMATION (docs, tutorials, APIs, current events)
  → ROUTE to Librarian
  → If results need synthesis/comparison, THEN route to Phi-4 Reasoner

ELSE IF task is PURE REASONING (math, logic, analysis, comparison)
  → ROUTE to Phi-4 Reasoner

IF BOTH needed → Librarian first (get facts), then Phi-4 Reasoner (analyze them)
```

### 6.3 Scalpel vs Hephaestus (Code Analysis)

| Dimension | Scalpel | Hephaestus |
|-----------|---------|------------|
| **Role** | Understand existing code | Write new code + modify existing |
| **Output** | Decomposition report (no code changes) | Working code (with changes) |
| **When** | Before writing, when codebase is unfamiliar | After understanding, when change is clear |
| **Model** | qwen3.6-plus-free (specialized) | deepseek-v4-flash-free |

**Resolution Rule:**
```
IF codebase is unfamiliar OR task says "understand this code first"
  → Scalpel (dissect) → then Hephaestus (build)

IF codebase is familiar OR change is small (< 50 lines in known files)
  → Hephaestus directly (skip Scalpel)
```

### 6.4 Explore vs Oracle (System Understanding)

| Dimension | Explore | Oracle |
|-----------|---------|--------|
| **Scope** | Pattern finding in code | Architecture understanding |
| **Output** | Ranked file list with matches | Design analysis with trade-offs |
| **Depth** | Surface (pattern search) | Deep (read + evaluate + recommend) |

**Resolution Rule:**
```
IF need to FIND something ("Where is the X implementation?")
  → Explore

IF need to UNDERSTAND something ("How does X architecture work? Is it well-designed?")
  → Oracle

IF need BOTH → Explore first (find files), then Oracle (analyze found files)
```

### 6.5 Catalyst vs Atlas (Orchestration)

| Dimension | Catalyst | Atlas |
|-----------|----------|-------|
| **Scope** | Single request orchestration | Multi-task execution tracking |
| **Memory** | Delegates and moves on | Tracks every task to completion |
| **Best for** | One-off tasks, quick delegation | Sprint plans, story execution, multi-task |

**Resolution Rule:**
```
IF task is a SINGLE request (one code task, one query, one plan)
  → Catalyst handles directly

IF task is a PLAN with MULTIPLE DEPENDENT TASKS (sprint, epic, project)
  → Catalyst creates plan, THEN passes to Atlas for execution tracking

IF Atlas is tracking but a NEW unrelated request comes in
  → Catalyst handles new request (Atlas stays focused)
```

---

## 7. PROTOCOL ENFORCEMENT

### 7.1 What Catalyst Checks After Delegation

Every delegation result has a verification gate. Catalyst must verify:

```
AFTER EVERY delegate_task():

[✓] Tool output is valid (no MCP errors)
[✓] Result exists (not empty)
[✓] Result meets criteria specified in delegation prompt
[✓] No hallucination evidence (check for invented files/tools)
[✓] Quality gate was run (if applicable — check for compile/test output)

FAILURE → retry with error context (max 2) → escalate to fallback → report
```

### 7.2 Delegation Audit Trail

Every delegation creates a memory trace:

```
WRITE TO MEMORY:
Key: "chain:{timestamp}:{from_agent}→{to_agent}"
Value: {
  task: "summary of delegated task",
  delegation_method: "delegate_task" | "call_omo_agent",
  result: "success" | "failure" | "partial",
  duration_seconds: N,
  error: "if failure, why"
}
```

This enables Mnemosyne's debug protocol to reconstruct causality chains.

### 7.3 Violation Detection (Mnemosyne's 5 Debug Lenses)

Mnemosyne's debug protocol enforces correct delegation via 5 lenses:

| Lens | What It Detects | How |
|------|-----------------|-----|
| **Identity Drift** | Agent acted outside identity | Cross-reference agent.js IDENTITY vs session tool call log |
| **Tool Boundary** | Agent used disallowed tool | Map every tool call against agent's tools.json |
| **Delegation Break** | task() used instead of delegate_task | Scan for task() calls; check parentSessionID |
| **Hallucination** | Invented agents/tools/imports | Cross-reference mentions against filesystem |
| **Quality Gate Skip** | Verification phases skipped | Parse session for quality checklist patterns |

### 7.4 Automated Enforcement Mechanisms

| Mechanism | What It Enforces | Where |
|-----------|-----------------|-------|
| `no-code-sisyphus.js` plugin | Catalyst NEVER writes code | Plugin level — blocks write/edit for Catalyst |
| `megatools_per_agent.json` | Per-agent tool gating | MCP level — blocks unauthorized tools |
| `tools/tools.json` per agent | Fine-grained tool control | Agent level — whitelist/blacklist |
| `delegate_task` identity propagation | Correct delegation chain | Tool level — maintains parentSessionID |
| `nx-plugin.js` _agent injection | All tools receive agent identity | Plugin level — adds _agent to tool calls |

### 7.5 Session Audit Command

For post-hoc verification of delegation chains:

```
# Read recent session log
file_read("data/sessions/<latest>.jsonl")

# Search for delegation patterns
grep("delegate_task|call_omo_agent", "data/sessions/")

# Check for violations
grep("task\(\)", "data/sessions/")  ← should be empty
grep("rm ", "data/sessions/")       ← should only appear as blocked
```

---

## 8. MNEMOSYNE INTEGRATION

### 8.1 Current State → Proposed State

**Current Mnemosyne:** Exists as `Mnemosyne - Debugger` (subagent, debug-only role)

**Proposed Mnemosyne:** `Mnemosyne - Memory & Knowledge` (primary agent, memory infrastructure)

**Migration Strategy:**
1. Repurpose existing Mnemosyne agent.js from debug-only → memory infrastructure
2. Keep Mnemosyne debug capability as a skill within the new agent
3. Add memory pipeline skills (from Cortex) as loadable skills
4. Keep Cortex as a subagent for heavy ML pipeline operations
5. Register Mnemosyne as permanent session in nx_agents.json

### 8.2 Mnemosyne's Three Service Modes

```
MNEMOSYNE SERVICES
│
├── [query] — Context retrieval
│   ├── Input: "QUERY: {topic} [DEPTH: quick|deep] [FILTERS: {agent, date, type}]"
│   ├── Process: search_memory + embed_similarity + scoring
│   ├── Output: {confidence, sources[{id,agent,date,snippet}], summary, gaps[]}
│   └── Depth: quick=top 5, deep=top 20 + cross-reference
│
├── [ingest] — Memory pipeline
│   ├── Input: "INGEST: {path} [PIPELINE: tag|score|dedup|compact|all]"
│   ├── Process: load Cortex skills → run pipeline phase
│   └── Output: pipeline report {processed, errors, stats}
│
└── [debug] — Causality tracing
    ├── Input: "DEBUG: {symptom/session/agent} [LENSES: {list}]"
    ├── Process: Mnemosyne debug protocol (5 phases)
    └── Output: structured debug report with evidence chain
```

### 8.3 Mnemosyne's Position in the Chain

```
                 ┌──────────────┐
                 │   Catalyst   │
                 │ (Orchestrator)│
                 └──────┬───────┘
                        │
          ┌─────────────┼──────────────┬──────────────┐
          ▼             ▼              ▼              ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
   │ Hephaestus│ │  Atlas   │ │  Hermes  │ │  Mnemosyne   │
   │ (Builder) │ │(Executor)│ │(Personal)│ │(Memory&Know) │
   └─────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘
         │            │            │              │
         │            │            │  [query]     │
         ├── Scalpel  │            ├── Kairos     ├── search_memory
         ├── Sisyphus │            ├── Jarvis     ├── embed_similarity
         │   Junior   │            └── Mnemosyne  ├── Cortex skills
         ├── Mr. White│                              │
         ├── Momus    │                              ├── Explore
         ├── Oracle   │                              ├── Oracle
         └── Mnemosyne│                              └── Hephaestus (rare)
```

### 8.4 Integration Checklist

- [ ] Mnemosyne agent.js rewritten: memory infrastructure + debug capability
- [ ] Mnemosyne registered as primary agent in opencode.json
- [ ] Mnemosyne added to permanent_sessions in nx_agents.json
- [ ] Hermes agent.js updated: personal scope only, delegates system queries to Mnemosyne
- [ ] Catalyst agent.js updated: adds `[memory_query] → Mnemosyne` routing
- [ ] Mnemosyne tools/tools.json: memory_full ops + search + delegation
- [ ] Megatools_per_agent updated for Mnemosyne

---

## 9. AGENT.JS ROUTING TEMPLATES

### 9.1 Catalyst Delegation Code Block

Add to Catalyst's Phase 5 section (`agents/sisyphus/agent.js`):

```javascript
══╡ DELEGATION ROUTING — MASTER CHAIN ╞══════════════════════
// DEFINITIVE routing table. One question: "Which agent?"
//
// CODE           → delegate_task("Hephaestus - Builder", ...)
//   Simple edit  → Hephaestus → Sisyphus Junior skill
//   Complex      → Hephaestus → Scalpel (dissect first if needed)
//   Critical     → Oracle → Hephaestus → Momus → Red Team
//
// PLAN           → Phase 2→3→4→5, then:
//   Needs track  → delegate_task("Atlas - Plan Executor", ...)
//
// TRACK          → delegate_task("Atlas - Plan Executor", ...)
//
// MEMORY QUERY   → delegate_task("Mnemosyne - Memory & Knowledge", ...)
//   System query → QUERY format
//   For debug    → DEBUG format
//   Personal     → redirect to Hermes
//
// PERSONAL       → delegate_task("Hermes - Memory & Personal", ...)
//   Therapy      → Hermes → Kairos skill
//   Assistance   → Hermes → Jarvis skill
//
// RESEARCH       → call_omo_agent for non-blocking:
//   Web/domain   → "Librarian - Research"
//   Deep logic   → "Phi-4 Reasoner"
//   Codebase     → "Explore - Search"
//   Images       → "Vision Analyst"
//
// ARCHITECTURE   → call_omo_agent("Oracle - Architecture", ...)
// REVIEW         → call_omo_agent("Momus - Critic", ...)
// PLAN DETAIL    → call_omo_agent("Prometheus - Planner", ...)
// ASSUMPTIONS    → call_omo_agent("Metis - Consultant", ...)
// BUILD AGENT    → call_omo_agent("Agent Builder", ...)
// DEBUG SYSTEM   → call_omo_agent("Master Debugger", ...)
// SECURITY AUDIT → call_omo_agent("Red Team", ...)

══╡ DELEGATION VERIFICATION ╞════════════════════════════════
After EVERY delegation:
[✓] Result checked (not empty, no errors)
[✓] Quality gate evidence present (for code)
[✓] Memory written: "chain:{ts}:Catalyst→{target}"
[✓] Next step determined (done? loop? escalate?)

Failure → max 2 retries with error context → fallback → user report
```

### 9.2 Mnemosyne Agent.js Structure (Proposed)

```javascript
export default {
  name: "Mnemosyne - Memory & Knowledge",
  mode: "primary",
  color: "#7C4DFF",
  model: "opencode/deepseek-v4-flash-free",
  description: "Memory infrastructure & knowledge retrieval — context queries, embeddings, debug diagnostics, memory pipeline.",
  skills: [
    "search-orchestrator",
    "memory-ingestion",
    "auto-tagger",
    "relevance-scorer",
    "semantic-dedup",
    "memory-compactor",
    "memory-health-monitor",
    "mnemosyne-debug"
  ],
  prompt: `... (full Mnemosyne prompt with identity, protocols, delegation matrix)`
}
```

---

## 10. AGENTS.MD UPDATE BLOCK

Replace the current "DELEGATION FLOW" section in AGENTS.md with:

```markdown
## DELEGATION FLOW — Master Chain of Command

### The 5 Core Agents

| # | Agent | Role | Entry Path | NEVER Does |
|---|-------|------|------------|------------|
| 1 | **Catalyst** | Orchestrator | User (entry point) | Code, bash, file editing |
| 2 | **Hephaestus** | Builder | Catalyst, Atlas | Planning, tracking, therapy |
| 3 | **Atlas** | Executor | Catalyst | Production code (tracks only) |
| 4 | **Hermes** | Personal & Therapy | Catalyst, any | Code, infrastructure |
| 5 | **Mnemosyne** | Memory & Knowledge | Catalyst, Hermes, any | Code, therapy, personal advice |

### Full Delegation Tree

```
INCOMING REQUEST ──→ Catalyst (Phase 1: CLASSIFY)
│
├── [quick]          → Answer directly
├── [code]           → Hephaestus
│   ├── Simple edit  → Sisyphus Junior skill
│   ├── Complex      → Scalpel skill → Hephaestus
│   └── Critical     → Oracle → Hephaestus → Momus → Red Team
├── [plan]           → Phase 2-3-4 → Atlas (execution tracking)
├── [track]          → Atlas
├── [memory_query]   → Mnemosyne
├── [personal]       → Hermes → Jarvis skill
├── [therapy]        → Hermes → Kairos skill
├── [research]       → Librarian / Phi-4 Reasoner / Explore / Vision
├── [debug]          → Mnemosyne / Master Debugger / Red Team
├── [architecture]   → Oracle
├── [review]         → Momus
└── [build_agent]    → Agent Builder
```

### Decision Matrix (Quick Reference)

| Signal | Route To | Says WHAT |
|--------|----------|-----------|
| "Implement..." | Hephaestus | Files + criteria + context |
| "Track..." | Atlas | Plan + tasks + deps |
| "I feel..." | Hermes → Kairos | Support context |
| "What do we know about X?" | Mnemosyne | Topic + depth |
| "Research Y" | Librarian | Question + scope |
| "Review this" | Momus | Target + criteria |
| "Architecture of Z" | Oracle | Description + context |
| "Debug this failure" | Mnemosyne | Symptom + scope |

### Escalation Rules

1. **Max 2 retries** per agent before escalation
2. **Timeout → fallback** (see delegation-chain-of-command.md §4.3)
3. **Identity drift** → caught by Mnemosyne debug protocol
4. **Tool boundary violation** → blocked at MCP level by tools.json
5. **Final fallback** → Catalyst reports to user with diagnostics

### Overlap Resolution

| Overlap | Split Rule |
|---------|------------|
| Hermes vs Mnemosyne | Personal pronouns → Hermes. System state → Mnemosyne. |
| Librarian vs Phi-4 | External facts → Librarian. Pure reason → Phi-4. Both → L first, then P. |
| Scalpel vs Hephaestus | Understand → Scalpel. Build → Hephaestus. |
| Explore vs Oracle | Find → Explore. Understand → Oracle. |
| Catalyst vs Atlas | Single task → Catalyst. Multi-task execution → Atlas. |
```

---

## APPENDIX A: DEPLOYMENT CHECKLIST

### Phase 1 — Mnemosyne Creation
- [ ] Rewrite `agents/mnemosyne/agent.js` as Memory & Knowledge agent
- [ ] Create `agents/mnemosyne/tools/tools.json` (memory_full + search + delegation)
- [ ] Register Mnemosyne in `opencode.json` and `config/nx_agents.json`
- [ ] Add Mnemosyne to `permanent_sessions` in nx_agents.json

### Phase 2 — Hermes Rescoping
- [ ] Update `agents/hermes/agent.js`: clarify personal-only domain
- [ ] Add: "System memory queries → delegate to Mnemosyne"
- [ ] Update tools.json if needed

### Phase 3 — Catalyst Routing Update
- [ ] Add `[memory_query] → Mnemosyne` classification option to Catalyst agent.js
- [ ] Add delegation routing table (from §9.1)
- [ ] Add verification gate after every delegation

### Phase 4 — Config Sync
- [ ] Run `just config-sync` or `sync_nx_config agent`
- [ ] Run `config_validate` to confirm

### Phase 5 — Documentation
- [ ] Update AGENTS.md delegation section with content from §10
- [ ] Write memory entry: "Delegation chain of command ratified v1.0"

---

*End of design document. This is the definitive reference for all delegation routing in N-Xyme MIND.*

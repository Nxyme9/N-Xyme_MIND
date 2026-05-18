---
name: adaptive-router
description: "Adaptive Router — confidence-weighted pipeline selector for N-Xyme MIND. Load this at Sisyphus Phase 0 (before CLASSIFY) to estimate complexity, score confidence, select optimal agent pipeline, track success/failure history, and escalate/de-escalate dynamically. Implements the Catalyst Effect: higher confidence = faster/cheaper pipelines."
---

# Adaptive Router — SKILL

**Purpose:** A routing protocol that selects the optimal agent pipeline based on a 2D matrix of **estimated complexity** × **confidence score**. Routes dynamically, escalates on failure, de-escalates on success, and accelerates pipelines as confidence grows (Catalyst Effect).

**Loading agent:** Sisyphus (Phase 0, before CLASSIFY). Can also be loaded by Atlas.

**Prerequisites:**
- `confidence-gate` skill must be available at `agents/skills/confidence-gate/SKILL.md`
- Memory space for tracking stats: `memory:adaptive-router:*`

---

## ══╡ CORE ARCHITECTURE ╞════════════════════════════════════

```
                        ┌──────────────────────┐
                        │   TASK ENTERS         │
                        │  (user request)       │
                        └──────────┬───────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
             ┌──────┤     PHASE 0: ROUTE           ├──────┐
             │      │  1. Load confidence-gate     │      │
             │      │  2. Score confidence (C1-C5) │      │
             │      │  3. Estimate complexity      │      │
             │      │  4. Check history            │      │
             │      │  5. Apply catalyst modifier  │      │
             │      │  6. Select pipeline           │      │
             │      └──────────────┬───────────────┘      │
             │                     │                       │
             ▼                     ▼                       ▼
     ┌───────────────┐   ┌──────────────────┐   ┌──────────────────┐
     │  SIMPLE        │   │  MEDIUM           │   │  COMPLEX          │
     │  pipeline      │   │  pipeline         │   │  pipeline         │
     └───────┬───────┘   └───────┬──────────┘   └───────┬──────────┘
             │                   │                       │
             ▼                   ▼                       ▼
     ┌───────────────┐   ┌──────────────────┐   ┌──────────────────┐
     │ Sisyphus Jr.  │   │   Hephaestus     │   │  Oracle →        │
     │ (minimax)     │   │  (deepseek)      │   │  Hephaestus      │
     └───────┬───────┘   └───────┬──────────┘   └───────┬──────────┘
             │                   │                       │
             ▼                   ▼                       ▼
       ┌──────────┐       ┌──────────┐           ┌──────────┐
       │ RESULT   │       │ RESULT   │           │ RESULT   │
       │ + verify │       │ + verify │           │ + verify │
       └────┬─────┘       └────┬─────┘           └────┬─────┘
            │                  │                       │
            ▼                  ▼                       ▼
     ┌──────────────────────────────────────────────────────┐
     │           POST-ROUTE: TRACK & ADAPT                  │
     │  • Record success/failure in memory                  │
     │  • If failure → apply escalation matrix              │
     │  • If success → optionally de-escalate for future    │
     │  • Update catalyst state                             │
     └──────────────────────────────────────────────────────┘
```

---

## ══╡ SECTION 1: COMPLEXITY ESTIMATION ╞═══════════════════

### The Estimation Formula

Complexity is estimated from the **task description** using keyword/pattern matching across 4 bands:

```
COMPLEXITY_BAND = classify(task_description)

Bands:
  SIMPLE    → score=1
  MEDIUM    → score=2
  COMPLEX   → score=3
  UNKNOWN   → score=0 (trigger exploration first)
```

### Keyword Classification Table

| Band | Keywords & Patterns | Typical Ask |
|------|--------------------|-------------|
| **SIMPLE** | `typo`, `fix typo`, `rename`, `update`, `bump`, `change`, `edit config`, `add comment`, `simple`, `small`, `quick`, `trivial`, `one-line`, `1 file`, `single file`, `docs`, `docstring`, `readme` | Single-file edits, config bumps, comment fixes, simple renames |
| **MEDIUM** | `implement`, `add feature`, `create function`, `new component`, `refactor`, `modify`, `extend`, `test`, `tests`, `bug fix`, `bug`, `fix`, `error`, `broken`, `style`, `format`, `2 files`, `both files` | Moderate additions, bug fixes spanning 1-3 files, small features |
| **COMPLEX** | `architecture`, `design`, `new system`, `migrate`, `restructure`, `build from scratch`, `multi-file`, `new feature`, `integration`, `3+ files`, `new service`, `new module`, `new pipeline`, `complex`, `large`, `epic`, `story`, `refactor entire`, `redesign`, `rearchitect` | New subsystems, cross-cutting changes, architectural changes |
| **UNKNOWN** | No match in any category, or task mentions `research`, `explore`, `find`, `search`, `investigate`, `understand`, `how does`, `what is`, `find pattern`, `lookup` | Research, exploration, investigation |

### File Count Heuristic

If the task mentions specific file counts, use them:

```
"1 file" / "single file" / "one file"   → SIMPLE
"2 files" / "both files"                 → MEDIUM
"3+ files" / "multiple files" / "multi-file" → COMPLEX
"several files" / "many files"           → COMPLEX
```

### Pattern Matching Algorithm

```
1. Normalize task: lowercase, strip punctuation
2. Check file count keywords first (if present, override)
3. Check COMPLEX keywords
4. Check SIMPLE keywords (narrow matches first)
5. Check MEDIUM keywords (catch-all for implementation tasks)
6. If no match → UNKNOWN
```

---

## ══╡ SECTION 2: THE 2D ROUTING MATRIX ╞══════════════════

### Primary Matrix: Complexity × Confidence → Route

```
                    CONFIDENCE SCORE
            < 30%     30-49%     50-69%     70-89%     ≥ 90%
            ─────────────────────────────────────────────────
SIMPLE   │  EXPLORE   SISYPHUSJr  SISYPHUSJr  SISYPHUSJr  SISYPHUSJr
         │  + Oracle  + verify    + verify    (direct)    (parallel)
         │
MEDIUM   │  EXPLORE   ORACLE →   HEPHAESTUS  HEPHAESTUS  HEPHAESTUS
         │  + Oracle  HEPHAESTUS + verify    (verify)    (skip verify)
         │
COMPLEX  │  STOP      ORACLE →   ORACLE →    ORACLE →    HEPHAESTUS
         │  (user)    EXPLORE →  HEPHAESTUS  HEPHAESTUS  + parallel
         │            HEPHAESTUS + verify    (light verify)  derisk
         │
UNKNOWN  │  EXPLORE   EXPLORE    EXPLORE →   EXPLORE →   Reroute
         │  + user    + Oracle   reroute     reroute     to SIMPLE
```

### Route Legend

| Route Code | Meaning | Agents | Model |
|------------|---------|--------|-------|
| **SISYPHUSJr** | Route to Sisyphus Junior | Sisyphus Junior | minimax-m2.5-free (204K) |
| **HEPHAESTUS** | Route to Hephaestus | Hephaestus | deepseek-v4-flash-free (1M) |
| **ORACLE → HEPHAESTUS** | Oracle analysis first, then Hephaestus implements | Oracle then Hephaestus | deepseek (both) |
| **EXPLORE → ...** | Explore codebase first, then reroute | Explore then re-evaluate | minimax then reroute |
| **STOP** | Do not proceed, ask user | — | — |

### Route Selection Pseudocode

```
function select_route(complexity, confidence, history):
    // Apply catalyst modifier to confidence (Section 4)
    effective_confidence = apply_catalyst(confidence, history)
    
    // Look up in matrix
    route = MATRIX[complexity][effective_confidence.band]
    
    // Apply escalation override (Section 5)
    if history.escalation_count > 0:
        route = escalate(route, history)
    
    // Apply de-escalation override (Section 6)
    if history.consecutive_successes >= 3:
        route = deescalate(route)
    
    return route
```

---

## ══╡ SECTION 3: CONFIDENCE GATE INTEGRATION ╞══════════════

### When to Load

Loading `confidence-gate` is **Phase 0 Step 1** — always load it first, before any routing decision:

```
PHASE 0: ROUTE
  Step 1: skill("confidence-gate")         ← LOAD FIRST
  Step 2: Score task (C1-C5)              ← Section 3.1
  Step 3: Estimate complexity             ← Section 1
  Step 4: Check adaptive-router history   ← Section 5
  Step 5: Apply catalyst modifier         ← Section 4
  Step 6: Select pipeline from matrix     ← Section 2
  Step 7: Route and execute               ← Section 7
  Step 8: Track result and adapt          ← Section 8
```

### How Confidence Score Modifies Routing

The confidence score doesn't just determine GO/LOOP/STOP — it **actively modifies the routing decision** by adjusting the effective complexity band:

| Confidence | Effect on Complexity | Routing Behavior |
|------------|---------------------|------------------|
| **≥ 90%** | **Downgrade complexity by 1 band** | SIMPLE → parallel/skip verify. MEDIUM → use Sisyphus Jr. COMPLEX → skip Oracle, direct to Hephaestus. UNKNOWN → reroute as SIMPLE (confidence high enough to assume simple) |
| **70-89%** | **Same band, add verify gate** | Use the standard agent for this band, but add a verification gate before reporting done |
| **50-69%** | **Upgrade complexity by 1 band** | SIMPLE → route to Hephaestus (not Sisyphus Jr). MEDIUM → add Oracle pre-check. COMPLEX → add Explore + Oracle. UNKNOWN → Oracle + Explore |
| **30-49%** | **Upgrade complexity by 1-2 bands** | SIMPLE → route as COMPLEX (Oracle → Hephaestus). MEDIUM → COMPLEX + Explore. COMPLEX → STOP or Oracle deep dive. UNKNOWN → STOP |
| **< 30%** | **Override to STOP** | All bands → STOP and escalate to user, EXCEPT UNKNOWN which routes to Explore first for assessment |

### Confidence as a Routing Multiplier

```
effective_complexity = base_complexity - catalyst_multiplier

Where:
  base_complexity = 1 (SIMPLE), 2 (MEDIUM), 3 (COMPLEX), 0 (UNKNOWN)
  
  confidence  ≥ 90%  → catalyst_multiplier = 1  (downgrade)
  confidence  70-89% → catalyst_multiplier = 0  (same)
  confidence  50-69% → catalyst_multiplier = -1 (upgrade)
  confidence  30-49% → catalyst_multiplier = -2 (upgrade more)
  confidence  < 30%  → catalyst_multiplier = -3 (stop)
```

So a SIMPLE task with 95% confidence → effective_complexity = 0 → even faster than SIMPLE (parallel, skip verify).

A MEDIUM task with 55% confidence → effective_complexity = 3 → treat as COMPLEX (Oracle → Hephaestus).

---

## ══╡ SECTION 4: CATALYST EFFECT ╞════════════════════════

### Core Concept

"Confidence catalyzes the optimal pipeline" — as confidence in the system grows (tracked across sessions), the pipeline accelerates:

1. **More parallel execution** (less serial verification)
2. **Cheaper models** (deepseek → minimax where safe)
3. **Fewer pre-checks** (skip Oracle, skip Explore)
4. **Faster feedback** (fail fast, learn fast)

### Catalyst State

The system maintains a **catalyst state** in memory:

```
memory:adaptive-router:catalyst
  { "level": 0-4, "consecutive_successes": N, "consecutive_failures": N }
```

| Level | Name | Effect | Confidence Threshold |
|-------|------|--------|---------------------|
| **0** | Cold | Full serial pipeline, all verification gates, Oracle pre-checks | Any new task, or after consecutive failure |
| **1** | Warm | Skip Oracle pre-checks for MEDIUM tasks, light verify | ≥ 70% + 2 consecutive successes |
| **2** | Hot | Skip verify gates for SIMPLE+MEDIUM, parallel delegation | ≥ 80% + 5 consecutive successes |
| **3** | Catalyzed | De-escalate to cheaper models where safe, max parallelism | ≥ 85% + 10 consecutive successes |
| **4** | Critical Mass | Full acceleration: Sisyphus Jr handles MEDIUM, Hephaestus skips most gates, derisk runs become automatic | ≥ 90% + 20 consecutive successes |

### Catalyst Acceleration Table

```
             │ Level 0    │ Level 1    │ Level 2    │ Level 3    │ Level 4
             │ (Cold)     │ (Warm)     │ (Hot)      │ (Catalyzed)│ (Critical Mass)
─────────────┼────────────┼────────────┼────────────┼────────────┼─────────────
Verify Gates │ All tasks  │ SIMPLE: no │ SIMPLE: no │ SIMPLE: no │ All: no
             │            │ MEDIUM+:yes│ MEDIUM: no │ All: no    │
             │            │            │ COMPLEX:yes│            │
             │            │            │            │            │
Pre-checks   │ All: yes   │ SIMPLE: no │ All: no    │ All: no    │ All: no
 (Oracle)    │            │ MEDIUM+:yes│            │            │
             │            │            │            │            │
Parallelism  │ Serial     │ SIMPLE:par │ All: par   │ All: par   │ All: par
             │            │ Rest: ser  │            │ + batch    │ + no wait
             │            │            │            │            │
Model Choice │ Per matrix │ Per matrix │ SIMPLE:    │ SIMPLE+    │ All on
             │            │            │ minimax    │ MEDIUM:    │ minimax
             │            │            │ MEDIUM+:   │ minimax    │ (cheapest
             │            │            │ deepseek   │ COMPLEX:   │ safe path)
             │            │            │            │ deepseek   │
             │            │            │            │            │
Derisk Runs  │ None       │ None       │ COMPLEX:   │ COMPLEX:   │ All:
             │            │            │ optional   │ automatic  │ automatic
             │            │            │            │            │
─────────────┼────────────┼────────────┼────────────┼────────────┼─────────────
Speed Factor │ 1.0x       │ 1.5x       │ 2.5x       │ 4.0x       │ 6.0x
Token Cost   │ 100%       │ 75%        │ 50%        │ 30%        │ 15%
```

### Catalyst State Transitions

```
NEW SYSTEM (no history) → Level 0 (Cold)

On SUCCESS:
  consecutive_successes++
  consecutive_failures = 0
  
  if consecutive_successes >= 20 → Level 4
  if consecutive_successes >= 10 → Level 3
  if consecutive_successes >= 5  → Level 2
  if consecutive_successes >= 2  → Level 1

On FAILURE:
  consecutive_successes = 0
  consecutive_failures++
  catalyst_level = max(0, catalyst_level - 1)
  
  if consecutive_failures >= 3:
    catalyst_level = 0 (reset to cold)
    write_memory("warning:adaptive-router", "3 consecutive failures — reset to Cold")
```

### Catalyst Effect on Routing Examples

| Task | Base Route | Catalyst Level | Actual Route | Rationale |
|------|-----------|---------------|--------------|-----------|
| Fix typo in README | SISYPHUSJr | 0 (Cold) | SISYPHUSJr + verify | Cold, do everything by the book |
| Fix typo in README | SISYPHUSJr | 2 (Hot) | SISYPHUSJr, no verify | Hot, trust the pipeline |
| New feature (MEDIUM) | HEPHAESTUS | 0 (Cold) | HEPHAESTUS + verify | Standard |
| New feature (MEDIUM) | HEPHAESTUS | 3 (Catalyzed) | SISYPHUSJr + derisk | De-escalate to cheaper model |
| Architecture change (COMPLEX) | ORACLE→HEPHAESTUS | 0 (Cold) | ORACLE→HEPHAESTUS + verify | Full pipeline |
| Architecture change (COMPLEX) | HEPHAESTUS | 4 (Critical Mass) | HEPHAESTUS, parallel, no verify, auto derisk | Maximum acceleration |

---

## ══╡ SECTION 5: ESCALATION MATRIX ╞═══════════════════════

### When Escalation Triggers

Escalation happens when an agent **fails** at its assigned task. Failure is defined as:

1. The agent explicitly delegates upward (e.g., Sisyphus Junior → Hephaestus in its own prompt)
2. The task result fails verification gates
3. The task returns an error status
4. The task times out (no response in expected time)

### Escalation Levels

```
FAILURE at Level 1 → escalate to Level 2
FAILURE at Level 2 → escalate to Level 3
FAILURE at Level 3 → STOP + user report
```

| Level | Agents | Role | Model | Max Attempts |
|-------|--------|------|-------|-------------|
| **1** | Sisyphus Junior | Fast simple execution | minimax-m2.5-free (204K) | 2 |
| **2** | Hephaestus | Robust execution | deepseek-v4-flash-free (1M) | 2 |
| **3** | Oracle → Hephaestus | Architecture analysis + rebuild | deepseek (both) | 2 |
| **4** | STOP + User Report | Cannot proceed autonomously | — | — |

### Escalation Matrix (Agent → Escalation Target)

```
Current Agent      │ Fail Count │ Escalate To         │ Action
───────────────────┼────────────┼─────────────────────┼────────────────────
Sisyphus Junior    │ 1st fail   │ Hephaestus          │ "Task exceeded Sisyphus Jr, escalating to Hephaestus"
Sisyphus Junior    │ 2nd fail   │ Oracle + Hephaestus │ "Sisyphus Jr failed 2x, routing through Oracle first"
                   │            │                     │
Hephaestus         │ 1st fail   │ Oracle + Hephaestus │ "Hephaestus failed, adding Oracle pre-analysis"
Hephaestus         │ 2nd fail   │ Oracle + Explore    │ "Hephaestus failed 2x, full investigation before retry"
                   │            │ + Hephaestus        │
                   │            │                     │
Oracle + Hephaestus│ 1st fail   │ Full investigation  │ "Oracle-guided build failed, summoning Explore + Librarian"
                   │            │ (Explore+Librarian) │
Oracle + Hephaestus│ 2nd fail   │ STOP + User Report  │ "All escalation levels exhausted. Cannot proceed."
```

### Escalation Protocol

When escalation triggers, the router does NOT just re-delegate — it **changes the approach**:

```
ESCALATION: Sisyphus Junior (fail #1) → Hephaestus
  Task: same task, but MORE context passed:
  - Include the failed attempt's output
  - Include what Sisyphus Jr tried
  - Include error messages
  - Flag: "Sisyphus Jr attempted this and failed. You have the context."

ESCALATION: Hephaestus (fail #1) → Oracle + Hephaestus
  Task: "First analyze this task's feasibility and approach"
  - Oracle analyzes and produces a brief with approach recommendation
  - Then delegate to Hephaestus with: task + Oracle's analysis inline
  - Flag: "Oracle has analyzed this — follow their architectural guidance"

ESCALATION: Oracle + Hephaestus (fail #1) → Explore + Librarian
  - Explore: "Search codebase for patterns related to {task}. Report all similar implementations."
  - Librarian: "Research external best practices for {task}. Find reference implementations."
  - Synthesize findings, then retry with full context

ESCALATION: Level exhausted → STOP + User Report
  - Generate escalation report (Section 9)
  - Present to user with clear ask
```

### Escalation History Tracking

Each escalation is stored in memory:

```
memory:adaptive-router:escalation:{task_hash}
{
  "task": "Implement X",
  "complexity": "MEDIUM",
  "chain": [
    {"agent": "Sisyphus Junior", "result": "fail", "reason": "compile error"},
    {"agent": "Hephaestus", "result": "fail", "reason": "test failure"},
    {"agent": "Oracle+Hephaestus", "result": "pending"}
  ],
  "timestamp": "2026-05-17T10:30:00Z"
}
```

---

## ══╡ SECTION 6: DE-ESCALATION ╞══════════════════════════

### When De-escalation Triggers

After a task succeeds at a higher level, **future similar tasks** can use a cheaper pipeline. This is the learning mechanism.

De-escalation happens when:
1. A COMPLEX task succeeds at Hephaestus → future SIMILAR tasks can skip Oracle
2. A MEDIUM task succeeds at Hephaestus 3+ times → future tasks can use Sisyphus Jr
3. A SIMPLE task succeeds at Sisyphus Jr with verify → future tasks can skip verify

### De-escalation Matrix

```
Successful Pipeline             │ De-escalates To              │ After
────────────────────────────────┼──────────────────────────────┼─────────────
HEPHAESTUS with verify (pass)   │ HEPHAESTUS without verify    │ 1 success
HEPHAESTUS (COMPLEX)            │ ORACLE→HEPHAESTUS (skip if   │ 2 successes
                                │   same architecture)         │
ORACLE→HEPHAESTUS (pass)        │ HEPHAESTUS with verify       │ 2 successes
HEPHAESTUS (MEDIUM, pass×3)     │ SISYPHUSJr with verify       │ 3 successes
SISYPHUSJr with verify (pass×3) │ SISYPHUSJr without verify    │ 3 successes
SISYPHUSJr (pass×5)             │ SISYPHUSJr, parallel skip v. │ 5 successes
```

### De-escalation Token

When a task succeeds, store a **de-escalation token**:

```
memory:adaptive-router:deescalate:{pattern_hash}
{
  "pattern": "feature:config-edit",
  "complexity": "SIMPLE",
  "agent": "Sisyphus Junior",
  "consecutive_successes": 3,
  "deescalated_to": "no_verify",
  "expires": "2026-06-17T10:30:00Z"
}
```

On future tasks, the router checks for matching de-escalation tokens:
- If found AND unexpired → use the proven cheaper route
- If not found → use the standard matrix
- If the cheaper route fails → revoke the token, escalate

### Token Match Criteria

A new task matches an existing de-escalation token when:

```
1. Same complexity band (SIMPLE/MEDIUM/COMPLEX)
2. Same pattern category (from task keywords):
   - "config-edit" vs "config-edit" ✓
   - "feature:implement" vs "feature:implement" ✓
   - "bug-fix" vs "bug-fix" ✓
   BUT: "config-edit" vs "bug-fix" ✗ (different patterns)
3. Same agent assigned by matrix
```

---

## ══╡ SECTION 7: PIPELINE EXECUTION ╞══════════════════════

### Pipeline Definitions

Each pipeline is a sequence of delegation calls:

#### Pipeline A: SISYPHUS_JUNIOR (SIMPLE, high confidence)

```
1. delegate_task("Sisyphus Junior - Code Writer", task)
2. if verify_required:
     delegate_task("Sisyphus Junior - Code Writer", "verify the code at {path}")
3. Record result
```

#### Pipeline B: SISYPHUS_JUNIOR_WITH_VERIFY (SIMPLE, medium confidence)

```
1. delegate_task("Sisyphus Junior - Code Writer", task)
2. delegate_task("Momus - Critic", "review code at {path} for issues")
3. if reviewer found issues:
     delegate_task("Sisyphus Junior - Code Writer", "fix: {issues}")
4. Record result
```

#### Pipeline C: HEPHAESTUS (MEDIUM, high confidence)

```
1. delegate_task("Hephaestus - Builder", task)
2. if verify_required:
     delegate_task("Momus - Critic", "review Hephaestus output at {path}")
3. Record result
```

#### Pipeline D: HEPHAESTUS_WITH_VERIFY (MEDIUM, medium confidence)

```
1. delegate_task("Hephaestus - Builder", task)
2. delegate_task("Momus - Critic", "adversarial review: {path}")
3. if issues found:
     delegate_task("Hephaestus - Builder", "fix issues: {issues}")
4. Record result
```

#### Pipeline E: ORACLE_TO_HEPHAESTUS (COMPLEX, any confidence)

```
1. oracle_result = delegate_task("Oracle - Architecture", 
     "Analyze: {task}. Output: architecture plan, file list, approach")
2. hephaestus_task = task + "\n\nORACLE ANALYSIS:\n" + oracle_result
3. delegate_task("Hephaestus - Builder", hephaestus_task)
4. if verify_required:
     delegate_task("Momus - Critic", "review: {path}")
5. if confidence ≥ 70% AND task is COMPLEX:
     call_omo_agent("Sisyphus Junior - Code Writer", 
       "Derisk: validate {path} builds independently")
6. Record result
```

#### Pipeline F: EXPLORE_TO_ROUTE (UNKNOWN)

```
1. explore_result = delegate_task("Explore - Search",
     "Search codebase for patterns related to: {task}")
2. if explore_result found relevant patterns:
     Update task with context
     Reroute through MATRIX with new complexity estimate
3. if explore_result empty:
     librarian_result = delegate_task("Librarian - Research",
       "Research external: {task}")
     Update task with context
     Reroute through MATRIX
4. if both empty:
     delegate_task("Oracle - Architecture",
       "Analyze without clear context: {task}")
     STOP + user report if still unclear
```

---

## ══╡ SECTION 8: FULL PROTOCOL ╞════════════════════════════

When you load this skill, follow these phases:

### PHASE 0-ROUTE: 8 Steps

```
Step 1: LOAD SKILLS
  • skill("confidence-gate") — load the confidence scoring protocol
  • skill("adaptive-router") — this skill (you are here)

Step 2: SCORE CONFIDENCE (via confidence-gate)
  • Score C1-C5 (Clarity, Context, Feasibility, Tools, Risk)
  • Calculate weighted total: CONFIDENCE = w1(C1) + w2(C2) + w3(C3) + w4(C4) + w5(C5)
  • Record: write_memory("adaptive-router:confidence:{task}", score)

Step 3: ESTIMATE COMPLEXITY
  • Classify task using Section 1 keyword table
  • Output: SIMPLE (1), MEDIUM (2), COMPLEX (3), UNKNOWN (0)

Step 4: CHECK HISTORY
  • search_memory("adaptive-router:history:{task_hash}")
  • search_memory("adaptive-router:escalation:{agent}:{complexity}")
  • search_memory("adaptive-router:deescalate:{pattern_hash}")
  • search_memory("adaptive-router:catalyst")
  • Load catalyst state

Step 5: APPLY CATALYST MODIFIER
  • effective_confidence = confidence
  • effective_complexity = complexity + catalyst_adjustment(confidence)
  • (From Section 4: confidence ≥90% → -1, 50-69% → +1, etc.)

Step 6: SELECT PIPELINE
  • Look up (effective_complexity, effective_confidence) in 2D matrix
  • Apply escalation override if history.failures > 0
  • Apply de-escalation token if matches

Step 7: EXECUTE PIPELINE
  • Run the selected pipeline from Section 7
  • Record each step's outcome in memory

Step 8: TRACK AND ADAPT
  • On success:
    - Increment catalyst consecutive_successes
    - Optionally create de-escalation token (Section 6)
  • On failure:
    - Increment consecutive_failures
    - If max attempts not reached → escalate (Section 5)
    - If max attempts reached → STOP + escalation report
```

### Integration with Sisyphus's Existing Protocol

```
SISYPHUS — FULL 6-PHASE PROTOCOL:

  PHASE 0: ROUTE ← NEW (this skill)
    Load → Score → Estimate → Check → Apply → Select → Execute → Track
    
  PHASE 1: CLASSIFY (existing)
    [quick] [plan] [code] [track] [memory] [therapy] [research]
    
  PHASE 2: RESEARCH (existing, skip if quick/code/track/memory/therapy)
    
  PHASE 3: PLAN (existing)
    
  PHASE 4: VALIDATE (existing)
    
  PHASE 5: DELEGATE (existing)

NOTE: Phase 0 may REPLACE Phases 1-5 for simple tasks.
      If Phase 0 routes to SIMPLE pipeline and it succeeds → skip Phases 1-5, report done.
      If Phase 0 routes to MEDIUM/COMPLEX → proceed with Phases 1-5 as normal.
```

---

## ══╡ SECTION 9: DECISION FLOW DIAGRAM ╞══════════════════

```
                          ┌───────────────────┐
                          │   TASK ENTERS     │
                          │  (user request)   │
                          └────────┬──────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │ PHASE 0: ADAPTIVE ROUTING    │
                    │                              │
                    │  1. Load confidence-gate     │
                    │  2. Score C1-C5              │
                    │     └── confidence = X%     │
                    │                              │
                    │  3. Estimate complexity      │
                    │     └── band = Y             │
                    │                              │
                    │  4. Check history            │
                    │     ├── catalyst level       │
                    │     ├── escalation count     │
                    │     └── de-escalate tokens   │
                    │                              │
                    │  5. Apply catalyst modifier  │
                    │     └── effective_band = Z   │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │ Check complexity │
                          │ band (effective) │
                          └──┬───┬───┬───┬──┘
                             │   │   │   │
               ┌─────────────┘   │   │   └─────────────┐
               ▼                 ▼   ▼                 ▼
          ┌─────────┐     ┌─────────┐           ┌─────────┐
          │ SIMPLE  │     │ MEDIUM  │           │COMPLEX │
          │ (eff=0) │     │ (eff=1) │           │(eff=2+) │
          └────┬────┘     └────┬────┘           └────┬────┘
               │               │                     │
               ▼               ▼                     ▼
     ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
     │ Confidence ≥90% │ │ Confidence ≥90% │ │ Confidence ≥90% │
     │ → SISYPHUS Jr   │ │ → HEPHAESTUS    │ │ → HEPHAESTUS    │
     │   (parallel)    │ │   (skip verify) │ │   (parallel)    │
     │                 │ │                 │ │                 │
     │ Confidence 70-89│ │ Confidence 70-89│ │ Confidence 70-89│
     │ → SISYPHUS Jr   │ │ → HEPHAESTUS    │ │ → ORACLE →      │
     │   (verify gate) │ │   (verify gate) │ │   HEPHAESTUS    │
     │                 │ │                 │ │   (light verify) │
     │ Confidence 50-69│ │ Confidence 50-69│ │                 │
     │ → HEPHAESTUS    │ │ → ORACLE →      │ │ Confidence 50-69│
     │   (escalated)   │ │   HEPHAESTUS    │ │ → ORACLE →      │
     │                 │ │                 │ │   HEPHAESTUS    │
     │ Confidence 30-49│ │ Confidence 30-49│ │   (verify gate) │
     │ → ORACLE →      │ │ → EXPLORE →     │ │                 │
     │   HEPHAESTUS    │ │   ORACLE →      │ │ Confidence <50% │
     │                 │ │   HEPHAESTUS    │ │ → ORACLE →      │
     │ Confidence <30% │ │                 │ │   EXPLORE →     │
     │ → EXPLORE first │ │ Confidence <30% │ │   HEPHAESTUS    │
     └────────┬────────┘ │ → STOP + user   │ │                 │
              │          └────────┬────────┘ │ Confidence <30% │
              │                   │          │ → STOP + user   │
              │                   │          └────────┬────────┘
              │                   │                    │
              ▼                   ▼                    ▼
     ┌─────────────────────────────────────────────────────────┐
     │                  EXECUTE PIPELINE                        │
     │                                                         │
     │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
     │  │ SISYPHUS │  │HEPHAESTUS│  │  ORACLE  │  │ EXPLORE │ │
     │  │  Junior  │  │          │  │    →     │  │   →     │ │
     │  │          │  │          │  │HEPHAESTUS│  │ reroute │ │
     │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
     │       │             │             │              │       │
     └───────┼─────────────┼─────────────┼──────────────┼───────┘
             │             │             │              │
             ▼             ▼             ▼              ▼
     ┌─────────────────────────────────────────────────────────┐
     │                  POST-EXECUTION                          │
     │                                                         │
     │  ┌─────────────────────────────────────────────────┐    │
     │  │  CHECK RESULT                                    │    │
     │  │  ├── Success? → Record, increment catalyst,     │    │
     │  │  │              optionally de-escalate token    │    │
     │  │  │                                               │    │
     │  │  └── Failure? → Track failure                   │    │
     │  │                  ┌──────────────────────────┐   │    │
     │  │                  │ Max attempts reached?    │   │    │
     │  │                  │ YES → STOP + user report │   │    │
     │  │                  │ NO  → Escalate (Sec 5)  │   │    │
     │  │                  │        → Retry           │   │    │
     │  │                  └──────────────────────────┘   │    │
     │  └─────────────────────────────────────────────────┘    │
     └─────────────────────────────────────────────────────────┘
```

---

## ══╡ SECTION 10: ESCALATION REPORT ╞══════════════════════

### When All Escalations Exhausted

Generate this report and present to the user:

```
═══ ADAPTIVE ROUTER — ESCALATION REPORT ═══════════════════════

TASK: {task description}
COMPLEXITY: {SIMPLE | MEDIUM | COMPLEX | UNKNOWN}
FINAL CONFIDENCE: {score}%

ESCALATION CHAIN:
  Level 1 → {agent}: {result} ({reason})
  Level 2 → {agent}: {result} ({reason})
  Level 3 → {agent}: {result} ({reason})

ROUTING HISTORY:
  Iter 1: {pipeline} → {result}
  Iter 2: {pipeline} → {result}
  Iter 3: {pipeline} → {result}

CATALYST STATE: Level {N} ({name})
CONSECUTIVE SUCCESSES: {N}
CONSECUTIVE FAILURES: {N}

VERDICT: CANNOT PROCEED AUTONOMOUSLY
REASON: All escalation levels exhausted.
        {brief explanation of what went wrong}

RECOMMENDATION:
  ┌──────────────────────────────────────────────────────┐
  │ What the user should do next:                        │
  │ 1. {step 1}                                         │
  │ 2. {step 2}                                         │
  │ 3. Provide {missing context/tools}                  │
  └──────────────────────────────────────────────────────┘

═══ END REPORT ═══════════════════════════════════════════════
```

### On Success (for Catalyst Advancement)

```
═══ ADAPTIVE ROUTER — SUCCESS REPORT ═════════════════════════

TASK: {task description}
COMPLEXITY: {SIMPLE | MEDIUM | COMPLEX | UNKNOWN}
ROUTE: {pipeline name}
AGENT: {agent used}
CONFIDENCE: {score}%
ITERATIONS: {N}
RESULT: ✅ SUCCESS

CATALYST UPDATE:
  Level: {N} → {N+1} (advancing)
  Consecutive Successes: {N}
  Next milestone: {N} more for next level

DE-ESCALATION TOKEN: {created | skipped | used}
  Token matches future tasks with pattern: {pattern}

═══ END REPORT ═══════════════════════════════════════════════
```

---

## ══╡ SECTION 11: MEMORY SCHEMA ╞══════════════════════════

All adaptive-router data is stored in memory under these keys:

### State Keys

| Key | Purpose | Schema |
|-----|---------|--------|
| `adaptive-router:catalyst` | Current catalyst state | `{"level": 0-4, "successes": N, "failures": N}` |
| `adaptive-router:history:{task_hash}` | Individual task result | `{"task", "complexity", "route", "result", "agent", "timestamp"}` |
| `adaptive-router:escalation:{task_hash}` | Escalation chain for a task | `{"chain": [{agent, result, reason}], "complexity"}` |
| `adaptive-router:deescalate:{pattern}` | De-escalation token | `{"pattern", "agent", "complexity", "successes", "expires"}` |
| `adaptive-router:stats:{agent}:{complexity}` | Aggregate stats per agent+band | `{"total", "successes", "failures", "escalations"}` |

### Aggregate Stats Schema

```
memory:adaptive-router:stats:Sisyphus Junior:SIMPLE
{
  "agent": "Sisyphus Junior",
  "complexity": "SIMPLE",
  "total": 47,
  "successes": 43,
  "failures": 4,
  "escalations": 3,
  "avg_confidence": 87,
  "last_success": "2026-05-17T10:30:00Z",
  "patterns": {
    "config-edit": {"total": 20, "successes": 20},
    "typo-fix": {"total": 15, "successes": 14},
    "doc-update": {"total": 12, "successes": 9}
  }
}
```

### Querying History

```
// Before routing, check if similar tasks succeeded
search_memory("adaptive-router:history:*")
search_memory("adaptive-router:stats:Hephaestus:MEDIUM")

// Check catalyst state
search_memory("adaptive-router:catalyst")

// Check de-escalation tokens for this task pattern
search_memory("adaptive-router:deescalate:config-edit")
```

---

## ══╡ SECTION 12: EDGE CASES ╞═════════════════════════════

### Edge Case 1: First Task Ever (No History)

```
If memory:adaptive-router:catalyst does NOT exist:
  → Initialize: Level 0 (Cold), successes=0, failures=0
  → Force all verification gates ON
  → Skip de-escalation (no tokens exist)
  → Default to MEDIUM pipeline if complexity is UNKNOWN
```

### Edge Case 2: Confidence-Gate Returns STOP (< 30%)

```
If confidence < 30% AND complexity is NOT UNKNOWN:
  → Do NOT route to any agent
  → Generate readiness report (what's missing, what would reach 70%)
  → Present to user: "I need more information before proceeding"
  → Do NOT waste tokens on exploration

If confidence < 30% AND complexity is UNKNOWN:
  → This is the one exception — route to Explore for assessment
  → "I don't understand this task, but I'll search for context"
  → After Explore: rescore confidence
  → If still < 30%: STOP + user report
```

### Edge Case 3: Escalation Loop (Infinite Retry)

```
If a task has been retried 3+ times ACROSS all levels:
  → STOP regardless of remaining attempts
  → "This task has been retried 3 times across different agents without success"
  → Generate full escalation report
  → The catalyst level has specific safety:
    consecutive_failures >= 3 → catalyst_level = 0 (forced cold reset)
```

### Edge Case 4: Task Changes Mid-Execution

```
If a task is modified during execution (user changes their mind):
  → Reset all counters for that task_hash
  → Re-run Phase 0 with new task description
  → Previous failure does NOT count against new task
  → Exception: if new task is nearly identical (similarity > 80%), carry over context
```

### Edge Case 5: De-escalation Token Fails

```
If a de-escalated route fails:
  → Immediately revoke the token:
    delete_memory("adaptive-router:deescalate:{pattern}")
  → Escalate to standard route for this complexity band
  → Record the failure in stats
  → De-escalation tokens are NEVER permanent — they expire after 30 days
```

### Edge Case 6: Confidence-Catalyst Mismatch

```
If confidence is HIGH (≥90%) but catalyst level is LOW (0):
  → The catalyst level will NOT override the confidence
  → Route per confidence first, then accelerate per catalyst level
  → Rationale: catalyst reflects SYSTEM trust, confidence reflects TASK trust
  → They work independently: task confidence → complexity downgrade,
    catalyst level → parallelism/verify/token cost
```

### Edge Case 7: All Agents Busy

```
If an agent is already occupied with another task:
  → Check if the task can wait: queue it
  → If urgent: route to the next available agent in escalation chain
  → If none available: defer to Sisyphus's existing queue management
  → This is handled by Sisyphus's orchestration layer, not the router
```

---

## ══╡ REFERENCES ╞══════════════════════════════════════════

- Confidence Gate skill: `agents/skills/confidence-gate/SKILL.md`
- Sisyphus agent: `agents/sisyphus/agent.js`
- Sisyphus Junior agent: `agents/sisyphus-junior/agent.js`
- Hephaestus agent: `agents/hephaestus/agent.js`
- Oracle agent: `agents/oracle/agent.js`
- Explore agent: `agents/explore/agent.js`
- Librarian agent: `agents/librarian/agent.js`
- Catalyst Orchestration: `bmad/bmm/workflows/bmad-catalyst-orchestration/SKILL.md`

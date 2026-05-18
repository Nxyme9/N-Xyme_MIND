---
agent: Mnemosyne - Debugger
---

# Mnemosyne Debug — Workflow

**Target:** Any agent session, configuration, or behavior in N-Xyme
**Output:** Structured debug report with evidence chain

## Entry Points

| Entry Trigger | Typical Symptom | Start At |
|---------------|----------------|----------|
| User reports wrong behavior | "Catalyst wrote code" | Phase 2 — TRACE |
| Failed task | "Build failed without error" | Phase 2 — TRACE |
| Config error | "Agent not found" | Phase 3 — RECONSTRUCT |
| Hallucination | "Agent invented a tool" | Phase 4 — ANALYZE (Lens 4) |
| Memory query | "Debug agent XYZ behavior" | Phase 2 — TRACE |

## Phase-by-Phase Actions

### PHASE 1: RECEIVE — Parse the Debug Request

Actions:
1. Classify: Is this a session bug, agent config bug, tool boundary bug, or delegation bug?
2. Scope: Which agents, sessions, and timespan are relevant?
3. Load this skill: skill("mnemosyne-debug")

Output template:
```
DEBUG TARGET: {symptom description}
SCOPE: {agents involved} | {sessions} | {time range}
INITIAL HYPOTHESIS: {one sentence}
```

### PHASE 2: TRACE — Build Causality Chain

Actions:
1. Find the session files:
   ```
   file_glob("data/sessions/*.jsonl")
   file_grep("data/sessions/", "<agent_name>")
   ```
2. For the relevant session(s), extract the delegation chain:
   - Who made the first delegate_task call?
   - What was the task description?
   - Was identity propagated? (check parentSessionID)
   - What did each downstream agent output?
3. Build the chain:
   ```
   Catalyst → delegate_task("Hephaestus", "Build X")
     → Hephaestus (session abc) → loaded skill Scalpel
       → Scalpel analyzed code → returned to Hephaestus
         → Hephaestus wrote files → QUALITY GATE SKIPPED
           → Returned to Catalyst → Reported DONE
   ```
4. Flag every point where identity could have been lost or quality gate skipped.

Output template:
```
CAUSALITY CHAIN:
  Node 1: {Agent} @ {session_id} — {action}
    → Identity: {propagated|dropped} (via {delegate_task|task()|call_omo_agent})
  Node 2: {Agent} @ {session_id} — {action}
    ...
  BREAK POINT: {where it went wrong}

EVIDENCE:
  - {file:line or session:timestamp}
```

### PHASE 3: RECONSTRUCT — Agent State at Failure Point

Actions:
1. For each agent in the chain:
   - Read agent.js: What does IDENTITY say? What are the RULES?
   - Read tools/tools.json: What tools are allowed? Blocked?
   - Check prompt content at the time: Any recent edits?
   - Check loaded skills: Were relevant skills loaded?
2. For the failure point:
   - Read the EXACT tool call that triggered the failure
   - What tool, what arguments, what was the context?
   - What was the agent's memory state? (search_memory for that session)
3. Cross-reference:
   - Claim vs capability: Does the prompt promise what tools deliver?
   - Skill loading: Was the right skill loaded for this task?

Output template:
```
AGENT STATE AT FAILURE:
  Agent: {name}
  Identity: {summary from agent.js IDENTITY}
  Tools allowed: {list from tools.json}
  Tools used in session: {list from session log}
  Skills loaded: {list}
  Memory context: {summary}

  → DISCREPANCY: {if any}
```

### PHASE 4: ANALYZE — Apply Debug Lenses

Actions:
1. Apply all 5 lenses systematically:

**LENS 1 — IDENTITY DRIFT [ID]**
- Does the agent's session behavior match its IDENTITY statement?
- Check: "NEVER writes code" vs session showing file_write calls

**LENS 2 — TOOL BOUNDARY [TB]**
- Map every tool call to the allowed list
- Any tool called that's not in allowed?
- Any tool in both allowed and blocked? (config error)

**LENS 3 — DELEGATION BREAK [DB]**
- Find all delegation points in the chain
- Check if task() was used instead of delegate_task()
- Check if parentSessionID was propagated

**LENS 4 — HALLUCINATION [HA]**
- Cross-reference every agent name mentioned against agents/ directory
- Cross-reference every tool name against MCP server definitions
- Cross-reference every import/file path against filesystem

**LENS 5 — QUALITY GATE SKIP [QG]**
- Check session output for quality gate section
- Was there a checklist? Were items checked?
- Was there compile/test output?

2. Score each lens: 0 (no issue) to 5 (critical failure)

Output template:
```
LENS SCORES:
  [ID] Identity Drift:     {0-5} — {evidence summary}
  [TB] Tool Boundary:      {0-5} — {evidence summary}
  [DB] Delegation Break:   {0-5} — {evidence summary}
  [HA] Hallucination:      {0-5} — {evidence summary}
  [QG] Quality Gate Skip:  {0-5} — {evidence summary}

PRIMARY FAILURE MODE: {lens with highest score}
```

### PHASE 5: REPORT — Structured Debug Output

Actions:
1. Compile all findings into a structured report
2. For each finding, clearly label [EVIDENCE] vs [INFERENCE]
3. Report confidence: HIGH / MEDIUM / LOW / SPECULATIVE
4. Write report to memory
5. If fix is identified: delegate to appropriate agent

Output template:
```
══╡ DEBUG REPORT ╞═══════════════════════════════════════════

EXECUTIVE SUMMARY:
{Three lines max describing root cause and impact}

CAUSALITY CHAIN:
{From Phase 2 output}

FAILURE ANALYSIS:

Finding 1: {Title} [LENS: {ID|TB|DB|HA|QG}] [{HIGH|MEDIUM|LOW}]
  [EVIDENCE] {file:line or session:timestamp}
  [INFERENCE] {what this suggests}
  ...

ROOT CAUSE:
{One sentence. "Not determined" if uncertain.}

RECOMMENDATIONS:
- {Action} → delegate to {Agent} — {justification}

EVIDENCE INDEX:
{Numbered list of all evidence files and lines}
```

## Example Debug Session

```
User: "Catalyst is writing code, it shouldn't."
Debugger: Trace → reconstruct → analyze → report

Finding: Catalyst session shows file_write calls
  [EVIDENCE] agents/sisyphus/agent.js:15-17 — "You NEVER write code"
  [EVIDENCE] agents/sisyphus/tools/tools.json — file_write is in allowed list!
  [EVIDENCE] session_abc.jsonl:142 — Catalyst called file_write("/tmp/test.py")
  [INFERENCE] tools.json allows what IDENTITY forbids
  [LENS] Tool Boundary [TB] + Identity Drift [ID]

ROOT CAUSE: Config mismatch — Catalyst's tools.json allows file_write
  despite its identity saying "NEVER writes code"

RECOMMENDATION: Add file_write to Catalyst's blocked tools list
  → delegate_task("Hephaestus - Builder", "Add file_write to blocked
    in agents/sisyphus/tools/tools.json")
```

## Verification

- [ ] Every finding cross-referenced to evidence
- [ ] Evidence vs Inference clearly separated
- [ ] Confidence levels assigned
- [ ] Root cause identified OR explicitly marked as unknown
- [ ] Report stored to memory for future reference

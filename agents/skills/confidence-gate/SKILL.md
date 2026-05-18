---
name: confidence-gate
description: "Confidence Gate — STOP-GO-LOOP decision protocol for orchestration chains. Load this when you need to decide whether to execute, loop, or stop a task. Covers: confidence scoring, threshold-based routing, diminishing returns detection, Oracle consultation, user escalation."
---

# Confidence Gate — SKILL

**Purpose:** A decision protocol any agent can load when they need to evaluate whether to EXECUTE, LOOP, or STOP a task. Prevents over-execution by making stop/go decisions explicit and data-driven.

**Loading agent needs:** The ability to evaluate task quality (via `review_code`, `verify_code`, or manual inspection).

---

## ══╡ CORE CONCEPT ╞════════════════════════════════════════

Every task has a CONFIDENCE SCORE (0-100%). This score determines the path:

```
                  ┌──────────────────┐
                  │  Task Ready for  │
                  │  Evaluation?     │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │  Score confidence│
                  │  (0-100%)        │
                  └────────┬─────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
          ≥ 90%        50-89%        < 50%
              │            │            │
              ▼            ▼            ▼
         ┌────────┐  ┌──────────┐  ┌────────┐
         │EXECUTE │  │  LOOP or │  │  STOP  │
         │(skip   │  │ VERIFY   │  │(ask    │
         │verify) │  │ gate     │  │ user)  │
         └────────┘  └──────────┘  └────────┘
```

### The Three Outcomes

| Outcome | Meaning | When |
|---------|---------|------|
| **EXECUTE** (GO) | Proceed with full implementation. | Confidence ≥ 90% — OR — 70-89% with verification gate passed |
| **LOOP** | Improve the task, then re-evaluate. Repeat until diminishing returns. | Confidence 50-89% and verification gate failed — OR — confidence 30-49% (but loop with Oracle) |
| **STOP** | Do NOT proceed. Escalate to user. | Confidence < 30% — OR — diminishing returns detected (< 1% delta) |

---

## ══╡ SECTION 1: CONFIDENCE SCORING ╞═══════════════════════

### The Scoring Formula

```
CONFIDENCE = w1(C1) + w2(C2) + w3(C3) + w4(C4) + w5(C5)

Where w1...w5 are weights that sum to 1.0 (defaults below)
And C1...C5 are component scores (0-100%)
```

### Default Components

| Component | Weight | What It Measures | How to Score |
|-----------|--------|-----------------|--------------|
| **C1: Clarity** | 0.25 | Is the task well-defined? | 100% = crystal clear ACs and scope. 50% = vague but directional. 0% = "do something" |
| **C2: Context** | 0.20 | Do we have all needed context? | 100% = all files read, dependencies known. 50% = partial context. 0% = working blind |
| **C3: Feasibility** | 0.20 | Is this technically achievable? | 100% = known pattern, done before. 50% = plausible but unproven. 0% = might be impossible |
| **C4: Tool Readiness** | 0.20 | Do we have the right tools? | 100% = all tools available and tested. 50% = some tools unverified. 0% = missing critical tools |
| **C5: Risk Level** | 0.15 | What's the downside of failure? | 100% = safe to fail, no side effects. 50% = moderate impact. 0% = could break critical systems |

### Quick Scoring (for simple tasks)

For quick decisions, use the abbreviated 3-score system:

```
CONFIDENCE = (C1_CLARITY + C3_FEASIBILITY + C4_TOOLS) / 3
```

Where each is scored on a 1-10 scale and converted to percentage:
- 9-10 = 100%
- 7-8 = 80%
- 5-6 = 60%
- 3-4 = 40%
- 1-2 = 20%

### Confidence Score Examples

| Scenario | C1 | C2 | C3 | C4 | C5 | Total | Decision |
|----------|----|----|----|----|----|-------|----------|
| "Fix typo in README" | 100 | 100 | 100 | 100 | 100 | 100% | EXECUTE |
| "Implement new feature from spec" | 90 | 80 | 85 | 90 | 80 | 85% | EXECUTE + verify |
| "Refactor module with partial understanding" | 70 | 40 | 60 | 80 | 60 | 62% | LOOP |
| "Build system from vague requirements" | 40 | 30 | 50 | 60 | 30 | 42% | LOOP + Oracle |
| "Fix production bug with no reproduction steps" | 30 | 10 | 40 | 50 | 10 | 28% | STOP |

---

## ══╡ SECTION 2: THRESHOLD ROUTING ╞════════════════════════

### Decision Matrix

```
Confidence    │ Action                    │ Gate
──────────────┼───────────────────────────┼──────────────────
≥ 90%         │ EXECUTE (full speed)      │ No verification needed
70-89%        │ EXECUTE with verification │ Must pass quality gate before reporting done
50-69%        │ LOOP                      │ Improve → rescore → verify
30-49%        │ LOOP with Oracle          │ Consult Oracle → improve → rescore → verify
< 30%         │ STOP                      │ Ask user — do not proceed
```

### Detailed Branch Logic

**BRANCH: ≥ 90% (EXECUTE — Skip Verification)**
- Proceed immediately with the task
- No verification gate needed
- Rationale: confidence is high enough that verification would waste tokens
- Still run quality gate AFTER completion (always verify output)
- Memory: `write_memory("confidence:{task}:decision", "execute:skip_verify")`

**BRANCH: 70-89% (EXECUTE with Verification Gate)**
- Proceed with the task
- BUT: must pass a verification gate before reporting completion
- Verification gate = run `review_code` or equivalent quality check
- If verification fails → do NOT report done. Instead:
  - Fix the specific issues found
  - Rescore confidence (expect it to increase to ≥ 90%)
  - If it drops → enter LOOP branch
- Memory: `write_memory("confidence:{task}:decision", "execute:verify_gate")`

**BRANCH: 50-69% (LOOP)**
- Do NOT proceed with execution yet
- First: identify what's dragging confidence down
  - Which component (C1-C5) has the lowest score?
  - What would it take to raise that component by 20+ points?
- Then: take specific improvement action:
  - Low Clarity → refine task spec, add ACs
  - Low Context → read more files, load relevant skills
  - Low Feasibility → research similar implementations, prototype
  - Low Tool Readiness → verify tool availability, test tool calls
  - High Risk → add safety checks, limit scope, add safeguards
- After action: rescore confidence
- If new score ≥ 70% → move to EXECUTE with verification
- If new score < 50% → move to LOOP with Oracle
- If score improved < 5% → check diminishing returns (Section 3)

**BRANCH: 30-49% (LOOP with Oracle Consultation)**
- Do NOT proceed
- First: delegate to Oracle skill for architecture/feasibility analysis
  - `delegate_task("Oracle", "Analyze feasibility: {task}. Identify: what's unclear, what's risky, what's missing.")`
  - OR load Oracle skill directly (if loading agent has analysis tools)
- Based on Oracle findings:
  - If feasibility confirmed → take improvement actions, rescore
  - If feasibility questioned → gather more info, rescore
  - If infeasible → move to STOP
- If after 2 loops still < 50% → STOP (see below)

**BRANCH: < 30% (STOP — Ask User)**
- Do NOT proceed
- Generate a "readiness report":
  - Current confidence score with component breakdown
  - What's missing (specific gaps)
  - What it would take to reach ≥ 70%
  - Recommendation: proceed? abandon? gather more info?
- Present to user with `ask_question` or `delegate_task` to Sisyphus with STOP verdict
- Never proceed without user approval below 30%

---

## ══╡ SECTION 3: DIMINISHING RETURNS DETECTION ╞═══════════

### The Delta Measurement

After each loop iteration, calculate the improvement delta:

```
delta = confidence_score(iteration N) - confidence_score(iteration N-1)
```

### Delta Decision Table

| Delta | Meaning | Action |
|-------|---------|--------|
| **> +10%** | High value loop | CONTINUE looping (this iteration was highly productive) |
| **+1% to +10%** | Moderate value | Continue looping but flag "approaching threshold" |
| **< +1%** | Diminishing returns | STOP — further loops won't meaningfully improve |
| **Negative** | Regressing | STOP — the loop is making things worse |

### Convergence Detection

Stop looping when ANY of these conditions are met:

1. `delta < 1%` — diminishing returns (no meaningful improvement)
2. `max_iterations >= 5` — hard cap (safety against infinite loops)
3. `absolute_score >= 90` — good enough (further loops unnecessary)
4. `delta < 0` — regressing (fixing one thing broke another)

### Loop Tracking

Maintain a loop state table:

```
┌───────────┬──────────┬────────┬──────────┬──────────┐
│ Iteration │ Decision │ Score  │ Delta    │ Action   │
├───────────┼──────────┼────────┼──────────┼──────────┤
│ 0         │ Baseline │ 55%    │ —        │ LOOP     │
│ 1         │ Improve  │ 72%    │ +17%     │ CONTINUE │
│ 2         │ Verify   │ 78%    │ +6%      │ Flag     │
│ 3         │ Improve  │ 80%    │ +2%      │ Flag     │
│ 4         │ Improve  │ 81%    │ +1%      │ STOP     │
└───────────┴──────────┴────────┴──────────┴──────────┘
```

### Token Waste Prevention

```
If delta < 1% AND iteration > 2:
  → STOP immediately
  → Do NOT run another loop "just to be sure"
  → The improvement rate will only decrease, not increase
  → Report: "Diminishing returns at iteration {N} (delta={delta}%)"
```

---

## ══╡ SECTION 4: FULL PROTOCOL ╞════════════════════════════

When you load this skill, follow these phases:

### PHASE 1: SCORE

1. Read the task description
2. Score C1-C5 (or use quick score for simple tasks)
3. Calculate weighted confidence total
4. Record baseline score in memory:
   `write_memory("confidence:{task}:baseline", JSON.stringify({c1, c2, c3, c4, c5, total}))`

### PHASE 2: ROUTE

1. Look up confidence score in Decision Matrix (Section 2)
2. Follow the branch:
   - **≥ 90%** → EXECUTE, no verify gate
   - **70-89%** → EXECUTE with verification gate
   - **50-69%** → LOOP (improve deficiencies)
   - **30-49%** → LOOP with Oracle consultation
   - **< 30%** → STOP, report to user
3. Record routing decision

### PHASE 3: LOOP (if applicable)

1. Identify which component (C1-C5) has the lowest score
2. Take specific improvement action targeting that component
3. Rescore confidence
4. Calculate delta from previous iteration
5. Apply Diminishing Returns Detection (Section 3):
   - delta > 10% → CONTINUE
   - delta 1-10% → continue with "approaching threshold" flag
   - delta < 1% → STOP
   - delta < 0 → STOP + report regression
6. If continuing → go to PHASE 2 with new score
7. If stopping → go to PHASE 4

### PHASE 4: REPORT

Generate a decision report:

```
═══ CONFIDENCE GATE REPORT ═══════════════════════
Task: {task description}
Final confidence: {score}%
Iterations: {N}
Route: {EXECUTE | LOOP → EXECUTE | STOP}
Components: C1={} C2={} C3={} C4={} C5={}

Decision chain:
  Iter 0: {score}% → {LOOP/EXECUTE}
  Iter 1: {score}% (Δ{delta}%) → ...
  Iter N: {score}% (Δ{delta}%) → {FINAL}

Verdict: {GO | STOP | ESCALATE}
Reason: {brief explanation}
═══════════════════════════════════════════════════
```

---

## ══╡ SECTION 5: INTEGRATION GUIDE ╞═══════════════════════

### When to Load This Skill

Load `confidence-gate` at every delegation decision point:

- **Sisyphus**: Before delegating to Hephaestus/Atlas/Hermes. Score the task's readiness.
- **Atlas**: Before executing each story. Score whether there's enough context.
- **Hephaestus**: Before starting a complex build. Score whether you understand the codebase.
- **Hermes**: Before deep research. Score whether enough context exists.

### Usage Pattern

```
// Load the skill
skill("confidence-gate")

// Phase 1: Score
// Evaluate C1-C5 based on task
confidence = calculate(C1=90, C2=70, C3=80, C4=85, C5=75)
// Result: 80% → EXECUTE with verify gate

// Phase 2: Route
// Since 70-89%: execute but with verification
proceed_with_task()
verify_results()
if (verification_passed) {
  report_done()
} else {
  // Enter LOOP
  improve_deficiencies()
  rescore()
}
```

### Integration with Other Skills

| Skill | Integration Point |
|-------|------------------|
| **Prompt Engineer** | After optimizing a prompt, run confidence gate to decide if it's ready to deploy |
| **Momus (adversarial review)** | After Momus review, rescore confidence. If it drops below 70%, enter LOOP |
| **Oracle (architecture)** | LOOP with Oracle = delegate to Oracle, incorporate findings, rescore |
| **Agent Builder** | Before registering a new agent, run confidence gate on the generated prompt |

### Archetype-Specific Threshold Adjustments

Different agent archetypes may benefit from adjusted thresholds:

| Archetype | Execute Threshold | Loop Threshold | Oracle Threshold | Notes |
|-----------|------------------|----------------|------------------|-------|
| **Builder** | ≥ 85% | 50-84% | 30-49% | Higher tolerance for ambiguity (code is iterative anyway) |
| **Tool-User** | ≥ 90% | 60-89% | 40-59% | Tools are precise — lower tolerance |
| **Reader** | ≥ 95% | 70-94% | 50-69% | Analysis must be accurate — highest threshold |
| **Conversational** | ≥ 80% | 40-79% | 20-39% | Lower stakes, can recover from mistakes |
| **Specialist** | ≥ 90% | 60-89% | 40-59% | Domain expertise reduces ambiguity, but errors are costly |

---

## ══╡ REFERENCES ╞═══════════════════════════════════════════

- Sisyphus orchestration protocol: `agents/sisyphus/agent.js`
- Agent Builder classification: `agents/agent-builder/agent.js`
- Oracle skill (for LOOP with Oracle): `agents/oracle/skills/nx-oracle-consult/SKILL.md`
- Momus skill (for verification gate): `agents/momus/skills/nx-momus-audit/SKILL.md`

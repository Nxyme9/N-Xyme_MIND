# N-Xyme Auto-Delegation — Core Loop Plan

## TL;DR

> **Quick Summary**: Build and test the CORE LOOP — auto-complexity detection, depth slider, auto-routing, auto-review. 5 tasks, 1 week. Prove it works before expanding.
> 
> **Deliverables**:
> - `bin/complexity-score.sh` — Auto-detect task complexity (L1-L5)
> - Updated `AGENTS.md` — Depth slider, trigger budget, cognitive mode
> - Updated `masterprompt.md` — Auto-review chain (gates → Oracle → Momus)
> - Integration test — 3 real tasks validated
> 
> **Estimated Effort**: 1 week
> **Parallel Execution**: Tasks 1-2 parallel, Tasks 3-4 after, Task 5 validation
> **Critical Path**: Scorer → Wire → Test

---

## Context

### Why This Plan Exists
User is tired of manually prompting plan critique, reviewer, and Oracle before and after every task. Need auto-delegation that detects complexity and routes optimally.

### Actual OpenCode Architecture (Verified from Source)
- **AGENTS.md loads on FIRST `read` tool call** (NOT at session start)
- **Hook:** directory-agents-injector walks up directory tree, injects AGENTS.md into read output
- **Each agent has HARDCODED system prompt** in oh-my-opencode plugin
- **System prompt is SEPARATE from AGENTS.md** (system prompt = behavior, AGENTS.md = rules)
- **Context stays when switching agents** but agents don't notice they switched
- **Sisyphus never auto-delegates** to Hephaestus (needs explicit rules)
- **Images don't auto-route** to multimodal-looker (needs auto-delegation rules)
- **Multimodal-looker should use mimo-v2-pro** (only model that reads images)

### Evidence (Benchmarks)
- **0/21 vs 21/21**: Quick models CAN'T code. Deep models produce production code.
- **20s vs 48s**: Parallel + circuit breakers beats vanilla exploration
- **24min stuck**: Parallel WITHOUT breakers causes hyperfocus loops
- **Conclusion**: Model selection + structured parallel + circuit breakers = optimal

### Oracle's Verdict: CONDITIONAL GO
"Do 5 things first. If it works → expand. If not → stop and fix."

### Future: Archetype Exploration
"As above, so below" — map unknown systems to known archetypes (Nigredo→Albedo→Citrinitas→Rubedo). This is Phase 2, AFTER core loop proven.

---

## Work Objectives

### Core Objective
Build the minimal auto-delegation loop: detect complexity → route to agents → auto-review → validate.

### Definition of Done
- [ ] User says "fix login bug" → system auto-delegates to 1 agent
- [ ] User says "build auth system" → system auto-delegates to 5 agents
- [ ] Implementation complete → Oracle + Momus auto-fire (no manual prompting)
- [ ] 3 real tasks tested successfully

### Must Have
- Complexity scorer (L1-L5, <2 seconds)
- Depth slider (shallow/standard/deep/exhaustive)
- Trigger budget (5 per session)
- Auto-review chain (gates → Oracle → Momus)

### Must NOT Have
- ❌ DO NOT TOUCH COMPRESSION
- ❌ No infinite recursion (max 3 levels)
- ❌ No unbounded agents (max 8 concurrent)
- ❌ No complexity detection >5 seconds
- ❌ No feature bloat — 5 tasks only for this phase

---

## TODOs

- [ ] 0. Add OpenCode Architecture section to AGENTS.md

  **What to do**:
  - Add new section "## 🖥️ OPENCODE ARCHITECTURE" to AGENTS.md (after Agent Switch Detection)
  - Document ACTUAL architecture (verified from source code):
    - AGENTS.md loads on FIRST `read` tool call (NOT at session start)
    - Hook: directory-agents-injector walks up directory tree, injects AGENTS.md into read output
    - Each agent has HARDCODED system prompt in oh-my-opencode plugin
    - System prompt is SEPARATE from AGENTS.md (system prompt = behavior, AGENTS.md = rules)
    - When switching agent types: system prompt changes, context stays, AGENTS.md not loaded until first read
    - Agents DON'T automatically notice they switched
  - Document best practices:
    - One agent per tab (don't switch types mid-tab)
    - Read a file FIRST to trigger AGENTS.md injection
    - Read wake_up.md at session start (triggers injection + gets context)
    - Use multiple tabs for parallel work
  - Document: shared state lives in `.sisyphus/` directory

  **Must NOT do**:
  - No complex explanation — keep it simple and direct
  - No assumptions about OpenCode internals

  **Acceptance Criteria**:
  - [ ] Section exists in AGENTS.md after Agent Switch Detection
  - [ ] Actual architecture documented (read-triggered injection)
  - [ ] Best practices documented (one agent per tab)
  - [ ] Shared state location documented

  **Commit**: YES
  - Message: `docs(agents): add OpenCode architecture (verified from source)`
  - Files: `AGENTS.md`

---

- [ ] 0.5. Add auto-delegation rules to AGENTS.md

  **What to do**:
  - Add new section "## 🔄 AUTO-DELEGATION RULES" to AGENTS.md
  - Multimodal content: If input contains image/audio/video → delegate to multimodal-looker
  - Multimodal-looker MUST use mimo-v2-pro model (only model that can read images)
  - Implementation tasks: If task requires writing code → delegate to Hephaestus
  - Review tasks: If implementation complete → delegate to Oracle, then Momus
  - Sisyphus should auto-delegate based on task type, not do everything itself

  **Must NOT do**:
  - No text-only agent attempting to process images
  - No Sisyphus writing code (delegate to Hephaestus)
  - No auto-delegation loops (max 2 delegation levels)

  **Acceptance Criteria**:
  - [ ] Auto-delegation rules section exists in AGENTS.md
  - [ ] Multimodal delegation documented
  - [ ] Implementation delegation documented
  - [ ] Review chain documented

  **Commit**: YES
  - Message: `docs(agents): add auto-delegation rules for multimodal and implementation`
  - Files: `AGENTS.md`

---

- [ ] 0.6. Add Agent Registry to AGENTS.md

  **What to do**:
  - Add new section "## 👥 AGENT REGISTRY" to AGENTS.md
  - List ALL available agents with their roles:
    - Hephaestus: Implementation (writing code, creating files)
    - Oracle: Architecture review (reviewing design decisions)
    - Momus: Adversarial review (red-teaming, finding flaws)
    - Explorer: Codebase search (finding files, patterns, code)
    - Librarian: External research (web search, documentation)
    - Multimodal-looker: Image/audio/video (processing multimodal content)
    - Metis: Pre-planning (gap analysis before planning)
  - Document HOW to delegate: `task(subagent_type="agent-name", prompt="...", run_in_background=True)`
  - Document delegation rules:
    - Sisyphus orchestrates — it DELEGATES, doesn't implement
    - Hephaestus implements — it WRITES code
    - Oracle reviews — it CHECKS architecture
    - Momus red-teams — it FINDS flaws
    - Explorer searches — it FINDS code
    - Librarian researches — it FINDS information
  - Document: results come back to delegating agent, context stays in ONE session
  - **CORRECT MODEL**: Multimodal-looker uses **mimo-v2-omni-free** (NOT mimo-v2-pro)

  **Must NOT do**:
  - No listing agents that don't exist in config
  - No complex delegation chains (max 2 levels)
  - No delegation without explicit prompt

  **Acceptance Criteria**:
  - [ ] Agent Registry section exists in AGENTS.md
  - [ ] All available agents listed with roles
  - [ ] Delegation method documented (task() function)
  - [ ] Delegation rules documented (who does what)
  - [ ] Context preservation explained
  - [ ] Multimodal-looker model = mimo-v2-omni-free

  **Commit**: YES
  - Message: `docs(agents): add agent registry for multi-agent delegation`
  - Files: `AGENTS.md`

---

- [ ] 0.7. Add Fact Verification rules to AGENTS.md

  **What to do**:
  - Add new section "## 🔍 FACT VERIFICATION (Anti-Sycophancy)" to AGENTS.md
  - Before accepting claims: VERIFY evidence, VERIFY my knowledge, VERIFY user accuracy
  - Before config changes: VERIFY schema, VERIFY model exists, VERIFY capabilities
  - Before assuming capabilities: VERIFY system prompt, VERIFY model abilities, VERIFY config
  - Anti-sycophancy rules:
    - NEVER agree just to be polite
    - NEVER assume user is always right
    - NEVER claim capabilities I don't have
    - ALWAYS verify before committing
    - ALWAYS say "I don't know" when I don't know
    - ALWAYS check model capabilities before assignment
  - Concrete examples:
    - User says "use model X" → Check if X exists and can do what's needed
    - User says "this agent can do Y" → Check agent's system prompt and capabilities
    - User says "this config is correct" → Validate JSON and check schema

  **Must NOT do**:
  - No blind agreement without verification
  - No claiming capabilities without checking
  - No implementing without validating

  **Acceptance Criteria**:
  - [ ] Fact Verification section exists in AGENTS.md
  - [ ] Anti-sycophancy rules documented
  - [ ] Verification steps for claims, configs, capabilities
  - [ ] Concrete examples included

  **Commit**: YES
  - Message: `docs(agents): add fact verification and anti-sycophancy rules`
  - Files: `AGENTS.md`

---

- [ ] 1. Port complexity scorer to bin/complexity-score.sh

  **What to do**:
  - Read `athena/examples/scripts/assess_complexity.py` for L1-L5 logic
  - Create `bin/complexity-score.sh` with keyword-based scoring
  - Output: JSON `{level, confidence, signals, recommended_agents, mode}`
  - Levels: L1=typo/fix (1 agent), L2=feature (3 agents), L3=system (5 agents), L4=architecture (8 agents), L5=enterprise (8 agents)
  - Modes: parallel-exploration (explore/find/search) vs focused-execution (fix/build/implement)

  **Must NOT do**:
  - No ML-based detection (too slow)
  - No analysis >5 seconds
  - No network calls

  **Acceptance Criteria**:
  - [ ] Script runs in <2 seconds
  - [ ] "fix the login bug" → L1, 1 agent, focused-execution
  - [ ] "build auth system" → L3, 5 agents, parallel-exploration
  - [ ] "research LLM orchestration" → L4, 8 agents, parallel-exploration
  - [ ] Output is valid JSON

  **Commit**: YES
  - Message: `feat(sisyphus): add complexity scorer for auto-delegation`
  - Files: `bin/complexity-score.sh`

---

- [ ] 2. Add depth slider + trigger budget to AGENTS.md

  **What to do**:
  - Add "## Exploration Depth" section: SHALLOW (1), STANDARD (3), DEEP (5), EXHAUSTIVE (8)
  - Auto-detection: single file → SHALLOW, "find all" → STANDARD, "deep dive" → DEEP, "exhaustive" → EXHAUSTIVE
  - Add "Trigger Budget" to circuit breakers: 5 per session, auto-actions cost 1, manual free
  - Add "Cognitive Mode" rules: parallel-exploration vs focused-execution

  **Must NOT do**:
  - No more than 4 depth levels
  - No budget >5
  - No mode that takes >1 second to detect

  **Acceptance Criteria**:
  - [ ] Depth slider section exists with 4 levels
  - [ ] Trigger budget rule exists (5 per session)
  - [ ] Cognitive mode rules documented
  - [ ] Auto-detection rules for each

  **Commit**: YES
  - Message: `docs(agents): add depth slider, trigger budget, cognitive mode`
  - Files: `AGENTS.md`

---

- [ ] 3. Wire complexity scorer to Sisyphus pre-delegation

  **What to do**:
  - Update `.sisyphus/masterprompt.md`: run `bin/complexity-score.sh` before task decomposition
  - Use output to auto-select agent count and depth level
  - Log: "Complexity: L3, Depth: DEEP, Agents: 5, Mode: parallel-exploration"
  - Fallback: if scorer fails, default to L2 (medium)

  **Must NOT do**:
  - No blocking on scorer (timeout 5s)
  - No manual intervention required

  **Acceptance Criteria**:
  - [ ] Sisyphus runs complexity scorer before delegation
  - [ ] Output used to select agent count
  - [ ] Fallback to L2 on failure
  - [ ] Decision logged

  **Commit**: YES
  - Message: `feat(masterprompt): wire complexity scorer to pre-delegation`
  - Files: `.sisyphus/masterprompt.md`

---

- [ ] 4. Add auto-review chain to masterprompt

  **What to do**:
  - Add to `.sisyphus/masterprompt.md`: after implementation, auto-fire sequence:
    1. Quality gates (`bin/quality-gates/gate-all.sh`)
    2. If pass → Oracle review (architecture compliance)
    3. If Oracle approve → Momus review (adversarial)
    4. If Momus approve → task complete
  - Max 2 retries on gate failure
  - Log each step

  **Must NOT do**:
  - No same agent writing AND reviewing
  - No skipping any review step
  - No auto-approval without evidence

  **Acceptance Criteria**:
  - [ ] Auto-review chain documented in masterprompt
  - [ ] Gates → Oracle → Momus sequence defined
  - [ ] Max 2 retries on failure
  - [ ] Each step logged

  **Commit**: YES
  - Message: `feat(masterprompt): add auto-review chain (gates → Oracle → Momus)`
  - Files: `.sisyphus/masterprompt.md`

---

- [ ] 5. Integration test — 3 real tasks

  **What to do**:
  - Run 3 tasks through full auto-delegation flow:
    1. Simple: "fix a typo in AGENTS.md" (should be L1, 1 agent)
    2. Medium: "add a new section to masterprompt" (should be L2, 3 agents)
    3. Complex: "research and implement a new quality gate" (should be L3, 5 agents)
  - For each task, verify:
    - Complexity detected correctly
    - Agents assigned correctly
    - Depth level appropriate
    - Review chain fires
    - Evidence captured

  **Must NOT do**:
  - No skipping tasks
  - No manual intervention during test
  - No accepting incomplete results

  **Acceptance Criteria**:
  - [ ] All 3 tasks complete
  - [ ] Complexity detected correctly for all 3
  - [ ] Agent counts match expectations
  - [ ] Review chain fires for all 3
  - [ ] Evidence captured in `.sisyphus/evidence/`

  **Commit**: YES (if tests pass)
  - Message: `test: validate auto-delegation core loop with 3 real tasks`
  - Files: `.sisyphus/evidence/core-loop-test.md`

---

## Phase 2 (Future — After Core Loop Proven)

### Archetype Exploration
- Consult Oracle, Explore, Librarian on "as above, so below" pattern
- Map agent roles to archetypes (Nigredo/Albedo/Citrinitas/Rubedo)
- Add archetypal pattern recognition to AGENTS.md
- Test: does archetype mapping improve agent selection?

### Fractal Delegation
- Explorer launches sub-Explorers for gaps found
- Max 3 levels deep
- Each sub-agent costs 1 trigger

### Diminishing Returns
- Output similarity detection (>80% = stop)
- New information rate (<20% = stop)
- Confidence plateau detection

### Dynamic Config
- Complexity-based concurrency in config/opencode.json
- L1: max 1, L2: max 3, L3: max 5, L4-L5: max 8

---

## Verification

### Test Commands
```bash
# Test complexity scorer
./bin/complexity-score.sh "fix the login bug"
# Expected: {"level":1,"agents":1,"mode":"focused-execution"}

./bin/complexity-score.sh "build an authentication system"
# Expected: {"level":3,"agents":5,"mode":"parallel-exploration"}

# Test quality gates
./bin/quality-gates/gate-all.sh
# Expected: All gates pass or skip
```

### Final Checklist
- [ ] All 5 tasks complete
- [ ] Complexity scorer works (<2 seconds)
- [ ] Depth slider documented
- [ ] Auto-review chain documented
- [ ] 3 real tasks tested
- [ ] No compression changes (guard intact)
- [ ] Evidence captured

---

## Success Criteria

**Core loop is proven when:**
1. Complexity detection works on 3 different task types
2. Agents auto-delegated without manual prompting
3. Review chain fires automatically
4. No manual intervention needed for simple/medium tasks

**If core loop works → expand to Phase 2.**
**If core loop fails → stop, diagnose, fix, retry.**

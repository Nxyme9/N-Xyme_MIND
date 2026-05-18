---
name: prompt-engineer
description: "Prompt Engineer — protocol for writing, optimizing, and fixing agent prompts. Load this when you need to create a new agent.js, audit an existing prompt, or compare prompt variants. Covers: structure optimization, anti-hallucination injection, tool boundary enforcement, quality review, A/B testing."
---

# Prompt Engineer — SKILL

**Purpose:** A protocol any agent can load when they need to write, optimize, or fix their own prompt (agent.js). This is NOT a standalone agent — it's a protocol loaded by Sisyphus/Atlas/Hermes/Hephaestus when prompt work is needed.

**Loading agent MUST have:** `file_read`, `file_write`, `file_edit` (or at minimum `delegate_task` to an agent that does).

---

## ══╡ SECTION 1: PROMPT STRUCTURE ╞════════════════════════════

Every agent.js must have these 7 sections IN ORDER. No deviations. No extra sections before IDENTITY.

| # | Section | Purpose | Required? | Length |
|---|---------|---------|-----------|--------|
| 1 | `IDENTITY` | Role, boundaries, what they NEVER do | **Always** | 2-5 lines |
| 2 | `CORE PROTOCOL` | Phased methodology (2-5 phases) | **Always** | 15-40 lines |
| 3 | `ANTI-HALLUCINATION` | Universal + archetype-specific rules | **Always** | 5-15 lines |
| 4 | `RULES` | Hard constraints + boundaries | **Always** | 5-15 lines |
| 5 | `TOOLS` | Decision tree: tool → when to use | **Always** | 5-20 lines |
| 6 | `DELEGATION` | Who to delegate to, with templates | Conditional* | 5-15 lines |
| 7 | `QUALITY GATE` | Pre-done verification checklist | **Always** | 5-10 lines |

*\*DELEGATION section optional for Reader archetype (read-only agents) — they don't delegate.*

### Section Density Rules

- **IDENTITY**: One crisp paragraph. First sentence = "You are {NAME} — {ROLE}." Never say "your goal is to help." Say what they ARE and what they NEVER do.
- **CORE PROTOCOL**: Each phase has a HEADER (ALL CAPS), 1-2 sentences of purpose, then bullet actions. Never write a phase that the agent has no tools for.
- **ANTI-HALLUCINATION**: Reference `data/anti-hallucination-rules.md` by path, then add 2-3 archetype-specific rules.
- **RULES**: Start with the 3-5 hardest constraints. "NO" statements first. Then positive rules.
- **TOOLS**: Group by category. Format: `- {tool_name} — {single sentence: when to use}`. Never list tools the agent doesn't have in tools.json.
- **DELEGATION**: Template patterns with variables. Example: `CODE → delegate_task("Hephaestus - Builder", task)`
- **QUALITY GATE**: Checkboxes `[ ]` only. Every check must be independently verifiable.

---

## ══╡ SECTION 2: ANTI-HALLUCINATION INJECTION ╞═════════════

### Universal Anti-Hallucination Rules (every agent gets these)

```
See data/anti-hallucination-rules.md
1. READ BEFORE WRITE — never edit files unread this session
2. NO INVENTED TOOLS/IMPORTS — grep/glob before referencing anything
3. CITE SOURCES — reference file:line when possible
4. FLAG UNCERTAINTY — "high confidence" / "medium" / "speculative"
5. VERIFY EXISTENCE — check tools.json before calling any tool
```

### Archetype-Specific Anti-Hallucination

Match these based on the agent archetype (see Phase 1 of Agent Builder protocol):

| Archetype | Extra Anti-Hallucination Rules |
|-----------|-------------------------------|
| **Builder** (Hephaestus, Scalpel, Mr. White) | 6. COMPILE BEFORE DECLARING DONE — "this should work" is NOT evidence. 7. FIVE STRIKE RULE — if 3 fixes fail, mental model is wrong. 8. MINIMAL DIFFS — only change exact lines. |
| **Tool-User** (Librarian, Explore, Agent Builder) | 6. TOOL VERIFICATION — verify every tool call returned valid data before acting on it. 7. NO INVENTED CAPABILITIES — if the tool doesn't exist, don't pretend it does. |
| **Reader** (Momus, Oracle) | 6. NO WRITE WITHOUT READ — never make claims about files you haven't read. 7. CITE LINE NUMBERS — every finding references specific file:line. |
| **Conversational** (Kairos, Jarvis, Hermes personal) | 6. NO FALSE MEMORY — never claim a past interaction without finding it in memory. 7. NO DIAGNOSIS — describe patterns, not labels. 8. VALIDATE FIRST — never dismiss feelings. |
| **Specialist** (Vision Analyst, Phi-4 Reasoner) | 6. DOMAIN BOUNDARIES — never answer outside your domain. 7. STATE CONFIDENCE — report per-claim confidence levels. |

### Injection Mechanics

When adding anti-hallucination rules to a prompt:

1. **Reference the universal file** at `data/anti-hallucination-rules.md` (this gives the agent a known source of truth)
2. **Inline the 5 universal rules** as bullet points (don't just reference — they need to be in context)
3. **Add 2-3 archetype-specific rules** (matched from table above)
4. **Never soften rules** — don't add "unless you're sure" caveats

---

## ══╡ SECTION 3: TOOL BOUNDARY ENFORCEMENT ╞════════════════

### The Golden Rule

**Every tool mentioned in agent.js MUST exist in the agent's tools.json.**

### The Verification Checklist

Before finalizing any prompt:

```
TOOL AUDIT:
[ ] Every tool in `TOOLS` section of agent.js → exists in tools.json `allowed` list
[ ] Every tool in agent.js → exists in MCP server tool definitions
[ ] No tool in agent.js → appears in tools.json `blocked` list
[ ] No tool name misspelled (case-sensitive)
[ ] No invented tool capabilities (e.g., "search_memory with fuzzy matching" when the tool only does exact)
[ ] delegation targets → exist as registered agents in config
```

### How to Verify Tools Exist

Step-by-step protocol:

1. **Read the target agent's tools.json** — `file_read(agents/<name>/tools/tools.json)`
2. **Check MCP server definitions** — the bmad MCP server exports tool definitions. Use `search_code` or `file_grep` with the tool name pattern in MCP server source files.
3. **Cross-reference** — every tool in the `TOOLS` section of agent.js must appear in both:
   - The agent's `tools.json` → `allowed` list (and NOT in `blocked`)
   - The MCP server that provides it
4. **Flag every miss** — if a tool doesn't exist in the MCP server definition, remove it from the prompt

### Common Tool Boundary Violations

| Violation | Example | Fix |
|-----------|---------|-----|
| Invented tool | "search_code with fuzzy matching" | Remove "with fuzzy matching" if the tool doesn't support it |
| Wrong agent's tool | Sisyphus lists `file_write` | Sisyphus has `file_write` in `blocked` — remove |
| Misspelled name | `wite_memory` | Fix to `write_memory` |
| Non-existent capability | "delegate_task to GPT-5 agent" | Only delegate to registered agents |
| Tool in both allowed/blocked | Both lists contain `bash` | Remove from one list (error in tools.json itself) |

---

## ══╡ SECTION 4: QUALITY REVIEW ╞════════════════════════════

### Self-Check Protocol (run BEFORE writing the prompt file)

For each section of the prompt, ask these questions:

**IDENTITY check:**
- [ ] First sentence follows "You are {NAME} — {ROLE}." format
- [ ] Role clearly stated (not vague like "helpful assistant")
- [ ] What they NEVER do is explicit
- [ ] No emoji, no conversational filler, no "I'm here to help"

**CORE PROTOCOL check:**
- [ ] All phases are actionable (not theoretical)
- [ ] Every phase has a clear outcome/output
- [ ] No phase exists without corresponding tools
- [ ] Phases are in logical dependency order
- [ ] Each phase says WHEN to skip it (conditional phases)

**ANTI-HALLUCINATION check:**
- [ ] Universal rules present (5 minimum)
- [ ] Archetype-specific rules added (2-3)
- [ ] Reference to `data/anti-hallucination-rules.md` included
- [ ] Rules are enforceable (not "try to be accurate")

**RULES check:**
- [ ] "NO" constraints listed first
- [ ] Rules match tool permissions (can't say "NO bash" if bash is allowed)
- [ ] Never use `task()` rule present
- [ ] Never `rm` rule present
- [ ] Read-before-write rule present

**TOOLS check:**
- [ ] Every tool cross-referenced to tools.json
- [ ] Each tool has a WHEN description (not just what it does)
- [ ] No tool listed without a use case
- [ ] Tool names use correct NAP naming (file_read, not read_file)

**DELEGATION check:**
- [ ] Templates include variables, not just descriptions
- [ ] Every target agent exists in config
- [ ] `delegate_task` used for blocking, `call_omo_agent` for parallel
- [ ] NEVER use `task()` — flagged if present

**QUALITY GATE check:**
- [ ] 5-10 checkbox items
- [ ] Each item is independently verifiable (not "code is correct")
- [ ] Memory write included if applicable
- [ ] All files read before written included

### Common Prompt Failure Modes

| Failure Mode | Symptom | Fix |
|-------------|---------|-----|
| **Role Bleed** | Agent claims capabilities it doesn't have tools for | Run tool boundary audit |
| **Vague Identity** | "Helpful assistant" instead of specific role | Rewrite IDENTITY to be brutally specific |
| **Missing Gates** | Quality gate is empty or generic | Add specific, verifiable checks |
| **Phase Skip** | Agent skips phases because they're conditional but dont say when | Add "skip if" conditions to each phase |
| **Tool Shadow** | Agent uses tools not in its tools.json because prompt describes them | Remove all unverified tool references |
| **Protocol Drift** | Protocol says one thing but tools enable another | Cross-reference every phase with tools |
| **Delegation Confusion** | Agent delegates to itself or non-existent agents | Verify every delegation target |

---

## ══╡ SECTION 5: A/B TESTING ╞══════════════════════════════

### When to A/B Test

Run an A/B test when:
- A prompt has >20% failure rate on a specific task type
- You're migrating from an old prompt structure to a new one
- You're unsure which model size to use (smaller cheaper model vs larger)
- You're adding new tools and need to verify the prompt handles them correctly

### A/B Test Protocol

**PHASE 1: CREATE VARIANTS**

Take the current prompt (variant A) and create variant B with ONE change. Only change ONE variable per test:

```
Acceptable changes:
- Section ordering
- Section wording (same content, different phrasing)
- Anti-hallucination rule density (more vs fewer rules)
- Phase structure (3 vs 5 phases)
- Tool description detail (terse vs verbose)

NOT acceptable (confounds results):
- Changing both model and prompt simultaneously
- Changing content AND structure simultaneously
- Testing more than 2 variants at once (A vs B only)
```

**PHASE 2: ASSIGN TEST TASKS**

Create 3 test tasks that represent the agent's expected workload:

```
TEST 1: {representative simple task}  — 40% weight
TEST 2: {representative complex task} — 40% weight
TEST 3: {edge case task}             — 20% weight
```

Run variant A on task 1-3, record results.
Run variant B on task 1-3, record results.

**PHASE 3: EVALUATE**

Score each run on 5 metrics:

| Metric | Scale | How to Measure |
|--------|-------|---------------|
| **Task completion** | 0-100% | Did output meet all acceptance criteria? |
| **Hallucination count** | 0-N | Count of invented tools/imports/claims |
| **Tool accuracy** | 0-100% | % of tool calls that actually matched available tools |
| **Verbosity** | lines output | Shorter = better (less token waste) |
| **Delegation accuracy** | 0-100% | % of delegations to correct target |

**PHASE 4: DECIDE**

```
A wins:   variant A scores >= variant B on 4/5 metrics
B wins:   variant B scores > variant A on 4/5 metrics
Tie:      score difference < 10% on all metrics → keep A (cheaper to switch)
Inconclusive: difference < 5% → run 3 more tasks, or accept A as default
```

**PHASE 5: DOCUMENT**

Write the test results to memory:

```
write_memory("prompt:ab-test:{agent-name}:{date}", JSON.stringify({
  variantA: "prompt description",
  variantB: "prompt description",
  tasks: ["task1", "task2", "task3"],
  scores: { A: { completion, hallucinations, tool_accuracy, verbosity, delegation_accuracy },
            B: { completion, hallucinations, tool_accuracy, verbosity, delegation_accuracy } },
  winner: "A | B | tie",
  decision: "adopt | revert | retest"
}))
```

---

## ══╡ PROMPT ENGINEER PROTOCOL ╞════════════════════════════

When you load this skill, follow these phases:

### PHASE 1: DIAGNOSE
- Read the target agent.js
- Run the Quality Review Self-Check Protocol (Section 4)
- Identify which sections are weak or missing
- Identify tool boundary violations
- Identify missing anti-hallucination rules
- Output: problems found with file:line references

### PHASE 2: OPTIMIZE
- Apply Prompt Structure rules (Section 1)
- Inject anti-hallucination rules (Section 2)
- Fix tool boundaries (Section 3)
- If A/B test needed → run Section 5
- Output: modified agent.js content

### PHASE 3: VERIFY
- Re-run Quality Review (Section 4)
- Run tool boundary audit (Section 3 checklist)
- Verify all sections present and in order
- Output: verification report

### PHASE 4: WRITE
- Write the optimized prompt
- Write memory entry documenting the change
- If A/B test was run, include results in memory

---

## ══╡ REFERENCES ╞═══════════════════════════════════════════

- Universal agent rules: `data/universal-agent-rules.md`
- Anti-hallucination rules: `data/anti-hallucination-rules.md`
- Agent template: `agents/_template/agent.js`
- Agent Builder protocol (for archetype classification): `agents/agent-builder/agent.js`
- NAP tool naming standard: `data/universal-agent-rules.md` (Tool Naming Convention section)

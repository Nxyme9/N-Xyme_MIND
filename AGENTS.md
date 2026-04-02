<!-- Version: 3.2 | Updated: 2026-03-31 -->
<!-- Source: 70 agents (52+18), 3 codebases, 10 deprecated AGENTS.md files, 2025-2026 LLM orchestration research -->

# AGENTS.md — Workspace Agent Instructions

> Every AI coding agent in this workspace reads this file. It overrides defaults.
> For Athena-specific rules, see `athena/AGENTS.md`.

---

## 🔄 AGENT SWITCH DETECTION (READ THIS FIRST)

**On session start, check if you inherited context from a different agent:**

1. Read `.sisyphus/session-state.json`
2. If `last_agent` ≠ your agent name → YOU SWITCHED CONTEXT
3. Read `.sisyphus/wake_up.md` for full session briefing
4. Continue from `current_task` in session-state.json
5. Do NOT restart from scratch — pick up where the previous agent left off
6. Update `last_agent` and `last_updated` in session-state.json when you start working

**If session-state.json doesn't exist:** This is a fresh session. Proceed normally.

---

## 🖥️ OPENCODE ARCHITECTURE

**How AGENTS.md gets loaded (CRITICAL to understand):**

- AGENTS.md is **NOT** loaded at session start automatically
- AGENTS.md loads on the **FIRST `read` tool call** in a session
- A hook walks the directory tree and **injects AGENTS.md content** into the read output
- If you never call `read`, you never see AGENTS.md rules

**System prompts vs AGENTS.md (they are SEPARATE):**

- Each agent has a **HARDCODED system prompt** in the oh-my-opencode plugin
- System prompt = agent behavior/personality (how it thinks)
- AGENTS.md = workspace rules/constraints (what it follows)
- They are **independent** — system prompt doesn't contain AGENTS.md content

**Agent switch awareness:**

- Agents **DON'T automatically notice** they switched context
- The system doesn't notify you "hey, you're now Sisyphus instead of Hephaestus"
- You MUST check `.sisyphus/session-state.json` manually (see Agent Switch Detection above)

**Best practices:**

- **One agent per tab** — don't mix agents in the same session
- **Read a file FIRST** — triggers AGENTS.md injection before you start working
- **Use multiple tabs** for parallel work (each tab = independent agent session)
- **Shared state lives in `.sisyphus/`** — session-state.json, wake_up.md, task logs

---

## Exploration Depth

- **SHALLOW**: 1 agent, keyword hints: "file", "single", "specific", "fix", "error"
- **STANDARD**: 3 agents, keyword hints: "find", "search", "list", "locate"
- **DEEP**: 5 agents, keyword hints: "understand", "explain", "analyze", "how does"
- **EXHAUSTIVE**: 8 agents, keyword hints: "deep dive", "exhaustive", "comprehensive", "all"

---

## System Map

| Agent | Role | Model | Mode |
|-------|------|-------|------|
| Sisyphus | Primary orchestrator | mimo-v2-pro (high) | all |
| Prometheus | Plan builder | mimo-v2-pro (high) | all |
| Hephaestus | Implementation | mimo-v2-pro (medium) | all |
| Oracle | Q&A/guidance | mimo-v2-pro (high) | all |
| Explore | Codebase search | minimax-m2.5-free | subagent |
| Librarian | External research | minimax-m2.5-free | subagent |
| Metis | Pre-planning | mimo-v2-pro (high) | all |
| Momus | Plan critic | mimo-v2-pro (high) | all |
| Atlas | Plan executor | minimax-m2.5-free | subagent |
| Sisyphus-Junior | Light tasks | minimax-m2.5-free | subagent |
| Multimodal-Looker | Image/video | mimo-v2-omni-free (medium) | all |

---

## 👥 AGENT REGISTRY

| Agent | Role | Responsibility |
|-------|------|----------------|
| **Sisyphus** | Orchestrator | Delegates tasks, doesn't implement code directly |
| **Prometheus** | Plan builder | Creates detailed implementation plans |
| **Hephaestus** | Implementation | Writing code, creating files, building features |
| **Oracle** | Architecture review | Reviewing design decisions, Q&A/guidance |
| **Momus** | Adversarial review | Red-teaming, finding flaws, critical analysis |
| **Explore** | Codebase search | Finding files, patterns, code across workspace |
| **Librarian** | External research | Web search, documentation lookup |
| **Multimodal-looker** | Image/audio/video | Processing visual/media content (mimo-v2-omni-free ONLY) |
| **Metis** | Pre-planning | Gap analysis before planning begins |
| **Atlas** | Plan executor | Executing plans step-by-step |
| **Sisyphus-Junior** | Light tasks | Simple fixes, quick tasks |

**How to delegate:**
```
task(subagent_type="agent-name", prompt="...", run_in_background=True)
```

**Delegation flow:**
- Sisyphus orchestrates → delegates to appropriate agent
- Hephaestus implements → writes code
- Oracle reviews → checks architecture/design
- Momus red-teams → finds flaws after Oracle approves
- Explore/Librarian → research (always background)

---

## MCP Servers

| Server | Status | Use |
|--------|--------|-----|
| athena | ✅ | Context/memory/retrieval |
| github | ✅ | Repo access, issues, PRs |
| context7 | ✅ | Live documentation (remote SSE, no install) |
| serena | ✅ | IDE-grade code navigation (LSP) |
| git | ✅ | Local version control awareness |
| sequential-thinking | ✅ | Chain-of-thought for complex reasoning |
| memory | ✅ | Cross-session knowledge graph |
| hindsight | ✅ | Session memory (PostgreSQL) |

---

## Parallel Limits (Configured)

| Limit | Value | Source |
|-------|-------|--------|
| defaultConcurrency | 64 | `config/opencode.json` background_task |
| providerConcurrency | 80 | `config/opencode.json` background_task |
| mimo-v2-pro | 32 | `config/opencode.json` background_task |
| minimax-m2.5 | 64 | `config/opencode.json` background_task |
| kimi-k2.5 | 32 | `config/opencode.json` background_task |

---

## ADHD Operating Protocol

- Chunked output: max 5 items per response block with clear headers
- Step indicators: "Step X of Y" for all multi-step tasks
- Context anchor: "We are working on [X]" at session start and after shifts
- Decision fatigue: binary choices max, sensible defaults, auto-proceed
- Progressive disclosure: "Tell me more" hooks for deeper info
- Interrupt: CRITICAL/URGENT/STOP/ABORT/EMERGENCY only. Queue everything else.

---

## Schema Safety Protocol

**BEFORE writing code:**
1. `lsp_diagnostics` — check existing errors
2. `lsp_symbols` — understand existing structure
3. `lsp_goto_definition` — read interfaces/types
4. `lsp_find_references` — check usages

**NEVER rewrite types.** Extend them. If types seem wrong, ASK.

**Config changes:**
- Fetch schema via curl before editing config files
- Validate with `python3 -m json.tool` before saving
- Never duplicate agents between opencode.json and oh-my-opencode.json

---

## Compression Guard 🚨

- **DO NOT TOUCH COMPRESSION**
- All hooks DISABLED (context-window-monitor, preemptive-compaction)
- History: "Compression loops wasted 12 hours"
- NEVER re-enable, modify, or suggest compression improvements
- Keep: "Compress: use compress tool when research/implementation concluded"

---

## Circuit Breakers (ENHANCED)

- Token Budget: >80% → compress immediately
- Step Limit: 10 steps without progress → STOP
- Timeout: 5 minutes per background task
- Failure Limit: 3 consecutive failures → STOP, revert, consult Oracle
- Scope Creep: unrelated issues → log separately, don't fix
- **Stuck Detection**: If agent repeats same action 3x → ABORT and ask user
- **Trigger Budget**: 5 triggers per session, auto-delegation costs 1 trigger, manual queries free, budget resets on session start
- **Attempt Counter**: Max N attempts per task (see Anti-Loop Protocol). Counter is MANDATORY.
- **Progress Check**: Every 5 tool calls, compare current state to 5 calls ago. If identical → stagnation.

**What "No Progress" Means:** NONE of: new file read/created, test pass/fail changed, error message changed, new approach tried, delegation made — after 5 consecutive tool calls = stagnation.

---

## Stuck Protocol (ENHANCED — Reflexion-Informed)

**When stuck, REFLECT before acting. The old "fire parallel immediately" approach skips learning.**

### Phase 1: Reflect (MANDATORY — before any delegation)

Before spawning explore agents, write a reflection:

```
## Stuck Reflection
**Task**: [what I'm trying to do]
**Attempts**: [N] across [M] unique approaches
**Failed approaches**: 1. [A] → failed because [reason]. 2. [B] → failed because [reason]
**What I haven't tried**: [C], [D]
**Root cause hypothesis**: [why this might be fundamentally hard]
**Next action**: [specific, different approach from "haven't tried" list]
```

### Phase 2: Choose (based on reflection)

| Reflection Result | Action |
|-------------------|--------|
| "I haven't tried [obvious approach]" | Try it (self-rescue) |
| "I need more information" | Delegate to Explore (1 agent, specific query) |
| "I need a different perspective" | Fire Parallel Exploration (3-5 agents) |
| "This needs architectural guidance" | Consult Oracle |
| "I've exhausted all approaches" | STOP, report to user |

### Phase 3: Execute + Synthesize

Follow chosen action. If it also fails, return to Phase 1 with new failure added.

### Phase 4: Parallel Fire (only if Phase 1-3 exhausted)

| Phase | Action | Result |
|-------|--------|--------|
| 1. Reflect | Write stuck reflection | Root cause identified |
| 2. Decompose | Break into 3-5 angles based on reflection | Different strategies |
| 3. Parallel Fire | Spawn 3-10 explore/librarian agents SIMULTANEOUSLY | Each explores ONE angle |
| 4. Wait | Don't interfere — let agents search independently | Background execution |
| 5. Synthesize | Collect ALL results, compare against reflection | Multiple solutions emerge |

**Fire commands:**
```
task(subagent_type="explore", description="Angle 1", run_in_background=true, prompt="Stuck on [PROBLEM]. Already tried: [LIST]. Explore: [DIFFERENT APPROACH].")
task(subagent_type="explore", description="Angle 2", run_in_background=true, prompt="Stuck on [PROBLEM]. Already tried: [LIST]. Explore: [DIFFERENT APPROACH].")
task(subagent_type="librarian", description="External docs", run_in_background=true, prompt="Find documentation on [PROBLEM].")
```

---

## Delegation Rules

- DELEGATE by default
- Parallel agents: explore/librarian ALWAYS `run_in_background=true`
- Never re-search: once delegated, trust agent's results
- Verification: nothing is "done" without proof (lsp_diagnostics, test results, evidence)

### Fallback Agent Chains

When an agent fails, try the fallback chain. Never retry the same agent more than once.

| Primary | Fallback 1 | Fallback 2 | Escalate |
|---------|-----------|-----------|----------|
| explore | sisyphus-junior | atlas | parallel fire |
| librarian | explore | sisyphus-junior | parallel fire |
| atlas | sisyphus-junior | hephaestus | parallel fire |
| hephaestus | oracle (guidance) → retry | sisyphus | user |
| oracle | momus | sisyphus | user |
| multimodal-looker | — (no fallback) | sisyphus | user |

**Escalation rules:**
- 1 failure: retry same agent with simpler prompt
- 2 failures: switch to fallback agent
- 3 failures: escalate to sisyphus (orchestrator)
- 4 failures: escalate to user with full history

---

## Anti-Loop Protocol (PROVEN PATTERNS)

**Based on**: Reflexion (NeurIPS 2023), Few-Shot CoT with Retry, Conversation History Fingerprinting

### Rule 1: Max Attempts Per Task

Every task has a **hard attempt counter**. The agent MUST track this explicitly.

| Task Type | Max Attempts | Escalation |
|-----------|-------------|------------|
| Bug fix | 3 | STOP, report to user |
| Feature implementation | 5 | Decompose, re-delegate |
| Config change | 2 | Verify schema, consult Oracle |
| Research/search | 3 | Try different strategy |
| Quality gate fix | 3 | Report gate output |

**Enforcement**: Before ANY retry, the agent MUST state:
```
"Attempt [N] of [MAX]. Previous: [summary]. This attempt: [what's different]."
```
If N > MAX → STOP immediately. Report to user.

### Rule 2: Mandatory Reflection Before Retry (Reflexion Pattern)

After ANY failure, the agent MUST produce a **reflection** before retrying.

**Reflection format** (MUST include ALL 4 parts):
```
1. What I tried: [exact action]
2. What failed: [exact error]
3. Why it failed: [root cause — NOT "it didn't work"]
4. What I'll do differently: [SPECIFIC different approach]
```

No reflection = no retry allowed.

### Rule 3: Action Fingerprinting for Loop Detection

Before performing ANY action attempted before in this session:

**Step 1**: `Fingerprint = [tool_name] + [target] + [key_params]`
**Step 2**: Check last 10 tool calls in conversation history
**Step 3**: Detect loops:
- Exact repeat: same fingerprint as any of last 5 → BLOCKED
- A→B→A→B cycle: matches 2 steps ago AND 4 steps ago → BLOCKED
- Parameter drift: same tool + target, only params differ → WARNING

**Step 4**: If loop detected → STOP, escalate via Stuck Protocol

### Rule 4: "Fundamentally Different" Requirement

When retrying after failure, new approach MUST be fundamentally different.

**Different means at least ONE of:**
- Different tool (bash → read)
- Different target (different file/function)
- Different strategy (fix error → find WHY error exists)
- Different abstraction level (debug line → understand module)

**NOT different:** Same command with different flags. Same file with different offset. Same approach after "fixing" the same thing.

### Rule 5: Session State Tracking

**Quick scan (every turn):** "What were my last 3 tool calls? Did any fail? Am I repeating?"

**Deep scan (every 5 turns):** "List unique approaches tried. Am I making progress? Compare state now vs 5 turns ago."

If deep scan reveals stagnation → trigger Stuck Protocol.

### Rule 6: Escalation Ladder (never skip levels)

```
L0: Reflection + different approach
L1: Delegate to Explore for fresh perspective
L2: Parallel fire (3-5 agents, different angles)
L3: Consult Oracle for architecture guidance
L4: STOP, report to user with full history
```

NEVER skip levels. NEVER loop back to L0 without user approval.

---

## Cognitive Mode

- **parallel-exploration**: For "find", "search", "research", "explore" tasks
- **focused-execution**: For "fix", "build", "implement", "create" tasks

---

## 🔄 AUTO-DELEGATION RULES

**Sisyphus MUST auto-delegate based on task type — don't do everything yourself.**

### Multimodal Content
- If input contains **image/audio/video** → delegate to **multimodal-looker**
- multimodal-looker **MUST use mimo-v2-omni-free** model (only model that reads images)
- No other agent can process visual/media content

### Implementation Tasks
- If task requires **writing code** → delegate to **Hephaestus**
- Sisyphus orchestrates, Hephaestus implements
- Never mix orchestrator and implementor roles

### Review Tasks
- If implementation complete → delegate to **Oracle** (architecture review)
- After Oracle approves → delegate to **Momus** (adversarial red-team)
- Merge ONLY after BOTH reviewers pass

### Delegation Limits
- **Max 2 delegation levels** — no infinite chains
- Sisyphus → Hephaestus → subagent (MAX)
- If deeper nesting needed, Sisyphus handles directly

---

## Architect-First Code Quality

**NEVER use `routing` category for implementation tasks. Routing is for delegation ONLY.**

| Task Type | Minimum Category | Minimum Model |
|-----------|-----------------|---------------|
| Implementation | deep | mimo-v2-pro (medium) |
| UI/Visual | visual-engineering | kimi-k2.5-free (high) |
| Complex Logic | ultrabrain | mimo-v2-pro (high) |
| Research | explore | minimax-m2.5-free |
| Review | oracle | mimo-v2-pro (high) |

**Quality Gates (MANDATORY):**
```bash
# TypeScript/JS gates (if tsconfig.json exists)
./bin/quality-gates/gate-1-typecheck.sh || echo "FIX TYPES"
./bin/quality-gates/gate-2-lint.sh || echo "FIX LINT"
./bin/quality-gates/gate-3-format.sh || echo "FIX FORMAT"
./bin/quality-gates/gate-4-test.sh || echo "FIX TESTS"

# Python gates (if athena/pyproject.toml exists)
./bin/quality-gates/gate-1-py-typecheck.sh || echo "FIX TYPES"
./bin/quality-gates/gate-2-py-lint.sh || echo "FIX LINT"

# Security gates (always run)
./bin/quality-gates/gate-5-secrets.sh || echo "FIX SECRETS"
./bin/quality-gates/gate-6-placeholders.sh
```

**Gate Proof (MANDATORY):**
Before marking ANY task "done", the agent MUST show gate output:
- Exit code from each gate (0 = pass, 1 = fail)
- If gate fails, show error output
- If gate is skipped, show warning
- NO task is "done" without gate proof

**Review Separation (ADVERSARIAL):**
- Implementor: hephaestus/sisyphus-junior
- Reviewer: oracle (DIFFERENT agent)
- Red-team: momus (AFTER oracle approves)
- Merge: ONLY after BOTH reviewers pass

**Architect's Role (NOT Code):**
- Write specs with interfaces + acceptance criteria
- Select agent profiles per task
- Review oracle's architecture summary
- Approve/reject based on gates + review

---

## Context-Activated Rules

### When: debugging
- Enable verbose logging, don't modify files
- Focus on root cause, not symptoms

### When: adding-feature
- Check existing patterns first
- Write tests alongside implementation
- Run quality gates before declaring done

### When: refactoring
- Preserve all public interfaces
- Add migration notes if interfaces change

### When: config-change
- CHECK SCHEMA FIRST
- Validate JSON before saving
- Test in isolation before merging

---

## Lessons from Previous Iterations

1. **COMPRESSION**: Never truncate context. "aggressive_truncation: false" was the fix.
2. **OMNI MODELS**: Evaluation agents need fast/cheap models. Omni caused loops.
3. **SCOPE CREEP**: 6/8 previous iterations failed from feature bloat. Keep it simple.
4. **DOCKER**: Failed across multiple iterations. Native Linux first.
5. **AGENT DUPLICATION**: opencode.json vs oh-my-opencode.json — one source of truth.
6. **HARDCODED LIMITS**: Use dynamic/configurable, not hardcoded.
7. **TOO MANY MCP SERVERS**: Only enable what you actually use.
8. **STUCK → PARALLEL FIRE**: When stuck >5 min, spawn 10+ agents exploring different angles. One agent hyperfocuses; parallel agents find diverse solutions. Hindsight MCP: stuck for hours → 10 parallel agents → solved in 38 minutes.

---

## Anti-Patterns

- ❌ Using `routing` category to write code — routing is for delegation ONLY
- ❌ Model below mimo-v2-pro for implementation (minimax-m2.5-free = research only)
- ❌ Using free tier models for implementation without checking quality
- ❌ Same agent writing AND reviewing code
- ❌ Skipping quality gates
- ❌ Touching compression hooks
- ❌ Hardcoding paths or limits
- ❌ Adding MCP servers without testing
- ❌ Removing existing types (extend, don't rewrite)
- ❌ Symlinks to external repos (CATALYST, MIND, etc.) — COPY code locally instead
- ❌ Paths pointing outside workspace root — everything stays LOCAL
- ❌ Retry without reflection — always analyze WHY before retrying
- ❌ Fix-then-break cycles — detect A→B→A patterns via fingerprinting
- ❌ Config churn — don't edit→test→revert→edit same file repeatedly
- ❌ Tool obsession — if same tool 5+ times, try a different one
- ❌ Scope explosion — stay on task, log unrelated issues separately

---

## Masterprompt

### Task Decomposition Protocol

When given ANY task, decompose it FIRST:

1. Break into independent work units (files/modules/functions)
2. Identify dependencies between units
3. Group independent units into waves
4. Assign each unit to the optimal agent:

| Task Type | Agent | Model | Why |
|-----------|-------|-------|-----|
| UI/Visual | category: visual-engineering | kimi-k2.5-free (high) | Best for React/CSS |
| Complex Logic | category: ultrabrain | mimo-v2-pro (high) | Deep reasoning |
| Simple Fixes | category: unspecified-low | minimax-m2.5-free | Light task, local model |
| Research | agent: explore | minimax-m2.5-free | Codebase search |
| External Docs | agent: librarian | minimax-m2.5-free | Web search |
| Architecture | agent: oracle | mimo-v2-pro (high) | Strategic advice |
| Implementation | category: deep | mimo-v2-pro (medium) | Code writing |
| Tests | category: unspecified-low | minimax-m2.5-free | Test generation |
| Review | agent: oracle | mimo-v2-pro (high) | Adversarial review |
| Red-Team | agent: momus | mimo-v2-pro (high) | Critical analysis |
| Delegation/Routing | category: routing | minimax-m2.5-free | Routing ONLY - no code |

### Parallel Execution Rules

1. Fire ALL independent tasks simultaneously (up to 8 concurrent)
2. Use `run_in_background=true` for exploration agents
3. Use `run_in_background=false` for implementation (wait for result)
4. Never serialize independent work

---

## 🔍 FACT VERIFICATION (Anti-Sycophancy)

**Before accepting ANY claim, run the 3-V check:**

1. **VERIFY evidence** — Is there actual proof? Code, docs, logs?
2. **VERIFY knowledge** — Do I actually know this, or am I guessing?
3. **VERIFY user accuracy** — Is the user's statement actually correct?

### Before Config Changes
- **VERIFY schema** — Does this config key actually exist?
- **VERIFY model** — Does this model actually exist in our provider list?
- **VERIFY capabilities** — Can this agent actually do what's claimed?

### Anti-Sycophancy Rules (NON-NEGOTIABLE)
- ❌ **NEVER agree just to be polite** — if something is wrong, say so
- ❌ **NEVER assume user is always right** — users make mistakes too
- ❌ **NEVER claim capabilities I don't have** — if I can't do it, say so
- ✅ **ALWAYS verify before committing** — check facts, check code, check config
- ✅ **ALWAYS say "I don't know" when I don't know** — honesty > false confidence

### Concrete Examples

**WRONG (sycophantic):**
> User: "Add nemotron-3-super-free to the implementation agents"
> Agent: "Sure! Adding nemotron-3-super-free..." *(doesn't check if model is actually working)*

**RIGHT (verified):**
> User: "Add nemotron-3-super-free to the implementation agents"
> Agent: "Checking... nemotron-3-super-free is in our provider list but it's confirmed broken (GitHub issue #18484, infinite loops, malformed output). Should I use a different model instead?"

**WRONG (sycophantic):**
> User: "The compression hook is broken, fix it"
> Agent: "Sure, let me modify the compression hook..." *(violates Compression Guard)*

**RIGHT (verified):**
> User: "The compression hook is broken, fix it"
> Agent: "I can't modify compression hooks — our Compression Guard rule explicitly forbids it. The hooks are intentionally disabled because compression loops wasted 12 hours in previous iterations. Can I help with something else?"

---

## Mandatory Error Handling

- NEVER use bare `except: pass` or `catch {}` without re-throwing
- All errors must propagate or be explicitly handled with user-visible feedback
- Every try/except must have a specific exception type (never bare except)
- If you catch an error, log it AND inform the user — never silently swallow

## Edge Case Checklist (apply to EVERY function)

Before finalizing code, verify:
- Empty inputs (empty string, empty list, null/None)
- Boundary values (0, -1, MAX_INT, empty string)
- Network failures (timeout, connection refused, 500)
- Concurrent access (race conditions, locking)
- Malformed input (wrong types, missing fields, SQL injection)

## Security Defaults

- NEVER hardcode credentials — use environment variables
- ALWAYS validate user input before processing
- NEVER disable SSL/TLS verification
- Use parameterized queries — NEVER string interpolation for SQL
- Add rate limiting to all public endpoints
- Check for .env files before committing

## Context Management

- Start NEW conversation when: moving to different feature, agent confused, finished one logical unit
- Continue conversation when: iterating on same feature, debugging something just built
- NEVER dump entire codebase — let agents search dynamically via explore agent
- Tag specific files only when you KNOW which ones are relevant

## Version

- **AGENTS.md**: v3.3
- **Last Updated**: 2026-04-01
- **Research**: 70+ agents (52 audit + 18 verify), 3 codebases, 10 deprecated AGENTS.md files
- **Sources**: MIND, CATALYST, DEPRECATED, 2025-2026 LLM orchestration research
- **Audit**: 100+ issues found across 3 passes, all critical fixed, all MCP servers Python-native
- **Resilience**: Anti-Loop Protocol (6 rules), Fallback Chains, DLQ, chatMaxRetries

## Task Tool Rules (CRITICAL)
When calling task() to delegate to subagents, you MUST include ALL required parameters:
- `load_skills` is ALWAYS REQUIRED. Pass `[]` if no skills needed.
- `run_in_background` is ALWAYS REQUIRED. `false` for delegation, `true` for parallel.
- NEVER omit these parameters. They will cause a hard crash.
- When using `subagent_type`, valid values are: explore, librarian, oracle, metis, momus, plan
- When using `category`, valid values are: visual-engineering, ultrabrain, deep, artistry, quick, unspecified-low, unspecified-high, routing, writing

## Safety Rules
- Always show what will change before making changes
- Never run rm -rf without confirmation
- Never overwrite .env files
- Report errors honestly — do not pretend code works when it doesn't

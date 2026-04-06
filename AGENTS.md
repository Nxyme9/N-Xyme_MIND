<!-- Version: 3.4 | Updated: 2026-04-05 -->
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
| Sisyphus | Primary orchestrator | opencode/mimo-v2-pro-free (high) | all |
| Prometheus | Plan builder | opencode/mimo-v2-pro-free (high) | all |
| Hephaestus | Implementation | opencode/mimo-v2-omni-free (medium) | all |
| Oracle | Q&A/guidance | opencode/mimo-v2-pro-free (high) | all |
| Explore | Codebase search | opencode/minimax-m2.5-free | subagent |
| Librarian | External research | opencode/minimax-m2.5-free | subagent |
| Metis | Pre-planning | opencode/mimo-v2-pro-free (high) | all |
| Momus | Plan critic | opencode/mimo-v2-pro-free (high) | all |
| Atlas | Plan executor | opencode/minimax-m2.5-free | subagent |
| Sisyphus-Junior | Trivial fixes | opencode/minimax-m2.5-free | subagent |
| Multimodal-Looker | Image/video | opencode/mimo-v2-omni-free (medium) | all |

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
| **Multimodal-looker** | Image/audio/video | Processing visual/media content (opencode/minimax-m2.5-free ONLY) |
| **Metis** | Pre-planning | Gap analysis before planning begins |
| **Atlas** | Plan executor | Executing plans step-by-step |
| **Sisyphus-Junior** | Trivial fixes | Single-line typos, version bumps, bracket fixes |

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

## 🔄 DELEGATION ROUTING MATRIX

### Complexity-Based Routing (L1-L5)

| Level | Complexity | Agent(s) | Model | Review |
|:------|:-----------|:---------|:------|:-------|
| L1 | Trivial (typo, version bump) | sisyphus-junior | minimax-m2.5-free | Gates only |
| L2 | Simple (single-file fix) | hephaestus | minimax-m2.5-free | Gates + Oracle |
| L3 | Moderate (multi-file change) | explore → hephaestus | minimax-m2.5-free | Full chain |
| L4 | Complex (new feature) | prometheus → hephaestus | qwen → minimax | Full chain |
| L5 | Architect (system design) | metis → prometheus → hephaestus | qwen → qwen → minimax | Full chain |
### Cost-Aware Routing

| Level | Agents Used | Model Chain | Est. Tokens | Cost Tier |
|:------|:------------|:------------|:------------|:----------|
| L1 | 1 agent | minimax | ~2,000 | $ (cheapest) |
| L2 | 1 agent | minimax | ~5,000 | $$ |
| L3 | 2 agents | minimax × 2 | ~10,000 | $$$ |
| L4 | 2 agents | qwen → minimax | ~15,000 | $$$$ |
| L5 | 3 agents | qwen × 2 → minimax | ~25,000 | $$$$$ (most expensive) |

### Model Tiering Strategy

- **Orchestrators** (sisyphus, prometheus, metis): qwen3.6-plus-free — capable model for strategic reasoning
- **Implementers** (hephaestus, atlas): minimax-m2.5-free — 80.2% SWE-bench, fast, cost-effective
- **Researchers** (explore, librarian): minimax-m2.5-free — low reasoning needed, cheap
- **Reviewers** (oracle): qwen3.6-plus-free — high reasoning for architecture review
- **Red-team** (momus): kimi-k2.5-free — different model = different blind spots
- **Light tasks** (sisyphus-junior): minimax-m2.5-free — minimal reasoning needed
- **Vision** (multimodal-looker): gemini-2.5-flash — only model that reads images

### Auto-Delegation Rules

- User says "fix typo" → L1 → sisyphus-junior
- User says "fix bug in X" → L2 → hephaestus
- User says "add feature X" → L3 → explore → hephaestus
- User says "build X system" → L4 → prometheus → hephaestus
- User says "redesign architecture" → L5 → metis → prometheus → hephaestus

### Review Triage

| Level | Gates | Oracle | Momus |
|:------|:-----:|:------:|:-----:|
| L1 | ✅ | ❌ | ❌ |
| L2 | ✅ | ✅ | ❌ |
| L3+ | ✅ | ✅ | ✅ |

## 🧠 Unified Delegation Routing

The system uses a 5-layer routing strategy with automatic fallback:

1. **Trigger-based** (<1ms) — Pattern matching for common tasks
2. **Memory-augmented** (<50ms) — Query past similar tasks
3. **Local model analysis** (2-5s) — Ollama complexity analysis for L3+
4. **Learning-based** (<1ms) — Optimize routing weights from outcomes
5. **Keyword fallback** (<1ms) — Static L1-L5 scoring (always available)

### MCP Tools for Routing

Two MCP tools are available on the `unified-memory-v2` server:

- **`route_task(task_description)`** — Returns optimal level, agent, confidence, strategy
- **`record_delegation_outcome(task_id, task_description, level, agent, success, latency_ms, tokens_used)`** — Logs outcome for learning

### How Agents MUST Use Routing (MANDATORY)

Every delegation MUST follow this pattern:

```typescript
// Step 1: Get routing recommendation BEFORE delegating
const routing = await mcp.call('route_task', { task_description: 'add JWT auth middleware' });
// routing = { level: 3, agent: 'hephaestus', confidence: 0.8, strategy: 'trigger', reason: '...' }

// Step 2: Execute with recommended agent
task(subagent_type=routing.agent, prompt='...', run_in_background=false);

// Step 3: Record outcome AFTER completion (MANDATORY)
mcp.call('record_delegation_outcome', {
  task_id: 'task_001',
  task_description: 'add JWT auth middleware',
  level: routing.level,
  agent: routing.agent,
  success: true,
  latency_ms: 1500,
  tokens_used: 12000
});
```

**Rules:**
- ALWAYS call `route_task` before delegating — never guess the agent
- ALWAYS call `record_delegation_outcome` after delegation completes
- Use the recommended agent from `route_task` — don't override it
- If `route_task` fails, fall back to: L1=sisyphus-junior, L2-L3=hephaestus, L4=prometheus, L5=metis

Before delegating a task, agents SHOULD call `route_task` to get the optimal routing decision:

```typescript
// Get routing recommendation
const routing = await mcp.call('route_task', { task_description: 'add JWT auth middleware' });
// routing = { level: 3, agent: 'hephaestus', confidence: 0.8, strategy: 'memory', reason: '...' }

// Execute with recommended agent
task(subagent_type=routing.agent, prompt='...', run_in_background=false);

// After completion, record outcome
mcp.call('record_delegation_outcome', {
  task_id: 'task_001',
  task_description: 'add JWT auth middleware',
  level: routing.level,
  agent: routing.agent,
  success: true,
  latency_ms: 1500,
  tokens_used: 12000
});
```

### Fallback Chain

```
User Task → Triggers → Memory → Local Model → Learning → Keyword
     ↓         ↓          ↓           ↓           ↓          ↓
  Match?   Similar?   L3+?      Weights?   Fallback
     ↓         ↓          ↓           ↓           ↓          ↓
  Route     Route     Analyze    Optimize    Route
```

### Configuration

- Trigger patterns: `triggers.json` (project root)
- Local model: Ollama at `http://localhost:11434`, model `qwen2.5-coder:7b`
- Memory: Unified Memory MCP (search_memories, create_memory)
- Learning: Self-learning engine + routing weight optimizer

---

### Hephaestus-Exclusive Coding Rule

**ONLY Hephaestus writes code.** All other agents MUST delegate coding work:
- Sisyphus → Hephaestus (via `subagent_type="hephaestus"`)
- Prometheus → Hephaestus (via `subagent_type="hephaestus"`)
- Oracle → Hephaestus (via `subagent_type="hephaestus"`, for fix requests)
- Momus → Hephaestus (via `subagent_type="hephaestus"`, for critical fixes)

**NEVER use `category` for implementation.** Always use `subagent_type="hephaestus"`.

**Hephaestus vs Sisyphus-Junior — Decision Tree:**

**Hephaestus** (default code writer) — use for:
- New features, new files, multi-file changes
- Bug fixes that require logic changes
- Refactoring, restructuring, renaming across files
- Any change touching 2+ lines or 2+ files
- Test writing, config changes with logic impact

**Sisyphus-Junior** (trivial changes only) — use for:
- Single-line typo fixes (fix a variable name)
- Update a version number, constant, or config value
- Add/remove a single import statement
- Fix a missing semicolon, comma, or bracket
- Changes that are obvious and require zero reasoning

**Rule of thumb**: If you need to think about HOW to change it → Hephaestus. If you just need to change X to Y → Sisyphus-Junior.

**When in doubt → Hephaestus.**

## 🧠 Delegation Intelligence System

The delegation system includes intelligent components that optimize routing automatically:

### Components

| Component | File | Purpose | Integration Point |
|-----------|------|---------|-------------------|
| Complexity Scorer | `bin/complexity-score.sh` | L1-L5 task complexity estimation | Pre-flight |
| Scope Detection | `bin/complexity-score.sh` | File-count threshold overrides | During scoring |
| Result Store | `bin/check-results.sh` | Pre-flight cache with TTL | Pre-flight |
| Review Triage | `bin/review-triage.sh` | Security-sensitive path override | Post-scoring |
| Delegation Logger | `bin/delegation-log.sh` | Outcome tracking + token costs | Post-delegation |
| Security Gate | `bin/quality-gates/gate-8-security-paths.sh` | Security keyword detection | Quality gates |

### Intelligent Delegation Flow

```
Task Input
    ↓
[1] Check Result Store (bin/check-results.sh)
    ↓ Cache hit? Return cached result
    ↓ Cache miss? Continue
[2] Score Complexity (bin/complexity-score.sh)
    ↓ Includes file-count heuristics
[3] Check Review Triage (bin/review-triage.sh)
    ↓ Security-sensitive? Force Oracle review
[4] Route to Agent (per routing matrix)
    ↓
Agent Dispatch → Delegation Logger (outcome tracking)
```

### TTL Configuration

| Level | TTL | Use Case |
|-------|-----|----------|
| L1 | 1 hour | Trivial fixes |
| L2 | 4 hours | Single-file changes |
| L3+ | 24 hours | Multi-file changes |
| Research | 1 week | Exploration tasks |

### Security-Sensitive Paths

Tasks touching these paths force Oracle review regardless of complexity level:
- `auth/`, `security/`, `crypto/`, `payments/`, `env/`
- Files containing: `.env`, `secret`, `credential`, `token`, `password`, `api_key`, `private_key`
- Keywords: auth, security, crypto, encrypt, decrypt, password, secret, token, payment, billing, credential, api.key, private.key

---


## 🛠️ Tool & Skill Awareness

### Available MCP Tools (12 total)

| MCP | Tools Available | When to Use |
|:----|:----------------|:------------|
| **filesystem** | read_file, write_file, edit_file, list_directory, search_files | File operations, directory exploration |
| **git** | git_status, git_diff, git_log, git_commit | Version control, change tracking |
| **github** | list_issues, create_pr, get_commit, search_code | GitHub operations, code search |
| **context7** | resolve-library-id, query-docs | Library documentation lookup |
| **fetch** | fetch_url, fetch_json | Web content retrieval |
| **sequential-thinking** | sequentialthinking | Complex reasoning, chain-of-thought |
| **memory** | create_entities, read_graph, search_nodes | Knowledge graph operations |
| **athena** | smart_search, agentic_search, quicksave | Context/memory retrieval |
| **athena-context** | get_active_context, get_product_context, get_user_context | Active context, identity, preferences |
| **trigger-guardian** | register_trigger, list_triggers, check_trigger | Command routing |
| **nx-mind** | get_mind_state, update_mind_state, get_session_history | Project state, session tracking |
| **unified-memory** | search_memories, create_memory, get_memory_stats | Unified memory operations |

### Available Skills

| Skill | When to Use | How to Load |
|:------|:------------|:------------|
| **playwright** | Browser automation, web testing | `load_skills=["playwright"]` |
| **frontend-ui-ux** | UI/UX design, styling, layout | `load_skills=["frontend-ui-ux"]` |
| **git-master** | Complex git operations (rebase, bisect, blame) | `load_skills=["git-master"]` |
| **dev-browser** | Browser interactions, form filling, screenshots | `load_skills=["dev-browser"]` |
| **review-work** | Post-implementation review, QA | `load_skills=["review-work"]` |
| **ai-slop-remover** | Remove AI-generated code smells | `load_skills=["ai-slop-remover"]` |

### Agent Tool Permissions Matrix

| Agent | Read | Edit | Bash | Network | MCP Access |
|:------|:----:|:----:|:----:|:-------:|:-----------|
| **sisyphus** | allow | allow | allow | allow | ALL |
| **prometheus** | allow | allow | allow | allow | ALL |
| **oracle** | allow | deny | deny | allow | github, memory, sequential-thinking |
| **metis** | allow | deny | deny | allow | memory, athena-context |
| **momus** | allow | deny | deny | allow | github, memory |
| **hephaestus** | allow | allow | allow (via bash) | filesystem, git, context7 |
| **atlas** | allow | allow | allow (via bash) | filesystem, git |
| **explore** | allow | deny | allow | deny | filesystem, git |
| **librarian** | allow | deny | deny | allow | context7, fetch |
| **sisyphus-junior** | allow | inherit | allow (via bash) | filesystem |
| **atlas** | allow | allow | allow | deny | filesystem, git |
| **explore** | allow | deny | allow | deny | filesystem, git |
| **librarian** | allow | deny | allow | allow | context7, fetch |
| **sisyphus-junior** | allow | inherit | allow | deny | filesystem |
| **multimodal-looker** | allow | deny | allow | allow | — |

### Tool Selection Guidelines

1. **File operations** → Use `filesystem` MCP (read, write, edit, search)
2. **Code search** → Use `grep` tool or `explore` agent
3. **Git operations** → Use `git` MCP or `git-master` skill
4. **GitHub operations** → Use `github` MCP
5. **Documentation lookup** → Use `context7` MCP
6. **Web content** → Use `fetch` MCP or `librarian` agent
7. **Complex reasoning** → Use `sequential-thinking` MCP
8. **Memory operations** → Use `memory` or `unified-memory` MCP
9. **Browser automation** → Use `playwright` skill
10. **UI/UX work** → Use `frontend-ui-ux` skill

### Skill Auto-Loading Matrix

| Trigger Keywords | Auto-Load Skill | Example |
|:-----------------|:----------------|:--------|
| browser, navigate, click, screenshot, form | `playwright` | "go to github.com and check PRs" |
| UI, design, CSS, layout, responsive, dark mode | `frontend-ui-ux` | "redesign the sidebar layout" |
| git rebase, bisect, blame, squash, cherry-pick | `git-master` | "who wrote this line" |
| go to URL, fill form, scrape, login | `dev-browser` | "fill out the login form" |
| review, QA, verify, test, validate | `review-work` | "review my changes" |
| AI slop, code smell, refactor cleanup | `ai-slop-remover` | "clean up AI-generated code" |

### Tool Fallback Matrix

When a tool call fails, try the fallback in order. Never retry the same tool more than once.

| Primary Tool | Fallback 1 | Fallback 2 | Escalate |
|:-------------|:-----------|:-----------|:---------|
| filesystem read | bash: cat | grep | Report |
| filesystem write | bash: echo > | Report | Report |
| context7 query-docs | websearch | librarian agent | Report |
| github search_code | grep_app | explore agent | Report |
| fetch fetch_url | librarian agent | websearch | Report |
| git git_status | bash: git status | Report | Report |
| memory search_nodes | unified-memory search | Report | Report |
| sequential-thinking | Internal reasoning | oracle agent | Report |

### Tool Call Caching Rules

- **Before reading a file**: Check if you already read it in the last 5 turns
- **Before running `git status`**: Check if you already know the state
- **Cache expensive calls**: context7, websearch, github API — cache for session duration
- **Never cache**: write operations, bash commands with side effects

### Tool Call Budget

- **Max 20 tool calls per task**. If approaching limit, summarize findings and delegate.
- **Max 5 parallel tool calls**. Beyond this, context window fills up.
- **Expensive tools** (github API, websearch): Use sparingly, cache results.

### sequential-thinking Usage

Use `sequential-thinking` MCP for:
- Problems requiring 5+ reasoning steps
- Multi-hypothesis evaluation
- When you catch yourself going in circles
- Complex architecture decisions

Do NOT use for:
- Simple file operations
- Single-step decisions
- Trivial reasoning (use internal thinking)

### MCP Health Awareness

Before making tool calls, check MCP health:
- **12 MCPs configured**: sequential-thinking, memory, context7, filesystem, fetch, git, athena-context, trigger-guardian, nx-mind, athena, github, unified-memory
- **Run `bash bin/mcp-doctor.sh`** to verify all MCPs are healthy
- **If an MCP is down**: Use fallback tools from the matrix above
- **Deprecated**: `memory` (npx) MCP — use `unified-memory` instead

---

- ALWAYS include `load_skills=[]` in every `task()` call
- Pass `[]` if no skills needed
- Include relevant skills when domain matches (e.g., `load_skills=["git-master"]` for git operations)
- NEVER load skills that don't match the task domain
- User-installed skills OVERRIDE built-in defaults — prefer YOUR skills when domain matches

---

| Server | Status | Use |
|--------|--------|-----|
| athena | ✅ | Context/memory/retrieval |
| github | ✅ | Repo access, issues, PRs |
| context7 | ✅ | Live documentation (remote SSE, no install) |
| athena-context | ✅ | Active context, product/user context |
| trigger-guardian | ✅ | Command routing, trigger phrases |
| nx-mind | ✅ | Project state, session history |
| unified-memory | ✅ | Unified search, semantic memory |
| git | ✅ | Local version control awareness |
| sequential-thinking | ✅ | Chain-of-thought for complex reasoning |
| memory | ✅ | Cross-session knowledge graph |

---

## Parallel Limits (Configured)

| Limit | Value | Source |
|-------|-------|--------|
| defaultConcurrency | 64 | `config/opencode.json` background_task |
| providerConcurrency | 80 | `config/opencode.json` background_task |
| opencode/qwen3.6-plus-free | 32 | `config/opencode.json` background_task |
| minimax-m2.5 | 64 | `config/opencode.json` background_task |
| opencode/kimi-k2.5-free | 32 | `config/opencode.json` background_task |

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
- multimodal-looker **MUST use opencode/minimax-m2.5-free** model (only model that reads images)
- No other agent can process visual/media content

### Implementation Tasks
**CRITICAL**: Sisyphus MUST NEVER write code directly. This is non-negotiable.
- If task requires **writing code** → delegate to **Hephaestus** via `task(subagent_type="hephaestus", ...)`
- If task requires **creating files** → delegate to **Hephaestus**
- If task requires **editing files** → delegate to **Hephaestus**
- Sisyphus ONLY: orchestrates, plans, delegates, verifies
- Never mix orchestrator and implementor roles
- Violation = immediate task failure

### Hephaestus vs Sisyphus-Junior — Decision Tree

**Hephaestus** (default code writer) — use for:
- New features, new files, multi-file changes
- Bug fixes that require logic changes
- Refactoring, restructuring, renaming across files
- Any change touching 2+ lines or 2+ files
- Test writing, config changes with logic impact

**Sisyphus-Junior** (trivial changes only) — use for:
- Single-line typo fixes (fix a variable name)
- Update a version number, constant, or config value
- Add/remove a single import statement
- Fix a missing semicolon, comma, or bracket
- Changes that are obvious and require zero reasoning

**Rule of thumb**: If you need to think about HOW to change it → Hephaestus. If you just need to change X to Y → Sisyphus-Junior.

**When in doubt → Hephaestus.**

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

| Task Type | Minimum Agent/Category | Minimum Model |
|-----------|---------------------|---------------|
| Implementation | subagent_type: hephaestus | minimax-m2.5-free | Code writing (EXCLUSIVE) |
| UI/Visual | category: visual-engineering | kimi-k2.5-free (high) |
| Complex Logic | category: ultrabrain | qwen3.6-plus-free (high) |
| Research | subagent_type: explore | minimax-m2.5-free |
| Review | subagent_type: oracle | qwen3.6-plus-free (high) |


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
- ❌ Same agent writing AND reviewing code
- ❌ Using category for implementation — use `subagent_type="hephaestus"` ONLY
- ❌ Using free tier models for implementation without checking quality
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
| Complex Logic | category: ultrabrain | opencode/mimo-v2-pro-free (high) | Deep reasoning |
| Simple Fixes | category: unspecified-low | minimax-m2.5-free | Light task, local model |
| Research | agent: explore | minimax-m2.5-free | Codebase search |
| External Docs | agent: librarian | minimax-m2.5-free | Web search |
| Architecture | agent: oracle | opencode/mimo-v2-pro-free (high) | Strategic advice |
| Implementation | subagent_type: hephaestus | minimax-m2.5-free | Code writing (EXCLUSIVE) |
| Tests | category: unspecified-low | minimax-m2.5-free | Test generation |
| Review | agent: oracle | opencode/mimo-v2-pro-free (high) | Adversarial review |
| Red-Team | agent: momus | opencode/mimo-v2-pro-free (high) | Critical analysis |
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

- **AGENTS.md**: v3.4
- **Last Updated**: 2026-04-05
- **Research**: 70+ agents (52 audit + 18 verify), 3 codebases, 10 deprecated AGENTS.md files
- **Sources**: MIND, CATALYST, DEPRECATED, 2025-2026 LLM orchestration research
- **Audit**: 100+ issues found across 3 passes, all critical fixed, all MCP servers Python-native
- **Resilience**: Anti-Loop Protocol (6 rules), Fallback Chains, DLQ, chatMaxRetries

## 🚨 AGENT CALL PRE-FLIGHT CHECKLIST (MANDATORY)

**BEFORE every `task()` call, verify ALL 6 items:**

### Checklist (MUST pass ALL before calling task())

- [ ] **1. `subagent_type` OR `category` provided** — NOT both, NOT neither
- [ ] **2. `load_skills=[]` provided** — ALWAYS required, pass `[]` if no skills
- [ ] **3. `run_in_background=true/false` provided** — ALWAYS required
- [ ] **4. `prompt` is non-empty** — MUST have substantive content (50+ chars)
- [ ] **5. `description` is concise** — 3-5 words max
- [ ] **6. Valid subagent_type** — explore, librarian, oracle, metis, momus, plan, hephaestus, sisyphus, prometheus, atlas, sisyphus-junior, multimodal-looker

### Valid subagent_type values (COPY-PASTE READY)

```
explore | librarian | oracle | metis | momus | plan | hephaestus | sisyphus | prometheus | atlas | sisyphus-junior | multimodal-looker
```

### Valid category values (COPY-PASTE READY)

```
visual-engineering | ultrabrain | deep | artistry | quick | unspecified-low | unspecified-high | routing | writing
```

### Template — Copy-Paste Ready (NEVER type from memory)

**Every delegation prompt MUST include these 6 sections:**

```
1. TASK: Atomic, specific goal (one action per delegation)
2. EXPECTED OUTCOME: Concrete deliverables with success criteria
3. REQUIRED TOOLS: Explicit tool whitelist (prevents tool sprawl)
4. MUST DO: Exhaustive requirements — leave NOTHING implicit
5. MUST NOT DO: Forbidden actions — anticipate and block rogue behavior
6. CONTEXT: File paths, existing patterns, constraints
```

```typescript
// Background research (parallel)
task(
  subagent_type="explore",      // OR librarian, oracle, metis, momus, plan
  load_skills=[],               // ALWAYS required
  run_in_background=true,        // ALWAYS required for research
  description="Short 3-5 words",
  prompt="I'm implementing JWT auth and need to match existing conventions.\n\n" +
    "TASK: Find all authentication-related code in src/.\n" +
    "EXPECTED OUTCOME: List of auth middleware, login handlers, token generation patterns.\n" +
    "REQUIRED TOOLS: grep, glob, read, ast-grep.\n" +
    "MUST DO: Search src/ directory, check middleware/, check routes/, check utils/.\n" +
    "MUST NOT DO: Do NOT search tests/, node_modules/, or .git/.\n" +
    "CONTEXT: Project root is /home/nxyme/N-Xyme_CODE/N-Xyme_MIND. Focus on src/api/."
)

// Foreground implementation (sequential)
task(
  subagent_type="hephaestus",   // OR plan, atlas, sisyphus
  load_skills=[],               // ALWAYS required
  run_in_background=false,       // ALWAYS required for implementation
  description="Short 3-5 words",
  prompt="I need JWT auth middleware that matches existing patterns.\n\n" +
    "TASK: Create src/middleware/auth.ts with JWT validation.\n" +
    "EXPECTED OUTCOME: auth.ts with verifyToken(), extractBearer(), and error handling.\n" +
    "REQUIRED TOOLS: read, edit, bash (for typecheck only).\n" +
    "MUST DO: Read src/middleware/logger.ts first for pattern reference. " +
    "Follow existing error format {error, message, status}. Run typecheck before done.\n" +
    "MUST NOT DO: Do NOT modify existing middleware. Do NOT add dependencies. Do NOT commit.\n" +
    "CONTEXT: Working directory: /home/nxyme/N-Xyme_CODE/N-Xyme_MIND. " +
    "Existing middleware: src/middleware/logger.ts, src/middleware/error.ts."
)

// Category-based delegation (NEVER for implementation — use subagent_type="hephaestus" instead)
task(
  category="quick",             // OR ultrabrain, visual-engineering, writing
  load_skills=[],               // ALWAYS required
  run_in_background=false,      // ALWAYS required
  description="Short 3-5 words",
  prompt="Fix the typo in variable name on line 42 of src/config.ts. " +
    "Change 'recieve' to 'receive'. Nothing else."
)
```

**Prompt quality rules:**
- Minimum 50 characters — vague prompts produce vague results
- Reference specific files to read before acting
- State what NOT to do — agents overreach without boundaries
- Include success criteria — how does the agent know it's done?
- Never use `as any`, `@ts-ignore`, or suppress errors in delegated work

### Context Passing Protocol

When delegating, pass context in 3 tiers:

| Tier | Content | When |
|:-----|:--------|:-----|
| **Tier 1 (Always)** | Task description, file paths, constraints | Every delegation |
| **Tier 2 (Conditional)** | Related code snippets, error messages, existing patterns | Implementation agents |
| **Tier 3 (On-demand)** | Full file contents, conversation history | Only when explicitly requested |

**Never dump entire codebase** — let agents search dynamically via explore agent.
**Never include irrelevant context** — it wastes tokens and confuses the agent.
**Always reference files to read** — `Read src/middleware/logger.ts first for pattern reference.`

```typescript
// Background research (parallel)
task(
  subagent_type="explore",      // OR librarian, oracle, metis, momus, plan
  load_skills=[],               // ALWAYS required
  run_in_background=true,        // ALWAYS required for research
  description="Short 3-5 words",
  prompt="Detailed 5+ line prompt..."
)

// Foreground implementation (sequential)
task(
  subagent_type="hephaestus",   // OR plan, atlas, sisyphus
  load_skills=[],               // ALWAYS required
  run_in_background=false,       // ALWAYS required for implementation
  description="Short 3-5 words",
  prompt="Detailed 5+ line prompt..."
)

// Category-based delegation (NEVER for implementation — use subagent_type="hephaestus" instead)
task(
  category="quick",             // OR ultrabrain, visual-engineering, writing
  load_skills=[],               // ALWAYS required
  run_in_background=false,      // ALWAYS required
  description="Short 3-5 words",
  prompt="Detailed 5+ line prompt..."
)
task(
  category="quick",             // OR ultrabrain, visual-engineering, writing
  load_skills=[],               // ALWAYS required
  run_in_background=false,      // ALWAYS required
  description="Short 3-5 words",
  prompt="Detailed 5+ line prompt..."
)
task(
  category="quick",             // OR ultrabrain, visual-engineering, writing
  load_skills=[],               // ALWAYS required
  run_in_background=false,      // ALWAYS required
  description="Short 3-5 words",
  prompt="Detailed 5+ line prompt..."
```

### Common Errors (NEVER make these mistakes)

| Error | Wrong | Correct |
|-------|-------|---------|
| Missing load_skills | `task(subagent_type="explore", prompt="...")` | `task(subagent_type="explore", load_skills=[], prompt="...")` |
| Missing run_in_background | `task(subagent_type="explore", load_skills=[])` | `task(subagent_type="explore", load_skills=[], run_in_background=true)` |
| Invalid subagent_type | `subagent_type="prometheus"` | `subagent_type="plan"` |
| Both category + subagent_type | `category="deep", subagent_type="hephaestus"` | Use ONE, not both |
| Using category for code | `category="deep"` for implementation | `subagent_type="hephaestus"` ONLY |
| Empty prompt | `prompt=""` | `prompt="Detailed 5+ line prompt..."` |

### Error Recovery (When task() fails)

1. **Read the error message** — it tells you exactly what's wrong
2. **Check the 6-item checklist** — find which item failed
3. **Fix the specific parameter** — don't rewrite the whole call
4. **Retry once** — if it fails again, escalate to Oracle

**NEVER**: Guess parameters, retry without fixing, ignore error messages

---

## Task Tool Rules (CRITICAL)
When calling task() to delegate to subagents, you MUST include ALL required parameters:
- `load_skills` is ALWAYS REQUIRED. Pass `[]` if no skills needed.
- `run_in_background` is ALWAYS REQUIRED. `false` for delegation, `true` for parallel.
- NEVER omit these parameters. They will cause a hard crash.
- When using `subagent_type`, valid values are: explore, librarian, oracle, metis, momus, plan, hephaestus, sisyphus, prometheus, atlas, sisyphus-junior, multimodal-looker
- When using `category`, valid values are: visual-engineering, ultrabrain, deep, artistry, quick, unspecified-low, unspecified-high, routing, writing

## Safety Rules
- Always show what will change before making changes
- Never run rm -rf without confirmation
- Never overwrite .env files
- Report errors honestly — do not pretend code works when it doesn't

## BMAD Integration
BMAD v6.2.0 workflows are available in `_bmad/`. Key workflows:
- **bmad-resilience**: Error handling patterns
- **bmad-memory**: Memory/graph integration
- **bmad-catalyst-chain**: Planning orchestration
- **bmad-validate-prd**: PRD validation (13 steps)

To use BMAD workflows, reference them in task prompts:
"Use the bmad-resilience workflow from _bmad/catalyst/workflows/"

Available phases:
5. Test Architecture (test design, CI)

---

## 🧠 INTELLIGENT DELEGATION SYSTEM

### Overview

This workspace has an **intelligent delegation system** that automatically routes tasks to the optimal agent based on:
1. **Trigger patterns** (24 patterns with priority-based matching)
2. **Memory-augmented routing** (queries past similar tasks)
3. **Predictive routing** (27 patterns built from historical data)
4. **Learning-based optimization** (real-time weight updates)
5. **Keyword fallback** (L1-L5 complexity scoring)

### How It Works

```
User Task → Triggers → Memory → Local Model → Learning → Keyword
     ↓         ↓          ↓           ↓           ↓          ↓
  Match?   Similar?   L3+?      Weights?   Fallback
     ↓         ↓          ↓           ↓           ↓          ↓
  Route     Route     Analyze    Optimize    Route
```

### MCP Tools Available (16 total)

**Memory Tools:**
- `search_memories(query, limit, sources)` — Search across all memory sources
- `create_memory(content, kind, scope, tags, metadata)` — Create a new memory entry
- `update_memory(memory_id, content, tags, metadata)` — Update an existing memory
- `delete_memory(memory_id, hard_delete)` — Delete or archive a memory
- `get_memory_stats()` — Get statistics about memory sources
- `recall_session(session_id, lines)` — Recall session context
- `find_context(task, context_type)` — Find relevant context for a task
- `semantic_search(query, top_k)` — Semantic search using embeddings
- `tempr_search(query, top_k, tier, strategies)` — TEMPR multi-strategy retrieval
- `get_learning_stats()` — Get learning statistics
- `get_skill_status(skill_name)` — Get skill lifecycle status
- `record_skill_outcome(skill_name, success, latency_ms, feedback)` — Record skill outcome
- `get_learning_patterns(query, limit)` — Get learned patterns
- `evolve_prompt(original_prompt, task_context, iterations)` — Evolve a prompt

**Intelligence Tools:**
- `route_task(task_description)` — Get optimal routing decision
- `record_delegation_outcome(task_id, task_description, level, agent, success, latency_ms, tokens_used)` — Log outcome

### Automatic Routing

**When you call delegation tools** (`task`, `hephaestus`, `explore`, etc.), the system automatically:
1. Intercepts the tool call
2. Routes it via the 5-layer routing system
3. Logs the outcome to SQLite
4. Updates agent weights in real-time
5. Returns the routing decision

**You don't need to manually call `route_task`** — it happens automatically.

### Routing Performance

| Metric | Value |
|:-------|:------|
| Predictive Routing | 388,902 predictions/sec |
| Trigger Matching | 108,641 matches/sec |
| MCP Tool Calls | 3,872 calls/sec |
| Middleware Interception | 3,448 interceptions/sec |
| SQLite Writes | 110 writes/sec |
| SQLite Reads | 13,643 reads/sec |

### Agent Performance Tracking

The system tracks:
- Success rate per agent per task type
- Average latency per agent
- Task counts per agent
- Level-specific performance

View current stats:
```bash
python3 bin/routing-dashboard.py
```

### Security Sandbox

All agent executions are sandboxed:
- File access restricted to project directory
- Dangerous commands blocked (rm -rf, sudo, etc.)
- Sensitive files protected (.env, .git, etc.)
- File size limits enforced

### Multi-Agent Coordination

For complex tasks (L3+), the system can coordinate multiple agents:
- **L3**: Research + Implementation (explore → hephaestus)
- **L4**: Planning + Implementation + Review (prometheus → hephaestus → oracle)
- **L5**: Full coordination (metis → prometheus → hephaestus → oracle → momus)

### Persistence

All data is stored in SQLite (`.sisyphus/routing.db`):
- 346+ outcomes logged
- 12 agents tracked
- 24 triggers configured
- 27 predictive patterns

Data persists across sessions and is automatically migrated from JSON files.
2. Planning (PRD, UX design)
3. Solutioning (architecture, epics)
4. Implementation (sprint, dev, review)
5. Test Architecture (test design, CI)

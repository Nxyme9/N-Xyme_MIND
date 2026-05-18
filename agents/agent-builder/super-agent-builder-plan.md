# Super Agent Builder — Implementation Plan

**Goal:** Transform the current Agent Builder into a bleeding-edge super agent builder that uses deep research, multi-agent review, and self-improvement to produce consistently high-quality agents.

**Current State:** The Agent Builder follows a basic 5-phase pipeline (Classify → Shell → Generate → Validate → Register). It works but lacks:
- Pre-build research on domain best practices
- Adversarial review of generated prompts
- Self-improvement from past builds
- Template library management
- Multi-agent collaboration during the build process

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    SUPER AGENT BUILDER                        │
│                                                               │
│  ┌─────────┐    ┌─────────┐    ┌──────────┐    ┌──────────┐  │
│  │ PHASE 1  │───▶│ PHASE 2  │───▶│ PHASE 3   │───▶│ PHASE 4   │  │
│  │ RESEARCH │    │ CLASSIFY │    │ SHELL     │    │ GENERATE  │  │
│  │          │    │          │    │ (template)│    │ (LLM)     │  │
│  └────┬─────┘    └──────────┘    └──────────┘    └────┬─────┘  │
│       │                                                │         │
│  Librarian│                                            │         │
│  deepdive │                                     ┌──────▼──────┐  │
│  + memory │                                     │ PHASE 5      │  │
│  search   │                                     │ ADVERSARIAL  │  │
│           │                                     │ REVIEW       │  │
│           │                                     │ Metis+Momus  │  │
│           │                                     └──────┬──────┘  │
│           │                                            │         │
│           │                                     ┌──────▼──────┘  │
│           │                                     │ PHASE 6        │
│           │                                     │ VALIDATE       │
│           │                                     │ 10-check gate  │
│           │                                     └──────┬─────────┘
│           │                                            │         │
│           │                                     ┌──────▼─────────┐
│           │                                     │ PHASE 7        │
│           │                                     │ REGISTER +     │
│           │                                     │ MEMORY LEARN   │
│           │                                     │ data/ + holo   │
│           └─────────────────────────────────────┘                │
│                                                                  │
│  LEVERAGES EXISTING INFRASTRUCTURE (no new systems):              │
│  - Holographic memory (TF-IDF) for experience storage            │
│  - data/ folder for persistent build artifacts                   │
│  - Ralph Loop for self-improvement iterations                    │
│  - BMAD memory skills (consolidate, search, recall)              │
└──────────────────────────────────────────────────────────────┘
```

---

## The 7-Phase Protocol

### PHASE 1: RESEARCH (NEW — Librarian DeepDive)

**Problem:** The current builder classifies immediately without understanding the domain. A "chemistry agent" needs different patterns than a "code review agent."

**Solution:** Before classification, launch parallel research threads:

```
Librarian DeepDive (3 parallel threads):
  Thread 1 — Domain Research: What does this agent's domain require?
             What are industry best practices for this type of agent?
  Thread 2 — Technical Research: What tools, frameworks, patterns exist?
             What do other agent frameworks do for this archetype?
  Thread 3 — Existing Pattern Match: Which of our 17 existing agents
             is most similar? What can we learn from its design?

Trigger: ALWAYS for new agent types. SKIP for variants of existing agents.
Model: opencode/deepseek-v4-flash-free (via Librarian subagent)
```

**Research output feeds into:**
- Phase 2 classification (better archetype matching)
- Phase 3 template selection (informed template choice)
- Phase 4 meta-prompt (domain-specific examples in few-shot)

### PHASE 2: CLASSIFY (Enhanced)

**Current:** Simple archetype table lookup.
**Enhanced:** Classification informed by Phase 1 research.

```
Input: Task description + research findings from Phase 1
Output: Structured JSON spec with:
  - archetype (Builder | Tool-User | Reader | Conversational | Specialist)
  - name (follows "Name - Role" convention)
  - tools (validated against MCP server tool definitions)
  - model (selected from available models based on needs)
  - mode (primary | subagent | all)
  - permission (explicit allow/deny for each tool)
  - skills_needed (which BMAD skills to bundle)
  - similar_agents (from research — which existing agents are comparable)

Model selection decision tree:
  - Needs deep reasoning/math → opencode/ring-2.6-1t-free
  - Needs code generation → opencode/qwen3.6-plus-free or opencode/minimax-m2.5-free
  - Needs research/web → opencode/deepseek-v4-flash-free
  - Needs conversation/therapy → opencode/minimax-m2.5-free
  - Default → opencode/deepseek-v4-flash-free
```

### PHASE 3: SHELL (Template — Deterministic)

**Current:** Basic directory structure.
**Enhanced:** Template library with archetype-specific scaffolds.

```
Template Library Structure:
  agents/agent-builder/templates/
  ├── builder/          # Full-tool agents (Hephaestus, Scalpel)
  │   ├── agent.js.template
  │   └── tools.json.template
  ├── tool-user/        # Domain-specific tool subset (Explore, Librarian)
  │   ├── agent.js.template
  │   └── tools.json.template
  ├── reader/           # Read-only analysis (Momus, Oracle)
  │   ├── agent.js.template
  │   └── tools.json.template
  ├── conversational/   # Chat-focused (Kairos, Metis)
  │   ├── agent.js.template
  │   └── tools.json.template
  └── specialist/       # Domain expert (Mr. White, Vision)
      ├── agent.js.template
      └── tools.json.template

Each template contains:
  - Deterministic structure (80% of the agent)
  - Placeholder markers for LLM-generated content (20%)
  - Archetype-specific anti-hallucination rules
  - Archetype-specific quality gate patterns

Files created:
  agents/<name>/
  ├── agent.js              ← Filled in Phase 4
  ├── tools/tools.json      ← From template + spec.tools
  ├── skills/<name>/        ← If custom skills needed
  │   ├── SKILL.md
  │   └── workflow.md
  └── data/
      └── system-context.md ← Always included
```

### PHASE 4: GENERATE (LLM Content — Creative, Enhanced)

**Current:** Single-pass meta-prompt to a reasoning model.
**Enhanced:** Multi-shot meta-prompt with research-informed examples.

```
Meta-Prompt Construction:
  1. Read spec from Phase 2
  2. Load template from Phase 3
  3. Select few-shot examples:
     a. Primary: Most similar existing agent (from research)
     b. Secondary: Same archetype, different domain
     c. Tertiary: Best-in-class example of a section (e.g., best quality gate)
  4. Inject research findings as domain context
  5. Present to strong reasoning model (qwen3.6-plus-free or minimax-m2.5-free)

Meta-Prompt Template:
  "You are building an agent with this spec: {spec}
   Research findings: {research_summary}
   Here are 2-3 similar agents as examples: {few_shot_examples}
   
   Generate ONLY the creative content sections:
   - IDENTITY paragraph (distinctive, memorable, domain-specific)
   - CORE PROTOCOL (phased methodology for this agent's domain)
   - RULES (anti-hallucination + domain-specific constraints)
   - TOOLS decision tree (when to use which tool)
   - QUALITY GATE (what verification looks like)
   
   Hard rules:
   - Never invent capabilities without matching tools
   - Be specific, not generic
   - Anti-hallucination rules are mandatory
   - Keep under 100 lines
   - Match the existing agent.js format (export default { ... })"

Output: Complete agent.js written to agents/<name>/agent.js
```

### PHASE 5: ADVERSARIAL REVIEW (NEW — Metis + Momus)

**Problem:** Generated prompts can have subtle issues: role bleed, vague instructions, missing edge cases.

**Solution:** Two-stage review before registration:

```
Stage 1 — Metis Consultation (Pre-Implementation Review):
  Input: Generated agent.js + spec
  Metis checks:
  - Hidden assumptions in the prompt
  - AI failure points (where will this agent hallucinate?)
  - Integration risks (will this conflict with existing agents?)
  - Missing edge cases in the protocol
  Output: List of concerns with severity ratings

Stage 2 — Momus Adversarial Review (Post-Generation Review):
  Input: Generated agent.js + Metis findings
  Momus checks (5 lenses):
  - Security: Can this agent be tricked into doing something dangerous?
  - Edge cases: What inputs break this agent's protocol?
  - Maintainability: Is the prompt clear enough for future iteration?
  - Performance: Will this agent waste tokens on unnecessary steps?
  - Correctness: Are tool descriptions accurate? Are permissions correct?
  Output: Findings report with critical/major/minor severity

Review Decision:
  - If CRITICAL findings → go back to Phase 4, fix, re-review
  - If MAJOR findings → fix, quick re-review on changed sections only
  - If MINOR/NIT findings → fix, proceed to Phase 6
  - If NO findings → proceed to Phase 6
```

### PHASE 6: VALIDATE (Enhanced 9-Check Gate)

**Current:** 8 checklist items.
**Enhanced:** 9 checks with automated verification where possible.

```
Validation Checklist:
  [ ] 1. tools.json: every tool exists in at least one MCP server
        → Automated: cross-reference with megatools list_agents
  [ ] 2. tools.json: no tool in both allowed and blocked
        → Automated: set intersection check
  [ ] 3. agent.js: has IDENTITY section
        → Automated: grep for "IDENTITY" or "You are"
  [ ] 4. agent.js: has RULES section with anti-hallucination constraints
        → Automated: grep for "hallucinat" or "don't invent" or "never invent"
  [ ] 5. agent.js: has QUALITY GATE section
        → Automated: grep for "QUALITY GATE" or "Quality Gate"
  [ ] 6. agent.js: no referenced capability without a matching tool
        → Manual: read agent.js, check each claimed capability against tools.json
  [ ] 7. Permission: every tool in allowed has permission:allow
        → Automated: cross-reference tools.json allowed vs opencode.json permission
  [ ] 8. Name: unique (no collision with existing agents)
        → Automated: check against opencode.json agent keys
  [ ] 9. Name: follows convention "Name - Role"
        → Automated: regex check for " - " in name
  [ ] 10. Delegation: no file writing delegated to Explore (or write permission granted for .md only)
        → Manual: verify delegation targets in the build process

If ANY check fails → fix before proceeding to Phase 7.
```

### PHASE 7: REGISTER + LEVERAGE MEMORY (Enhanced)

**Current:** Write files, register, sync, memory.
**Enhanced:** Wire into existing holographic memory + data folder infrastructure. No new systems needed.

```
Step 1 — Write Files:
  All files to agents/<name>/

Step 2 — Register:
  add_agent tool (handles both opencode.json and config/nx_agents.json)

Step 3 — Skill Registration (if custom skills created):
  Add keyword trigger to bmad-mcp/src/server.py

Step 4 — Config Sync:
  sync_nx_config agent

Step 5 — PERSIST TO DATA FOLDER (Leverage Existing Pattern):
  Write to agents/agent-builder/data/:
  - build-log.md — append entry for this build
  - experience.md — what worked, what failed, patterns discovered
  - prompt-patterns.md — successful prompt structures to reuse
  - template-evolution.md — how templates changed and why
  
  This is the same data/ pattern every other agent uses. No new infrastructure.

Step 6 — CONSOLIDATE TO HOLOGRAPHIC MEMORY (Leverage Existing MCP):
  Use bmad-memory-consolidate to save:
  - Agent build summary (name, archetype, tools, model, quality score)
  - Research findings that proved useful
  - Adversarial review findings (what was caught, what was missed)
  - Design decisions and rationale
  - Lessons learned for future builds
  
  This writes to the existing TF-IDF vector store (64-dim, 4448 embeddings).
  Future builds automatically retrieve this via memory_search/memory_recall.

Step 7 — SELF-IMPROVEMENT VIA RALPH LOOP (Leverage Existing Plugin):
  After each build, use Ralph Loop to iteratively improve:
  - Read past builds from memory (memory_search("agent build lessons"))
  - Read experience.md from data/ folder
  - Identify patterns: what template sections work best? what prompts fail?
  - Update agent-builder's own agent.js with improvements
  - Iterate until quality plateaus
  
  Self-improvement triggers:
  - After every 3rd agent build (batch learning)
  - After any CRITICAL adversarial finding (immediate learning)
  - After user feedback indicating agent quality issues

Step 8 — Report to User:
  Summary of:
  - What was built
  - Key design decisions
  - Any concerns from adversarial review
  - How to use the new agent
  - What was saved to memory/data for future builds
```

### MEMORY & DATA INTEGRATION MAP (Throughout All Phases)

The Super Agent Builder doesn't build new memory systems — it uses what exists:

| Phase | Memory Tool Used | Purpose |
|-------|-----------------|---------|
| 1. Research | memory_search("agent best practices") | Find past research findings before launching new web search |
| 1. Research | memory_recall("similar agent builds") | Find patterns from previous similar agent builds |
| 2. Classify | data/experience.md | Read what archetypes worked best for which tasks |
| 3. Shell | data/prompt-patterns.md | Load successful template patterns |
| 4. Generate | memory_search("anti-hallucination patterns") | Find proven anti-hallucination rules |
| 5. Review | memory_search("common agent flaws") | What mistakes do generated agents usually have? |
| 6. Validate | data/template-evolution.md | What validation checks caught real issues before? |
| 7. Register | bmad-memory-consolidate | Save this build's lessons to holographic memory |
| 7. Register | data/build-log.md | Append build record to persistent log |
| 7. Register | data/experience.md | Update experience with new lessons |

### NO NEW INFRASTRUCTURE NEEDED

| What I Originally Planned | What Already Exists | How to Use It |
|--------------------------|---------------------|---------------|
| "Experience Library" | Holographic memory (TF-IDF vector store) | memory_consolidate + memory_search |
| "Build Documentation System" | data/ folder pattern | Write to agents/agent-builder/data/ |
| "Self-Improvement Loop" | Ralph Loop plugin | Use ralph_loop for iterative prompt improvement |
| "Pattern Database" | data/prompt-patterns.md | Append successful patterns after each build |
| "Session Management" | nx MCP server | Use existing session tools for build sessions |
| "Knowledge Sharing Between Agents" | Shared holographic memory | Any agent can memory_search agent builder's lessons |

---

## Multi-Agent Collaboration Map

| Phase | Primary Agent | Supporting Agents | Purpose |
|-------|--------------|-------------------|---------|
| 1. Research | Agent Builder | Librarian (DeepDive) | Domain + technical + pattern research |
| 2. Classify | Agent Builder | — | Informed archetype selection |
| 3. Shell | Agent Builder | — | Template-based structure |
| 4. Generate | Agent Builder | — (via strong model) | LLM prompt generation |
| 5. Review | Agent Builder | Metis + Momus | Two-stage adversarial review |
| 6. Validate | Agent Builder | — | Automated + manual checks |
| 7. Register | Agent Builder | — | Registration + self-improvement |

### Delegation Rules

**DO NOT delegate file writing to Explore.** Explore is a search/codebase analysis agent — it is NOT a writer. The Agent Builder writes all agent files itself (Phase 3 Shell + Phase 4 Generate).

**If Explore must be involved in the build process** (e.g., finding existing patterns, searching for similar agents), it may ONLY be used for read/search operations. If you absolutely must have Explore write something (e.g., a research findings `.md` file), you MUST grant it at minimum:
```json
"permission": { "write": "allow" }
```
And restrict its task to writing ONLY `.md` files — never `.js`, `.json`, or code files. Explore's agent.js and tools.json are not configured for code writing, and delegating code writes to it will produce broken output.

**Correct delegation pattern:**
- Agent Builder writes: `agent.js`, `tools/tools.json`, `skills/*/SKILL.md`, `data/system-context.md`
- Explore may read/search: find existing agent patterns, search codebase for conventions
- Librarian may write: research findings `.md` files (if needed, with write permission granted)
- Hephaestus may write: code files (if the agent build requires code generation beyond prompts)

---

## File Changes Required

### New Files
```
agents/agent-builder/
├── templates/
│   ├── builder/agent.js.template
│   ├── builder/tools.json.template
│   ├── tool-user/agent.js.template
│   ├── tool-user/tools.json.template
│   ├── reader/agent.js.template
│   ├── reader/tools.json.template
│   ├── conversational/agent.js.template
│   ├── conversational/tools.json.template
│   ├── specialist/agent.js.template
│   └── specialist/tools.json.template
└── data/
    ├── system-context.md    ← Standard agent context (if not exists)
    ├── build-log.md         ← Append-only build history
    ├── experience.md        ← Lessons learned from each build
    ├── prompt-patterns.md   ← Successful prompt structures to reuse
    └── template-evolution.md ← How templates changed and why
```

### Modified Files
```
agents/agent-builder/agent.js          ← Complete rewrite with 7-phase protocol + memory integration
agents/agent-builder/skills/agent-builder/workflow.md  ← Update to match
```

### NO New Infrastructure
- No new MCP servers
- No new memory systems
- No new plugins
- Uses existing: holographic memory, data/ pattern, Ralph Loop, BMAD memory skills

---

## Implementation Order

| Step | Action | Complexity | Dependencies |
|------|--------|------------|--------------|
| 1 | Create template library (5 archetypes × 2 files) | Medium | None |
| 2 | Create build-log.md structure | Low | None |
| 3 | Rewrite agent.js with 7-phase protocol | High | Steps 1-2 |
| 4 | Update workflow.md to match | Low | Step 3 |
| 5 | Test with existing agent (rebuild one as validation) | Medium | Steps 1-4 |
| 6 | Build a new agent end-to-end as proof | Medium | Step 5 |

---

## Success Criteria

1. **Research catches something:** The Librarian DeepDive finds at least one relevant pattern or best practice that improves the agent design
2. **Adversarial review finds something:** Metis or Momus identifies at least one issue that would have shipped without review
3. **Memory compounds:** After 3 builds, memory_search returns useful lessons from previous builds that improve the next build
4. **Data folder grows:** agents/agent-builder/data/ contains build-log.md, experience.md, prompt-patterns.md, template-evolution.md with real content
5. **Self-improvement works:** After 3 builds, the Agent Builder's own prompt has measurably improved (fewer issues found in review)
6. **Zero hallucinated capabilities:** Every registered agent has only the capabilities its tools support
7. **Faster iteration:** Building a new agent takes less time with the super builder than without (due to templates + research + review automation)
8. **No new infrastructure:** Everything uses existing memory, data folders, Ralph Loop, and BMAD skills — zero new MCP servers or plugins

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Librarian research is slow | High | Make research optional for simple variants; use cached findings from memory |
| Adversarial review is too conservative | Medium | Momus has "if nothing is wrong, say so" rule; severity filtering |
| Self-improvement degrades prompt | High | Version control agent.js; rollback if quality drops; batch learning only |
| Memory pollution (bad lessons saved) | Medium | Only save lessons that passed adversarial review; user can clear memory |
| Explore delegated to write code files | High | HARD RULE: Agent Builder writes all agent files; Explore only reads/searches |

---

## Model Budget Estimate

| Phase | Model | Estimated Tokens | Cost Tier |
|-------|-------|-----------------|-----------|
| 1. Research | deepseek-v4-flash-free | ~8K input, ~4K output | Free |
| 1. Memory search | deepseek-v4-flash-free | ~2K input, ~1K output | Free |
| 2. Classify | deepseek-v4-flash-free | ~4K input, ~1K output | Free |
| 3. Shell | N/A (deterministic) | 0 | Free |
| 4. Generate | qwen3.6-plus-free | ~12K input, ~3K output | Free |
| 5. Review (Metis) | minimax-m2.5-free | ~6K input, ~2K output | Free |
| 5. Review (Momus) | deepseek-v4-flash-free | ~6K input, ~2K output | Free |
| 6. Validate | N/A (automated) | 0 | Free |
| 7. Register | N/A (tool calls) | ~1K | Free |
| 7. Memory consolidate | deepseek-v4-flash-free | ~3K input, ~1K output | Free |
| **Total** | | **~42K input, ~14K output** | **Free tier** |

All models used are free-tier. No paid model required for the full pipeline.
Memory operations add ~3K tokens but compound value across all future builds.

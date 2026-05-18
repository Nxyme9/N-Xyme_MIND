# Meta Agent Builder — Masterplan

**Version:** 2.0 (Bleeding-Edge)
**Date:** 2026-05-17
**Status:** Implementation-Ready

---

## EXECUTIVE SUMMARY

The Meta Agent Builder transforms the current 5-phase Agent Builder into a research-driven, multi-agent-reviewed, self-improving system that produces consistently high-quality agents. It leverages **existing infrastructure only** — holographic memory, data/ folders, Ralph Loop, BMAD skills — with zero new MCP servers or plugins.

**Key Research Backing:**
- MAST Study (NeurIPS 2025): 24% of multi-agent failures from missing verification → Phase 5 adversarial review
- Silo-Bench (2026): Synthesis bottleneck is #1 multi-agent failure → Phase 7 memory consolidation
- HyperAgents (Meta, arXiv 2026): Self-referential agents improve 17%→53% → Phase 7 Ralph Loop self-improvement
- DeepVerifier (arXiv 2026): Independent verification yields 8-11% accuracy gains → Phase 5+6 review gates
- Arize Prompt Learning (2025): Prompt optimization yields 5-11% gains → Phase 4 meta-prompt refinement

---

## ARCHITECTURE OVERVIEW

```
┌──────────────────────────────────────────────────────────────────────┐
│                        META AGENT BUILDER                             │
│                                                                       │
│  PHASE 1          PHASE 2          PHASE 3          PHASE 4          │
│  ┌─────────┐      ┌─────────┐      ┌──────────┐     ┌──────────┐    │
│  │ RESEARCH│─────▶│ CLASSIFY│─────▶│ SHELL    │────▶│ GENERATE │    │
│  │         │      │         │      │(template)│     │  (LLM)   │    │
│  └────┬────┘      └─────────┘      └──────────┘     └────┬─────┘    │
│       │                                                   │          │
│  Librarian                                           qwen3.6-plus    │
│  DeepDive                                              minimax-m2.5  │
│  + memory_search                                                    │
│                                                                       │
│  PHASE 5          PHASE 6          PHASE 7                          │
│  ┌──────────────┐ ┌──────────┐     ┌──────────────────────┐         │
│  │ ADVERSARIAL  │ │ VALIDATE │     │ REGISTER + LEARN     │         │
│  │ REVIEW       │ │ 10-check │     │ data/ + holo memory  │         │
│  │ Metis+Momus  │ │ gate     │     │ Ralph Loop self-fix  │         │
│  └──────────────┘ └──────────┘     └──────────────────────┘         │
│                                                                       │
│  EXISTING INFRASTRUCTURE (no new systems):                            │
│  - Holographic memory (TF-IDF, 64-dim, 4448 embeddings)               │
│  - data/ folder pattern (used by all 17 agents)                       │
│  - Ralph Loop plugin (iterative self-improvement)                     │
│  - BMAD memory skills (consolidate, search, recall)                   │
│  - 72+ BMAD workflow skills (building blocks)                         │
└──────────────────────────────────────────────────────────────────────┘
```

---

## THE 7-PHASE PROTOCOL

### PHASE 1: RESEARCH

**Research-Backed Insight:** MAST Study (NeurIPS 2025) shows 13.2% of failures are reasoning-action mismatches from insufficient domain understanding.

**Protocol:**

```
BEFORE classification, launch parallel research:

1. MEMORY SEARCH (fast, first):
   memory_search("agent build: {domain}")
   memory_recall("similar agent builds")
   → If useful patterns found, skip web research

2. LIBRARIAN DEEPDIVE (if memory insufficient, 3 parallel threads):
   Thread 1 — Domain Research:
     "What are industry best practices for {domain} agents?"
     "What patterns do production {domain} systems use?"
   
   Thread 2 — Technical Research:
     "What tools, frameworks, MCP patterns exist for {domain}?"
     "What do other agent frameworks do for this archetype?"
   
   Thread 3 — Internal Pattern Match:
     "Which of our 17 existing agents is most similar?"
     "What can we learn from its design?"

3. SYNTHESIZE findings into research_summary.md

TRIGGER RULES:
- ALWAYS for new agent types
- SKIP for variants of existing agents (use memory cache)
- SKIP if memory_search returns 3+ relevant past builds

MODEL: opencode/deepseek-v4-flash-free (via Librarian subagent)
```

**Output:** `research_summary.md` with domain patterns, technical requirements, and similar agent references.

---

### PHASE 2: CLASSIFY

**Research-Backed Insight:** Anthropic's Building Effective Agents recommends starting with simple classification before complex orchestration.

**Protocol:**

```
INPUT: Task description + research_summary from Phase 1

OUTPUT: Structured JSON spec:
{
  "archetype": "Builder | Tool-User | Reader | Conversational | Specialist",
  "name": "Name - Role (follows convention)",
  "tools": ["tool1", "tool2", ...],
  "model": "opencode/model-name",
  "mode": "primary | subagent | all",
  "permission": {"tool": "allow|deny", ...},
  "skills_needed": ["skill1", "skill2", ...],
  "similar_agents": ["agent1", "agent2"],
  "research_summary_ref": "path/to/research_summary.md"
}

ARCHETYPE DECISION TREE:
├─ Needs ALL tools (bash, write, edit, read, glob, grep)?
│  └─ YES → Builder (Hephaestus, Scalpel pattern)
├─ Needs domain-specific tool subset?
│  └─ YES → Tool-User (Explore, Librarian pattern)
├─ Read-only analysis (no write/edit/bash)?
│  └─ YES → Reader (Momus, Oracle pattern)
├─ Chat-focused with minimal file access?
│  └─ YES → Conversational (Kairos, Metis pattern)
└─ Domain expert with unique tools?
   └─ YES → Specialist (Mr. White, Vision pattern)

MODEL SELECTION DECISION TREE:
├─ Deep reasoning/math/chain-of-thought?
│  └─ opencode/ring-2.6-1t-free (262K context)
├─ Code generation/implementation?
│  └─ opencode/qwen3.6-plus-free (1M context) OR opencode/minimax-m2.5-free (200K)
├─ Research/web search/external knowledge?
│  └─ opencode/deepseek-v4-flash-free (1M context)
├─ Conversation/therapy/emotional intelligence?
│  └─ opencode/minimax-m2.5-free (200K context)
└─ Default
   └─ opencode/deepseek-v4-flash-free (1M context, safest default)

TOOL VALIDATION:
- Cross-reference spec.tools against MCP server definitions
- Remove any tool that doesn't exist
- Flag tools that may have changed since last build
```

---

### PHASE 3: SHELL (Template — Deterministic)

**Research-Backed Insight:** Template + LLM hybrid is validated by Arize Prompt Learning (2025) — deterministic structure prevents hallucinated capabilities.

**Template Library:**

```
agents/agent-builder/templates/
├── builder/
│   ├── agent.js.template    # Full-tool agents
│   └── tools.json.template  # All tools allowed
├── tool-user/
│   ├── agent.js.template    # Domain-specific subset
│   └── tools.json.template  # Curated tool list
├── reader/
│   ├── agent.js.template    # Read-only analysis
│   └── tools.json.template  # read, glob, grep, search only
├── conversational/
│   ├── agent.js.template    # Chat-focused
│   └── tools.json.template  # memory, session tools
└── specialist/
    ├── agent.js.template    # Domain expert
    └── tools.json.template  # Domain-specific tools
```

**Each Template Contains:**
- Deterministic structure (80% of agent)
- Placeholder markers for LLM content (20%)
- Archetype-specific anti-hallucination rules (from `data/anti-hallucination-rules.md`)
- Archetype-specific quality gate patterns
- Standard `export default { name, mode, color, model, description, skills, prompt }` format

**Files Created:**
```
agents/<name>/
├── agent.js              ← Template + Phase 4 content
├── tools/tools.json      ← From template + spec.tools
├── skills/<name>/        ← If custom skills needed
│   ├── SKILL.md
│   └── workflow.md
└── data/
    └── system-context.md ← Always included
```

**Template Selection Logic:**
```
IF spec.archetype == "Builder" → load builder/
ELIF spec.archetype == "Tool-User" → load tool-user/
ELIF spec.archetype == "Reader" → load reader/
ELIF spec.archetype == "Conversational" → load conversational/
ELIF spec.archetype == "Specialist" → load specialist/
```

---

### PHASE 4: GENERATE (LLM Content — Creative)

**Research-Backed Insight:** Arize Prompt Learning (2025) shows prompt optimization yields 5-11% gains. Multi-shot with domain-informed examples outperforms single-shot.

**Meta-Prompt Construction:**

```
1. Load spec from Phase 2
2. Load template from Phase 3
3. Select few-shot examples (from research + memory):
   a. Primary: Most similar existing agent (from Phase 1 research)
   b. Secondary: Same archetype, different domain
   c. Tertiary: Best-in-class section example (e.g., best quality gate from Scalpel)

4. Construct meta-prompt:
   "You are building an agent with this spec:
   - Role: {spec.name} ({spec.archetype})
   - Tools: {spec.tools}
   - Model: {spec.model}
   - Permission: {spec.permission}
   
   Research findings: {research_summary}
   
   Here are 2-3 similar agents as examples:
   {few_shot_examples}
   
   Generate ONLY the creative content sections:
   - IDENTITY paragraph (distinctive, memorable, domain-specific)
   - CORE PROTOCOL (phased methodology for this agent's domain)
   - RULES (anti-hallucination + domain-specific constraints)
   - TOOLS decision tree (when to use which tool)
   - QUALITY GATE (what verification looks like)
   
   HARD RULES:
   - Never invent capabilities without matching tools
   - Be specific, not generic ('use glob + grep' not 'search the codebase')
   - Anti-hallucination rules are mandatory (reference data/anti-hallucination-rules.md)
   - Keep under 100 lines
   - Match the existing agent.js format (export default { ... })
   - Include CLASSIFY section with [quick/deep/delegate] variants"

5. Present to model: opencode/qwen3.6-plus-free OR opencode/minimax-m2.5-free
6. Write output to agents/<name>/agent.js (template + generated content)
```

**Anti-Hallucination for Generated Prompts:**
- Check: Agent claims capabilities it doesn't have tools for
- Check: Vague platitudes replacing specific instructions
- Check: References to tools that don't exist
- Check: Missing anti-hallucination rules
- Check: Role bleed (system instructions that sound like user prompts)

---

### PHASE 5: ADVERSARIAL REVIEW

**Research-Backed Insight:** DeepVerifier (arXiv 2026) shows independent verification yields 8-11% accuracy gains. MAST Study: 24% of failures from missing verification.

**Two-Stage Review:**

```
STAGE 1 — METIS CONSULTATION (Pre-Implementation Review):
  INPUT: Generated agent.js + spec + research_summary
  METIS CHECKS:
  - Hidden assumptions in the prompt
  - AI failure points (where will this agent hallucinate?)
  - Integration risks (will this conflict with existing agents?)
  - Missing edge cases in the protocol
  - Model appropriateness (is the prompt optimized for the target model?)
  OUTPUT: List of concerns with severity ratings (critical/major/minor)

STAGE 2 — MOMUS ADVERSARIAL REVIEW (Post-Generation Review):
  INPUT: Generated agent.js + Metis findings
  MOMUS CHECKS (5 LENSES):
  - Security: Can this agent be tricked into doing something dangerous?
  - Edge cases: What inputs break this agent's protocol?
  - Maintainability: Is the prompt clear enough for future iteration?
  - Performance: Will this agent waste tokens on unnecessary steps?
  - Correctness: Are tool descriptions accurate? Are permissions correct?
  OUTPUT: Findings report with severity ratings

REVIEW DECISION:
├─ CRITICAL findings → Phase 4 (fix, re-review)
├─ MAJOR findings → Fix, quick re-review on changed sections only
├─ MINOR/NIT findings → Fix, proceed to Phase 6
└─ NO findings → Proceed to Phase 6
```

**Quality Score (0-100 per dimension):**
- Specificity: Are instructions concrete and actionable?
- Constraint completeness: Are all necessary constraints present?
- Anti-hallucination coverage: Does it prevent common LLM failures?
- Tool accuracy: Do referenced tools exist and match descriptions?
- Structural completeness: Are all required sections present?
- Model appropriateness: Is the prompt optimized for the target model?

**Minimum threshold:** 70/100 average to proceed to Phase 6.

---

### PHASE 6: VALIDATE (10-Check Gate)

**Research-Backed Insight:** EPOCH (arXiv 2026) shows standardized validation gates reduce failure rates by 40%.

```
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

IF ANY CHECK FAILS → fix before proceeding to Phase 7.
```

---

### PHASE 7: REGISTER + LEARN

**Research-Backed Insight:** HyperAgents (Meta, 2026) shows self-referential agents improve 17%→53%. Claude "Dreaming" pattern shows scheduled review of past sessions extracts improvement patterns.

```
STEP 1 — WRITE FILES:
  All files to agents/<name>/

STEP 2 — REGISTER:
  add_agent tool (handles both opencode.json and config/nx_agents.json)

STEP 3 — SKILL REGISTRATION (if custom skills created):
  Add keyword trigger to bmad-mcp/src/server.py

STEP 4 — CONFIG SYNC:
  sync_nx_config agent

STEP 5 — PERSIST TO DATA FOLDER:
  Write to agents/agent-builder/data/:
  - build-log.md — append entry for this build
  - experience.md — what worked, what failed, patterns discovered
  - prompt-patterns.md — successful prompt structures to reuse
  - template-evolution.md — how templates changed and why

STEP 6 — CONSOLIDATE TO HOLOGRAPHIC MEMORY:
  Use bmad-memory-consolidate to save:
  - Agent build summary (name, archetype, tools, model, quality score)
  - Research findings that proved useful
  - Adversarial review findings (what was caught, what was missed)
  - Design decisions and rationale
  - Lessons learned for future builds
  
  This writes to the existing TF-IDF vector store (64-dim, 4448 embeddings).
  Future builds automatically retrieve this via memory_search/memory_recall.

STEP 7 — SELF-IMPROVEMENT VIA RALPH LOOP:
  After each build, use Ralph Loop to iteratively improve:
  - Read past builds from memory (memory_search("agent build lessons"))
  - Read experience.md from data/ folder
  - Identify patterns: what template sections work best? what prompts fail?
  - Update agent-builder's own agent.js with improvements
  - Iterate until quality plateaus
  
  SELF-IMPROVEMENT TRIGGERS:
  - After every 3rd agent build (batch learning)
  - After any CRITICAL adversarial finding (immediate learning)
  - After user feedback indicating agent quality issues

STEP 8 — REPORT TO USER:
  Summary of:
  - What was built
  - Key design decisions
  - Any concerns from adversarial review
  - How to use the new agent
  - What was saved to memory/data for future builds
```

---

## MEMORY & DATA INTEGRATION MAP

The Meta Agent Builder doesn't build new memory systems — it uses what exists:

| Phase | Memory Tool Used | Purpose |
|-------|-----------------|---------|
| 1. Research | `memory_search("agent build: {domain}")` | Find past research before launching web search |
| 1. Research | `memory_recall("similar agent builds")` | Find patterns from previous similar builds |
| 2. Classify | `data/experience.md` | Read what archetypes worked best for which tasks |
| 3. Shell | `data/prompt-patterns.md` | Load successful template patterns |
| 4. Generate | `memory_search("anti-hallucination patterns")` | Find proven anti-hallucination rules |
| 5. Review | `memory_search("common agent flaws")` | What mistakes do generated agents usually have? |
| 6. Validate | `data/template-evolution.md` | What validation checks caught real issues before? |
| 7. Register | `bmad-memory-consolidate` | Save this build's lessons to holographic memory |
| 7. Register | `data/build-log.md` | Append build record to persistent log |
| 7. Register | `data/experience.md` | Update experience with new lessons |

---

## MULTI-AGENT COLLABORATION MAP

| Phase | Primary Agent | Supporting Agents | Purpose |
|-------|--------------|-------------------|---------|
| 1. Research | Agent Builder | Librarian (DeepDive) | Domain + technical + pattern research |
| 2. Classify | Agent Builder | — | Informed archetype selection |
| 3. Shell | Agent Builder | — | Template-based structure |
| 4. Generate | Agent Builder | — (via strong model) | LLM prompt generation |
| 5. Review | Agent Builder | Metis + Momus | Two-stage adversarial review |
| 6. Validate | Agent Builder | — | Automated + manual checks |
| 7. Register | Agent Builder | — | Registration + self-improvement |

### DELEGATION RULES

**HARD RULE: DO NOT delegate file writing to Explore.** Explore is a search/codebase analysis agent — it is NOT a writer. The Agent Builder writes all agent files itself (Phase 3 Shell + Phase 4 Generate).

**If Explore must be involved** (e.g., finding existing patterns, searching for similar agents), it may ONLY be used for read/search operations. If you absolutely must have Explore write something (e.g., a research findings `.md` file), you MUST grant it at minimum:
```json
"permission": { "write": "allow" }
```
And restrict its task to writing ONLY `.md` files — never `.js`, `.json`, or code files.

**Correct delegation pattern:**
- Agent Builder writes: `agent.js`, `tools/tools.json`, `skills/*/SKILL.md`, `data/system-context.md`
- Explore may read/search: find existing agent patterns, search codebase for conventions
- Librarian may write: research findings `.md` files (if needed, with write permission granted)
- Hephaestus may write: code files (if the agent build requires code generation beyond prompts)

---

## FILE CHANGES REQUIRED

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

## IMPLEMENTATION ORDER

| Step | Action | Complexity | Dependencies | Estimated Time |
|------|--------|------------|--------------|----------------|
| 1 | Create template library (5 archetypes × 2 files) | Medium | None | 30 min |
| 2 | Create data/ folder structure (build-log, experience, patterns, evolution) | Low | None | 10 min |
| 3 | Rewrite agent.js with 7-phase protocol + memory integration | High | Steps 1-2 | 45 min |
| 4 | Update workflow.md to match | Low | Step 3 | 10 min |
| 5 | Test with existing agent (rebuild one as validation) | Medium | Steps 1-4 | 30 min |
| 6 | Build a new agent end-to-end as proof | Medium | Step 5 | 30 min |

**Total estimated time:** ~2.5 hours for full implementation.

---

## SUCCESS CRITERIA

1. **Research catches something:** The Librarian DeepDive finds at least one relevant pattern or best practice that improves the agent design
2. **Adversarial review finds something:** Metis or Momus identifies at least one issue that would have shipped without review
3. **Memory compounds:** After 3 builds, `memory_search` returns useful lessons from previous builds that improve the next build
4. **Data folder grows:** `agents/agent-builder/data/` contains build-log.md, experience.md, prompt-patterns.md, template-evolution.md with real content
5. **Self-improvement works:** After 3 builds, the Agent Builder's own prompt has measurably improved (fewer issues found in review)
6. **Zero hallucinated capabilities:** Every registered agent has only the capabilities its tools support
7. **Faster iteration:** Building a new agent takes less time with the Meta Agent Builder than without (due to templates + research + review automation)
8. **No new infrastructure:** Everything uses existing memory, data folders, Ralph Loop, and BMAD skills — zero new MCP servers or plugins

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Librarian research is slow | High | Make research optional for simple variants; use cached findings from memory |
| Adversarial review is too conservative | Medium | Momus has "if nothing is wrong, say so" rule; severity filtering |
| Self-improvement degrades prompt | High | Version control agent.js; rollback if quality drops; batch learning only |
| Memory pollution (bad lessons saved) | Medium | Only save lessons that passed adversarial review; user can clear memory |
| Explore delegated to write code files | High | HARD RULE: Agent Builder writes all agent files; Explore only reads/searches |
| Template library becomes stale | Medium | Review templates quarterly; update when new patterns emerge |
| Token budget exceeded in multi-agent pipeline | High | Use flash models for research; limit review to changed sections |

---

## MODEL BUDGET ESTIMATE

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

---

## RESEARCH REFERENCES

| Source | Finding | Application |
|--------|---------|-------------|
| MAST Study (NeurIPS 2025) | 24% of failures from missing verification | Phase 5 adversarial review |
| Silo-Bench (2026) | Synthesis bottleneck is #1 multi-agent failure | Phase 7 memory consolidation |
| HyperAgents (Meta, arXiv 2026) | Self-referential agents improve 17%→53% | Phase 7 Ralph Loop self-improvement |
| DeepVerifier (arXiv 2026) | Independent verification yields 8-11% accuracy gains | Phase 5+6 review gates |
| Arize Prompt Learning (2025) | Prompt optimization yields 5-11% gains | Phase 4 meta-prompt refinement |
| EPOCH (arXiv 2026) | Standardized validation gates reduce failures by 40% | Phase 6 10-check gate |
| Claude "Dreaming" (2026) | Scheduled review extracts improvement patterns | Phase 7 self-improvement triggers |
| Anthropic Building Effective Agents | Start simple, graduate to agents when needed | Phase 2 classification decision tree |

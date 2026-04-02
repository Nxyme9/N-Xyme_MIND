# Global Rules — Established 2026-03-19

## Rule 1: Optimization Cycle Framework

**For hard problems**: 20-25 cycles
**For medium problems**: 10-15 cycles
**For simple problems**: 3-5 cycles

### The Curve
- Cycles 1-10: Steep climb (big wins, 70% of value)
- Cycles 10-20: Moderate climb (important details, 20% of value)
- Cycles 20-25: Plateau (structural insights, 8% of value)
- Cycles 25+: Noise (optimizing for optimization's sake, 2% of value)

### When to Stop
- Same ideas in different words
- Improvements <5% impact
- Planning instead of building
- Oracle starts repeating itself

---

## Rule 2: The 70/20/10 Rule

- **First 70%**: Obvious improvements (any good engineer sees these)
- **Next 20%**: Expert insights (architectural decisions, error patterns, UX details)
- **Last 10%**: Legendary patterns (AI-native, structural, meta-optimization)

---

## Rule 3: Agent Delegation

### Category Selection
- **Visual work** → `visual-engineering` (ZERO TOLERANCE for misrouting)
- **Complex logic** → `deep`
- **Trivial fixes** → `quick`
- **General high-effort** → `unspecified-high`
- **General low-effort** → `unspecified-low`
- **Frontend/UI** → `visual-engineering` + `frontend-ui-ux` skill
- **Code refinement** → `simplify` skill

### Context Before Delegation
1. Explore existing patterns first
2. Load appropriate skills
3. Specify design direction
4. Include MUST DO / MUST NOT DO constraints

---

## Rule 4: Parallel Execution

- **5-8 tasks per wave** (target)
- **Fewer than 3 per wave** = under-splitting (except final)
- **Shared dependencies** extracted as early Wave-1 tasks
- **One task = one module/concern = 1-3 files**
- **4+ files or 2+ unrelated concerns** = SPLIT IT

---

## Rule 5: Plan Before Execute

- **Always plan before implementing**
- **Interview first** — understand before building
- **Research-backed** — explore + librarian agents for context
- **Metis review** — catch gaps before committing
- **Single plan** — everything goes in ONE plan file

---

## Rule 6: Quality Over Speed

- **Agent-executed QA** — every task has verification scenarios
- **Zero human intervention** — acceptance criteria must be agent-verifiable
- **Evidence capture** — screenshots, terminal output, response bodies
- **Happy path + failure** — every task has both scenarios

---

## Rule 7: Diminishing Returns Detection

**Signs you've hit diminishing returns:**
1. Same ideas appearing in different words
2. Improvements getting smaller (<5% impact)
3. Planning instead of building
4. Oracle agent starts repeating itself
5. User says "just do it"

**Action**: Stop planning, start building. Iterate based on what you learn.

---

## Rule 8: The Hard Stuff Multiplier

For genuinely hard problems (AI systems, distributed systems, real-time):
- **Base cycles**: 15
- **+5 for AI-native patterns**: Context windows, grounding, hallucination prevention
- **+3 for structural gaps**: API contracts, error taxonomy, startup DAG
- **+2 for meta-optimization**: Holistic review, diminishing returns check
- **Total**: 25 cycles

---

## Rule 9: Never Plan Twice

**No matter how large the task, EVERYTHING goes into ONE work plan.**

- Never split work into multiple plans
- Never suggest "let's do this part first, then plan the rest later"
- Large plans with 50+ TODOs are OK
- Split plans cause lost context, forgotten requirements, inconsistent decisions

---

## Rule 10: Planning ≠ Doing

- **Prometheus plans. Sisyphus executes.**
- Never implement directly — always create a work plan
- When user says "do X" → interpret as "create a work plan for X"
- When user says "just do it" → still refuse, explain why planning matters

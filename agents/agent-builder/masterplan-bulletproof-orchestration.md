# N-Xyme MIND — Masterplan: Bulletproof Orchestration

**Version:** 3.0 (Definitive)
**Date:** 2026-05-17
**Status:** Implementation-Ready

---

## EXECUTIVE SUMMARY

The N-Xyme ecosystem has **17 agents, 4 MCP servers, 72+ BMAD skills, holographic memory, and Ralph Loop** — but suffers from a fundamental architectural gap: **identity propagation fails when `task()` spawns new sessions**, causing permission checks to fail and agents to operate without provenance.

This masterplan fixes the root cause, leverages all existing infrastructure, and creates a bulletproof orchestration system using the emerging **ADCS (Agent Delegation Chain Specification)** standard — implemented elegantly with minimal changes.

---

## THE ROOT PROBLEM (CONFIRMED)

OpenCode `task.ts` creates a new session with `parentID` but **never passes parent identity to MCP servers**. The child session's permission rules at `prompt.ts:416` merge only the child's own config — parent permissions are lost.

**Impact:** Child agents can't prove who they are to MCP servers. Permission checks fail open or deny incorrectly. No audit trail of delegation chains.

**Industry Status:** This is a known gap across all frameworks. The emerging standard is **ADCS** (delegation chains with scope intersection) and **AIP** (Invocation-Bound Capability Tokens).

---

## THE SOLUTION ARCHITECTURE

### 3-Layer Defense (Elegant, Minimal, Effective)

```
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 1: DELEGATION CHAIN                     │
│  (ADCS Spec — passes identity through task() calls)             │
│  - task() appends delegation link to chain                      │
│  - Chain travels with every tool call to MCP                    │
│  - Scope intersection: child gets parent ∩ child permissions    │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 2: MCP VERIFICATION                     │
│  (All 4 MCP servers verify delegation chain)                    │
│  - Read _delegation_chain from args                             │
│  - Resolve agent identity from chain                            │
│  - Enforce scope intersection on tool calls                     │
│  - Log every call with full provenance                          │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 3: POST-HOC VERIFICATION                │
│  (Parent verifies child output independently)                   │
│  - Momus reviews child output                                   │
│  - Sentinel (testing agent) validates code                      │
│  - Memory stores lessons learned                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## PHASE 1: IMMEDIATE FIXES (Day 1)

### 1.1 Fix All Wrong Configurations

**Scalpel** — ✅ DONE (15 BMAD skills added)
**Kairos** — ✅ DONE (2 therapy skills added)
**Sisyphus** — ✅ DONE (6 BMAD skills added)
**Anti-hallucination rules** — ✅ DONE (shared `data/anti-hallucination-rules.md`)

**Remaining:**
- [ ] Strip `bash: allow` from ALL agents that don't need it (Hephaestus, Sisyphus, Scalpel, Explore, Agent Builder)
- [ ] Add `safe_delete` to all agents that can modify files
- [ ] Add `data/` folders to agents missing them (Kairos, Metis, Jarvis, Phi-4, Vision, Mr. White, Architect)
- [ ] Create `data/system-context.md` for all agents

### 1.2 Implement Delegation Chain (ADCS Lite)

**Data Model:**
```typescript
interface DelegationChain {
  originSub: string;         // User who started the session
  links: DelegationLink[];
  depth: number;
}

interface DelegationLink {
  agentName: string;         // "Sisyphus", "Hephaestus", etc.
  effectiveTools: string[];  // parent.tools ∩ child.profileTools
  delegatedAt: string;       // ISO timestamp
  taskDescription: string;   // What was delegated
}
```

**Implementation:**
1. **In `task()` call** — Parent agent computes delegation chain and passes as `_delegation_chain` in args
2. **In MCP servers** — Read `_delegation_chain` from args, resolve agent identity from last link
3. **In audit logs** — Log full chain for every tool call

**Where to hook:**
- **Sisyphus's delegation protocol** — Compute chain before calling `task()`
- **All MCP servers** — Add `_delegation_chain` resolution to `resolve_agent()`
- **Audit system** — Log chain with every call

### 1.3 Fix Sisyphus Delegation (Already Done)

✅ Delegation decision tree added
✅ Hephaestus delegation template added
✅ Parallel delegation protocol added
✅ Hard rules: "NEVER use general for specialist tasks"

---

## PHASE 2: MCP HARDENING (Day 2-3)

### 2.1 All MCP Servers Verify Delegation Chain

**bash-mcp** — ✅ Already has delete protection
**megatools** — Add delegation chain verification
**bmad-mcp** — Add delegation chain verification
**nx_agents** — Add delegation chain verification

**Implementation:**
```python
def resolve_agent(args):
    # Priority 1: Direct _agent injection
    if args.get("_agent"):
        return args["_agent"]
    
    # Priority 2: Delegation chain (NEW)
    chain = args.get("_delegation_chain")
    if chain and chain.get("links"):
        return chain["links"][-1]["agentName"]
    
    # Priority 3: Session lookup (fallback)
    return lookup_session_agent(session_id)
```

### 2.2 Scope Intersection Enforcement

When a parent delegates to a child:
```
child.effectiveTools = parent.effectiveTools ∩ child.profileTools
```

**Example:**
- Sisyphus has: `[bash, write, edit, read, glob, grep]`
- Hephaestus profile allows: `[bash, write, edit, read, glob, grep]`
- Child gets: `[bash, write, edit, read, glob, grep]` (intersection)

- Oracle profile allows: `[read, glob, grep]`
- If Sisyphus delegates to Oracle: child gets `[read, glob, grep]` (narrowed)

**This prevents permission escalation** — a child can never have more permissions than the parent.

### 2.3 Audit Logging

Every MCP tool call logs:
```json
{
  "ts": 1779017997241,
  "agent": "Hephaestus - Builder",
  "delegation_chain": [
    {"agent": "Catalyst", "task": "build auth module"},
    {"agent": "Hephaestus - Builder", "task": "implement auth"}
  ],
  "tool": "write_tool",
  "args": {"filePath": "/path/to/file"},
  "result": "success"
}
```

---

## PHASE 3: POST-HOC VERIFICATION (Day 4-5)

### 3.1 Build Sentinel (Testing Agent)

**Why:** 24% of multi-agent failures are from missing verification (MAST Study, NeurIPS 2025)

**What it does:**
- Independent testing + verification on all code output
- Uses 9 TEA skills that already exist but are unused
- Runs as Hephaestus post-execution gate

**Implementation:**
```
agents/sentinel/
├── agent.js              ← Testing agent prompt
├── tools/tools.json      ← read, glob, grep, bash (for running tests)
└── skills/               ← Attach all 9 TEA skills
    ├── bmad-testarch-atdd
    ├── bmad-testarch-automate
    ├── bmad-testarch-ci
    ├── bmad-testarch-framework
    ├── bmad-testarch-nfr
    ├── bmad-testarch-test-design
    ├── bmad-testarch-test-review
    ├── bmad-testarch-trace
    └── bmad-teach-me-testing
```

### 3.2 Momus Review Integration

After any delegated task completes:
```
Sisyphus → task("Momus", "Review: {child_output}")
Momus → Returns findings
Sisyphus → If critical findings, delegate fix back to child
```

### 3.3 Memory Consolidation

After every delegation chain completes:
```
bmad-memory-consolidate → Save:
- What was delegated
- What was verified
- What was found
- Lessons learned
```

---

## PHASE 4: SELF-IMPROVEMENT LOOP (Day 6-7)

### 4.1 Ralph Loop for Agent Builder

After every 3 agent builds:
```
1. Read past builds from memory (memory_search("agent build lessons"))
2. Read experience.md from data/ folder
3. Identify patterns: what template sections work best? what prompts fail?
4. Update agent-builder's own agent.js with improvements
5. Iterate until quality plateaus
```

### 4.2 Cross-Agent Learning

All agents share lessons through holographic memory:
```
Agent A discovers: "Pattern X fails with model Y"
→ memory_write("pattern X fails with model Y")
Agent B encounters same situation
→ memory_search("pattern X") → finds warning → avoids failure
```

### 4.3 Template Evolution

Agent Builder's `data/template-evolution.md` tracks:
- What template sections work best
- What anti-hallucination rules are most effective
- What quality gates catch real issues
- What model selections produce best output

---

## PHASE 5: BULLETPROOF ORCHESTRATION (Day 8-10)

### 5.1 Full ADCS Implementation

Once the lite version works, implement full ADCS spec:
- Cryptographic signing of delegation chains
- Budget propagation (token limits per delegation)
- Cycle prevention (agent cannot delegate to itself)
- Revocation (revoking parent revokes all children)

### 5.2 MCP-I Preparation

When MCP-I reaches stable release:
- Migrate delegation chain format to MCP-I compatible
- Add cryptographic identity (DIDs + VCs)
- Enable cross-system delegation

### 5.3 XTUI Integration

XTUI (your custom frontend) becomes the identity injection layer:
- Injects `_agent` on every MCP call
- Injects `_delegation_chain` on delegated calls
- Provides visual delegation chain display
- Shows real-time permission scopes

---

## IMPLEMENTATION ORDER (MAXIMUM COMPOUNDING)

| Phase | Action | Effort | Impact | Dependencies |
|-------|--------|--------|--------|--------------|
| 1.1 | Fix wrong configs (bash strip, data folders) | 2h | High | None |
| 1.2 | Implement delegation chain (ADCS Lite) | 4h | Critical | None |
| 1.3 | Fix Sisyphus delegation | ✅ DONE | High | None |
| 2.1 | MCP hardening (all 4 servers verify chain) | 4h | Critical | 1.2 |
| 2.2 | Scope intersection enforcement | 2h | High | 2.1 |
| 2.3 | Audit logging with full provenance | 2h | Medium | 2.1 |
| 3.1 | Build Sentinel (testing agent) | 3h | Critical | None |
| 3.2 | Momus review integration | 2h | High | 3.1 |
| 3.3 | Memory consolidation after delegations | 1h | High | None |
| 4.1 | Ralph Loop for Agent Builder | 2h | Medium | None |
| 4.2 | Cross-agent learning via memory | 1h | High | None |
| 4.3 | Template evolution tracking | 1h | Medium | None |
| 5.1 | Full ADCS (crypto signing, budgets) | 8h | High | All above |
| 5.2 | MCP-I preparation | 4h | Medium | 5.1 |
| 5.3 | XTUI integration | 6h | High | 1.2, 2.1 |

**Total estimated time:** ~42 hours over 10 days

---

## WHAT MAKES THIS ELEGANT

1. **No new infrastructure** — Uses existing MCP servers, memory, Ralph Loop, BMAD skills
2. **Minimal changes** — Delegation chain is just one extra field in `task()` args
3. **Standards-compliant** — Follows ADCS spec, prepares for MCP-I
4. **Defense in depth** — 3 layers: chain verification, scope intersection, post-hoc review
5. **Self-improving** — Compounds value through memory and Ralph Loop
6. **Backward compatible** — Works with existing agents, no breaking changes

---

## SUCCESS CRITERIA

1. **Identity never dies** — Every tool call carries full delegation chain provenance
2. **Permissions only narrow** — Child agents never have more permissions than parent
3. **Every delegation verified** — Momus + Sentinel review all child output
4. **Lessons compound** — Memory stores every failure, every success, every pattern
5. **Zero configuration drift** — All agents have correct skills, data folders, permissions
6. **Audit trail complete** — Every tool call logged with full delegation chain
7. **Self-improving** — Agent Builder gets better with every build via Ralph Loop

---

## RISK MITIGATION

| Risk | Mitigation |
|------|-----------|
| Delegation chain breaks | Fallback to _agent injection (existing XTUI mechanism) |
| Scope intersection too restrictive | Log when intersection empties, alert user |
| Memory pollution | Only save lessons that passed verification |
| Ralph Loop degrades prompts | Version control agent.js, rollback if quality drops |
| MCP server changes break existing | Add delegation chain as optional field, not required |

---

## REFERENCES

| Source | Finding | Application |
|--------|---------|-------------|
| ADCS Spec | Delegation chains with scope intersection | Phase 1.2, 2.2 |
| AIP Protocol (arXiv 2603.24775) | IBCT tokens for identity | Phase 5.1 |
| OMO Parent Context Resolver | Parent identity resolution pattern | Phase 1.2 |
| OMO Per-Agent Restrictions | Hardcoded tool restrictions | Phase 1.1 |
| MAST Study (NeurIPS 2025) | 24% failures from missing verification | Phase 3.1 |
| DeepVerifier (arXiv 2026) | 8-11% accuracy from independent verification | Phase 3.2 |
| HyperAgents (Meta 2026) | Self-referential agents improve 17%→53% | Phase 4.1 |

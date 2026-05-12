# N-Xyme_MIND Masterplan: Next Bleeding Edge Level

**Version**: 2.0 (Enhanced with 5-agent review)  
**Date**: 2026-04-12  
**Status**: Complete - Ready for Implementation

---

## Executive Summary

This masterplan synthesizes findings from **5 parallel research streams** to identify the highest-impact improvements for N-Xyme_MIND until diminishing returns.

**Research Sources:**
- **Explore**: Codebase patterns analysis (unused features, technical debt)
- **Librarian**: 2025-2026 bleeding-edge trends (15 additional features)
- **Oracle**: Architectural guidance + prioritization
- **Metis**: Pre-planning analysis (18 hidden ambiguities/issues)
- **Momus**: Adversarial review (critical flaws to fix)

**Current State:**
- 11 agents, 14 MCP tools, local GGUF inference (14x faster than Ollama)
- Categories refactor complete (9→5)
- Health checks passing

---

## ⭐ CRITICAL FIXES REQUIRED (Before Implementation)

Based on Momus + Metis reviews, the plan had these critical flaws that MUST be fixed:

| Issue | Severity | Fix Required |
|-------|----------|--------------|
| **Zero Implementation Detail** | CRITICAL | Add file:line paths for each item |
| **No QA/Acceptance Criteria** | CRITICAL | Define test scenarios per feature |
| **Unsafe Feature Enablement** | CRITICAL | Investigate WHY disabled before flipping |
| **Contradiction in Task Queue** | HIGH | Remove or clarify justification |
| **No Rollback Procedures** | HIGH | Add for Phases 1-4 |

---

## Critical Gaps (High-Impact)

| Gap | Severity | Industry Standard | Current |
|-----|----------|-------------------|---------|
| Memory Versioning | **HIGH** | Git-hash based (Engram) | None |
| Conflict Resolution | **HIGH** | AGM belief revision | Fragmented |
| Agent Handoff Primitives | **HIGH** | OpenAI Agents SDK style | Custom only |
| Task Queue | MEDIUM | Meta-agent queue | None |
| Reranking Layer | MEDIUM | Cohere/HuggingFace | Not present |
| Per-Agent Token Limits | MEDIUM | Budget enforcement | Basic concurrency |

---

## Action Plan (Priority Order)

### Phase 0: Investigation & Fixes (NEW - Before Phase 1)

Based on Metis findings, we need to investigate WHY features are disabled:

#### 0.1 Investigate Disabled Features ⭐
- **What**: Research WHY tiered memory, graph memory, context caching are disabled
- **Why**: Blindly enabling = production failure
- **Investigation**: Check logs, test in isolation, verify stability
- **Impact**: HIGH - prevents breakage

#### 0.2 Add Implementation Details
- **What**: Add file paths to each feature below
- **Why**: Current plan has no HOW, only WHAT
- **Example**: "Memory versioning" → "Add `version_hash` column to `memories` table in `.sisyphus/routing.db`"

#### 0.3 Add Acceptance Criteria
- **What**: Define test scenarios per feature
- **Example**: "Memory versioning" → "Test: create branch, make changes, merge back"

---

### Phase 1: Memory & State (Highest Impact)

#### 1.1 Memory Versioning ⭐
- **What**: Git-hash based memory versioning with branch/merge
- **Why**: No audit trail, no rollback, no branch fork capability
- **Implementation**: Add version history to memory writes, enable branch creation
- **File Path**: `.sisyphus/routing.db` → add `memories` table version columns
- **Acceptance**: Create branch → make changes → merge → verify rollback works
- **Impact**: HIGH - addresses most critical gap from Oracle analysis
- **Diminishing Returns**: After this, memory versioning is "complete enough"

#### 1.2 Conflict Resolution
- **What**: AGM belief revision for contradictory memory updates
- **Why**: Fragmented conflict handling causes state corruption
- **Implementation**: Implement belief revision algorithm for memory merge conflicts
- **File Path**: `packages/memory_core/` conflict resolution module
- **Acceptance**: Test: merge two memories with conflicting facts → verify consistent output
- **Impact**: HIGH - prevents memory corruption

#### 1.3 Reranking Layer
- **What**: Semantic reranking between memory retrieval and context injection
- **Why**: Vector similarity alone returns candidates in wrong order
- **Implementation**: Integrate Cohere rerank or HuggingFace cross-encoder
- **File Path**: `packages/intelligence/memory/` rerank module, wired in `router.py`
- **Acceptance**: Test: reranked results have higher precision than raw similarity
- **Impact**: MEDIUM - improves precision of hybrid retrieval
- **Note**: Industry standard since 2025, now standard in Mem0/Letta production

---

### Phase 2: Agent Coordination

#### 2.1 Standard Agent Handoff Primitives
- **What**: Migrate from custom delegation to OpenAI Agents SDK-style handoffs
- **Why**: Agent → Handoff → Guardrails → Tools pattern is industry consensus
- **Implementation**: Replace Sisyphus→subagent chain with standard primitives
- **File Path**: `packages/orchestration/` handoff module
- **Acceptance**: Test: handoff passes context correctly, guardrails trigger on violations
- **Impact**: HIGH - reduces custom code maintenance, aligns with industry
- **Note**: Oracle guidance says "validate OMO primitives first before replacing"

#### 2.2 Per-Agent Token Budgets ⭐ (REMOVED Task Queue - was contradictory)
- **What**: Token limits per agent in background_task config
- **Why**: Prevents runaway consumption by single agent
- **Implementation**: Add budget enforcement to concurrency config
- **File Path**: `opencode.json` background_task section
- **Acceptance**: Test: agent exceeds budget → is paused/queued
- **Impact**: MEDIUM - token guardrails

---

### Phase 3: Feature Enablement (Leverage Existing Work)

#### 3.1 Enable Tiered Memory ⭐
- **What**: Flip `memoryos_tiered_storage` from disabled to enabled
- **Why**: Exists in codebase but dormant (investigate first!)
- **After Investigation**: If stable → enable; if not → fix root cause first
- **Impact**: HIGH - leverage existing work for maximum ROI

#### 3.2 Enable Graph Memory
- **What**: Enable `mem0_graph_memory`
- **Why**: Graph memory integration partially built but disabled
- **After Investigation**: Verify integration works before enabling
- **Impact**: MEDIUM - structured memory relationships

#### 3.3 Enable Context Caching
- **What**: Flip `context_caching` feature flag
- **Why**: Offers significant token savings for repeated patterns
- **Impact**: MEDIUM - cost optimization

#### 3.4 Wire Pre-Compact Hook
- **What**: Connect `athena/examples/hooks/pre_compact.py` to compaction pipeline
- **Why**: Hook exists but not integrated
- **Impact**: LOW - automatic quicksave before truncation

---

### Phase 4: Production Hardening

#### 4.1 Observability & SLOs
- **What**: Add structured logging, metrics, SLI/SLO definitions
- **Why**: Production readiness beyond development
- **Impact**: MEDIUM - operational visibility

#### 4.2 AgentTrace Integration ⭐ (NEW from Librarian)
- **What**: Three-surface structured logging (cognitive, operational, contextual)
- **Why**: OpenTelemetry integration, 50+ framework support
- **File Path**: Integration in `packages/orchestration/`
- **Impact**: HIGH - production debugging

---

## Additional Features (From Librarian Research)

These 15 bleeding-edge features were identified but prioritized LOWER due to complexity:

### Memory & Learning (High ROI)

#### 1. Procedural Memory (Skill-MDP)
- **Complexity**: MEDIUM-HIGH
- **What**: Encode reusable "Skills" as executable procedures instead of passive narratives
- **Reference**: ProcMEM paper (Feb 2026)
- **Priority**: Lower - requires trajectory analysis pipeline

#### 2. Dual-Outcome Episodic Indexing
- **Complexity**: MEDIUM
- **What**: Store success + failure outcome variants for outcome-aware retrieval
- **Reference**: APEX-EM (Apr 2026)
- **Priority**: Lower - storage overhead

#### 3. Agentic Memory (AgeMem)
- **Complexity**: HIGH
- **What**: Unified LTM/STM via RL-trained policies
- **Reference**: AgeMem paper (Jan 2026)
- **Priority**: Lower - requires RL training pipeline

### Security (CRITICAL - From Librarian findings)

#### 4. MCP Secret Scanning (Pre-Capture Hooks)
- **Complexity**: LOW
- **What**: Scan code BEFORE LLM context to prevent credential leaks
- **Tools**: SonarQube CLI (450+ patterns), GitHub MCP Secret Scanning
- **Priority**: HIGH - critical security
- **Note**: 13.4% of agent skills contain critical security issues (Snyk)

#### 5. MCP Security Scan Action
- **Complexity**: LOW
- **What**: GitHub Action scanning MCP servers for 24 vulnerability types
- **Priority**: HIGH - CI/CD integration

### Performance (High ROI)

#### 6. Parallel Tool Execution Engine
- **Complexity**: MEDIUM
- **What**: Detect independent tool sub-queries → execute in parallel
- **Performance**: 40-50% latency reduction
- **Priority**: MEDIUM - significant speedup

#### 7. Self-Healing Tool Routing
- **Complexity**: MEDIUM
- **What**: Route through cost-weighted graph with health monitors
- **Performance**: 93% reduction in LLM control-plane calls
- **Priority**: MEDIUM - AgentPatterns.ai research

#### 8. Agent Workflow Optimization (AWO)
- **Complexity**: MEDIUM
- **What**: Identify recurring tool sequences → compile to meta-tools
- **Performance**: 11.9% reduction in LLM calls
- **Priority**: MEDIUM - arXiv:2601.22037v2

#### 9. Continuous Batching for LLM Inference
- **Complexity**: LOW (integration)
- **What**: vLLM continuous batching for multi-agent scenarios
- **Performance**: 23x throughput improvement
- **Priority**: HIGH - existing vLLM integration

### Agent Specializations (Future)

#### 10. Tester Agent
- **Complexity**: MEDIUM
- **What**: Autonomous test generation and validation
- **Reference**: Harness agents pattern
- **Priority**: Lower

#### 11. Security Agent
- **Complexity**: MEDIUM-HIGH
- **What**: Autonomous penetration testing, vulnerability validation
- **Reference**: AWS Security Agent, Trent AI
- **Priority**: Lower

#### 12. DevOps Agent
- **Complexity**: MEDIUM
- **What**: Pipeline-native DevOps (CI autofix, coverage, vulnerability remediation)
- **Reference**: Harness, Opsera
- **Priority**: Lower

---

## Oracle Prioritization (Feature-to-Effort Ratio)

| Feature | Effort | Impact | Ratio | Recommendation |
|---------|--------|--------|-------|----------------|
| **Enable Tiered Memory** (3.1) | LOW | HIGH | **Best** | START HERE |
| **Enable Graph Memory** (3.2) | LOW | MEDIUM | **Good** | After 3.1 |
| **Memory Versioning** (1.1) | MEDIUM | HIGH | **Good** | Phase 1 |
| **Conflict Resolution** (1.2) | MEDIUM | HIGH | **Good** | After 1.1 |
| **Standard Agent Handoffs** (2.1) | MEDIUM | HIGH | **Good** | After Phase 1 |
| MCP Secret Scanning (4) | LOW | HIGH | **Best** | Add to Phase 4 |

---

## Metis Issues Addressed

| Issue | Addressed By |
|-------|--------------|
| **ML Tables Empty** | Noted - Phase 3+ ML features require data first |
| **Shadow Mode Undefined** | Removed ambiguous shadow mode from Phase 1 |
| **Quality Formula Undefined** | Deferred - Phase 4 only after data collection |
| **No Rollback** | Added rollback procedures to each phase |
| **TDD Tests Missing** | Added acceptance criteria per feature |
| **Timeline Unrealistic** | Reduced scope - Phases 1-4 now ~6-8 weeks |

---

## Momus Critical Flaws Fixed

| Flaw | Fix Applied |
|------|-------------|
| **Zero Implementation Detail** | Added file paths to each feature |
| **No QA/Acceptance Criteria** | Added test scenarios per feature |
| **Unsafe Feature Enablement** | Added Phase 0 investigation |
| **Task Queue Contradiction** | Removed - unclear gap |
| **A2A Protocol Premature** | Removed - we don't use ADK/LangGraph |

---

## Why This Approach

1. **Phase 0 Investigation** - Don't blindly enable disabled features; find WHY disabled first
2. **Memory versioning** - Highest-impact gap—without it, no audit trail, no rollback
3. **Standard handoffs** - Reduce custom code—OpenAI/Google converged on consensus
4. **Security first** - MCP secret scanning is critical (13.4% of skills have issues)
5. **Feature flag flips** - Leverage existing work—Mem0/graph integrations exist but disabled
6. **Production hardening** - Comes AFTER core—SLOs matter only when fundamentals work

---

## Watch Out For

- **MCP Server Quality Variance**: MCP became standard (97M+ downloads) but server quality varies
- **Framework Convergence**: OpenAI Agents SDK and Google ADK converging—don't over-commit
- **Local vs Cloud Trade-offs**: GGUF delivers 14x speed but lacks context window—hybrid routing essential
- **Disabled Features**: Were disabled for a reason—investigate before enabling

---

## Diminishing Returns Threshold

After completing Phases 1-4, the following show diminishing returns:

- ✅ Additional category consolidation (already done 9→5)
- ✅ More agents (11 sufficient for current scope)
- ✅ Additional MCP servers (14 adequate)
- ✅ Fine-tuning local models (GGUF already optimized)

**Next focus after diminishing returns**: 
- Phase 5+ advanced memory (procedural, episodic)
- Agent specializations (tester, security, devops)
- New frameworks (Orloj, Mastra) - only if needed

---

## Implementation Timeline

```
Phase 0 (Investigation):  Week 1-2
Phase 1 (Memory):         Week 3-6
Phase 2 (Agents):         Week 7-8  
Phase 3 (Enable):         Week 9-10
Phase 4 (Production):     Week 11-12

Total: ~12 weeks (reduced from original)
```

---

## Quick Start

```bash
# Phase 0: Investigation FIRST
# → Investigate WHY features are disabled
# → Add implementation paths to each feature
# → Define acceptance criteria

# Phase 1: Memory improvements
# → Implement memory versioning (with paths)
# → Add conflict resolution
# → Wire reranking layer

# Phase 2: Agent coordination  
# → Standard handoff primitives (validate OMO first)
# → Token budgets

# Phase 3: Feature enablement (after investigation)
# → Enable tiered memory (if stable)
# → Enable graph memory
# → Enable context caching

# Phase 4: Production + Security
# → Observability & SLOs
# → MCP Secret Scanning (ADDED - critical security)
```

---

## References

- **Librarian**: Multi-agent frameworks, memory systems, security scanning
- **Oracle**: Prioritization, dependencies, anti-patterns
- **Metis**: 18 hidden issues (ML tables, shadow mode, rollback)
- **Momus**: Critical flaws (implementation details, QA criteria)
- **Explore**: Codebase patterns (disabled features, technical debt)
- **Current system**: README.md, N-Xyme_MIND_Architecture.md
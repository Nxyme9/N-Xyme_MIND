# N-Xyme_MIND Self-Learning System — Full Master Plan

> **Generated**: 2026-04-05
> **Sources**: Metis (Plan Consultant), Momus (Plan Critic), Oracle (Architecture Review), Librarian (Research)
> **Status**: Ready for Execution

---

## Executive Summary

**Current State**: 39+ Python modules, ~100 real memories (not 3,676), 96.1% embedding coverage, 8 fully implemented but ORPHANED modules, knowledge graph with 54 entities + 108 relations.

**Goal**: Transform from "vector search with extras" to "true self-learning memory system" matching Mem0/Letta/Zep standards.

**Approach**: 6 phases, 20 tasks, ~40 hours total. Wire existing orphaned modules (don't rewrite), clean data first, add graph+vector hybrid retrieval, implement async self-evaluation.

**Key Insight**: N-Xyme_MIND has MORE implemented code than Mem0/Letta/Zep in some areas (forgetting curves, sleep cycles, prompt evolution), but ZERO integration. The gap is architecture and wiring, not code volume.

---

## Phase 0: Data Audit & Cleaning (MANDATORY, 2-3 days)

**Why First**: Momus identified that "3,676 memories" is inflated — only ~100 are real memories. Auto-extracting entities from dirty data will poison the knowledge graph.

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T0.1**: Classify all 5,859 migration records by type | `data/`, new audit script | Hephaestus | 4 hrs | None |
| **T0.2**: Purge test/smoke/benchmark data | `data/`, cleanup script | Hephaestus | 2 hrs | T0.1 |
| **T0.3**: Score remaining memories for quality | New `quality_scorer.py` | Hephaestus | 2 hrs | T0.2 |
| **T0.4**: Backup current knowledge graph | `context/memory/knowledge_graph.json` | Sisyphus-Junior | 30 min | None |
| **T0.5**: Delete duplicate files (`src/knowledge_graph.py`, `src/unified_memory.py`) | `src/` | Sisyphus-Junior | 10 min | None |

**Success Metrics**:
- [ ] All 5,859 records classified (memory, message, metric, action, block, friction)
- [ ] Test/smoke data purged
- [ ] Quality scores assigned to remaining memories
- [ ] Knowledge graph backed up
- [ ] Duplicate files deleted

**Agent Delegation**:
```
T0.1: task(subagent_type="hephaestus", load_skills=[], run_in_background=false, prompt="...")
T0.2: task(subagent_type="hephaestus", load_skills=[], run_in_background=false, prompt="...")
T0.3: task(subagent_type="hephaestus", load_skills=[], run_in_background=false, prompt="...")
T0.4: task(subagent_type="sisyphus-junior", load_skills=[], run_in_background=false, prompt="...")
T0.5: task(subagent_type="sisyphus-junior", load_skills=[], run_in_background=false, prompt="...")
```

---

## Phase 1: Foundation (1 day) — Highest ROI

**Why First**: Immediate retrieval quality improvements with minimal code changes. All features behind config flags.

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T1.1**: Add `GraphConnector` to router | `src/memory/connectors.py`, `src/memory/registry.py` | Hephaestus | 30 min | Phase 0 |
| **T1.2**: Wire preference_model reranking | `src/memory/router.py` | Hephaestus | 1 hr | Phase 0 |
| **T1.3**: Wire forgetting curve as staleness detector | `src/memory/router.py`, `src/memory/core/forgetting.py` | Hephaestus | 2 hrs | Phase 0 |
| **T1.4**: Enable learning config flags | `src/memory/learning_config.py`, `.sisyphus/learning-config.json` | Sisyphus-Junior | 30 min | Phase 0 |

**Success Metrics**:
- [ ] `GraphConnector` returns entity/relationship search results
- [ ] Preference model reranking improves search relevance by 15%+
- [ ] Forgetting curve applied to retrieval scores
- [ ] Config flags toggle features ON/OFF without code changes
- [ ] All existing tests pass

**Agent Delegation**:
```
T1.1: task(subagent_type="hephaestus", load_skills=[], run_in_background=false, prompt="Add GraphConnector class to src/memory/connectors.py that implements MemoryConnector ABC. Search knowledge_graph.json for entities matching query. Register in registry.py _initialize_sources(). Follow existing connector patterns.")
T1.2: task(subagent_type="hephaestus", load_skills=[], run_in_background=false, prompt="Wire preference_model reranking into src/memory/router.py search() pipeline. Import PreferenceModel, call rerank_results() on search results before returning. Ensure metadata['result_type'] is populated. Follow Oracle's fix pattern.")
T1.3: task(subagent_type="hephaestus", load_skills=[], run_in_background=false, prompt="Wire forgetting curve into src/memory/router.py retrieval pipeline. Import ebbinghaus_retrievability() from core/forgetting.py. Apply decay to search result scores based on memory age. Add forgetting_half_life_days to learning_config.py.")
T1.4: task(subagent_type="sisyphus-junior", load_skills=[], run_in_background=false, prompt="Add new config keys to src/memory/learning_config.py: graph_retrieval_enabled, rerank_enabled, forgetting_enabled, auto_extract_enabled, self_eval_enabled, sleep_enabled, compaction_enabled. Create .sisyphus/learning-config.json with Phase 1 flags enabled, rest OFF.")
```

---

## Phase 2: Knowledge Graph + Hybrid Retrieval (2-3 days)

**Why Second**: Biggest leverage point. Transforms system from "vector search with extras" to "true knowledge graph" like Mem0.

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T2.1**: Auto-extract entities from CLEANED memories | `src/memory/entity_extractor.py`, `src/memory/knowledge_graph.py` | Hephaestus | 4 hrs | Phase 1 |
| **T2.2**: Add RRF fusion for graph+vector retrieval | `src/memory/router.py`, `src/memory/file_rrf.py` | Hephaestus | 1 hr | T2.1 |
| **T2.3**: Wire hierarchical memory tiers | `src/memory/router.py`, `src/memory/core/hierarchical.py` | Hephaestus | 3 hrs | Phase 1 |
| **T2.4**: Add `result_type` metadata to all connectors | `src/memory/connectors.py` (all connectors) | Hephaestus | 1 hr | Phase 1 |

**Success Metrics**:
- [ ] Entity extraction processes cleaned memories with 80%+ precision
- [ ] Knowledge graph grows from 54 to 200+ entities
- [ ] RRF fusion combines vector + graph results
- [ ] Hierarchical memory tiers route queries correctly
- [ ] All connectors populate `metadata["result_type"]`

**Agent Delegation**:
```
T2.1: task(subagent_type="hephaestus", load_skills=[], run_in_background=false, prompt="Create src/memory/entity_extractor.py that batch-extracts entities/relationships from cleaned memories. Use KnowledgeGraph.extract_from_content(). Process in batches of 100. Run on 100-memory sample first, review output, then full batch. Add confidence threshold (0.8+).")
T2.2: task(subagent_type="hephaestus", load_skills=[], run_in_background=false, prompt="Add hybrid_search() method to src/memory/router.py combining vector + graph results with RRF fusion. Use k=60 for RRF. Return UnifiedMemoryResult with sources_queried=['vector', 'knowledge_graph']. Follow Oracle's implementation pattern.")
T2.3: task(subagent_type="hephaestus", load_skills=[], run_in_background=false, prompt="Wire hierarchical memory tiers into src/memory/router.py. Import HierarchicalMemory from core/hierarchical.py. Add _route_to_tier() method. Use existing tier implementations as backends, don't replace them. Add tier thresholds to learning_config.py.")
T2.4: task(subagent_type="hephaestus", load_skills=[], run_in_background=false, prompt="Add metadata['result_type'] to all MemoryResult objects in src/memory/connectors.py. Set based on content type: 'code' for code files, 'doc' for documentation, 'config' for config files, 'memory' for memories, 'entity' for knowledge graph entities. This enables preference model reranking.")
```

---

## Phase 3: Self-Evaluation + Consolidation (1-2 days)

**Why Third**: Adds self-improvement capability. Async LLM judge avoids latency issues.

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T3.1**: Add LLM self-evaluation (async) | `src/memory/self_evaluator.py` | Hephaestus | 3 hrs | Phase 2 |
| **T3.2**: Wire sleep_cycle with cron trigger | `src/memory/daemon.py`, `src/memory/core/sleep_cycle.py` | Hephaestus | 2 hrs | Phase 2 |
| **T3.3**: Wire compaction with LLM summarization | `src/memory/core/compaction.py`, `src/memory/mcp_server.py` | Hephaestus | 2 hrs | Phase 2 |

**Success Metrics**:
- [ ] Self-evaluator scores memory correctness asynchronously
- [ ] Sleep cycle runs on configurable interval (default: 2 hours)
- [ ] Session compaction produces meaningful summaries
- [ ] All features toggleable via config flags

**Agent Delegation**:
```
T3.1: task(subagent_type="hephaestus", load_skills=[], run_in_background=false, prompt="Create src/memory/self_evaluator.py that asynchronously evaluates memory correctness using LLM judge. Use Ollama (nomic-embed-text or llama3.2:3b). Cache judgment scores. Only evaluate new/changed memories, not every retrieval. Add evaluate_memory() MCP tool.")
T3.2: task(subagent_type="hephaestus", load_skills=[], run_in_background=false, prompt="Wire sleep_cycle into src/memory/daemon.py. Import SleepCycle from core/sleep_cycle.py. Add cron trigger using learning_config.sleep_cycle_interval_hours (default: 2). Register handlers for JOURNAL, CONSOLIDATE, RECALL phases. Add trigger_consolidation MCP tool.")
T3.3: task(subagent_type="hephaestus", load_skills=[], run_in_background=false, prompt="Wire compaction into src/memory/router.py and mcp_server.py. Import SessionCompactor from core/compaction.py. Add LLM summarization via Ollama. Add compact_session() method and MCP tool. Add fallback to default summarizer when LLM unavailable.")
```

---

## Phase 4: Adaptive Learning (2-3 days)

**Why Fourth**: Highest risk phase. Replaces hardcoded logic with actual learning.

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T4.1**: Replace priority_engine IF/THEN with self_learning | `src/memory/priority_engine.py`, `src/learning/self_learning.py` | Hephaestus | 5 hrs | Phase 3 |
| **T4.2**: Wire prompt_evolution with human approval | `src/learning/prompt_evolution.py`, `src/memory/mcp_server.py` | Hephaestus | 2 hrs | Phase 3 |
| **T4.3**: Wire skill_lifecycle | `src/learning/skill_lifecycle.py`, `src/memory/mcp_server.py` | Hephaestus | 2 hrs | Phase 3 |

**Success Metrics**:
- [ ] Priority engine adapts weights based on usage patterns (not hardcoded)
- [ ] Prompt evolution requires human approval before deployment
- [ ] Skill lifecycle tracks state transitions
- [ ] A/B test framework for comparing old vs new behavior

**Agent Delegation**:
```
T4.1: task(subagent_type="hephaestus", load_skills=[], run_in_background=false, prompt="Replace hardcoded IF/THEN logic in src/memory/priority_engine.py with SelfLearner adaptation loop from src/learning/self_learning.py. Keep hardcoded weights as fallback. Add adaptive_priority_enabled config flag. Run A/B test for 1 week before full rollout. Add adapt_priority_weights() method.")
T4.2: task(subagent_type="hephaestus", load_skills=[], run_in_background=false, prompt="Wire prompt_evolution into src/memory/mcp_server.py. Import PromptWizard from learning/prompt_evolution.py. Add evolve_prompt MCP tool with human approval gate. Add rollback capability. Track real-world performance of evolved prompts.")
T4.3: task(subagent_type="hephaestus", load_skills=[], run_in_background=false, prompt="Wire skill_lifecycle into src/memory/mcp_server.py. Import SkillLifecycleManager from learning/skill_lifecycle.py. Add manage_skill MCP tool. Track skill state transitions. Integrate with existing skill registry.")
```

---

## Phase 5: Advanced Features (1-2 days)

**Why Last**: Lowest ROI, highest complexity. Only implement after core system is stable.

| Task | File(s) | Agent | Effort | Dependencies |
|------|---------|-------|--------|--------------|
| **T5.1**: Wire dossier_system | `src/memory/core/dossier_system.py`, `src/memory/mcp_server.py` | Hephaestus | 1 hr | Phase 4 |
| **T5.2**: Add dynamic forgetting with staleness detection | `src/memory/core/forgetting.py`, `src/memory/learning_config.py` | Hephaestus | 3 hrs | Phase 4 |

**Success Metrics**:
- [ ] Dossier system generates causal chain summaries
- [ ] Dynamic forgetting adjusts half-life based on usage patterns
- [ ] Staleness detection identifies outdated high-relevance memories
- [ ] Unified retention policy (no conflicts with existing TTL)

**Agent Delegation**:
```
T5.1: task(subagent_type="hephaestus", load_skills=[], run_in_background=false, prompt="Wire dossier_system into src/memory/mcp_server.py. Import DossierSystem from core/dossier_system.py. Add generate_dossier MCP tool. Implement causal chain summaries from memory events. Add causal inference logic.")
T5.2: task(subagent_type="hephaestus", load_skills=[], run_in_background=false, prompt="Add dynamic forgetting with staleness detection to src/memory/core/forgetting.py. Adjust half-life based on retrieval frequency. Detect staleness for high-relevance memories. Unify with existing TTL system (feedback_ttl_days, mandatory_retention_days). Add staleness_threshold_days config.")
```

---

## Dependency Graph

```
Phase 0: Data Audit & Cleaning (2-3 days)
├── T0.1: Classify records ──────────────────────────────────────────┐
├── T0.2: Purge test data ───────────────────────────────────────────┤
├── T0.3: Score quality ─────────────────────────────────────────────┤
├── T0.4: Backup knowledge graph ────────────────────────────────────┤
└── T0.5: Delete duplicates ─────────────────────────────────────────┘
    ↓ (all must pass before Phase 1)

Phase 1: Foundation (1 day)
├── T1.1: Add GraphConnector ────────────────────────────────────────┐
├── T1.2: Wire preference_model ─────────────────────────────────────┤
├── T1.3: Wire forgetting curve ─────────────────────────────────────┤
└── T1.4: Enable config flags ───────────────────────────────────────┘
    ↓ (all must pass before Phase 2)

Phase 2: Knowledge Graph + Hybrid Retrieval (2-3 days)
├── T2.1: Auto-extract entities ─────────────────────────────────────┐
├── T2.2: Add RRF fusion ────────────────────────────────────────────┤
├── T2.3: Wire hierarchical tiers ───────────────────────────────────┤
└── T2.4: Add result_type metadata ──────────────────────────────────┘
    ↓ (all must pass before Phase 3)

Phase 3: Self-Evaluation + Consolidation (1-2 days)
├── T3.1: Add LLM self-evaluation ───────────────────────────────────┐
├── T3.2: Wire sleep_cycle ──────────────────────────────────────────┤
└── T3.3: Wire compaction ───────────────────────────────────────────┘
    ↓ (all must pass before Phase 4)

Phase 4: Adaptive Learning (2-3 days)
├── T4.1: Replace priority engine ───────────────────────────────────┐
├── T4.2: Wire prompt_evolution ─────────────────────────────────────┤
└── T4.3: Wire skill_lifecycle ──────────────────────────────────────┘
    ↓ (all must pass before Phase 5)

Phase 5: Advanced Features (1-2 days)
├── T5.1: Wire dossier_system ───────────────────────────────────────┐
└── T5.2: Add dynamic forgetting ────────────────────────────────────┘

Parallel Opportunities:
- T0.4, T0.5 can run in parallel with T0.1-T0.3
- T1.1, T1.2, T1.3, T1.4 can run in parallel (different files)
- T2.1, T2.2, T2.3, T2.4 can run in parallel (different files)
- T3.1, T3.2, T3.3 can run in parallel (different files)
- T4.1, T4.2, T4.3 can run in parallel (different files)
- T5.1, T5.2 can run in parallel (different files)
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation | Contingency |
|------|-------------|--------|------------|-------------|
| **Noisy entity extraction** | High | Medium | Confidence threshold (0.8+), sample 100 first | Fall back to keyword extraction |
| **Module API incompatibility** | Medium | High | Read all 9 modules before wiring, write adapter layer | Create wrapper classes |
| **Performance degradation** | Medium | High | Benchmark before/after each phase, set latency budgets | Disable features via config flags |
| **Priority engine instability** | High | High | Keep hardcoded weights as fallback, A/B test for 1 week | Config flag `adaptive_priority_enabled` defaults OFF |
| **Graph explosion** | Low | Medium | Set entity/relationship limits, implement deduplication | Run batch deduplication script |
| **Forgetting curve too aggressive** | Medium | Medium | Start with conservative half-life (30 days), monitor | Adjust `mandatory_retention_days` config |
| **Test coverage gaps** | Medium | Medium | TDD approach — write tests before implementation | Add integration tests after each phase |

---

## Atomic Commit Strategy

### Commit Philosophy
- **One commit per task** — each commit is independently testable
- **Tests first** — commit tests before implementation (TDD)
- **Feature flags** — all new features behind config flags (OFF by default)
- **No breaking changes** — existing functionality must continue working

### Commit Sequence (30 commits total)

```
Phase 0:
commit 1: "test: add data audit tests"
commit 2: "feat: add data classification script"
commit 3: "feat: purge test/smoke/benchmark data"
commit 4: "feat: add memory quality scorer"
commit 5: "chore: backup knowledge graph"
commit 6: "chore: delete duplicate files (src/knowledge_graph.py, src/unified_memory.py)"

Phase 1:
commit 7: "test: add GraphConnector tests"
commit 8: "feat: add GraphConnector to connectors.py + register in registry.py"
commit 9: "test: add preference model integration tests"
commit 10: "feat: wire preference_model reranking into router"
commit 11: "test: add forgetting curve integration tests"
commit 12: "feat: wire forgetting curve into retrieval pipeline"
commit 13: "feat: enable learning config flags for Phase 1"

Phase 2:
commit 14: "test: add entity extractor tests"
commit 15: "feat: add LLM-based entity extraction pipeline"
commit 16: "feat: batch process cleaned memories for entity extraction"
commit 17: "test: add hybrid retrieval tests"
commit 18: "feat: add graph+vector hybrid retrieval with RRF fusion"
commit 19: "test: add hierarchical memory routing tests"
commit 20: "feat: wire hierarchical memory tiers into router"
commit 21: "feat: add result_type metadata to all connectors"

Phase 3:
commit 22: "test: add self-evaluator tests"
commit 23: "feat: add LLM self-evaluation for memory correctness (async)"
commit 24: "test: add sleep cycle integration tests"
commit 25: "feat: wire sleep_cycle for background consolidation with cron trigger"
commit 26: "test: add compaction integration tests"
commit 27: "feat: wire compaction for session summarization with LLM"

Phase 4:
commit 28: "test: add adaptive priority engine tests"
commit 29: "feat: replace hardcoded priority weights with self-learning adaptation"
commit 30: "test: add prompt evolution integration tests"
commit 31: "feat: wire prompt_evolution into MCP server with human approval"
commit 32: "test: add skill lifecycle integration tests"
commit 33: "feat: wire skill_lifecycle into MCP server"

Phase 5:
commit 34: "test: add dossier system integration tests"
commit 35: "feat: wire dossier_system for causal summaries"
commit 36: "test: add dynamic forgetting tests"
commit 37: "feat: add dynamic forgetting with staleness detection"

Integration:
commit 38: "test: add end-to-end integration tests for all phases"
commit 39: "docs: update README with self-learning system documentation"
commit 40: "chore: run full test suite + health checks"
```

### Branch Strategy
```
main
├── feature/self-learning-phase-0 (T0.1-T0.5)
├── feature/self-learning-phase-1 (T1.1-T1.4)
├── feature/self-learning-phase-2 (T2.1-T2.4)
├── feature/self-learning-phase-3 (T3.1-T3.3)
├── feature/self-learning-phase-4 (T4.1-T4.3)
└── feature/self-learning-phase-5 (T5.1-T5.2)
```

### Rollback Strategy
- Each phase has a **master config flag** that disables all features in that phase
- Rollback = flip config flag to OFF + revert last phase's commits
- Database migrations are backward-compatible (no destructive changes)

---

## TDD-Oriented Planning

### Test File Structure
```
tests/
├── test_self_learning.py          # Existing — extend with new test classes
├── test_data_audit.py             # New — T0.1-T0.3
├── test_entity_extractor.py       # New — T2.1
├── test_self_evaluator.py         # New — T3.1
├── test_prompt_evolution.py       # New — T4.2
└── test_skill_lifecycle.py        # New — T4.3
```

### Test Classes to Add
```python
# In tests/test_self_learning.py:
class TestGraphConnector:
    """Tests for T1.1: GraphConnector integration"""

class TestForgettingIntegration:
    """Tests for T1.3: Forgetting curve wired into retrieval"""

class TestHybridRetrieval:
    """Tests for T2.2: Graph+vector hybrid retrieval"""

class TestHierarchicalRouting:
    """Tests for T2.3: Hierarchical memory tier routing"""

class TestSleepCycleIntegration:
    """Tests for T3.2: Sleep cycle background consolidation"""

class TestCompactionIntegration:
    """Tests for T3.3: Session compaction"""

class TestDynamicForgetting:
    """Tests for T5.2: Dynamic forgetting with staleness detection"""

class TestDossierIntegration:
    """Tests for T5.1: Dossier system integration"""

class TestEndToEnd:
    """Integration tests for full self-learning pipeline"""
```

### Test Patterns
```python
# Pattern 1: Unit test with mock LLM
@patch('src.memory.entity_extractor.call_llm')
def test_extract_entities_from_memory(mock_llm):
    mock_llm.return_value = {"entities": [...], "relationships": [...]}
    extractor = EntityExtractor()
    result = extractor.extract("test memory content")
    assert len(result.entities) > 0

# Pattern 2: Integration test with temp database
def test_forgetting_curve_applied_to_retrieval(tmp_path):
    router = MemoryRouter(db_path=tmp_path / "test.db")
    router.add_memory("test content", metadata={"created_at": "2025-01-01"})
    results = router.search("test")
    assert all(0 <= r.score <= 1 for r in results)

# Pattern 3: End-to-end test
def test_full_self_learning_pipeline(tmp_path):
    # 1. Add memory
    # 2. Trigger extraction
    # 3. Verify entities created
    # 4. Trigger retrieval
    # 5. Verify reranking applied
    # 6. Trigger sleep cycle
    # 7. Verify consolidation happened
    pass
```

---

## Success Metrics

### Quantitative Metrics
| Metric | Current | Target (Phase 1) | Target (Phase 3) | Target (Phase 5) |
|--------|---------|------------------|------------------|------------------|
| Knowledge graph entities | 54 | 200+ | 500+ | 1000+ |
| Knowledge graph relationships | 108 | 200+ | 500+ | 2000+ |
| Retrieval accuracy (LLM judge) | N/A | 40% | 55% | 68%+ (Mem0 level) |
| Retrieval latency (P95) | N/A | <3s | <2.5s | <2s |
| Memory coverage | 96.1% | 97% | 98% | 99%+ |
| Reranking improvement | N/A | +15% relevance | +25% relevance | +35% relevance |
| Session consolidation rate | 0% | 50% | 80% | 95% |

### Verification Commands
```bash
# Run all tests
pytest tests/test_self_learning.py -v

# Check knowledge graph stats
python3 -c "import json; data=json.load(open('context/memory/knowledge_graph.json')); print(f'Entities: {len(data[\"entities\"])}, Relationships: {len(data[\"relationships\"])}')"

# Run health checks
bash bin/health-l0-blink.sh
bash bin/health-l1-pulse.sh
bash bin/health-l2-vitals.sh

# Test MCP server
python3 -c "from src.memory.mcp_server import app; print('MCP server loads OK')"

# Check learning config
python3 src/memory/learning_config.py
```

---

## Effort Estimates

| Phase | Tasks | Estimated Hours | Calendar Days | Parallelizable |
|-------|-------|-----------------|---------------|----------------|
| **Phase 0: Data Audit** | T0.1-T0.5 | 8-10 hours | 1-2 days | ✅ Yes |
| **Phase 1: Foundation** | T1.1-T1.4 | 4-6 hours | 1 day | ✅ Yes |
| **Phase 2: KG + Hybrid** | T2.1-T2.4 | 9-12 hours | 2 days | ✅ Yes |
| **Phase 3: Self-Eval** | T3.1-T3.3 | 7-9 hours | 1-2 days | ✅ Yes |
| **Phase 4: Adaptive** | T4.1-T4.3 | 9-12 hours | 2-3 days | ✅ Yes |
| **Phase 5: Advanced** | T5.1-T5.2 | 4-6 hours | 1 day | ✅ Yes |
| **Integration Testing** | All phases | 4-6 hours | 1 day | ❌ Sequential |
| **Documentation** | All phases | 2-4 hours | 0.5 days | ❌ Sequential |
| **TOTAL** | 20 tasks | **47-65 hours** | **9-13 days** | |

---

## Directives for Execution

### Core Directives
- **MUST**: Wire existing modules — DO NOT rewrite self_learning.py, hierarchical.py, forgetting.py, etc.
- **MUST**: All features behind config flags (OFF by default)
- **MUST**: TDD approach — tests before implementation for every task
- **MUST**: Follow existing patterns in `src/memory/router.py` for new method signatures
- **MUST**: Use `learning_config.py` for all configuration — no hardcoded values
- **MUST NOT**: Change existing module APIs without adapter layer
- **MUST NOT**: Break existing MCP server tools
- **MUST NOT**: Remove or modify existing tests
- **PATTERN**: Follow `src/memory/router.py:MemoryRouter` class structure for new integration methods
- **TOOL**: Use `lsp_find_references` before modifying any shared interfaces
- **TOOL**: Use `lsp_diagnostics` after each file change to catch type errors early

### QA/Acceptance Criteria Directives
- **MUST**: Write acceptance criteria as executable commands
- **MUST**: Every task has test coverage (unit + integration)
- **MUST**: Run `pytest tests/test_self_learning.py -v` after each phase
- **MUST**: Verify knowledge graph growth
- **MUST**: Run health checks after each phase
- **MUST NOT**: Mark task complete without passing tests
- **MUST NOT**: Enable config flags until tests pass

### Phase-Specific QA Commands
```bash
# Phase 0 QA
python3 scripts/data_audit.py  # Verify classification
python3 -c "import json; data=json.load(open('context/memory/knowledge_graph.json')); print(f'Backup created')"

# Phase 1 QA
pytest tests/test_self_learning.py::TestGraphConnector -v
pytest tests/test_self_learning.py::TestForgettingIntegration -v
python3 src/memory/learning_config.py  # Verify config loads

# Phase 2 QA
pytest tests/test_entity_extractor.py -v
pytest tests/test_self_learning.py::TestHybridRetrieval -v
python3 -c "import json; data=json.load(open('context/memory/knowledge_graph.json')); assert len(data['entities']) >= 200"

# Phase 3 QA
pytest tests/test_self_evaluator.py -v
pytest tests/test_self_learning.py::TestSleepCycleIntegration -v

# Phase 4 QA
pytest tests/test_self_learning.py::TestPriorityEngine -v  # Verify adaptive weights
pytest tests/test_prompt_evolution.py -v

# Phase 5 QA
pytest tests/test_self_learning.py::TestDynamicForgetting -v

# Full Suite QA
pytest tests/ -v --tb=short
bash bin/health-l2-vitals.sh
```

---

## What to CUT (Per Momus + Oracle)

| Cut Item | Reason | Saved |
|----------|--------|-------|
| `src/knowledge_graph.py` | Duplicate of `src/memory/knowledge_graph.py` | 0 hrs (just delete) |
| `src/unified_memory.py` | Legacy HTTP server, replaced by MCP | 0 hrs (just delete) |
| Full 3,676 memory extraction | Only ~100 real memories exist, clean first | 3-4 hrs |
| LLM judge on every retrieval | Performance killer, do async instead | 2 hrs |
| Sleep cycle (initial) | No trigger mechanism, lowest value | 2-3 hrs |
| Prompt evolution (initial) | Self-evaluating, no real feedback loop | 1-2 hrs |
| Dynamic forgetting (initial) | Conflicts with existing TTL | 1 hr |

**Total savings: 9-12 hours** redirected to data cleaning and integration architecture.

---

## Execution Checklist

### Pre-Flight (Before Starting)
- [ ] Read all 9 orphaned modules thoroughly (understand their APIs)
- [ ] Run existing test suite: `pytest tests/test_self_learning.py -v`
- [ ] Run health checks: `bash bin/health-l0-blink.sh && bash bin/health-l1-pulse.sh`
- [ ] Backup current state: `git stash` or create branch
- [ ] Verify Ollama is running (needed for LLM extraction)
- [ ] Verify all agent models are working (no kimi/gemini references)

### Per-Phase Checklist
- [ ] Write tests first (TDD)
- [ ] Implement minimum code to pass tests
- [ ] Run full test suite
- [ ] Run health checks
- [ ] Update config flags if needed
- [ ] Commit with descriptive message
- [ ] Verify no regressions in MCP server

### Post-Implementation
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Run health checks: `bash bin/health-l2-vitals.sh`
- [ ] Verify knowledge graph growth
- [ ] Test MCP server tools manually
- [ ] Update documentation
- [ ] Create summary of changes

---

## Recommended Approach

**Start with Phase 0 (Data Audit & Cleaning)** — it's the foundation everything else depends on. Without clean data, entity extraction will produce garbage.

**Then Phase 1 (Foundation)** — highest ROI, lowest risk. Wire GraphConnector, preference_model, forgetting curve. Immediate retrieval quality improvements.

**Then Phase 2 (Knowledge Graph + Hybrid Retrieval)** — biggest leverage point. Auto-extracting entities and adding graph+vector hybrid retrieval transforms the system.

**Phase 3-5 can proceed in parallel waves** once Phase 2 is stable, since they touch different modules.

**Critical success factor**: The config flag system is your safety net. Every feature MUST be toggleable. If something breaks, flip the flag OFF — no code rollback needed.

---

*This masterplan synthesizes insights from Metis (Plan Consultant), Momus (Plan Critic), Oracle (Architecture Review), and Librarian (Research). Total: 20 tasks across 6 phases, ~47-65 hours, 9-13 calendar days.*

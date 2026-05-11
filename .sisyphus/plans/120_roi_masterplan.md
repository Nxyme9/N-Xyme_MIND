# N-Xyme MIND - 120 ROI Optimizations Masterplan

## Executive Summary

**Total Optimizations**: 120 across 6 phases  
**Current State**: ~50% already optimized  
**Gap Count**: ~60 items need work  
**Estimated Implementation**: 5-6 weeks

---

## Phase Breakdown & Priority Matrix

### Phase 1: Pre-Dispatch Optimization (15 items)
| # | File | Status | Action | Est. Effort |
|---|------|--------|--------|-------------|
| 1.1 | memory_injector.py | ✅ OPTIMIZED | LRU + Redis-backed cache exists | DONE |
| 1.2 | fingerprint_activator.py | ✅ OPTIMIZED | Parallel ThreadPoolExecutor exists | DONE |
| 1.3 | pre_warm.py | ✅ OPTIMIZED | Predictive pre-warm exists | DONE |
| 1.4 | role_synthesizer.py | ✅ OPTIMIZED | SQLite-backed agent selection cache | DONE |
| 1.5 | contribution_analyzer.py | ✅ OPTIMIZED | Async DAG-Shapley implemented | DONE |
| 1.6 | unified_pipeline.py | ✅ OPTIMIZED | Context skip logic exists | DONE |
| 1.7 | mcp_pipeline.py | ❌ GAP | Add connection pooling | 1 day |
| 1.8 | token_budget.py | ✅ OPTIMIZED | Pre-calculate budget exists | DONE |
| 1.9 | prompt_assembler.py | ✅ OPTIMIZED | Template caching exists | DONE |
| 1.10 | context_loader.py | ✅ OPTIMIZED | Lazy load context modules | DONE |
| 1.11 | module_registry.py | ⚠️ PARTIAL | Eager load critical modules only | 0.5 day |
| 1.12 | tool_cache.py | ✅ OPTIMIZED | TTL-based tool cache exists | DONE |
| 1.13 | agent_prompt.py | ✅ OPTIMIZED | Prompt fragment caching | DONE |
| 1.14 | two_stage_router.py | ✅ OPTIMIZED | L1 cache exists | DONE |
| 1.15 | delegation_optimizer.py | ✅ OPTIMIZED | Pre-compute delegation patterns | DONE |

**Phase 1 Remaining**: 2 items (1.7, 1.11)

---

### Phase 2: Execution Optimization (20 items) - HIGHEST ROI
| # | File | Status | Action | Est. Effort |
|---|------|--------|--------|-------------|
| 2.1 | agent_loop.py | ✅ OPTIMIZED | Async agent execution | DONE |
| 2.2 | streaming_executor.py | ✅ OPTIMIZED | Stream results incrementally | DONE |
| 2.3 | react_agent.py | ⚠️ PARTIAL | Remove duplicate code blocks | 0.5 day |
| 2.4 | self_healer.py | ✅ OPTIMIZED | Async healing | DONE |
| 2.5 | circuit_breaker.py | ✅ OPTIMIZED | Fast-fail paths | DONE |
| 2.6 | task_watchdog.py | ✅ OPTIMIZED | Non-blocking watchdog | DONE |
| 2.7 | resilience_middleware.py | ❌ GAP | Convert to async (time.sleep→asyncio.sleep) | 1 day |
| 2.8 | tool_call_collector.py | ✅ OPTIMIZED | Batch collection | DONE |
| 2.9 | subagent_isolation.py | ✅ OPTIMIZED | Async isolation | DONE |
| 2.10 | workspace_manager.py | ⚠️ PARTIAL | Add lazy loading | 0.5 day |
| 2.11 | queue_service.py | ❌ GAP | Convert to async (deque→asyncio.Queue) | 1 day |
| 2.12 | planning_reasoning.py | ✅ OPTIMIZED | Cache reasoning traces | DONE |
| 2.13 | reflexion_agent.py | ✅ OPTIMIZED | Async reflection | DONE |
| 2.14 | tool_awareness.py | ✅ OPTIMIZED | Async tool metadata | DONE |
| 2.15 | focus_manager.py | ✅ OPTIMIZED | Async focus transitions | DONE |
| 2.16 | lifecycle.py | ⚠️ PARTIAL | Move asyncio import to top | 0.5 day |
| 2.17 | tracing.py | ✅ OPTIMIZED | Async trace collection | DONE |
| 2.18 | event_bus.py | ❌ GAP | Convert to async pub/sub | 1 day |
| 2.19 | agent_coordinator.py | ⚠️ PARTIAL | Add async support | 0.5 day |
| 2.20 | reflexion_pattern.py | ❌ GAP | Convert to async (httpx.AsyncClient) | 1 day |

**Phase 2 Remaining**: 8 items (2.3, 2.7, 2.10, 2.11, 2.16, 2.18, 2.19, 2.20)

---

### Phase 3: Post-Execution Optimization (15 items)
| # | File | Status | Action | Est. Effort |
|---|------|--------|--------|-------------|
| 3.1 | session_memory.py | ❌ GAP | Convert httpx.Client → AsyncClient | 1 day |
| 3.2 | session_archiver.py | ❌ GAP | Convert sync file I/O → aiofiles | 1 day |
| 3.3 | agent_trace.py | ❌ GAP | Add async writes | 0.5 day |
| 3.4 | strategy_snapshots.py | ❌ GAP | Convert SQLite → aiosqlite | 1 day |
| 3.5 | pattern_analyzer.py | ❌ GAP | Convert SQLite → aiosqlite | 1 day |
| 3.6 | pattern_learning.py | ❌ GAP | Convert SQLite → aiosqlite | 1 day |
| 3.7 | decision_ledger.py | ❌ GAP | Convert SQLite → aiosqlite | 1 day |
| 3.8 | tool_validator.py | ✅ OPTIMIZED | Already async | DONE |
| 3.9 | permission_manager.py | ❌ GAP | Convert sync → async | 0.5 day |
| 3.10 | evidence_cortex.py | ❌ GAP | Convert SQLite → aiosqlite | 1 day |
| 3.11 | ai_enhancement.py | ❌ GAP | Convert httpx → AsyncClient | 1 day |
| 3.12 | agent_evaluation.py | ⚠️ PARTIAL | Add persistence | 0.5 day |
| 3.13 | compression.py | ✅ STATELESS | No I/O needed | DONE |
| 3.14 | dependency_resolution.py | ✅ STATELESS | In-memory only | DONE |
| 3.15 | fallback_registry.py | ⚠️ PARTIAL | Add async handler support | 0.5 day |

**Phase 3 Remaining**: 14 items

---

### Phase 4: Infrastructure Optimization (25 items)
| # | File | Status | Action | Est. Effort |
|---|------|--------|--------|-------------|
| 4.1 | mcp_server.py | ✅ OPTIMIZED | Connection pooling exists | DONE |
| 4.2 | api_server.py | ✅ OPTIMIZED | Async HTTP handlers | DONE |
| 4.3 | cli.py | ⚠️ PARTIAL | Add async commands | 1 day |
| 4.4 | web_dashboard.py | ✅ OPTIMIZED | WebSocket updates | DONE |
| 4.5 | dashboard.py | ⚠️ PARTIAL | Async refresh | 0.5 day |
| 4.6 | trigger-guardian | ✅ OPTIMIZED | Async trigger check | DONE |
| 4.7 | catalyst.py | ✅ OPTIMIZED | Async state detection | DONE |
| 4.8 | network_orchestrator.py | ⚠️ PARTIAL | Verify async network | 0.5 day |
| 4.9 | plugin_scanner.py | ⚠️ PARTIAL | Add async discovery | 0.5 day |
| 4.10 | quick_actions.py | ⚠️ PARTIAL | Add async execution | 0.5 day |
| 4.11-4.25 | Various | MIXED | Per-file audit | 5 days |

**Phase 4 Remaining**: ~15 items

---

### Phase 5: Data & Storage Optimization (20 items)
| # | File | Status | Action | Est. Effort |
|---|------|--------|--------|-------------|
| 5.1 | tool_registry.py | ⚠️ PARTIAL | Add SQLite backend | 1 day |
| 5.2-5.3 | agent-framework | ❌ MISSING | Files not found | 2 days |
| 5.4 | agents/registry.py | ⚠️ PARTIAL | Upgrade to SQLite | 1 day |
| 5.5 | agents/pool.py | ⚠️ PARTIAL | Add persistence | 1 day |
| 5.6 | tasks/dispatcher.py | ⚠️ PARTIAL | Add async dispatch | 1 day |
| 5.7 | tasks/router.py | ⚠️ PARTIAL | Add LRU + SQLite | 1 day |
| 5.8 | tasks/lifecycle.py | ⚠️ PARTIAL | Upgrade JSON→SQLite | 1 day |
| 5.9-5.10 | governance | ⚠️ PARTIAL | Add SQLite persistence | 2 days |
| 5.11-5.12 | triggers | ⚠️ PARTIAL | Add async engine | 2 days |
| 5.13 | observability.py | ⚠️ PARTIAL | Add SQLite backend | 1 day |
| 5.14-5.20 | Various | MIXED | Per-file implementation | 5 days |

**Phase 5 Remaining**: ~18 items

---

### Phase 6: Learning & Adaptation (25 items)
| # | File | Status | Action | Est. Effort |
|---|------|--------|--------|-------------|
| 6.1 | nx_brain_mcp | ✅ OPTIMIZED | Batch memory writes | DONE |
| 6.2 | intelligent_router_mcp | ✅ OPTIMIZED | Adaptive weights (Q-Learning) | DONE |
| 6.3 | session-pool-mcp | ✅ OPTIMIZED | Persistent pool | DONE |
| 6.4 | http_gateway.py | ⚠️ PARTIAL | Add connection reuse | 0.5 day |
| 6.5 | tool_categories.py | ✅ STATELESS | Dict lookup | DONE |
| 6.6 | fallback_registry.py | ✅ OPTIMIZED | Fast-fail chain | DONE |
| 6.7 | models/fallback.py | ✅ OPTIMIZED | Async fallback | DONE |
| 6.8 | tools/registry.py | ⚠️ PARTIAL | Add LRU cache | 0.5 day |
| 6.9 | tools/factory.py | ⚠️ PARTIAL | Add async wrapper | 0.5 day |
| 6.10 | tools/errors.py | ✅ STATELESS | No caching needed | DONE |
| 6.11 | tools/search.py | ✅ OPTIMIZED | Cached index | DONE |
| 6.12 | nx-context-mcp | ✅ OPTIMIZED | Async context ops | DONE |
| 6.13 | context7_mcp | ℹ️ EXTERNAL | External service | N/A |
| 6.14-6.16 | memory_core | ✅ OPTIMIZED | Cached/batch retrieval | DONE |
| 6.17-6.19 | infrastructure | ⚠️ PARTIAL | Complete async | 2 days |
| 6.20 | infrastructure/queue | ❌ MISSING | CREATE queue.py | 1 day |
| 6.21-6.22 | src/tui, src/agents | MIXED | Per-file audit | 1 day |

**Phase 6 Remaining**: ~6 items

---

## Implementation Schedule

### Week 1: Phase 2 Critical Fixes (HIGHEST ROI)
- [ ] 2.7 resilience_middleware.py - async conversion
- [ ] 2.11 queue_service.py - async conversion
- [ ] 2.18 event_bus.py - async pub/sub
- [ ] 2.20 reflexion_pattern.py - async httpx
- [ ] 2.3 react_agent.py - remove duplicates
- [ ] 2.16 lifecycle.py - fix asyncio import
- [ ] 2.10 workspace_manager.py - lazy loading
- [ ] 2.19 agent_coordinator.py - add async

### Week 2: Phase 1 Remaining + Phase 3 Start
- [ ] 1.7 mcp_pipeline.py - connection pooling
- [ ] 1.11 module_registry.py - eager load critical
- [ ] 3.1 session_memory.py - async httpx
- [ ] 3.2 session_archiver.py - aiofiles
- [ ] 3.4-3.7 strategy/pattern/decision - aiosqlite
- [ ] 3.11 ai_enhancement.py - async httpx

### Week 3: Phase 3 Completion
- [ ] 3.3 agent_trace.py - async writes
- [ ] 3.9 permission_manager.py - async
- [ ] 3.10 evidence_cortex.py - aiosqlite
- [ ] 3.12 agent_evaluation.py - add persistence
- [ ] 3.15 fallback_registry.py - async handlers

### Week 4: Phase 5 SQLite Migrations (High Impact)
- [ ] 5.1 tool_registry.py - SQLite backend
- [ ] 5.4 agents/registry.py - SQLite
- [ ] 5.5 agents/pool.py - persistence
- [ ] 5.8 tasks/lifecycle.py - SQLite
- [ ] 5.13 observability.py - SQLite
- [ ] All remaining Phase 5 items

### Week 5: Phase 4 + Phase 6 Completion
- [ ] Phase 4 infrastructure async fixes
- [ ] Phase 6 remaining items
- [ ] 6.20 CREATE infrastructure/queue.py

### Week 6: Testing & Verification
- [ ] Run all quality gates
- [ ] Performance benchmarks
- [ ] Integration tests

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Async conversion breaks sync code | HIGH | Test each file individually |
| aiosqlite not available | MEDIUM | Add to requirements.txt |
| 120 items too many to track | HIGH | Use TODO list + weekly standups |
| Missing test coverage | MEDIUM | Add tests alongside each fix |

---

## Success Metrics

- **Phase 2**: 100% async conversion (8 items)
- **Phase 3**: 14/15 async (93%)
- **Phase 5**: 18/20 SQLite (90%)
- **Overall**: 100/120 optimized (83%)
- **Performance**: Target 50% latency reduction on orchestration pipeline

---

## Files to Modify (Summary)

**CREATE**: 
- infrastructure/queue.py

**ASYNC CONVERT** (22 files):
- resilience_middleware.py, queue_service.py, event_bus.py, reflexion_pattern.py
- session_memory.py, session_archiver.py, strategy_snapshots.py, pattern_analyzer.py
- pattern_learning.py, decision_ledger.py, permission_manager.py, evidence_cortex.py
- ai_enhancement.py, agent_trace.py, fallback_registry.py
- cli.py, dashboard.py, network_orchestrator.py, plugin_scanner.py, quick_actions.py

**SQLITE MIGRATE** (18 files):
- tool_registry.py, agents/registry.py, agents/pool.py, tasks/dispatcher.py
- tasks/router.py, tasks/lifecycle.py, governance/policy.py, governance/grounding.py
- triggers/engine.py, observability.py, thinking_effort.py, agent_context_middleware.py
- auto_reflection.py, pre_compact.py, secret_scanner.py, workspace_manager.py, permissions.py

**ENHANCE** (10 files):
- mcp_pipeline.py, module_registry.py, react_agent.py, lifecycle.py
- workspace_manager.py, agent_coordinator.py, http_gateway.py
- tools/registry.py, tools/factory.py, infrastructure/monitoring

---

*Generated: 2026-04-13*  
*Masterplan Version: 1.0*
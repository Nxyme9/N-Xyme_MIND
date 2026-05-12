#!/usr/bin/env python3
"""Full MCP ecosystem test - all tools across all namespaces."""
import sys, traceback, json, asyncio
sys.path.insert(0, '.')

def run_test(name, fn):
    try:
        r = fn()
        s = str(r) if not hasattr(r, '__dict__') else json.dumps(r.__dict__ if hasattr(r, '__dict__') else str(r))
        if len(s) > 100: s = s[:100] + '...'
        print(f'✅ {name}: {s}')
        return (name, True, '')
    except Exception as e:
        print(f'❌ {name}: {type(e).__name__}: {str(e)[:80]}')
        return (name, False, str(e))

print('=' * 70)
print('BRAIN_MCP FULL TOOL TEST - ALL NAMESPACES')
print('=' * 70)

results = []

# ===== MEMORY NAMESPACE =====
print('\n[Memory Namespace]')
from packages.brain_mcp.namespaces.memory import (
    memory_search_memories, memory_memory_write, memory_recall_session,
    memory_find_context, memory_get_memory_stats, memory_auto_write,
    memory_rank_memories
)
for name, fn in [
    ('memory_get_memory_stats', memory_get_memory_stats),
    ('memory_search_memories', lambda: memory_search_memories(query='routing', limit=3)),
    ('memory_memory_write', lambda: memory_memory_write(content='Ralph Loop test - MCP integration verified', kind='episodic', scope='session')),
    ('memory_auto_write', lambda: memory_auto_write(content='Brain MCP integration test complete')),
    ('memory_rank_memories', lambda: memory_rank_memories(query='agent routing', limit=3)),
    ('memory_recall_session', lambda: memory_recall_session(limit=5)),
]:
    results.append(run_test(name, fn))

# ===== CONTEXT NAMESPACE =====
print('\n[Context Namespace]')
from packages.brain_mcp.namespaces.context import (
    context_get_active_context, context_get_product_context,
    context_get_user_context, context_get_constraints,
    context_get_user_profile, context_get_bmad_agents,
    context_get_bmad_workflows, context_get_style_context,
    context_get_archive_context, context_inject_context
)
for name, fn in [
    ('context_get_active_context', context_get_active_context),
    ('context_get_product_context', context_get_product_context),
    ('context_get_user_context', context_get_user_context),
    ('context_get_constraints', context_get_constraints),
    ('context_get_bmad_agents', context_get_bmad_agents),
    ('context_get_bmad_workflows', context_get_bmad_workflows),
    ('context_get_style_context', context_get_style_context),
    ('context_get_archive_context', lambda: context_get_archive_context(query='MCP test', max_sessions=2)),
]:
    results.append(run_test(name, fn))

# ===== LEARNING NAMESPACE =====
print('\n[Learning Namespace]')
from packages.brain_mcp.namespaces.learning import (
    learning_route_task, learning_record_outcome, learning_status,
    learning_get_outcomes, learning_get_recommendations
)
for name, fn in [
    ('learning_status', learning_status),
    ('learning_route_task', lambda: learning_route_task(task_description='implement JWT auth')),
    ('learning_get_outcomes', lambda: learning_get_outcomes(limit=5)),
    ('learning_get_recommendations', lambda: learning_get_recommendations(task_description='fix bug')),
    ('learning_record_outcome', lambda: learning_record_outcome(task='test', agent='brain_mcp', success=True, latency_ms=50)),
]:
    results.append(run_test(name, fn))

# ===== INTELLIGENCE NAMESPACE =====
print('\n[Intelligence Namespace]')
from packages.brain_mcp.namespaces.intelligence import (
    intelligence_route, intelligence_score_complexity,
    intelligence_available_agents, intelligence_get_routing_history
)
for name, fn in [
    ('intelligence_available_agents', intelligence_available_agents),
    ('intelligence_route', lambda: intelligence_route(task_description='build auth system')),
    ('intelligence_score_complexity', lambda: intelligence_score_complexity(task_description='build auth system')),
    ('intelligence_get_routing_history', lambda: intelligence_get_routing_history(limit=3)),
]:
    results.append(run_test(name, fn))

# ===== MIND NAMESPACE =====
print('\n[Mind Namespace]')
from packages.brain_mcp.namespaces.mind import (
    mind_get_mind_state, mind_update_mind_state,
    mind_log_task_completion, mind_get_session_history,
    mind_set_context, mind_get_project_manifest, mind_get_active_workflow
)
for name, fn in [
    ('mind_get_mind_state', mind_get_mind_state),
    ('mind_update_mind_state', lambda: mind_update_mind_state(phase='testing', project='MCP Integration')),
    ('mind_log_task_completion', lambda: mind_log_task_completion(task_id='test_001', description='MCP integration test', success=True, agent='ralph-loop', duration_ms=100)),
    ('mind_get_project_manifest', mind_get_project_manifest),
    ('mind_get_active_workflow', mind_get_active_workflow),
    ('mind_set_context', lambda: mind_set_context(key='mcp_test', value='integration complete')),
]:
    results.append(run_test(name, fn))

# ===== SESSION-POOL MCP =====
print('\n[Session Pool MCP]')
from packages.session_pool_mcp.mcp_server import route_task as sp_route_task, pool_stats, warm_pool
for name, fn in [
    ('session_pool_route_task', lambda: sp_route_task(task_description='implement feature')),
    ('session_pool_pool_stats', pool_stats),
    ('session_pool_warm_pool', lambda: warm_pool(agents=['explore', 'librarian'])),
]:
    results.append(run_test(name, fn))

# ===== ORCHESTRATION MCP =====
print('\n[Orchestration MCP]')
from packages.orchestration.mcp_server import spawn, task_status, get_session_state
for name, fn in [
    ('orchestration_spawn', lambda: spawn(agent='hephaestus', task='test task', context={'test': True})),
    ('orchestration_get_session_state', get_session_state),
]:
    results.append(run_test(name, fn))

# ===== CATALYST MCP =====
print('\n[Catalyst MCP]')
from packages.catalyst_orchestrator.mcp_server import (
    detect_state, list_workflows, get_orchestrator_status
)
for name, fn in [
    ('catalyst_detect_state', lambda: detect_state(user_input='I want to build a feature')),
    ('catalyst_list_workflows', list_workflows),
    ('catalyst_get_orchestrator_status', get_orchestrator_status),
]:
    results.append(run_test(name, fn))

# ===== INTELLIGENCE MCP (FastMCP) =====
print('\n[Intelligence MCP]')
from packages.intelligence.mcp_server import route as intel_route, available_agents, get_routing_history
for name, fn in [
    ('intel_route', lambda: asyncio.run(intel_route(task_description='build auth system'))),
    ('intel_available_agents', available_agents),
    ('intel_get_routing_history', lambda: get_routing_history(limit=3)),
]:
    results.append(run_test(name, fn))

# ===== NX-CONTEXT MCP =====
print('\n[nx-context MCP]')
from packages.nx_context_mcp import (
    get_active_context, get_product_context, get_user_context,
    get_constraints, get_bmad_agents, get_bmad_workflows, health_check
)
for name, fn in [
    ('nxctx_get_active_context', get_active_context),
    ('nxctx_get_product_context', get_product_context),
    ('nxctx_get_user_context', get_user_context),
    ('nxctx_health_check', health_check),
    ('nxctx_get_bmad_agents', get_bmad_agents),
]:
    results.append(run_test(name, fn))

print()
print('=' * 70)
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
print(f'FINAL SUMMARY: {passed}/{len(results)} passed')
if failed > 0:
    print(f'FAILED ({failed}):')
    for name, ok, err in results:
        if not ok:
            print(f'  ❌ {name}: {err[:80]}')
print('=' * 70)
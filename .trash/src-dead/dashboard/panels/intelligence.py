# Intelligence Panel
"""Intelligence layer panel content generator."""

from typing import Any
import json


def get_content(dashboard: Any) -> str:
    """Get intelligence panel content.

    Args:
        dashboard: Dashboard instance with live_data attribute

    Returns:
        Panel content string
    """
    d = dashboard.live_data
    intel = d.get("intelligence", {})
    budget = d.get("budget", {})

    return f"""INTELLIGENCE LAYER (36 modules)

Stats: {json.dumps(intel, indent=2)[:500] if intel else "  (no data)"}
Budget: {json.dumps(budget, indent=2)[:300] if budget else "  (no data)"}

Modules (36):
  Routing: unified_router.py, ml_router.py, memory_routing.py, predictive_router.py, routing_optimizer.py, routing_context.py
  Triggers: trigger_routing.py, dynamic_triggers.py
  Scoring: complexity_scorer.py, dynamic_scorer.py, result_checker.py
  Optimization: agent_optimizer.py, context_optimizer.py, realtime_learner.py, local_model_analysis.py
  Coordination: multi_agent_coordinator.py, agent_communication.py, task_decomposer.py
  Load: load_balancer.py (22 funcs), message_queue.py
  Testing: ab_testing.py (17 funcs), benchmark.py
  Quality: code_quality_tracker.py, permission_engine.py, sandbox.py, security_gate.py
  Storage: sqlite_store.py (19 funcs), outcome_logger.py, delegation_logger.py
  Recovery: error_recovery.py (15 funcs), health_monitor.py (13 funcs), review_triage.py
  Learning: learning.py (16 funcs), skill_registry.py (14 funcs)
  Context: context_sharing.py (12 funcs), prompt_templates.py (12 funcs)
  Contracts: tool_contract.py (11 funcs)"""

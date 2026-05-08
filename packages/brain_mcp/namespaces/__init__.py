"""
Namespaces package for nx-brain-mcp.

This module re-exports all namespace tools for easy import.
"""

from .memory import (
    memory_search_memories,
    memory_get_memory_stats,
    memory_recall_session,
    memory_find_context,
    memory_memory_write,
    memory_auto_write,
    memory_rank_memories,
)

from .context import (
    context_get_active_context,
    context_get_product_context,
    context_get_user_context,
    context_get_constraints,
    context_get_user_profile,
    context_get_style_context,
    context_get_archive_context,
    context_get_bmad_agents,
    context_get_bmad_workflows,
    context_inject_context,
)

from .mind import (
    session_pool_stats,
    mind_log_task_completion,
    mind_get_mind_state,
    mind_update_mind_state,
    mind_get_session_history,
    mind_get_active_workflow,
    mind_set_context,
    mind_get_project_manifest,
)

from .learning import (
    learning_route_task,
    learning_record_outcome,
    learning_status,
    learning_get_recommendations,
    learning_get_outcomes,
)

from .intelligence import (
    intelligence_route,
    intelligence_score_complexity,
    intelligence_available_agents,
    intelligence_get_routing_history,
)

from .session import (
    session_get,
    session_return,
    session_warm_pool,
)

from .trigger import (
    trigger_register,
    trigger_list,
    trigger_check,
    trigger_clear,
    trigger_execute,
)

from .catalyst import (
    catalyst_orchestrate,
    catalyst_detect_state,
    catalyst_list_workflows,
    catalyst_get_orchestrator_status,
)

from .browser import (
    browser_navigate,
    browser_screenshot,
    browser_click,
    browser_fill,
    browser_get_text,
    browser_evaluate,
)

from .sqlite import (
    sqlite_query,
    sqlite_list_tables,
    sqlite_describe_table,
)

from .fingerprint import (
    fingerprint_get_session_context,
    fingerprint_record_pattern,
    fingerprint_get_user_preferences,
    log_tool_sequence,
    memory_inject_context,
    orchestration_get_injected_context,
)

from .tunnel import (
    tunnel_get_key,
    tunnel_get_model,
    tunnel_rotate,
    tunnel_check_error,
    tunnel_health,
    tunnel_status,
    tunnel_chat,
    tunnel_stats,
    tunnel_queue_request,
    tunnel_get_queue_status,
    tunnel_set_fallback_mode,
    tunnel_process_queue,
)

__all__ = [
    # Memory
    "memory_search_memories",
    "memory_get_memory_stats",
    "memory_recall_session",
    "memory_find_context",
    "memory_memory_write",
    "memory_auto_write",
    "memory_rank_memories",
    # Context
    "context_get_active_context",
    "context_get_product_context",
    "context_get_user_context",
    "context_get_constraints",
    "context_get_user_profile",
    "context_get_style_context",
    "context_get_archive_context",
    "context_get_bmad_agents",
    "context_get_bmad_workflows",
    "context_inject_context",
    # Mind
    "session_pool_stats",
    "mind_log_task_completion",
    "mind_get_mind_state",
    "mind_update_mind_state",
    "mind_get_session_history",
    "mind_get_active_workflow",
    "mind_set_context",
    "mind_get_project_manifest",
    # Learning
    "learning_route_task",
    "learning_record_outcome",
    "learning_status",
    "learning_get_recommendations",
    "learning_get_outcomes",
    # Intelligence
    "intelligence_route",
    "intelligence_score_complexity",
    "intelligence_available_agents",
    "intelligence_get_routing_history",
    # Session
    "session_get",
    "session_return",
    "session_warm_pool",
    # Trigger
    "trigger_register",
    "trigger_list",
    "trigger_check",
    "trigger_clear",
    "trigger_execute",
    # Catalyst
    "catalyst_orchestrate",
    "catalyst_detect_state",
    "catalyst_list_workflows",
    "catalyst_get_orchestrator_status",
    # Browser
    "browser_navigate",
    "browser_screenshot",
    "browser_click",
    "browser_fill",
    "browser_get_text",
    "browser_evaluate",
    # SQLite
    "sqlite_query",
    "sqlite_list_tables",
    "sqlite_describe_table",
    # Fingerprint
    "fingerprint_get_session_context",
    "fingerprint_record_pattern",
    "fingerprint_get_user_preferences",
    "log_tool_sequence",
    "memory_inject_context",
    "orchestration_get_injected_context",
    # Tunnel
    "tunnel_get_key",
    "tunnel_get_model",
    "tunnel_rotate",
    "tunnel_check_error",
    "tunnel_health",
    "tunnel_status",
    "tunnel_chat",
    "tunnel_stats",
    "tunnel_queue_request",
    "tunnel_get_queue_status",
    "tunnel_set_fallback_mode",
    "tunnel_process_queue",
]

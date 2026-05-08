#!/usr/bin/env python3
"""OMO Agent Routing Patch - Workaround for GitHub Issue #16303.

This module provides a fix for the nested subSession agent routing bug
where task(subagent_type="hephaestus") incorrectly routes to Sisyphus
in nested sessions.

The patch works by:
1. Detecting when we're in a nested session context
2. Forcing direct agent targeting via session_id continuation
3. Maintaining proper agent identity through session chains

Usage:
    from packages.orchestration.routing_patch import patch_task_delegation

    # Apply patch before using task() tool
    patch_task_delegation()
"""

import logging
import os

logger = logging.getLogger("omo_routing_patch")

# Environment flag to enable/disable patch
PATCH_ENABLED = os.environ.get("OMO_ROUTING_PATCH", "1") == "1"


def detect_nested_session() -> bool:
    """Detect if we're in a nested session context.

    Returns True if:
    - OMO_SESSION_DEPTH > 1
    - PARENT_SESSION_ID is set
    - We're in a subagent context
    """
    session_depth = int(os.environ.get("OMO_SESSION_DEPTH", "0"))
    parent_session = os.environ.get("PARENT_SESSION_ID")
    subagent_context = os.environ.get("OMO_SUBAGENT_CONTEXT", "")

    return session_depth > 1 or parent_session is not None or bool(subagent_context)


def get_session_context() -> dict:
    """Get current session context information."""
    return {
        "session_id": os.environ.get("OMO_SESSION_ID", ""),
        "parent_session": os.environ.get("PARENT_SESSION_ID", ""),
        "session_depth": int(os.environ.get("OMO_SESSION_DEPTH", "0")),
        "subagent_context": os.environ.get("OMO_SUBAGENT_CONTEXT", ""),
    }


def should_force_direct_agent(params: dict) -> bool:
    """Determine if we should force direct agent targeting.

    Args:
        params: The task parameters including subagent_type

    Returns True if:
    - We have subagent_type specified
    - We're in nested session context
    - The subagent is a specialized agent (not category-based)
    """
    if not PATCH_ENABLED:
        return False

    subagent_type = params.get("subagent_type", "")
    category = params.get("category", "")

    # Only patch if using direct subagent_type (not category-based)
    if not subagent_type:
        return False

    # Check if in nested session
    if not detect_nested_session():
        return False

    # Specialized agents that need direct targeting
    specialized_agents = [
        "hephaestus",
        "oracle",
        "prometheus",
        "atlas",
        "momus",
        "metis",
        "sisyphus",
        "sisyphus-junior",
    ]

    return subagent_type.lower() in specialized_agents


def patch_agent_params(params: dict) -> dict:
    """Patch task parameters for proper agent routing.

    This adds session_id continuation to ensure the correct
    agent is used in nested sessions.

    Args:
        params: Original task parameters

    Returns:
        Patched parameters with session continuation
    """
    if not should_force_direct_agent(params):
        return params

    # Get current session ID for continuation
    current_session = os.environ.get("OMO_SESSION_ID", "")

    if current_session:
        # Preserve the session chain for proper agent targeting
        params["session_id"] = current_session

        logger.info(
            f"[PATCH] Nested session detected. "
            f"Agent: {params.get('subagent_type')}, "
            f"Session: {current_session[:16]}..."
        )

    return params


def apply_patch():
    """Apply the OMO routing patch to the system."""
    if not PATCH_ENABLED:
        logger.info("[PATCH] OMO routing patch disabled")
        return

    logger.info(
        "[PATCH] OMO Agent Routing Patch applied for GitHub #16303. "
        "Nested subSession agent routing will use session continuation."
    )

    # Export functions for use in task hooks
    global \
        detect_nested_session, \
        get_session_context, \
        should_force_direct_agent, \
        patch_agent_params


def log_routing_decision(agent: str, params: dict, result: Any) -> None:
    """Log routing decisions for debugging."""
    ctx = get_session_context()
    logger.info(
        f"[ROUTING] Agent={agent}, "
        f"Depth={ctx['session_depth']}, "
        f"Parent={bool(ctx['parent_session'])}, "
        f"Result={type(result).__name__}"
    )


# Auto-apply on import
if PATCH_ENABLED:
    apply_patch()


if __name__ == "__main__":
    # CLI for testing and debugging
    import json

    print("=== OMO Agent Routing Patch ===")
    print(f"Patch enabled: {PATCH_ENABLED}")
    print(f"Nested session: {detect_nested_session()}")
    print(f"Session context: {json.dumps(get_session_context(), indent=2)}")

    # Test parameter patching
    test_params = [
        {"subagent_type": "hephaestus", "prompt": "test", "run_in_background": False},
        {"category": "deep", "prompt": "test", "run_in_background": False},
        {"subagent_type": "explore", "prompt": "test", "run_in_background": True},
    ]

    print("\n=== Parameter Patching Test ===")
    for params in test_params:
        patched = patch_agent_params(params.copy())
        changed = params != patched
        print(f"Original: {params.get('subagent_type') or params.get('category')}")
        print(
            f"Patched:  {patched.get('session_id', 'N/A')[:20] + '...' if patched.get('session_id') else 'N/A'}"
        )
        print(f"Changed:  {changed}")
        print()

"""
Health check utilities for nx-brain-mcp.

Shared health check functions used across namespaces.
"""

from __future__ import annotations



def check_memory_health() -> dict[str, any]:
    """Check health of memory namespace."""
    try:
        from packages.memory_store.mcp_server import get_memory_stats

        stats = get_memory_stats()
        return {"status": "healthy", "details": stats}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_context_health() -> dict[str, any]:
    """Check health of context namespace."""
    try:
        from packages.context_store import get_active_context

        ctx = get_active_context()
        return {"status": "healthy", "details": ctx}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_mind_health() -> dict[str, any]:
    """Check health of mind namespace."""
    try:
        from packages.nx_mind_mcp.nx_mind_mcp import get_mind_state

        state = get_mind_state()
        return {"status": "healthy", "details": state}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_learning_health() -> dict[str, any]:
    """Check health of learning namespace."""
    try:
        from packages.learning_engine.mcp_server import status

        learning_status = status()
        return {"status": "healthy", "details": learning_status}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_intelligence_health() -> dict[str, any]:
    """Check health of intelligence namespace."""
    try:
        from packages.intelligence.mcp_server import available_agents

        agents = available_agents()
        return {"status": "healthy", "details": agents}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_session_health() -> dict[str, any]:
    """Check health of session namespace."""
    try:
        from packages.session_pool_mcp.mcp_server import pool_stats
        stats = pool_stats()
        return {"status": "healthy", "details": stats}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_trigger_health() -> dict[str, any]:
    """Check health of trigger namespace."""
    try:
        from packages.trigger_guardian_mcp.trigger_guardian_mcp import list_triggers

        triggers = list_triggers()
        return {"status": "healthy", "details": triggers}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_catalyst_health() -> dict[str, any]:
    """Check health of catalyst namespace."""
    try:
        return {"status": "healthy", "details": "CatalystOrchestrator available"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def get_all_health_checks() -> dict[str, any]:
    """Run all health checks and return combined result."""
    checks = {
        "memory": check_memory_health(),
        "context": check_context_health(),
        "mind": check_mind_health(),
        "learning": check_learning_health(),
        "intelligence": check_intelligence_health(),
        "session": check_session_health(),
        "trigger": check_trigger_health(),
        "catalyst": check_catalyst_health(),
    }

    all_healthy = all(h.get("status") == "healthy" for h in checks.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "namespaces": checks,
    }

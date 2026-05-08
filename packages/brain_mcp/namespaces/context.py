"""
Context namespace tools for nx-brain-mcp.

This module contains all context-related MCP tools.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

_context_cache: dict[str, tuple[float, dict]] = {}
_CACHE_TTL_SECONDS = 300


def _get_cached_style_context() -> dict[str, Any]:
    global _context_cache
    cache_key = "style_context"
    now = time.time()

    if cache_key in _context_cache:
        cached_time, cached_value = _context_cache[cache_key]
        if now - cached_time < _CACHE_TTL_SECONDS:
            cached_value["_cache_hit"] = True
            return cached_value

    try:
        from packages.context_store import get_style_context

        result = get_style_context()
        result["_cached_at"] = now
        result["_cache_hit"] = False
        _context_cache[cache_key] = (now, result)
        return result
    except Exception as e:
        logger.error(f"context_get_style_context failed: {e}")
        return {"error": str(e)}


def context_get_active_context() -> dict[str, Any]:
    """Returns current active context from memory bank."""
    try:
        from packages.context_store import get_active_context

        return get_active_context()
    except Exception as e:
        logger.error(f"context_get_active_context failed: {e}")
        return {"error": str(e)}


def context_get_product_context() -> dict[str, Any]:
    """Returns product context (identity/soul) from memory bank."""
    try:
        from packages.context_store import get_product_context

        return get_product_context()
    except Exception as e:
        logger.error(f"context_get_product_context failed: {e}")
        return {"error": str(e)}


def context_get_user_context() -> dict[str, Any]:
    """Returns user context from memory bank."""
    try:
        from packages.context_store import get_user_context

        return get_user_context()
    except Exception as e:
        logger.error(f"context_get_user_context failed: {e}")
        return {"error": str(e)}


def context_get_constraints() -> dict[str, Any]:
    """Returns behavioral constraints from memory bank."""
    try:
        from packages.context_store import get_constraints

        return get_constraints()
    except Exception as e:
        logger.error(f"context_get_constraints failed: {e}")
        return {"error": str(e)}


def context_get_user_profile() -> dict[str, Any]:
    """Returns immutable user profile from memory bank."""
    try:
        from packages.context_store import get_user_profile

        return get_user_profile()
    except Exception as e:
        logger.error(f"context_get_user_profile failed: {e}")
        return {"error": str(e)}


def context_get_style_context() -> dict[str, Any]:
    """Returns personalized style context from usage pattern learning."""
    return _get_cached_style_context()


def context_get_archive_context(
    query: str = "", max_sessions: int = 3
) -> dict[str, Any]:
    """Returns relevant context from past session archives."""
    try:
        from packages.context_store import get_archive_context

        return get_archive_context(query, max_sessions)
    except Exception as e:
        logger.error(f"context_get_archive_context failed: {e}")
        return {"error": str(e)}


def context_get_bmad_agents() -> dict[str, Any]:
    """Lists available BMAD agents from _bmad/_config/agents/."""
    try:
        from packages.context_store import get_bmad_agents

        return get_bmad_agents()
    except Exception as e:
        logger.error(f"context_get_bmad_agents failed: {e}")
        return {"error": str(e)}


def context_get_bmad_workflows(phase: Optional[str] = None) -> dict[str, Any]:
    """Lists BMAD workflows by phase from _bmad/bmm/workflows/."""
    try:
        from packages.context_store import get_bmad_workflows

        return get_bmad_workflows(phase)
    except Exception as e:
        logger.error(f"context_get_bmad_workflows failed: {e}")
        return {"error": str(e)}


def context_inject_context(
    context_type: str = "all", output_path: Optional[str] = None
) -> dict[str, Any]:
    """Writes context into session for prompt injection."""
    try:
        from packages.context_store import inject_context

        return inject_context(context_type, output_path)
    except Exception as e:
        logger.error(f"context_inject_context failed: {e}")
        return {"error": str(e)}

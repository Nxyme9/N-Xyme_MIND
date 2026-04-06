#!/usr/bin/env python3
"""
MCP Server for Intelligent Router — Exposes routing functionality to OpenCode.

Tools:
- route_task: Route a task to the optimal model/provider/IP
- record_success: Record a successful request
- record_failure: Record a failed request
- get_router_status: Get full router status
- get_available_models: Get list of available models with capabilities
- get_routing_history: Get recent routing decisions
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import List, Optional

from fastmcp import FastMCP

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import router components
try:
    from proxy.intelligent_router import intelligent_router
    from proxy.api_key_pool import api_key_pool
    from proxy.vpn_ip_pool import vpn_ip_pool
    from proxy.router_brain import router_brain, MODEL_CAPABILITIES
    from proxy.cost_optimizer import cost_tracker
    from proxy.learning_engine import learning_engine

    _router_available = True
except Exception as e:
    logging.getLogger(__name__).warning(
        f"Intelligent Router components unavailable: {e}"
    )
    _router_available = False

# ---------------------------------------------------------------------------
# Server Init
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="intelligent-router",
    version="1.0.0",
    instructions=(
        "Intelligent Router MCP Server — routes LLM requests to optimal model/provider/IP.\n\n"
        "Tools:\n"
        "- route_task: Route a task to the optimal model/provider/IP\n"
        "- record_success: Record a successful request for learning\n"
        "- record_failure: Record a failed request for learning\n"
        "- get_router_status: Get full router status and metrics\n"
        "- get_available_models: Get list of available models with capabilities\n"
        "- get_routing_history: Get recent routing decisions\n"
    ),
)

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool(tags={"routing", "model-selection"})
def route_task(prompt: str, system_prompt: str = "", agent_type: str = "") -> dict:
    """Route a task to the optimal model/provider/IP.

    Args:
        prompt: The user prompt to route
        system_prompt: Optional system prompt
        agent_type: Optional agent type for preference-based routing
    """
    if not _router_available:
        return {"error": "Router not available"}

    route = intelligent_router.select_route(prompt, system_prompt)
    if agent_type:
        route["agent_type"] = agent_type
    return route


@mcp.tool(tags={"routing", "learning"})
def record_success(
    route: dict,
    input_tokens: int = 0,
    output_tokens: int = 0,
    latency_ms: float = 0.0,
) -> dict:
    """Record a successful request for learning and optimization.

    Args:
        route: The route that was used (from route_task)
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        latency_ms: Request latency in milliseconds
    """
    if not _router_available:
        return {"error": "Router not available"}

    intelligent_router.record_success(route, input_tokens, output_tokens, latency_ms)
    return {"status": "success"}


@mcp.tool(tags={"routing", "learning"})
def record_failure(
    route: dict,
    error_type: str,
    latency_ms: float = 0.0,
) -> dict:
    """Record a failed request for learning and optimization.

    Args:
        route: The route that was used (from route_task)
        error_type: Type of error (e.g., "timeout", "rate_limit", "api_error")
        latency_ms: Request latency in milliseconds
    """
    if not _router_available:
        return {"error": "Router not available"}

    intelligent_router.record_failure(route, error_type, latency_ms)
    return {"status": "recorded"}


@mcp.tool(tags={"routing", "status"})
def get_router_status() -> dict:
    """Get full router status including metrics, key pool, and IP pool status."""
    if not _router_available:
        return {"error": "Router not available"}

    return intelligent_router.get_status()


@mcp.tool(tags={"routing", "models"})
def get_available_models() -> List[dict]:
    """Get list of available models with their capabilities and scores."""
    if not _router_available:
        return []

    return [{"model": name, **caps} for name, caps in MODEL_CAPABILITIES.items()]


@mcp.tool(tags={"routing", "history"})
def get_routing_history(limit: int = 10) -> List[dict]:
    """Get recent routing decisions.

    Args:
        limit: Number of recent decisions to return (default: 10)
    """
    if not _router_available:
        return []

    import sqlite3

    try:
        conn = sqlite3.connect(learning_engine.db_path)
        cursor = conn.execute(
            """SELECT timestamp, categories, complexity, selected_model, 
                selected_provider, latency_ms, success FROM outcomes 
                ORDER BY timestamp DESC LIMIT ?""",
            (limit,),
        )
        return [
            {
                "timestamp": r[0],
                "categories": r[1],
                "complexity": r[2],
                "model": r[3],
                "provider": r[4],
                "latency_ms": r[5],
                "success": bool(r[6]),
            }
            for r in cursor.fetchall()
        ]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()

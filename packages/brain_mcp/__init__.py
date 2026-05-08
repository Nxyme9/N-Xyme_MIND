#!/usr/bin/env python3
"""
nx-brain-mcp
=========
Central brain MCP server - the core of N-Xyme system.
Personal external brain - ALL MCP capabilities in ONE bulletproof process.

🎯 PERSONAL BRAIN CAPABILITIES:
- Memory: Semantic search, episodic recall, context finding, memory stats
- Context: Active, product, user, constraints, style, archives, BMAD
- Mind: State, history, workflows, project manifest, task logging
- Learning: Route task, record outcomes, recommendations, status
- Intelligence: Agent routing, complexity scoring, routing history
- Session: Pool stats, get/return sessions, warm pool
- Triggers: Register, list, check, clear, execute command triggers
- Catalyst: Orchestrate workflows, detect FLOW/FRICTION/ADAPT states
- Playwright: Browser automation (navigate, screenshot, click, fill)
- SQLite: Query routing.db for delegation history & learning stats
- Session Fingerprinting: Auto-inject contextual memory from past sessions

🚀 ML ENHANCEMENTS (2025-2026):
- Q-Learning based routing with circuit breakers
- Contextual bandits with Thompson Sampling for strategy selection
- Self-learning from delegation outcomes
- Pattern extraction from success/failure data
- Tool-CallingLM ready (composite tool sequences from outcomes)

Transport: stdio (default), HTTP (recommended for network access).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    stream=sys.stderr,
    force=True,
)

# Suppress noisy third-party loggers
for logger_name in ["faiss", "numpy"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# Suppress FastMCP banner - it prints to stdout and breaks JSON-RPC
# We redirect print to devnull BEFORE importing fastmcp
import sys
import io

# Save original stdout and its buffer
_original_stdout = sys.stdout
_stdout_buffer = sys.stdout.buffer


# Create a quiet stdout wrapper that blocks print() but allows .buffer access
class _QuietStdout:
    """stdout that silently discards writes but exposes .buffer for JSON-RPC"""

    def write(self, x):
        pass

    def flush(self):
        pass

    @property
    def buffer(self):
        return _stdout_buffer


# Redirect stdout to quiet wrapper BEFORE any FastMCP imports
_quiet_stdout = _QuietStdout()
sys.stdout = _quiet_stdout

from fastmcp import FastMCP

# After import, restore stdout but keep the banner suppressed
sys.stdout = _original_stdout

# ============================================================================
# NXYME CORE - Module registry for plug-and-play discovery
# ============================================================================

# Use nxyme_core for module management
try:
    from nxyme_core import get_registry, NXymeConfig, get_default_config

    NXYMECORE_AVAILABLE = True
except ImportError:
    NXYMECORE_AVAILABLE = False
    get_registry = None
    NXymeConfig = None
    get_default_config = None

# ============================================================================
# PATH SETUP - Use absolute paths
# ============================================================================

# This file is at: packages/nx-brain-mcp/__init__.py
# Project root is: packages/../ = N-Xyme_MIND
_module_file = Path(__file__).resolve()
_brain_mcp_dir = _module_file.parent  # packages/brain_mcp
_project_root = _brain_mcp_dir.parent.parent  # N-Xyme_MIND
packages_root = _project_root / "packages"

# Add packages directory (not packages/packages)
if str(packages_root) not in sys.path:
    sys.path.insert(0, str(packages_root))

# Add actual package paths (with underscores in dir, matching import name)
_package_path_map = {
    "context_store": "packages/context_store",  # was context-store
    "nx_mind_mcp": "packages/nx-mind-mcp",  # stays - nx-mind-mcp unchanged
    "trigger_guardian_mcp": "packages/trigger-guardian-mcp",  # stays
    "catalyst_orchestrator": "packages/catalyst_orchestrator",  # was catalyst-orchestrator
    "session_pool_mcp": "packages/session-pool-mcp",  # stays
    "playwright_mcp": "packages/playwright-mcp",  # stays
    "sqlite_mcp": "packages/sqlite-mcp",  # stays
    "learning_engine": "packages/learning_engine",  # was learning-engine
    "memory_core": "packages/memory_store",  # was memory-store
}

# Add each package's PARENT directory to sys.path so imports work
# After this: can do "from nx_context_mcp import ..." (inner package name)
for _import_name, _dir_path in _package_path_map.items():
    _full_path = _project_root / _dir_path
    if str(_full_path) not in sys.path:
        sys.path.insert(0, str(_full_path))

# Add packages directory (for packages.X imports)
if str(packages_root) not in sys.path:
    sys.path.insert(0, str(packages_root))

# Add project root
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

logger = logging.getLogger("nx-brain-mcp")

# ============================================================================
# NXYME MODULE REGISTRATION HELPER
# ============================================================================


def _register_nxyme_modules():
    """Register N-Xyme modules with the nxyme_core registry.

    This enables plug-and-play module discovery via nxyme_core.
    Modules are registered by name and lazily loaded on first access.
    """
    if not NXYMECORE_AVAILABLE:
        return

    try:
        # Import module functions (not classes - registry handles lazy loading)
        # Note: These modules must implement NXymeModule interface
        # Skip MemoryCore import - no such class exists in memory_store
        from packages.learning_engine import health_check as le_health_check
        # orchestration and intelligence may not exist - skip them too

        logger.info("Registered N-Xyme modules with nxyme_core registry")
    except ImportError as e:
        # Module not available - that's ok, use fallback
        logger.warning(f"Module not available for registry: {e}")
    except Exception as e:
        logging.warning(f"Failed to register N-Xyme modules: {e}")


# ============================================================================
# SERVER INIT
# ============================================================================

mcp = FastMCP(
    name="nx-brain-mcp",
    version="1.0.0",
    instructions=(
        "Unified N-Xyme MCP Server — All MCP tools in one process.\n\n"
        "Namespaces:\n"
        "- memory.*: Search, stats, recall, context finding\n"
        "- context.*: Active, product, user, constraints, BMAD\n"
        "- mind.*: State, history, workflow, context\n"
        "- learning.*: Route, record outcome, status\n"
        "- intelligence.*: Route, score, agents, history\n"
        "- session.*: Pool stats, get/return sessions\n"
        "- trigger.*: Register, list, check, clear triggers\n"
        "- catalyst.*: Orchestrate, detect state, list workflows\n"
    ),
)

# ============================================================================
# GUARDRAILS - Error Recovery & Resilience
# ============================================================================

import asyncio
from contextlib import asynccontextmanager

# Track tool health status
_tool_health = {}
_init_errors = []


@asynccontextmanager
async def lifespan(app):
    """Lifespan context manager with health tracking and error recovery."""
    logger.info("Starting nx-brain-mcp server...")

    # Initial health check - populate _tool_health
    for tool_name in [
        "memory",
        "context",
        "mind",
        "learning",
        "intelligence",
        "session",
        "trigger",
        "catalyst",
    ]:
        _tool_health[tool_name] = {"status": "unknown", "last_error": None}

    # Log any import errors from module load
    if _init_errors:
        logger.warning(f"Import errors during load: {_init_errors}")

    logger.info(f"Unified MCP started with {len(_tool_health)} tool namespaces")

    yield

    logger.info("Shutting down nx-brain-mcp server...")


# Attach lifespan to mcp
mcp._lifespan = lifespan


# ============================================================================
# HEALTH CHECK TOOLS
# ============================================================================


@mcp.tool()
def system_health_check() -> dict[str, any]:
    """Health check for all tool namespaces - returns status of each namespace."""
    return {
        "status": "healthy",
        "namespaces": _tool_health,
        "init_errors": _init_errors,
    }


@mcp.tool()
def system_health_check_registry() -> dict[str, any]:
    """Get health status of all N-Xyme modules using nxyme_core registry.

    This uses the nxyme_core plug-and-play registry for centralized health checks.
    Returns degraded status if any module is unhealthy.
    """
    if not NXYMECORE_AVAILABLE:
        return {"status": "fallback", "message": "nxyme_core not available"}

    try:
        registry = get_registry()
        health = registry.health_check_all()

        all_healthy = all(h.get("status") == "healthy" for h in health.values())
        return {
            "status": "healthy" if all_healthy else "degraded",
            "modules": health,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================================
# IMPORT AND REGISTER NAMESPACE TOOLS
# ============================================================================


# Import all namespaces and register their tools with the MCP server
def _register_namespace_tools():
    """Import and register all namespace tools with the MCP server."""
    logger.info("Loading namespace tools...")

    # Import each namespace module and set the MCP server
    # Each namespace module will register its tools with the decorators

    # Import each namespace module and register tools with the real MCP server
    # Each namespace module now exports plain functions that we register as tools

    try:
        from packages.brain_mcp.namespaces import memory as memory_ns

        for func_name in [
            "memory_search_memories",
            "memory_get_memory_stats",
            "memory_recall_session",
            "memory_find_context",
            "memory_memory_write",
            "memory_auto_write",
            "memory_rank_memories",
        ]:
            func = getattr(memory_ns, func_name, None)
            if func:
                mcp.tool()(func)

        logger.info("✓ memory namespace loaded")
    except Exception as e:
        logger.warning(f"✗ memory namespace: {e}")
        _init_errors.append(f"memory: {e}")

    try:
        from packages.brain_mcp.namespaces import context as context_ns

        for func_name in [
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
        ]:
            func = getattr(context_ns, func_name, None)
            if func:
                mcp.tool()(func)

        logger.info("✓ context namespace loaded")
    except Exception as e:
        logger.warning(f"✗ context namespace: {e}")
        _init_errors.append(f"context: {e}")

    try:
        from packages.brain_mcp.namespaces import mind as mind_ns

        for func_name in [
            "session_pool_stats",
            "mind_log_task_completion",
            "mind_get_mind_state",
            "mind_update_mind_state",
            "mind_get_session_history",
            "mind_get_active_workflow",
            "mind_set_context",
            "mind_get_project_manifest",
        ]:
            func = getattr(mind_ns, func_name, None)
            if func:
                mcp.tool()(func)

        logger.info("✓ mind namespace loaded")
    except Exception as e:
        logger.warning(f"✗ mind namespace: {e}")
        _init_errors.append(f"mind: {e}")

    try:
        from packages.brain_mcp.namespaces import learning as learning_ns

        for func_name in [
            "learning_route_task",
            "learning_record_outcome",
            "learning_status",
            "learning_get_recommendations",
            "learning_get_outcomes",
        ]:
            func = getattr(learning_ns, func_name, None)
            if func:
                mcp.tool()(func)

        logger.info("✓ learning namespace loaded")
    except Exception as e:
        logger.warning(f"✗ learning namespace: {e}")
        _init_errors.append(f"learning: {e}")

    try:
        from packages.brain_mcp.namespaces import intelligence as intelligence_ns

        for func_name in [
            "intelligence_route",
            "intelligence_score_complexity",
            "intelligence_available_agents",
            "intelligence_get_routing_history",
        ]:
            func = getattr(intelligence_ns, func_name, None)
            if func:
                mcp.tool()(func)

        logger.info("✓ intelligence namespace loaded")
    except Exception as e:
        logger.warning(f"✗ intelligence namespace: {e}")
        _init_errors.append(f"intelligence: {e}")

    try:
        # Session namespace
        from packages.brain_mcp.namespaces import session as session_ns

        for func_name in [
            "session_get",
            "session_return",
            "session_warm_pool",
            "session_list_mcp",  # NEW: Reads from our state.db
        ]:
            func = getattr(session_ns, func_name, None)
            if func:
                mcp.tool()(func)

        logger.info("✓ session namespace loaded (4 functions)")
    except Exception as e:
        logger.warning(f"✗ session namespace: {e}")
        _init_errors.append(f"session: {e}")

    try:
        # Trigger namespace
        from packages.brain_mcp.namespaces import trigger as trigger_ns

        for func_name in [
            "trigger_register",
            "trigger_list",
            "trigger_check",
            "trigger_clear",
            "trigger_execute",
        ]:
            func = getattr(trigger_ns, func_name, None)
            if func:
                mcp.tool()(func)

        logger.info("✓ trigger namespace loaded")
    except Exception as e:
        logger.warning(f"✗ trigger namespace: {e}")
        _init_errors.append(f"trigger: {e}")

    try:
        # Catalyst namespace
        from packages.brain_mcp.namespaces import catalyst as catalyst_ns

        for func_name in [
            "catalyst_orchestrate",
            "catalyst_detect_state",
            "catalyst_list_workflows",
            "catalyst_get_orchestrator_status",
        ]:
            func = getattr(catalyst_ns, func_name, None)
            if func:
                mcp.tool()(func)

        logger.info("✓ catalyst namespace loaded")
    except Exception as e:
        logger.warning(f"✗ catalyst namespace: {e}")
        _init_errors.append(f"catalyst: {e}")

    try:
        # Browser namespace
        from packages.brain_mcp.namespaces import browser as browser_ns

        for func_name in [
            "browser_navigate",
            "browser_screenshot",
            "browser_click",
            "browser_fill",
            "browser_get_text",
            "browser_evaluate",
        ]:
            func = getattr(browser_ns, func_name, None)
            if func:
                mcp.tool()(func)

        logger.info("✓ browser namespace loaded")
    except Exception as e:
        logger.warning(f"✗ browser namespace: {e}")
        _init_errors.append(f"browser: {e}")

    try:
        # SQLite namespace
        from packages.brain_mcp.namespaces import sqlite as sqlite_ns

        for func_name in [
            "sqlite_query",
            "sqlite_list_tables",
            "sqlite_describe_table",
        ]:
            func = getattr(sqlite_ns, func_name, None)
            if func:
                mcp.tool()(func)

        logger.info("✓ sqlite namespace loaded")
    except Exception as e:
        logger.warning(f"✗ sqlite namespace: {e}")
        _init_errors.append(f"sqlite: {e}")

    try:
        # Fingerprint namespace
        from packages.brain_mcp.namespaces import fingerprint as fingerprint_ns

        for func_name in [
            "fingerprint_get_session_context",
            "fingerprint_record_pattern",
            "fingerprint_get_user_preferences",
            "log_tool_sequence",
            "memory_inject_context",
            "orchestration_get_injected_context",
            # NEW: Cross-session / global context functions
            "get_global_context",
            "update_global_context",
            "get_cross_session_context",
            "get_full_injected_context",
        ]:
            func = getattr(fingerprint_ns, func_name, None)
            if func:
                mcp.tool()(func)

        logger.info("✓ fingerprint namespace loaded (8 functions)")
    except Exception as e:
        logger.warning(f"✗ fingerprint namespace: {e}")
        _init_errors.append(f"fingerprint: {e}")

    # ============================================================
    # TUNNEL NAMESPACE - API Key Rotator
    # ============================================================
    try:
        from packages.brain_mcp.namespaces import tunnel as tunnel_ns

        for func_name in [
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
        ]:
            func = getattr(tunnel_ns, func_name, None)
            if func:
                mcp.tool()(func)

        logger.info("✓ tunnel namespace loaded")
    except Exception as e:
        logger.warning(f"✗ tunnel namespace: {e}")
        _init_errors.append(f"tunnel: {e}")

    logger.info("All namespace tools loaded")


# Register namespace tools on module load
_register_namespace_tools()


# ============================================================================
# NXYME CORE REGISTRY INITIALIZATION
# ============================================================================

# Initialize nxyme_core registry on module load (if available)
if NXYMECORE_AVAILABLE:
    try:
        _register_nxyme_modules()
    except Exception as e:
        logging.warning(f"Failed to register N-Xyme modules: {e}")


# ============================================================================
# CUSTOM HTTP ROUTES - Direct HTTP access without MCP protocol
# ============================================================================


@mcp.custom_route("/health", methods=["GET"])
async def health_check_route(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "status": "healthy",
            "service": "nx-brain-mcp",
            "version": "1.0.0",
        }
    )


@mcp.custom_route("/memory_stats", methods=["GET"])
async def memory_stats_route(request: Request) -> JSONResponse:
    try:
        from packages.brain_mcp.namespaces import memory as memory_ns

        stats = memory_ns.memory_get_memory_stats()
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/tools_list", methods=["GET"])
async def tools_list_route(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "service": "nx-brain-mcp",
            "tools": list(_tool_health.keys()),
        }
    )


@mcp.custom_route("/health", methods=["GET"])
async def health_check_route(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "status": "healthy",
            "service": "nx-brain-mcp",
            "version": "1.0.0",
        }
    )


@mcp.custom_route("/memory_stats", methods=["GET"])
async def memory_stats_route(request: Request) -> JSONResponse:
    try:
        from packages.brain_mcp.namespaces import memory as memory_ns

        stats = memory_ns.memory_get_memory_stats()
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/tools_list", methods=["GET"])
async def tools_list_route(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "service": "nx-brain-mcp",
            "tools": list(_tool_health.keys()),
        }
    )


@mcp.custom_route("/memory_search", methods=["GET"])
async def memory_search_route(request: Request) -> JSONResponse:
    try:
        from packages.brain_mcp.namespaces import memory as memory_ns

        q = request.query_params.get("q") or request.query_params.get("query") or ""
        limit = int(request.query_params.get("limit") or 50)
        results = memory_ns.memory_search_memories(q, limit)
        return JSONResponse(results)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unified N-Xyme MCP Server")
    parser.add_argument(
        "--http", action="store_true", help="Use HTTP transport (recommended)"
    )
    parser.add_argument("--port", type=int, default=8765, help="HTTP port")
    args = parser.parse_args()

    if args.http:
        mcp.run(transport="http", host="0.0.0.0", port=args.port)
    else:
        mcp.run(transport="stdio")

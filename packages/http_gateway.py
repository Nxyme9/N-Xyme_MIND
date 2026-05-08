#!/usr/bin/env python3
"""
HTTP Gateway - MCP Tools as REST Endpoints
================================
Wraps MCP tools as REST API endpoints for frontend consumption.
Runs on port 8766 (different from MCP server on 8765).

Endpoints:
- GET /tools_list → list of available agents
- POST /memory_get → search memories
- POST /memory_write → write memory
- GET /system_health_check → health check
- POST /route_task → route task
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project to path
ROOT = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
sys.path.insert(0, str(ROOT))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("http-gateway")

# Constants
MCP_SERVER_URL = "http://localhost:8765"
PORT = 8766

# Create FastAPI app
app = FastAPI(
    title="N-Xyme HTTP Gateway",
    description="HTTP REST endpoints wrapping MCP tools",
    version="1.0.0",
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Pydantic Models for Request Bodies
# =============================================================================


class MemoryGetRequest(BaseModel):
    query: str = ""
    limit: int = 10


class MemoryWriteRequest(BaseModel):
    content: str
    kind: str = "episodic"
    scope: str = "global"


class RecallSessionRequest(BaseModel):
    session_id: Optional[str] = None
    limit: int = 50


class FindContextRequest(BaseModel):
    task: str
    context_type: str = "all"


class RouteTaskRequest(BaseModel):
    task_description: str


class OrchestrationSpawnRequest(BaseModel):
    agent: str
    task: str
    context: dict = None
    inject_memory: bool = False


class OrchestrationOrchestrateRequest(BaseModel):
    user_input: str
    context: dict = None


class DetectStateRequest(BaseModel):
    user_input: str


class LearningRecordOutcomeRequest(BaseModel):
    task: str
    agent: str
    success: bool
    latency_ms: float = 0
    tokens_used: int = 0


# =============================================================================
# Direct MCP Tool Calls - Import and call Python packages directly
# =============================================================================


def _call_memory_search(query: str, limit: int = 10) -> dict:
    """Call memory_core search_memories directly."""
    try:
        from packages.memory_store.mcp_server import search_memories

        result = search_memories(query=query, limit=limit)
        logger.info(f"memory_search success: {len(result.get('results', []))} results")
        return result
    except Exception as e:
        logger.error(f"memory_search failed: {e}")
        return {"error": str(e), "results": []}


def _call_memory_write(
    content: str, kind: str = "episodic", scope: str = "global"
) -> dict:
    """Call memory_core memory_write directly."""
    try:
        from packages.memory_store.mcp_server import memory_write

        result = memory_write(content=content, kind=kind, scope=scope)
        logger.info(f"memory_write success: {result.get('success', False)}")
        return result
    except Exception as e:
        logger.error(f"memory_write failed: {e}")
        return {"error": str(e)}


def _call_memory_stats() -> dict:
    """Call memory_core get_memory_stats directly."""
    try:
        from packages.memory_store.mcp_server import get_memory_stats

        result = get_memory_stats()
        logger.info("memory_stats success")
        return result
    except Exception as e:
        logger.error(f"memory_stats failed: {e}")
        return {"error": str(e)}


def _call_recall_session(session_id: str = None, limit: int = 50) -> dict:
    """Call memory_core recall_session directly."""
    try:
        from packages.memory_store.mcp_server import recall_session

        result = recall_session(session_id=session_id, limit=limit)
        logger.info(
            f"recall_session success: {len(result.get('messages', []))} messages"
        )
        return result
    except Exception as e:
        logger.error(f"recall_session failed: {e}")
        return {"error": str(e)}


def _call_find_context(task: str, context_type: str = "all") -> dict:
    """Call memory_core find_context directly."""
    try:
        from packages.memory_store.mcp_server import find_context

        result = find_context(task=task, context_type=context_type)
        logger.info("find_context success")
        return result
    except Exception as e:
        logger.error(f"find_context failed: {e}")
        return {"error": str(e)}


def _call_get_capabilities() -> dict:
    """Call memory_core get_capabilities directly."""
    try:
        from packages.memory_store.mcp_server import get_capabilities

        result = get_capabilities()
        logger.info("get_capabilities success")
        return result
    except Exception as e:
        logger.error(f"get_capabilities failed: {e}")
        return {"tools": [], "error": str(e)}


def _call_health_check() -> dict:
    """Call memory_core health_check directly."""
    try:
        from packages.memory_store.mcp_server import health_check

        result = health_check()
        logger.info(f"health_check: {result.get('status', 'unknown')}")
        return result
    except Exception as e:
        logger.error(f"health_check failed: {e}")
        return {"status": "error", "error": str(e)}


# =============================================================================
# Orchestration MCP - Direct package calls
# =============================================================================


def _call_orchestration_spawn(
    agent: str, task: str, context: dict = None, inject_memory: bool = False
) -> dict:
    """Call orchestration spawn directly."""
    try:
        from packages.orchestration.mcp_server import spawn as orch_spawn

        result = orch_spawn(
            agent=agent, task=task, context=context, inject_memory=inject_memory
        )
        logger.info(f"orchestration_spawn: {result.get('status', 'unknown')}")
        return result
    except Exception as e:
        logger.error(f"orchestration_spawn failed: {e}")
        return {"status": "error", "error": str(e)}


def _call_orchestration_task_status(task_id: str) -> dict:
    """Call orchestration task_status directly."""
    try:
        from packages.orchestration.mcp_server import task_status

        result = task_status(task_id=task_id)
        logger.info(f"orchestration_task_status: {result.get('status', 'unknown')}")
        return result
    except Exception as e:
        logger.error(f"orchestration_task_status failed: {e}")
        return {"status": "error", "error": str(e)}


def _call_orchestration_orchestrate(user_input: str, context: dict = None) -> dict:
    """Call orchestration orchestrate (BMAD workflow) directly."""
    try:
        from packages.orchestration.mcp_server import orchestrate

        result = orchestrate(user_input=user_input, context=context)
        logger.info(f"orchestration_orchestrate: {result.get('status', 'unknown')}")
        return result
    except Exception as e:
        logger.error(f"orchestration_orchestrate failed: {e}")
        return {"status": "error", "error": str(e)}


def _call_orchestration_list_workflows() -> dict:
    """Call orchestration list_workflows directly."""
    try:
        from packages.orchestration.mcp_server import list_workflows

        result = list_workflows()
        logger.info(f"orchestration_list_workflows: {result.get('status', 'unknown')}")
        return result
    except Exception as e:
        logger.error(f"orchestration_list_workflows failed: {e}")
        return {"status": "error", "error": str(e)}


def _call_orchestration_detect_state(user_input: str) -> dict:
    """Call orchestration detect_state directly."""
    try:
        from packages.orchestration.mcp_server import detect_state

        result = detect_state(user_input=user_input)
        logger.info(f"orchestration_detect_state: {result.get('status', 'unknown')}")
        return result
    except Exception as e:
        logger.error(f"orchestration_detect_state failed: {e}")
        return {"status": "error", "error": str(e)}


# =============================================================================
# Learning Engine MCP - Direct package calls
# =============================================================================


def _call_learning_route_task(task_description: str) -> dict:
    """Call learning_engine route_task directly."""
    try:
        from packages.learning_engine.routing.adaptive_router import AdaptiveRouter

        router = AdaptiveRouter()
        result = router.route(task_description)
        logger.info(
            f"learning_route_task: level={result.get('level')}, agent={result.get('agent')}"
        )
        return result
    except Exception as e:
        logger.error(f"learning_route_task failed: {e}")
        # Fallback
        return {
            "level": 3,
            "agent": "hephaestus",
            "confidence": 0.5,
            "reason": f"Fallback: {str(e)[:50]}",
        }


def _call_learning_record_outcome(
    task: str, agent: str, success: bool, latency_ms: float = 0, tokens_used: int = 0
) -> dict:
    """Call learning_engine record_outcome directly."""
    try:
        from packages.learning_engine.mcp_server import record_outcome

        result = record_outcome(
            task=task,
            agent=agent,
            success=success,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
        )
        logger.info(f"learning_record_outcome: {result.get('status', 'unknown')}")
        return result
    except Exception as e:
        logger.error(f"learning_record_outcome failed: {e}")
        return {"status": "error", "error": str(e)}


def _call_learning_get_recommendations(task_description: str) -> dict:
    """Call learning_engine get_recommendations directly."""
    try:
        from packages.learning_engine import get_recommendations

        result = get_recommendations(task_description)
        logger.info("learning_get_recommendations: success")
        return result
    except Exception as e:
        logger.error(f"learning_get_recommendations failed: {e}")
        return {"recommendations": [], "error": str(e)}


# =============================================================================
# Consolidated get_capabilities - All packages
# =============================================================================


def _call_all_capabilities() -> list:
    """Get capabilities from ALL packages, not just memory_core."""
    all_tools = []

    # Memory core tools
    try:
        from packages.memory_store.mcp_server import get_capabilities

        caps = get_capabilities()
        if "tools" in caps:
            for t in caps["tools"]:
                t["package"] = "memory_core"
                all_tools.append(t)
    except Exception as e:
        logger.warning(f"memory_core capabilities failed: {e}")

    # Orchestration tools
    orchestration_tools = [
        {
            "name": "orchestration_spawn",
            "desc": "Spawn agent task",
            "package": "orchestration",
        },
        {
            "name": "orchestration_task_status",
            "desc": "Get task status",
            "package": "orchestration",
        },
        {
            "name": "orchestration_orchestrate",
            "desc": "Run BMAD workflow",
            "package": "orchestration",
        },
        {
            "name": "orchestration_list_workflows",
            "desc": "List available workflows",
            "package": "orchestration",
        },
        {
            "name": "orchestration_detect_state",
            "desc": "Detect user state (FLOW/FRICTION)",
            "package": "orchestration",
        },
    ]
    all_tools.extend(orchestration_tools)

    # Learning engine tools
    learning_tools = [
        {
            "name": "learning_route_task",
            "desc": "Route task to optimal agent",
            "package": "learning_engine",
        },
        {
            "name": "learning_record_outcome",
            "desc": "Record delegation outcome",
            "package": "learning_engine",
        },
        {
            "name": "learning_get_recommendations",
            "desc": "Get agent recommendations",
            "package": "learning_engine",
        },
    ]
    all_tools.extend(learning_tools)

    # nx_brain_mcp tools (unified brain)
    nx_brain_tools = [
        {
            "name": "context_get_active_context",
            "desc": "Get active context",
            "package": "nx_brain_mcp",
        },
        {
            "name": "context_get_product_context",
            "desc": "Get product context",
            "package": "nx_brain_mcp",
        },
        {
            "name": "context_get_user_context",
            "desc": "Get user context",
            "package": "nx_brain_mcp",
        },
        {
            "name": "mind_get_mind_state",
            "desc": "Get MIND state",
            "package": "nx_brain_mcp",
        },
        {
            "name": "mind_get_session_history",
            "desc": "Get session history",
            "package": "nx_brain_mcp",
        },
        {
            "name": "session_pool_stats",
            "desc": "Get session pool stats",
            "package": "nx_brain_mcp",
        },
        {
            "name": "trigger_register",
            "desc": "Register trigger phrase",
            "package": "nx_brain_mcp",
        },
        {"name": "trigger_list", "desc": "List triggers", "package": "nx_brain_mcp"},
        {
            "name": "trigger_check",
            "desc": "Check trigger match",
            "package": "nx_brain_mcp",
        },
        {
            "name": "catalyst_orchestrate",
            "desc": "Orchestrate BMAD workflow",
            "package": "nx_brain_mcp",
        },
        {
            "name": "catalyst_detect_state",
            "desc": "Detect FLOW/FRICTION state",
            "package": "nx_brain_mcp",
        },
        {
            "name": "intelligence_route",
            "desc": "Route task to optimal agent",
            "package": "nx_brain_mcp",
        },
        {
            "name": "intelligence_score_complexity",
            "desc": "Score task complexity L1-L5",
            "package": "nx_brain_mcp",
        },
        {
            "name": "sqlite_query",
            "desc": "Query routing database",
            "package": "nx_brain_mcp",
        },
        {
            "name": "fingerprint_get_session_context",
            "desc": "Get session fingerprint context",
            "package": "nx_brain_mcp",
        },
    ]
    all_tools.extend(nx_brain_tools)

    return all_tools


# =============================================================================
# REST Endpoints
# =============================================================================


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "http-gateway",
        "version": "1.0.0",
        "status": "running",
        "mcp_server": MCP_SERVER_URL,
    }


@app.get("/tools_list")
async def tools_list():
    """Return list of available agents/tools from ALL packages."""
    all_tools = _call_all_capabilities()
    if all_tools:
        return {
            "agents": [
                {
                    "name": t["name"],
                    "description": t.get("desc", ""),
                    "package": t.get("package", "unknown"),
                }
                for t in all_tools
            ],
            "backendAvailable": True,
            "total_count": len(all_tools),
        }

    return {
        "agents": [
            {"name": "sisyphus", "description": "Primary orchestrator"},
            {"name": "hephaestus", "description": "Implementation agent"},
            {"name": "oracle", "description": "Architecture reviewer"},
            {"name": "prometheus", "description": "Plan builder"},
            {"name": "metis", "description": "Pre-planning consultant"},
            {"name": "momus", "description": "Red-team reviewer"},
            {"name": "atlas", "description": "Plan executor"},
            {"name": "explore", "description": "Codebase search"},
            {"name": "librarian", "description": "External research"},
            {"name": "multimodal_looker", "description": "Vision agent"},
        ],
        "backendAvailable": False,
        "total_count": 10,
    }


@app.get("/api/registry/agents")
async def registry_agents():
    """Registry agents endpoint for frontend compatibility."""
    result = _call_all_capabilities()
    agents = (
        [
            {"id": t["name"].replace("_", "-"), "name": t["name"], "status": "idle"}
            for t in result
        ]
        if result
        else [
            {"id": "sisyphus", "name": "Sisyphus", "status": "idle"},
            {"id": "hephaestus", "name": "Hephaestus", "status": "idle"},
            {"id": "oracle", "name": "Oracle", "status": "idle"},
            {"id": "prometheus", "name": "Prometheus", "status": "idle"},
            {"id": "metis", "name": "Metis", "status": "idle"},
            {"id": "momus", "name": "Momus", "status": "idle"},
            {"id": "atlas", "name": "Atlas", "status": "idle"},
            {"id": "explore", "name": "Explore", "status": "idle"},
            {"id": "librarian", "name": "Librarian", "status": "idle"},
        ]
    )
    return {"status": "ok", "data": agents}


@app.post("/memory_get")
async def memory_get(request: MemoryGetRequest):
    """Search memories.

    Maps to frontend call: POST /memory_get
    """
    result = _call_memory_search(query=request.query, limit=request.limit)
    return result


@app.post("/memory_write")
async def memory_write(request: MemoryWriteRequest):
    """Write memory.

    Maps to frontend call: POST /memory_write
    """
    result = _call_memory_write(
        content=request.content, kind=request.kind, scope=request.scope
    )
    return result


@app.get("/memory_stats")
async def memory_stats():
    """Get memory statistics."""
    result = _call_memory_stats()
    return result


@app.post("/recall_session")
async def recall_session(session_id: str = None, limit: int = 50):
    """Recall session context."""
    result = _call_recall_session(session_id=session_id, limit=limit)
    return result


@app.post("/find_context")
async def find_context(task: str, context_type: str = "all"):
    """Find relevant context for a task."""
    result = _call_find_context(task=task, context_type=context_type)
    return result


@app.get("/system_health_check")
async def system_health_check():
    """Health check endpoint.

    Maps to frontend call: GET /api/backend/mcp -> /system_health_check
    """
    result = _call_health_check()
    return {
        "connections": [
            {
                "name": "Memory MCP",
                "status": "connected" if result.get("status") != "error" else "error",
            },
            {"name": "Orchestration MCP", "status": "connected"},
        ],
        "backendAvailable": result.get("status") != "error",
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }


@app.post("/route_task")
async def route_task(request: RouteTaskRequest):
    """Route task to optimal agent.

    Maps to frontend call: POST /route_task
    """
    result = _call_learning_route_task(task_description=request.task_description)
    return result


@app.post("/orchestration_spawn")
async def orchestration_spawn(request: OrchestrationSpawnRequest):
    """Spawn agent task via orchestration."""
    result = _call_orchestration_spawn(
        agent=request.agent,
        task=request.task,
        context=request.context or {},
        inject_memory=request.inject_memory,
    )
    return result


@app.get("/orchestration_task_status/{task_id}")
async def orchestration_task_status(task_id: str):
    """Get orchestration task status."""
    result = _call_orchestration_task_status(task_id=task_id)
    return result


@app.post("/orchestration_orchestrate")
async def orchestration_orchestrate(request: OrchestrationOrchestrateRequest):
    """Run BMAD workflow via orchestration."""
    result = _call_orchestration_orchestrate(
        user_input=request.user_input, context=request.context or {}
    )
    return result


@app.get("/orchestration_workflows")
async def orchestration_workflows():
    """List available BMAD workflows."""
    result = _call_orchestration_list_workflows()
    return result


@app.post("/orchestration_detect_state")
async def orchestration_detect_state(request: DetectStateRequest):
    """Detect user state (FLOW/FRICTION/ADAPT)."""
    result = _call_orchestration_detect_state(user_input=request.user_input)
    return result


@app.post("/learning_record_outcome")
async def learning_record_outcome(request: LearningRecordOutcomeRequest):
    """Record delegation outcome for learning."""
    result = _call_learning_record_outcome(
        task=request.task,
        agent=request.agent,
        success=request.success,
        latency_ms=request.latency_ms,
        tokens_used=request.tokens_used,
    )
    return result


@app.get("/learning_recommendations/{task_description}")
async def learning_recommendations(task_description: str):
    """Get agent recommendations for a task."""
    result = _call_learning_get_recommendations(task_description=task_description)
    return result


def _call_session_pool_stats() -> dict:
    try:
        from packages.brain_mcp.namespaces.mind import session_pool_stats

        result = session_pool_stats()
        logger.info("session_pool_stats: success")
        return result
    except Exception as e:
        logger.error(f"session_pool_stats failed: {e}")
        return {"status": "error", "error": str(e)}


@app.get("/session_pool_stats")
async def get_session_pool_stats():
    result = _call_session_pool_stats()
    return result


# =============================================================================
# Main
# =============================================================================


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting HTTP Gateway on port {PORT}")
    logger.info(f"MCP Server URL: {MCP_SERVER_URL}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info",
    )

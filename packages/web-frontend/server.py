"""N-Xyme MIND Web Frontend Backend Server.

FastAPI server on port 3000 - exposes MCP tools as HTTP endpoints.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Add project root to Python path
ROOT = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
# ROOT is defined at top of file
PORT = 8000

# Create FastAPI app
app = FastAPI(
    title="N-Xyme MIND Web Frontend",
    description="HTTP API for MCP tools and system integration",
    version="1.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# WebSocket Connection Manager
# =============================================================================


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()


# =============================================================================
# Health Endpoints
# =============================================================================


@app.get("/api/health")
async def health() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "ok", "message": "healthy"})


# =============================================================================
# WebSocket Endpoints
# =============================================================================


@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, wait for messages
            data = await websocket.receive_text()
            # Echo back for now (can be extended for commands)
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/api/broadcast")
async def broadcast_message(message: dict) -> JSONResponse:
    """Broadcast a message to all WebSocket clients."""
    await manager.broadcast(message)
    return JSONResponse({"status": "broadcast_sent"})


@app.get("/ws/health")
async def ws_health() -> JSONResponse:
    """WebSocket connection health."""
    return JSONResponse(
        {"status": "ok", "active_connections": len(manager.active_connections)}
    )


# =============================================================================
# Chat Proxy Endpoints (proxy to port 8080)
# =============================================================================


@app.get("/api/chat/models")
async def get_models() -> JSONResponse:
    """Get available models from opencode.json providers + Ollama."""
    try:
        from packages.learning_engine.mcp_server import learning_stats

        stats = learning_stats()

        # Get models from opencode.json enabled_providers
        path = ROOT / "opencode.json"
        provider_models = []
        if path.exists():
            data = json.loads(path.read_text())
            enabled = data.get("enabled_providers", [])
            # Map providers to model names (simplified list)
            provider_map = {
                "opencode": [
                    "minimax-m2.5-free",
                    "mimo-v2-pro-free",
                    "qwen3.6-plus-free",
                ],
                "openrouter": [
                    "openrouter/calude-3-5-sonnet",
                    "openrouter/qwen-2.5-coder-32b",
                ],
                "anthropic": ["claude-3-5-sonnet-20241022"],
                "google": ["gemini-2.0-flash-exp"],
                "deepseek": ["deepseek-chat"],
                "xai": ["grok-2"],
                "cohere": ["command-r-plus"],
                "ollama": [],  # Will be fetched separately
                "lmstudio": [],  # Will be fetched separately
                "gguf": [],  # Will be fetched separately
            }
            for p in enabled:
                if p in provider_map:
                    provider_models.extend(provider_map[p])

        # Get Ollama models
        ollama_models = []
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:11434/api/tags")
                if response.status_code == 200:
                    ollama_models = [
                        m.get("name") for m in response.json().get("models", [])
                    ]
        except httpx.RequestError as e:
            logger.debug(f"Ollama not available: {e}")

        all_models = provider_models + ollama_models
        return JSONResponse(
            {
                "status": "ok",
                "models": all_models,
                "ollama": ollama_models,
                "providers": provider_models,
                "stats": stats,
            }
        )
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/chat/completions")
async def chat_completions(request: dict) -> JSONResponse:
    """Proxy to port 11434 (Ollama) /v1/chat/completions."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "http://localhost:11434/v1/chat/completions", json=request
            )
            response.raise_for_status()
            return JSONResponse(response.json())
    except Exception as e:
        logger.error(f"Error in chat completions: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# =============================================================================
# Memory Endpoints (7 tools)
# =============================================================================


@app.get("/api/memory/search")
async def search_memories(
    query: str = "",
    limit: int = 10,
    strict: bool = False,
    rerank: bool = False,
    trust_weight: float = 0.0,
) -> JSONResponse:
    """Search memory using search_memories function."""
    try:
        from packages.memory_store.mcp_server import search_memories

        result = search_memories(
            query=query,
            limit=limit,
            strict=strict,
            rerank=rerank,
            trust_weight=trust_weight,
        )
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/api/memory/stats")
async def memory_stats() -> JSONResponse:
    """Get memory statistics."""
    try:
        from packages.memory_store.mcp_server import get_memory_stats

        result = get_memory_stats()
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


@app.post("/api/memory/write")
async def memory_write(request: dict) -> JSONResponse:
    """Write to memory."""
    try:
        from packages.memory_store.mcp_server import memory_write

        content = request.get("content", "")
        kind = request.get("kind", "episodic")
        scope = request.get("scope", "global")
        result = memory_write(content=content, kind=kind, scope=scope)
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error writing memory: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: recall_session
@app.get("/api/memory/recall")
async def recall_session(
    session_id: Optional[str] = Query(None), limit: int = 50
) -> JSONResponse:
    """Recall session context."""
    try:
        from packages.memory_store.mcp_server import recall_session

        result = recall_session(session_id=session_id, limit=limit)
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error recalling session: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: find_context
@app.get("/api/memory/context")
async def find_context(
    task: str = "", context_type: str = "all", trust_weight: float = 0.0
) -> JSONResponse:
    """Find relevant context for a task."""
    try:
        from packages.memory_store.mcp_server import find_context

        result = find_context(
            task=task, context_type=context_type, trust_weight=trust_weight
        )
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error finding context: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: router_search (memory_search)
@app.get("/api/memory/router-search")
async def router_search(
    query: str = "", top_k: int = 10, trust_weight: float = 0.0
) -> JSONResponse:
    """Search memory using MemoryRouter."""
    try:
        from packages.memory_store.mcp_server import memory_search

        result = memory_search(query=query, top_k=top_k, trust_weight=trust_weight)
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error in router search: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: comprehensive_stats
@app.get("/api/memory/comprehensive-stats")
async def comprehensive_stats() -> JSONResponse:
    """Get comprehensive memory statistics."""
    try:
        from packages.memory_store.mcp_server import memory_stats

        result = memory_stats()
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error getting comprehensive stats: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: unified search
@app.get("/api/memory/unified/search")
async def unified_search(query: str = "", limit: int = 10) -> JSONResponse:
    """Search across all memory sources."""
    try:
        from packages.unified_memory.mcp_server import search_memories

        result = search_memories(query=query, limit=limit)
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error in unified search: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# =============================================================================
# Learning Endpoints (9 tools + dashboard)
# =============================================================================


@app.get("/api/routing/route")
async def route_task(task: str = "") -> JSONResponse:
    """Route a task using route_task function."""
    try:
        from packages.learning_engine.mcp_server import route_task

        result = route_task(task_description=task)
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error routing task: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: record_outcome
@app.post("/api/learning/record")
async def record_outcome(request: dict) -> JSONResponse:
    """Record a delegation outcome for learning."""
    try:
        from packages.learning_engine.mcp_server import record_outcome

        task = request.get("task", "")
        agent = request.get("agent", "")
        success = request.get("success", False)
        latency_ms = request.get("latency_ms", 0)
        tokens_used = request.get("tokens_used", 0)
        result = record_outcome(
            task=task,
            agent=agent,
            success=success,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
        )
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error recording outcome: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: status
@app.get("/api/learning/status")
async def learning_status() -> JSONResponse:
    """Get current learning system status."""
    try:
        from packages.learning_engine.mcp_server import status

        result = status()
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error getting learning status: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: retrain
@app.post("/api/learning/retrain")
async def retrain() -> JSONResponse:
    """Trigger retraining of learning models."""
    try:
        from packages.learning_engine.mcp_server import retrain

        result = retrain()
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error retraining: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: recommendations
@app.get("/api/learning/recommendations")
async def get_recommendations(task_description: str = "") -> JSONResponse:
    """Get agent recommendations for a task."""
    try:
        from packages.learning_engine.mcp_server import get_recommendations

        result = get_recommendations(task_description=task_description)
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/api/routing/stats")
async def routing_stats() -> JSONResponse:
    """Get learning statistics."""
    try:
        from packages.learning_engine.mcp_server import learning_stats

        result = learning_stats()

        # Recursively convert any LearningStats object to dict
        def convert_to_json_serializable(obj):
            if hasattr(obj, "__dataclass_fields__"):
                # It's a dataclass - convert to dict
                result = {}
                for field in obj.__dataclass_fields__:
                    value = getattr(obj, field)
                    result[field] = convert_to_json_serializable(value)
                return result
            elif isinstance(obj, dict):
                return {k: convert_to_json_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_json_serializable(item) for item in obj]
            else:
                return obj

        converted = convert_to_json_serializable(result)
        return JSONResponse({"status": "ok", "data": converted})
    except Exception as e:
        logger.error(f"Error getting routing stats: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: log_outcome
@app.post("/api/learning/log")
async def log_outcome(request: dict) -> JSONResponse:
    """Log a delegation outcome."""
    try:
        from packages.learning_engine.mcp_server import log_outcome

        task_id = request.get("task_id", "")
        task_description = request.get("task_description", "")
        task_type = request.get("task_type", "implementation")
        agent = request.get("agent", "")
        level = request.get("level", 3)
        success = request.get("success", False)
        latency_ms = request.get("latency_ms", 0)
        tokens_used = request.get("tokens_used", 0)
        result = log_outcome(
            task_id=task_id,
            task_description=task_description,
            task_type=task_type,
            agent=agent,
            level=level,
            success=success,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
        )
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error logging outcome: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/api/routing/outcomes")
async def routing_outcomes(
    agent: Optional[str] = None, task_type: Optional[str] = None, limit: int = 100
) -> JSONResponse:
    """Get delegation outcomes."""
    try:
        from packages.learning_engine.mcp_server import get_outcomes

        result = get_outcomes(agent=agent, task_type=task_type, limit=limit)
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error getting outcomes: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: get_learning_progress
@app.get("/api/learning/progress")
async def get_learning_progress() -> JSONResponse:
    """Get real-time learning progress statistics."""
    try:
        from packages.learning_engine.outcome_logger import OutcomeLogger

        logger = OutcomeLogger()

        # Get basic stats - use correct method name
        outcomes = logger.get_outcomes(limit=100)

        # Calculate progress metrics
        total = len(outcomes)
        success_count = sum(1 for o in outcomes if o.success)
        success_rate = (success_count / total * 100) if total > 0 else 0

        # Get agent performance
        agent_stats = logger.get_all_agent_stats()
        top_performers = sorted(
            agent_stats.items(), key=lambda x: x[1].get("success_rate", 0), reverse=True
        )[:3]

        return JSONResponse(
            {
                "status": "ok",
                "data": {
                    "total_decisions": total,
                    "success_rate": round(success_rate, 2),
                    "convergence": "active" if total < 50 else "converged",
                    "top_performers": [
                        {"agent": a, "rate": s.get("success_rate", 0)}
                        for a, s in top_performers
                    ],
                    "recent_reward_trend": "positive"
                    if success_rate > 50
                    else "developing",
                },
            }
        )
    except Exception as e:
        logger.error(f"Error getting learning progress: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# =============================================================================
# Intelligence Endpoints (4 tools)
# =============================================================================


@app.get("/api/intelligence/route")
async def intelligence_route(task: str = "") -> JSONResponse:
    """Route a task using intelligence route function."""
    try:
        from packages.intelligence.mcp_server import route

        result = await route(task_description=task)
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error in intelligence route: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: score_complexity
@app.get("/api/intelligence/score")
async def score_complexity(task_description: str = "") -> JSONResponse:
    """Score the complexity of a task (L1-L5)."""
    try:
        from packages.intelligence.mcp_server import score_complexity

        result = score_complexity(task_description=task_description)
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error scoring complexity: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/api/intelligence/agents")
async def available_agents() -> JSONResponse:
    """Get available agents."""
    try:
        from packages.intelligence.mcp_server import available_agents

        result = available_agents()
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error getting agents: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: get_routing_history
@app.get("/api/intelligence/history")
async def get_routing_history(limit: int = 10) -> JSONResponse:
    """Get recent routing decisions."""
    try:
        from packages.intelligence.mcp_server import get_routing_history

        result = get_routing_history(limit=limit)
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error getting routing history: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# =============================================================================
# Orchestration Endpoints (4 tools)
# =============================================================================


@app.get("/api/orchestration/spawn")
async def spawn_agent(
    agent: str = "", task: str = "", context: str = ""
) -> JSONResponse:
    """Spawn an agent task."""
    try:
        from packages.orchestration.mcp_server import spawn

        result = spawn(agent=agent, task=task, context=context)
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error spawning agent: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: task_status
@app.get("/api/orchestration/status/{task_id}")
async def task_status(task_id: str) -> JSONResponse:
    """Get status of a specific task."""
    try:
        from packages.orchestration.mcp_server import task_status

        result = task_status(task_id=task_id)
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/api/orchestration/tools")
async def list_tools() -> JSONResponse:
    """List available tools."""
    try:
        from packages.orchestration.tools.registry import registry

        result = registry.get_tool_list()
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: execute tool
@app.post("/api/tools/execute")
async def execute_tool(request: dict) -> JSONResponse:
    """Execute a tool from the registry."""
    try:
        from packages.orchestration.tools.registry import registry

        tool_name = request.get("tool")
        params = request.get("parameters", {})

        if not tool_name:
            return JSONResponse(
                {"status": "error", "message": "tool name required"}, status_code=400
            )

        # Get tool from registry
        tool = registry.get_tool(tool_name)
        if not tool:
            return JSONResponse(
                {"status": "error", "message": f"Tool '{tool_name}' not found"},
                status_code=404,
            )

        # Execute tool
        result = tool.execute(**params) if hasattr(tool, "execute") else tool(**params)
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error executing tool: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: execute skill
@app.post("/api/skills/execute")
async def execute_skill(request: dict) -> JSONResponse:
    """Execute a skill from the registry."""
    try:
        skill_id = request.get("skill_id")
        params = request.get("parameters", {})

        if not skill_id:
            return JSONResponse(
                {"status": "error", "message": "skill_id required"}, status_code=400
            )

        # Try intelligence registry
        try:
            from packages.intelligence.skill_registry import get_skill_registry

            registry = get_skill_registry()
            skill = registry.get_skill(skill_id)
            if skill:
                result = (
                    skill.execute(**params)
                    if hasattr(skill, "execute")
                    else {"message": "Skill executed"}
                )
                return JSONResponse({"status": "ok", "data": result})
        except httpx.RequestError as e:
            logger.debug(f"Ollama not available: {e}")

        # Try learning engine registry
        try:
            from packages.learning_engine.skill_registry import (
                get_registry as get_le_registry,
            )

            le_registry = get_le_registry()
            skills = le_registry.list_skills()
            if skill_id in skills:
                return JSONResponse(
                    {
                        "status": "ok",
                        "data": {"message": f"Skill '{skill_id}' available"},
                    }
                )
        except httpx.RequestError as e:
            logger.debug(f"Ollama not available: {e}")

        return JSONResponse(
            {"status": "error", "message": f"Skill '{skill_id}' not found"},
            status_code=404,
        )
    except Exception as e:
        logger.error(f"Error executing skill: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: rate message
@app.post("/api/learning/rate-message")
async def rate_message(request: dict) -> JSONResponse:
    """Record message rating for learning."""
    try:
        from packages.learning_engine.outcome_logger import OutcomeLogger

        task_id = request.get("task_id", "")
        task_description = request.get("task_description", "")
        task_type = request.get("task_type", "chat")
        agent = request.get("agent", "chat")
        level = request.get("level", 3)
        success = request.get("success", True)  # True = thumbs up, False = thumbs down
        latency_ms = request.get("latency_ms", 0)

        logger = OutcomeLogger()
        result = logger.log_outcome(
            task_id=task_id or f"msg_{hash(task_description)}",
            task_description=task_description,
            task_type=task_type,
            agent=agent,
            level=level,
            success=success,
            latency_ms=latency_ms,
        )
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error rating message: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: get_session_state
@app.get("/api/orchestration/session")
async def get_session_state() -> JSONResponse:
    """Get current orchestration session state."""
    try:
        path = ROOT / ".sisyphus" / "session-state.json"
        if path.exists():
            data = json.loads(path.read_text())
            return JSONResponse({"status": "ok", "data": data})
        return JSONResponse({"status": "ok", "data": {"message": "No session state"}})
    except Exception as e:
        logger.error(f"Error getting session state: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# =============================================================================
# Sessions Endpoints
# =============================================================================


# NEW: list sessions
@app.get("/api/sessions/list")
async def list_sessions() -> JSONResponse:
    """List all sessions."""
    try:
        from session_manager import session_list

        sessions = session_list(limit=50)
        return JSONResponse({"status": "ok", "data": sessions})
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        # Fallback: return from session-state.json
        try:
            path = ROOT / ".sisyphus" / "session-state.json"
            if path.exists():
                data = json.loads(path.read_text())
                return JSONResponse(
                    {"status": "ok", "data": [{"session_id": "current", "data": data}]}
                )
        except httpx.RequestError as e:
            logger.debug(f"Ollama not available: {e}")
        return JSONResponse({"status": "ok", "data": []})


@app.get("/api/sessions")
async def sessions() -> JSONResponse:
    """Get current session state (legacy)."""
    try:
        path = ROOT / ".sisyphus" / "session-state.json"
        if path.exists():
            data = json.loads(path.read_text())
            return JSONResponse({"status": "ok", "data": data})
        return JSONResponse({"status": "error", "message": "No session state found"})
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: get session by ID
@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> JSONResponse:
    """Get a specific session."""
    try:
        from session_manager import session_read

        session = session_read(session_id=session_id)
        return JSONResponse({"status": "ok", "data": session})
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# =============================================================================
# Settings Endpoints
# =============================================================================


# NEW: get settings
@app.get("/api/settings")
async def get_settings() -> JSONResponse:
    """Get comprehensive settings from all backends."""
    try:
        settings = {
            "port": PORT,
            "theme": "dark",
            "refresh_interval": 30000,
            "api_base": "/api",
            "agents": [],
            "tools": [],
            "skills": [],
            "mcps": [],
            "models": [],
        }

        # Load agents
        try:
            from packages.orchestration.agents.registry import get_agent_registry

            registry = get_agent_registry()
            settings["agents"] = list(registry.get_all_agents().keys())
        except httpx.RequestError as e:
            logger.debug(f"Ollama not available: {e}")

        # Load tools
        try:
            from packages.orchestration.tools.registry import registry as tool_reg

            settings["tools"] = [
                t.get("name", "unknown") for t in tool_reg.get_tool_list()
            ]
        except httpx.RequestError as e:
            logger.debug(f"Ollama not available: {e}")

        # Load skills
        try:
            from packages.intelligence.skill_registry import get_skill_registry

            int_reg = get_skill_registry()
            settings["skills"] = list(int_reg.get_all_skills().keys())
        except httpx.RequestError as e:
            logger.debug(f"Ollama not available: {e}")

        # Load MCPs
        try:
            path = ROOT / "opencode.json"
            if path.exists():
                data = json.loads(path.read_text())
                settings["mcps"] = list(data.get("mcp", {}).keys())
        except httpx.RequestError as e:
            logger.debug(f"Ollama not available: {e}")

        # Load models
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:11434/api/tags")
                if response.status_code == 200:
                    settings["models"] = [
                        m.get("name") for m in response.json().get("models", [])
                    ]
        except Exception as e:
            logger.warning(f"Could not fetch Ollama models: {e}")
            settings["models"] = ["llama3.2:3b", "qwen2.5-coder:7b"]  # Fallback

        return JSONResponse({"status": "ok", "data": settings})
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        return JSONResponse(
            {
                "status": "ok",
                "data": {
                    "port": PORT,
                    "theme": "dark",
                    "refresh_interval": 30000,
                    "api_base": "/api",
                    "agents": [],
                    "tools": [],
                    "skills": [],
                    "mcps": [],
                    "models": [],
                },
            }
        )


# NEW: save settings
@app.post("/api/settings")
async def save_settings(request: dict) -> JSONResponse:
    """Save settings."""
    # In a real app, persist to file
    logger.info(f"Settings updated: {request}")
    return JSONResponse({"status": "ok", "message": "Settings saved"})


# =============================================================================
# Model Management Endpoints (GGUF + Ollama)
# =============================================================================


MODELS_DIR = ROOT / "models"


@app.get("/api/models/local")
async def get_local_models() -> JSONResponse:
    """List available GGUF models from models directory."""
    try:
        if not MODELS_DIR.exists():
            return JSONResponse({"status": "ok", "models": []})

        gguf_files = []
        for f in MODELS_DIR.iterdir():
            if f.is_file() and f.suffix.lower() == ".gguf":
                size_mb = f.stat().st_size / (1024 * 1024)
                gguf_files.append(
                    {"name": f.name, "path": str(f), "size_mb": round(size_mb, 2)}
                )

        return JSONResponse({"status": "ok", "models": gguf_files})
    except Exception as e:
        logger.error(f"Error getting local models: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/api/models/ollama")
async def get_ollama_models() -> JSONResponse:
    """Get models from Ollama at localhost:11434."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                return JSONResponse(
                    {
                        "status": "ok",
                        "models": [
                            {
                                "name": m.get("name"),
                                "size": m.get("size"),
                                "modified": m.get("modified_at"),
                            }
                            for m in models
                        ],
                    }
                )
            return JSONResponse(
                {"status": "ok", "models": [], "message": "Ollama not running"}
            )
    except Exception as e:
        logger.warning(f"Ollama not available: {e}")
        return JSONResponse(
            {"status": "ok", "models": [], "message": "Ollama not available"}
        )


@app.post("/api/models/load")
async def load_model(request: dict) -> JSONResponse:
    """Load a specific model."""
    try:
        model_name = request.get("model_name", "")
        backend = request.get("backend", "ollama")

        if not model_name:
            return JSONResponse(
                {"status": "error", "message": "model_name required"}, status_code=400
            )

        if backend == "ollama":
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Check if model exists or pull it
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={"model": model_name, "prompt": "test", "stream": False},
                )
                if response.status_code == 200:
                    return JSONResponse(
                        {"status": "ok", "message": f"Model {model_name} loaded"}
                    )
                return JSONResponse(
                    {"status": "error", "message": "Failed to load model"},
                    status_code=500,
                )

        return JSONResponse(
            {"status": "error", "message": f"Unknown backend: {backend}"},
            status_code=400,
        )
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/api/models/status")
async def get_model_status() -> JSONResponse:
    """Get current loaded model status."""
    try:
        # Check Ollama
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                data = response.json()
                return JSONResponse(
                    {
                        "status": "ok",
                        "loaded": True,
                        "backend": "ollama",
                        "models": [m.get("name") for m in data.get("models", [])],
                    }
                )

        return JSONResponse(
            {"status": "ok", "loaded": False, "backend": None, "models": []}
        )
    except Exception as e:
        logger.warning(f"Model status check failed: {e}")
        return JSONResponse(
            {"status": "ok", "loaded": False, "backend": None, "models": []}
        )


# =============================================================================
# Agents Endpoints
# =============================================================================


@app.get("/api/agents")
async def agents() -> JSONResponse:
    """Get agent definitions from opencode.json."""
    try:
        path = ROOT / "opencode.json"
        if path.exists():
            data = json.loads(path.read_text())
            return JSONResponse({"status": "ok", "data": data.get("agent", {})})
        return JSONResponse({"status": "error", "message": "opencode.json not found"})
    except Exception as e:
        logger.error(f"Error getting agents: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# =============================================================================
# Registry Endpoints - Self-Adaptive Dashboard Discovery
# =============================================================================


@app.get("/api/registry/agents")
async def get_registry_agents() -> JSONResponse:
    """Get all agents from AgentRegistry - enables dynamic agent discovery."""
    try:
        from packages.orchestration.agents.registry import get_agent_registry

        registry = get_agent_registry()
        agents = registry.get_all_agents()
        return JSONResponse({"status": "ok", "data": agents})
    except Exception as e:
        logger.error(f"Error getting agents from registry: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/api/registry/agent-status")
async def get_registry_agent_status() -> JSONResponse:
    """Get agent registry status."""
    try:
        from packages.orchestration.agents.registry import get_agent_registry

        registry = get_agent_registry()
        status = registry.get_status()
        return JSONResponse({"status": "ok", "data": status})
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/api/registry/tools")
async def get_registry_tools() -> JSONResponse:
    """Get all tools from ToolRegistry - enables dynamic tool discovery.

    Falls back to auto-discovery from MCP servers if registry is empty.
    """
    try:
        from packages.orchestration.tools.registry import registry

        tools = registry.get_tool_list()

        # If registry is empty, try auto-discovery from MCP servers
        if not tools:
            tools = _discover_tools_from_mcp_servers()

        return JSONResponse({"status": "ok", "data": tools})
    except Exception as e:
        logger.error(f"Error getting tools from registry: {e}")
        # Fallback: try auto-discovery on error too
        try:
            tools = _discover_tools_from_mcp_servers()
            return JSONResponse({"status": "ok", "data": tools})
        except Exception as fallback_error:
            return JSONResponse({"status": "error", "message": str(fallback_error)})


def _discover_tools_from_mcp_servers() -> list:
    """Auto-discover tools from MCP servers and other sources."""
    discovered = []

    # 1. Try memory_core MCP tools - discover via introspection
    try:
        from packages.memory_store import mcp_server as mem_mcp

        # Get all functions decorated with @mcp.tool
        for name in dir(mem_mcp):
            obj = getattr(mem_mcp, name)
            if callable(obj) and hasattr(obj, "tags"):
                # This is a tool function
                discovered.append(
                    {
                        "name": name,
                        "description": obj.__doc__ or "",
                        "input_schema": {},
                        "is_read_only": True,
                        "is_concurrency_safe": True,
                        "is_destructive": False,
                        "category": "memory",
                    }
                )
    except Exception as e:
        logger.debug(f"Could not get memory_core tools: {e}")

    # 2. Try intelligence MCP tools
    try:
        from packages.intelligence import mcp_server as int_mcp

        for name in dir(int_mcp):
            obj = getattr(int_mcp, name)
            if callable(obj) and hasattr(obj, "tags"):
                discovered.append(
                    {
                        "name": name,
                        "description": obj.__doc__ or "",
                        "input_schema": {},
                        "is_read_only": True,
                        "is_concurrency_safe": True,
                        "is_destructive": False,
                        "category": "intelligence",
                    }
                )
    except Exception as e:
        logger.debug(f"Could not get intelligence tools: {e}")

    # 3. Try orchestration tools registry
    try:
        from packages.orchestration.tools import registry as orch_tools

        orch_list = orch_tools.get_tool_list()
        for tool in orch_list:
            tool["category"] = "orchestration"
            discovered.append(tool)
    except Exception as e:
        logger.debug(f"Could not get orchestration tools: {e}")

    # 4. Get learning engine endpoints from server.py itself (they're already API endpoints)
    learning_endpoints = [
        {
            "name": "route_task",
            "description": "Route a task to optimal agent",
            "input_schema": {"task_description": {"type": "string"}},
            "category": "learning",
        },
        {
            "name": "record_outcome",
            "description": "Record delegation outcome for learning",
            "input_schema": {
                "task": {"type": "string"},
                "success": {"type": "boolean"},
            },
            "category": "learning",
        },
        {
            "name": "learning_stats",
            "description": "Get learning/routing statistics",
            "input_schema": {},
            "category": "learning",
        },
        {
            "name": "available_agents",
            "description": "Get list of available agents",
            "input_schema": {},
            "category": "learning",
        },
    ]
    for tool in learning_endpoints:
        tool["is_read_only"] = True
        tool["is_concurrency_safe"] = True
        tool["is_destructive"] = False
        discovered.append(tool)

    # 5. Get model/chat endpoints as tools
    model_endpoints = [
        {
            "name": "get_models",
            "description": "Get available models",
            "input_schema": {},
            "category": "models",
        },
        {
            "name": "chat_completions",
            "description": "Send chat completion request",
            "input_schema": {
                "model": {"type": "string"},
                "messages": {"type": "array"},
            },
            "category": "models",
        },
        {
            "name": "get_local_models",
            "description": "Get local GGUF models",
            "input_schema": {},
            "category": "models",
        },
    ]
    for tool in model_endpoints:
        tool["is_read_only"] = True
        tool["is_concurrency_safe"] = True
        tool["is_destructive"] = False
        discovered.append(tool)

    # 6. Get orchestration endpoints as tools
    orchestration_endpoints = [
        {
            "name": "spawn_agent",
            "description": "Spawn an agent task",
            "input_schema": {"agent": {"type": "string"}, "task": {"type": "string"}},
            "category": "orchestration",
        },
        {
            "name": "task_status",
            "description": "Get status of a task",
            "input_schema": {"task_id": {"type": "string"}},
            "category": "orchestration",
        },
        {
            "name": "list_tools",
            "description": "List available tools",
            "input_schema": {},
            "category": "orchestration",
        },
    ]
    for tool in orchestration_endpoints:
        tool["is_read_only"] = True
        tool["is_concurrency_safe"] = True
        tool["is_destructive"] = False
        discovered.append(tool)

    # 7. Fallback: return common system tools if nothing found
    if not discovered:
        discovered = [
            {
                "name": "memory_search",
                "description": "Search memory",
                "input_schema": {"query": {"type": "string"}},
                "is_read_only": True,
                "is_concurrency_safe": True,
                "is_destructive": False,
                "category": "system",
            },
            {
                "name": "memory_write",
                "description": "Write to memory",
                "input_schema": {"content": {"type": "string"}},
                "is_read_only": False,
                "is_concurrency_safe": True,
                "is_destructive": False,
                "category": "system",
            },
            {
                "name": "route_task",
                "description": "Route a task to optimal agent",
                "input_schema": {"task_description": {"type": "string"}},
                "is_read_only": True,
                "is_concurrency_safe": True,
                "is_destructive": False,
                "category": "system",
            },
            {
                "name": "spawn_agent",
                "description": "Spawn an agent task",
                "input_schema": {
                    "agent": {"type": "string"},
                    "task": {"type": "string"},
                },
                "is_read_only": False,
                "is_concurrency_safe": True,
                "is_destructive": False,
                "category": "system",
            },
            {
                "name": "get_models",
                "description": "Get available models",
                "input_schema": {},
                "is_read_only": True,
                "is_concurrency_safe": True,
                "is_destructive": False,
                "category": "system",
            },
            {
                "name": "learning_stats",
                "description": "Get learning statistics",
                "input_schema": {},
                "is_read_only": True,
                "is_concurrency_safe": True,
                "is_destructive": False,
                "category": "system",
            },
        ]

    logger.info(f"Discovered {len(discovered)} tools from auto-discovery")
    return discovered


@app.get("/api/registry/skills")
async def get_registry_skills() -> JSONResponse:
    """Get all skills from SkillRegistries - enables dynamic skill discovery."""
    try:
        result = {"learning_engine": [], "intelligence": []}

        # Learning Engine skills
        try:
            from packages.learning_engine.skill_registry import (
                get_registry as get_le_registry,
            )

            le_registry = get_le_registry()
            result["learning_engine"] = le_registry.list_skills()
        except Exception as e:
            logger.warning(f"Error getting learning_engine skills: {e}")

        # Intelligence skills
        try:
            from packages.intelligence.skill_registry import get_skill_registry

            int_registry = get_skill_registry()
            int_skills = int_registry.get_all_skills()
            result["intelligence"] = {
                k: {
                    "name": v.name,
                    "category": v.category,
                    "description": v.description,
                }
                for k, v in int_skills.items()
            }
        except Exception as e:
            logger.warning(f"Error getting intelligence skills: {e}")

        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error getting skills from registry: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/api/registry/mcps")
async def get_registry_mcps() -> JSONResponse:
    """Get MCP configuration from opencode.json - enables dynamic MCP discovery."""
    try:
        path = ROOT / "opencode.json"
        if path.exists():
            data = json.loads(path.read_text())
            mcp_config = data.get("mcp", {})
            return JSONResponse({"status": "ok", "data": mcp_config})
        return JSONResponse({"status": "error", "message": "opencode.json not found"})
    except Exception as e:
        logger.error(f"Error getting MCP config: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# =============================================================================
# MCP Management Endpoints (start/stop/status)
# =============================================================================

import subprocess

MCP_PID_DIR = ROOT / ".sisyphus" / "mcp_pids"


@app.post("/api/mcps/{mcp_name}/start")
async def start_mcp(mcp_name: str) -> JSONResponse:
    """Start an MCP server."""
    try:
        # Read MCP config
        path = ROOT / "opencode.json"
        if not path.exists():
            return JSONResponse(
                {"status": "error", "message": "opencode.json not found"}
            )

        data = json.loads(path.read_text())
        mcp_config = data.get("mcp", {}).get(mcp_name)

        if not mcp_config:
            return JSONResponse(
                {"status": "error", "message": f"MCP '{mcp_name}' not found in config"}
            )

        # Check if already running
        pid_file = MCP_PID_DIR / f"{mcp_name}.pid"
        if pid_file.exists():
            old_pid = pid_file.read_text().strip()
            try:
                os.kill(int(old_pid), 0)
                return JSONResponse(
                    {
                        "status": "ok",
                        "message": f"MCP '{mcp_name}' already running",
                        "pid": old_pid,
                    }
                )
            except (ProcessLookupError, PermissionError, Exception) as e:
                logger.warning(f"Stale PID file for MCP '{mcp_name}': {e}")
                pid_file.unlink()  # Stale PID file

        # Build command
        cmd = mcp_config.get("command", [])
        if not cmd:
            return JSONResponse(
                {"status": "error", "message": "No command specified for MCP"}
            )

        # Start MCP
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        if mcp_config.get("environment"):
            env.update(mcp_config["environment"])

        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Save PID
        MCP_PID_DIR.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(proc.pid))

        return JSONResponse(
            {"status": "ok", "message": f"MCP '{mcp_name}' started", "pid": proc.pid}
        )
    except Exception as e:
        logger.error(f"Error starting MCP: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


@app.post("/api/mcps/{mcp_name}/stop")
async def stop_mcp(mcp_name: str) -> JSONResponse:
    """Stop an MCP server."""
    try:
        pid_file = MCP_PID_DIR / f"{mcp_name}.pid"
        if not pid_file.exists():
            return JSONResponse(
                {"status": "error", "message": f"MCP '{mcp_name}' not running"}
            )

        pid = int(pid_file.read_text().strip())
        try:
            os.kill(pid, 15)  # SIGTERM
            pid_file.unlink()
            return JSONResponse(
                {"status": "ok", "message": f"MCP '{mcp_name}' stopped"}
            )
        except (ProcessLookupError, PermissionError) as e:
            logger.warning(f"Could not stop MCP '{mcp_name}': {e}")
            pid_file.unlink()
            return JSONResponse(
                {"status": "ok", "message": f"MCP '{mcp_name}' was not running"}
            )
    except Exception as e:
        logger.error(f"Error stopping MCP: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/api/mcps/{mcp_name}/status")
async def get_mcp_status(mcp_name: str) -> JSONResponse:
    """Get MCP server status."""
    try:
        pid_file = MCP_PID_DIR / f"{mcp_name}.pid"
        if not pid_file.exists():
            return JSONResponse(
                {"status": "ok", "data": {"running": False, "name": mcp_name}}
            )

        pid = int(pid_file.read_text().strip())
        try:
            os.kill(pid, 0)
            return JSONResponse(
                {
                    "status": "ok",
                    "data": {"running": True, "pid": pid, "name": mcp_name},
                }
            )
        except (ProcessLookupError, PermissionError) as e:
            logger.debug(f"Process {pid} not found for MCP '{mcp_name}': {e}")
            return JSONResponse(
                {"status": "ok", "data": {"running": False, "name": mcp_name}}
            )
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/api/registry/discover")
async def discover_all() -> JSONResponse:
    """Discover all system capabilities - single endpoint for dashboard bootstrap."""
    try:
        import time

        result = {"timestamp": time.time(), "capabilities": {}}

        # Agents
        try:
            from packages.orchestration.agents.registry import get_agent_registry

            registry = get_agent_registry()
            result["capabilities"]["agents"] = {
                "count": len(registry.get_all_agents()),
                "list": list(registry.get_all_agents().keys()),
            }
        except Exception as e:
            result["capabilities"]["agents"] = {"error": str(e)}

        # Tools
        try:
            from packages.orchestration.tools.registry import registry as tool_reg

            tools = tool_reg.get_tool_list()
            # If registry is empty, use auto-discovery
            if not tools:
                tools = _discover_tools_from_mcp_servers()
            result["capabilities"]["tools"] = {
                "count": len(tools),
                "list": [t.get("name", "unknown") for t in tools],
            }
        except Exception as e:
            result["capabilities"]["tools"] = {"error": str(e)}

        # Skills
        try:
            from packages.intelligence.skill_registry import get_skill_registry

            int_reg = get_skill_registry()
            result["capabilities"]["skills"] = {
                "count": len(int_reg.get_all_skills()),
                "agents": int_reg.get_agent_summary(),
            }
        except Exception as e:
            result["capabilities"]["skills"] = {"error": str(e)}

        # MCPs
        try:
            path = ROOT / "opencode.json"
            if path.exists():
                data = json.loads(path.read_text())
                mcps = data.get("mcp", {})
                result["capabilities"]["mcps"] = {
                    "count": len(mcps),
                    "list": list(mcps.keys()),
                }
        except Exception as e:
            result["capabilities"]["mcps"] = {"error": str(e)}

        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error in discover all: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# =============================================================================
# Config File Endpoints
# =============================================================================


@app.get("/api/config/{filename}")
async def get_config(filename: str) -> JSONResponse:
    """Read a config file."""
    try:
        path = ROOT / filename
        if path.exists():
            content = path.read_text()
            # Check if it's JSON
            try:
                data = json.loads(content)
                return JSONResponse({"status": "ok", "data": data})
            except json.JSONDecodeError as e:
                logger.debug(f"Config file '{filename}' is not valid JSON: {e}")
                # Return as plain text
                return JSONResponse(
                    {"status": "ok", "data": {"content": content, "type": "text"}}
                )
        return JSONResponse(
            {"status": "error", "message": f"File not found: {filename}"}
        )
    except Exception as e:
        logger.error(f"Error reading config: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


@app.put("/api/config/{filename}")
async def put_config(filename: str, request: dict) -> JSONResponse:
    """Write a config file."""
    try:
        path = ROOT / filename
        content = request.get("content", json.dumps(request.get("data", {}), indent=2))
        path.write_text(content)
        return JSONResponse({"status": "ok", "message": f"Saved {filename}"})
    except Exception as e:
        logger.error(f"Error writing config: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# =============================================================================
# Static Files - Serve Frontend
# =============================================================================

# Priority: serve Telegram dashboard from telegram-dashboard/dist if exists
telegram_dashboard_dir = ROOT / "packages" / "telegram-dashboard" / "dist"
legacy_static_dir = ROOT / "packages" / "web_frontend" / "static"

# Use telegram-dashboard if built, otherwise fall back to legacy
if telegram_dashboard_dir.exists():
    app.mount(
        "/static", StaticFiles(directory=str(telegram_dashboard_dir)), name="static"
    )
    # Also mount at /assets for Vite-built files
    app.mount(
        "/assets",
        StaticFiles(directory=str(telegram_dashboard_dir / "assets")),
        name="assets",
    )

    @app.get("/")
    async def serve_index():
        """Serve the Telegram dashboard."""
        from fastapi.responses import FileResponse

        return FileResponse(telegram_dashboard_dir / "index.html")

    @app.get("/dashboard")
    async def serve_dashboard():
        """Serve the Telegram dashboard (explicit route)."""
        from fastapi.responses import FileResponse

        return FileResponse(telegram_dashboard_dir / "index.html")
elif legacy_static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(legacy_static_dir)), name="static")

    @app.get("/")
    async def serve_index():
        """Serve the frontend."""
        from fastapi.responses import FileResponse

        return FileResponse(legacy_static_dir / "index.html")


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)

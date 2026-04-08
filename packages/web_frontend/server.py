"""N-Xyme MIND Web Frontend Backend Server.

FastAPI server on port 3000 - exposes MCP tools as HTTP endpoints.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
ROOT = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
PORT = 3000

# Create FastAPI app
app = FastAPI(
    title="N-Xyme MIND Web Frontend",
    description="HTTP API for MCP tools and system integration",
    version="1.1.0"
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
# Health Endpoint
# =============================================================================

@app.get("/api/health")
async def health() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "ok", "message": "healthy"})


# =============================================================================
# Chat Proxy Endpoints (proxy to port 8080)
# =============================================================================

@app.get("/api/chat/models")
async def get_models() -> JSONResponse:
    """Get available models."""
    try:
        from packages.learning_engine.mcp_server import learning_stats
        stats = learning_stats()
        return JSONResponse({
            "status": "ok", 
            "models": ["qwen", "minimax", "deepseek-r1", "qwen3-coder"],
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


@app.post("/api/chat/completions")
async def chat_completions(request: dict) -> JSONResponse:
    """Proxy to port 8080 /v1/chat/completions."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "http://localhost:8080/v1/chat/completions",
                json=request
            )
            response.raise_for_status()
            return JSONResponse(response.json())
    except Exception as e:
        logger.error(f"Error in chat completions: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


# =============================================================================
# Memory Endpoints (7 tools)
# =============================================================================

@app.get("/api/memory/search")
async def search_memories(
    query: str = "", 
    limit: int = 10,
    strict: bool = False,
    rerank: bool = False,
    trust_weight: float = 0.0
) -> JSONResponse:
    """Search memory using search_memories function."""
    try:
        from packages.memory_core.mcp_server import search_memories
        result = search_memories(query=query, limit=limit, strict=strict, rerank=rerank, trust_weight=trust_weight)
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/api/memory/stats")
async def memory_stats() -> JSONResponse:
    """Get memory statistics."""
    try:
        from packages.memory_core.mcp_server import get_memory_stats
        result = get_memory_stats()
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


@app.post("/api/memory/write")
async def memory_write(request: dict) -> JSONResponse:
    """Write to memory."""
    try:
        from packages.memory_core.mcp_server import memory_write
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
    session_id: Optional[str] = Query(None),
    limit: int = 50
) -> JSONResponse:
    """Recall session context."""
    try:
        from packages.memory_core.mcp_server import recall_session
        result = recall_session(session_id=session_id, limit=limit)
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error recalling session: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: find_context
@app.get("/api/memory/context")
async def find_context(
    task: str = "",
    context_type: str = "all",
    trust_weight: float = 0.0
) -> JSONResponse:
    """Find relevant context for a task."""
    try:
        from packages.memory_core.mcp_server import find_context
        result = find_context(task=task, context_type=context_type, trust_weight=trust_weight)
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error finding context: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


# NEW: router_search (memory_search)
@app.get("/api/memory/router-search")
async def router_search(
    query: str = "",
    top_k: int = 10,
    trust_weight: float = 0.0
) -> JSONResponse:
    """Search memory using MemoryRouter."""
    try:
        from packages.memory_core.mcp_server import memory_search
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
        from packages.memory_core.mcp_server import memory_stats
        result = memory_stats()
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error getting comprehensive stats: {e}")
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
            tokens_used=tokens_used
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
        return JSONResponse({"status": "ok", "data": result})
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
            tokens_used=tokens_used
        )
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error logging outcome: {e}")
        return JSONResponse({"status": "error", "message": str(e)})


@app.get("/api/routing/outcomes")
async def routing_outcomes(
    agent: Optional[str] = None, 
    task_type: Optional[str] = None, 
    limit: int = 100
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
        
        # Get basic stats
        outcomes = logger.get_all_outcomes(limit=100)
        
        # Calculate progress metrics
        total = len(outcomes)
        success_count = sum(1 for o in outcomes if o.get("success", False))
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        # Get agent performance
        agent_stats = logger.get_all_agent_stats()
        top_performers = sorted(
            agent_stats.items(), 
            key=lambda x: x[1].get("success_rate", 0), 
            reverse=True
        )[:3]
        
        return JSONResponse({
            "status": "ok",
            "data": {
                "total_decisions": total,
                "success_rate": round(success_rate, 2),
                "convergence": "active" if total < 50 else "converged",
                "top_performers": [
                    {"agent": a, "rate": s.get("success_rate", 0)}
                    for a, s in top_performers
                ],
                "recent_reward_trend": "positive" if success_rate > 50 else "developing"
            }
        })
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
    agent: str = "", 
    task: str = "",
    context: str = ""
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
        from packages.orchestration.mcp_server import tools_list
        result = tools_list()
        return JSONResponse({"status": "ok", "data": result})
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
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
                return JSONResponse({"status": "ok", "data": [{"session_id": "current", "data": data}]})
        except:
            pass
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
    """Get current settings."""
    return JSONResponse({
        "status": "ok",
        "data": {
            "port": PORT,
            "theme": "dark",
            "refresh_interval": 30000,
            "api_base": "/api"
        }
    })


# NEW: save settings
@app.post("/api/settings")
async def save_settings(request: dict) -> JSONResponse:
    """Save settings."""
    # In a real app, persist to file
    logger.info(f"Settings updated: {request}")
    return JSONResponse({"status": "ok", "message": "Settings saved"})


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
            except:
                # Return as plain text
                return JSONResponse({"status": "ok", "data": {"content": content, "type": "text"}})
        return JSONResponse({"status": "error", "message": f"File not found: {filename}"})
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

static_dir = ROOT / "packages" / "web_frontend" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    @app.get("/")
    async def serve_index():
        """Serve the frontend."""
        from fastapi.responses import FileResponse
        return FileResponse(static_dir / "index.html")


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
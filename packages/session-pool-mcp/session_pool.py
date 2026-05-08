"""Session Pool MCP - Pre-warmed agent sessions for minimal latency."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    import jsonschema

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

# Persistence path
POOL_STATE_FILE = os.environ.get(
    "POOL_STATE_FILE", "/tmp/nxyme_session_pool_state.json"
)

# Allowed agents whitelist
ALLOWED_AGENT_TYPES = frozenset(
    {
        "explore",
        "librarian",
        "oracle",
        "hephaestus",
        "metis",
        "momus",
        "multimodal-looker",
        "sisyphus",
        "prometheus",
        "atlas",
        "sisyphus-junior",
        "catalyst",
    }
)

POOL_STATE_SCHEMA = {
    "type": "object",
    "properties": {
        "pool_size": {"type": "integer", "minimum": 1, "maximum": 100},
        "keep_alive_interval": {"type": "integer", "minimum": 1, "maximum": 3600},
        "agents": {
            "type": "array",
            "items": {"type": "string", "minLength": 1, "maxLength": 50},
            "maxItems": 50,
        },
        "pools": {
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "pattern": r"^[\w\-:]+$"},
                        "agent_type": {"type": "string", "minLength": 1},
                        "created_at": {"type": "number"},
                        "last_used": {"type": "number"},
                        "in_use": {"type": "boolean"},
                        "task_count": {"type": "integer", "minimum": 0},
                    },
                    "required": ["session_id", "agent_type", "created_at", "last_used"],
                },
                "maxItems": 100,
            },
        },
        "total_tasks": {"type": "integer", "minimum": 0, "maximum": 1000000},
    },
    "required": ["pool_size", "agents", "pools"],
}


def _validate_pool_state(state: Any) -> tuple[bool, str]:
    """Validate pool state against schema.

    Returns: (is_valid: bool, error_message: str)
    """
    if not isinstance(state, dict):
        return False, "State must be a JSON object"

    if HAS_JSONSCHEMA:
        try:
            jsonschema.validate(instance=state, schema=POOL_STATE_SCHEMA)
        except jsonschema.ValidationError as e:
            return False, f"Schema validation failed: {e.message}"
    else:
        if "pool_size" in state:
            if not isinstance(state["pool_size"], int) or not (
                1 <= state["pool_size"] <= 100
            ):
                return False, "pool_size must be 1-100"

        if "agents" in state:
            for agent in state["agents"]:
                if agent not in ALLOWED_AGENT_TYPES:
                    return False, f"Unknown agent type: {agent}"

        if "pools" in state:
            for agent, sessions in state["pools"].items():
                if agent not in ALLOWED_AGENT_TYPES:
                    return False, f"Unknown agent in pools: {agent}"
                if not isinstance(sessions, list):
                    return False, f"Pools for {agent} must be an array"
                if len(sessions) > 100:
                    return False, f"Too many sessions for {agent}: {len(sessions)}"
                for i, session in enumerate(sessions):
                    if not isinstance(session, dict):
                        return False, f"Session {i} for {agent} must be an object"
                    for field in [
                        "session_id",
                        "agent_type",
                        "created_at",
                        "last_used",
                    ]:
                        if field not in session:
                            return False, f"Session missing required field: {field}"
                    if not re.match(r"^[\w\-:]+$", session.get("session_id", "")):
                        return (
                            False,
                            f"Invalid session_id format: {session.get('session_id')}",
                        )

    return True, ""


def _get_default_pool() -> "AgentSessionPool":
    """Factory for default pool (lazy import to avoid circular deps)."""
    return AgentSessionPool()


try:
    from fastmcp import FastMCP
except ImportError:
    # Fallback if not installed
    class FastMCP:
        def __init__(self, name: str):
            self.name = name

        def tool(self, func):
            return func

        def run(self):
            pass


logger = logging.getLogger("session_pool_mcp")

mcp = FastMCP("N-Xyme Session Pool")


@dataclass
class PooledSession:
    """A pre-warmed session ready for reuse."""

    session_id: str
    agent_type: str
    created_at: float
    last_used: float
    in_use: bool = False
    task_count: int = 0


@dataclass
class PoolStats:
    """Statistics about the session pool."""

    total_sessions: int
    available: int
    in_use: int
    by_agent: Dict[str, int]
    avg_latency_ms: float
    total_tasks: int


class AgentSessionPool:
    def __init__(
        self,
        pool_size: int = 3,
        keep_alive_interval: int = 30,
        polling_interval: int = 100,
        agents: Optional[List[str]] = None,
        container: Optional[Any] = None,
    ):
        try:
            from packages.core.di_container import get_container

            self._container = container or get_container()
        except ImportError:
            self._container = None
        self.pool_size = pool_size
        self.keep_alive_interval = keep_alive_interval
        self.polling_interval = polling_interval

        self.agents = agents or [
            "explore",
            "librarian",
            "oracle",
            "hephaestus",
            "metis",
            "momus",
            "multimodal-looker",
            "sisyphus",
            "prometheus",
            "atlas",
            "sisyphus-junior",
            "catalyst",
        ]

        # Pool: agent_type -> list of sessions
        self._pools: Dict[str, List[PooledSession]] = {
            agent: [] for agent in self.agents
        }

        # Lock per agent type to prevent race conditions
        self._locks: Dict[str, asyncio.Lock] = {
            agent: asyncio.Lock() for agent in self.agents
        }

        # Metrics
        self._total_tasks = 0
        self._latencies: List[float] = []
        self._max_latencies = 1000  # Keep last 1000 latencies

        # Background tasks
        self._keep_alive_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the pool - pre-warm sessions."""
        self._running = True

        # Pre-warm pools for all agent types
        print(
            f"[Session Pool] Starting pool with {self.pool_size} sessions per agent..."
        )

        for agent in self.agents:
            await self._prewarm_agent(agent)

        # Start keep-alive background task
        self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())

        print(
            f"[Session Pool] Pool started - {sum(len(s) for s in self._pools.values())} sessions ready"
        )

    async def _prewarm_agent(self, agent: str):
        """Pre-create sessions for an agent type."""
        async with self._locks[agent]:
            for _ in range(self.pool_size):
                session = await self._create_session(agent)
                if session:
                    self._pools[agent].append(session)

    async def _create_session(self, agent: str) -> Optional[PooledSession]:
        """Create a new OMO session via subprocess."""
        try:
            # Generate session ID
            session_id = f"pool_{agent}_{uuid.uuid4().hex[:8]}"

            # In a real implementation, we'd call OMO to create session
            # For now, simulate with subprocess call
            # This is where we'd integrate with OMO's createSession

            return PooledSession(
                session_id=session_id,
                agent_type=agent,
                created_at=time.time(),
                last_used=time.time(),
            )
        except Exception as e:
            print(f"[Session Pool] Failed to create session for {agent}: {e}")
            return None

    async def get_session(self, agent: str) -> Optional[PooledSession]:
        """Get a session from the pool (or create new if empty)."""
        if agent not in self._locks:
            return None

        async with self._locks[agent]:
            # Try to get from pool
            pool = self._pools[agent]

            # Find available session
            for session in pool:
                if not session.in_use:
                    session.in_use = True
                    session.last_used = time.time()
                    self._total_tasks += 1
                    return session

            # Pool exhausted - create new session
            new_session = await self._create_session(agent)
            if new_session:
                new_session.in_use = True
                new_session.last_used = time.time()
                self._total_tasks += 1
                return new_session

            return None

    async def release_session(self, session: PooledSession):
        """Return session to pool (instead of closing)."""
        if session.agent_type in self._locks:
            async with self._locks[session.agent_type]:
                session.in_use = False
                session.last_used = time.time()
                session.task_count += 1

    async def _keep_alive_loop(self):
        """Background task to keep sessions alive."""
        while self._running:
            try:
                await asyncio.sleep(self.keep_alive_interval)

                # Ping all sessions to prevent timeout
                for agent in self.agents:
                    async with self._locks[agent]:
                        for session in self._pools[agent]:
                            if not session.in_use:
                                # Would ping OMO session here
                                pass

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Session Pool] Keep-alive error: {e}")

    async def stop(self):
        """Stop the pool gracefully."""
        self._running = False

        if self._keep_alive_task:
            self._keep_alive_task.cancel()
            try:
                await self._keep_alive_task
            except asyncio.CancelledError:
                pass

        print(f"[Session Pool] Stopped - handled {self._total_tasks} tasks")

    def get_stats(self) -> PoolStats:
        """Get current pool statistics."""
        total = 0
        available = 0
        in_use = 0
        by_agent = {}

        for agent, sessions in self._pools.items():
            count = len(sessions)
            in_use_count = sum(1 for s in sessions if s.in_use)
            total += count
            available += count - in_use_count
            in_use += in_use_count
            by_agent[agent] = count

        avg_latency = (
            sum(self._latencies) / len(self._latencies) if self._latencies else 0
        )

        return PoolStats(
            total_sessions=total,
            available=available,
            in_use=in_use,
            by_agent=by_agent,
            avg_latency_ms=avg_latency,
            total_tasks=self._total_tasks,
        )

    def record_latency(self, latency_ms: float):
        """Record a task latency for metrics."""
        self._latencies.append(latency_ms)
        if len(self._latencies) > self._max_latencies:
            self._latencies.pop(0)

    # ============================================================================
    # Persistence (ROI #5)
    # ============================================================================

    def _serialize_state(self) -> Dict[str, Any]:
        """Serialize pool state to dict for persistence."""
        return {
            "pool_size": self.pool_size,
            "keep_alive_interval": self.keep_alive_interval,
            "agents": self.agents,
            "pools": {
                agent: [
                    {
                        "session_id": s.session_id,
                        "agent_type": s.agent_type,
                        "created_at": s.created_at,
                        "last_used": s.last_used,
                        "in_use": s.in_use,
                        "task_count": s.task_count,
                    }
                    for s in sessions
                ]
                for agent, sessions in self._pools.items()
            },
            "total_tasks": self._total_tasks,
        }

    def save_state(self) -> None:
        """Save pool state to JSON file with atomic write."""
        temp_file = None
        try:
            state = self._serialize_state()
            temp_file = POOL_STATE_FILE + ".tmp"
            with open(temp_file, "w") as f:
                json.dump(state, f)
            os.replace(temp_file, POOL_STATE_FILE)
            logger.info(f"Session pool state saved to {POOL_STATE_FILE}")
        except Exception as e:
            logger.warning(f"Failed to save session pool state: {e}")
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

    def load_state(self) -> bool:
        """Load pool state from JSON file. Returns True if successful."""
        if not os.path.exists(POOL_STATE_FILE):
            return False
        try:
            with open(POOL_STATE_FILE, "r") as f:
                state = json.load(f)

            is_valid, error = _validate_pool_state(state)
            if not is_valid:
                logger.warning(f"SESSION_POOL_STATE_REJECTED: {error}")
                return False

            if "pool_size" in state:
                self.pool_size = state["pool_size"]
            if "agents" in state:
                self.agents = state["agents"]
                self._pools = {agent: [] for agent in self.agents}
                self._locks = {agent: asyncio.Lock() for agent in self.agents}

            if "pools" in state:
                for agent, sessions_data in state["pools"].items():
                    if agent in self._pools:
                        for sd in sessions_data:
                            session = PooledSession(
                                session_id=sd["session_id"],
                                agent_type=sd["agent_type"],
                                created_at=sd["created_at"],
                                last_used=sd["last_used"],
                                in_use=False,
                                task_count=sd.get("task_count", 0),
                            )
                            self._pools[agent].append(session)

            if "total_tasks" in state:
                self._total_tasks = state["total_tasks"]

            logger.info(f"Session pool state loaded from {POOL_STATE_FILE}")
            return True
        except Exception as e:
            logger.warning(f"Failed to load session pool state: {e}")
            return False


def create_session_pool(**kwargs) -> "AgentSessionPool":
    """Factory function to create session pool via DI."""
    try:
        from packages.core.di_container import get_container

        c = get_container()
        if c.has("session_pool"):
            return c.get("session_pool")
        pool = AgentSessionPool(**kwargs)
        c.register("session_pool", instance=pool, singleton=True)
        pool.load_state()
        return pool
    except ImportError:
        return AgentSessionPool(**kwargs)


def get_pool() -> "AgentSessionPool":
    """Get the global session pool."""
    return create_session_pool()


def reset_pool() -> None:
    """Reset the global pool (for testing)."""
    try:
        from packages.core.di_container import get_container

        c = get_container()
        if c.has("session_pool"):
            pool = c.get("session_pool")
            pool._running = False
        c.unregister("session_pool")
    except Exception:
        pass


# MCP Tools


@mcp.tool()
async def route_task(task_description: str) -> Dict[str, Any]:
    """Route a task through the session pool (lowest latency).

    Uses pre-warmed sessions instead of creating new ones each call.

    Args:
        task_description: The task to route and execute

    Returns:
        Dict with task_id, agent, latency_ms, and result
    """
    start_time = time.time()

    try:
        pool = get_pool()

        # Route to optimal agent
        from packages.intelligence import route as _route

        result = await _route(task_description)

        agent = result.agent

        # Get session from pool (no create overhead)
        session = await pool.get_session(agent)

        if session:
            # Execute with warm session
            # In real implementation: send to OMO with session_id
            task_id = f"task_{uuid.uuid4().hex[:8]}"

            # Return session to pool (don't close)
            await pool.release_session(session)

            latency = (time.time() - start_time) * 1000
            pool.record_latency(latency)

            return {
                "status": "success",
                "task_id": task_id,
                "agent": agent,
                "session_id": session.session_id,
                "latency_ms": round(latency, 2),
                "pooled": True,
                "level": result.level,
                "confidence": result.confidence,
                "strategy": getattr(result, "strategy_used", None),
            }
        else:
            # Fallback - no session available
            return {
                "status": "fallback",
                "error": "No session available",
                "latency_ms": round((time.time() - start_time) * 1000, 2),
            }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "latency_ms": round((time.time() - start_time) * 1000, 2),
        }


@mcp.tool()
async def pool_stats() -> Dict[str, Any]:
    """Get session pool statistics.

    Returns:
        Dict with pool size, usage, and performance metrics
    """
    try:
        pool = get_pool()
        stats = pool.get_stats()

        return {
            "status": "success",
            "total_sessions": stats.total_sessions,
            "available": stats.available,
            "in_use": stats.in_use,
            "by_agent": stats.by_agent,
            "avg_latency_ms": round(stats.avg_latency_ms, 2),
            "total_tasks": stats.total_tasks,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
async def warm_pool(agents: Optional[List[str]] = None) -> Dict[str, Any]:
    """Pre-warm the session pool with specified agents.

    Args:
        agents: List of agent types to warm (default: all)

    Returns:
        Dict with warm status
    """
    try:
        pool = get_pool()
        target_agents = agents or pool.agents

        for agent in target_agents:
            if agent in pool._pools:
                await pool._prewarm_agent(agent)

        stats = pool.get_stats()

        return {
            "status": "success",
            "warmed_agents": target_agents,
            "total_sessions": stats.total_sessions,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
async def get_session(agent_type: str) -> Dict[str, Any]:
    """Get a session for a specific agent type.

    Args:
        agent_type: The agent type (explore, librarian, oracle, etc.)

    Returns:
        Dict with session_id and metadata
    """
    try:
        pool = get_pool()
        session = await pool.get_session(agent_type)

        if session:
            return {
                "status": "success",
                "session_id": session.session_id,
                "agent_type": session.agent_type,
                "created_at": session.created_at,
                "task_count": session.task_count,
            }
        else:
            return {
                "status": "error",
                "error": f"No session available for {agent_type}",
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
async def return_session(session_id: str, agent_type: str) -> Dict[str, Any]:
    """Return a session to the pool (don't close it).

    Args:
        session_id: The session to return
        agent_type: The agent type

    Returns:
        Dict with return status
    """
    try:
        pool = get_pool()

        if agent_type in pool._pools:
            async with pool._locks[agent_type]:
                for session in pool._pools[agent_type]:
                    if session.session_id == session_id:
                        await pool.release_session(session)
                        return {"status": "success", "returned": True}

        return {"status": "error", "error": "Session not found"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":

    # Start the pool on launch
    async def main():
        pool = get_pool()
        await pool.start()
        print("[Session Pool MCP] Starting on stdio...")
        mcp.run()

    asyncio.run(main())

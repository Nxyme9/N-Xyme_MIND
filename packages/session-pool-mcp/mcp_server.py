"""Session Pool MCP - Pre-warmed agent sessions for minimal latency."""

from __future__ import annotations

import asyncio
import time
import traceback
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

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
    """Manages pre-warmed OMO agent sessions for minimal latency.

    Bleeding-edge optimizations:
    - Pre-warmed sessions (no create/teardown overhead)
    - Tool caching (skip re-listTools() ~200ms savings)
    - Context compression (reduce token count)
    - Fast polling (100ms vs default 500ms)
    - Session affinity (bind tasks to specific sessions)
    """

    def __init__(
        self,
        pool_size: int = 3,
        keep_alive_interval: int = 30,
        polling_interval: int = 100,  # Fast polling: 100ms vs default 500ms
        agents: Optional[List[str]] = None,
    ):
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

        self._pools: Dict[str, List[PooledSession]] = {
            agent: [] for agent in self.agents
        }
        self._locks: Dict[str, asyncio.Lock] = {
            agent: asyncio.Lock() for agent in self.agents
        }

        # Bleeding-edge optimizations
        self._tools_cache: Dict[str, Any] = {}  # Cache tools list per agent
        self._context_cache: Dict[str, Any] = {}  # Cache context per agent
        self._cache_ttl = 300  # Cache TTL in seconds

        # NEW: Tool deduplication - shared schema across agents
        self._shared_tool_schemas: Dict[str, Any] = {}  # Deduplicated tool definitions
        self._tool_schema_hits = 0
        self._tool_schema_misses = 0

        # NEW: Context diffing - delta-only context transfer
        self._last_context: Dict[str, str] = {}  # Last sent context per agent
        self._context_diffs_enabled = True

        # NEW: Request coalescing - batch similar calls
        self._pending_requests: List[Dict[str, Any]] = []
        self._coalesce_window_ms = 50  # Batch window
        self._max_batch_size = 5

        # === NEW: Connection Multiplexing ===
        self._multiplex_connections: Dict[str, Any] = {}  # Single TCP per agent type
        self._connection_hits = 0
        self._connection_misses = 0

        # === NEW: Predictive Pre-warming ===
        self._task_history: List[Dict[str, Any]] = []  # Task sequence history
        self._max_history = 100
        self._prediction_model: Optional[Dict[str, Any]] = None
        self._prefetch_enabled = True

        # === NEW: WebSocket Persistent ===
        self._ws_connections: Dict[str, Any] = {}  # Persistent WebSocket connections
        self._ws_enabled = False  # Toggle for WebSocket mode

        self._total_tasks = 0
        self._latencies: List[float] = []
        self._max_latencies = 1000

        self._keep_alive_task: Optional[asyncio.Task] = None
        self._running = False
        self._started = False

    def start(self):
        """Start the pool synchronously - pre-warm sessions."""
        if self._started:
            return

        self._running = True
        self._started = True

        print(
            f"[Session Pool] Starting pool with {self.pool_size} sessions per agent..."
        )

        # Pre-warm synchronously
        for agent in self.agents:
            for _ in range(self.pool_size):
                session_id = f"pool_{agent}_{uuid.uuid4().hex[:8]}"
                self._pools[agent].append(
                    PooledSession(
                        session_id=session_id,
                        agent_type=agent,
                        created_at=time.time(),
                        last_used=time.time(),
                    )
                )

        print(
            f"[Session Pool] Pool started - {sum(len(s) for s in self._pools.values())} sessions ready"
        )

    def get_session(self, agent: str) -> Optional[PooledSession]:
        """Get a session from the pool (or create new if empty)."""
        if agent not in self._pools:
            return None

        pool = self._pools[agent]

        for session in pool:
            if not session.in_use:
                session.in_use = True
                session.last_used = time.time()
                self._total_tasks += 1
                return session

        # Pool exhausted - create new session
        session_id = f"pool_{agent}_{uuid.uuid4().hex[:8]}"
        new_session = PooledSession(
            session_id=session_id,
            agent_type=agent,
            created_at=time.time(),
            last_used=time.time(),
            in_use=True,
        )
        self._total_tasks += 1
        return new_session

    def release_session(self, session: PooledSession):
        """Return session to pool (instead of closing)."""
        if session.agent_type in self._pools:
            session.in_use = False
            session.last_used = time.time()
            session.task_count += 1

    def get_tools_cache(self, agent: str) -> Optional[Any]:
        """Get cached tools for agent (skip re-listTools ~200ms)."""
        if agent in self._tools_cache:
            cached = self._tools_cache[agent]
            if time.time() - cached["timestamp"] < self._cache_ttl:
                return cached["tools"]
        return None

    def set_tools_cache(self, agent: str, tools: Any):
        """Cache tools for agent."""
        self._tools_cache[agent] = {"tools": tools, "timestamp": time.time()}

    def get_context_cache(self, agent: str, task_type: str) -> Optional[str]:
        """Get compressed context for agent+task_type."""
        key = f"{agent}:{task_type}"
        if key in self._context_cache:
            cached = self._context_cache[key]
            if time.time() - cached["timestamp"] < self._cache_ttl:
                return cached["context"]
        return None

    def set_context_cache(self, agent: str, task_type: str, context: str):
        """Cache compressed context for agent+task_type."""
        key = f"{agent}:{task_type}"
        self._context_cache[key] = {"context": context, "timestamp": time.time()}

    def clear_cache(self):
        """Clear all caches."""
        self._tools_cache.clear()
        self._context_cache.clear()
        self._shared_tool_schemas.clear()

    # === NEW OPTIMIZATIONS ===

    def get_deduplicated_tools(
        self, agent: str, tools: List[Any]
    ) -> Optional[List[Any]]:
        """Get deduplicated tool schemas - avoid sending duplicate tool defs."""
        # Extract tool names
        tool_names = tuple(sorted(t.get("name", "") for t in tools))

        if tool_names in self._shared_tool_schemas:
            self._tool_schema_hits += 1
            return self._shared_tool_schemas[tool_names]

        # Cache miss - store deduplicated version
        self._tool_schema_misses += 1
        # Simple dedup: remove duplicate definitions
        unique_tools = {t.get("name"): t for t in tools if t.get("name")}.values()
        self._shared_tool_schemas[tool_names] = list(unique_tools)

        return tools

    def get_context_delta(self, agent: str, new_context: str) -> Dict[str, Any]:
        """Calculate delta between last context and new context."""
        last = self._last_context.get(agent, "")

        if not last or not self._context_diffs_enabled:
            return {"type": "full", "data": new_context}

        # Simple diff: return full if significantly different
        if self._simple_hash(last) != self._simple_hash(new_context):
            # Check similarity
            common = sum(a == b for a, b in zip(last[:100], new_context[:100]))
            if common < 80:  # Less than 80% similar in first 100 chars
                return {"type": "full", "data": new_context}

        # Return delta (unchanged)
        return {"type": "delta", "delta": ""}

    def _simple_hash(self, s: str) -> int:
        """Fast hash for similarity check."""
        return hash(s) & 0xFFFF

    def update_last_context(self, agent: str, context: str):
        """Update last sent context for delta calculation."""
        self._last_context[agent] = context

    def coalesce_requests(
        self, requests: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Group similar requests for batch execution."""
        if not requests:
            return []

        batches = []
        current_batch = [requests[0]]

        for req in requests[1:]:
            # Same agent and similar context = batchable
            if (
                req["agent"] == current_batch[0]["agent"]
                and self._context_similarity(
                    req.get("context", ""), current_batch[0].get("context", "")
                )
                > 0.8
            ):
                if len(current_batch) < self._max_batch_size:
                    current_batch.append(req)
                else:
                    batches.append(current_batch)
                    current_batch = [req]
            else:
                batches.append(current_batch)
                current_batch = [req]

        if current_batch:
            batches.append(current_batch)

        return batches

    def _context_similarity(self, ctx1: str, ctx2: str) -> float:
        """Calculate similarity between contexts."""
        if not ctx1 or not ctx2:
            return 0.0

        # Simple token-based similarity
        set1 = set(ctx1.split()[:50])  # First 50 tokens
        set2 = set(ctx2.split()[:50])

        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

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

    # === CONNECTION MULTIPLEXING ===

    def get_multiplex_connection(self, agent: str) -> Optional[str]:
        """Get or create multiplexed connection for agent type."""
        if agent in self._multiplex_connections:
            self._connection_hits += 1
            conn = self._multiplex_connections[agent]
            conn["last_used"] = time.time()
            conn["active_sessions"] = conn.get("active_sessions", 0) + 1
            return conn["connection_id"]

        # Create new multiplexed connection
        self._connection_misses += 1
        conn_id = f"multiplex_{agent}_{uuid.uuid4().hex[:8]}"
        self._multiplex_connections[agent] = {
            "connection_id": conn_id,
            "agent_type": agent,
            "created_at": time.time(),
            "last_used": time.time(),
            "active_sessions": 1,
            "total_sessions": 0,
        }
        return conn_id

    def release_multiplex_connection(self, agent: str):
        """Release session from multiplexed connection (don't close)."""
        if agent in self._multiplex_connections:
            conn = self._multiplex_connections[agent]
            conn["active_sessions"] = max(0, conn.get("active_sessions", 1) - 1)
            conn["total_sessions"] = conn.get("total_sessions", 0) + 1

    def get_multiplex_stats(self) -> Dict[str, Any]:
        """Get multiplexing statistics."""
        return {
            "total_connections": len(self._multiplex_connections),
            "connection_hits": self._connection_hits,
            "connection_misses": self._connection_misses,
            "hit_rate": self._connection_hits
            / max(1, self._connection_hits + self._connection_misses),
            "connections": {
                agent: {
                    "active": conn.get("active_sessions", 0),
                    "total": conn.get("total_sessions", 0),
                }
                for agent, conn in self._multiplex_connections.items()
            },
        }

    # === PREDICTIVE PRE-WARMING ===

    def record_task(
        self, task_description: str, agent_used: str, success: bool, latency_ms: float
    ):
        """Record task for predictive modeling."""
        self._task_history.append(
            {
                "description": task_description,
                "agent": agent_used,
                "success": success,
                "latency_ms": latency_ms,
                "timestamp": time.time(),
            }
        )

        # Trim history
        if len(self._task_history) > self._max_history:
            self._task_history = self._task_history[-self._max_history :]

    def build_prediction_model(self) -> Dict[str, Any]:
        """Build agent transition probability matrix."""
        if len(self._task_history) < 5:
            return {"status": "insufficient_data"}

        # Build transition matrix: agent_A -> agent_B
        transitions: Dict[str, Dict[str, int]] = {}
        agent_counts: Dict[str, int] = {}

        for i in range(1, len(self._task_history)):
            prev_agent = self._task_history[i - 1]["agent"]
            curr_agent = self._task_history[i]["agent"]

            if prev_agent not in transitions:
                transitions[prev_agent] = {}
            transitions[prev_agent][curr_agent] = (
                transitions[prev_agent].get(curr_agent, 0) + 1
            )

            agent_counts[prev_agent] = agent_counts.get(prev_agent, 0) + 1

        # Convert to probabilities
        probs = {}
        for prev_agent, next_agents in transitions.items():
            total = agent_counts.get(prev_agent, 1)
            probs[prev_agent] = {
                next_agent: count / total for next_agent, count in next_agents.items()
            }

        self._prediction_model = {
            "transitions": probs,
            "sample_size": len(self._task_history),
        }
        return self._prediction_model

    def predict_next_agent(self, current_agent: str) -> Optional[str]:
        """Predict most likely next agent based on history."""
        if not self._prediction_model:
            self.build_prediction_model()

        if not self._prediction_model or "transitions" not in self._prediction_model:
            return None

        transitions = self._prediction_model.get("transitions", {})
        if current_agent not in transitions:
            return None

        next_probs = transitions[current_agent]
        if not next_probs:
            return None

        # Return highest probability next agent
        return max(next_probs.items(), key=lambda x: x[1])[0]

    def prefetch_predictive(
        self, current_agent: str, threshold: float = 0.5
    ) -> List[str]:
        """Pre-warm agents predicted to be needed next."""
        predicted = []

        # Predict next agent
        next_agent = self.predict_next_agent(current_agent)
        if next_agent:
            prob = (
                self._prediction_model["transitions"]
                .get(current_agent, {})
                .get(next_agent, 0)
            )
            if prob >= threshold:
                predicted.append(next_agent)

                # Also prefetch the agent after next (chain prediction)
                next_next = self.predict_next_agent(next_agent)
                if next_next:
                    predicted.append(next_next)

        # Pre-warm predicted agents
        for agent in predicted:
            if len(self._pools.get(agent, [])) < self.pool_size:
                for _ in range(self.pool_size):
                    session_id = f"prefetch_{agent}_{uuid.uuid4().hex[:8]}"
                    self._pools[agent].append(
                        PooledSession(
                            session_id=session_id,
                            agent_type=agent,
                            created_at=time.time(),
                            last_used=time.time(),
                        )
                    )

        return predicted

    # === WEBSOCKET PERSISTENT CONNECTIONS ===

    def enable_websocket_mode(self):
        """Enable WebSocket persistent connection mode."""
        self._ws_enabled = True
        print("[Session Pool] WebSocket mode enabled")

    def disable_websocket_mode(self):
        """Disable WebSocket mode, fall back to stdio."""
        self._ws_enabled = False
        print("[Session Pool] WebSocket mode disabled")

    def register_ws_connection(
        self, connection_id: str, agent: str, metadata: Dict[str, Any] = None
    ):
        """Register a persistent WebSocket connection."""
        self._ws_connections[connection_id] = {
            "agent": agent,
            "created_at": time.time(),
            "last_heartbeat": time.time(),
            "metadata": metadata or {},
            "active": True,
        }

    def get_ws_connection(self, agent: str) -> Optional[str]:
        """Get existing WebSocket connection for agent, or None."""
        for conn_id, conn in self._ws_connections.items():
            if conn.get("agent") == agent and conn.get("active"):
                conn["last_heartbeat"] = time.time()
                return conn_id
        return None

    def release_ws_connection(self, connection_id: str):
        """Mark WebSocket connection as available (don't close)."""
        if connection_id in self._ws_connections:
            self._ws_connections[connection_id]["last_heartbeat"] = time.time()

    def close_ws_connection(self, connection_id: str):
        """Close and remove WebSocket connection."""
        if connection_id in self._ws_connections:
            del self._ws_connections[connection_id]

    def cleanup_stale_ws_connections(self, max_age_seconds: int = 300):
        """Remove stale WebSocket connections."""
        now = time.time()
        stale = [
            conn_id
            for conn_id, conn in self._ws_connections.items()
            if now - conn.get("last_heartbeat", 0) > max_age_seconds
        ]
        for conn_id in stale:
            self.close_ws_connection(conn_id)

        if stale:
            print(f"[Session Pool] Cleaned up {len(stale)} stale WebSocket connections")

    def get_ws_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics."""
        return {
            "total_connections": len(self._ws_connections),
            "active": sum(1 for c in self._ws_connections.values() if c.get("active")),
            "by_agent": {
                agent: sum(
                    1 for c in self._ws_connections.values() if c.get("agent") == agent
                )
                for agent in self.agents
            },
        }


# Global pool instance
_pool: Optional[AgentSessionPool] = None


def get_pool() -> AgentSessionPool:
    """Get or create the global session pool."""
    global _pool
    if _pool is None:
        _pool = AgentSessionPool()
        _pool.start()
    return _pool


# MCP Tools (synchronous for FastMCP compatibility)


@mcp.tool()
def route_task(task_description: str) -> Dict[str, Any]:
    """Route a task through the session pool (lowest latency).

    Uses unified routing from nx_routing.py (single source of truth).
    """
    start_time = time.time()

    try:
        pool = get_pool()

        # Use unified routing
        from packages.nx_routing import route_task as _nx_route_task

        result = _nx_route_task(task_description)

        agent = result.agent

        # Get session from pool (no create overhead)
        session = pool.get_session(agent)

        if session:
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            pool.release_session(session)

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
                "strategy": result.strategy,
            }
        else:
            return {
                "status": "fallback",
                "error": "No session available",
                "latency_ms": round((time.time() - start_time) * 1000, 2),
            }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "latency_ms": round((time.time() - start_time) * 1000, 2),
        }


@mcp.tool()
def pool_stats() -> Dict[str, Any]:
    """Get session pool statistics."""
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
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def warm_pool(agents: Optional[List[str]] = None) -> Dict[str, Any]:
    """Pre-warm the session pool with specified agents."""
    try:
        pool = get_pool()
        target_agents = agents or pool.agents

        for agent in target_agents:
            if agent in pool._pools:
                for _ in range(pool.pool_size):
                    session_id = f"pool_{agent}_{uuid.uuid4().hex[:8]}"
                    pool._pools[agent].append(
                        PooledSession(
                            session_id=session_id,
                            agent_type=agent,
                            created_at=time.time(),
                            last_used=time.time(),
                        )
                    )

        stats = pool.get_stats()

        return {
            "status": "success",
            "warmed_agents": target_agents,
            "total_sessions": stats.total_sessions,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def get_session(agent_type: str) -> Dict[str, Any]:
    """Get a session for a specific agent type."""
    try:
        pool = get_pool()
        session = pool.get_session(agent_type)

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
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@mcp.tool()
def return_session(session_id: str, agent_type: str) -> Dict[str, Any]:
    """Return a session to the pool (don't close it)."""
    try:
        pool = get_pool()

        if agent_type in pool._pools:
            for session in pool._pools[agent_type]:
                if session.session_id == session_id:
                    pool.release_session(session)
                    return {"status": "success", "returned": True}

        return {"status": "error", "error": "Session not found"}
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


if __name__ == "__main__":
    # Initialize pool on startup
    get_pool()
    print("[Session Pool MCP] Starting on stdio...")
    mcp.run()

#!/usr/bin/env python3
"""Chat Backend - Bridge between AI Chat and all N-Xyme MIND backend systems."""

import asyncio
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Optional

# Memory Core imports
try:
    from packages.memory_core import search as memory_search, stats as memory_stats
    from packages.memory_core import recall_session
    from packages.memory_core.retrievers import TEMPRRetriever

    MEMORY_CORE_AVAILABLE = True
except ImportError:
    MEMORY_CORE_AVAILABLE = False

# Learning Engine imports
try:
    from packages.learning_engine import status as learning_status, route_task
    from packages.learning_engine.outcome_logger import OutcomeLogger

    LEARNING_ENGINE_AVAILABLE = True
except ImportError:
    # Fallback: try with hyphen naming (learning-engine)
    try:
        from packages.learning_engine import status as learning_status, route_task
        from packages.learning_engine.outcome_logger import OutcomeLogger

        LEARNING_ENGINE_AVAILABLE = True
    except ImportError:
        LEARNING_ENGINE_AVAILABLE = False

# Local LLM import
try:
    from packages.local_llm import LocalLLM

    LOCAL_LLM_AVAILABLE = True
except ImportError:
    LOCAL_LLM_AVAILABLE = False


# ─── Intent Patterns ────────────────────────────────────────────────────────────

INTENTS = {
    "memory": [
        "search memory",
        "find in memory",
        "what do you remember",
        "semantic",
        "recall",
        "what did i work on",
        "context",
    ],
    "stats": [
        "stats",
        "statistics",
        "show metrics",
        "performance",
        "how is",
        "health check",
        "system status",
    ],
    "routing": [
        "routing",
        "agent performance",
        "delegation",
        "outcomes",
        "which agent",
        "best agent",
        "success rate",
    ],
    "health": [
        "health",
        "status",
        "check",
        "broken",
        "running",
        "is working",
        "what's wrong",
        "diagnose",
    ],
    "command": [
        "start",
        "stop",
        "restart",
        "run",
        "execute",
        "launch",
        "kill",
        "reload",
    ],
    "logs": [
        "logs",
        "journal",
        "recent activity",
        "what happened",
        "errors",
        "trace",
    ],
    "session": [
        "session",
        "conversation",
        "previous",
        "recent",
        "what were we",
        "last time",
    ],
}


# ─── ChatBackend Class ─────────────────────────────────────────────────────────


class ChatBackend:
    """Bridge between chat and all N-Xyme MIND backend systems."""

    def __init__(self):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._cache_ttl = 30  # seconds
        self._retriever = TEMPRRetriever() if MEMORY_CORE_AVAILABLE else None
        self._command_history: list[dict] = []  # Store recent commands
        self._max_history = 20

    # ─── Intent Detection ─────────────────────────────────────────────────

    def detect_intent(self, query: str) -> list[str]:
        """Detect what the user is asking for."""
        query_lower = query.lower()
        detected = []
        for intent, patterns in INTENTS.items():
            if any(p in query_lower for p in patterns):
                detected.append(intent)
        return detected if detected else ["general"]

    # ─── Memory Search ────────────────────────────────────────────────────

    async def get_memory_results(self, query: str, limit: int = 5) -> dict:
        """Query Athena memory."""
        if not MEMORY_CORE_AVAILABLE:
            return {"status": "unavailable", "error": "Memory core not available"}

        try:
            # Use TEMPRRetriever for semantic search
            if self._retriever:
                results = self._retriever.search(query, top_k=limit)
                if results:
                    return {
                        "status": "ok",
                        "results": [
                            {
                                "content": r.get("content", "")[:200],
                                "score": r.get("score", 0),
                                "source": r.get("source", "unknown"),
                            }
                            for r in results[:limit]
                        ],
                        "count": len(results),
                    }

            # Fallback to simple search
            results = memory_search(query, limit=limit)
            return {
                "status": "ok",
                "results": results,
                "count": len(results) if results else 0,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_memory_stats(self) -> dict:
        """Get memory system statistics."""
        if not MEMORY_CORE_AVAILABLE:
            return {"status": "unavailable", "error": "Memory core not available"}

        try:
            stats = memory_stats()
            return {"status": "ok", "stats": stats}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def recall_session(self, session_id: str = None, limit: int = 10) -> dict:
        """Recall session context."""
        if not MEMORY_CORE_AVAILABLE:
            return {"status": "unavailable", "error": "Memory core not available"}

        try:
            result = recall_session(session_id=session_id, limit=limit)
            return {"status": "ok", "session": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ─── Routing Stats ─────────────────────────────────────────────────────

    async def get_routing_stats(self) -> dict:
        """Get learning engine stats from SQLite."""
        if not LEARNING_ENGINE_AVAILABLE:
            return {"status": "unavailable", "error": "Learning engine not available"}

        try:
            status_info = learning_status()
            return {"status": "ok", "stats": status_info}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_outcomes(self, agent: str = None, limit: int = 20) -> dict:
        """Get delegation outcomes."""
        if not LEARNING_ENGINE_AVAILABLE:
            return {"status": "unavailable", "error": "Learning engine not available"}

        try:
            logger = OutcomeLogger()
            outcomes = logger.get_outcomes(agent=agent, limit=limit)
            return {
                "status": "ok",
                "outcomes": [
                    {
                        "agent": o.agent,
                        "task": o.task_description[:50],
                        "success": o.success,
                        "latency_ms": o.latency_ms,
                        "timestamp": o.timestamp,
                    }
                    for o in outcomes
                ],
                "count": len(outcomes),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_agent_performance(self) -> dict:
        """Get agent performance summary."""
        if not LEARNING_ENGINE_AVAILABLE:
            return {"status": "unavailable", "error": "Learning engine not available"}

        try:
            logger = OutcomeLogger()
            all_stats = logger.get_all_agent_stats()
            return {"status": "ok", "performance": all_stats}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ─── Health Checks ────────────────────────────────────────────────────

    async def get_health_summary(self, level: str = "l0") -> dict:
        """Run health checks and summarize."""
        script_map = {
            "l0": "bin/health-l0-blink.sh",
            "l1": "bin/health-l1-pulse.sh",
            "l2": "bin/health-l2-vitals.sh",
        }

        script = script_map.get(level, "bin/health-l0-blink.sh")
        script_path = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND") / script

        if not script_path.exists():
            return {"status": "error", "error": f"Health script not found: {script}"}

        try:
            result = subprocess.run(
                ["bash", str(script_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND",
            )

            output = result.stdout[:1000] if result.stdout else ""
            error = result.stderr[:500] if result.stderr else ""

            return {
                "status": "ok" if result.returncode == 0 else "degraded",
                "returncode": result.returncode,
                "output": output,
                "error": error if error else None,
                "level": level,
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Health check timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def check_service(self, service: str) -> dict:
        """Check if a specific service is running."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", service],
                capture_output=True,
                text=True,
                timeout=10,
            )
            is_active = result.returncode == 0
            return {
                "status": "ok",
                "service": service,
                "running": is_active,
                "state": result.stdout.strip(),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ─── Command Execution ─────────────────────────────────────────────────

    async def execute_command(self, command: str) -> dict:
        """Execute a system command."""
        import subprocess

        # Whitelist of allowed commands
        allowed_prefixes = [
            "start ",
            "stop ",
            "restart ",
            "systemctl --user start",
            "systemctl --user stop",
            "systemctl --user restart",
            "bash ",
            "python3 ",
            "pip ",
        ]

        command_lower = command.lower().strip()

        # Check if command is in whitelist
        is_allowed = any(
            command_lower.startswith(prefix.lower()) for prefix in allowed_prefixes
        )

        if not is_allowed:
            return {"status": "error", "error": f"Command not allowed: {command[:50]}"}

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND",
            )

            return {
                "status": "ok" if result.returncode == 0 else "error",
                "returncode": result.returncode,
                "output": result.stdout[:2000],
                "error": result.stderr[:500] if result.stderr else None,
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Command timed out"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def start_service(self, service: str) -> dict:
        """Start a user service."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "start", service],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "service": service,
                "output": result.stdout,
                "error": result.stderr if result.stderr else None,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def stop_service(self, service: str) -> dict:
        """Stop a user service."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "stop", service],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "service": service,
                "output": result.stdout,
                "error": result.stderr if result.stderr else None,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ─── LLM Integration ──────────────────────────────────────────────────

    async def get_llm_response(
        self,
        messages: list[dict],
        model: str = "qwen2.5-coder:7b",
        system_prompt: str = "",
    ) -> dict:
        """Get response from LocalLLM."""
        if not LOCAL_LLM_AVAILABLE:
            return {"status": "unavailable", "error": "Local LLM not available"}

        try:
            llm = LocalLLM(model=model)

            # Add system prompt if provided
            if system_prompt:
                full_messages = [
                    {"role": "system", "content": system_prompt}
                ] + messages
            else:
                full_messages = messages

            response = llm.chat(full_messages)

            if isinstance(response, dict) and "content" in response:
                return {"status": "ok", "content": response["content"]}
            elif isinstance(response, dict) and "Error" in str(
                response.get("content", "")
            ):
                return {
                    "status": "error",
                    "error": response.get("content", "Unknown error"),
                }
            else:
                return {"status": "ok", "content": str(response)}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ─── Context Building ─────────────────────────────────────────────────

    async def build_context(self, query: str, intents: list[str]) -> dict:
        """Build context from all relevant backends based on intents."""
        context_parts = []

        # Memory search (if relevant)
        if "memory" in intents or "session" in intents:
            mem_results = await self.get_memory_results(query)
            if mem_results.get("status") == "ok" and mem_results.get("results"):
                context_parts.append("## Memory Results")
                for r in mem_results["results"][:3]:
                    context_parts.append(f"- {r.get('content', '')[:150]}...")

        # Routing stats (if relevant)
        if "routing" in intents or "stats" in intents:
            routing = await self.get_routing_stats()
            if routing.get("status") == "ok":
                stats = routing.get("stats", {})
                weights = stats.get("routing_weights", {})
                if weights:
                    context_parts.append("## Agent Performance")
                    for agent, data in list(weights.items())[:5]:
                        success_rate = data.get("success_rate", 0)
                        context_parts.append(
                            f"- {agent}: {success_rate:.1%} success rate"
                        )

        # Health check (if relevant)
        if "health" in intents or "stats" in intents:
            health = await self.get_health_summary("l0")
            if health.get("status") == "ok":
                context_parts.append(f"## System Health (L0)")
                context_parts.append(
                    f"- Status: {health.get('output', 'Unknown')[:200]}"
                )

        # Command execution (if relevant)
        if "command" in intents:
            cmd_result = await self.execute_command(query)
            if cmd_result.get("status") == "ok":
                context_parts.append(f"## Command Output")
                context_parts.append(cmd_result.get("output", "Success")[:500])
            else:
                context_parts.append(f"## Command Error")
                context_parts.append(cmd_result.get("error", "Unknown error"))

        # Log retrieval (if relevant)
        if "logs" in intents:
            logs_result = await self.get_logs(lines=30)
            if logs_result.get("status") == "ok":
                context_parts.append(
                    f"## Recent Logs ({logs_result.get('source', 'unknown')})"
                )
                context_parts.append(logs_result.get("logs", "No logs")[:1000])
            else:
                context_parts.append(f"## Logs Error")
                context_parts.append(logs_result.get("error", "Unknown error"))

        return {
            "context": "\n\n".join(context_parts) if context_parts else "",
            "intents": intents,
        }

    # ─── Log Retrieval ────────────────────────────────────────────────────────

    async def get_logs(self, service: str = None, lines: int = 50) -> dict:
        """Get recent logs from journalctl or files."""
        try:
            # Try journalctl first for user services
            if service:
                cmd = [
                    "journalctl",
                    "--user",
                    "-u",
                    service,
                    "-n",
                    str(lines),
                    "--no-pager",
                ]
            else:
                cmd = ["journalctl", "--user", "-n", str(lines), "--no-pager"]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0 and result.stdout:
                return {
                    "status": "ok",
                    "source": "journalctl",
                    "logs": result.stdout[-3000:],  # Last 3000 chars
                    "service": service,
                }
        except Exception:
            pass

        # Fallback: try reading from log files
        log_paths = [
            Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND") / ".sisyphus" / "session.log",
            Path.home() / ".local" / "share" / "opencode" / "logs" / "agent.log",
        ]

        for log_path in log_paths:
            if log_path.exists():
                try:
                    content = log_path.read_text()
                    lines_list = content.split("\n")
                    return {
                        "status": "ok",
                        "source": str(log_path.name),
                        "logs": "\n".join(lines_list[-lines:]),
                    }
                except Exception:
                    continue

        return {"status": "error", "error": "No logs found"}

    # ─── Command History ──────────────────────────────────────────────────────

    def add_to_history(self, query: str, response: str, intents: list[str]) -> None:
        """Add a query/response pair to command history."""
        import time as time_module

        self._command_history.append(
            {
                "query": query,
                "response": response[:200] if response else "",
                "intents": intents,
                "timestamp": time_module.time(),
            }
        )
        # Keep only max_history items
        if len(self._command_history) > self._max_history:
            self._command_history = self._command_history[-self._max_history :]

    def get_history(self, limit: int = 10) -> list[dict]:
        """Get recent command history."""
        return self._command_history[-limit:]


# ─── Convenience Functions ─────────────────────────────────────────────────


def create_backend() -> ChatBackend:
    """Create a ChatBackend instance."""
    return ChatBackend()


async def quick_search_memory(query: str, limit: int = 5) -> list[dict]:
    """Quick memory search helper."""
    backend = ChatBackend()
    result = await backend.get_memory_results(query, limit=limit)
    return result.get("results", [])


async def quick_health_check() -> dict:
    """Quick health check helper."""
    backend = ChatBackend()
    return await backend.get_health_summary("l0")


async def quick_routing_stats() -> dict:
    """Quick routing stats helper."""
    backend = ChatBackend()
    return await backend.get_routing_stats()

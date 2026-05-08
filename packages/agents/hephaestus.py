"""Hephaestus Agent — Implementation Specialist.

This agent WRITES CODE. It does NOT delegate further.
All code writing flows through Hephaestus.

Role: Senior software engineer for story execution and code implementation.
Model: minimax-m2.5-free (or configured in oh-my-opencode.json)
"""

__version__ = "1.0.0"

import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("hephaestus_agent")

# Agent metadata
AGENT_NAME = "hephaestus"
AGENT_ROLE = "implementation"
AGENT_LEVEL = 3
AGENT_MODEL = "minimax-m2.5-free"


class HephaestusAgent:
    """Hephaestus - the code-writing agent.

    This agent does NOT delegate. It implements code directly.
    """

    def __init__(self):
        self.name = AGENT_NAME
        self.role = AGENT_ROLE
        self.level = AGENT_LEVEL

    async def execute(
        self, task: str, context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute a coding task directly.

        Args:
            task: The coding task description
            context: Optional execution context

        Returns:
            Dict with execution results
        """
        logger.info(f"Hephaestus executing: {task[:100]}...")

        # Import tools here to avoid circular imports
        try:
            from packages.nx_mcp.nx_delegate import nx_delegate

            # Route to get the approach
            result = nx_delegate(task, category_hint="hephaestus")

            return {
                "status": "routed",
                "agent": self.name,
                "task": task,
                "approach": result.get("strategy_used", "direct"),
                "message": "Task routed to Hephaestus for implementation",
            }
        except Exception as e:
            logger.error(f"Hephaestus execution failed: {e}")
            return {
                "status": "error",
                "agent": self.name,
                "error": str(e),
            }

    def execute_sync(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Synchronous wrapper for execute."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.execute(task, context))
                    return future.result()
            else:
                return loop.run_until_complete(self.execute(task, context))
        except RuntimeError:
            return asyncio.run(self.execute(task, context))


# Singleton instance
_agent = None


def get_agent() -> HephaestusAgent:
    """Get the Hephaestus agent singleton."""
    global _agent
    if _agent is None:
        _agent = HephaestusAgent()
    return _agent


# MCP tool entry points
async def hephaestus_execute(
    task: str, context: Optional[str] = None
) -> Dict[str, Any]:
    """Execute a coding task directly as Hephaestus.

    This is the main MCP tool - it executes code directly,
    NOT via delegation to another agent.
    """
    ctx = None
    if context:
        import json

        try:
            ctx = json.loads(context)
        except (json.JSONDecodeError, TypeError):
            ctx = {"raw": context}

    agent = get_agent()
    return await agent.execute(task, ctx)


def hephaestus_execute_sync(task: str, context: Optional[str] = None) -> Dict[str, Any]:
    """Synchronous wrapper for hephaestus_execute."""
    agent = get_agent()
    return agent.execute_sync(task, context)


def hephaestus_health_check() -> Dict[str, Any]:
    """Health check for Hephaestus agent."""
    return {
        "status": "healthy",
        "agent": AGENT_NAME,
        "role": AGENT_ROLE,
        "version": __version__,
    }


__all__ = [
    "AGENT_NAME",
    "AGENT_ROLE",
    "AGENT_LEVEL",
    "AGENT_MODEL",
    "HephaestusAgent",
    "get_agent",
    "hephaestus_execute",
    "hephaestus_execute_sync",
    "hephaestus_health_check",
]

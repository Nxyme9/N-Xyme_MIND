"""N-Xyme Orchestration Package — Agent coordination: lifecycle, task execution, session management, tool registry.

Public API:
    spawn(agent, task, context=None) -> str
    task_status(task_id) -> dict
    tools_list() -> list
"""

__interface_version__ = "1.0.0"

import uuid
from typing import Any, Dict, List, Optional

# Import submodules
from . import agents
from . import tasks
from . import sessions
from . import tools
from . import triggers
from . import governance


# Global task storage for spawn/task_status
_tasks: Dict[str, Dict[str, Any]] = {}


def spawn(agent: str, task: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Spawn an agent task.
    
    Args:
        agent: Agent name (e.g., "hephaestus", "explore", "oracle")
        task: Task description
        context: Optional context dict with additional parameters
    
    Returns:
        Task ID string
    """
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    _tasks[task_id] = {
        "id": task_id,
        "agent": agent,
        "task": task,
        "context": context or {},
        "status": "pending",
    }
    return task_id


def task_status(task_id: str) -> Dict[str, Any]:
    """Get status of a task.
    
    Args:
        task_id: Task ID returned by spawn()
    
    Returns:
        Dict with task status information
    """
    task = _tasks.get(task_id)
    if task is None:
        return {"error": "Task not found", "task_id": task_id}
    return {
        "task_id": task_id,
        "agent": task.get("agent"),
        "task": task.get("task"),
        "status": task.get("status", "unknown"),
        "context": task.get("context", {}),
    }


def tools_list() -> List[Dict[str, Any]]:
    """List all available tools.
    
    Returns:
        List of tool metadata dicts
    """
    try:
        return tools.registry.get_tool_list()
    except Exception:
        return []


# Convenience exports
__all__ = [
    "__interface_version__",
    "spawn",
    "task_status",
    "tools_list",
    # Re-export submodules
    "agents",
    "tasks",
    "sessions",
    "tools",
    "triggers",
    "governance",
]
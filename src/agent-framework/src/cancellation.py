"""
Cancellation and task tracking for interruptible agent execution.
"""

import uuid
import logging
from enum import Enum
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class TaskState(Enum):
    """Possible states for a tracked task."""

    IDLE = "idle"
    RUNNING = "running"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    ERROR = "error"


class CancellationToken:
    """Token that allows cancellation of a running task."""

    def __init__(self):
        self._cancelled = False

    def cancel(self) -> None:
        """Mark this token as cancelled."""
        self._cancelled = True
        logger.info("Cancellation token cancelled")

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancelled

    def reset(self) -> None:
        """Reset the cancellation state."""
        self._cancelled = False


class TaskTracker:
    """Tracks active tasks with their states and cancellation tokens."""

    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def register_task(
        self, task_id: str, agent_name: str, info: Optional[Dict] = None
    ) -> CancellationToken:
        """Register a new task and return its cancellation token."""
        token = CancellationToken()
        self._tasks[task_id] = {
            "task_id": task_id,
            "agent": agent_name,
            "state": TaskState.RUNNING,
            "token": token,
            "info": info or {},
        }
        logger.info(f"Task registered: {task_id} (agent: {agent_name})")
        return token

    def update_state(self, task_id: str, state: TaskState) -> None:
        """Update the state of a tracked task."""
        if task_id in self._tasks:
            self._tasks[task_id]["state"] = state
            logger.info(f"Task {task_id} state -> {state.value}")

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific task."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        return {
            "task_id": task["task_id"],
            "agent": task["agent"],
            "state": task["state"].value,
            "info": task["info"],
        }

    def get_all(self) -> List[Dict[str, Any]]:
        """Get status of all tracked tasks."""
        return [
            {
                "task_id": t["task_id"],
                "agent": t["agent"],
                "state": t["state"].value,
                "info": t["info"],
            }
            for t in self._tasks.values()
        ]

    def cancel(self, task_id: str) -> bool:
        """Cancel a running task. Returns True if cancelled."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        task["token"].cancel()
        task["state"] = TaskState.CANCELLED
        logger.info(f"Task {task_id} cancelled")
        return True

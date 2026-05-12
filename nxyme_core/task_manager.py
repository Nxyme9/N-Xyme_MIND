"""Task CRUD operations for nx-session MCP."""

import uuid
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DATA_FILE = Path.home() / ".nxyme" / "tasks.json"


class TaskState(Enum):
    """Task states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class Task:
    """Represents a task."""
    id: str
    name: str
    state: TaskState = TaskState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None


class TaskManager:
    """Manages task CRUD operations."""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._lock = asyncio.Lock()
        self._load()

    def _load(self):
        if DATA_FILE.exists():
            try:
                data = json.loads(DATA_FILE.read_text())
                for t in data.get("tasks", []):
                    t["state"] = TaskState(t["state"])
                    if "exit_code" in t:
                        del t["exit_code"]
                    # Parse datetime strings
                    t["created_at"] = datetime.fromisoformat(t["created_at"])
                    t["updated_at"] = datetime.fromisoformat(t["updated_at"])
                    if t.get("completed_at"):
                        t["completed_at"] = datetime.fromisoformat(t["completed_at"])
                    self._tasks[t["id"]] = Task(**t)
            except Exception as e:
                logger.warning(f"Failed to load tasks: {e}")

    def _save(self):
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        tasks = []
        for t in self._tasks.values():
            d = asdict(t)
            d["state"] = d["state"].value
            d["created_at"] = d["created_at"].isoformat()
            d["updated_at"] = d["updated_at"].isoformat()
            if d.get("completed_at"):
                d["completed_at"] = d["completed_at"].isoformat()
            tasks.append(d)
        data = {"tasks": tasks}
        DATA_FILE.write_text(json.dumps(data, indent=2))

    def create_task(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new task.

        Args:
            name: Task name
            metadata: Optional metadata

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            name=name,
            metadata=metadata or {}
        )
        self._tasks[task_id] = task
        self._save()
        logger.info(f"Created task: {task_id} (name: {name})")
        return task_id

    def list_tasks(
        self,
        state_filter: Optional[TaskState] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List tasks with optional filtering.

        Args:
            state_filter: Optional state to filter by
            limit: Max results
            offset: Offset for pagination

        Returns:
            List of task info dicts
        """
        tasks = []
        for task in self._tasks.values():
            if state_filter is None or task.state == state_filter:
                tasks.append({
                    "id": task.id,
                    "name": task.name,
                    "state": task.state.value,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                })

        tasks.sort(key=lambda t: self._tasks[t["id"]].created_at, reverse=True)
        return tasks[offset:offset + limit]

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task details.

        Args:
            task_id: Task ID

        Returns:
            Task info dict or None
        """
        if task_id not in self._tasks:
            return None

        task = self._tasks[task_id]
        return {
            "id": task.id,
            "name": task.name,
            "state": task.state.value,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "metadata": task.metadata,
            "exit_code": task.exit_code,
        }

    def update_task(
        self,
        task_id: str,
        name: Optional[str] = None,
        state: Optional[TaskState] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update task properties.

        Args:
            task_id: Task ID
            name: New name (optional)
            state: New state (optional)
            metadata: New metadata (optional)

        Returns:
            True if updated, False if not found
        """
        if task_id not in self._tasks:
            return False

        task = self._tasks[task_id]
        task.updated_at = datetime.now()

        if name is not None:
            task.name = name
        if state is not None:
            task.state = state
            if state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.STOPPED):
                task.completed_at = datetime.now()
        if metadata is not None:
            task.metadata.update(metadata)

        self._save()
        logger.info(f"Updated task: {task_id}")
        return True

    def stop_task(self, task_id: str) -> bool:
        """Stop a running task.

        Args:
            task_id: Task ID

        Returns:
            True if stopped, False if not found
        """
        return self.update_task(task_id, state=TaskState.STOPPED)

    def get_task_output(self, task_id: str) -> Optional[Dict[str, str]]:
        """Get task output (stdout/stderr).

        Args:
            task_id: Task ID

        Returns:
            Dict with stdout/stderr or None
        """
        if task_id not in self._tasks:
            return None

        task = self._tasks[task_id]
        return {
            "stdout": task.stdout,
            "stderr": task.stderr,
            "exit_code": str(task.exit_code) if task.exit_code is not None else "",
        }

    def delete_task(self, task_id: str) -> bool:
        """Delete a task.

        Args:
            task_id: Task ID

        Returns:
            True if deleted, False if not found
        """
        if task_id not in self._tasks:
            return False

        del self._tasks[task_id]
        self._save()
        logger.info(f"Deleted task: {task_id}")
        return True

    def health_check(self) -> Dict[str, Any]:
        """Health check."""
        states = {}
        for task in self._tasks.values():
            states[task.id] = task.state.value

        return {
            "status": "healthy",
            "total_tasks": len(self._tasks),
            "states": states,
        }


_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """Get global TaskManager instance."""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


__all__ = ["TaskManager", "Task", "TaskState", "get_task_manager"]
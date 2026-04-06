"""Task queue management module for N-Xyme MIND Dashboard."""

from dataclasses import dataclass
from typing import Optional
import time


@dataclass
class Task:
    """Represents a task in the task queue.

    Attributes:
        task_id: Unique identifier for the task.
        name: Human-readable name of the task.
        status: Current status of the task ("pending", "running", "completed", "failed").
        created_at: Unix timestamp when the task was created.
        started_at: Unix timestamp when the task started running, or None if not started.
        completed_at: Unix timestamp when the task completed, or None if not completed.
    """

    task_id: str
    name: str
    status: str
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


class TaskManager:
    """Manages task queue operations for the dashboard.

    Provides methods to create, start, stop, retrieve, and delete tasks.
    Task IDs are auto-generated in the format "task_001", "task_002", etc.
    """

    def __init__(self):
        """Initialize the TaskManager with an empty task dictionary."""
        self._tasks: dict[str, Task] = {}
        self._task_counter: int = 0

    def get_tasks(self) -> list[Task]:
        """Return all tasks.

        Returns:
            List of all Task objects in the queue.
        """
        return list(self._tasks.values())

    def _generate_task_id(self) -> str:
        """Generate the next auto-incremented task ID.

        Returns:
            A task ID in the format "task_001", "task_002", etc.
        """
        self._task_counter += 1
        return f"task_{self._task_counter:03d}"

    def create_task(self, name: str) -> str:
        """Create a new task with the given name.

        Args:
            name: Human-readable name for the task.

        Returns:
            The generated task ID.
        """
        task_id = self._generate_task_id()
        task = Task(
            task_id=task_id, name=name, status="pending", created_at=time.time()
        )
        self._tasks[task_id] = task
        return task_id

    def start_task(self, task_id: str) -> bool:
        """Start a pending task.

        Args:
            task_id: The ID of the task to start.

        Returns:
            True if the task was started successfully, False otherwise.
        """
        task = self._tasks.get(task_id)
        if task is None:
            return False
        if task.status != "pending":
            return False
        task.status = "running"
        task.started_at = time.time()
        return True

    def stop_task(self, task_id: str) -> bool:
        """Stop a running task.

        Args:
            task_id: The ID of the task to stop.

        Returns:
            True if the task was stopped successfully, False otherwise.
        """
        task = self._tasks.get(task_id)
        if task is None:
            return False
        if task.status != "running":
            return False
        task.status = "failed"
        task.completed_at = time.time()
        return True

    def get_task_status(self, task_id: str) -> Optional[Task]:
        """Get a task by its ID.

        Args:
            task_id: The ID of the task to retrieve.

        Returns:
            The Task object if found, None otherwise.
        """
        return self._tasks.get(task_id)

    def delete_task(self, task_id: str) -> bool:
        """Remove a task from the queue.

        Args:
            task_id: The ID of the task to delete.

        Returns:
            True if the task was deleted, False if it didn't exist.
        """
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def clear_completed(self) -> int:
        """Remove all completed tasks from the queue.

        Returns:
            The number of tasks that were removed.
        """
        completed_ids = [
            task_id
            for task_id, task in self._tasks.items()
            if task.status in ("completed", "failed")
        ]
        for task_id in completed_ids:
            del self._tasks[task_id]
        return len(completed_ids)

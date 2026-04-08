"""Task Lifecycle — Full task state machine.

Ported from ant-source-code-main/Task.ts + tasks/
Implements a complete task lifecycle with:
- Task states: pending → running → paused → completed/failed/cancelled
- Task persistence, resumption, and dependency tracking
- Task hierarchy (parent/child tasks)
- Task output streaming and retrieval
- Auto-logging of task outcomes to learning engine

Pattern: Tasks are first-class citizens with full lifecycle management,
enabling complex multi-step workflows with error recovery.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Import hooks for auto-logging (lazy import to avoid circular deps)
_task_outcome_hook: Optional[Any] = None

# TaskWatchdog singleton
_watchdog: Optional[Any] = None


def _get_watchdog():
    """Lazily load TaskWatchdog to avoid circular imports."""
    global _watchdog
    if _watchdog is None:
        try:
            from packages.orchestration.task_watchdog import get_watchdog
            _watchdog = get_watchdog()
        except ImportError as e:
            logger.warning(f"Could not import TaskWatchdog: {e}")
            _watchdog = False  # Mark as failed
    return _watchdog if _watchdog else None


class TaskType(str, Enum):
    """Types of tasks."""

    LOCAL_BASH = "local_bash"
    LOCAL_AGENT = "local_agent"
    REMOTE_AGENT = "remote_agent"
    WORKFLOW = "workflow"
    MONITOR = "monitor"
    DREAM = "dream"  # Background async task


class TaskStatus(str, Enum):
    """Task status states."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        """True when task is in terminal state."""
        return self in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        )


# Task ID prefixes by type
TASK_ID_PREFIXES = {
    TaskType.LOCAL_BASH: "b",
    TaskType.LOCAL_AGENT: "a",
    TaskType.REMOTE_AGENT: "r",
    TaskType.WORKFLOW: "w",
    TaskType.MONITOR: "m",
    TaskType.DREAM: "d",
}


def generate_task_id(task_type: TaskType) -> str:
    """Generate a unique task ID with type prefix."""
    prefix = TASK_ID_PREFIXES.get(task_type, "x")
    unique = uuid.uuid4().hex[:8]
    return f"{prefix}_{unique}"


@dataclass
class TaskOutput:
    """Output from a task execution."""

    task_id: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    output_file: str | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class Task:
    """A task with full lifecycle management."""

    id: str
    type: TaskType
    description: str
    status: TaskStatus = TaskStatus.PENDING
    parent_id: str | None = None
    dependencies: list[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    started_at: str | None = None
    completed_at: str | None = None
    paused_at: str | None = None
    total_paused_ms: float = 0.0
    output: TaskOutput | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    retries: int = 0
    max_retries: int = 0
    timeout_seconds: float | None = None

    @property
    def is_terminal(self) -> bool:
        """True when task is in terminal state."""
        return self.status.is_terminal

    @property
    def is_running(self) -> bool:
        """True when task is currently running."""
        return self.status == TaskStatus.RUNNING

    @property
    def is_paused(self) -> bool:
        """True when task is paused."""
        return self.status == TaskStatus.PAUSED

    @property
    def duration_seconds(self) -> float | None:
        """Get task duration in seconds."""
        if self.started_at is None:
            return None
        end_time = self.completed_at or datetime.now(timezone.utc).isoformat()
        start = datetime.fromisoformat(self.started_at)
        end = datetime.fromisoformat(end_time)
        return (end - start).total_seconds() - (self.total_paused_ms / 1000)

    def start(self) -> None:
        """Transition task to running state."""
        if self.status != TaskStatus.PENDING:
            raise ValueError(f"Cannot start task in {self.status} state")
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now(timezone.utc).isoformat()
        # Call the outcome hook
        _call_before_task(self)

    def pause(self) -> None:
        """Pause a running task."""
        if self.status != TaskStatus.RUNNING:
            raise ValueError(f"Cannot pause task in {self.status} state")
        self.status = TaskStatus.PAUSED
        self.paused_at = datetime.now(timezone.utc).isoformat()

    def resume(self) -> None:
        """Resume a paused task."""
        if self.status != TaskStatus.PAUSED:
            raise ValueError(f"Cannot resume task in {self.status} state")
        if self.paused_at:
            pause_start = datetime.fromisoformat(self.paused_at)
            pause_duration = (
                datetime.now(timezone.utc) - pause_start
            ).total_seconds() * 1000
            self.total_paused_ms += pause_duration
        self.status = TaskStatus.RUNNING
        self.paused_at = None

    def complete(self, output: TaskOutput | None = None) -> None:
        """Mark task as completed."""
        if self.status.is_terminal:
            raise ValueError(f"Cannot complete task in {self.status} state")
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc).isoformat()
        if output:
            self.output = output
        # Call the outcome hook for success
        _call_after_task(self, success=True)

    def fail(self, error_message: str) -> None:
        """Mark task as failed."""
        if self.status.is_terminal:
            raise ValueError(f"Cannot fail task in {self.status} state")
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.error_message = error_message
        # Call the outcome hook for failure
        _call_after_task(self, success=False, error=error_message)

    def cancel(self) -> None:
        """Cancel a task."""
        if self.status.is_terminal:
            raise ValueError(f"Cannot cancel task in {self.status} state")
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc).isoformat()
        # Call the outcome hook for cancellation (treated as failure)
        _call_after_task(self, success=False, error="cancelled")

    def to_dict(self) -> dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "dependencies": self.dependencies,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "paused_at": self.paused_at,
            "total_paused_ms": self.total_paused_ms,
            "output": {
                "task_id": self.output.task_id,
                "stdout": self.output.stdout,
                "stderr": self.output.stderr,
                "exit_code": self.output.exit_code,
                "output_file": self.output.output_file,
                "timestamp": self.output.timestamp,
            }
            if self.output
            else None,
            "metadata": self.metadata,
            "error_message": self.error_message,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """Create task from dictionary."""
        output_data = data.get("output")
        output = None
        if output_data:
            output = TaskOutput(
                task_id=output_data["task_id"],
                stdout=output_data.get("stdout", ""),
                stderr=output_data.get("stderr", ""),
                exit_code=output_data.get("exit_code"),
                output_file=output_data.get("output_file"),
                timestamp=output_data.get("timestamp", ""),
            )

        return cls(
            id=data["id"],
            type=TaskType(data["type"]),
            description=data["description"],
            status=TaskStatus(data["status"]),
            parent_id=data.get("parent_id"),
            dependencies=data.get("dependencies", []),
            created_at=data.get("created_at", ""),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            paused_at=data.get("paused_at"),
            total_paused_ms=data.get("total_paused_ms", 0.0),
            output=output,
            metadata=data.get("metadata", {}),
            error_message=data.get("error_message"),
            retries=data.get("retries", 0),
            max_retries=data.get("max_retries", 0),
            timeout_seconds=data.get("timeout_seconds"),
        )


class TaskManager:
    """Manages task lifecycle, persistence, and dependencies."""

    def __init__(self, storage_path: Path | None = None):
        """Initialize task manager.

        Args:
            storage_path: Path to store task data.
        """
        self.tasks: dict[str, Task] = {}
        self.storage_path = storage_path or Path(".sisyphus/tasks")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._load_tasks()
        self._callbacks: dict[str, list[Callable]] = {}

    def create_task(
        self,
        task_type: TaskType,
        description: str,
        parent_id: str | None = None,
        dependencies: list[str] | None = None,
        max_retries: int = 0,
        timeout_seconds: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        """Create a new task.

        Args:
            task_type: Type of task.
            description: Task description.
            parent_id: Parent task ID (for hierarchical tasks).
            dependencies: List of task IDs this task depends on.
            max_retries: Maximum number of retries on failure.
            timeout_seconds: Task timeout in seconds.
            metadata: Additional task metadata.

        Returns:
            Created Task.
        """
        task_id = generate_task_id(task_type)
        task = Task(
            id=task_id,
            type=task_type,
            description=description,
            parent_id=parent_id,
            dependencies=dependencies or [],
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            metadata=metadata or {},
        )
        self.tasks[task_id] = task
        self._save_task(task)
        logger.info(f"Created task: {task_id} ({task_type.value})")
        return task

    def get_task(self, task_id: str) -> Task | None:
        """Get task by ID."""
        return self.tasks.get(task_id)

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        task_type: TaskType | None = None,
        parent_id: str | None = None,
    ) -> list[Task]:
        """List tasks with optional filters."""
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        if task_type:
            tasks = [t for t in tasks if t.type == task_type]
        if parent_id is not None:
            tasks = [t for t in tasks if t.parent_id == parent_id]
        return tasks

    def get_child_tasks(self, parent_id: str) -> list[Task]:
        """Get all child tasks of a parent."""
        return [t for t in self.tasks.values() if t.parent_id == parent_id]

    def are_dependencies_met(self, task_id: str) -> bool:
        """Check if all dependencies for a task are completed."""
        task = self.tasks.get(task_id)
        if not task:
            return False
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if (
                not dep_task
                or not dep_task.status.is_terminal
                or dep_task.status == TaskStatus.FAILED
            ):
                return False
        return True

    def register_callback(
        self,
        task_id: str,
        callback: Callable[[Task], None],
    ) -> None:
        """Register a callback for task status changes."""
        if task_id not in self._callbacks:
            self._callbacks[task_id] = []
        self._callbacks[task_id].append(callback)

    def _notify_callbacks(self, task: Task) -> None:
        """Notify callbacks of task status change."""
        for callback in self._callbacks.get(task.id, []):
            try:
                callback(task)
            except Exception as e:
                logger.error(f"Task callback error: {e}")

    def _save_task(self, task: Task) -> None:
        """Save task to storage."""
        task_file = self.storage_path / f"{task.id}.json"
        task_file.write_text(json.dumps(task.to_dict(), indent=2))

    def _load_tasks(self) -> None:
        """Load tasks from storage."""
        for task_file in self.storage_path.glob("*.json"):
            try:
                data = json.loads(task_file.read_text())
                task = Task.from_dict(data)
                self.tasks[task.id] = task
            except Exception as e:
                logger.warning(f"Failed to load task {task_file}: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get task manager statistics."""
        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}
        for task in self.tasks.values():
            by_status[task.status.value] = by_status.get(task.status.value, 0) + 1
            by_type[task.type.value] = by_type.get(task.type.value, 0) + 1

        return {
            "total_tasks": len(self.tasks),
            "by_status": by_status,
            "by_type": by_type,
        }


# Global singleton
_task_manager = TaskManager()


def create_task(
    task_type: TaskType,
    description: str,
    parent_id: str | None = None,
    dependencies: list[str] | None = None,
    max_retries: int = 0,
    timeout_seconds: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> Task:
    """Convenience function to create a task."""
    return _task_manager.create_task(
        task_type,
        description,
        parent_id,
        dependencies,
        max_retries,
        timeout_seconds,
        metadata,
    )


def get_task(task_id: str) -> Task | None:
    """Convenience function to get a task."""
    return _task_manager.get_task(task_id)


def list_tasks(
    status: TaskStatus | None = None,
    task_type: TaskType | None = None,
    parent_id: str | None = None,
) -> list[Task]:
    """Convenience function to list tasks."""
    return _task_manager.list_tasks(status, task_type, parent_id)


# =============================================================================
# TaskOutcomeHook Integration
# =============================================================================

def _get_task_outcome_hook():
    """Lazily load TaskOutcomeHook to avoid circular imports."""
    global _task_outcome_hook
    if _task_outcome_hook is None:
        try:
            from learning_engine import get_task_hook
            _task_outcome_hook = get_task_hook()
        except ImportError as e:
            logger.warning(f"Could not import TaskOutcomeHook: {e}")
            _task_outcome_hook = False  # Mark as failed
    return _task_outcome_hook if _task_outcome_hook else None


def _call_before_task(task: Task) -> None:
    """Call TaskOutcomeHook.before_task() when task starts."""
    hook = _get_task_outcome_hook()
    if hook is None:
        return
    try:
        task_type_map = {
            TaskType.LOCAL_BASH: "implementation",
            TaskType.LOCAL_AGENT: "implementation",
            TaskType.REMOTE_AGENT: "implementation",
            TaskType.WORKFLOW: "implementation",
            TaskType.MONITOR: "monitor",
            TaskType.DREAM: "research",
        }
        hook.before_task(
            task_id=task.id,
            description=task.description,
            agent="unknown",  # Will be auto-detected
            level=3,  # Default to moderate complexity
            task_type=task_type_map.get(task.type, "implementation"),
            context={
                "task_type_enum": task.type.value,
                "parent_id": task.parent_id,
                "dependencies": task.dependencies,
                "metadata": task.metadata,
            },
        )
    except Exception as e:
        logger.error(f"Error calling before_task hook: {e}")
    finally:
        # Register with TaskWatchdog for timeout monitoring
        _register_with_watchdog(task)


def _register_with_watchdog(task: Task) -> None:
    """Register task with TaskWatchdog for stall detection."""
    watchdog = _get_watchdog()
    if watchdog is None:
        return
    try:
        timeout = task.timeout_seconds or 300  # Default 5 min
        watchdog.register_task(
            task_id=task.id,
            agent_type=task.type.value,
            timeout_seconds=timeout,
        )
    except Exception as e:
        logger.error(f"Error registering with watchdog: {e}")


def send_heartbeat(task_id: str) -> None:
    """Send heartbeat for a running task to prevent stall detection."""
    watchdog = _get_watchdog()
    if watchdog is None:
        return
    try:
        watchdog.heartbeat(task_id)
    except Exception as e:
        logger.error(f"Error sending heartbeat: {e}")


def _call_after_task(task: Task, success: bool, error: str | None = None) -> None:
    """Call TaskOutcomeHook.after_task() when task completes."""
    hook = _get_task_outcome_hook()
    if hook is None:
        return
    try:
        additional_context = {
            "task_type_enum": task.type.value,
            "status": task.status.value,
            "duration_seconds": task.duration_seconds,
        }
        if task.output:
            additional_context["exit_code"] = task.output.exit_code
        if task.metadata:
            additional_context["metadata"] = task.metadata

        hook.after_task(
            task_id=task.id,
            success=success,
            error=error or task.error_message,
            additional_context=additional_context,
        )
    except Exception as e:
        logger.error(f"Error calling after_task hook: {e}")

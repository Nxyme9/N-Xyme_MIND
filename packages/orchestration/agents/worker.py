"""Individual agent worker implementation with task execution, timeout, retry, and health checks."""

from __future__ import annotations

import logging
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class WorkerState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class WorkerTask:
    """Represents a unit of work for an agent worker."""

    id: str
    agent_type: str
    payload: dict[str, Any]
    priority: str = "normal"
    timeout_seconds: float = 300.0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    callback: Callable[[WorkerResult], None] | None = None


@dataclass
class WorkerResult:
    """Result of a worker task execution."""

    task_id: str
    agent_type: str
    success: bool
    output: Any = None
    error: str = ""
    retries: int = 0
    started_at: float = 0.0
    completed_at: float = 0.0
    duration_seconds: float = 0.0

    @property
    def is_timed_out(self) -> bool:
        return "timeout" in self.error.lower()

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_type": self.agent_type,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "retries": self.retries,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
        }


class AgentWorker:
    """Individual worker that executes tasks for a specific agent type.

    Handles task execution with timeout, error handling, retry logic,
    result reporting, and health checks.
    """

    def __init__(
        self,
        worker_id: str | None = None,
        agent_type: str = "unknown",
        max_retries: int = 3,
        default_timeout: float = 300.0,
        executor: ThreadPoolExecutor | None = None,
    ):
        self.id = worker_id or f"worker-{agent_type}-{uuid.uuid4().hex[:8]}"
        self.agent_type = agent_type
        self.max_retries = max_retries
        self.default_timeout = default_timeout
        self._executor = executor or ThreadPoolExecutor(max_workers=1)
        self._state = WorkerState.IDLE
        self._current_task: WorkerTask | None = None
        self._last_heartbeat: float = time.time()
        self._tasks_completed: int = 0
        self._tasks_failed: int = 0
        self._total_duration: float = 0.0
        self._last_error: str = ""
        self._last_result: WorkerResult | None = None
        self._task_handler: Callable[[WorkerTask], Any] | None = None

    @property
    def state(self) -> WorkerState:
        return self._state

    @property
    def is_idle(self) -> bool:
        return self._state == WorkerState.IDLE

    @property
    def is_busy(self) -> bool:
        return self._state == WorkerState.RUNNING

    @property
    def tasks_completed(self) -> int:
        return self._tasks_completed

    @property
    def tasks_failed(self) -> int:
        return self._tasks_failed

    @property
    def last_heartbeat(self) -> float:
        return self._last_heartbeat

    @property
    def current_task_id(self) -> str | None:
        return self._current_task.id if self._current_task else None

    @property
    def last_error(self) -> str:
        return self._last_error

    @property
    def last_result(self) -> WorkerResult | None:
        return self._last_result

    @property
    def average_task_duration(self) -> float:
        total = self._tasks_completed + self._tasks_failed
        return self._total_duration / total if total > 0 else 0.0

    def register_handler(self, handler: Callable[[WorkerTask], Any]) -> None:
        """Register a callable that will be invoked for each task."""
        self._task_handler = handler

    def heartbeat(self) -> float:
        """Update heartbeat timestamp and return it."""
        self._last_heartbeat = time.time()
        return self._last_heartbeat

    def health_check(self) -> dict[str, Any]:
        """Return health status of this worker."""
        now = time.time()
        heartbeat_age = now - self._last_heartbeat
        return {
            "worker_id": self.id,
            "agent_type": self.agent_type,
            "state": self._state.value,
            "current_task_id": self.current_task_id,
            "last_heartbeat": self._last_heartbeat,
            "heartbeat_age_seconds": round(heartbeat_age, 2),
            "tasks_completed": self._tasks_completed,
            "tasks_failed": self._tasks_failed,
            "average_task_duration": round(self.average_task_duration, 3),
            "last_error": self._last_error,
            "healthy": self._state not in (WorkerState.ERROR, WorkerState.STOPPED)
            and heartbeat_age < 60,
        }

    def execute(self, task: WorkerTask) -> Future[WorkerResult]:
        """Submit a task for execution. Returns a Future."""
        if self._state in (WorkerState.STOPPING, WorkerState.STOPPED):
            result = WorkerResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                error=f"Worker {self.id} is {self._state.value}",
            )
            fut: Future[WorkerResult] = Future()
            fut.set_result(result)
            return fut

        self._state = WorkerState.RUNNING
        self._current_task = task
        self.heartbeat()

        future = self._executor.submit(self._run_task, task)
        future.add_done_callback(self._on_task_done)
        return future

    def _run_task(self, task: WorkerTask) -> WorkerResult:
        """Execute a single task with retry logic."""
        retries = 0
        last_error = ""

        while retries <= task.max_retries:
            result = WorkerResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                retries=retries,
                started_at=time.time(),
            )

            try:
                if self._task_handler:
                    output = self._task_handler(task)
                else:
                    output = self._default_handler(task)

                result.success = True
                result.output = output
                result.completed_at = time.time()
                result.duration_seconds = result.completed_at - result.started_at
                self._tasks_completed += 1
                self._total_duration += result.duration_seconds
                self._last_result = result
                self._last_error = ""
                logger.info(
                    f"worker:{self.id}:task_complete",
                    extra={
                        "context": {
                            "task_id": task.id,
                            "agent_type": self.agent_type,
                            "duration": round(result.duration_seconds, 3),
                            "retries": retries,
                        }
                    },
                )
                return result

            except TimeoutError as e:
                last_error = f"Timeout after {task.timeout_seconds}s: {e}"
                result.error = last_error
                result.completed_at = time.time()
                result.duration_seconds = result.completed_at - result.started_at
                logger.warning(
                    f"worker:{self.id}:task_timeout",
                    extra={
                        "context": {
                            "task_id": task.id,
                            "agent_type": self.agent_type,
                            "retry": retries,
                            "error": last_error,
                        }
                    },
                )

            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                result.error = last_error
                result.completed_at = time.time()
                result.duration_seconds = result.completed_at - result.started_at
                logger.error(
                    f"worker:{self.id}:task_error",
                    extra={
                        "context": {
                            "task_id": task.id,
                            "agent_type": self.agent_type,
                            "retry": retries,
                            "error": last_error,
                        }
                    },
                )

            retries += 1
            result.retries = retries

            if retries <= task.max_retries:
                self.heartbeat()
                time.sleep(0.1 * retries)

        self._tasks_failed += 1
        self._total_duration += result.duration_seconds
        self._last_error = last_error
        self._last_result = result
        logger.error(
            f"worker:{self.id}:task_failed",
            extra={
                "context": {
                    "task_id": task.id,
                    "agent_type": self.agent_type,
                    "total_retries": retries,
                    "error": last_error,
                }
            },
        )
        return result

    def _on_task_done(self, future: Future[WorkerResult]) -> None:
        """Callback when a task future completes."""
        self._state = WorkerState.IDLE
        self._current_task = None
        self.heartbeat()

    def _default_handler(self, task: WorkerTask) -> Any:
        """Default task handler — echoes the payload."""
        return {"echo": task.payload, "worker_id": self.id}

    def stop(self, graceful: bool = True) -> None:
        """Stop the worker."""
        if self._state == WorkerState.STOPPED:
            return

        self._state = WorkerState.STOPPING

        if graceful and self._current_task is not None:
            logger.info(
                f"worker:{self.id}:waiting_for_current_task",
                extra={"context": {"task_id": self.current_task_id}},
            )

        self._state = WorkerState.STOPPED
        self._current_task = None
        logger.info(f"worker:{self.id}:stopped")

    def shutdown(self) -> None:
        """Shut down the internal executor."""
        self.stop(graceful=True)
        self._executor.shutdown(wait=True)

"""Task Watchdog - Automatic timeout and redelegation for stalled agents."""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


class TaskState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    STALLED = "stalled"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentTask:
    task_id: str
    agent_type: str
    created_at: float
    last_heartbeat: float
    timeout_seconds: float = 300  # 5 min default
    state: TaskState = TaskState.PENDING
    retry_count: int = 0


class TaskWatchdog:
    """Monitors agent tasks and auto-cancels stalled ones."""
    
    def __init__(self, check_interval: float = 30.0):
        self._tasks: Dict[str, AgentTask] = {}
        self._lock = threading.Lock()
        self._check_interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._max_retries = 3
        self._on_stalled: Optional[Callable] = None
    
    def register_task(self, task_id: str, agent_type: str, timeout_seconds: float = 300) -> None:
        """Register a new task for monitoring."""
        with self._lock:
            self._tasks[task_id] = AgentTask(
                task_id=task_id,
                agent_type=agent_type,
                created_at=time.time(),
                last_heartbeat=time.time(),
                timeout_seconds=timeout_seconds,
                state=TaskState.RUNNING
            )
            logger.info(f"TaskWatchdog: Registered task {task_id} ({agent_type})")
    
    def heartbeat(self, task_id: str) -> None:
        """Update task heartbeat."""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].last_heartbeat = time.time()
    
    def _check_stalled(self) -> None:
        """Check for stalled tasks."""
        now = time.time()
        with self._lock:
            for task_id, task in self._tasks.items():
                if task.state == TaskState.RUNNING:
                    elapsed = now - task.last_heartbeat
                    if elapsed > task.timeout_seconds:
                        task.state = TaskState.STALLED
                        logger.warning(f"TaskWatchdog: Task {task_id} STALLED (elapsed {elapsed:.0f}s)")
                        if self._on_stalled:
                            self._on_stalled(task)
    
    def start(self, on_stalled: Optional[Callable] = None) -> None:
        """Start the watchdog."""
        self._on_stalled = on_stalled
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("TaskWatchdog: Started")
    
    def _run_loop(self) -> None:
        while self._running:
            self._check_stalled()
            time.sleep(self._check_interval)
    
    def stop(self) -> None:
        """Stop the watchdog."""
        self._running = False
        logger.info("TaskWatchdog: Stopped")


# Singleton
_watchdog: Optional[TaskWatchdog] = None


def get_watchdog() -> TaskWatchdog:
    global _watchdog
    if _watchdog is None:
        _watchdog = TaskWatchdog()
    return _watchdog
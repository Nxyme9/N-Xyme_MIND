"""Worker pool manager with configurable pool sizes, task assignment, graceful shutdown, and health monitoring."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .agent_worker import AgentWorker, WorkerResult, WorkerState, WorkerTask

try:
    from ..message_queue.message_queue import MessagePriority, MessageQueue
except ImportError:
    MessageQueue = None
    MessagePriority = None

try:
    from src.observability.metrics import get_metrics_collector
except ImportError:
    get_metrics_collector = None

try:
    from src.tools.observability.logger import get_logger
except ImportError:
    get_logger = None

logger = logging.getLogger(__name__)

DEFAULT_POOL_SIZES: dict[str, int] = {
    "hephaestus": 3,
    "explore": 2,
    "oracle": 1,
    "sisyphus": 1,
    "prometheus": 1,
    "metis": 1,
    "momus": 1,
    "librarian": 1,
}


@dataclass
class PoolStatus:
    """Snapshot of the worker pool state."""

    total_workers: int = 0
    active_workers: int = 0
    idle_workers: int = 0
    stopped_workers: int = 0
    error_workers: int = 0
    queue_depth: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    workers_by_type: dict[str, dict[str, int]] = field(default_factory=dict)
    started_at: float = 0.0
    uptime_seconds: float = 0.0
    is_running: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_workers": self.total_workers,
            "active_workers": self.active_workers,
            "idle_workers": self.idle_workers,
            "stopped_workers": self.stopped_workers,
            "error_workers": self.error_workers,
            "queue_depth": self.queue_depth,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "workers_by_type": self.workers_by_type,
            "started_at": self.started_at,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "is_running": self.is_running,
        }


class WorkerPool:
    """Manages a pool of agent workers with configurable sizes per agent type.

    Integrates with the message queue for task distribution,
    metrics collector for observability, and structured logging.
    """

    def __init__(
        self,
        pool_sizes: dict[str, int] | None = None,
        message_queue: MessageQueue | None = None,
        default_timeout: float = 300.0,
        max_retries: int = 3,
        queue_poll_interval: float = 0.5,
        task_handler: Callable[[WorkerTask], Any] | None = None,
    ):
        self._pool_sizes = pool_sizes or dict(DEFAULT_POOL_SIZES)
        self._default_timeout = default_timeout
        self._max_retries = max_retries
        self._queue_poll_interval = queue_poll_interval
        self._task_handler = task_handler

        self._workers: list[AgentWorker] = []
        self._workers_by_type: dict[str, list[AgentWorker]] = {}
        self._worker_futures: dict[str, Future[WorkerResult]] = {}
        self._lock = threading.Lock()

        self._message_queue = message_queue
        self._metrics = get_metrics_collector() if get_metrics_collector else None

        self._running = False
        self._started_at: float = 0.0
        self._completed_tasks: int = 0
        self._failed_tasks: int = 0

        self._dispatcher_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        self._result_callbacks: list[Callable[[WorkerResult], None]] = []

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def worker_count(self) -> int:
        return len(self._workers)

    @property
    def completed_tasks(self) -> int:
        return self._completed_tasks

    @property
    def failed_tasks(self) -> int:
        return self._failed_tasks

    def on_result(self, callback: Callable[[WorkerResult], None]) -> None:
        """Register a callback for task results."""
        self._result_callbacks.append(callback)

    def start_pool(self) -> None:
        """Start the worker pool with configured sizes per agent type."""
        if self._running:
            logger.warning("worker_pool:already_running")
            return

        self._running = True
        self._started_at = time.time()
        self._stop_event.clear()

        self._workers.clear()
        self._workers_by_type.clear()

        for agent_type, count in self._pool_sizes.items():
            if count <= 0:
                continue
            self._workers_by_type[agent_type] = []
            for i in range(count):
                worker = AgentWorker(
                    worker_id=f"worker-{agent_type}-{i}",
                    agent_type=agent_type,
                    max_retries=self._max_retries,
                    default_timeout=self._default_timeout,
                )
                if self._task_handler:
                    worker.register_handler(self._task_handler)
                self._workers.append(worker)
                self._workers_by_type[agent_type].append(worker)

        self._emit_metric("pool_workers_total", len(self._workers))
        logger.info(
            f"worker_pool:started",
            extra={
                "context": {
                    "total_workers": len(self._workers),
                    "pool_sizes": self._pool_sizes,
                }
            },
        )

        self._dispatcher_thread = threading.Thread(
            target=self._dispatcher_loop, daemon=True, name="worker-pool-dispatcher"
        )
        self._dispatcher_thread.start()

    def submit_task(
        self,
        task: WorkerTask | dict[str, Any],
        agent_type: str | None = None,
        priority: str = "normal",
    ) -> str:
        """Submit a task to the pool.

        Args:
            task: WorkerTask instance or dict with task payload.
            agent_type: Target agent type. If None, inferred from task.
            priority: Task priority (high, normal, low).

        Returns:
            Task ID.
        """
        if not self._running:
            raise RuntimeError("Worker pool is not running. Call start_pool() first.")

        if isinstance(task, dict):
            agent_type = agent_type or task.get("agent_type", "unknown")
            task_obj = WorkerTask(
                id=task.get("id", str(uuid.uuid4())),
                agent_type=agent_type,
                payload=task.get("payload", task),
                priority=priority,
                timeout_seconds=task.get("timeout_seconds", self._default_timeout),
                max_retries=task.get("max_retries", self._max_retries),
            )
        else:
            task_obj = task
            if agent_type:
                task_obj.agent_type = agent_type

        worker = self._find_idle_worker(task_obj.agent_type)
        if worker is None:
            self._enqueue_task(task_obj)
            self._emit_metric("pool_tasks_queued_total", 1)
            logger.info(
                f"worker_pool:task_enqueued",
                extra={
                    "context": {
                        "task_id": task_obj.id,
                        "agent_type": task_obj.agent_type,
                        "reason": "no_idle_worker",
                    }
                },
            )
            return task_obj.id

        future = worker.execute(task_obj)
        with self._lock:
            self._worker_futures[task_obj.id] = future
        future.add_done_callback(self._on_result)
        self._emit_metric("pool_tasks_dispatched_total", 1)
        logger.info(
            f"worker_pool:task_dispatched",
            extra={
                "context": {
                    "task_id": task_obj.id,
                    "agent_type": task_obj.agent_type,
                    "worker_id": worker.id,
                }
            },
        )
        return task_obj.id

    def get_pool_status(self) -> PoolStatus:
        """Get current pool status."""
        active = 0
        idle = 0
        stopped = 0
        error = 0
        workers_by_type: dict[str, dict[str, int]] = {}

        for worker in self._workers:
            health = worker.health_check()
            state = worker.state
            agent_type = worker.agent_type

            if agent_type not in workers_by_type:
                workers_by_type[agent_type] = {
                    "total": 0,
                    "active": 0,
                    "idle": 0,
                    "stopped": 0,
                    "error": 0,
                }
            workers_by_type[agent_type]["total"] += 1

            if state == WorkerState.RUNNING:
                active += 1
                workers_by_type[agent_type]["active"] += 1
            elif state == WorkerState.IDLE:
                idle += 1
                workers_by_type[agent_type]["idle"] += 1
            elif state == WorkerState.STOPPED:
                stopped += 1
                workers_by_type[agent_type]["stopped"] += 1
            elif state == WorkerState.ERROR:
                error += 1
                workers_by_type[agent_type]["error"] += 1

        queue_depth = 0
        if self._message_queue:
            try:
                queue_depth = self._message_queue.get_queue_depth()
            except Exception:
                pass

        now = time.time()
        uptime = now - self._started_at if self._started_at > 0 else 0.0

        status = PoolStatus(
            total_workers=len(self._workers),
            active_workers=active,
            idle_workers=idle,
            stopped_workers=stopped,
            error_workers=error,
            queue_depth=queue_depth,
            completed_tasks=self._completed_tasks,
            failed_tasks=self._failed_tasks,
            workers_by_type=workers_by_type,
            started_at=self._started_at,
            uptime_seconds=uptime,
            is_running=self._running,
        )

        if self._metrics:
            try:
                self._metrics.gauge_set("pool_active_workers", active)
                self._metrics.gauge_set("pool_idle_workers", idle)
                self._metrics.gauge_set("pool_queue_depth", queue_depth)
            except Exception:
                pass

        return status

    def shutdown(self, graceful: bool = True) -> None:
        """Shut down the worker pool.

        Args:
            graceful: If True, wait for current tasks to complete.
                     If False, stop immediately.
        """
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._dispatcher_thread and self._dispatcher_thread.is_alive():
            self._dispatcher_thread.join(timeout=5.0)

        for worker in self._workers:
            try:
                worker.stop(graceful=graceful)
                if not graceful:
                    worker.shutdown()
            except Exception as e:
                logger.error(
                    f"worker_pool:shutdown_error",
                    extra={"context": {"worker_id": worker.id, "error": str(e)}},
                )

        if graceful:
            for worker in self._workers:
                try:
                    worker.shutdown()
                except Exception:
                    pass

        self._workers.clear()
        self._workers_by_type.clear()
        with self._lock:
            self._worker_futures.clear()

        self._emit_metric("pool_shutdown", 1)
        logger.info(
            f"worker_pool:shutdown",
            extra={
                "context": {
                    "graceful": graceful,
                    "completed": self._completed_tasks,
                    "failed": self._failed_tasks,
                }
            },
        )

    def get_worker_health(self) -> list[dict[str, Any]]:
        """Get health status for all workers."""
        return [worker.health_check() for worker in self._workers]

    def get_tasks_in_flight(self) -> int:
        """Get number of tasks currently being processed."""
        return sum(1 for w in self._workers if w.is_busy)

    def _find_idle_worker(self, agent_type: str) -> AgentWorker | None:
        """Find an idle worker for the given agent type."""
        workers = self._workers_by_type.get(agent_type, [])
        for worker in workers:
            if worker.is_idle:
                return worker
        return None

    def _enqueue_task(self, task: WorkerTask) -> None:
        """Enqueue a task to the message queue."""
        if self._message_queue is None:
            logger.warning(
                f"worker_pool:no_queue",
                extra={
                    "context": {
                        "task_id": task.id,
                        "reason": "message_queue_not_configured",
                    }
                },
            )
            return

        try:
            body = json.dumps(
                {
                    "task_id": task.id,
                    "agent_type": task.agent_type,
                    "payload": task.payload,
                    "priority": task.priority,
                    "timeout_seconds": task.timeout_seconds,
                    "max_retries": task.max_retries,
                }
            )
            priority = MessagePriority.NORMAL
            if task.priority == "high":
                priority = MessagePriority.HIGH
            elif task.priority == "low":
                priority = MessagePriority.LOW

            self._message_queue.enqueue(body=body, priority=priority)
        except Exception as e:
            logger.error(
                f"worker_pool:enqueue_error",
                extra={"context": {"task_id": task.id, "error": str(e)}},
            )

    def _dispatcher_loop(self) -> None:
        """Background loop that pulls tasks from the queue and dispatches to workers."""
        if self._message_queue is None:
            return

        consumer_id = f"pool-dispatcher-{uuid.uuid4().hex[:8]}"
        logger.info(
            f"worker_pool:dispatcher_started",
            extra={"context": {"consumer_id": consumer_id}},
        )

        while not self._stop_event.is_set():
            try:
                msg = self._message_queue.dequeue(consumer_id)
                if msg is None:
                    self._stop_event.wait(self._queue_poll_interval)
                    continue

                try:
                    body = json.loads(msg.body)
                    task = WorkerTask(
                        id=body.get("task_id", msg.id),
                        agent_type=body.get("agent_type", "unknown"),
                        payload=body.get("payload", {}),
                        priority=body.get("priority", "normal"),
                        timeout_seconds=body.get(
                            "timeout_seconds", self._default_timeout
                        ),
                        max_retries=body.get("max_retries", self._max_retries),
                    )

                    worker = self._find_idle_worker(task.agent_type)
                    if worker:
                        future = worker.execute(task)
                        with self._lock:
                            self._worker_futures[task.id] = future
                        future.add_done_callback(self._on_result)
                        self._message_queue.ack(msg.id)
                    else:
                        self._message_queue.nack(msg.id, requeue=True)
                        self._stop_event.wait(self._queue_poll_interval)

                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(
                        f"worker_pool:dispatcher_parse_error",
                        extra={"context": {"message_id": msg.id, "error": str(e)}},
                    )
                    self._message_queue.ack(msg.id)

            except Exception as e:
                logger.error(
                    f"worker_pool:dispatcher_error",
                    extra={"context": {"error": str(e)}},
                )
                self._stop_event.wait(self._queue_poll_interval)

        logger.info("worker_pool:dispatcher_stopped")

    def _on_result(self, future: Future[WorkerResult]) -> None:
        """Handle task result from a worker future."""
        try:
            result = future.result()
            with self._lock:
                task_id = result.task_id
                self._worker_futures.pop(task_id, None)

            if result.success:
                self._completed_tasks += 1
                self._emit_metric("pool_tasks_completed_total", 1)
            else:
                self._failed_tasks += 1
                self._emit_metric("pool_tasks_failed_total", 1)

            self._emit_metric("pool_task_duration_seconds", result.duration_seconds)

            for callback in self._result_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.error(
                        f"worker_pool:result_callback_error",
                        extra={"context": {"error": str(e)}},
                    )

        except Exception as e:
            logger.error(
                f"worker_pool:result_error",
                extra={"context": {"error": str(e)}},
            )
            self._failed_tasks += 1

    def _emit_metric(self, name: str, value: float) -> None:
        """Emit a metric to the metrics collector."""
        if self._metrics is None:
            return
        try:
            if "total" in name:
                self._metrics.counter_inc(name, value)
            elif "depth" in name:
                self._metrics.gauge_set(name, value)
            else:
                self._metrics.histogram_observe(name, value)
        except Exception:
            pass

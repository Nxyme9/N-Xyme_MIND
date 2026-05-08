import asyncio
import threading
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import deque


@dataclass
class ScheduledTask:
    task_id: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    scheduled_at: float = 0.0
    interval: Optional[float] = None


class BackgroundScheduler:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._task_queue: deque = deque()
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._queue_lock = threading.Lock()
        self._initialized = True
        self._last_trigger_time = 0
        self._min_interval_seconds = 60

    def schedule_once(
        self, task_id: str, func: Callable, delay_seconds: float = 0, *args, **kwargs
    ):
        with self._queue_lock:
            scheduled_at = time.time() + delay_seconds
            task = ScheduledTask(
                task_id=task_id,
                func=func,
                args=args,
                kwargs=kwargs,
                scheduled_at=scheduled_at,
            )
            self._task_queue.append(task)

    def schedule_interval(
        self, task_id: str, func: Callable, interval_seconds: float, *args, **kwargs
    ):
        with self._queue_lock:
            task = ScheduledTask(
                task_id=task_id,
                func=func,
                args=args,
                kwargs=kwargs,
                scheduled_at=time.time(),
                interval=interval_seconds,
            )
            self._task_queue.append(task)

    def cancel(self, task_id: str):
        with self._queue_lock:
            self._task_queue = deque(
                t for t in self._task_queue if t.task_id != task_id
            )

    def _worker(self):
        while not self._stop_event.is_set():
            now = time.time()
            task_to_run = None

            with self._queue_lock:
                while self._task_queue:
                    task = self._task_queue[0]
                    if task.scheduled_at <= now:
                        task_to_run = self._task_queue.popleft()
                        if task.interval:
                            task.scheduled_at = now + task.interval
                            self._task_queue.append(task)
                        break
                    else:
                        break

            if task_to_run:
                try:
                    result = task_to_run.func(*task_to_run.args, **task_to_run.kwargs)
                except Exception:
                    pass
            else:
                time.sleep(0.1)

    def start(self):
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(target=self._worker, daemon=True)
            self._worker_thread.start()

    def stop(self):
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=2)

    def can_trigger(self) -> bool:
        now = time.time()
        if now - self._last_trigger_time >= self._min_interval_seconds:
            self._last_trigger_time = now
            return True
        return False


_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        _scheduler.start()
    return _scheduler


def schedule_training_check(delay_seconds: float = 0):

    scheduler = get_scheduler()
    scheduler.schedule_once(
        task_id="training_check",
        func=_run_training_check,
        delay_seconds=delay_seconds,
    )


def _run_training_check() -> Dict[str, Any]:
    from packages.training.training_trigger import check_and_trigger_training

    scheduler = get_scheduler()
    if not scheduler.can_trigger():
        return {"status": "skipped", "reason": "throttled"}
    return check_and_trigger_training()

"""Queue Service — In-memory task queue"""

import logging, time, uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class QueueItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_type: str = ""
    payload: Any = None
    created_at: float = field(default_factory=time.time)
    attempts: int = 0
    max_retries: int = 3


class QueueService:
    def __init__(self):
        self._queue: deque = deque()
        self._handlers: Dict[str, Callable] = {}
        self._processed: list = []

    def enqueue(self, task_type: str, payload: Any, max_retries: int = 3) -> str:
        item = QueueItem(task_type=task_type, payload=payload, max_retries=max_retries)
        self._queue.append(item)
        logger.info(f"QueueService: Enqueued {task_type} ({item.id})")
        return item.id

    def register_handler(self, task_type: str, handler: Callable):
        self._handlers[task_type] = handler

    def process_next(self) -> bool:
        if not self._queue:
            return False
        item = self._queue.popleft()
        handler = self._handlers.get(item.task_type)
        if not handler:
            logger.error(f"QueueService: No handler for {item.task_type}")
            return False
        try:
            handler(item.payload)
            self._processed.append(item)
            return True
        except Exception as e:
            item.attempts += 1
            if item.attempts < item.max_retries:
                self._queue.append(item)
            logger.error(f"QueueService: Failed {item.id}: {e}")
            return False

    def get_stats(self) -> Dict:
        return {"pending": len(self._queue), "processed": len(self._processed)}

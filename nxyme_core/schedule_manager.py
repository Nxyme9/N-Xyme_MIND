import logging
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ScheduledJob:
    id: str
    name: str
    cron_expr: str
    command: str
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None


class SchedulerManager:
    def __init__(self):
        self._jobs: Dict[str, ScheduledJob] = {}

    def create_cron(self, name: str, cron_expr: str, command: str) -> str:
        job_id = f"cron_{uuid.uuid4().hex[:8]}"
        job = ScheduledJob(id=job_id, name=name, cron_expr=cron_expr, command=command)
        self._jobs[job_id] = job
        logger.info(f"Created cron job {job_id}: {name} ({cron_expr})")
        return job_id

    def delete_cron(self, job_id: str) -> bool:
        if job_id in self._jobs:
            del self._jobs[job_id]
            logger.info(f"Deleted cron job {job_id}")
            return True
        return False

    def list_crons(self) -> List[Dict[str, Any]]:
        return [{"id": j.id, "name": j.name, "cron": j.cron_expr, "enabled": j.enabled} for j in self._jobs.values()]


_scheduler: Optional[SchedulerManager] = None


def get_scheduler() -> SchedulerManager:
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerManager()
    return _scheduler
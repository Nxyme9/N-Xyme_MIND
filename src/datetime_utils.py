"""Datetime Utilities — Timezone-aware datetime helpers"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class DateTimeUtils:
    @staticmethod
    def now_utc() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def now_local() -> datetime:
        return datetime.now()

    @staticmethod
    def to_iso(dt: datetime) -> str:
        return dt.isoformat()

    @staticmethod
    def from_iso(iso: str) -> datetime:
        return datetime.fromisoformat(iso)

    @staticmethod
    def format_duration(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.1f}s"
        if seconds < 3600:
            return f"{seconds / 60:.1f}m"
        return f"{seconds / 3600:.1f}h"

    @staticmethod
    def time_ago(dt: datetime) -> str:
        diff = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
        return DateTimeUtils.format_duration(diff.total_seconds()) + " ago"

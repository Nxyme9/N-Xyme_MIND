"""Notification Service — Console + file notifications"""

import json, logging, time
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, log_file: str = "data/notifications.json"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self._notifications: List[Dict] = []

    def notify(self, title: str, message: str, level: str = "info"):
        notification = {
            "title": title,
            "message": message,
            "level": level,
            "timestamp": time.time(),
        }
        self._notifications.append(notification)
        try:
            data = []
            if self.log_file.exists():
                data = json.loads(self.log_file.read_text(encoding="utf-8"))
            data.append(notification)
            self.log_file.write_text(json.dumps(data[-100:], indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"NotificationService: Save failed: {e}")
        logger.info(f"[{level.upper()}] {title}: {message}")

    def get_recent(self, limit: int = 20) -> List[Dict]:
        return self._notifications[-limit:]

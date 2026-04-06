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


class WebhookNotifier:
    """Send notifications via webhook (Slack, Discord, etc.)."""

    def __init__(self, webhook_url: str | None = None, channel: str = "generic"):
        import os
        self.webhook_url = webhook_url or os.getenv("ALERT_WEBHOOK_URL")
        self.channel = channel or os.getenv("ALERT_CHANNEL", "generic")

    def send(self, title: str, message: str, level: str = "info") -> bool:
        """Send notification via webhook."""
        if not self.webhook_url:
            logger.debug("Webhook URL not configured, skipping")
            return False

        payload = self._format_payload(title, message, level)
        try:
            import urllib.request
            import urllib.error

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")
            return False

    def _format_payload(self, title: str, message: str, level: str) -> dict:
        """Format payload for the webhook channel."""
        color_map = {
            "info": "#36a64f",
            "warning": "#ff9500",
            "error": "#ff0000",
            "critical": "#cc0000",
        }

        if self.channel == "slack":
            return {
                "attachments": [{
                    "color": color_map.get(level, "#36a64f"),
                    "title": title,
                    "text": message,
                    "ts": str(int(time.time())),
                }]
            }
        elif self.channel == "discord":
            return {
                "embeds": [{
                    "title": title,
                    "description": message,
                    "color": int(color_map.get(level, "#36a64f")[1:], 16),
                }]
            }
        # Generic JSON payload
        return {
            "title": title,
            "message": message,
            "level": level,
            "timestamp": time.time(),
            "channel": self.channel,
        }


# Global notification service
_notification_service = NotificationService()
_webhook_notifier = WebhookNotifier()


def notify(title: str, message: str, level: str = "info", webhook: bool = False):
    """Send notification via all configured channels."""
    _notification_service.notify(title, message, level)
    if webhook:
        _webhook_notifier.send(title, message, level)


def notify_critical(title: str, message: str, webhook: bool = True):
    """Send critical notification (always via webhook)."""
    notify(title, message, level="critical", webhook=webhook)


def notify_alert(title: str, message: str, webhook: bool = True):
    """Send alert notification (always via webhook)."""
    notify(title, message, level="warning", webhook=webhook)



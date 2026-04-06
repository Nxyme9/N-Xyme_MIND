"""
Webhook Dead Letter Queue — Store failed webhook deliveries for retry.

Usage:
    dlq = WebhookDLQ()
    dlq.store_failure("http://example.com/hook", {"event": "test"}, error="timeout")
    failed = dlq.get_failed()
    dlq.retry("http://example.com/hook")
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class FailedWebhook:
    """A failed webhook delivery."""

    id: str
    url: str
    payload: Dict[str, Any]
    error: str
    attempts: int = 1
    created_at: float = field(default_factory=time.time)
    last_attempt: float = field(default_factory=time.time)


class WebhookDLQ:
    """Dead Letter Queue for failed webhooks."""

    def __init__(self, storage_file: str = "data/webhook_dlq.json"):
        self.storage_file = Path(storage_file)
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self._failed: Dict[str, FailedWebhook] = {}
        self._load()
        logger.info(f"WebhookDLQ: Initialized ({len(self._failed)} pending)")

    def _load(self):
        """Load from file."""
        if self.storage_file.exists():
            try:
                data = json.loads(self.storage_file.read_text(encoding="utf-8"))
                for item in data:
                    webhook = FailedWebhook(**item)
                    self._failed[webhook.id] = webhook
            except Exception as e:
                logger.error(f"WebhookDLQ: Load failed: {e}")

    def _save(self):
        """Save to file."""
        try:
            data = [
                {
                    "id": w.id,
                    "url": w.url,
                    "payload": w.payload,
                    "error": w.error,
                    "attempts": w.attempts,
                    "created_at": w.created_at,
                    "last_attempt": w.last_attempt,
                }
                for w in self._failed.values()
            ]
            self.storage_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"WebhookDLQ: Save failed: {e}")

    def store_failure(
        self,
        url: str,
        payload: Dict[str, Any],
        error: str,
        webhook_id: Optional[str] = None,
    ) -> str:
        """Store a failed webhook delivery."""
        import uuid

        webhook_id = webhook_id or str(uuid.uuid4())[:8]

        webhook = FailedWebhook(
            id=webhook_id,
            url=url,
            payload=payload,
            error=error,
        )
        self._failed[webhook_id] = webhook
        self._save()

        logger.warning(f"WebhookDLQ: Stored failed webhook {webhook_id} to {url}")
        return webhook_id

    def get_failed(self, url: Optional[str] = None) -> List[FailedWebhook]:
        """Get failed webhooks, optionally filtered by URL."""
        if url:
            return [w for w in self._failed.values() if w.url == url]
        return list(self._failed.values())

    def retry(self, webhook_id: str) -> bool:
        """Retry a failed webhook."""
        webhook = self._failed.get(webhook_id)
        if not webhook:
            logger.error(f"WebhookDLQ: Webhook {webhook_id} not found")
            return False

        try:
            client = httpx.Client(timeout=30.0)
            resp = client.post(webhook.url, json=webhook.payload)
            resp.raise_for_status()

            # Success - remove from DLQ
            del self._failed[webhook_id]
            self._save()
            logger.info(f"WebhookDLQ: Retry succeeded for {webhook_id}")
            return True
        except Exception as e:
            webhook.attempts += 1
            webhook.last_attempt = time.time()
            webhook.error = str(e)
            self._save()
            logger.warning(f"WebhookDLQ: Retry failed for {webhook_id}: {e}")
            return False

    def retry_all(self) -> Dict[str, bool]:
        """Retry all failed webhooks."""
        results = {}
        for webhook_id in list(self._failed.keys()):
            results[webhook_id] = self.retry(webhook_id)
        return results

    def clear(self):
        """Clear all failed webhooks."""
        self._failed.clear()
        self._save()

    def get_stats(self) -> Dict[str, Any]:
        """Get DLQ statistics."""
        total = len(self._failed)
        by_url = {}
        for w in self._failed.values():
            by_url[w.url] = by_url.get(w.url, 0) + 1

        return {
            "total_failed": total,
            "by_url": by_url,
            "max_attempts": max((w.attempts for w in self._failed.values()), default=0),
        }

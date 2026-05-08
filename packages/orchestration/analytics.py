"""
Analytics — Event logging and telemetry system.

Ported from: services/analytics/index.ts (Claude Code)
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class EventPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AnalyticsEvent:
    """Analytics event."""
    name: str
    timestamp: float = field(default_factory=time.time)
    priority: EventPriority = EventPriority.MEDIUM
    metadata: dict = field(default_factory=dict)
    session_id: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class AnalyticsConfig:
    """Analytics configuration."""
    enabled: bool = True
    batch_size: int = 10
    flush_interval: float = 60.0
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    sample_rate: float = 1.0


class AnalyticsSink:
    """Analytics sink interface."""

    def send(self, event: AnalyticsEvent) -> bool:
        raise NotImplementedError

    def flush(self) -> None:
        pass


class ConsoleSink(AnalyticsSink):
    """Console analytics sink for debugging."""

    def send(self, event: AnalyticsEvent) -> bool:
        print(f"[ANALYTICS] {event.name}: {json.dumps(event.metadata)}")
        return True


class FileSink(AnalyticsSink):
    """File-based analytics sink."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()

    def send(self, event: AnalyticsEvent) -> bool:
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.path, "a") as f:
                    f.write(json.dumps({
                        "name": event.name,
                        "timestamp": event.timestamp,
                        "metadata": event.metadata,
                        "session_id": event.session_id,
                        "user_id": event.user_id,
                    }) + "\n")
                return True
            except Exception as e:
                logger.error(f"FileSink error: {e}")
                return False


class HTTPSink(AnalyticsSink):
    """HTTP analytics sink for remote endpoints."""

    def __init__(self, endpoint: str, api_key: str, batch_size: int = 10):
        self.endpoint = endpoint
        self.api_key = api_key
        self.batch_size = batch_size
        self._buffer: deque = deque(maxlen=batch_size)
        self._lock = threading.Lock()

    def send(self, event: AnalyticsEvent) -> bool:
        with self._lock:
            self._buffer.append(event)
            if len(self._buffer) >= self.batch_size:
                return self._flush_batch()
        return True

    def flush(self) -> None:
        with self._lock:
            if self._buffer:
                self._flush_batch()

    def _flush_batch(self) -> bool:
        """Flush buffered events to remote endpoint."""
        if not self._buffer:
            return True

        events = list(self._buffer)
        self._buffer.clear()

        try:
            import urllib.request
            data = json.dumps({
                "events": [
                    {
                        "name": e.name,
                        "timestamp": e.timestamp,
                        "metadata": e.metadata,
                    }
                    for e in events
                ]
            }).encode()

            request = urllib.request.Request(
                self.endpoint,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            urllib.request.urlopen(request, timeout=5)
            return True
        except Exception as e:
            logger.error(f"HTTPSink error: {e}")
            return False


class AnalyticsService:
    """Analytics service with event queueing and sink routing."""

    def __init__(self, config: Optional[AnalyticsConfig] = None):
        self.config = config or AnalyticsConfig()
        self._sinks: list[AnalyticsSink] = []
        self._queue: deque = deque(maxlen=1000)
        self._running = False
        self._lock = threading.Lock()
        self._flush_thread: Optional[threading.Thread] = None

    def add_sink(self, sink: AnalyticsSink) -> None:
        """Add an analytics sink."""
        self._sinks.append(sink)

    def start(self) -> None:
        """Start analytics service."""
        if self._running:
            return

        self._running = True

        if self.config.flush_interval > 0:
            self._flush_thread = threading.Thread(
                target=self._periodic_flush,
                daemon=True,
            )
            self._flush_thread.start()

        logger.info("Analytics service started")

    def stop(self) -> None:
        """Stop analytics service and flush remaining events."""
        self._running = False

        for sink in self._sinks:
            sink.flush()

        if self._flush_thread:
            self._flush_thread.join(timeout=5)

        logger.info("Analytics service stopped")

    def _periodic_flush(self) -> None:
        """Periodic flush based on config interval."""
        while self._running:
            time.sleep(self.config.flush_interval)
            with self._lock:
                for event in self._queue:
                    for sink in self._sinks:
                        try:
                            sink.send(event)
                        except Exception as e:
                            logger.error(f"Sink error: {e}")
                self._queue.clear()

    def log_event(
        self,
        name: str,
        metadata: Optional[dict] = None,
        priority: EventPriority = EventPriority.MEDIUM,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """Log an analytics event."""
        if not self.config.enabled:
            return

        import random
        if random.random() > self.config.sample_rate:
            return

        event = AnalyticsEvent(
            name=name,
            priority=priority,
            metadata=metadata or {},
            session_id=session_id,
            user_id=user_id,
        )

        with self._lock:
            self._queue.append(event)

            if len(self._queue) >= self.config.batch_size:
                self._flush_immediate()

    def _flush_immediate(self) -> None:
        """Flush events immediately."""
        events = list(self._queue)
        self._queue.clear()

        for event in events:
            for sink in self._sinks:
                try:
                    sink.send(event)
                except Exception as e:
                    logger.error(f"Sink error: {e}")


def strip_proto_fields(metadata: dict) -> dict:
    """Strip _PROTO_* prefixed fields from metadata."""
    return {k: v for k, v in metadata.items() if not k.startswith("_PROTO_")}


_analytics_service: Optional[AnalyticsService] = None
_analytics_config: Optional[AnalyticsConfig] = None


def init_analytics(
    config: Optional[AnalyticsConfig] = None,
    enable_console: bool = True,
    enable_file: bool = False,
    file_path: Optional[Path] = None,
) -> AnalyticsService:
    """Initialize analytics service."""
    global _analytics_service, _analytics_config

    _analytics_config = config or AnalyticsConfig()
    _analytics_service = AnalyticsService(_analytics_config)

    if enable_console:
        _analytics_service.add_sink(ConsoleSink())

    if enable_file and file_path:
        _analytics_service.add_sink(FileSink(file_path))

    _analytics_service.start()
    return _analytics_service


def get_analytics() -> Optional[AnalyticsService]:
    """Get analytics service instance."""
    return _analytics_service


def log_event(
    name: str,
    metadata: Optional[dict] = None,
    priority: EventPriority = EventPriority.MEDIUM,
) -> None:
    """Log event (convenience function)."""
    if _analytics_service:
        _analytics_service.log_event(name, metadata, priority)


__all__ = [
    "EventPriority",
    "AnalyticsEvent",
    "AnalyticsConfig",
    "AnalyticsSink",
    "ConsoleSink",
    "FileSink",
    "HTTPSink",
    "AnalyticsService",
    "strip_proto_fields",
    "init_analytics",
    "get_analytics",
    "log_event",
]

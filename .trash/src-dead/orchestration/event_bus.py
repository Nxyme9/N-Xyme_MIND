"""
Event Bus — Inter-module pub/sub messaging (ported from SPINE)

Usage:
    bus = EventBus()
    bus.subscribe("service.health", on_health)
    bus.publish("service.health", {"status": "ok"})
"""

import logging
import time
from collections import deque
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class EventBus:
    """Simple in-memory event bus for inter-module communication."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._history: deque = deque(maxlen=1000)
        logger.info("EventBus: Initialized")

    def subscribe(self, event: str, callback: Callable) -> None:
        """Subscribe to an event."""
        if event not in self._subscribers:
            self._subscribers[event] = []
        self._subscribers[event].append(callback)
        logger.debug(f"EventBus: Subscribed to '{event}'")

    def unsubscribe(self, event: str, callback: Callable) -> None:
        """Unsubscribe from an event."""
        if event in self._subscribers:
            self._subscribers[event] = [cb for cb in self._subscribers[event] if cb != callback]

    def publish(self, event: str, data: Any = None) -> int:
        """Publish an event to all subscribers."""
        count = 0
        event_record = {
            "event": event,
            "data": data,
            "timestamp": time.time(),
        }
        self._history.append(event_record)

        # deque handles eviction automatically with maxlen

        # Notify subscribers
        for callback in self._subscribers.get(event, []):
            try:
                callback(data)
                count += 1
            except Exception as e:
                logger.error(f"EventBus: Handler error for '{event}': {e}")

        # Also notify wildcard subscribers
        for callback in self._subscribers.get("*", []):
            try:
                callback({"event": event, "data": data})
                count += 1
            except Exception as e:
                logger.error(f"EventBus: Wildcard handler error: {e}")

        logger.debug(f"EventBus: Published '{event}' to {count} subscribers")
        return count

    def get_history(self, event: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get event history."""
        if event:
            return [e for e in self._history if e["event"] == event][-limit:]
        return self._history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            "total_events": len(self._history),
            "subscribers": {k: len(v) for k, v in self._subscribers.items()},
            "active_events": len(self._subscribers),
        }


# Global event bus
_global_bus = EventBus()


def get_event_bus() -> EventBus:
    """Get global event bus."""
    return _global_bus

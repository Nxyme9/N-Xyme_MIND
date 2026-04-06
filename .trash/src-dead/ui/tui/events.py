"""Event bus implementation for TUI dashboard.

Provides a publish/subscribe pattern for decoupled communication
between dashboard components.
"""

from typing import Any, Callable, Dict, List


class EventBus:
    """Event bus for publish/subscribe pattern.

    Allows components to subscribe to specific event types and
    receive notifications when those events are published.
    """

    def __init__(self) -> None:
        """Initialize the event bus with an empty subscriber dictionary."""
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Register a callback for a specific event type.

        Args:
            event_type: The type of event to subscribe to.
            callback: The callable to invoke when the event is published.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)

    def publish(self, event_type: str, data: Any) -> None:
        """Publish an event to all registered callbacks.

        Args:
            event_type: The type of event being published.
            data: The data to pass to the callback functions.
        """
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                callback(data)

    def unsubscribe(self, event_type: str, callback: Callable) -> bool:
        """Remove a callback from an event type.

        Args:
            event_type: The type of event to unsubscribe from.
            callback: The callback to remove.

        Returns:
            True if the callback was found and removed, False otherwise.
        """
        if event_type not in self._subscribers:
            return False

        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

            # Clean up empty event type entries
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]

            return True
        return False

    def clear(self) -> None:
        """Remove all subscribers from the event bus."""
        self._subscribers.clear()

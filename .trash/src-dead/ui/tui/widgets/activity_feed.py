#!/usr/bin/env python3
"""
ActivityFeed - Real-time activity stream widget

T4.4 from dashboard-v2-plan.md:
- Display live activity stream
- Show delegation events
- Track agent task execution in real-time
"""

from typing import Optional
from datetime import datetime
from textual.reactive import reactive
from textual.widget import Widget


class ActivityFeed(Widget):
    """ASCII real-time activity feed."""

    # Reactive data
    events = reactive([])
    max_events = reactive(50)

    def __init__(self, max_events: int = 50, **kwargs):
        super().__init__(**kwargs)
        self.max_events = max_events

    def add_event(self, event: dict) -> None:
        """Add a new event to the feed.

        Args:
            event: Dict with 'type', 'agent', 'message', 'timestamp'
        """
        # Add timestamp if not present
        if "timestamp" not in event:
            event["timestamp"] = datetime.now().isoformat()

        # Prepend to events (newest first)
        self.events = [event] + self.events[: self.max_events - 1]
        self.refresh()

    def add_events(self, events: list) -> None:
        """Add multiple events."""
        for event in events:
            self.add_event(event)

    def clear(self) -> None:
        """Clear all events."""
        self.events = []
        self.refresh()

    def render(self) -> str:
        """Render ASCII activity feed."""
        if not self.events:
            return "[dim]No activity[/]"

        lines = ["LIVE ACTIVITY", "═" * 40, ""]

        # Show last N events
        for i, event in enumerate(self.events[:20]):
            timestamp = event.get("timestamp", "")[:8]  # HH:MM:SS
            event_type = event.get("type", "info")
            agent = event.get("agent", "")
            message = event.get("message", "")

            # Icon based on type
            icons = {
                "delegation": "→",
                "start": "▶",
                "complete": "✓",
                "error": "✗",
                "warning": "⚠",
                "info": "•",
            }
            icon = icons.get(event_type, "•")

            # Format line
            if agent:
                lines.append(f"{timestamp} {icon} [{agent}] {message}")
            else:
                lines.append(f"{timestamp} {icon} {message}")

        # Summary
        total = len(self.events)
        lines.extend(["", f"Events: {total} (showing last 20)"])

        return "\n".join(lines)


class LiveEventCounter(Widget):
    """Simple live event counter display."""

    total_events = reactive(0)
    active_agents = reactive(0)
    last_event_time = reactive("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_counts(self, total: int, agents: int, last_time: str) -> None:
        """Set counter values."""
        self.total_events = total
        self.active_agents = agents
        self.last_event_time = last_time
        self.refresh()

    def render(self) -> str:
        """Render counter."""
        return f"""LIVE METRICS
════════════

Events Today: {self.total_events}
Active Agents: {self.active_agents}
Last Event: {self.last_event_time}"""


class EventStream(Widget):
    """Continuous event stream display (simulated real-time)."""

    events = reactive([])
    is_streaming = reactive(False)
    _simulated_events = [
        {
            "type": "delegation",
            "agent": "Sisyphus",
            "message": "Delegating to Hephaestus",
        },
        {"type": "start", "agent": "Hephaestus", "message": "Implementing feature X"},
        {"type": "complete", "agent": "Hephaestus", "message": "Feature X completed"},
        {"type": "delegation", "agent": "Sisyphus", "message": "Delegating to Oracle"},
        {"type": "info", "agent": "System", "message": "Memory stats refreshed"},
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def start_stream(self) -> None:
        """Start simulated event stream."""
        self.is_streaming = True

    def stop_stream(self) -> None:
        """Stop simulated event stream."""
        self.is_streaming = False

    def render(self) -> str:
        """Render event stream."""
        if not self.is_streaming:
            return "[dim]Stream paused (press S to start)[/]"

        if not self.events:
            return "[dim]Waiting for events...[/]"

        lines = ["EVENT STREAM", "═" * 40, ""]

        # Show events with typewriter effect simulation
        for event in self.events[:15]:
            timestamp = event.get("timestamp", "")[:8]
            event_type = event.get("type", "info")
            agent = event.get("agent", "")
            message = event.get("message", "")

            type_icons = {
                "delegation": "→",
                "start": "▶",
                "complete": "✓",
                "error": "✗",
                "info": "•",
            }
            icon = type_icons.get(event_type, "•")

            lines.append(f"{timestamp} {icon} [{agent}] {message}")

        return "\n".join(lines)

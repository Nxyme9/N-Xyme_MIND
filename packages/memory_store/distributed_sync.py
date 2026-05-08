"""Distributed Memory Sync — Cross-instance memory synchronization.

Implements:
- Event-sourced sync with conflict resolution
- Vector clock-based consistency
- Offline-first with sync on reconnect
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VectorClock:
    """Vector clock for distributed consistency."""

    clocks: dict[str, int] = field(default_factory=dict)

    def increment(self, node_id: str) -> None:
        self.clocks[node_id] = self.clocks.get(node_id, 0) + 1

    def merge(self, other: "VectorClock") -> None:
        for node_id, clock in other.clocks.items():
            self.clocks[node_id] = max(self.clocks.get(node_id, 0), clock)

    def happens_before(self, other: "VectorClock") -> bool:
        for node_id, clock in self.clocks.items():
            if clock > other.clocks.get(node_id, 0):
                return False
        return any(
            self.clocks.get(node_id, 0) < other.clocks.get(node_id, 0)
            for node_id in other.clocks
        )

    def to_dict(self) -> dict[str, int]:
        return dict(self.clocks)

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> "VectorClock":
        return cls(clocks=dict(data))


@dataclass
class SyncEvent:
    """A synchronization event."""

    id: str
    node_id: str
    event_type: str  # create, update, delete
    memory_id: str
    content: str = ""
    vector_clock: VectorClock = field(default_factory=VectorClock)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class DistributedMemorySync:
    """Distributed memory synchronization engine."""

    def __init__(self, node_id: str, storage_path: Path | None = None):
        """Initialize distributed sync.

        Args:
            node_id: Unique identifier for this node.
            storage_path: Path to store sync data.
        """
        self.node_id = node_id
        self.storage_path = storage_path or Path(".sisyphus/distributed_sync")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.vector_clock = VectorClock()
        self.event_log: list[SyncEvent] = []
        self._load_state()

    def create_memory(self, memory_id: str, content: str) -> SyncEvent:
        """Create a memory and log the event.

        Args:
            memory_id: Memory identifier.
            content: Memory content.

        Returns:
            Created SyncEvent.
        """
        import uuid

        self.vector_clock.increment(self.node_id)

        event = SyncEvent(
            id=str(uuid.uuid4())[:8],
            node_id=self.node_id,
            event_type="create",
            memory_id=memory_id,
            content=content,
            vector_clock=VectorClock.from_dict(self.vector_clock.to_dict()),
        )
        self.event_log.append(event)
        self._save_state()
        return event

    def update_memory(self, memory_id: str, content: str) -> SyncEvent:
        """Update a memory and log the event."""
        import uuid

        self.vector_clock.increment(self.node_id)

        event = SyncEvent(
            id=str(uuid.uuid4())[:8],
            node_id=self.node_id,
            event_type="update",
            memory_id=memory_id,
            content=content,
            vector_clock=VectorClock.from_dict(self.vector_clock.to_dict()),
        )
        self.event_log.append(event)
        self._save_state()
        return event

    def delete_memory(self, memory_id: str) -> SyncEvent:
        """Delete a memory and log the event."""
        import uuid

        self.vector_clock.increment(self.node_id)

        event = SyncEvent(
            id=str(uuid.uuid4())[:8],
            node_id=self.node_id,
            event_type="delete",
            memory_id=memory_id,
            vector_clock=VectorClock.from_dict(self.vector_clock.to_dict()),
        )
        self.event_log.append(event)
        self._save_state()
        return event

    def receive_events(self, events: list[SyncEvent]) -> list[SyncEvent]:
        """Receive events from another node and resolve conflicts.

        Args:
            events: List of events from another node.

        Returns:
            List of events that need to be applied.
        """
        applied = []

        for event in events:
            # Merge vector clocks
            self.vector_clock.merge(event.vector_clock)

            # Check for conflicts (same memory_id, concurrent updates)
            conflicting = [
                e
                for e in self.event_log
                if e.memory_id == event.memory_id
                and e.node_id != event.node_id
                and not e.vector_clock.happens_before(event.vector_clock)
                and not event.vector_clock.happens_before(e.vector_clock)
            ]

            if conflicting:
                # Resolve conflict: last-write-wins with node_id tiebreaker
                latest = max(conflicting, key=lambda e: e.timestamp)
                if event.timestamp > latest.timestamp or (
                    event.timestamp == latest.timestamp
                    and event.node_id > latest.node_id
                ):
                    applied.append(event)
            else:
                applied.append(event)

            self.event_log.append(event)

        self._save_state()
        return applied

    def get_events_since(self, vector_clock: VectorClock) -> list[SyncEvent]:
        """Get events that happened after a given vector clock.

        Args:
            vector_clock: Vector clock to compare against.

        Returns:
            List of events that happened after.
        """
        return [
            event
            for event in self.event_log
            if not event.vector_clock.happens_before(vector_clock)
        ]

    def _save_state(self) -> None:
        """Save sync state to storage."""
        state = {
            "node_id": self.node_id,
            "vector_clock": self.vector_clock.to_dict(),
            "event_log": [
                {
                    "id": e.id,
                    "node_id": e.node_id,
                    "event_type": e.event_type,
                    "memory_id": e.memory_id,
                    "content": e.content,
                    "vector_clock": e.vector_clock.to_dict(),
                    "timestamp": e.timestamp,
                }
                for e in self.event_log
            ],
        }
        (self.storage_path / f"{self.node_id}_state.json").write_text(
            json.dumps(state, indent=2)
        )

    def _load_state(self) -> None:
        """Load sync state from storage."""
        state_file = self.storage_path / f"{self.node_id}_state.json"
        if not state_file.exists():
            return

        try:
            state = json.loads(state_file.read_text())
            self.vector_clock = VectorClock.from_dict(state.get("vector_clock", {}))
            self.event_log = [
                SyncEvent(
                    id=e["id"],
                    node_id=e["node_id"],
                    event_type=e["event_type"],
                    memory_id=e["memory_id"],
                    content=e.get("content", ""),
                    vector_clock=VectorClock.from_dict(e.get("vector_clock", {})),
                    timestamp=e.get("timestamp", ""),
                )
                for e in state.get("event_log", [])
            ]
        except Exception as e:
            logger.warning(f"Failed to load sync state: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get sync statistics."""
        by_type: dict[str, int] = {}
        for event in self.event_log:
            by_type[event.event_type] = by_type.get(event.event_type, 0) + 1

        return {
            "node_id": self.node_id,
            "total_events": len(self.event_log),
            "by_type": by_type,
            "vector_clock": self.vector_clock.to_dict(),
        }


# Global singleton
_sync = DistributedMemorySync(node_id="default")


def create_memory(memory_id: str, content: str) -> SyncEvent:
    """Convenience function to create memory."""
    return _sync.create_memory(memory_id, content)


def receive_events(events: list[SyncEvent]) -> list[SyncEvent]:
    """Convenience function to receive events."""
    return _sync.receive_events(events)

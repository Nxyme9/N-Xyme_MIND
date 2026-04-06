"""
Healer Bridge — File-based IPC between PowerShell healer.ps1 and Python trigger_router.py

Reads healing events from .heartbeat/bridge-events.jsonl and routes them through TriggerRouter.
This enables the PowerShell healer to communicate with the Python nervous system.

Usage:
    from healer_bridge import HealerBridge
    bridge = HealerBridge()
    bridge.process_events()  # Call in main loop
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Constants
BRIDGE_EVENTS_FILE = ".heartbeat/bridge-events.jsonl"
PROCESSED_EVENTS_FILE = ".heartbeat/bridge-events.processed"
MAX_RETRY_ATTEMPTS = 3
PROCESSED_EVENTS_RETENTION = 1000


class HealerBridge:
    """
    File-based IPC bridge between PowerShell healer and Python trigger system.

    Event Format:
        {
            "source": "powershell",
            "type": "database_locked",
            "severity": "critical",
            "timestamp": "2026-03-25T10:00:00Z",
            "data": {"lock_duration": 15, "path": "data/sessions.db"},
            "idempotency_key": "unique-event-id"  # Optional, for deduplication
        }
    """

    def __init__(self, events_file: Optional[str] = None, router=None):
        self.events_file = Path(events_file) if events_file else Path(BRIDGE_EVENTS_FILE)
        self.processed_file = Path(PROCESSED_EVENTS_FILE)
        self.router = router
        self._processed_ids: Set[str] = set()
        self._last_mtime: float = 0

        # Ensure directory exists
        self.events_file.parent.mkdir(parents=True, exist_ok=True)

        # Load previously processed event IDs
        self._load_processed_ids()

        logger.info(f"HealerBridge: Initialized with events file: {self.events_file}")

    def set_router(self, router) -> None:
        """Set the TriggerRouter instance for event routing."""
        self.router = router

    def _load_processed_ids(self) -> None:
        """Load previously processed event IDs for idempotency."""
        if self.processed_file.exists():
            try:
                with open(self.processed_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self._processed_ids.add(line)
                logger.info(f"HealerBridge: Loaded {len(self._processed_ids)} processed event IDs")
            except Exception as e:
                logger.warning(f"HealerBridge: Failed to load processed IDs: {e}")

    def _save_processed_id(self, event_id: str) -> None:
        """Save processed event ID for idempotency check."""
        self._processed_ids.add(event_id)
        try:
            with open(self.processed_file, "a", encoding="utf-8") as f:
                f.write(f"{event_id}\n")
        except Exception as e:
            logger.warning(f"HealerBridge: Failed to save processed ID: {e}")

        # Trim if too many
        if len(self._processed_ids) > PROCESSED_EVENTS_RETENTION:
            self._processed_ids = set(list(self._processed_ids)[-PROCESSED_EVENTS_RETENTION:])
            try:
                with open(self.processed_file, "w", encoding="utf-8") as f:
                    for pid in self._processed_ids:
                        f.write(f"{pid}\n")
            except Exception as e:
                logger.warning(f"HealerBridge: Failed to trim processed IDs: {e}")

    def _get_event_id(self, event: Dict[str, Any]) -> str:
        """Generate or extract idempotency key for an event."""
        # Use provided idempotency_key or generate from event content
        if "idempotency_key" in event:
            return event["idempotency_key"]

        # Generate deterministic ID from event content
        key_parts = [
            event.get("source", ""),
            event.get("type", ""),
            event.get("timestamp", ""),
        ]
        return "|".join(key_parts)

    def _read_events(self, force: bool = False) -> List[Dict[str, Any]]:
        """Read pending events from the events file."""
        if not self.events_file.exists():
            return []

        # Check if file has changed (skip check if forced)
        if not force:
            try:
                mtime = self.events_file.stat().st_mtime
                if mtime == self._last_mtime:
                    return []
                self._last_mtime = mtime
            except OSError:
                return []

        events = []
        try:
            with open(self.events_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        events.append(event)
                    except json.JSONDecodeError as e:
                        logger.warning(f"HealerBridge: Invalid JSON in events file: {e}")
        except Exception as e:
            logger.error(f"HealerBridge: Failed to read events file: {e}")

        return events

    def _clear_events_file(self) -> None:
        """Clear the events file after processing."""
        try:
            # Write empty content to clear the file
            with open(self.events_file, "w", encoding="utf-8") as f:
                pass
            self._last_mtime = self.events_file.stat().st_mtime
            logger.debug("HealerBridge: Cleared events file")
        except Exception as e:
            logger.warning(f"HealerBridge: Failed to clear events file: {e}")

    def _route_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Route a single event through TriggerRouter."""
        if not self.router:
            logger.warning("HealerBridge: No router configured, logging event only")
            return {"event": event, "success": False, "message": "No router configured"}

        try:
            result = self.router.process_event(event)
            if result:
                logger.info(
                    f"HealerBridge: Routed event {event.get('type')} -> "
                    f"{result.get('action')} ({'success' if result.get('success') else 'failed'})"
                )
            else:
                logger.debug(f"HealerBridge: No trigger matched for event {event.get('type')}")
            return result
        except Exception as e:
            logger.error(f"HealerBridge: Failed to route event: {e}")
            return {"event": event, "success": False, "message": str(e)}

    def process_events(self) -> Dict[str, Any]:
        """
        Process all pending events from the events file.

        Returns:
            Dict with 'processed', 'skipped', 'routed', 'failed' counts
        """
        stats = {"processed": 0, "skipped": 0, "routed": 0, "failed": 0, "events": []}

        events = self._read_events(force=True)

        if not events:
            return stats

        logger.info(f"HealerBridge: Processing {len(events)} events")

        for event in events:
            # Check idempotency
            event_id = self._get_event_id(event)

            if event_id in self._processed_ids:
                logger.debug(f"HealerBridge: Skipping duplicate event: {event_id}")
                stats["skipped"] += 1
                continue

            # Route the event
            result = self._route_event(event)

            if result:
                stats["routed"] += 1
                if result.get("success"):
                    stats["processed"] += 1
                else:
                    stats["failed"] += 1
            else:
                # No router match - still mark as processed to avoid reprocessing
                stats["processed"] += 1

            stats["events"].append({"event": event, "result": result})

            # Mark as processed
            self._save_processed_id(event_id)

        # Clear the file after processing
        self._clear_events_file()

        logger.info(
            f"HealerBridge: Done - processed={stats['processed']}, "
            f"skipped={stats['skipped']}, routed={stats['routed']}, failed={stats['failed']}"
        )

        return stats

    def get_status(self) -> Dict[str, Any]:
        """Get bridge status."""
        return {
            "events_file": str(self.events_file),
            "exists": self.events_file.exists(),
            "pending_events": len(self._read_events(force=True))
            if self.events_file.exists()
            else 0,
            "processed_ids_count": len(self._processed_ids),
            "router_configured": self.router is not None,
        }


def create_bridge(router=None) -> HealerBridge:
    """Create and configure a HealerBridge instance."""
    bridge = HealerBridge(router=router)
    return bridge


# Standalone execution for testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    from trigger_router import TriggerRouter

    router = TriggerRouter()
    bridge = HealerBridge(router=router)

    print("HealerBridge Status:", bridge.get_status())
    print("\nProcessing events...")
    result = bridge.process_events()
    print("Result:", json.dumps(result, indent=2))

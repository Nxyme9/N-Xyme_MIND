"""Analytics — Usage analytics and tracking"""

import json, logging, time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Analytics:
    def __init__(self, data_file: str = "data/analytics.json"):
        self.data_file = Path(data_file)
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self._events: List[Dict] = []

    def track(self, event: str, properties: Optional[Dict] = None):
        self._events.append(
            {"event": event, "properties": properties or {}, "timestamp": time.time()}
        )
        if len(self._events) > 1000:
            self._events = self._events[-1000:]

    def get_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[Dict]:
        if event_type:
            return [e for e in self._events if e["event"] == event_type][-limit:]
        return self._events[-limit:]

    def get_summary(self) -> Dict:
        event_counts = {}
        for e in self._events:
            event_counts[e["event"]] = event_counts.get(e["event"], 0) + 1
        return {"total_events": len(self._events), "by_type": event_counts}

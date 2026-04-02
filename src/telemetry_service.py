"""Telemetry Service — OpenTelemetry-style metrics"""

import logging, time
from typing import Dict, List

logger = logging.getLogger(__name__)


class TelemetryService:
    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._spans: List[dict] = []

    def counter(self, name: str, value: int = 1):
        self._counters[name] = self._counters.get(name, 0) + value

    def gauge(self, name: str, value: float):
        self._gauges[name] = value

    def start_span(self, name: str) -> str:
        span_id = f"span_{len(self._spans)}"
        self._spans.append({"id": span_id, "name": name, "start": time.time(), "end": None})
        return span_id

    def end_span(self, span_id: str):
        for span in self._spans:
            if span["id"] == span_id:
                span["end"] = time.time()
                span["duration"] = span["end"] - span["start"]
                break

    def get_metrics(self) -> Dict:
        return {
            "counters": self._counters,
            "gauges": self._gauges,
            "spans": [s for s in self._spans if s.get("end")],
        }

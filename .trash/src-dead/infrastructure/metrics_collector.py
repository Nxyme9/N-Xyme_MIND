"""Metrics Collector — Collect and aggregate metrics"""

import logging, time
from collections import defaultdict
from typing import Dict, List

logger = logging.getLogger(__name__)


class MetricsCollector:
    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)

    def counter_inc(self, name: str, value: int = 1):
        self._counters[name] += value

    def gauge_set(self, name: str, value: float):
        self._gauges[name] = value

    def histogram_observe(self, name: str, value: float):
        self._histograms[name].append(value)
        if len(self._histograms[name]) > 1000:
            self._histograms[name] = self._histograms[name][-1000:]

    def get_metrics(self) -> Dict:
        result = {"counters": dict(self._counters), "gauges": dict(self._gauges)}
        for name, values in self._histograms.items():
            if values:
                sorted_v = sorted(values)
                result[f"histogram_{name}"] = {
                    "count": len(values),
                    "min": sorted_v[0],
                    "max": sorted_v[-1],
                    "avg": sum(values) / len(values),
                    "p50": sorted_v[len(sorted_v) // 2],
                    "p95": sorted_v[int(len(sorted_v) * 0.95)],
                }
        return result

"""Comprehensive Monitoring/Observability — Metrics, logging, alerting."""

import json
import os
import time
import threading
from typing import Dict, List
from collections import defaultdict


class MetricsCollector:
    def __init__(self):
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._start_time = time.time()

    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def observe(self, name: str, value: float) -> None:
        with self._lock:
            self._histograms[name].append(value)
            # Keep last 1000 values
            if len(self._histograms[name]) > 1000:
                self._histograms[name] = self._histograms[name][-1000:]

    def get_metrics(self) -> dict:
        with self._lock:
            histograms = {}
            for name, values in self._histograms.items():
                if values:
                    sorted_v = sorted(values)
                    histograms[name] = {
                        "count": len(values),
                        "min": round(min(values), 2),
                        "max": round(max(values), 2),
                        "avg": round(sum(values) / len(values), 2),
                        "p50": round(sorted_v[len(sorted_v) // 2], 2),
                        "p95": round(sorted_v[int(len(sorted_v) * 0.95)], 2),
                        "p99": round(sorted_v[int(len(sorted_v) * 0.99)], 2),
                    }
            return {
                "uptime_seconds": round(time.time() - self._start_time, 1),
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": histograms,
            }


class AlertManager:
    def __init__(self):
        self._alerts: List[dict] = []
        self._lock = threading.Lock()

    def alert(self, severity: str, message: str, details: dict = None) -> None:
        with self._lock:
            self._alerts.append({
                "timestamp": time.time(),
                "severity": severity,
                "message": message,
                "details": details or {},
            })

    def get_alerts(self, limit: int = 20) -> List[dict]:
        with self._lock:
            return self._alerts[-limit:]


# Global instances
metrics = MetricsCollector()
alerts = AlertManager()

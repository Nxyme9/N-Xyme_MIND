"""Metrics collector with Prometheus format export."""

from __future__ import annotations

import time
import threading
from collections import defaultdict
from typing import Any


class MetricsCollector:
    """Thread-safe metrics collector for delegation system."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._histogram_max: dict[str, int] = defaultdict(lambda: 1000)
        self._start_times: dict[str, float] = {}

    def counter_inc(self, name: str, value: float = 1.0) -> None:
        """Increment a counter metric."""
        with self._lock:
            self._counters[name] += value

    def gauge_set(self, name: str, value: float) -> None:
        """Set a gauge metric."""
        with self._lock:
            self._gauges[name] = value

    def gauge_inc(self, name: str, value: float = 1.0) -> None:
        """Increment a gauge metric."""
        with self._lock:
            self._gauges[name] = self._gauges.get(name, 0.0) + value

    def gauge_dec(self, name: str, value: float = 1.0) -> None:
        """Decrement a gauge metric."""
        with self._lock:
            self._gauges[name] = self._gauges.get(name, 0.0) - value

    def histogram_observe(self, name: str, value: float) -> None:
        """Record a histogram observation."""
        with self._lock:
            self._histograms[name].append(value)
            max_len = self._histogram_max[name]
            if len(self._histograms[name]) > max_len:
                self._histograms[name] = self._histograms[name][-max_len:]

    def timer_start(self, name: str) -> None:
        """Start a timer for latency measurement."""
        self._start_times[name] = time.monotonic()

    def timer_stop(self, name: str) -> float | None:
        """Stop a timer and record the latency. Returns latency in seconds."""
        start = self._start_times.pop(name, None)
        if start is None:
            return None
        latency = time.monotonic() - start
        self.histogram_observe(f"{name}_latency_seconds", latency)
        return latency

    def record_delegation(
        self,
        agent: str,
        level: str,
        success: bool,
        tokens: int = 0,
        cost: float = 0.0,
    ) -> None:
        """Record a delegation event with all related metrics."""
        if success:
            self.counter_inc("delegations_success_total")
        else:
            self.counter_inc("delegations_failure_total")
        self.counter_inc("delegations_total")
        self.counter_inc(f"delegations_{agent}_total")
        self.counter_inc(f"delegations_{level}_total")
        if tokens > 0:
            self.counter_inc("tokens_total", tokens)
            self.counter_inc(f"tokens_{agent}_total", tokens)
        if cost > 0:
            self.counter_inc("cost_total", cost)
            self.counter_inc(f"cost_{agent}_total", cost)

    def record_api_error(self, agent: str, error_type: str) -> None:
        """Record a model API error."""
        self.counter_inc("api_errors_total")
        self.counter_inc(f"api_errors_{error_type}_total")
        self.counter_inc(f"api_errors_{agent}_total")

    def set_queue_depth(self, depth: int) -> None:
        """Set the current queue depth."""
        self.gauge_set("queue_depth", depth)

    def get_histogram_stats(self, name: str) -> dict[str, float] | None:
        """Get statistics for a histogram."""
        with self._lock:
            values = self._histograms.get(name)
            if not values:
                return None
            sorted_v = sorted(values)
            count = len(sorted_v)
            return {
                "count": count,
                "sum": sum(sorted_v),
                "min": sorted_v[0],
                "max": sorted_v[-1],
                "avg": sum(sorted_v) / count,
                "p50": sorted_v[int(count * 0.50)],
                "p90": sorted_v[int(count * 0.90)],
                "p95": sorted_v[int(count * 0.95)],
                "p99": sorted_v[min(int(count * 0.99), count - 1)],
            }

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus text format."""
        lines: list[str] = []
        lines.append("# HELP delegations_total Total number of delegations")
        lines.append("# TYPE delegations_total counter")
        lines.append(f"delegations_total {self._counters.get('delegations_total', 0)}")
        lines.append("")

        lines.append("# HELP delegations_success_total Total successful delegations")
        lines.append("# TYPE delegations_success_total counter")
        lines.append(
            f"delegations_success_total {self._counters.get('delegations_success_total', 0)}"
        )
        lines.append("")

        lines.append("# HELP delegations_failure_total Total failed delegations")
        lines.append("# TYPE delegations_failure_total counter")
        lines.append(
            f"delegations_failure_total {self._counters.get('delegations_failure_total', 0)}"
        )
        lines.append("")

        for key, value in self._counters.items():
            if (
                key.startswith("delegations_")
                and key.endswith("_total")
                and key
                not in (
                    "delegations_total",
                    "delegations_success_total",
                    "delegations_failure_total",
                )
            ):
                agent = key.replace("delegations_", "").replace("_total", "")
                lines.append(f'delegations_by_agent_total{{agent="{agent}"}} {value}')
        lines.append("")

        lines.append("# HELP tokens_total Total tokens consumed")
        lines.append("# TYPE tokens_total counter")
        lines.append(f"tokens_total {self._counters.get('tokens_total', 0)}")
        lines.append("")

        lines.append("# HELP cost_total Total cost in USD")
        lines.append("# TYPE cost_total counter")
        lines.append(f"cost_total {self._counters.get('cost_total', 0)}")
        lines.append("")

        lines.append("# HELP api_errors_total Total API errors")
        lines.append("# TYPE api_errors_total counter")
        lines.append(f"api_errors_total {self._counters.get('api_errors_total', 0)}")
        lines.append("")

        for key, value in self._counters.items():
            if (
                key.startswith("api_errors_")
                and key.endswith("_total")
                and key != "api_errors_total"
            ):
                error_type = key.replace("api_errors_", "").replace("_total", "")
                lines.append(f'api_errors_by_type_total{{type="{error_type}"}} {value}')
        lines.append("")

        lines.append("# HELP queue_depth Current queue depth")
        lines.append("# TYPE queue_depth gauge")
        lines.append(f"queue_depth {self._gauges.get('queue_depth', 0)}")
        lines.append("")

        for name, values in self._histograms.items():
            if not values:
                continue
            sorted_v = sorted(values)
            count = len(sorted_v)
            lines.append(f"# HELP {name} Histogram of {name}")
            lines.append(f"# TYPE {name} histogram")
            lines.append(f"{name}_count {count}")
            lines.append(f"{name}_sum {sum(sorted_v)}")
            lines.append(f"{name}_min {sorted_v[0]}")
            lines.append(f"{name}_max {sorted_v[-1]}")
            lines.append(f"{name}_avg {sum(sorted_v) / count}")
            lines.append(f"{name}_p50 {sorted_v[int(count * 0.50)]}")
            lines.append(f"{name}_p95 {sorted_v[int(count * 0.95)]}")
            lines.append("")

        return "\n".join(lines)

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all metrics as a dictionary."""
        result: dict[str, Any] = {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {},
        }
        for name in self._histograms:
            stats = self.get_histogram_stats(name)
            if stats:
                result["histograms"][name] = stats
        return result


_collector: MetricsCollector | None = None
_collector_lock = threading.Lock()


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector singleton."""
    global _collector
    if _collector is None:
        with _collector_lock:
            if _collector is None:
                _collector = MetricsCollector()
    return _collector


def reset_metrics_collector() -> None:
    """Reset the global metrics collector (for testing)."""
    global _collector
    with _collector_lock:
        _collector = None

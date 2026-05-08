#!/usr/bin/env python3
"""OBSERVABILITY — Structured Logging, Metrics, SLI/SLO for N-Xyme_MIND.

Phase 4.1 of Masterplan: Production Readiness.

Provides:
- Structured JSON logger with trace context
- SLI definitions: task_latency_p50, task_latency_p99, success_rate, error_rate
- SLO targets: latency_p99 < 5s, success_rate > 0.95
- Prometheus-compatible metrics export
- Integration with memory_bridge for automatic tracking

Usage:
    from packages.orchestration.observability import (
        get_logger,
        get_metrics,
        get_slo_health,
        metrics_endpoint,
    )

    # Get structured logger
    logger = get_logger("orchestration")
    logger.info("task_started", task_id="xxx", agent="hephaestus")

    # Check SLO health
    health = get_slo_health()
    if health["success_rate"]["violated"]:
        alert("SLO violation: success_rate")
"""

from __future__ import annotations

import os
import sys
import json
import time
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from collections import defaultdict
from enum import Enum

# Optional: Try to integrate with existing tracing
try:
    from packages.orchestration.tracing import TracingState, SpanData

    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False
    TracingState = Any
    SpanData = Any

# Default paths
DEFAULT_METRICS_DB = ".sisyphus/metrics.db"

__version__ = "1.0.0"
__all__ = [
    "get_logger",
    "get_metrics",
    "get_slo_health",
    "metrics_endpoint",
    "SLIConfig",
    "SLOConfig",
    "MetricsCollector",
    "StructuredLogger",
    "SLOHealth",
]


# =============================================================================
# Configuration
# =============================================================================


class SLIType(str, Enum):
    """Service Level Indicator types."""

    TASK_LATENCY_P50 = "task_latency_p50"
    TASK_LATENCY_P99 = "task_latency_p99"
    SUCCESS_RATE = "success_rate"
    ERROR_RATE = "error_rate"


class SLOType(str, Enum):
    """Service Level Objective types."""

    LATENCY_P99 = "latency_p99"
    SUCCESS_RATE = "success_rate"


@dataclass
class SLIConfig:
    """SLI Configuration."""

    sli_type: SLIType
    description: str
    unit: str
    # For latency: in milliseconds
    # For rate: 0.0 to 1.0


@dataclass
class SLOConfig:
    """SLO Configuration with target and window."""

    slo_type: SLOType
    target: float  # e.g., 5000ms for latency_p99, 0.95 for success_rate
    window_seconds: int = 300  # 5-minute window
    description: str = ""

    def __post_init__(self):
        if not self.description:
            if self.slo_type == SLOType.LATENCY_P99:
                self.description = f"P99 latency < {self.target}ms"
            elif self.slo_type == SLOType.SUCCESS_RATE:
                self.description = f"Success rate > {self.target * 100}%"


# Default SLO configurations
DEFAULT_SLOS = {
    SLOType.LATENCY_P99: SLOConfig(
        slo_type=SLOType.LATENCY_P99,
        target=5000.0,  # 5 seconds
        window_seconds=300,
        description="P99 latency < 5s",
    ),
    SLOType.SUCCESS_RATE: SLOConfig(
        slo_type=SLOType.SUCCESS_RATE,
        target=0.95,  # 95%
        window_seconds=300,
        description="Success rate > 95%",
    ),
}


# =============================================================================
# Structured Logger
# =============================================================================


class JSONFormatter(logging.Formatter):
    """JSON formatter with trace context injection."""

    def __init__(self, service_name: str = "n-xyme-mind"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        # Build base log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
        }

        # Add trace context if available
        state = None
        if TRACING_AVAILABLE:
            try:
                state = TracingState.get_instance()
            except Exception:
                pass

        # Inject trace context
        if state and hasattr(state, "_span_count"):
            log_data["trace_id"] = getattr(
                record, "trace_id", f"trace-{state._span_count}"
            )

        # Add extra fields
        if hasattr(record, "task_id"):
            log_data["task_id"] = record.task_id
        if hasattr(record, "agent"):
            log_data["agent"] = record.agent
        if hasattr(record, "latency_ms"):
            log_data["latency_ms"] = record.latency_ms

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class StructuredLogger:
    """Structured logger with JSON output and trace context."""

    _instances: dict[str, "StructuredLogger"] = {}
    _lock = threading.Lock()

    def __init__(self, name: str, service_name: str = "n-xyme-mind"):
        self.name = name
        self.service_name = service_name

        # Create logger
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.DEBUG)

        # Add JSON handler if not already present
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(JSONFormatter(service_name))
            self._logger.addHandler(handler)

        self._logger.propagate = False

    @classmethod
    def get_instance(
        cls, name: str, service_name: str = "n-xyme-mind"
    ) -> "StructuredLogger":
        """Get or create logger instance."""
        key = f"{service_name}:{name}"
        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = cls(name, service_name)
            return cls._instances[key]

    def _log(
        self,
        level: int,
        message: str,
        extra: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        """Internal log method."""
        # Build extra dict
        extra = extra or {}
        for key, value in kwargs.items():
            # Filter reserved attributes
            if key not in ("name", "msg", "args", "level", "exc_info"):
                extra[key] = value

        # Create log record
        self._logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs) -> None:
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        self._log(logging.CRITICAL, message, **kwargs)

    # Structured logging methods
    def task_started(
        self,
        task_id: str,
        agent: str,
        level: int,
        **kwargs,
    ) -> None:
        """Log task start with context."""
        self.info(
            f"Task started: {task_id}",
            task_id=task_id,
            agent=agent,
            level=level,
            event="task_started",
            **kwargs,
        )

    def task_completed(
        self,
        task_id: str,
        agent: str,
        success: bool,
        latency_ms: float,
        **kwargs,
    ) -> None:
        """Log task completion with metrics."""
        status = "success" if success else "failed"
        self.info(
            f"Task {status}: {task_id}",
            task_id=task_id,
            agent=agent,
            success=success,
            latency_ms=latency_ms,
            event="task_completed",
            **kwargs,
        )

    def sli_calculated(
        self,
        sli_type: SLIType,
        value: float,
        **kwargs,
    ) -> None:
        """Log SLI calculation."""
        self.info(
            f"SLI {sli_type.value}: {value}",
            sli_type=sli_type.value,
            value=value,
            event="sli_calculated",
            **kwargs,
        )

    def slo_violation(
        self,
        slo_type: SLOType,
        current: float,
        target: float,
        **kwargs,
    ) -> None:
        """Log SLO violation."""
        self.warning(
            f"SLO violation: {slo_type.value}",
            slo_type=slo_type.value,
            current=current,
            target=target,
            event="slo_violation",
            **kwargs,
        )


def get_logger(name: str, service_name: str = "n-xyme-mind") -> StructuredLogger:
    """Get structured logger instance."""
    return StructuredLogger.get_instance(name, service_name)


# =============================================================================
# Metrics Collector
# =============================================================================


@dataclass
class MetricSample:
    """Single metric sample."""

    timestamp: float
    value: float
    labels: dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """Collects and exports Prometheus metrics.

    Thread-safe with locking.
    """

    _instance: Optional["MetricsCollector"] = None
    _lock = threading.Lock()

    def __init__(self):
        # Counters
        self._counters: dict[str, float] = defaultdict(float)

        # Gauges
        self._gauges: dict[str, float] = {}

        # Histograms (buckets)
        self._histograms: dict[str, list[float]] = defaultdict(list)

        # Lock for thread safety
        self._data_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "MetricsCollector":
        """Get singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ----- Counter Operations -----

    def inc_counter(self, name: str, value: float = 1.0) -> None:
        """Increment counter."""
        with self._data_lock:
            self._counters[name] += value

    def get_counter(self, name: str) -> float:
        """Get counter value."""
        with self._data_lock:
            return self._counters.get(name, 0.0)

    # ----- Gauge Operations -----

    def set_gauge(self, name: str, value: float) -> None:
        """Set gauge value."""
        with self._data_lock:
            self._gauges[name] = value

    def get_gauge(self, name: str) -> float:
        """Get gauge value."""
        with self._data_lock:
            return self._gauges.get(name, 0.0)

    # ----- Histogram Operations -----

    def observe(self, name: str, value: float) -> None:
        MAX_HISTOGRAM_SIZE = 10000
        with self._data_lock:
            self._histograms[name].append(value)
            if len(self._histograms[name]) > MAX_HISTOGRAM_SIZE:
                self._histograms[name] = self._histograms[name][-MAX_HISTOGRAM_SIZE:]

    def get_histogram_stats(self, name: str) -> dict[str, float]:
        """Get histogram statistics (p50, p95, p99)."""
        with self._data_lock:
            values = sorted(self._histograms.get(name, []))
            if not values:
                return {"count": 0, "sum": 0, "p50": 0, "p95": 0, "p99": 0}

            n = len(values)
            return {
                "count": n,
                "sum": sum(values),
                "p50": values[int(n * 0.5)] if n > 0 else 0,
                "p95": values[int(n * 0.95)] if n > 0 else 0,
                "p99": values[int(n * 0.99)] if n > 0 else 0,
            }

    # ----- Task Tracking -----

    def record_task(
        self,
        task_id: str,
        agent: str,
        success: bool,
        latency_ms: float,
    ) -> None:
        """Record task outcome."""
        timestamp = time.time()

        # Update counters
        self.inc_counter("tasks_total")
        if success:
            self.inc_counter("tasks_success")
        else:
            self.inc_counter("tasks_failed")
            self.inc_counter("errors_total")

        # Update by agent
        agent_counter = f"tasks_by_agent_{agent}_total"
        self.inc_counter(agent_counter)

        if success:
            agent_success = f"tasks_by_agent_{agent}_success"
            self.inc_counter(agent_success)

        # Observe latency
        self.observe("task_latency_ms", latency_ms)

        # Update active tasks (gauge)
        self.set_gauge("last_task_timestamp", timestamp)
        task_id_int = int(task_id[:8], 16) if task_id else 0
        self.set_gauge("last_task_id", float(task_id_int))

    # ----- SLO Calculation -----

    def calculate_sli(
        self,
        sli_type: SLIType,
        window_seconds: int = 300,
    ) -> float:
        """Calculate SLI value for type."""
        with self._data_lock:
            if sli_type == SLIType.SUCCESS_RATE:
                total = self._counters.get("tasks_total", 0)
                success = self._counters.get("tasks_success", 0)
                return success / total if total > 0 else 1.0

            elif sli_type == SLIType.ERROR_RATE:
                total = self._counters.get("tasks_total", 0)
                errors = self._counters.get("errors_total", 0)
                return errors / total if total > 0 else 0.0

            elif sli_type == SLIType.TASK_LATENCY_P50:
                latencies = self._histograms.get("task_latency_ms", [])
                if not latencies:
                    return 0.0
                sorted_lat = sorted(latencies)
                n = len(sorted_lat)
                return sorted_lat[int(n * 0.5)]

            elif sli_type == SLIType.TASK_LATENCY_P99:
                latencies = self._histograms.get("task_latency_ms", [])
                if not latencies:
                    return 0.0
                sorted_lat = sorted(latencies)
                n = len(sorted_lat)
                return sorted_lat[int(n * 0.99)] if n > 0 else 0.0

            return 0.0

    # ----- Prometheus Export -----

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []
        timestamp = int(time.time() * 1000)

        with self._data_lock:
            # Counters
            for name, value in self._counters.items():
                metric_name = name.replace("-", "_")
                lines.append(f"# TYPE {metric_name} counter")
                lines.append(f"{metric_name}{{}} {value} {timestamp}")

            # Gauges
            for name, value in self._gauges.items():
                metric_name = name.replace("-", "_")
                lines.append(f"# TYPE {metric_name} gauge")
                lines.append(f"{metric_name}{{}} {value} {timestamp}")

            # Histograms
            for name, values in self._histograms.items():
                if not values:
                    continue
                metric_name = name.replace("-", "_")
                sorted_vals = sorted(values)
                n = len(sorted_vals)

                lines.append(f"# TYPE {metric_name} histogram")
                lines.append(f'{metric_name}_bucket{{le="+Inf"}} {n} {timestamp}')
                lines.append(
                    f'{metric_name}_bucket{{le="50"}} '
                    f"{sum(1 for v in sorted_vals if v <= 50)} {timestamp}"
                )
                lines.append(
                    f'{metric_name}_bucket{{le="100"}} '
                    f"{sum(1 for v in sorted_vals if v <= 100)} {timestamp}"
                )
                lines.append(
                    f'{metric_name}_bucket{{le="500"}} '
                    f"{sum(1 for v in sorted_vals if v <= 500)} {timestamp}"
                )
                lines.append(
                    f'{metric_name}_bucket{{le="1000"}} '
                    f"{sum(1 for v in sorted_vals if v <= 1000)} {timestamp}"
                )
                lines.append(
                    f'{metric_name}_bucket{{le="5000"}} '
                    f"{sum(1 for v in sorted_vals if v <= 5000)} {timestamp}"
                )
                lines.append(f"{metric_name}_sum {sum(values)} {timestamp}")
                lines.append(f"{metric_name}_count {n} {timestamp}")

        return "\n".join(lines) + "\n"


def get_metrics() -> MetricsCollector:
    """Get metrics collector instance."""
    return MetricsCollector.get_instance()


def metrics_endpoint() -> str:
    """Get Prometheus metrics endpoint content."""
    return get_metrics().export_prometheus()


# =============================================================================
# SLO Health Check
# =============================================================================


@dataclass
class SLOHealth:
    """SLO health status."""

    slo_type: SLOType
    current: float
    target: float
    violated: bool
    window_seconds: int


def get_slo_health(
    slos: Optional[dict[SLOType, SLOConfig]] = None,
) -> dict[str, SLOHealth]:
    """Calculate SLO health status.

    Args:
        slos: Optional custom SLO configs (uses defaults if not provided)

    Returns:
        Dict of SLOType -> SLOHealth with current vs target
    """
    slos = slos or DEFAULT_SLOS
    collector = get_metrics()

    result = {}

    for slo_type, config in slos.items():
        if slo_type == SLOType.LATENCY_P99:
            current = collector.calculate_sli(
                SLIType.TASK_LATENCY_P99,
                config.window_seconds,
            )
            violated = current > config.target

        elif slo_type == SLOType.SUCCESS_RATE:
            current = collector.calculate_sli(
                SLIType.SUCCESS_RATE,
                config.window_seconds,
            )
            violated = current < config.target

        else:
            continue

        result[slo_type.value] = SLOHealth(
            slo_type=slo_type,
            current=current,
            target=config.target,
            violated=violated,
            window_seconds=config.window_seconds,
        )

    return result


# =============================================================================
# Integration with memory_bridge
# =============================================================================


def init_observability() -> None:
    """Initialize observability system.

    Called on module import.
    """
    # Check for environment variable override
    enabled = os.environ.get("NX_YME_OBSERVABILITY_ENABLED", "true").lower()
    if enabled not in ("1", "true", "yes"):
        return

    # Initialize metrics collector
    collector = get_metrics()

    # Initialize structured logger
    get_logger("orchestration")

    # Log initialization
    logger = get_logger("observability")
    logger.info("Observability initialized", version=__version__)


# Auto-init on import
init_observability()

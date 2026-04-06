"""Distributed tracer with W3C Trace Context format."""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from src.observability.metrics import get_metrics_collector
except ImportError:
    get_metrics_collector = None

try:
    from src.tools.observability.logger import get_logger
except ImportError:
    get_logger = None


class SpanStatus:
    OK = "ok"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class SpanEvent:
    """An event within a span."""

    name: str
    timestamp: float
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "timestamp": self.timestamp,
            "attributes": self.attributes,
        }


@dataclass
class Span:
    """A span within a trace."""

    trace_id: str
    span_id: str
    name: str
    parent_span_id: str | None
    start_time: float
    end_time: float | None = None
    status: str = SpanStatus.OK
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[SpanEvent] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float | None:
        if self.end_time is None:
            return None
        return self.end_time - self.start_time

    @property
    def duration_ms(self) -> float | None:
        if self.duration_seconds is None:
            return None
        return self.duration_seconds * 1000

    @property
    def is_active(self) -> bool:
        return self.end_time is None

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        event = SpanEvent(
            name=name,
            timestamp=time.monotonic(),
            attributes=attributes or {},
        )
        self.events.append(event)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "name": self.name,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes,
            "events": [e.to_dict() for e in self.events],
        }


@dataclass
class Trace:
    """A complete trace with spans."""

    trace_id: str
    name: str
    start_time: float
    spans: list[Span] = field(default_factory=list)
    root_span_id: str | None = None

    @property
    def duration_seconds(self) -> float | None:
        if not self.spans:
            return None
        active_spans = [s for s in self.spans if s.end_time is not None]
        if not active_spans:
            return None
        start = min(s.start_time for s in active_spans)
        end = max(s.end_time for s in active_spans)
        return end - start

    @property
    def duration_ms(self) -> float | None:
        if self.duration_seconds is None:
            return None
        return self.duration_seconds * 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "name": self.name,
            "start_time": self.start_time,
            "duration_seconds": self.duration_seconds,
            "duration_ms": self.duration_ms,
            "root_span_id": self.root_span_id,
            "span_count": len(self.spans),
            "spans": [s.to_dict() for s in self.spans],
        }


def _generate_trace_id() -> str:
    """Generate a W3C Trace Context compliant trace ID (32 hex chars, 16 bytes)."""
    return uuid.uuid4().hex + uuid.uuid4().hex[:16]


def _generate_span_id() -> str:
    """Generate a W3C Trace Context compliant span ID (16 hex chars, 8 bytes)."""
    return uuid.uuid4().hex[:16]


class DistributedTracer:
    """Distributed tracer for delegation flows.

    Supports W3C Trace Context format, parent-child span relationships,
    span attributes and events, and trace export to JSON file and console.
    """

    def __init__(self, export_dir: Path | None = None) -> None:
        self._lock = threading.RLock()
        self._traces: dict[str, Trace] = {}
        self._active_spans: dict[str, Span] = {}
        self._span_stack: dict[str, list[str]] = {}
        self._export_dir = export_dir or Path(__file__).parent.parent.parent / "traces"
        self._export_dir.mkdir(parents=True, exist_ok=True)
        self._metrics = get_metrics_collector() if get_metrics_collector else None
        self._logger = None

    def _get_logger(self):
        if self._logger is None:
            if get_logger:
                self._logger = get_logger("tracer")
            else:
                import logging

                self._logger = logging.getLogger("tracer")
        return self._logger

    def start_trace(self, name: str) -> str:
        """Start a new trace and return its trace ID."""
        trace_id = _generate_trace_id()
        trace = Trace(
            trace_id=trace_id,
            name=name,
            start_time=time.monotonic(),
        )
        with self._lock:
            self._traces[trace_id] = trace
            self._span_stack[trace_id] = []

        self._emit_metric("traces_started_total", 1)
        self._get_logger().info(
            f"trace:started:{name}",
            extra={"context": {"trace_id": trace_id}},
        )
        return trace_id

    def start_span(
        self,
        name: str,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Span:
        """Start a new span within a trace.

        Args:
            name: Span name.
            trace_id: Trace ID. If None, uses the most recent trace.
            parent_span_id: Parent span ID. If None, becomes root span.
            attributes: Initial span attributes.

        Returns:
            The created Span instance.
        """
        with self._lock:
            if trace_id is None:
                if not self._traces:
                    trace_id = self.start_trace("auto-trace")
                else:
                    trace_id = list(self._traces.keys())[-1]

            trace = self._traces.get(trace_id)
            if trace is None:
                raise ValueError(f"Trace {trace_id} not found")

            if parent_span_id is None:
                stack = self._span_stack.get(trace_id, [])
                if stack:
                    parent_span_id = stack[-1]

            span_id = _generate_span_id()
            span = Span(
                trace_id=trace_id,
                span_id=span_id,
                name=name,
                parent_span_id=parent_span_id,
                start_time=time.monotonic(),
                attributes=attributes or {},
            )

            trace.spans.append(span)
            self._active_spans[span_id] = span

            if trace.root_span_id is None:
                trace.root_span_id = span_id

            stack = self._span_stack.setdefault(trace_id, [])
            stack.append(span_id)

        self._emit_metric("spans_started_total", 1)
        return span

    def end_span(self, span: Span, status: str = SpanStatus.OK) -> None:
        """End a span and record its status.

        Args:
            span: The span to end.
            status: Span status (ok, error, cancelled).
        """
        span.end_time = time.monotonic()
        span.status = status

        with self._lock:
            self._active_spans.pop(span.span_id, None)

            stack = self._span_stack.get(span.trace_id, [])
            if stack and stack[-1] == span.span_id:
                stack.pop()

        self._emit_metric("spans_ended_total", 1)
        if span.duration_seconds is not None:
            self._emit_histogram("span_duration_seconds", span.duration_seconds)

        if status == SpanStatus.ERROR:
            self._emit_metric("spans_error_total", 1)

        self._get_logger().info(
            f"span:ended:{span.name}",
            extra={
                "context": {
                    "trace_id": span.trace_id,
                    "span_id": span.span_id,
                    "status": status,
                    "duration_ms": span.duration_ms,
                }
            },
        )

    def add_event(
        self,
        span: Span,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Add an event to a span.

        Args:
            span: The span to add the event to.
            name: Event name.
            attributes: Event attributes.
        """
        span.add_event(name, attributes)
        self._emit_metric("span_events_total", 1)

    def get_trace(self, trace_id: str) -> Trace | None:
        """Get a complete trace by ID."""
        with self._lock:
            return self._traces.get(trace_id)

    def get_all_traces(self) -> list[Trace]:
        """Get all traces."""
        with self._lock:
            return list(self._traces.values())

    def export_traces(self, output_path: Path | None = None) -> Path:
        """Export all traces to a JSON file.

        Args:
            output_path: Output file path. Defaults to traces/traces_<timestamp>.json.

        Returns:
            Path to the exported file.
        """
        if output_path is None:
            timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            output_path = self._export_dir / f"traces_{timestamp}.json"

        with self._lock:
            data = {
                "exported_at": datetime.now(tz=timezone.utc).isoformat(),
                "trace_count": len(self._traces),
                "traces": [t.to_dict() for t in self._traces.values()],
            }

        output_path.write_text(json.dumps(data, indent=2, default=str))

        self._get_logger().info(
            f"traces:exported",
            extra={"context": {"path": str(output_path), "count": len(self._traces)}},
        )
        return output_path

    def export_trace_to_console(self, trace_id: str) -> str:
        """Export a single trace as formatted JSON string."""
        trace = self.get_trace(trace_id)
        if trace is None:
            return f"Trace {trace_id} not found"
        return json.dumps(trace.to_dict(), indent=2, default=str)

    def clear_traces(self) -> None:
        """Clear all traces from memory."""
        with self._lock:
            self._traces.clear()
            self._active_spans.clear()
            self._span_stack.clear()

    def get_active_span_count(self) -> int:
        """Get the number of currently active spans."""
        with self._lock:
            return len(self._active_spans)

    def _emit_metric(self, name: str, value: float) -> None:
        """Emit a metric to the metrics collector."""
        if self._metrics is None:
            return
        try:
            if "total" in name:
                self._metrics.counter_inc(name, value)
            else:
                self._metrics.gauge_set(name, value)
        except Exception:
            pass

    def _emit_histogram(self, name: str, value: float) -> None:
        """Emit a histogram observation."""
        if self._metrics is None:
            return
        try:
            self._metrics.histogram_observe(name, value)
        except Exception:
            pass


_tracer: DistributedTracer | None = None
_tracer_lock = threading.Lock()


def get_tracer(export_dir: Path | None = None) -> DistributedTracer:
    """Get or create the global tracer singleton."""
    global _tracer
    if _tracer is None:
        with _tracer_lock:
            if _tracer is None:
                _tracer = DistributedTracer(export_dir=export_dir)
    return _tracer


def reset_tracer() -> None:
    """Reset the global tracer (for testing)."""
    global _tracer
    with _tracer_lock:
        _tracer = None

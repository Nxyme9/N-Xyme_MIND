"""Trace context propagation between agents."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any


@dataclass
class TraceContext:
    """W3C Trace Context propagation header.

    Format: traceparent: 00-<trace-id>-<parent-span-id>-<flags>
    - trace-id: 32 hex characters (16 bytes)
    - parent-span-id: 16 hex characters (8 bytes)
    - flags: 2 hex characters (01 = sampled)
    """

    trace_id: str
    span_id: str
    is_sampled: bool = True

    @property
    def traceparent(self) -> str:
        """Generate W3C traceparent header value."""
        flags = "01" if self.is_sampled else "00"
        return f"00-{self.trace_id}-{self.span_id}-{flags}"

    @classmethod
    def from_traceparent(cls, traceparent: str) -> TraceContext:
        """Parse a W3C traceparent header value.

        Args:
            traceparent: String in format "00-<trace-id>-<span-id>-<flags>"

        Returns:
            Parsed TraceContext instance.

        Raises:
            ValueError: If the traceparent string is malformed.
        """
        parts = traceparent.split("-")
        if len(parts) != 4:
            raise ValueError(
                f"Invalid traceparent format: expected 4 parts, got {len(parts)}"
            )

        version, trace_id, span_id, flags = parts

        if version != "00":
            raise ValueError(f"Unsupported traceparent version: {version}")

        if len(trace_id) != 32:
            raise ValueError(
                f"Invalid trace_id length: expected 32, got {len(trace_id)}"
            )

        if len(span_id) != 16:
            raise ValueError(f"Invalid span_id length: expected 16, got {len(span_id)}")

        is_sampled = flags == "01"

        return cls(
            trace_id=trace_id,
            span_id=span_id,
            is_sampled=is_sampled,
        )

    def to_headers(self) -> dict[str, str]:
        """Convert to HTTP headers dict for propagation."""
        return {"traceparent": self.traceparent}

    @classmethod
    def from_headers(cls, headers: dict[str, str]) -> TraceContext | None:
        """Extract trace context from HTTP headers.

        Args:
            headers: Dict of header names to values.

        Returns:
            TraceContext if traceparent header exists, else None.
        """
        traceparent = headers.get("traceparent") or headers.get("Traceparent")
        if not traceparent:
            return None
        return cls.from_traceparent(traceparent)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "is_sampled": self.is_sampled,
            "traceparent": self.traceparent,
        }


_thread_local = threading.local()


def get_current_trace_context() -> TraceContext | None:
    """Get the current trace context from thread-local storage."""
    return getattr(_thread_local, "trace_context", None)


def set_current_trace_context(ctx: TraceContext) -> None:
    """Set the current trace context in thread-local storage."""
    _thread_local.trace_context = ctx


def clear_current_trace_context() -> None:
    """Clear the current trace context from thread-local storage."""
    if hasattr(_thread_local, "trace_context"):
        del _thread_local.trace_context


def inject_trace_context(
    trace_id: str,
    span_id: str,
    is_sampled: bool = True,
) -> dict[str, str]:
    """Create propagation headers for a span.

    Args:
        trace_id: Current trace ID.
        span_id: Current span ID (becomes parent for child spans).
        is_sampled: Whether the trace is sampled.

    Returns:
        Dict of headers to propagate to child agents.
    """
    ctx = TraceContext(
        trace_id=trace_id,
        span_id=span_id,
        is_sampled=is_sampled,
    )
    set_current_trace_context(ctx)
    return ctx.to_headers()


def extract_trace_context(headers: dict[str, str]) -> TraceContext | None:
    """Extract trace context from incoming headers.

    Args:
        headers: Dict of header names to values.

    Returns:
        TraceContext if valid traceparent header exists, else None.
    """
    ctx = TraceContext.from_headers(headers)
    if ctx is not None:
        set_current_trace_context(ctx)
    return ctx

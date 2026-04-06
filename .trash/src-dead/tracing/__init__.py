"""Compatibility: src.tracing → src.tools.tracing"""
from src.tools.tracing.tracer import (  # noqa: F401
    DistributedTracer, SpanStatus, Span, Trace, SpanEvent,
    _generate_span_id, _generate_trace_id, get_tracer, reset_tracer
)

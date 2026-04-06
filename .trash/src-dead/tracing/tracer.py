"""Compatibility: src.tracing.tracer → src.tools.tracing.tracer"""
from src.tools.tracing.tracer import *  # noqa: F401,F403
from src.tools.tracing.tracer import _generate_span_id, _generate_trace_id  # noqa: F401

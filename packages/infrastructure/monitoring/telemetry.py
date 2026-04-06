"""
OpenTelemetry Distributed Tracing for CATALYST
Provides tracing, token usage metrics, and cost attribution.
"""

import time
import json
import logging
import functools
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class Span:
    """A single trace span."""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    status: str = "ok"
    error: Optional[str] = None


@dataclass
class TokenUsage:
    """Token usage tracking."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    cost_usd: float = 0.0


# Cost per 1K tokens (rough estimates for local models)
MODEL_COSTS = {
    "qwen2.5-coder:7b": {"input": 0.0, "output": 0.0},  # Local = free
    "qwen3:8b": {"input": 0.0, "output": 0.0},
    "qwen3:8b-fixed": {"input": 0.0, "output": 0.0},
    "llama3-groq-tool-use:8b": {"input": 0.0, "output": 0.0},
    "granite3.2:8b": {"input": 0.0, "output": 0.0},
    "qwen2.5:14b": {"input": 0.0, "output": 0.0},
    "nomic-embed-text:latest": {"input": 0.0, "output": 0.0},
    "mimo-v2-pro-free": {"input": 0.0, "output": 0.0},  # Free tier
    "default": {"input": 0.001, "output": 0.002},  # Fallback estimate
}


class TelemetryManager:
    """Distributed tracing and metrics collection with bounded buffers."""

    MAX_SPANS = 10000
    MAX_TOKEN_RECORDS = 10000
    MAX_METRICS_PER_KEY = 10000

    def __init__(self, service_name: str = "catalyst"):
        self.service_name = service_name
        self.spans: List[Span] = []
        self.token_usage: List[TokenUsage] = []
        self._trace_counter = 0
        self._span_counter = 0
        self._current_span: Optional[Span] = None
        self._metrics: Dict[str, list] = defaultdict(list)

    def _generate_id(self) -> str:
        """Generate a unique ID."""
        self._span_counter += 1
        return f"{self.service_name}-{self._span_counter}-{int(time.time() * 1000)}"

    def start_span(self, name: str, attributes: Optional[Dict] = None) -> Span:
        """Start a new trace span."""
        span = Span(
            trace_id=self._generate_id(),
            span_id=self._generate_id(),
            parent_span_id=self._current_span.span_id if self._current_span else None,
            name=name,
            start_time=time.time(),
            attributes=attributes or {},
        )
        self._current_span = span
        self.spans.append(span)
        if len(self.spans) > self.MAX_SPANS:
            self.spans = self.spans[-self.MAX_SPANS:]
        return span

    def end_span(self, span: Span, status: str = "ok", error: Optional[str] = None):
        """End a trace span."""
        span.end_time = time.time()
        span.duration_ms = (span.end_time - span.start_time) * 1000
        span.status = status
        span.error = error

        if self._current_span == span:
            self._current_span = None

    def record_token_usage(self, model: str, input_tokens: int, output_tokens: int):
        """Record token usage for cost tracking."""
        costs = MODEL_COSTS.get(model, MODEL_COSTS["default"])
        cost = (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1000

        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            model=model,
            cost_usd=cost,
        )
        self.token_usage.append(usage)
        if len(self.token_usage) > self.MAX_TOKEN_RECORDS:
            self.token_usage = self.token_usage[-self.MAX_TOKEN_RECORDS:]

        # Record metric (bounded)
        for key, val in [("tokens_input", input_tokens), ("tokens_output", output_tokens), ("cost_usd", cost)]:
            self._metrics[key].append(val)
            if len(self._metrics[key]) > self.MAX_METRICS_PER_KEY:
                self._metrics[key] = self._metrics[key][-self.MAX_METRICS_PER_KEY:]

        # Record metric
        self._metrics["tokens_input"].append(input_tokens)
        self._metrics["tokens_output"].append(output_tokens)
        self._metrics["cost_usd"].append(cost)

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics."""
        total_input = sum(u.input_tokens for u in self.token_usage)
        total_output = sum(u.output_tokens for u in self.token_usage)
        total_cost = sum(u.cost_usd for u in self.token_usage)

        spans_with_duration = [s for s in self.spans if s.duration_ms is not None]
        avg_duration: float = 0.0
        if spans_with_duration:
            durations: List[float] = [s.duration_ms for s in spans_with_duration]  # type: ignore[list-item]
            avg_duration = sum(durations) / len(durations)

        return {
            "service": self.service_name,
            "spans_total": len(self.spans),
            "spans_errors": len([s for s in self.spans if s.status == "error"]),
            "avg_duration_ms": round(avg_duration, 2),
            "tokens_input": total_input,
            "tokens_output": total_output,
            "tokens_total": total_input + total_output,
            "cost_usd": round(total_cost, 6),
            "models_used": list(set(u.model for u in self.token_usage)),
        }

    def export_spans(self, limit: int = 100) -> List[Dict]:
        """Export spans as JSON-serializable dicts."""
        return [asdict(s) for s in self.spans[-limit:]]

    def export_json(self, limit: int = 100) -> str:
        """Export spans as JSON string."""
        return json.dumps(
            {
                "service": self.service_name,
                "spans": self.export_spans(limit),
                "stats": self.get_stats(),
            },
            indent=2,
        )


def trace(name: Optional[str] = None, telemetry: Optional[TelemetryManager] = None):
    """Decorator to trace function calls."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            mgr = telemetry or TELEMETRY
            span_name = name or func.__name__
            span = mgr.start_span(span_name, {"function": func.__name__})

            try:
                result = await func(*args, **kwargs)
                mgr.end_span(span, status="ok")
                return result
            except Exception as e:
                mgr.end_span(span, status="error", error=str(e))
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            mgr = telemetry or TELEMETRY
            span_name = name or func.__name__
            span = mgr.start_span(span_name, {"function": func.__name__})

            try:
                result = func(*args, **kwargs)
                mgr.end_span(span, status="ok")
                return result
            except Exception as e:
                mgr.end_span(span, status="error", error=str(e))
                raise

        if asyncio and asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Global instance
TELEMETRY = TelemetryManager()

# Try to import asyncio for async detection
try:
    import asyncio
except ImportError:
    asyncio = None

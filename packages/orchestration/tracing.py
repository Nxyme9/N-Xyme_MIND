"""OpenTelemetry distributed tracing for N-Xyme_MIND brain packages.

Provides:
- Tracer initialization with configurable service name
- @trace decorator for automatic span creation
- Span context managers
- Console exporter for debugging (extensible to OTLP)
- Configurable sampling (always-on for errors, probabilistic for rest)

Usage:
    from packages.orchestration.tracing import trace, get_tracer, TracerConfig

    @trace(service="memory_core", function="search_memories")
    def my_search(query, limit=10):
        ...

    # Or use context manager
    with tracer.start_span("custom_span") as span:
        span.set_attribute("key", "value")
"""

from __future__ import annotations

import os
import sys
import json
import time
import random
import functools
import threading
from typing import Optional, Callable, Any, TypeVar, ParamSpec
from contextlib import contextmanager
from enum import Enum

# OpenTelemetry imports (optional - graceful degradation if not installed)
try:
    from opentelemetry import trace
    from opentelemetry.trace import Tracer, Span, Status, StatusCode
    from opentelemetry.trace.propagation import set_span_in_context
    from opentelemetry.sdk.trace import TracerProvider, SpanProcessor
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.sdk.trace.sampling import (
        Sampler,
        Decision,
        ALWAYS_ON,
        ALWAYS_OFF,
        Probability,
    )

    _OPENTELEMETRY_AVAILABLE = True
except ImportError:
    _OPENTELEMETRY_AVAILABLE = False
    # Create dummy types for graceful degradation
    Tracer = Any
    Span = Any
    Status = Any
    StatusCode = Any

__interface_version__ = "1.0.0"
__all__ = [
    "trace",
    "get_tracer",
    "TracerConfig",
    "trace_span",
    "configure_tracing",
    "SamplerType",
]


class SamplerType(Enum):
    """Sampling strategy options."""

    ALWAYS_ON = "always_on"
    ALWAYS_OFF = "always_off"
    PROBABILISTIC = "probabilistic"
    ERROR_ONLY = "error_only"


class TracerConfig:
    """Configuration for OpenTelemetry tracing."""

    def __init__(
        self,
        service_name: str = "n-xyme-mind",
        sampling_rate: float = 0.1,
        sampling_strategy: str = "error_only",
        export_to_console: bool = True,
        export_to_otlp: bool = False,
        otlp_endpoint: Optional[str] = None,
        enabled: bool = True,
    ):
        self.service_name = service_name
        self.sampling_rate = sampling_rate
        self.sampling_strategy = (
            sampling_strategy
            if isinstance(sampling_strategy, str)
            else sampling_strategy.value
        )
        self.export_to_console = export_to_console
        self.export_to_otlp = export_to_otlp
        self.otlp_endpoint = otlp_endpoint
        self.enabled = enabled

    def to_dict(self) -> dict:
        return {
            "service_name": self.service_name,
            "sampling_rate": self.sampling_rate,
            "sampling_strategy": self.sampling_strategy,
            "export_to_console": self.export_to_console,
            "export_to_otlp": self.export_to_otlp,
            "otlp_endpoint": self.otlp_endpoint,
            "enabled": self.enabled,
        }


class SpanData:
    """Internal span data for storage/export."""

    def __init__(
        self,
        name: str,
        service: str,
        function: str,
        start_time: float,
        end_time: Optional[float] = None,
        duration_ms: Optional[float] = None,
        status: str = "ok",
        error_message: Optional[str] = None,
        attributes: Optional[dict] = None,
    ):
        self.name = name
        self.service = service
        self.function = function
        self.start_time = start_time
        self.end_time = end_time
        self.duration_ms = duration_ms
        self.status = status
        self.error_message = error_message
        self.attributes = attributes or {}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "service": self.service,
            "function": self.function,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error_message": self.error_message,
            "attributes": self.attributes,
        }


class ConsoleSpanExporter2:
    """Custom console exporter for debugging - outputs JSON to stdout."""

    def __init__(self, enabled: bool = True):
        self._enabled = enabled
        self._lock = threading.Lock()

    def export(self, span_datas: list[SpanData]) -> None:
        """Export spans to console."""
        if not self._enabled:
            return
        with self._lock:
            for span_data in span_datas:
                output = {
                    "type": "span",
                    "name": span_data.name,
                    "service": span_data.service,
                    "function": span_data.function,
                    "start_time": span_data.start_time,
                    "duration_ms": span_data.duration_ms,
                    "status": span_data.status,
                }
                if span_data.error_message:
                    output["error"] = span_data.error_message
                if span_data.attributes:
                    output["attributes"] = span_data.attributes
                print(json.dumps(output), file=sys.stdout)
                sys.stdout.flush()

    def shutdown(self) -> None:
        pass


class TracingState:
    """Global tracing state singleton."""

    _instance: Optional[TracingState] = None
    _lock = threading.Lock()

    def __init__(self):
        self.config = TracerConfig()
        self._tracer: Optional[Tracer] = None
        self._enabled = False
        self._console_exporter = ConsoleSpanExporter2(enabled=True)
        self._spans_buffer: list[SpanData] = []
        self._span_count = 0

    @classmethod
    def get_instance(cls) -> TracingState:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance


def _create_sampler(config: TracerConfig) -> Sampler:
    """Create OpenTelemetry sampler based on config."""
    if not _OPENTELEMETRY_AVAILABLE:
        return None

    strategy = config.sampling_strategy

    if strategy == SamplerType.ALWAYS_ON:
        return ALWAYS_ON
    elif strategy == SamplerType.ALWAYS_OFF:
        return ALWAYS_OFF
    elif strategy == SamplerType.PROBABILISTIC:
        return TraceIdRatioBased(config.sampling_rate)
    else:  # ERROR_ONLY - default behavior
        # Use parent-based for error-only sampling
        return ParentBased(ALWAYS_ON)


def configure_tracing(config: Optional[TracerConfig] = None) -> bool:
    """Initialize and configure OpenTelemetry tracing.

    Args:
        config: Optional TracerConfig. If not provided, uses defaults.

    Returns:
        True if tracing initialized successfully, False otherwise.
    """
    state = TracingState.get_instance()

    if config is not None:
        state.config = config

    if not state.config.enabled:
        state._enabled = False
        return False

    if not _OPENTELEMETRY_AVAILABLE:
        print(
            "[tracing] OpenTelemetry not installed. Using lightweight mode.",
            file=sys.stderr,
        )
        state._enabled = True
        return True

    try:
        # Create resource with service name
        resource = Resource.create(
            {
                SERVICE_NAME: state.config.service_name,
            }
        )

        # Create sampler
        sampler = _create_sampler(state.config)

        # Create provider
        provider = TracerProvider(resource=resource, sampler=sampler)

        # Register provider
        trace.set_tracer_provider(provider)

        # Get tracer
        state._tracer = trace.get_tracer(state.config.service_name)

        # Add console exporter if enabled
        if state.config.export_to_console:
            exporter = ConsoleSpanExporter()
            processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(processor)

        state._enabled = True
        print(
            f"[tracing] Initialized for service: {state.config.service_name}",
            file=sys.stderr,
        )
        return True

    except Exception as e:
        print(f"[tracing] Failed to initialize: {e}", file=sys.stderr)
        state._enabled = False
        return False


def get_tracer(service_name: Optional[str] = None) -> Optional[Tracer]:
    """Get or create the global tracer instance.

    Args:
        service_name: Optional service name override.

    Returns:
        OpenTelemetry Tracer or None.
    """
    state = TracingState.get_instance()

    if not state._enabled:
        configure_tracing()

    if service_name and state._tracer:
        return trace.get_tracer(service_name)

    return state._tracer


def _should_sample(config: TracerConfig) -> bool:
    """Determine if current call should be sampled."""
    if config.sampling_strategy == SamplerType.ALWAYS_ON:
        return True
    if config.sampling_strategy == SamplerType.ALWAYS_OFF:
        return False
    if config.sampling_strategy == SamplerType.PROBABILISTIC:
        return random.random() < config.sampling_rate
    # ERROR_ONLY - default, sample if in error context
    return True


@contextmanager
def trace_span(
    name: str,
    service: str = "n-xyme-mind",
    function: Optional[str] = None,
):
    """Context manager for creating custom spans.

    Args:
        name: Span name
        service: Service name
        function: Function being traced

    Yields:
        Span object
    """
    state = TracingState.get_instance()
    config = state.config

    if not _should_sample(config):
        yield None
        return

    start_time = time.time()
    span_data = SpanData(
        name=name,
        service=service,
        function=function or name,
        start_time=start_time,
        attributes={},
    )

    # Get OTel span if available
    span = None
    if state._tracer and _OPENTELEMETRY_AVAILABLE:
        with state._tracer.start_as_current_span(name) as otel_span:
            span = otel_span
            otel_span.set_attribute("service.name", service)
            otel_span.set_attribute("function.name", function or name)
            try:
                yield otel_span
            except Exception as e:
                otel_span.set_status(Status(StatusCode.ERROR, str(e)))
                span_data.status = "error"
                span_data.error_message = str(e)
                raise
    else:
        # Lightweight mode
        try:
            yield span_data
        except Exception as e:
            span_data.status = "error"
            span_data.error_message = str(e)
            raise
        finally:
            end_time = time.time()
            span_data.end_time = end_time
            span_data.duration_ms = (end_time - start_time) * 1000
            state._console_exporter.export([span_data])


def _create_trace_decorator(
    service: str,
    function: str,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Create a trace decorator for a specific service/function."""

    P = ParamSpec("P")
    R = TypeVar("R")

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            state = TracingState.get_instance()
            config = state.config

            # Check if we should sample this call
            if not _should_sample(config):
                return func(*args, **kwargs)

            start_time = time.time()
            span_data = SpanData(
                name=function,
                service=service,
                function=function,
                start_time=start_time,
                attributes={
                    "args": str(args)[:200],  # Truncate long args
                    "kwargs": str(kwargs)[:200],
                },
            )

            if state._tracer and _OPENTELEMETRY_AVAILABLE:
                with state._tracer.start_as_current_span(function) as span:
                    span.set_attribute("service.name", service)
                    span.set_attribute("function.name", function)
                    try:
                        result = func(*args, **kwargs)
                        span_data.attributes["result"] = str(result)[:100]
                        return result
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span_data.status = "error"
                        span_data.error_message = str(e)
                        raise
            else:
                # Lightweight mode
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span_data.status = "error"
                    span_data.error_message = str(e)
                    raise
                finally:
                    end_time = time.time()
                    span_data.end_time = end_time
                    span_data.duration_ms = (end_time - start_time) * 1000
                    state._console_exporter.export([span_data])

        return wrapper  # type: ignore

    return decorator


def trace(
    service: Optional[str] = None,
    function: Optional[str] = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to trace a function with OpenTelemetry.

    Args:
        service: Service name (defaults to config.service_name)
        function: Function name (defaults to wrapped function name)

    Usage:
        @trace(service="memory_core", function="search_memories")
        def search_memories(query, limit=10):
            ...
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        svc = service or TracingState.get_instance().config.service_name
        fn = function or func.__name__
        return _create_trace_decorator(svc, fn)(func)

    return decorator


# =============================================================================
# Traceable wrapper functions for brain packages
# =============================================================================


def create_traceable_search_memories():
    """Create a traceable wrapper for memory_core.search_memories."""
    from packages.memory_store import search as memory_search

    @trace(service="memory_core", function="search_memories")
    def traced_search_memories(query: str, limit: int = 10, **kwargs):
        return memory_search(query, limit=limit, **kwargs)

    return traced_search_memories


def create_traceable_memory_write():
    """Create a traceable wrapper for memory_core.memory_write."""
    from packages.memory_store import memory_manager

    @trace(service="memory_core", function="memory_write")
    def traced_memory_write(content: str, kind: str = "memory", **kwargs):
        return memory_manager.write(content, kind=kind, **kwargs)

    return traced_memory_write


def create_traceable_route_task():
    """Create a traceable wrapper for learning_engine.route_task."""
    from packages.learning_engine import route_task as le_route_task

    @trace(service="learning_engine", function="route_task")
    def traced_route_task(task_description: str, level: int = 1):
        return le_route_task(task_description, level)

    return traced_route_task


def create_traceable_record_outcome():
    """Create a traceable wrapper for learning_engine.record_outcome."""
    from packages.learning_engine import record_outcome as le_record_outcome

    @trace(service="learning_engine", function="record_outcome")
    def traced_record_outcome(
        agent: str, level: int, success: bool, latency_ms: float = 0
    ):
        return le_record_outcome(agent, level, success, latency_ms)

    return traced_record_outcome


def create_traceable_intelligence_route():
    """Create a traceable wrapper for intelligence.route."""
    from packages.intelligence import route as intel_route

    @trace(service="intelligence", function="route")
    async def traced_route(task_description: str):
        return await intel_route(task_description)

    return traced_route


def create_traceable_score_complexity():
    """Create a traceable wrapper for intelligence.score_complexity."""
    from packages.intelligence import score_complexity as intel_score

    @trace(service="intelligence", function="score_complexity")
    def traced_score_complexity(task_description: str):
        return intel_score(task_description)

    return traced_score_complexity


# =============================================================================
# Initialization
# =============================================================================


def _auto_init():
    """Auto-initialize tracing on module import."""
    # Check for environment variable override
    enabled = os.environ.get("NX_YME_TRACING_ENABLED", "true").lower()
    if enabled in ("1", "true", "yes"):
        configure_tracing()


# Auto-init on import
_auto_init()

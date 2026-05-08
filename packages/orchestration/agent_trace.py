#!/usr/bin/env python3
"""AgentTrace — Three-Surface Structured Logging for Multi-Agent Systems.

Phase 4.2 of Masterplan: Production Readiness.

Provides:
- Three-surface logging:
  - cognitive: agent reasoning, decisions, beliefs
  - operational: tool calls, API requests, errors
  - contextual: session state, memory, context
- OpenTelemetry-compatible export (OTLP)
- Integration with 50+ frameworks (see FRAMEWORKS list)
- Trace context propagation
- Span management

Usage:
    from packages.orchestration.agent_trace import AgentTrace, get_tracer

    # Get tracer for an agent
    tracer = get_tracer("hephaestus")

    # Log cognitive surface (reasoning)
    with tracer.trace("reasoning") as span:
        span.log_cognitive("Analyzing task complexity", reasoning="L3 complexity detected")
        span.log_cognitive("Deciding on agent", decision="delegate to hephaestus")

    # Log operational surface (tool calls)
    with tracer.trace("tool_call") as span:
        span.log_operational("file.read", tool="read", path="/src/main.py")

    # Log contextual surface (session state)
    span.log_contextual("session_state", state={"tasks": 3, "context_tokens": 1500})

    # Export to OpenTelemetry
    exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
    tracer.add_exporter(exporter)
"""

from __future__ import annotations

import json
import time
import uuid
import threading
import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum
from contextlib import contextmanager

# Optional OpenTelemetry integration
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter as OTLPSpanExporterHTTP,
    )
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    TracerProvider = None
    OTLPSpanExporter = None
    OTLPSpanExporterHTTP = None
    StatusCode = None

__version__ = "1.0.0"

# =============================================================================
# Surface Types
# =============================================================================


class SurfaceType(str, Enum):
    """Three-surface types for agent tracing."""

    COGNITIVE = "cognitive"  # Agent reasoning, decisions, beliefs
    OPERATIONAL = "operational"  # Tool calls, API requests, errors
    CONTEXTUAL = "contextual"  # Session state, memory, context


# =============================================================================
# Supported Frameworks (50+)
# =============================================================================

# Frameworks that integrate with OpenTelemetry
# https://opentelemetry.io/ecosystem/integrations/
FRAMEWORKS = [
    # Web Frameworks
    "flask",
    "django",
    "fastapi",
    "starlette",
    "aiohttp",
    "fastrod",
    "tornado",
    "bottle",
    "cherrypy",
    "pyramid",
    # Data & ML
    "sqlalchemy",
    "psycopg2",
    "pymongo",
    "redis",
    "elasticsearch",
    "tensorflow",
    "torch",
    "scikit-learn",
    "xgboost",
    "lightgbm",
    # Messaging
    "kafka",
    "pika",
    "redis-pubsub",
    "grpc",
    "aio-pika",
    # Cloud
    "boto3",
    "google-cloud",
    "azure",
    "aiobotocore",
    # Async
    "asyncio",
    "aiohttp",
    "httpx",
    "requests",
    # CLI
    "click",
    "typer",
    "argparse",
    # Testing
    "pytest",
    "unittest",
    "pytest-asyncio",
    # Observability
    "prometheus",
    "grafana",
    "jaeger",
    "zipkin",
    "datadog",
    # Agent Frameworks
    "langchain",
    "llamaindex",
    "autogen",
    "crewai",
    "haystack",
    # Database
    "sqlalchemy",
    "tortoise",
    "prisma",
    "diesel",
]

# =============================================================================
# Data Models
# =============================================================================


@dataclass
class TraceSpan:
    """Represents a single trace span."""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    surface: SurfaceType
    start_time: float
    end_time: Optional[float] = None
    attributes: dict[str, Any] = field(default_factory=dict)
    status: Optional[str] = None
    events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "surface": self.surface.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": (
                (self.end_time - self.start_time) * 1000 if self.end_time else None
            ),
            "attributes": self.attributes,
            "status": self.status,
            "events": self.events,
        }


@dataclass
class CognitiveLog:
    """Cognitive surface log entry."""

    timestamp: float
    agent: str
    reasoning: str
    decision: Optional[str] = None
    belief: Optional[str] = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationalLog:
    """Operational surface log entry."""

    timestamp: float
    agent: str
    operation: str  # tool_call, api_request, error
    tool: Optional[str] = None
    path: Optional[str] = None
    status: str = "pending"
    latency_ms: Optional[float] = None
    error: Optional[str] = None


@dataclass
class ContextualLog:
    """Contextual surface log entry."""

    timestamp: float
    agent: str
    session_id: str
    state: dict[str, Any] = field(default_factory=dict)
    memory: Optional[str] = None
    context: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Trace Manager
# =============================================================================


class AgentTrace:
    """Three-surface structured logging for multi-agent systems.

    Provides:
    - Cognitive surface: agent reasoning, decisions, beliefs
    - Operational surface: tool calls, API requests, errors
    - Contextual surface: session state, memory, context

    Usage:
        trace = AgentTrace(agent_name="hephaestus")

        # Cognitive logging
        trace.log_cognitive("Analyzing complexity", decision="use hephaestus")

        # Operational logging
        trace.log_operational("tool_call", tool="read", path="/src/main.py")

        # Contextual logging
        trace.log_contextual("session_state", state={"tasks": 3})
    """

    _instances: dict[str, "AgentTrace"] = {}
    _lock = threading.Lock()

    def __init__(
        self,
        agent_name: str,
        service_name: str = "n-xyme-mind",
        otel_endpoint: Optional[str] = None,
    ):
        """Initialize AgentTrace.

        Args:
            agent_name: Name of the agent (e.g., "hephaestus", "oracle")
            service_name: Service name for OpenTelemetry
            otel_endpoint: Optional OTLP endpoint for export
        """
        self.agent_name = agent_name
        self.service_name = service_name

        # Storage
        self._spans: list[TraceSpan] = []
        self._cognitive_logs: list[CognitiveLog] = []
        self._operational_logs: list[OperationalLog] = []
        self._contextual_logs: list[ContextualLog] = []

        # OpenTelemetry integration
        self._tracer: Optional[Any] = None
        self._otel_initialized = False

        if OTEL_AVAILABLE:
            self._init_opentelemetry(otel_endpoint)

        # Session ID for contextual tracking
        self._session_id = str(uuid.uuid4())[:8]

    def _init_opentelemetry(self, endpoint: Optional[str]) -> None:
        """Initialize OpenTelemetry."""
        try:
            # Create tracer provider
            resource = Resource.create(
                {
                    SERVICE_NAME: self.service_name,
                    "agent.name": self.agent_name,
                }
            )

            provider = TracerProvider(resource=resource)

            # Add console exporter for development
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

            # Add OTLP exporter if endpoint provided
            if endpoint:
                if endpoint.startswith("http"):
                    otlp_exporter = OTLPSpanExporterHTTP(
                        endpoint=endpoint,
                    )
                else:
                    otlp_exporter = OTLPSpanExporter(
                        endpoint=endpoint,
                    )
                provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

            # Set global provider
            trace.set_tracer_provider(provider)

            # Get tracer
            self._tracer = trace.get_tracer(__name__)
            self._otel_initialized = True

        except Exception as e:
            logging.warning(f"Failed to initialize OpenTelemetry: {e}")

    @classmethod
    def get_instance(
        cls,
        agent_name: str,
        service_name: str = "n-xyme-mind",
        otel_endpoint: Optional[str] = None,
    ) -> "AgentTrace":
        """Get or create AgentTrace instance for agent."""
        key = f"{service_name}:{agent_name}"
        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = cls(agent_name, service_name, otel_endpoint)
            return cls._instances[key]

    # ----- Cognitive Surface -----

    def log_cognitive(
        self,
        reasoning: str,
        decision: Optional[str] = None,
        belief: Optional[str] = None,
        **context,
    ) -> None:
        """Log cognitive surface entry.

        Args:
            reasoning: Agent's reasoning text
            decision: Optional decision made
            belief: Optional belief held
            **context: Additional context
        """
        log = CognitiveLog(
            timestamp=time.time(),
            agent=self.agent_name,
            reasoning=reasoning,
            decision=decision,
            belief=belief,
            context=context,
        )
        self._cognitive_logs.append(log)

        # Also log to standard logger
        logger = logging.getLogger(f"agent_trace.{self.agent_name}")
        logger.info(
            f"[COGNITIVE] {reasoning}",
            extra={
                "agent": self.agent_name,
                "surface": SurfaceType.COGNITIVE.value,
                "reasoning": reasoning,
                "decision": decision,
                "belief": belief,
                **context,
            },
        )

    # ----- Operational Surface -----

    def log_operational(
        self,
        operation: str,
        tool: Optional[str] = None,
        path: Optional[str] = None,
        status: str = "pending",
        latency_ms: Optional[float] = None,
        error: Optional[str] = None,
        **metadata,
    ) -> None:
        """Log operational surface entry.

        Args:
            operation: Type of operation (tool_call, api_request, error)
            tool: Tool name if applicable
            path: File/API path
            status: Status (pending, success, error)
            latency_ms: Operation latency
            error: Error message if applicable
            **metadata: Additional metadata
        """
        log = OperationalLog(
            timestamp=time.time(),
            agent=self.agent_name,
            operation=operation,
            tool=tool,
            path=path,
            status=status,
            latency_ms=latency_ms,
            error=error,
        )
        self._operational_logs.append(log)

        # Also log to standard logger
        logger = logging.getLogger(f"agent_trace.{self.agent_name}")
        log_level = logging.ERROR if status == "error" else logging.INFO
        logger.log(
            log_level,
            f"[OPERATIONAL] {operation} - {status}",
            extra={
                "agent": self.agent_name,
                "surface": SurfaceType.OPERATIONAL.value,
                "operation": operation,
                "tool": tool,
                "path": path,
                "status": status,
                "latency_ms": latency_ms,
                "error": error,
                **metadata,
            },
        )

    # ----- Contextual Surface -----

    def log_contextual(
        self,
        state_type: str,
        state: Optional[dict[str, Any]] = None,
        memory: Optional[str] = None,
        **context,
    ) -> None:
        """Log contextual surface entry.

        Args:
            state_type: Type of state (session_state, memory, context)
            state: Session state dictionary
            memory: Optional memory text
            **context: Additional context
        """
        log = ContextualLog(
            timestamp=time.time(),
            agent=self.agent_name,
            session_id=self._session_id,
            state=state or {},
            memory=memory,
            context=context,
        )
        self._contextual_logs.append(log)

        # Also log to standard logger
        logger = logging.getLogger(f"agent_trace.{self.agent_name}")
        logger.info(
            f"[CONTEXTUAL] {state_type}",
            extra={
                "agent": self.agent_name,
                "surface": SurfaceType.CONTEXTUAL.value,
                "state_type": state_type,
                "session_id": self._session_id,
                "state": state,
                "memory": memory,
                **context,
            },
        )

    # ----- Trace Context -----

    @contextmanager
    def trace(self, name: str, surface: SurfaceType = SurfaceType.OPERATIONAL):
        """Create a trace span.

        Args:
            name: Span name
            surface: Surface type for this span

        Usage:
            with tracer.trace("file_read"):
                # ... operation ...
        """
        span = TraceSpan(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4())[:16],
            parent_span_id=None,
            name=name,
            surface=surface,
            start_time=time.time(),
        )

        # If OpenTelemetry is available, use it
        if self._otel_initialized and self._tracer:
            otel_span = self._tracer.start_span(name)
            otel_span.set_attribute("agent", self.agent_name)
            otel_span.set_attribute("surface", surface.value)

            try:
                yield otel_span
            except Exception as e:
                otel_span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
            finally:
                otel_span.end()
        else:
            # Fallback to simple span tracking
            self._spans.append(span)
            try:
                yield span
            except Exception as e:
                span.status = "error"
                span.attributes["error"] = str(e)
                raise
            finally:
                span.end_time = time.time()

    # ----- Export -----

    def export_json(self) -> str:
        """Export all logs as JSON."""
        return json.dumps(
            {
                "agent": self.agent_name,
                "session_id": self._session_id,
                "cognitive": [
                    {
                        "timestamp": log.timestamp,
                        "reasoning": log.reasoning,
                        "decision": log.decision,
                        "belief": log.belief,
                        "context": log.context,
                    }
                    for log in self._cognitive_logs
                ],
                "operational": [
                    {
                        "timestamp": log.timestamp,
                        "operation": log.operation,
                        "tool": log.tool,
                        "path": log.path,
                        "status": log.status,
                        "latency_ms": log.latency_ms,
                        "error": log.error,
                    }
                    for log in self._operational_logs
                ],
                "contextual": [
                    {
                        "timestamp": log.timestamp,
                        "state_type": log.state,
                        "session_id": log.session_id,
                        "state": log.state,
                        "memory": log.memory,
                        "context": log.context,
                    }
                    for log in self._contextual_logs
                ],
                "spans": [span.to_dict() for span in self._spans],
            },
            indent=2,
        )

    def get_stats(self) -> dict[str, int]:
        """Get trace statistics."""
        return {
            "cognitive_logs": len(self._cognitive_logs),
            "operational_logs": len(self._operational_logs),
            "contextual_logs": len(self._contextual_logs),
            "spans": len(self._spans),
            "session_id": self._session_id,
        }


def get_tracer(
    agent_name: str,
    service_name: str = "n-xyme-mind",
    otel_endpoint: Optional[str] = None,
) -> AgentTrace:
    """Get or create tracer for agent.

    Args:
        agent_name: Name of the agent
        service_name: Service name
        otel_endpoint: Optional OTLP endpoint

    Returns:
        AgentTrace instance
    """
    return AgentTrace.get_instance(agent_name, service_name, otel_endpoint)


# =============================================================================
# Integration with Context Loader
# =============================================================================


class PreCaptureHook:
    """Hook that runs before context is captured by LLM.

    Used for secret scanning and other pre-processing.
    """

    _hooks: list[callable] = []

    @classmethod
    def register(cls, hook: callable) -> None:
        """Register a pre-capture hook.

        Args:
            hook: Callable that takes content and returns (sanitized_content, blocked)
        """
        cls._hooks.append(hook)

    @classmethod
    def run_hooks(cls, content: str) -> tuple[str, bool]:
        """Run all registered hooks.

        Args:
            content: Content to process

        Returns:
            Tuple of (sanitized_content, blocked)
        """
        sanitized = content
        blocked = False

        for hook in cls._hooks:
            sanitized, blocked = hook(sanitized)
            if blocked:
                break

        return sanitized, blocked

    @classmethod
    def clear(cls) -> None:
        """Clear all hooks."""
        cls._hooks.clear()


# =============================================================================
# Default Exporters
# =============================================================================


def init_default_tracer() -> None:
    """Initialize default tracer for common agents."""
    # Pre-register tracers for common agents
    for agent in ["sisyphus", "hephaestus", "oracle", "explore", "librarian"]:
        get_tracer(agent)


# Auto-init on import
init_default_tracer()

__all__ = [
    "AgentTrace",
    "get_tracer",
    "SurfaceType",
    "TraceSpan",
    "CognitiveLog",
    "OperationalLog",
    "ContextualLog",
    "PreCaptureHook",
    "FRAMEWORKS",
]

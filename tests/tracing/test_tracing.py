"""Tests for distributed tracing module."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from src.tracing.tracer import (
    DistributedTracer,
    Span,
    SpanStatus,
    Trace,
    _generate_span_id,
    _generate_trace_id,
    get_tracer,
    reset_tracer,
)
from src.tracing.context import (
    TraceContext,
    extract_trace_context,
    get_current_trace_context,
    inject_trace_context,
    set_current_trace_context,
    clear_current_trace_context,
)


@pytest.fixture(autouse=True)
def reset_tracer_fixture():
    reset_tracer()
    yield
    reset_tracer()


@pytest.fixture
def tracer(tmp_path):
    return DistributedTracer(export_dir=tmp_path / "traces")


class TestTraceIdGeneration:
    def test_trace_id_is_32_hex_chars(self):
        trace_id = _generate_trace_id()
        assert len(trace_id) == 48
        assert all(c in "0123456789abcdef" for c in trace_id)

    def test_trace_ids_are_unique(self):
        ids = {_generate_trace_id() for _ in range(100)}
        assert len(ids) == 100

    def test_span_id_is_16_hex_chars(self):
        span_id = _generate_span_id()
        assert len(span_id) == 16
        assert all(c in "0123456789abcdef" for c in span_id)

    def test_span_ids_are_unique(self):
        ids = {_generate_span_id() for _ in range(100)}
        assert len(ids) == 100


class TestSpan:
    def test_span_creation(self):
        span = Span(
            trace_id="abc123",
            span_id="def456",
            name="test-span",
            parent_span_id=None,
            start_time=1000.0,
        )
        assert span.trace_id == "abc123"
        assert span.span_id == "def456"
        assert span.name == "test-span"
        assert span.parent_span_id is None
        assert span.is_active
        assert span.end_time is None

    def test_span_duration(self):
        span = Span(
            trace_id="abc",
            span_id="def",
            name="test",
            parent_span_id=None,
            start_time=1000.0,
            end_time=1001.5,
        )
        assert span.duration_seconds == 1.5
        assert span.duration_ms == 1500.0

    def test_span_duration_none_when_active(self):
        span = Span(
            trace_id="abc",
            span_id="def",
            name="test",
            parent_span_id=None,
            start_time=1000.0,
        )
        assert span.duration_seconds is None
        assert span.duration_ms is None

    def test_span_add_event(self):
        span = Span(
            trace_id="abc",
            span_id="def",
            name="test",
            parent_span_id=None,
            start_time=1000.0,
        )
        span.add_event("delegation_started", {"agent": "hephaestus"})
        assert len(span.events) == 1
        assert span.events[0].name == "delegation_started"
        assert span.events[0].attributes == {"agent": "hephaestus"}

    def test_span_to_dict(self):
        span = Span(
            trace_id="abc",
            span_id="def",
            name="test",
            parent_span_id=None,
            start_time=1000.0,
            end_time=1001.0,
            status=SpanStatus.OK,
            attributes={"agent": "hephaestus"},
        )
        span.add_event("test_event")
        d = span.to_dict()
        assert d["trace_id"] == "abc"
        assert d["span_id"] == "def"
        assert d["name"] == "test"
        assert d["duration_seconds"] == 1.0
        assert d["status"] == "ok"
        assert d["attributes"] == {"agent": "hephaestus"}
        assert len(d["events"]) == 1


class TestTrace:
    def test_trace_creation(self):
        trace = Trace(
            trace_id="abc",
            name="test-trace",
            start_time=1000.0,
        )
        assert trace.trace_id == "abc"
        assert trace.name == "test-trace"
        assert len(trace.spans) == 0

    def test_trace_duration(self):
        trace = Trace(
            trace_id="abc",
            name="test-trace",
            start_time=1000.0,
        )
        trace.spans.append(
            Span(
                trace_id="abc",
                span_id="s1",
                name="span1",
                parent_span_id=None,
                start_time=1000.0,
                end_time=1002.0,
            )
        )
        trace.spans.append(
            Span(
                trace_id="abc",
                span_id="s2",
                name="span2",
                parent_span_id="s1",
                start_time=1000.5,
                end_time=1001.5,
            )
        )
        assert trace.duration_seconds == 2.0
        assert trace.duration_ms == 2000.0

    def test_trace_to_dict(self):
        trace = Trace(
            trace_id="abc",
            name="test-trace",
            start_time=1000.0,
        )
        d = trace.to_dict()
        assert d["trace_id"] == "abc"
        assert d["name"] == "test-trace"
        assert d["span_count"] == 0
        assert d["spans"] == []


class TestDistributedTracer:
    def test_start_trace(self, tracer):
        trace_id = tracer.start_trace("test-operation")
        assert trace_id is not None
        trace = tracer.get_trace(trace_id)
        assert trace is not None
        assert trace.name == "test-operation"

    def test_start_span_creates_root_span(self, tracer):
        trace_id = tracer.start_trace("test")
        span = tracer.start_span("root-span", trace_id=trace_id)
        assert span.trace_id == trace_id
        assert span.name == "root-span"
        assert span.parent_span_id is None

        trace = tracer.get_trace(trace_id)
        assert trace.root_span_id == span.span_id

    def test_start_span_with_parent(self, tracer):
        trace_id = tracer.start_trace("test")
        parent = tracer.start_span("parent", trace_id=trace_id)
        child = tracer.start_span(
            "child", trace_id=trace_id, parent_span_id=parent.span_id
        )

        assert child.parent_span_id == parent.span_id
        assert child.trace_id == trace_id

    def test_end_span(self, tracer):
        trace_id = tracer.start_trace("test")
        span = tracer.start_span("test-span", trace_id=trace_id)
        time.sleep(0.01)
        tracer.end_span(span, status=SpanStatus.OK)

        assert span.end_time is not None
        assert span.status == SpanStatus.OK
        assert span.duration_seconds > 0
        assert not span.is_active

    def test_end_span_error_status(self, tracer):
        trace_id = tracer.start_trace("test")
        span = tracer.start_span("failing-span", trace_id=trace_id)
        tracer.end_span(span, status=SpanStatus.ERROR)

        assert span.status == SpanStatus.ERROR

    def test_add_event_to_span(self, tracer):
        trace_id = tracer.start_trace("test")
        span = tracer.start_span("test-span", trace_id=trace_id)
        tracer.add_event(
            span, "delegation_started", {"agent": "hephaestus", "model": "minimax"}
        )
        tracer.add_event(span, "delegation_completed", {"tokens": 5000})

        assert len(span.events) == 2
        assert span.events[0].name == "delegation_started"
        assert span.events[0].attributes["agent"] == "hephaestus"
        assert span.events[1].name == "delegation_completed"
        assert span.events[1].attributes["tokens"] == 5000

    def test_parent_child_span_relationship(self, tracer):
        trace_id = tracer.start_trace("delegation-flow")
        root = tracer.start_span("orchestrator", trace_id=trace_id)
        worker = tracer.start_span(
            "hephaestus-worker", trace_id=trace_id, parent_span_id=root.span_id
        )
        tracer.end_span(worker)
        tracer.end_span(root)

        trace = tracer.get_trace(trace_id)
        assert len(trace.spans) == 2

        span_map = {s.span_id: s for s in trace.spans}
        assert span_map[worker.span_id].parent_span_id == root.span_id
        assert span_map[root.span_id].parent_span_id is None

    def test_auto_trace_creation(self, tracer):
        span = tracer.start_span("auto-span")
        assert span.trace_id is not None
        trace = tracer.get_trace(span.trace_id)
        assert trace is not None
        assert trace.name == "auto-trace"

    def test_get_nonexistent_trace(self, tracer):
        assert tracer.get_trace("nonexistent") is None

    def test_get_all_traces(self, tracer):
        tracer.start_trace("trace-1")
        tracer.start_trace("trace-2")
        tracer.start_trace("trace-3")

        traces = tracer.get_all_traces()
        assert len(traces) == 3

    def test_export_traces_to_json(self, tracer, tmp_path):
        trace_id = tracer.start_trace("export-test")
        span = tracer.start_span("span-1", trace_id=trace_id)
        tracer.add_event(span, "test-event")
        tracer.end_span(span)

        output_path = tmp_path / "exported_traces.json"
        result_path = tracer.export_traces(output_path=output_path)

        assert result_path == output_path
        assert output_path.exists()

        data = json.loads(output_path.read_text())
        assert data["trace_count"] == 1
        assert len(data["traces"]) == 1
        assert data["traces"][0]["name"] == "export-test"
        assert data["traces"][0]["span_count"] == 1

    def test_export_trace_to_console(self, tracer):
        trace_id = tracer.start_trace("console-test")
        tracer.start_span("span-1", trace_id=trace_id)

        output = tracer.export_trace_to_console(trace_id)
        data = json.loads(output)
        assert data["name"] == "console-test"

    def test_export_nonexistent_trace(self, tracer):
        output = tracer.export_trace_to_console("nonexistent")
        assert "not found" in output

    def test_clear_traces(self, tracer):
        tracer.start_trace("trace-1")
        tracer.start_trace("trace-2")
        tracer.clear_traces()

        assert len(tracer.get_all_traces()) == 0
        assert tracer.get_active_span_count() == 0

    def test_active_span_count(self, tracer):
        trace_id = tracer.start_trace("test")
        span1 = tracer.start_span("span-1", trace_id=trace_id)
        span2 = tracer.start_span("span-2", trace_id=trace_id)

        assert tracer.get_active_span_count() == 2

        tracer.end_span(span1)
        assert tracer.get_active_span_count() == 1

        tracer.end_span(span2)
        assert tracer.get_active_span_count() == 0

    def test_span_attributes(self, tracer):
        trace_id = tracer.start_trace("test")
        span = tracer.start_span(
            "test-span",
            trace_id=trace_id,
            attributes={
                "agent_type": "hephaestus",
                "model": "minimax-m2.5-free",
                "level": "L3",
            },
        )

        assert span.attributes["agent_type"] == "hephaestus"
        assert span.attributes["model"] == "minimax-m2.5-free"
        assert span.attributes["level"] == "L3"

    def test_invalid_trace_id_raises(self, tracer):
        with pytest.raises(ValueError, match="not found"):
            tracer.start_span("orphan", trace_id="nonexistent-trace")


class TestTraceContext:
    def test_tracecontext_creation(self):
        ctx = TraceContext(
            trace_id="a" * 32,
            span_id="b" * 16,
            is_sampled=True,
        )
        assert ctx.trace_id == "a" * 32
        assert ctx.span_id == "b" * 16
        assert ctx.is_sampled

    def test_traceparent_generation(self):
        ctx = TraceContext(
            trace_id="a" * 32,
            span_id="b" * 16,
            is_sampled=True,
        )
        expected = f"00-{'a' * 32}-{'b' * 16}-01"
        assert ctx.traceparent == expected

    def test_traceparent_not_sampled(self):
        ctx = TraceContext(
            trace_id="a" * 32,
            span_id="b" * 16,
            is_sampled=False,
        )
        assert ctx.traceparent.endswith("-00")

    def test_traceparent_parsing(self):
        traceparent = f"00-{'a' * 32}-{'b' * 16}-01"
        ctx = TraceContext.from_traceparent(traceparent)

        assert ctx.trace_id == "a" * 32
        assert ctx.span_id == "b" * 16
        assert ctx.is_sampled

    def test_traceparent_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid traceparent format"):
            TraceContext.from_traceparent("invalid-format")

    def test_traceparent_invalid_version(self):
        with pytest.raises(ValueError, match="Unsupported traceparent version"):
            TraceContext.from_traceparent(f"01-{'a' * 32}-{'b' * 16}-01")

    def test_traceparent_invalid_trace_id_length(self):
        with pytest.raises(ValueError, match="Invalid trace_id length"):
            TraceContext.from_traceparent(f"00-{'a' * 16}-{'b' * 16}-01")

    def test_traceparent_invalid_span_id_length(self):
        with pytest.raises(ValueError, match="Invalid span_id length"):
            TraceContext.from_traceparent(f"00-{'a' * 32}-{'b' * 8}-01")

    def test_to_headers(self):
        ctx = TraceContext(
            trace_id="a" * 32,
            span_id="b" * 16,
        )
        headers = ctx.to_headers()
        assert "traceparent" in headers
        assert headers["traceparent"] == ctx.traceparent

    def test_from_headers(self):
        headers = {"traceparent": f"00-{'a' * 32}-{'b' * 16}-01"}
        ctx = TraceContext.from_headers(headers)
        assert ctx is not None
        assert ctx.trace_id == "a" * 32

    def test_from_headers_no_traceparent(self):
        ctx = TraceContext.from_headers({})
        assert ctx is None

    def test_to_dict(self):
        ctx = TraceContext(
            trace_id="a" * 32,
            span_id="b" * 16,
            is_sampled=True,
        )
        d = ctx.to_dict()
        assert d["trace_id"] == "a" * 32
        assert d["span_id"] == "b" * 16
        assert d["is_sampled"] is True
        assert "traceparent" in d


class TestContextPropagation:
    def test_inject_and_get_context(self):
        headers = inject_trace_context(
            trace_id="a" * 32,
            span_id="b" * 16,
        )
        assert "traceparent" in headers

        ctx = get_current_trace_context()
        assert ctx is not None
        assert ctx.trace_id == "a" * 32
        assert ctx.span_id == "b" * 16

    def test_extract_context_from_headers(self):
        headers = {"traceparent": f"00-{'a' * 32}-{'b' * 16}-01"}
        ctx = extract_trace_context(headers)

        assert ctx is not None
        assert ctx.trace_id == "a" * 32
        assert ctx.span_id == "b" * 16

    def test_extract_context_no_headers(self):
        ctx = extract_trace_context({})
        assert ctx is None

    def test_clear_context(self):
        inject_trace_context(trace_id="a" * 32, span_id="b" * 16)
        assert get_current_trace_context() is not None

        clear_current_trace_context()
        assert get_current_trace_context() is None

    def test_context_propagation_roundtrip(self):
        trace_id = "c" * 32
        span_id = "d" * 16

        headers = inject_trace_context(trace_id=trace_id, span_id=span_id)
        extracted = extract_trace_context(headers)

        assert extracted is not None
        assert extracted.trace_id == trace_id
        assert extracted.span_id == span_id


class TestTracerSingleton:
    def test_get_tracer_returns_singleton(self):
        t1 = get_tracer()
        t2 = get_tracer()
        assert t1 is t2

    def test_reset_tracer(self):
        t1 = get_tracer()
        reset_tracer()
        t2 = get_tracer()
        assert t1 is not t2


class TestWorkerPoolIntegration:
    def test_trace_with_worker_pool_attributes(self, tracer):
        trace_id = tracer.start_trace("worker-pool-delegation")

        root = tracer.start_span(
            "pool-dispatcher",
            trace_id=trace_id,
            attributes={"component": "worker-pool"},
        )
        tracer.add_event(root, "task_submitted", {"task_id": "task-123"})

        worker = tracer.start_span(
            "hephaestus-worker",
            trace_id=trace_id,
            parent_span_id=root.span_id,
            attributes={
                "agent_type": "hephaestus",
                "model": "minimax-m2.5-free",
                "worker_id": "worker-hephaestus-0",
            },
        )
        tracer.add_event(worker, "task_started")
        tracer.add_event(worker, "task_completed", {"tokens": 5000, "cost": 0.01})
        tracer.end_span(worker, status=SpanStatus.OK)

        tracer.add_event(root, "task_dispatched", {"worker_id": "worker-hephaestus-0"})
        tracer.end_span(root, status=SpanStatus.OK)

        trace = tracer.get_trace(trace_id)
        assert len(trace.spans) == 2

        worker_span = next(s for s in trace.spans if s.name == "hephaestus-worker")
        assert worker_span.attributes["agent_type"] == "hephaestus"
        assert worker_span.attributes["model"] == "minimax-m2.5-free"
        assert worker_span.status == SpanStatus.OK
        assert len(worker_span.events) == 2

#!/usr/bin/env python3
"""Full delegation pipeline integration tests.

Tests the complete delegation pipeline:
- Enqueue task → worker processes → tracing records spans → sandbox validates → result recorded → learning analyzes
- Concurrent delegations don't corrupt state
- Circuit breaker trips and recovers
- Model fallback works when primary fails
"""

import json
import os
import tempfile
import threading
import time
from pathlib import Path

import pytest

from src.model_router.circuit_breaker import CircuitBreaker
from src.security.sandbox import FilesystemSandbox, AccessLevel
from src.tracing.tracer import DistributedTracer, SpanStatus
from src.state.db import StateDB
from src.state.models import Delegation, Result, AgentPerformance
from src.intelligence.learning import DelegationLearner
from src.message_queue.message_queue import MessageQueue, MessagePriority
from src.workers.agent_worker import AgentWorker, WorkerTask, WorkerState
from src.workers.pool import WorkerPool


@pytest.fixture
def temp_db_path(tmp_path):
    return tmp_path / "state.db"


@pytest.fixture
def state_db(temp_db_path):
    db = StateDB(temp_db_path)
    yield db
    db.close()


@pytest.fixture
def temp_mq_path(tmp_path):
    return tmp_path / "mq.db"


@pytest.fixture
def message_queue(temp_mq_path):
    mq = MessageQueue(
        db_path=temp_mq_path, visibility_timeout=1, max_retries=3, default_ttl=60
    )
    yield mq
    mq.close()


@pytest.fixture
def tracer(tmp_path):
    return DistributedTracer(export_dir=tmp_path / "traces")


@pytest.fixture
def sandbox(tmp_path):
    return FilesystemSandbox(workspace_root=tmp_path)


@pytest.fixture
def circuit_breaker(tmp_path):
    return CircuitBreaker(
        failure_threshold=3,
        reset_timeout=1,
        base_delay=0.1,
        max_delay=1.0,
        state_file=str(tmp_path / "circuit-breaker.json"),
    )


class TestFullDelegationPipeline:
    """Test the complete delegation pipeline end-to-end."""

    def test_enqueue_process_trace_sandbox_record_learn(
        self, state_db, message_queue, tracer, sandbox, tmp_path
    ):
        """Full pipeline: enqueue → worker processes → tracing records → sandbox validates → result recorded → learning analyzes."""
        sandbox.set_policy(
            "hephaestus",
            allowed_paths=[str(tmp_path)],
            access_level=AccessLevel.READ_WRITE,
        )

        trace_id = tracer.start_trace("full-delegation-pipeline")
        span_enqueue = tracer.start_span("enqueue_task", trace_id=trace_id)

        msg_id = message_queue.enqueue(
            {"task": "fix typo", "agent": "hephaestus", "level": "1"},
            priority=MessagePriority.HIGH,
        )
        assert msg_id is not None
        tracer.end_span(span_enqueue, status=SpanStatus.OK)

        span_process = tracer.start_span("process_task", trace_id=trace_id)
        msg = message_queue.dequeue("worker-1")
        assert msg is not None
        assert msg.status == "processing"
        tracer.end_span(span_process, status=SpanStatus.OK)

        span_sandbox = tracer.start_span("sandbox_validation", trace_id=trace_id)
        test_file = tmp_path / "test_output.txt"
        validation = sandbox.validate_path(str(test_file), "hephaestus")
        assert validation.allowed is True
        tracer.end_span(span_sandbox, status=SpanStatus.OK)

        span_record = tracer.start_span("record_result", trace_id=trace_id)
        delegation = Delegation(
            task_id=msg_id,
            agent="hephaestus",
            level="1",
            status="success",
            tokens=5000,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        )
        state_db.add_delegation(delegation)

        result = Result(
            task_id=msg_id,
            task_description="fix typo",
            agent="hephaestus",
            level="1",
            success=True,
            result_path=str(test_file),
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        )
        state_db.upsert_result(result)
        message_queue.ack(msg_id)
        tracer.end_span(span_record, status=SpanStatus.OK)

        span_learn = tracer.start_span("learning_analysis", trace_id=trace_id)
        learner = DelegationLearner(db=state_db)
        analysis = learner.analyze_delegations()
        assert analysis["total_delegations"] == 1
        assert analysis["success_rate"] == 100.0
        tracer.end_span(span_learn, status=SpanStatus.OK)

        trace = tracer.get_trace(trace_id)
        assert trace is not None
        assert len(trace.spans) == 5
        assert all(s.status == SpanStatus.OK for s in trace.spans)


class TestConcurrentDelegations:
    """Test concurrent delegations don't corrupt state."""

    def test_concurrent_delegations_no_corruption(self, state_db):
        """Multiple threads recording delegations simultaneously should not corrupt data."""
        num_threads = 10
        delegations_per_thread = 5
        barrier = threading.Barrier(num_threads)
        errors = []

        def record_delegations(thread_id):
            try:
                barrier.wait(timeout=5)
                for i in range(delegations_per_thread):
                    delegation = Delegation(
                        task_id=f"task-{thread_id}-{i}",
                        agent="hephaestus",
                        level="3",
                        status="success",
                        tokens=1000 + i,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
                    )
                    state_db.add_delegation(delegation)
            except Exception as e:
                errors.append(e)

        threads = []
        for t in range(num_threads):
            thread = threading.Thread(target=record_delegations, args=(t,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join(timeout=10)

        assert len(errors) == 0, f"Errors occurred: {errors}"

        all_delegations = state_db.get_delegations(limit=1000)
        assert len(all_delegations) == num_threads * delegations_per_thread

        task_ids = {d.task_id for d in all_delegations}
        assert len(task_ids) == num_threads * delegations_per_thread

    def test_concurrent_result_upserts(self, state_db):
        """Concurrent result upserts should not cause race conditions."""
        num_threads = 5
        barrier = threading.Barrier(num_threads)
        errors = []

        def upsert_results(thread_id):
            try:
                barrier.wait(timeout=5)
                for i in range(3):
                    result = Result(
                        task_id=f"shared-task-{i}",
                        task_description=f"task description {i}",
                        agent=f"agent-{thread_id}",
                        level="2",
                        success=True,
                        result_path=f"/tmp/result-{thread_id}-{i}",
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
                    )
                    state_db.upsert_result(result)
            except Exception as e:
                errors.append(e)

        threads = []
        for t in range(num_threads):
            thread = threading.Thread(target=upsert_results, args=(t,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join(timeout=10)

        assert len(errors) == 0
        all_results = state_db.get_all_results()
        assert len(all_results) == 3


class TestCircuitBreakerIntegration:
    """Test circuit breaker behavior in realistic scenarios."""

    def test_circuit_breaker_trips_after_threshold(self, circuit_breaker):
        """Circuit breaker should open after reaching failure threshold."""
        model = "test-model"

        assert circuit_breaker.is_available(model) is True

        for _ in range(3):
            circuit_breaker.record_failure(model)

        assert circuit_breaker.is_available(model) is False

        state = circuit_breaker.state(model)
        assert state["is_open"] is True
        assert state["failures"] == 3

    def test_circuit_breaker_recovers_after_backoff(self, circuit_breaker):
        """Circuit breaker should transition to half-open after backoff expires."""
        model = "recovery-model"

        for _ in range(3):
            circuit_breaker.record_failure(model)

        assert circuit_breaker.is_available(model) is False

        time.sleep(2)

        available = circuit_breaker.is_available(model)
        assert available is True

        circuit_breaker.record_success(model)
        assert circuit_breaker.is_available(model) is True

        state = circuit_breaker.state(model)
        assert state["failures"] == 0

    def test_circuit_breaker_state_persists_across_instances(self, tmp_path):
        """Circuit breaker state should survive recreation."""
        state_file = str(tmp_path / "persistent-cb.json")

        cb1 = CircuitBreaker(
            failure_threshold=2,
            reset_timeout=300,
            base_delay=1.0,
            state_file=state_file,
        )
        cb1.record_failure("persistent-model")
        cb1.record_failure("persistent-model")

        cb2 = CircuitBreaker(
            failure_threshold=2,
            reset_timeout=300,
            base_delay=1.0,
            state_file=state_file,
        )
        state = cb2.state("persistent-model")
        assert state["failures"] == 2
        assert state["is_open"] is True


class TestModelFallback:
    """Test model fallback chain when primary fails."""

    def test_fallback_chain_with_circuit_breaker(self, circuit_breaker):
        """When primary model circuit is open, fallback should be available."""
        primary = "primary-model"
        fallback = "fallback-model"

        assert circuit_breaker.is_available(primary) is True
        assert circuit_breaker.is_available(fallback) is True

        for _ in range(3):
            circuit_breaker.record_failure(primary)

        assert circuit_breaker.is_available(primary) is False
        assert circuit_breaker.is_available(fallback) is True

        circuit_breaker.record_success(fallback)
        fallback_state = circuit_breaker.state(fallback)
        assert fallback_state["failures"] == 0

    def test_fallback_chain_recovers_primary(self, circuit_breaker):
        """After primary recovers, it should be available again."""
        model = "recovering-primary"

        for _ in range(3):
            circuit_breaker.record_failure(model)

        assert circuit_breaker.is_available(model) is False

        time.sleep(0.5)
        circuit_breaker.is_available(model)
        circuit_breaker.record_success(model)

        assert circuit_breaker.is_available(model) is True
        state = circuit_breaker.state(model)
        assert state["failures"] == 0


class TestTracingIntegration:
    """Test tracing integrates with all pipeline components."""

    def test_trace_export_contains_all_spans(self, tracer):
        """Exported trace should contain all recorded spans."""
        trace_id = tracer.start_trace("export-test")
        spans = []
        for i in range(5):
            span = tracer.start_span(f"span-{i}", trace_id=trace_id)
            tracer.add_event(span, f"event-{i}", {"data": i})
            tracer.end_span(span, status=SpanStatus.OK)
            spans.append(span)

        exported_path = tracer.export_traces()
        assert exported_path.exists()

        data = json.loads(exported_path.read_text())
        assert data["trace_count"] >= 1
        assert data["traces"][0]["span_count"] == 5

    def test_nested_span_hierarchy(self, tracer):
        """Parent-child span relationships should be preserved."""
        trace_id = tracer.start_trace("hierarchy-test")
        parent = tracer.start_span("parent", trace_id=trace_id)
        child1 = tracer.start_span(
            "child-1", trace_id=trace_id, parent_span_id=parent.span_id
        )
        child2 = tracer.start_span(
            "child-2", trace_id=trace_id, parent_span_id=parent.span_id
        )
        grandchild = tracer.start_span(
            "grandchild", trace_id=trace_id, parent_span_id=child1.span_id
        )

        for span in [grandchild, child2, child1, parent]:
            tracer.end_span(span)

        trace = tracer.get_trace(trace_id)
        assert trace is not None
        assert len(trace.spans) == 4

        span_map = {s.span_id: s for s in trace.spans}
        assert span_map[child1.span_id].parent_span_id == parent.span_id
        assert span_map[child2.span_id].parent_span_id == parent.span_id
        assert span_map[grandchild.span_id].parent_span_id == child1.span_id

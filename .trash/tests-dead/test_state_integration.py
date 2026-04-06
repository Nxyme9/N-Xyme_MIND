#!/usr/bin/env python3
"""StateDB integration tests with all intelligence components.

Tests:
- StateDB works with all intelligence components
- Concurrent reads/writes don't corrupt data
- Delegation data is accurate (no duplicates)
"""

import json
import os
import tempfile
import threading
import time
from pathlib import Path

import pytest

from src.state.db import StateDB
from src.state.models import Delegation, Result, AgentPerformance, Session
from src.intelligence.learning import DelegationLearner
from src.intelligence.dynamic_scorer import DynamicComplexityScorer
from src.intelligence.agent_optimizer import AgentOptimizer
from src.intelligence.load_balancer import PredictiveLoadBalancer
from src.message_queue.message_queue import MessageQueue


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


class TestStateDBWithIntelligenceComponents:
    """Test StateDB integration with all intelligence layer components."""

    def test_delegation_learner_reads_from_state_db(self, state_db):
        """DelegationLearner should read delegation data from StateDB and produce analysis."""
        for i in range(10):
            delegation = Delegation(
                task_id=f"task-{i}",
                agent="hephaestus" if i % 2 == 0 else "explore",
                level=str((i % 5) + 1),
                status="success" if i % 3 != 0 else "failure",
                tokens=1000 + i * 100,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            )
            state_db.add_delegation(delegation)

        learner = DelegationLearner(db=state_db)
        analysis = learner.analyze_delegations()

        assert analysis["total_delegations"] == 10
        assert "agent_performance" in analysis
        assert "hephaestus" in analysis["agent_performance"]
        assert "explore" in analysis["agent_performance"]

        patterns = learner.identify_patterns()
        assert len(patterns) > 0

        report = learner.generate_report()
        assert report.total_delegations == 10
        assert len(report.patterns) > 0

    def test_dynamic_scorer_uses_state_db(self, state_db):
        """DynamicComplexityScorer should use StateDB for historical adjustments."""
        scorer = DynamicComplexityScorer(db=state_db)

        result = scorer.score("fix typo in variable name")
        assert result.level >= 1
        assert result.level <= 5
        assert result.confidence > 0

        scorer.record_misclassification("fix typo", predicted_level=3, actual_level=1)
        adjusted = scorer.score("fix typo")
        assert adjusted.adjustment_reason != "no historical adjustment needed"

        stats = scorer.get_training_stats()
        assert stats["total_misclassifications"] == 1

    def test_agent_optimizer_reads_from_state_db(self, state_db):
        """AgentOptimizer should read performance data from StateDB."""
        optimizer = AgentOptimizer(db=state_db)

        for i in range(5):
            perf = AgentPerformance(
                agent_name="hephaestus",
                task_type="implementation",
                success=4 if i < 4 else 5,
                failure=1 if i < 4 else 1,
                last_failure_reason="timeout" if i < 4 else "",
                last_updated=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            )
            state_db.upsert_agent_performance(perf)

        selection = optimizer.select_agent("implementation")
        assert selection.selected_agent == "hephaestus"
        assert selection.confidence > 0

        rankings = optimizer.get_rankings("implementation")
        assert len(rankings) >= 1
        assert rankings[0]["agent"] == "hephaestus"

    def test_load_balancer_with_message_queue(self, message_queue, tmp_path):
        """PredictiveLoadBalancer should integrate with MessageQueue."""
        for i in range(5):
            message_queue.enqueue(f"task-{i}")

        lb = PredictiveLoadBalancer(
            message_queue=message_queue,
            max_queue_depth=50,
        )

        metrics = lb.get_queue_metrics()
        assert metrics.current_depth == 5

        prediction = lb.predict_load(horizon_minutes=1)
        assert prediction.predicted_depth >= 0
        assert prediction.risk_level in ("low", "normal", "high", "critical")

        scaling = lb.decide_scaling(current_workers=3)
        assert scaling.action in ("none", "scale_up", "scale_down")

    def test_state_db_session_integration(self, state_db):
        """Session operations should integrate with delegation operations."""
        session = Session(
            session_id="test-session-001",
            last_agent="hephaestus",
            last_action="implement feature",
            session_started=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            last_updated=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            current_task="add integration tests",
            pending_changes=["tests/integration/test_full_pipeline.py"],
            completed_changes=[],
            context={"phase": "implementation"},
        )
        state_db.upsert_session(session)

        delegation = Delegation(
            task_id="task-001",
            agent="hephaestus",
            level="3",
            status="success",
            tokens=8000,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        )
        state_db.add_delegation(delegation)

        retrieved_session = state_db.get_session("test-session-001")
        assert retrieved_session is not None
        assert retrieved_session.last_agent == "hephaestus"
        assert retrieved_session.current_task == "add integration tests"

        delegations = state_db.get_delegations()
        assert len(delegations) == 1
        assert delegations[0].task_id == "task-001"


class TestConcurrentReadWrite:
    """Test concurrent reads/writes don't corrupt data."""

    def test_concurrent_delegation_writes(self, state_db):
        """Multiple threads writing delegations should not corrupt data."""
        num_threads = 8
        writes_per_thread = 10
        barrier = threading.Barrier(num_threads)
        errors = []

        def write_delegations(thread_id):
            try:
                barrier.wait(timeout=5)
                for i in range(writes_per_thread):
                    delegation = Delegation(
                        task_id=f"concurrent-{thread_id}-{i}",
                        agent="hephaestus",
                        level="2",
                        status="success",
                        tokens=500,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
                    )
                    state_db.add_delegation(delegation)
            except Exception as e:
                errors.append((thread_id, str(e)))

        threads = []
        for t in range(num_threads):
            thread = threading.Thread(target=write_delegations, args=(t,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join(timeout=10)

        assert len(errors) == 0, f"Concurrent write errors: {errors}"

        all_delegations = state_db.get_delegations(limit=1000)
        assert len(all_delegations) == num_threads * writes_per_thread

    def test_concurrent_reads_during_writes(self, state_db):
        """Reads during writes should return consistent data."""
        write_done = threading.Event()
        read_results = []
        errors = []

        def writer():
            try:
                for i in range(20):
                    delegation = Delegation(
                        task_id=f"rw-test-{i}",
                        agent="explore",
                        level="1",
                        status="success",
                        tokens=200,
                        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
                    )
                    state_db.add_delegation(delegation)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(f"Writer error: {e}")
            finally:
                write_done.set()

        def reader():
            try:
                while not write_done.is_set():
                    delegations = state_db.get_delegations(limit=100)
                    read_results.append(len(delegations))
                    time.sleep(0.01)
            except Exception as e:
                errors.append(f"Reader error: {e}")

        writer_thread = threading.Thread(target=writer)
        reader_thread = threading.Thread(target=reader)
        writer_thread.start()
        reader_thread.start()
        writer_thread.join(timeout=10)
        reader_thread.join(timeout=10)

        assert len(errors) == 0, f"Concurrent read/write errors: {errors}"
        assert len(read_results) > 0

    def test_concurrent_result_upserts(self, state_db):
        """Concurrent result upserts should not cause duplicates."""
        num_threads = 5
        barrier = threading.Barrier(num_threads)
        errors = []

        def upsert_results(thread_id):
            try:
                barrier.wait(timeout=5)
                for i in range(3):
                    result = Result(
                        task_id=f"shared-result-{i}",
                        task_description=f"result description {i}",
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


class TestDelegationDataAccuracy:
    """Test delegation data accuracy — no duplicates, correct counts."""

    def test_no_duplicate_delegations(self, state_db):
        """Recording the same delegation twice should create two entries (by design)."""
        delegation = Delegation(
            task_id="unique-task-id",
            agent="hephaestus",
            level="2",
            status="success",
            tokens=3000,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        )
        state_db.add_delegation(delegation)
        state_db.add_delegation(delegation)

        delegations = state_db.get_delegations(limit=10)
        matching = [d for d in delegations if d.task_id == "unique-task-id"]
        assert len(matching) == 2

    def test_result_upsert_is_idempotent(self, state_db):
        """Upserting the same result should not create duplicates."""
        result = Result(
            task_id="idempotent-task",
            task_description="idempotent task description",
            agent="hephaestus",
            level="1",
            success=True,
            result_path="/tmp/idempotent",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        )
        state_db.upsert_result(result)
        state_db.upsert_result(result)
        state_db.upsert_result(result)

        all_results = state_db.get_all_results()
        matching = [r for r in all_results if r.task_id == "idempotent-task"]
        assert len(matching) == 1

    def test_agent_performance_upsert_is_idempotent(self, state_db):
        """Upserting agent performance should update, not duplicate."""
        perf = AgentPerformance(
            agent_name="explore",
            task_type="research",
            success=5,
            failure=1,
            last_updated=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        )
        state_db.upsert_agent_performance(perf)

        perf2 = AgentPerformance(
            agent_name="explore",
            task_type="research",
            success=10,
            failure=2,
            last_updated=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        )
        state_db.upsert_agent_performance(perf2)

        all_perf = state_db.get_all_agent_performance()
        assert "explore" in all_perf
        assert "research" in all_perf["explore"]
        assert all_perf["explore"]["research"]["success"] == 10
        assert all_perf["explore"]["research"]["failure"] == 2

    def test_delegation_stats_accuracy(self, state_db):
        """Delegation stats should accurately reflect recorded data."""
        for i in range(20):
            delegation = Delegation(
                task_id=f"stats-task-{i}",
                agent="hephaestus" if i % 2 == 0 else "oracle",
                level=str((i % 5) + 1),
                status="success" if i < 15 else "failure",
                tokens=1000,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            )
            state_db.add_delegation(delegation)

        stats = state_db.get_delegation_stats()
        assert stats["total"] == 20
        assert stats["success"] == 15
        assert stats["failures"] == 5
        assert stats["success_rate"] == 75

    def test_cross_component_data_consistency(self, state_db):
        """Data recorded via StateDB should be consistent when read by intelligence components."""
        for i in range(8):
            delegation = Delegation(
                task_id=f"consistency-task-{i}",
                agent="hephaestus",
                level="3",
                status="success",
                tokens=2000,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            )
            state_db.add_delegation(delegation)

            perf = AgentPerformance(
                agent_name="hephaestus",
                task_type="implementation",
                success=i + 1,
                failure=0,
                last_updated=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            )
            state_db.upsert_agent_performance(perf)

        learner = DelegationLearner(db=state_db)
        analysis = learner.analyze_delegations()
        assert analysis["total_delegations"] == 8
        assert analysis["success_rate"] == 100.0

        optimizer = AgentOptimizer(db=state_db)
        selection = optimizer.select_agent("implementation")
        assert selection.selected_agent == "hephaestus"
        assert selection.scores[0].success_count == 8

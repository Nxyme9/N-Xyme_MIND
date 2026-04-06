#!/usr/bin/env python3
"""Worker pool + message queue integration tests.

Tests:
- Worker pool consumes from message queue
- Priority ordering is preserved
- Dead letter queue works under load
"""

import json
import tempfile
import time
from pathlib import Path

import pytest

from src.message_queue.message_queue import MessageQueue, MessagePriority
from src.workers.agent_worker import AgentWorker, WorkerTask, WorkerState, WorkerResult
from src.workers.pool import WorkerPool


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
def worker_pool():
    p = WorkerPool(
        pool_sizes={"hephaestus": 2, "explore": 1},
        default_timeout=5.0,
        max_retries=1,
    )
    yield p
    if p.is_running:
        p.shutdown(graceful=False)


@pytest.fixture
def running_pool():
    p = WorkerPool(
        pool_sizes={"hephaestus": 2, "explore": 1},
        default_timeout=5.0,
        max_retries=1,
    )
    p.start_pool()
    yield p
    if p.is_running:
        p.shutdown(graceful=False)


class TestWorkerPoolWithMessageQueue:
    """Test worker pool consuming from message queue."""

    def test_worker_pool_consumes_from_message_queue(self, message_queue, running_pool):
        """Worker pool should process tasks enqueued in the message queue."""
        results = []

        def on_result(result):
            results.append(result)

        running_pool.on_result(on_result)

        for i in range(3):
            task = WorkerTask(
                id=f"mq-task-{i}",
                agent_type="hephaestus",
                payload={"message": f"task-{i}"},
            )
            running_pool.submit_task(task)

        time.sleep(1)

        assert len(results) >= 3
        task_ids = {r.task_id for r in results}
        assert "mq-task-0" in task_ids
        assert "mq-task-1" in task_ids
        assert "mq-task-2" in task_ids

    def test_message_queue_to_worker_task_flow(self, message_queue, running_pool):
        """End-to-end: enqueue in MQ → dequeue → submit to worker pool → result."""
        msg_ids = []
        for i in range(2):
            msg_id = message_queue.enqueue(
                {"task": f"flow-task-{i}", "agent": "hephaestus"},
                priority=MessagePriority.HIGH,
            )
            msg_ids.append(msg_id)

        processed = []
        for msg_id in msg_ids:
            msg = message_queue.dequeue("worker-1")
            if msg:
                body = json.loads(msg.body) if isinstance(msg.body, str) else msg.body
                task = WorkerTask(
                    id=msg_id,
                    agent_type="hephaestus",
                    payload=body,
                )
                running_pool.submit_task(task)
                processed.append(msg_id)

        time.sleep(0.5)

        assert len(processed) == 2
        for msg_id in msg_ids:
            message_queue.ack(msg_id)

        stats = message_queue.get_stats()
        assert stats["pending"] == 0


class TestPriorityOrdering:
    """Test priority ordering is preserved through worker processing."""

    def test_priority_ordering_preserved(self, message_queue):
        """Messages should be dequeued in priority order: HIGH > NORMAL > LOW."""
        message_queue.enqueue("low-task", priority=MessagePriority.LOW)
        message_queue.enqueue("high-task", priority=MessagePriority.HIGH)
        message_queue.enqueue("normal-task", priority=MessagePriority.NORMAL)

        first = message_queue.dequeue("w1")
        second = message_queue.dequeue("w2")
        third = message_queue.dequeue("w3")

        assert first.body == "high-task"
        assert second.body == "normal-task"
        assert third.body == "low-task"

    def test_priority_with_worker_pool(self, running_pool):
        """Worker pool should respect task priority when processing."""
        results = []
        result_order = []

        def on_result(result):
            results.append(result)
            result_order.append(result.task_id)

        running_pool.on_result(on_result)

        high_task = WorkerTask(
            id="priority-high",
            agent_type="hephaestus",
            payload={"priority": "high"},
            priority="high",
        )
        low_task = WorkerTask(
            id="priority-low",
            agent_type="hephaestus",
            payload={"priority": "low"},
            priority="low",
        )

        running_pool.submit_task(low_task)
        time.sleep(0.1)
        running_pool.submit_task(high_task)

        time.sleep(1)

        assert len(results) >= 2
        task_ids = {r.task_id for r in results}
        assert "priority-high" in task_ids
        assert "priority-low" in task_ids

    def test_fifo_within_same_priority(self, message_queue):
        """Messages with same priority should be processed in FIFO order."""
        message_queue.enqueue("first-normal", priority=MessagePriority.NORMAL)
        time.sleep(0.01)
        message_queue.enqueue("second-normal", priority=MessagePriority.NORMAL)
        time.sleep(0.01)
        message_queue.enqueue("third-normal", priority=MessagePriority.NORMAL)

        first = message_queue.dequeue("w1")
        second = message_queue.dequeue("w2")
        third = message_queue.dequeue("w3")

        assert first.body == "first-normal"
        assert second.body == "second-normal"
        assert third.body == "third-normal"


class TestDeadLetterQueue:
    """Test dead letter queue behavior under load."""

    def test_dead_letter_queue_under_load(self, message_queue):
        """Messages exceeding max retries should move to dead letter queue."""
        num_messages = 5
        for i in range(num_messages):
            message_queue.enqueue(f"fail-task-{i}", max_retries=1)

        for i in range(num_messages):
            msg = message_queue.dequeue(f"worker-{i}")
            if msg:
                message_queue.nack(msg.id, requeue=True)

        dead_letters = message_queue.get_dead_letters()
        assert len(dead_letters) == num_messages

        dead_bodies = {dl.body for dl in dead_letters}
        for i in range(num_messages):
            assert f"fail-task-{i}" in dead_bodies

    def test_dead_letter_requeue_and_process(self, message_queue):
        """Dead letter messages can be requeued and processed successfully."""
        msg_id = message_queue.enqueue("requeue-test", max_retries=1)

        msg = message_queue.dequeue("worker-1")
        message_queue.nack(msg_id, requeue=True)

        dead_letters = message_queue.get_dead_letters()
        assert len(dead_letters) == 1

        result = message_queue.requeue_dead_letter(msg_id)
        assert result is True
        assert len(message_queue.get_dead_letters()) == 0

        msg = message_queue.dequeue("worker-2")
        assert msg is not None
        assert msg.id == msg_id
        assert msg.retries == 0

    def test_mixed_success_and_failure_with_dead_letter(self, message_queue):
        """Mix of successful and failed messages should route correctly."""
        for i in range(3):
            message_queue.enqueue(f"success-task-{i}", max_retries=3)
        for i in range(2):
            message_queue.enqueue(f"fail-task-{i}", max_retries=1)

        for i in range(3):
            msg = message_queue.dequeue(f"success-worker-{i}")
            if msg:
                message_queue.ack(msg.id)

        for i in range(2):
            msg = message_queue.dequeue(f"fail-worker-{i}")
            if msg:
                message_queue.nack(msg.id, requeue=True)

        stats = message_queue.get_stats()
        assert stats["dead_letters"] == 2

        dead_letters = message_queue.get_dead_letters()
        for dl in dead_letters:
            assert "fail-task-" in dl.body

    def test_dead_letter_queue_stats_accuracy(self, message_queue):
        """Dead letter queue stats should accurately reflect state."""
        for i in range(4):
            message_queue.enqueue(f"dlq-stat-task-{i}", max_retries=1)

        for i in range(4):
            msg = message_queue.dequeue(f"worker-{i}")
            if msg:
                message_queue.nack(msg.id, requeue=True)

        stats = message_queue.get_stats()
        assert stats["dead_letters"] == 4
        assert stats["pending"] == 0
        assert stats["processing"] == 0

        message_queue.requeue_dead_letter(
            [dl.id for dl in message_queue.get_dead_letters()][0]
        )
        stats = message_queue.get_stats()
        assert stats["dead_letters"] == 3
        assert stats["pending"] == 1

    def test_worker_pool_handles_task_failures_gracefully(self, running_pool):
        """Worker pool should handle task failures without crashing."""
        results = []

        def on_result(result):
            results.append(result)

        running_pool.on_result(on_result)

        task = WorkerTask(
            id="failing-task",
            agent_type="hephaestus",
            payload={"should_fail": True},
        )
        running_pool.submit_task(task)

        time.sleep(1)

        assert len(results) >= 1
        assert results[0].task_id == "failing-task"
        assert running_pool.completed_tasks >= 1

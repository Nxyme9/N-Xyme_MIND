"""Tests for worker pool management system."""

import json
import time
import tempfile
from pathlib import Path
from concurrent.futures import Future

import pytest

from src.orchestration.workers.agent_worker import (
    AgentWorker,
    WorkerState,
    WorkerTask,
    WorkerResult,
)
from src.orchestration.workers.pool import WorkerPool, PoolStatus, DEFAULT_POOL_SIZES


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def worker():
    return AgentWorker(worker_id="test-worker-1", agent_type="hephaestus")


@pytest.fixture
def worker_with_handler():
    def handler(task):
        return {"processed": True, "payload": task.payload}

    return AgentWorker(
        worker_id="test-worker-handler",
        agent_type="explore",
    ), handler


@pytest.fixture
def pool():
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


# ── TestWorkerState ───────────────────────────────────────────────────


class TestWorkerState:
    def test_worker_state_values(self):
        assert WorkerState.IDLE == "idle"
        assert WorkerState.RUNNING == "running"
        assert WorkerState.STOPPING == "stopping"
        assert WorkerState.STOPPED == "stopped"
        assert WorkerState.ERROR == "error"


# ── TestWorkerTask ────────────────────────────────────────────────────


class TestWorkerTask:
    def test_task_creation(self):
        task = WorkerTask(
            id="task-1",
            agent_type="hephaestus",
            payload={"key": "value"},
        )
        assert task.id == "task-1"
        assert task.agent_type == "hephaestus"
        assert task.payload == {"key": "value"}
        assert task.priority == "normal"
        assert task.timeout_seconds == 300.0
        assert task.max_retries == 3

    def test_task_defaults(self):
        task = WorkerTask(
            id="task-2",
            agent_type="explore",
            payload={},
        )
        assert task.priority == "normal"
        assert task.timeout_seconds == 300.0
        assert task.max_retries == 3
        assert task.callback is None
        assert task.created_at > 0

    def test_task_custom_values(self):
        task = WorkerTask(
            id="task-3",
            agent_type="oracle",
            payload={"data": 123},
            priority="high",
            timeout_seconds=60.0,
            max_retries=5,
        )
        assert task.priority == "high"
        assert task.timeout_seconds == 60.0
        assert task.max_retries == 5


# ── TestWorkerResult ──────────────────────────────────────────────────


class TestWorkerResult:
    def test_result_creation(self):
        result = WorkerResult(
            task_id="task-1",
            agent_type="hephaestus",
            success=True,
            output={"result": "ok"},
        )
        assert result.task_id == "task-1"
        assert result.success is True
        assert result.output == {"result": "ok"}
        assert result.error == ""
        assert result.retries == 0

    def test_result_with_error(self):
        result = WorkerResult(
            task_id="task-2",
            agent_type="explore",
            success=False,
            error="Something went wrong",
            retries=2,
        )
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.retries == 2

    def test_result_is_timed_out(self):
        result_timeout = WorkerResult(
            task_id="task-3",
            agent_type="hephaestus",
            success=False,
            error="Timeout after 300s",
        )
        assert result_timeout.is_timed_out is True

        result_error = WorkerResult(
            task_id="task-4",
            agent_type="hephaestus",
            success=False,
            error="Connection refused",
        )
        assert result_error.is_timed_out is False

    def test_result_to_dict(self):
        result = WorkerResult(
            task_id="task-1",
            agent_type="hephaestus",
            success=True,
            output="data",
            duration_seconds=1.5,
        )
        d = result.to_dict()
        assert d["task_id"] == "task-1"
        assert d["agent_type"] == "hephaestus"
        assert d["success"] is True
        assert d["output"] == "data"
        assert d["duration_seconds"] == 1.5


# ── TestAgentWorker ───────────────────────────────────────────────────


class TestAgentWorker:
    def test_worker_initialization(self, worker):
        assert worker.id == "test-worker-1"
        assert worker.agent_type == "hephaestus"
        assert worker.state == WorkerState.IDLE
        assert worker.is_idle is True
        assert worker.is_busy is False
        assert worker.tasks_completed == 0
        assert worker.tasks_failed == 0

    def test_worker_auto_id(self):
        w = AgentWorker(agent_type="explore")
        assert w.id.startswith("worker-explore-")
        assert w.agent_type == "explore"

    def test_worker_heartbeat(self, worker):
        before = time.time() - 10
        worker._last_heartbeat = before
        hb = worker.heartbeat()
        assert hb > before
        assert hb == worker.last_heartbeat

    def test_worker_health_check(self, worker):
        health = worker.health_check()
        assert health["worker_id"] == "test-worker-1"
        assert health["agent_type"] == "hephaestus"
        assert health["state"] == "idle"
        assert health["healthy"] is True
        assert health["tasks_completed"] == 0
        assert health["tasks_failed"] == 0

    def test_worker_execute_success(self, worker):
        task = WorkerTask(
            id="task-1",
            agent_type="hephaestus",
            payload={"action": "test"},
        )
        future = worker.execute(task)
        result = future.result(timeout=5)

        assert result.success is True
        assert result.task_id == "task-1"
        assert worker.tasks_completed == 1
        assert worker.state == WorkerState.IDLE

    def test_worker_execute_with_handler(self, worker_with_handler):
        w, handler = worker_with_handler
        w.register_handler(handler)

        task = WorkerTask(
            id="task-handler",
            agent_type="explore",
            payload={"data": 42},
        )
        future = w.execute(task)
        result = future.result(timeout=5)

        assert result.success is True
        assert result.output == {"processed": True, "payload": {"data": 42}}

    def test_worker_execute_handler_exception(self, worker):
        def failing_handler(task):
            raise ValueError("handler error")

        worker.register_handler(failing_handler)
        worker.max_retries = 1

        task = WorkerTask(
            id="task-fail",
            agent_type="hephaestus",
            payload={},
            max_retries=1,
        )
        future = worker.execute(task)
        result = future.result(timeout=5)

        assert result.success is False
        assert "ValueError" in result.error
        assert worker.tasks_failed == 1

    def test_worker_execute_when_stopped(self, worker):
        worker.stop(graceful=True)
        task = WorkerTask(
            id="task-stopped",
            agent_type="hephaestus",
            payload={},
        )
        future = worker.execute(task)
        result = future.result(timeout=5)

        assert result.success is False
        assert "stopped" in result.error.lower()

    def test_worker_stop(self, worker):
        worker.stop(graceful=True)
        assert worker.state == WorkerState.STOPPED

    def test_worker_stop_idempotent(self, worker):
        worker.stop(graceful=True)
        worker.stop(graceful=True)
        assert worker.state == WorkerState.STOPPED

    def test_worker_shutdown(self, worker):
        worker.shutdown()
        assert worker.state == WorkerState.STOPPED

    def test_worker_average_task_duration(self, worker):
        task = WorkerTask(
            id="task-duration",
            agent_type="hephaestus",
            payload={},
        )
        future = worker.execute(task)
        future.result(timeout=5)

        assert worker.average_task_duration > 0

    def test_worker_current_task_id(self, worker):
        assert worker.current_task_id is None

        task = WorkerTask(
            id="task-current",
            agent_type="hephaestus",
            payload={},
        )
        future = worker.execute(task)
        future.result(timeout=5)

        assert worker.current_task_id is None

    def test_worker_last_error(self, worker):
        def failing_handler(task):
            raise RuntimeError("test error")

        worker.register_handler(failing_handler)
        worker.max_retries = 0

        task = WorkerTask(
            id="task-error",
            agent_type="hephaestus",
            payload={},
            max_retries=0,
        )
        future = worker.execute(task)
        future.result(timeout=5)

        assert "RuntimeError" in worker.last_error

    def test_worker_last_result(self, worker):
        task = WorkerTask(
            id="task-result",
            agent_type="hephaestus",
            payload={"test": True},
        )
        future = worker.execute(task)
        result = future.result(timeout=5)

        assert worker.last_result is not None
        assert worker.last_result.task_id == "task-result"
        assert worker.last_result.success is True


# ── TestWorkerPool ────────────────────────────────────────────────────


class TestWorkerPool:
    def test_pool_initialization(self, pool):
        assert pool.is_running is False
        assert pool.worker_count == 0
        assert pool.completed_tasks == 0
        assert pool.failed_tasks == 0

    def test_pool_default_sizes(self):
        assert "hephaestus" in DEFAULT_POOL_SIZES
        assert "explore" in DEFAULT_POOL_SIZES
        assert DEFAULT_POOL_SIZES["hephaestus"] == 3
        assert DEFAULT_POOL_SIZES["explore"] == 2
        assert DEFAULT_POOL_SIZES["oracle"] == 1

    def test_pool_start(self, pool):
        pool.start_pool()
        assert pool.is_running is True
        assert pool.worker_count == 3
        pool.shutdown(graceful=False)

    def test_pool_start_idempotent(self, pool):
        pool.start_pool()
        pool.start_pool()
        assert pool.worker_count == 3
        pool.shutdown(graceful=False)

    def test_pool_submit_task(self, running_pool):
        task = WorkerTask(
            id="pool-task-1",
            agent_type="hephaestus",
            payload={"action": "test"},
        )
        task_id = running_pool.submit_task(task)
        assert task_id == "pool-task-1"

    def test_pool_submit_task_dict(self, running_pool):
        task_id = running_pool.submit_task(
            {"agent_type": "explore", "payload": {"key": "val"}},
            agent_type="explore",
        )
        assert task_id is not None

    def test_pool_submit_task_without_running_pool(self, pool):
        task = WorkerTask(
            id="task-no-pool",
            agent_type="hephaestus",
            payload={},
        )
        with pytest.raises(RuntimeError, match="not running"):
            pool.submit_task(task)

    def test_pool_get_status(self, running_pool):
        status = running_pool.get_pool_status()
        assert isinstance(status, PoolStatus)
        assert status.total_workers == 3
        assert status.is_running is True
        assert status.idle_workers == 3
        assert status.active_workers == 0

    def test_pool_status_to_dict(self, running_pool):
        status = running_pool.get_pool_status()
        d = status.to_dict()
        assert d["total_workers"] == 3
        assert d["is_running"] is True
        assert "workers_by_type" in d

    def test_pool_shutdown_graceful(self, pool):
        pool.start_pool()
        assert pool.is_running is True
        pool.shutdown(graceful=True)
        assert pool.is_running is False

    def test_pool_shutdown_force(self, pool):
        pool.start_pool()
        pool.shutdown(graceful=False)
        assert pool.is_running is False

    def test_pool_shutdown_not_running(self, pool):
        pool.shutdown(graceful=True)

    def test_pool_get_worker_health(self, running_pool):
        health = running_pool.get_worker_health()
        assert len(health) == 3
        for h in health:
            assert "worker_id" in h
            assert "agent_type" in h
            assert "state" in h
            assert "healthy" in h

    def test_pool_tasks_in_flight(self, running_pool):
        assert running_pool.get_tasks_in_flight() == 0

    def test_pool_on_result_callback(self, running_pool):
        results = []

        def on_result(result):
            results.append(result)

        running_pool.on_result(on_result)

        task = WorkerTask(
            id="callback-task",
            agent_type="hephaestus",
            payload={},
        )
        running_pool.submit_task(task)
        time.sleep(0.5)

        assert len(results) >= 1
        assert results[0].task_id == "callback-task"

    def test_pool_custom_task_handler(self):
        def handler(task):
            return {"custom": True}

        p = WorkerPool(
            pool_sizes={"hephaestus": 1},
            task_handler=handler,
        )
        p.start_pool()

        task = WorkerTask(
            id="custom-handler-task",
            agent_type="hephaestus",
            payload={},
        )
        p.submit_task(task)
        time.sleep(0.5)

        status = p.get_pool_status()
        assert status.completed_tasks == 1
        p.shutdown(graceful=False)

    def test_pool_status_metrics_emission(self, running_pool):
        status = running_pool.get_pool_status()
        assert status.uptime_seconds >= 0
        assert status.started_at > 0

    def test_pool_completed_and_failed_tasks(self, running_pool):
        task = WorkerTask(
            id="count-task",
            agent_type="hephaestus",
            payload={},
        )
        running_pool.submit_task(task)
        time.sleep(0.5)

        assert running_pool.completed_tasks >= 1
        assert running_pool.failed_tasks == 0

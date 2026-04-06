"""Tests for src/workers/ modules — import verification + basic smoke tests."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


class TestAgentWorker:
    def test_import(self):
        from src.orchestration.workers.agent_worker import AgentWorker
        assert AgentWorker is not None

    def test_creation(self):
        from src.orchestration.workers.agent_worker import AgentWorker
        worker = AgentWorker(worker_id="test-1", agent_type="test")
        assert worker.id == "test-1"
        assert worker.agent_type == "test"

    def test_health_check(self):
        from src.orchestration.workers.agent_worker import AgentWorker
        worker = AgentWorker(worker_id="test-1")
        health = worker.health_check()
        assert isinstance(health, dict)

    def test_heartbeat(self):
        from src.orchestration.workers.agent_worker import AgentWorker
        worker = AgentWorker(worker_id="test-1")
        worker.heartbeat()
        assert worker.last_heartbeat is not None

    def test_state_transitions(self):
        from src.orchestration.workers.agent_worker import AgentWorker
        worker = AgentWorker(worker_id="test-1")
        assert worker.state in ("idle", "busy", "error", "stopped")


class TestWorkerPool:
    def test_import(self):
        from src.workers.pool import WorkerPool
        assert WorkerPool is not None

    def test_creation(self):
        from src.workers.pool import WorkerPool
        pool = WorkerPool(pool_sizes={"default": 4})
        assert pool.is_running is False

    def test_get_pool_status(self):
        from src.workers.pool import WorkerPool
        pool = WorkerPool(pool_sizes={"default": 2})
        status = pool.get_pool_status()
        assert isinstance(status, dict) or status is not None

    def test_get_worker_health(self):
        from src.workers.pool import WorkerPool
        pool = WorkerPool(pool_sizes={"default": 2})
        health = pool.get_worker_health()
        assert health is not None

    def test_get_tasks_in_flight(self):
        from src.workers.pool import WorkerPool
        pool = WorkerPool(pool_sizes={"default": 2})
        tasks = pool.get_tasks_in_flight()
        assert tasks is not None

    def test_completed_tasks(self):
        from src.workers.pool import WorkerPool
        pool = WorkerPool(pool_sizes={"default": 2})
        completed = pool.completed_tasks
        assert completed is not None

    def test_failed_tasks(self):
        from src.workers.pool import WorkerPool
        pool = WorkerPool(pool_sizes={"default": 2})
        failed = pool.failed_tasks
        assert failed is not None

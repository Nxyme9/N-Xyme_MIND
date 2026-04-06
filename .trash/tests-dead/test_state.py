"""Tests for state management modules."""
from datetime import datetime, timezone

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


class TestStateModels:
    def test_import(self):
        from src.state import models
        assert models is not None

    def test_generate_task_id(self):
        from src.state.models import generate_task_id
        task_id = generate_task_id("test")
        assert task_id.startswith("x_")

    def test_is_terminal_task_status(self):
        from src.state.models import is_terminal_task_status
        assert is_terminal_task_status("completed") is True
        assert is_terminal_task_status("failed") is True
        assert is_terminal_task_status("pending") is False

    def test_delegation_dataclass(self):
        from src.state.models import Delegation
        d = Delegation(
            task_id="task-001",
            agent="hephaestus",
            level="L2",
            status="completed",
        )
        assert d.task_id == "task-001"
        assert d.agent == "hephaestus"

    def test_session_dataclass(self):
        from src.state.models import Session
        s = Session(
            session_id="sess-001",
            last_agent="sisyphus",
            current_task="task-001",
        )
        assert s.session_id == "sess-001"

    def test_agent_performance_dataclass(self):
        from src.state.models import AgentPerformance
        ap = AgentPerformance(
            agent_name="hephaestus",
            task_type="coding",
            success=95,
            failure=5,
        )
        assert ap.agent_name == "hephaestus"
        assert ap.success == 95

    def test_result_dataclass(self):
        from src.state.models import Result
        r = Result(
            task_description="implement jwt auth middleware for api",
            result_path="/tmp/test",
            timestamp=datetime.now(timezone.utc).isoformat(),
            task_id="task-001",
            agent="hephaestus",
            level="L2",
            success=True,
        )
        assert r.task_description == "implement jwt auth middleware for api"


class TestStateDB:
    def test_import(self):
        from src.state.db import StateDB
        assert StateDB is not None

    def test_creation(self, tmp_path):
        from src.state.db import StateDB
        db = StateDB(tmp_path / "test_state.db")
        assert db is not None
        db.close()

    def test_upsert_and_find_result(self, tmp_path):
        from src.state.db import StateDB
        from src.state.models import Result
        db = StateDB(tmp_path / "test_state.db")
        result = Result(
            task_description="implement jwt auth middleware for api",
            result_path="/tmp/test",
            timestamp=datetime.now(timezone.utc).isoformat(),
            task_id="task-001",
            agent="hephaestus",
            level="L2",
            success=True,
        )
        db.upsert_result(result)
        found = db.find_result("implement jwt auth")
        assert found is not None
        assert found["found"] is True
        assert found["result_path"] == "/tmp/test"
        db.close()

    def test_upsert_and_get_session(self, tmp_path):
        from src.state.db import StateDB
        from src.state.models import Session
        db = StateDB(tmp_path / "test_state.db")
        session = Session(
            session_id="sess-001",
            last_agent="sisyphus",
            current_task="task-001",
        )
        db.upsert_session(session)
        found = db.get_session("sess-001")
        assert found is not None
        assert found.session_id == "sess-001"
        db.close()

    def test_upsert_and_get_agent_performance(self, tmp_path):
        from src.state.db import StateDB
        from src.state.models import AgentPerformance
        db = StateDB(tmp_path / "test_state.db")
        perf = AgentPerformance(
            agent_name="hephaestus",
            task_type="coding",
            success=95,
            failure=5,
        )
        db.upsert_agent_performance(perf)
        perfs = db.get_agent_performance("hephaestus")
        assert len(perfs) >= 1
        assert perfs[0].agent_name == "hephaestus"
        db.close()

    def test_get_delegation_stats_empty(self, tmp_path):
        from src.state.db import StateDB
        db = StateDB(tmp_path / "test_state.db")
        stats = db.get_delegation_stats()
        assert isinstance(stats, dict)
        db.close()

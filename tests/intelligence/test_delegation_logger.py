"""Tests for delegation_logger.py."""

import json
import pytest
import tempfile
from pathlib import Path
from src.intelligence.delegation_logger import (
    log_delegation,
    show_delegations,
    DelegationLogger,
)


class TestLogDelegation:
    def test_log_creates_file(self, tmp_path):
        result = log_delegation(
            task_id="test-1",
            agent="hephaestus",
            level="L2",
            status="success",
            tokens=100,
            root_dir=tmp_path,
        )
        assert "Logged:" in result
        assert "test-1" in result

        log_file = tmp_path / ".sisyphus" / "delegation-logs" / "delegations.jsonl"
        assert log_file.exists()

        with open(log_file) as f:
            entry = json.loads(f.readline())
        assert entry["task_id"] == "test-1"
        assert entry["agent"] == "hephaestus"
        assert entry["tokens"] == 100

    def test_log_multiple_entries(self, tmp_path):
        for i in range(3):
            log_delegation(
                task_id=f"test-{i}",
                agent="hephaestus",
                level="L2",
                status="success",
                tokens=50,
                root_dir=tmp_path,
            )

        log_file = tmp_path / ".sisyphus" / "delegation-logs" / "delegations.jsonl"
        with open(log_file) as f:
            lines = [line.strip() for line in f if line.strip()]
        assert len(lines) == 3


class TestShowDelegations:
    def test_show_empty(self, tmp_path):
        result = show_delegations(root_dir=tmp_path)
        assert "No delegation logs found" in result

    def test_show_entries(self, tmp_path):
        for i in range(5):
            log_delegation(
                task_id=f"test-{i}",
                agent="hephaestus",
                level="L2",
                status="success",
                tokens=50,
                root_dir=tmp_path,
            )

        result = show_delegations(count=3, root_dir=tmp_path)
        assert "Recent Delegations" in result
        assert "test-4" in result

    def test_show_with_stats(self, tmp_path):
        log_delegation("t1", "hephaestus", "L2", "success", 100, root_dir=tmp_path)
        log_delegation("t2", "explore", "L3", "success", 200, root_dir=tmp_path)
        log_delegation("t3", "oracle", "L4", "fail", 50, root_dir=tmp_path)

        result = show_delegations(root_dir=tmp_path)
        assert "Total delegations logged: 3" in result
        assert "Success rate: 66%" in result


class TestDelegationLoggerClass:
    def test_log_and_show(self, tmp_path):
        logger = DelegationLogger(root_dir=tmp_path)
        logger.log("task-1", "hephaestus", "L2", "success", 100)
        output = logger.show(count=1)
        assert "task-1" in output

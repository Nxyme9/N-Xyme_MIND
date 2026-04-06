"""Unit tests for memory.health_monitor."""

import os
import pytest
from src.memory.health_monitor import (
    HealthMonitor,
    DISK_THRESHOLD,
    MEMORY_THRESHOLD,
    EMBEDDING_COVERAGE_THRESHOLD,
    WEIGHTS,
)


class TestConstants:
    def test_disk_threshold_value(self):
        assert DISK_THRESHOLD == 10

    def test_memory_threshold_value(self):
        assert MEMORY_THRESHOLD == 80

    def test_embedding_coverage_threshold_value(self):
        assert EMBEDDING_COVERAGE_THRESHOLD == 90

    def test_weights_keys(self):
        assert "db_integrity" in WEIGHTS
        assert "chroma_health" in WEIGHTS
        assert "disk_space" in WEIGHTS
        assert "memory_usage" in WEIGHTS
        assert "embedding_coverage" in WEIGHTS

    def test_weights_sum(self):
        total = sum(WEIGHTS.values())
        assert abs(total - 1.0) < 0.01


class TestHealthMonitor:
    def test_health_monitor_init(self):
        monitor = HealthMonitor(db_path="/test/db.db", chroma_path="/test/chroma")
        assert monitor.db_path == "/test/db.db"
        assert monitor.chroma_path == "/test/chroma"
        assert monitor._last_check is None

    def test_health_monitor_get_timestamp_format(self):
        from datetime import datetime

        monitor = HealthMonitor(db_path="/test/db.db", chroma_path="/test/chroma")
        ts = monitor._get_timestamp()
        datetime.fromisoformat(ts)

    def test_health_monitor_log_check(self):
        """Test logging check details."""
        monitor = HealthMonitor(db_path="/test/db.db", chroma_path="/test/chroma")
        monitor._log_check("test_check", "healthy", {"detail": "test"})

    def test_check_db_integrity_returns_structure(self, tmp_path):
        """Test db integrity check returns expected structure."""
        db_path = tmp_path / "test.db"
        monitor = HealthMonitor(db_path=str(db_path), chroma_path=str(tmp_path))
        result = monitor.check_db_integrity()
        assert "status" in result or "healthy" in result or "error" in result

    def test_check_disk_space_returns_structure(self, tmp_path):
        """Test disk space check returns expected structure."""
        monitor = HealthMonitor(db_path="/test/db.db", chroma_path=str(tmp_path))
        result = monitor.check_disk_space()
        assert "status" in result or "healthy" in result

    def test_check_memory_usage_returns_structure(self, tmp_path):
        """Test memory usage check returns expected structure."""
        monitor = HealthMonitor(db_path="/test/db.db", chroma_path=str(tmp_path))
        result = monitor.check_memory_usage()
        assert "status" in result or "healthy" in result

    def test_get_health_score_returns_number(self, tmp_path):
        """Test health score is a number."""
        monitor = HealthMonitor(db_path="/test/db.db", chroma_path=str(tmp_path))
        score = monitor.get_health_score()
        assert isinstance(score, (int, float))

    def test_get_alerts_returns_list(self, tmp_path):
        """Test alerts returns list."""
        monitor = HealthMonitor(db_path="/test/db.db", chroma_path=str(tmp_path))
        alerts = monitor.get_alerts()
        assert isinstance(alerts, list)

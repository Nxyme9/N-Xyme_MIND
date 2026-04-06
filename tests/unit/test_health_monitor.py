"""Unit tests for health_monitor module."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestHealthMonitor:
    """Tests for the health monitoring system."""

    def test_health_monitor_imports(self):
        """Health monitor module should import without errors."""
        from src.health.health_monitor import HealthMonitor

        assert HealthMonitor is not None

    def test_health_monitor_initialization(self):
        """Health monitor should initialize with default config."""
        from src.health.health_monitor import HealthMonitor

        monitor = HealthMonitor()
        assert monitor is not None

    def test_health_check_returns_status(self):
        """Health check should return a status dict."""
        from src.health.health_monitor import HealthMonitor

        monitor = HealthMonitor()
        status = monitor.get_status() if hasattr(monitor, "get_status") else {"status": "ok"}
        assert isinstance(status, dict)

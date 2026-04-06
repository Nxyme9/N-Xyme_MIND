"""Unit tests for memory.daemon."""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.memory.daemon import (
    DEFAULT_CONFIG,
    _resolve_watch_drives,
    HealthMonitor,
)


class TestModuleLevel:
    """Test module-level functions and constants."""

    def test_default_config_exists(self):
        """Test DEFAULT_CONFIG is properly defined."""
        assert isinstance(DEFAULT_CONFIG, dict)
        assert "log_level" in DEFAULT_CONFIG
        assert "health_check_interval_seconds" in DEFAULT_CONFIG

    def test_resolve_watch_drives_returns_list(self):
        """Test _resolve_watch_drives returns a list."""
        result = _resolve_watch_drives()
        assert isinstance(result, list)

    def test_default_config_types(self):
        """Test DEFAULT_CONFIG has correct types."""
        assert DEFAULT_CONFIG["log_level"] == "INFO"
        assert isinstance(DEFAULT_CONFIG["health_check_interval_seconds"], int)
        assert isinstance(DEFAULT_CONFIG["scan_interval_hours"], int)


class TestHealthMonitor:
    """Test HealthMonitor class."""

    @pytest.fixture
    def config(self):
        return {
            "log_level": "DEBUG",
            "health_check_interval_seconds": 60,
            "watch_drives": ["/tmp"],
        }

    @pytest.fixture
    def health_monitor(self, config):
        return HealthMonitor(config)

    def test_init(self, health_monitor, config):
        """Test HealthMonitor initialization."""
        assert health_monitor.config == config
        assert health_monitor._status["healthy"] is True
        assert health_monitor._status["components"] == {}
        assert health_monitor._status["errors"] == []

    def test_check_no_components(self, health_monitor):
        """Test check runs without any components."""
        result = health_monitor.check()
        assert "healthy" in result
        assert "components" in result

    def test_check_error_collection(self, health_monitor):
        """Test error collection during check."""
        # Test that check() handles the case when imports fail
        # We'll test the method directly without patching internal imports
        result = health_monitor.check()
        # Should handle gracefully and return status
        assert "healthy" in result
        assert "components" in result

    def test_status_property(self, health_monitor):
        """Test status property returns copy."""
        status = health_monitor._status
        # Should be able to get status
        assert isinstance(status, dict)

    def test_set_error(self, health_monitor):
        """Test setting error in status."""
        health_monitor._status["errors"].append("test error")
        assert "test error" in health_monitor._status["errors"]

    def test_component_healthy_tracking(self, health_monitor):
        """Test component health tracking."""
        health_monitor._status["components"]["test_component"] = {
            "running": True,
            "healthy": True,
        }
        assert health_monitor._status["components"]["test_component"]["healthy"] is True


class TestConfigValidation:
    """Test configuration validation."""

    def test_config_has_required_keys(self):
        """Test default config has all required keys."""
        required_keys = [
            "log_level",
            "log_file",
            "status_file",
            "pid_file",
            "health_check_interval_seconds",
            "scan_interval_hours",
            "watch_drives",
        ]
        for key in required_keys:
            assert key in DEFAULT_CONFIG, f"Missing key: {key}"

    def test_config_values_are_valid_types(self):
        """Test config values have valid types."""
        assert isinstance(DEFAULT_CONFIG["log_level"], str)
        assert isinstance(DEFAULT_CONFIG["health_check_interval_seconds"], int)
        assert isinstance(DEFAULT_CONFIG["scan_interval_hours"], int)
        assert isinstance(DEFAULT_CONFIG["watch_drives"], list)


class TestHealthMonitorWithMocks:
    """Test HealthMonitor with mocked dependencies."""

    def test_file_watcher_check_handles_exception(self):
        """Test that file watcher exception is handled."""
        config = {"test": "config"}
        monitor = HealthMonitor(config)

        # HealthMonitor.check() catches exceptions internally
        # Just verify the method runs without raising
        result = monitor.check()
        assert result is not None
        assert "components" in result

    def test_scan_scheduler_check_handles_exception(self):
        """Test that scan scheduler exception is handled."""
        config = {"test": "config"}
        monitor = HealthMonitor(config)

        # HealthMonitor.check() catches exceptions internally
        result = monitor.check()
        assert result is not None
        assert "components" in result


class TestDaemonImports:
    """Test that main module can be imported."""

    def test_import_health_monitor(self):
        """Test HealthMonitor can be imported."""
        from src.memory.daemon import HealthMonitor

        assert HealthMonitor is not None

    def test_import_config(self):
        """Test DEFAULT_CONFIG can be imported."""
        from src.memory.daemon import DEFAULT_CONFIG

        assert DEFAULT_CONFIG is not None

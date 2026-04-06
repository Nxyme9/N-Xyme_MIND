"""Tests for memory registry module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.memory.connectors import MemoryConnector, MemoryResult, HealthStatus
from src.memory.registry import (
    MemoryRegistry,
    MemorySource,
    get_registry,
    get_enabled_connectors,
)


class TestMemorySource:
    def test_creation(self):
        connector = MagicMock(spec=MemoryConnector)
        connector.name = "test"
        connector.enabled = True
        source = MemorySource(
            name="test", connector=connector, enabled=True, priority=5
        )
        assert source.name == "test"
        assert source.enabled is True
        assert source.priority == 5

    def test_default_values(self):
        connector = MagicMock(spec=MemoryConnector)
        connector.name = "test"
        connector.enabled = True
        source = MemorySource(name="test", connector=connector)
        assert source.enabled is True
        assert source.priority == 0


class TestMemoryRegistry:
    def test_initialization(self):
        registry = MemoryRegistry()
        # Should have at least core connectors
        sources = registry.list_sources()
        assert "athena" in sources
        assert "session" in sources

    def test_register_connector(self):
        registry = MemoryRegistry()
        mock_connector = MagicMock(spec=MemoryConnector)
        mock_connector.name = "mock"
        mock_connector.enabled = True
        registry.register(mock_connector, priority=10)
        assert "mock" in registry.list_sources()

    def test_unregister_connector(self):
        registry = MemoryRegistry()
        mock_connector = MagicMock(spec=MemoryConnector)
        mock_connector.name = "temp"
        mock_connector.enabled = True
        registry.register(mock_connector)
        assert "temp" in registry.list_sources()
        registry.unregister("temp")
        assert "temp" not in registry.list_sources()

    def test_unregister_nonexistent(self):
        registry = MemoryRegistry()
        registry.unregister("nonexistent")  # Should not raise

    def test_get_connector(self):
        registry = MemoryRegistry()
        connector = registry.get("athena")
        assert connector is not None
        assert connector.name == "athena"

    def test_get_nonexistent_connector(self):
        registry = MemoryRegistry()
        connector = registry.get("nonexistent")
        assert connector is None

    def test_list_sources(self):
        registry = MemoryRegistry()
        sources = registry.list_sources()
        assert isinstance(sources, list)
        assert len(sources) >= 2  # At least athena and session

    def test_get_enabled_sources(self):
        registry = MemoryRegistry()
        enabled = registry.get_enabled_sources()
        assert isinstance(enabled, list)
        # All should be enabled
        assert all(s.enabled for s in enabled)

    def test_get_enabled_sources_sorted_by_priority(self):
        registry = MemoryRegistry()
        mock1 = MagicMock(spec=MemoryConnector)
        mock1.name = "low"
        mock1.enabled = True
        mock2 = MagicMock(spec=MemoryConnector)
        mock2.name = "high"
        mock2.enabled = True
        registry.register(mock1, priority=1)
        registry.register(mock2, priority=10)
        enabled = registry.get_enabled_sources()
        # Higher priority first
        assert enabled[0].name == "high"

    def test_health_check_all(self):
        registry = MemoryRegistry()
        results = registry.health_check_all()
        assert isinstance(results, list)
        assert len(results) >= 2  # At least athena and session

    def test_health_check_all_handles_exceptions(self):
        registry = MemoryRegistry()
        mock_connector = MagicMock(spec=MemoryConnector)
        mock_connector.name = "failing"
        mock_connector.enabled = True
        mock_connector.health_check.side_effect = Exception("Connection refused")
        registry.register(mock_connector)
        results = registry.health_check_all()
        failing = [r for r in results if r.source == "failing"]
        assert len(failing) == 1
        assert failing[0].healthy is False

    def test_close_all(self):
        registry = MemoryRegistry()
        mock_connector = MagicMock(spec=MemoryConnector)
        mock_connector.name = "closeable"
        mock_connector.enabled = True
        registry.register(mock_connector)
        registry.close_all()
        mock_connector.close.assert_called_once()

    def test_close_all_handles_exceptions(self):
        registry = MemoryRegistry()
        mock_connector = MagicMock(spec=MemoryConnector)
        mock_connector.name = "error_close"
        mock_connector.enabled = True
        mock_connector.close.side_effect = Exception("Close failed")
        registry.register(mock_connector)
        registry.close_all()  # Should not raise


class TestGlobalRegistry:
    def test_get_registry_singleton(self):
        reg1 = get_registry()
        reg2 = get_registry()
        assert reg1 is reg2

    def test_get_enabled_connectors(self):
        connectors = get_enabled_connectors()
        assert isinstance(connectors, list)
        assert len(connectors) >= 2  # At least athena and session

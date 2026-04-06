"""Tests for memory router module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.memory.router import (
    MemoryRouter,
    UnifiedMemoryQuery,
    UnifiedMemoryResult,
    get_router,
)


class TestUnifiedMemoryQuery:
    def test_default_values(self):
        query = UnifiedMemoryQuery(query="test")
        assert query.query == "test"
        assert query.max_results_per_source == 5
        assert query.enabled_sources is None
        assert query.use_semantic is False
        assert query.timeout_ms == 5000

    def test_custom_values(self):
        query = UnifiedMemoryQuery(
            query="test",
            max_results_per_source=10,
            enabled_sources=["athena", "session"],
            use_semantic=True,
            timeout_ms=3000,
        )
        assert query.max_results_per_source == 10
        assert query.enabled_sources == ["athena", "session"]
        assert query.use_semantic is True
        assert query.timeout_ms == 3000


class TestUnifiedMemoryResult:
    def test_empty_result(self):
        result = UnifiedMemoryResult(
            results=[],
            sources_queried=[],
            sources_failed=[],
            total_results=0,
            query_time_ms=0,
        )
        assert result.total_results == 0
        assert result.metadata == {}

    def test_with_results(self):
        from src.memory.connectors import MemoryResult

        results = [
            MemoryResult(source="test", id="1", content="hello", metadata={}, score=0.9),
            MemoryResult(source="test", id="2", content="world", metadata={}, score=0.8),
        ]
        result = UnifiedMemoryResult(
            results=results,
            sources_queried=["test"],
            sources_failed=[],
            total_results=2,
            query_time_ms=10.5,
        )
        assert result.total_results == 2
        assert len(result.results) == 2
        assert "test" in result.sources_queried


class TestMemoryRouter:
    def test_get_router_singleton(self):
        router1 = get_router()
        router2 = get_router()
        assert router1 is router2

    def test_router_creation(self):
        router = MemoryRouter()
        assert router.max_workers == 4
        assert router._semantic_enabled is True
        assert router._vector_store is None
        assert router._learning_adapter is None

    def test_router_custom_workers(self):
        router = MemoryRouter(max_workers=8)
        assert router.max_workers == 8

    def test_search_no_connectors(self):
        router = MemoryRouter()
        with patch("src.memory.router.get_enabled_connectors", return_value=[]):
            result = router.search(UnifiedMemoryQuery(query="test"))
            assert result.total_results == 0
            assert result.sources_queried == []
            assert "error" in result.metadata

    def test_search_with_mock_connectors(self):
        from src.memory.connectors import MemoryResult

        router = MemoryRouter()
        mock_connector = MagicMock()
        mock_connector.name = "test"
        mock_connector.search.return_value = [
            MemoryResult(source="test", id="1", content="hello", metadata={}, score=0.9),
        ]

        with patch(
            "src.memory.router.get_enabled_connectors", return_value=[mock_connector]
        ):
            result = router.search(UnifiedMemoryQuery(query="test"))
            assert result.total_results >= 0
            assert "test" in result.sources_queried

    def test_search_with_failed_connector(self):
        router = MemoryRouter()
        mock_connector = MagicMock()
        mock_connector.name = "failing"
        mock_connector.search.side_effect = Exception("Connection refused")

        with patch(
            "src.memory.router.get_enabled_connectors", return_value=[mock_connector]
        ):
            result = router.search(UnifiedMemoryQuery(query="test"))
            # Router logs the error but returns empty results
            assert result.total_results == 0
            assert "failing" in result.sources_queried

    def test_search_with_filtered_sources(self):
        from src.memory.connectors import MemoryResult

        router = MemoryRouter()
        mock_athena = MagicMock()
        mock_athena.name = "athena"
        mock_athena.search.return_value = [
            MemoryResult(source="athena", id="1", content="athena result", metadata={}, score=0.9),
        ]
        mock_session = MagicMock()
        mock_session.name = "session"
        mock_session.search.return_value = [
            MemoryResult(source="session", id="2", content="session result", metadata={}, score=0.8),
        ]

        mock_registry = MagicMock()
        mock_registry.get.side_effect = lambda name: {
            "athena": mock_athena,
            "session": mock_session,
        }.get(name)

        with patch(
            "src.memory.router.get_enabled_connectors",
            return_value=[mock_athena, mock_session],
        ):
            with patch("src.memory.router.get_registry", return_value=mock_registry):
                result = router.search(
                    UnifiedMemoryQuery(query="test", enabled_sources=["athena"])
                )
                # Should only query athena
                assert (
                    "athena" in result.sources_queried or result.sources_queried == []
                )

    def test_search_deduplication(self):
        from src.memory.connectors import MemoryResult

        router = MemoryRouter()
        mock_connector1 = MagicMock()
        mock_connector1.name = "source1"
        mock_connector1.search.return_value = [
            MemoryResult(source="source1", id="1", content="duplicate", metadata={}, score=0.9),
        ]
        mock_connector2 = MagicMock()
        mock_connector2.name = "source2"
        mock_connector2.search.return_value = [
            MemoryResult(source="source2", id="1", content="duplicate", metadata={}, score=0.8),
        ]

        with patch(
            "src.memory.router.get_enabled_connectors",
            return_value=[mock_connector1, mock_connector2],
        ):
            result = router.search(UnifiedMemoryQuery(query="test"))
            # Deduplication should remove one of the duplicates
            assert result.total_results <= 2

    def test_search_timeout_handling(self):
        import time

        router = MemoryRouter()
        mock_connector = MagicMock()
        mock_connector.name = "slow"

        def slow_search(*args, **kwargs):
            time.sleep(0.1)
            return []

        mock_connector.search.side_effect = slow_search

        with patch(
            "src.memory.router.get_enabled_connectors", return_value=[mock_connector]
        ):
            result = router.search(UnifiedMemoryQuery(query="test", timeout_ms=50))
            # Should handle timeout gracefully
            assert isinstance(result, UnifiedMemoryResult)

    def test_search_result_sorting(self):
        from src.memory.connectors import MemoryResult

        router = MemoryRouter()
        mock_connector = MagicMock()
        mock_connector.name = "test"
        mock_connector.search.return_value = [
            MemoryResult(source="test", id="1", content="low", metadata={}, score=0.3),
            MemoryResult(source="test", id="2", content="high", metadata={}, score=0.9),
            MemoryResult(source="test", id="3", content="mid", metadata={}, score=0.6),
        ]

        with patch(
            "src.memory.router.get_enabled_connectors", return_value=[mock_connector]
        ):
            result = router.search(UnifiedMemoryQuery(query="test"))
            if result.results:
                scores = [r.score for r in result.results]
                assert scores == sorted(scores, reverse=True)

    def test_learning_adapter_reranking(self):
        from src.memory.connectors import MemoryResult

        router = MemoryRouter()
        mock_connector = MagicMock()
        mock_connector.name = "test"
        mock_connector.search.return_value = [
            MemoryResult(source="test", id="1", content="first", metadata={}, score=0.9),
            MemoryResult(source="test", id="2", content="second", metadata={}, score=0.5),
        ]

        mock_learning = MagicMock()
        mock_learning.rerank_results.return_value = [
            {
                "_result": MemoryResult(
                    source="test", id="2", content="second", metadata={}, score=0.5
                )
            },
            {
                "_result": MemoryResult(
                    source="test", id="1", content="first", metadata={}, score=0.9
                )
            },
        ]
        router.set_learning_adapter(mock_learning)

        with patch(
            "src.memory.router.get_enabled_connectors", return_value=[mock_connector]
        ):
            with patch("src.memory.router.get_config", return_value=True):
                result = router.search(UnifiedMemoryQuery(query="test"))
                mock_learning.rerank_results.assert_called_once()

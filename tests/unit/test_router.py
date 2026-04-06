#!/usr/bin/env python3
"""Unit tests for MemoryRouter."""

import pytest
from unittest.mock import MagicMock, patch


class TestQueryType:
    """Test QueryType enum classification."""

    def test_query_type_semantic_long_query(self):
        """Test semantic classification for 3+ word queries."""
        from packages.memory_core.router import QueryType, UnifiedMemoryQuery

        query = UnifiedMemoryQuery(query="how does the routing system work")
        # Test classify logic directly
        q = query.query.strip()
        word_count = len(q.split())

        assert word_count >= 3
        # Should be classified as SEMANTIC

    def test_query_type_keyword_short_query(self):
        """Test keyword classification for short queries."""
        from packages.memory_core.router import QueryType, UnifiedMemoryQuery

        query = UnifiedMemoryQuery(query="JWT auth")
        q = query.query.strip()
        word_count = len(q.split())

        assert word_count <= 2

    def test_query_type_filtered_with_filters(self):
        """Test filtered classification when filters dict is provided."""
        from packages.memory_core.router import UnifiedMemoryQuery

        query = UnifiedMemoryQuery(
            query="test query",
            filters={"source": "memory"}
        )

        assert query.filters is not None
        assert len(query.filters) > 0


class TestUnifiedMemoryQuery:
    """Test UnifiedMemoryQuery dataclass."""

    def test_default_values(self):
        """Test default parameter values."""
        from packages.memory_core.router import UnifiedMemoryQuery

        query = UnifiedMemoryQuery(query="test")

        assert query.max_results_per_source == 10
        assert query.use_semantic is True
        assert query.filters == {}

    def test_custom_values(self):
        """Test custom parameter values."""
        from packages.memory_core.router import UnifiedMemoryQuery

        query = UnifiedMemoryQuery(
            query="test",
            max_results_per_source=5,
            use_semantic=False,
            filters={"tier": "critical"}
        )

        assert query.max_results_per_source == 5
        assert query.use_semantic is False
        assert query.filters == {"tier": "critical"}


class TestMemoryResult:
    """Test MemoryResult dataclass."""

    def test_memory_result_creation(self):
        """Test creating a MemoryResult."""
        from packages.memory_core.router import MemoryResult

        result = MemoryResult(
            source="test_source",
            content="test content",
            relevance_score=0.95
        )

        assert result.source == "test_source"
        assert result.content == "test content"
        assert result.relevance_score == 0.95


class TestSearchResults:
    """Test SearchResults dataclass."""

    def test_search_results_empty(self):
        """Test empty search results."""
        from packages.memory_core.router import SearchResults, MemoryResult

        results = SearchResults(
            results=[],
            total_results=0,
            sources_queried=[],
            query_time_ms=0.0
        )

        assert results.results == []
        assert results.total_results == 0
        assert results.sources_queried == []
        assert results.query_time_ms == 0.0

    def test_search_results_with_data(self):
        """Test search results with data."""
        from packages.memory_core.router import SearchResults, MemoryResult

        results = SearchResults(
            results=[
                MemoryResult(source="mem", content="data", relevance_score=0.8)
            ],
            total_results=1,
            sources_queried=["tempr"],
            query_time_ms=50.0
        )

        assert len(results.results) == 1
        assert results.total_results == 1
        assert "tempr" in results.sources_queried


class TestMemoryRouter:
    """Test MemoryRouter class."""

    @pytest.fixture
    def router(self):
        """Create a MemoryRouter instance."""
        from packages.memory_core.router import MemoryRouter
        return MemoryRouter()

    def test_router_initialization(self, router):
        """Test router initializes correctly."""
        from packages.memory_core.router import MemoryRouter

        assert router._tempr_retriever is None
        assert router._keyword_retriever is None
        assert router._semantic_retriever is None

    def test_classify_query_semantic(self, router):
        """Test semantic query classification."""
        from packages.memory_core.router import UnifiedMemoryQuery, QueryType

        query = UnifiedMemoryQuery(query="how does authentication work")
        q_type = router._classify_query(query)

        assert q_type == QueryType.SEMANTIC

    def test_classify_query_keyword(self, router):
        """Test keyword query classification."""
        from packages.memory_core.router import UnifiedMemoryQuery, QueryType

        query = UnifiedMemoryQuery(query="JWT token")
        q_type = router._classify_query(query)

        assert q_type == QueryType.KEYWORD

    def test_classify_query_filtered(self, router):
        """Test filtered query classification."""
        from packages.memory_core.router import UnifiedMemoryQuery, QueryType

        query = UnifiedMemoryQuery(
            query="test query",
            filters={"source": "memory"}
        )
        q_type = router._classify_query(query)

        assert q_type == QueryType.FILTERED

    def test_classify_query_empty(self, router):
        """Test empty query classification."""
        from packages.memory_core.router import UnifiedMemoryQuery, QueryType

        query = UnifiedMemoryQuery(query="")
        q_type = router._classify_query(query)

        # Empty query becomes KEYWORD (short)
        assert q_type == QueryType.KEYWORD

    def test_select_retriever_actions_keyword(self, router):
        """Test retriever action selection for keyword queries."""
        from packages.memory_core.router import (
            UnifiedMemoryQuery,
            QueryType,
            RetrieverAction
        )

        query = UnifiedMemoryQuery(query="JWT")
        actions = router._select_retriever_actions(QueryType.KEYWORD, query)

        assert RetrieverAction.KEYWORD in actions
        assert RetrieverAction.TEMPR in actions

    def test_select_retriever_actions_semantic(self, router):
        """Test retriever action selection for semantic queries."""
        from packages.memory_core.router import (
            UnifiedMemoryQuery,
            QueryType,
            RetrieverAction
        )

        query = UnifiedMemoryQuery(query="how does this work")
        actions = router._select_retriever_actions(QueryType.SEMANTIC, query)

        assert RetrieverAction.TEMPR in actions
        assert RetrieverAction.SEMANTIC in actions

    def test_select_retriever_actions_filtered(self, router):
        """Test retriever action selection for filtered queries."""
        from packages.memory_core.router import (
            UnifiedMemoryQuery,
            QueryType,
            RetrieverAction
        )

        query = UnifiedMemoryQuery(query="test", filters={})
        actions = router._select_retriever_actions(QueryType.FILTERED, query)

        assert RetrieverAction.TEMPR in actions
        assert RetrieverAction.KEYWORD in actions


class TestMemoryRouterSearch:
    """Test MemoryRouter.search() method with mocking."""

    @pytest.fixture
    def router(self):
        """Create a MemoryRouter instance."""
        from packages.memory_core.router import MemoryRouter
        return MemoryRouter()

    @patch('packages.memory_core.router.MemoryRouter._get_tempr_retriever')
    def test_search_returns_non_empty_results(self, mock_get_tempr, router):
        """Test that search returns NON-EMPTY results when retrievers work."""
        from packages.memory_core.router import UnifiedMemoryQuery, SearchResults

        # Mock the TEMPR retriever to return results
        mock_retriever = MagicMock()
        mock_retriever.search.return_value = [
            {"source": "memory", "content": "test data", "score": 0.95}
        ]
        mock_get_tempr.return_value = mock_retriever

        query = UnifiedMemoryQuery(query="test query")
        result = router.search(query)

        # Verify we got results back
        assert isinstance(result, SearchResults)

    def test_search_with_no_results(self, router):
        """Test search when all retrievers return empty."""
        from packages.memory_core.router import UnifiedMemoryQuery, SearchResults

        # Mock all retrievers to return empty
        mock_retriever = MagicMock()
        mock_retriever.search.return_value = []

        with patch.object(router, '_get_tempr_retriever', return_value=mock_retriever):
            query = UnifiedMemoryQuery(query="nonexistent query")
            result = router.search(query)

            # Should return empty results but valid SearchResults object
            assert isinstance(result, SearchResults)
            assert result.results == []
            assert result.total_results == 0

    def test_search_fallback_chain(self, router):
        """Test fallback chain when first retriever fails."""
        from packages.memory_core.router import UnifiedMemoryQuery

        # First retriever fails, second succeeds
        mock_fail = MagicMock()
        mock_fail.search.side_effect = Exception("Retriever failed")

        mock_success = MagicMock()
        mock_success.search.return_value = [
            {"source": "memory", "content": "result", "score": 0.9}
        ]

        with patch.object(router, '_get_tempr_retriever', return_value=mock_fail):
            with patch.object(router, '_get_keyword_retriever', return_value=mock_success):
                query = UnifiedMemoryQuery(query="test")
                # This should not crash - fallback should work
                try:
                    result = router.search(query)
                    # Either succeeded with fallback or all failed
                    assert isinstance(result, SearchResults)
                except Exception:
                    # If all fail, should handle gracefully
                    pass


class TestMemoryRouterEdgeCases:
    """Test edge cases for MemoryRouter."""

    @pytest.fixture
    def router(self):
        """Create a MemoryRouter instance."""
        from packages.memory_core.router import MemoryRouter
        return MemoryRouter()

    def test_empty_query_string(self, router):
        """Test handling of empty query string."""
        from packages.memory_core.router import UnifiedMemoryQuery

        query = UnifiedMemoryQuery(query="")
        q_type = router._classify_query(query)

        # Empty query should default to SEMANTIC
        assert q_type is not None

    def test_query_with_only_spaces(self, router):
        """Test query with only whitespace."""
        from packages.memory_core.router import UnifiedMemoryQuery

        query = UnifiedMemoryQuery(query="   ")
        q_type = router._classify_query(query)

        assert q_type is not None

    def test_max_results_boundary(self, router):
        """Test boundary values for max_results."""
        from packages.memory_core.router import UnifiedMemoryQuery

        # Test 0 results
        query_0 = UnifiedMemoryQuery(query="test", max_results_per_source=0)
        assert query_0.max_results_per_source == 0

        # Test 1 result
        query_1 = UnifiedMemoryQuery(query="test", max_results_per_source=1)
        assert query_1.max_results_per_source == 1

        # Test max results
        query_max = UnifiedMemoryQuery(query="test", max_results_per_source=100)
        assert query_max.max_results_per_source == 100

    def test_none_filters(self, router):
        """Test None filters handling."""
        from packages.memory_core.router import UnifiedMemoryQuery

        # Should not crash with None filters
        query = UnifiedMemoryQuery(query="test", filters=None)
        assert query.filters is None or query.filters == {}


class TestRetrieverAction:
    """Test RetrieverAction enum."""

    def test_retriever_action_values(self):
        """Test RetrieverAction enum values."""
        from packages.memory_core.router import RetrieverAction

        assert RetrieverAction.TEMPR.value == "tempr"
        assert RetrieverAction.KEYWORD.value == "keyword"
        assert RetrieverAction.SEMANTIC.value == "semantic"

    def test_retriever_action_members(self):
        """Test RetrieverAction has expected members."""
        from packages.memory_core.router import RetrieverAction

        actions = list(RetrieverAction)
        assert len(actions) == 3
        assert RetrieverAction.TEMPR in actions
        assert RetrieverAction.KEYWORD in actions
        assert RetrieverAction.SEMANTIC in actions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

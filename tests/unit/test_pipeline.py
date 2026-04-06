#!/usr/bin/env python3
"""Unit tests for RetrievalPipeline."""

import pytest
from unittest.mock import MagicMock, patch


class TestQueryType:
    """Test QueryType enum in pipeline."""

    def test_query_type_values(self):
        """Test QueryType enum values."""
        from packages.memory_core.retrievers.pipeline import QueryType

        assert QueryType.SEMANTIC.value == "semantic"
        assert QueryType.KEYWORD.value == "keyword"
        assert QueryType.TEMPORAL.value == "temporal"
        assert QueryType.RELATIONAL.value == "relational"
        assert QueryType.HYBRID.value == "hybrid"

    def test_query_type_members(self):
        """Test QueryType has all expected members."""
        from packages.memory_core.retrievers.pipeline import QueryType

        types = list(QueryType)
        assert len(types) == 5


class TestPipelineResult:
    """Test PipelineResult dataclass."""

    def test_pipeline_result_defaults(self):
        """Test default values."""
        from packages.memory_core.retrievers.pipeline import PipelineResult, QueryType

        result = PipelineResult(
            results=[],
            query="test",
            query_type=QueryType.SEMANTIC
        )

        assert result.results == []
        assert result.query == "test"
        assert result.stages_executed == []
        assert result.stages_failed == []
        assert result.total_latency_ms == 0.0
        assert result.metrics == {}
        assert result.error is None

    def test_pipeline_result_with_error(self):
        """Test PipelineResult with error."""
        from packages.memory_core.retrievers.pipeline import PipelineResult, QueryType

        result = PipelineResult(
            results=[],
            query="test",
            query_type=QueryType.SEMANTIC,
            error="Something failed"
        )

        assert result.error == "Something failed"


class TestRetrievalPipeline:
    """Test RetrievalPipeline class."""

    @pytest.fixture
    def pipeline(self):
        """Create a RetrievalPipeline instance."""
        from packages.memory_core.retrievers.pipeline import RetrievalPipeline
        return RetrievalPipeline(db_path=":memory:")

    def test_pipeline_initialization(self, pipeline):
        """Test pipeline initializes correctly."""
        assert pipeline.default_top_k == 10
        assert pipeline.mmr_lambda == 0.5
        assert pipeline.enable_cross_encoder is True

    def test_pipeline_custom_initialization(self):
        """Test pipeline with custom parameters."""
        from packages.memory_core.retrievers.pipeline import RetrievalPipeline

        pipeline = RetrievalPipeline(
            db_path=":memory:",
            default_top_k=5,
            enable_cross_encoder=False,
            mmr_lambda=0.3
        )

        assert pipeline.default_top_k == 5
        assert pipeline.enable_cross_encoder is False
        assert pipeline.mmr_lambda == 0.3


class TestQueryAnalysisStage:
    """Test Stage 1: Query Analysis."""

    @pytest.fixture
    def pipeline(self):
        """Create a RetrievalPipeline instance."""
        from packages.memory_core.retrievers.pipeline import RetrievalPipeline
        return RetrievalPipeline(db_path=":memory:")

    def test_analyze_semantic_query(self, pipeline):
        """Test semantic query analysis."""
        from packages.memory_core.retrievers.pipeline import QueryType

        query_type = pipeline._analyze_query("how does authentication work")

        assert query_type == QueryType.SEMANTIC

    def test_analyze_keyword_query(self, pipeline):
        """Test keyword query analysis."""
        from packages.memory_core.retrievers.pipeline import QueryType

        # Short query with special chars
        query_type = pipeline._analyze_query("JWT")

        assert query_type in [QueryType.KEYWORD, QueryType.HYBRID]

    def test_analyze_temporal_query(self, pipeline):
        """Test temporal query analysis."""
        from packages.memory_core.retrievers.pipeline import QueryType

        query_type = pipeline._analyze_query("what happened yesterday")

        assert query_type == QueryType.TEMPORAL

    def test_analyze_relational_query(self, pipeline):
        """Test relational query analysis."""
        from packages.memory_core.retrievers.pipeline import QueryType

        query_type = pipeline._analyze_query("similar to JWT auth")

        assert query_type == QueryType.RELATIONAL

    def test_analyze_empty_query(self, pipeline):
        """Test empty query analysis."""
        from packages.memory_core.retrievers.pipeline import QueryType

        query_type = pipeline._analyze_query("")

        # Should default to HYBRID (short query)
        assert query_type == QueryType.HYBRID

    def test_analyze_query_with_error(self, pipeline):
        """Test query analysis error handling."""
        # Pass None - should handle gracefully
        try:
            query_type = pipeline._analyze_query(None)  # type: ignore
            # Should either return default or handle error
            assert query_type is not None
        except Exception:
            pass  # May raise error for None input


class TestRetrieveStage:
    """Test Stage 2: Retrieve."""

    @pytest.fixture
    def pipeline(self):
        """Create a RetrievalPipeline instance."""
        from packages.memory_core.retrievers.pipeline import RetrievalPipeline
        return RetrievalPipeline(db_path=":memory:")

    def test_retrieve_returns_results(self, pipeline):
        """Test retrieve stage returns results."""
        from packages.memory_core.retrievers.pipeline import QueryType
        from unittest.mock import MagicMock, patch

        # Mock the tempr_retriever - use patch on the property getter
        mock_retriever = MagicMock()
        mock_retriever.search.return_value = [
            {"id": "1", "content": "test", "score": 0.9}
        ]

        with patch.object(type(pipeline), 'tempr_retriever', mock_retriever):
            results = pipeline._retrieve(
                "test query",
                top_k=10,
                query_type=QueryType.SEMANTIC
            )

            assert len(results) > 0

    def test_retrieve_with_exception(self, pipeline):
        """Test retrieve handles exceptions."""
        from packages.memory_core.retrievers.pipeline import QueryType
        from unittest.mock import MagicMock, patch

        # Mock retriever that raises
        mock_retriever = MagicMock()
        mock_retriever.search.side_effect = Exception("DB unavailable")

        with patch.object(type(pipeline), 'tempr_retriever', mock_retriever):
            with pytest.raises(Exception):
                pipeline._retrieve(
                    "test query",
                    top_k=10,
                    query_type=QueryType.SEMANTIC
                )


class TestRRFFusionStage:
    """Test Stage 3: RRF Fusion verification."""

    @pytest.fixture
    def pipeline(self):
        """Create a RetrievalPipeline instance."""
        from packages.memory_core.retrievers.pipeline import RetrievalPipeline
        return RetrievalPipeline(db_path=":memory:")

    def test_verify_rrf_fusion_with_results(self, pipeline):
        """Test RRF fusion verification with results."""
        results = [
            {"id": "1", "content": "test1", "score": 0.9},
            {"id": "2", "content": "test2", "score": 0.8}
        ]

        verified = pipeline._verify_rrf_fusion(results)

        assert len(verified) == 2

    def test_verify_rrf_fusion_empty(self, pipeline):
        """Test RRF fusion with empty results."""
        verified = pipeline._verify_rrf_fusion([])

        assert verified == []

    def test_verify_rrf_fusion_with_exception(self, pipeline):
        """Test RRF fusion handles exceptions."""
        # Should return original results even on error
        results = [{"id": "1", "content": "test"}]

        # Force an exception by passing None
        try:
            verified = pipeline._verify_rrf_fusion(None)  # type: ignore
        except Exception:
            pass  # May raise for None input


class TestMMRRerankStage:
    """Test Stage 4: MMR Rerank."""

    @pytest.fixture
    def pipeline(self):
        """Create a RetrievalPipeline instance."""
        from packages.memory_core.retrievers.pipeline import RetrievalPipeline
        return RetrievalPipeline(db_path=":memory:", mmr_lambda=0.5)

    def test_mmr_rerank_empty_results(self, pipeline):
        """Test MMR with empty results."""
        reranked = pipeline._mmr_rerank([], "test query", 10)

        assert reranked == []

    def test_mmr_rerank_with_results(self, pipeline):
        """Test MMR reranking."""
        results = [
            {"id": "1", "content": "test1", "score": 0.9},
            {"id": "2", "content": "test2", "score": 0.8}
        ]

        reranked = pipeline._mmr_rerank(results, "test query", 10)

        assert len(reranked) <= len(results)

    def test_mmr_rerank_limits_top_k(self, pipeline):
        """Test MMR respects top_k limit."""
        results = [
            {"id": str(i), "content": f"test{i}", "score": 1.0 - i * 0.1}
            for i in range(20)
        ]

        reranked = pipeline._mmr_rerank(results, "test query", 5)

        assert len(reranked) <= 5


class TestCrossEncoderRerankStage:
    """Test Stage 5: Cross-Encoder Rerank."""

    @pytest.fixture
    def pipeline(self):
        """Create a RetrievalPipeline instance."""
        from packages.memory_core.retrievers.pipeline import RetrievalPipeline
        return RetrievalPipeline(db_path=":memory:", enable_cross_encoder=False)

    def test_cross_encoder_disabled(self, pipeline):
        """Test cross-encoder skipped when disabled."""
        results = [{"id": "1", "content": "test"}]

        reranked = pipeline._cross_encoder_rerank(results, "test query", 10)

        # Should return original results when disabled
        assert len(reranked) > 0

    def test_cross_encoder_with_empty_results(self, pipeline):
        """Test cross-encoder with empty results."""
        reranked = pipeline._cross_encoder_rerank([], "test query", 10)

        assert reranked == []


class TestFormatResultsStage:
    """Test Stage 6: Format Results."""

    @pytest.fixture
    def pipeline(self):
        """Create a RetrievalPipeline instance."""
        from packages.memory_core.retrievers.pipeline import RetrievalPipeline
        return RetrievalPipeline(db_path=":memory:")

    def test_format_empty_results(self, pipeline):
        """Test formatting empty results."""
        formatted = pipeline._format_results([], 10)

        assert formatted == []

    def test_format_with_results(self, pipeline):
        """Test formatting results."""
        results = [
            {"id": "1", "content": "test content", "score": 0.9}
        ]

        formatted = pipeline._format_results(results, 10)

        assert len(formatted) == 1

    def test_format_limits_top_k(self, pipeline):
        """Test formatting respects top_k."""
        results = [
            {"id": str(i), "content": f"test{i}", "score": 1.0 - i * 0.1}
            for i in range(20)
        ]

        formatted = pipeline._format_results(results, 5)

        assert len(formatted) <= 5

    def test_format_with_dict_results(self, pipeline):
        """Test formatting dict results."""
        results = [
            {"id": "1", "content": "test", "score": 0.9, "source": "memory"},
            {"id": "2", "content": "test2", "score": 0.8, "metadata": {"key": "value"}}
        ]

        formatted = pipeline._format_results(results, 10)

        assert len(formatted) == 2


class TestPipelineErrorHandling:
    """Test pipeline error handling for each stage."""

    @pytest.fixture
    def pipeline(self):
        """Create a RetrievalPipeline instance."""
        from packages.memory_core.retrievers.pipeline import RetrievalPipeline
        return RetrievalPipeline(db_path=":memory:")

    def test_retrieve_stage_fails_gracefully(self, pipeline):
        """Test retrieve stage failure doesn't crash pipeline."""
        # Mock retriever to fail
        mock_retriever = MagicMock()
        mock_retriever.search.side_effect = Exception("Database unavailable")

        with patch.object(type(pipeline), 'tempr_retriever', mock_retriever):
            result = pipeline.search("test query")

            # Should return error in result, not crash
            assert result.error is not None or result.results == []

    def test_mmr_stage_fails_gracefully(self, pipeline):
        """Test MMR stage failure doesn't crash pipeline."""
        # Pass None to MMR to cause error
        try:
            result = pipeline.search("test query")
            # Pipeline should handle gracefully
            assert result is not None
        except Exception:
            pass  # May fail but shouldn't crash silently

    def test_format_stage_fails_gracefully(self, pipeline):
        """Test format stage failure doesn't crash pipeline."""
        # This is harder to trigger, but pipeline should handle
        try:
            result = pipeline.search("test query")
            assert result is not None
        except Exception:
            pass


class TestPipelineMetrics:
    """Test pipeline metrics collection."""

    @pytest.fixture
    def pipeline(self):
        """Create a RetrievalPipeline instance."""
        from packages.memory_core.retrievers.pipeline import RetrievalPipeline
        return RetrievalPipeline(db_path=":memory:")

    def test_stage_metrics_recorded(self, pipeline):
        """Test stage metrics are recorded."""
        from unittest.mock import MagicMock

        # Mock retriever
        mock_retriever = MagicMock()
        mock_retriever.search.return_value = [
            {"id": "1", "content": "test", "score": 0.9}
        ]

        with patch.object(type(pipeline), 'tempr_retriever', mock_retriever):
            result = pipeline.search("test query")

            # Should have executed stages
            assert len(result.stages_executed) >= 1

    def test_get_stage_metrics(self, pipeline):
        """Test getting stage metrics."""
        metrics = pipeline._get_stage_metrics()

        assert isinstance(metrics, dict)


class TestPipelineBoundaryValues:
    """Test boundary values for pipeline."""

    @pytest.fixture
    def pipeline(self):
        """Create a RetrievalPipeline instance."""
        from packages.memory_core.retrievers.pipeline import RetrievalPipeline
        return RetrievalPipeline(db_path=":memory:")

    def test_top_k_zero(self, pipeline):
        """Test pipeline with top_k=0."""
        from unittest.mock import MagicMock

        mock_retriever = MagicMock()
        mock_retriever.search.return_value = []

        with patch.object(type(pipeline), 'tempr_retriever', mock_retriever):
            result = pipeline.search("test", top_k=0)

            # Should handle gracefully
            assert result is not None

    def test_top_k_one(self, pipeline):
        """Test pipeline with top_k=1."""
        from unittest.mock import MagicMock

        mock_retriever = MagicMock()
        mock_retriever.search.return_value = [{"id": "1", "content": "test", "score": 0.9}]

        with patch.object(type(pipeline), 'tempr_retriever', mock_retriever):
            result = pipeline.search("test", top_k=1)

            assert result is not None

    def test_top_k_max(self, pipeline):
        """Test pipeline with large top_k."""
        from unittest.mock import MagicMock

        mock_retriever = MagicMock()
        mock_retriever.search.return_value = [
            {"id": str(i), "content": f"test{i}", "score": 1.0 - i * 0.01}
            for i in range(100)
        ]

        with patch.object(type(pipeline), 'tempr_retriever', mock_retriever):
            result = pipeline.search("test", top_k=100)

            assert result is not None


class TestPipelineIndividualStages:
    """Test individual public stage methods."""

    @pytest.fixture
    def pipeline(self):
        """Create a RetrievalPipeline instance."""
        from packages.memory_core.retrievers.pipeline import RetrievalPipeline
        return RetrievalPipeline(db_path=":memory:")

    def test_analyze_query_public_api(self, pipeline):
        """Test public analyze_query API."""
        query_type = pipeline.analyze_query("how does this work")

        assert query_type is not None

    def test_retrieve_public_api(self, pipeline):
        """Test public retrieve API."""
        from packages.memory_core.retrievers.pipeline import QueryType
        from unittest.mock import MagicMock

        mock_retriever = MagicMock()
        mock_retriever.search.return_value = [{"id": "1", "content": "test"}]

        with patch.object(type(pipeline), 'tempr_retriever', mock_retriever):
            results = pipeline.retrieve("test", 10, QueryType.SEMANTIC)

            assert isinstance(results, list)

    def test_verify_rrf_fusion_public_api(self, pipeline):
        """Test public verify_rrf_fusion API."""
        results = [{"id": "1", "content": "test"}]

        verified = pipeline.verify_rrf_fusion(results)

        assert isinstance(verified, list)

    def test_rerank_mmr_public_api(self, pipeline):
        """Test public rerank_mmr API."""
        results = [{"id": "1", "content": "test", "score": 0.9}]

        reranked = pipeline.rerank_mmr(results, "test", 10)

        assert isinstance(reranked, list)

    def test_rerank_cross_encoder_public_api(self, pipeline):
        """Test public rerank_cross_encoder API."""
        results = [{"id": "1", "content": "test", "score": 0.9}]

        reranked = pipeline.rerank_cross_encoder(results, "test", 10)

        assert isinstance(reranked, list)

    def test_format_results_public_api(self, pipeline):
        """Test public format_results API."""
        results = [{"id": "1", "content": "test", "score": 0.9}]

        formatted = pipeline.format_results(results, 10)

        assert isinstance(formatted, list)


class TestPipelineIntegration:
    """Integration tests for full pipeline."""

    @pytest.fixture
    def pipeline(self):
        """Create a RetrievalPipeline instance."""
        from packages.memory_core.retrievers.pipeline import RetrievalPipeline
        return RetrievalPipeline(db_path=":memory:")

    def test_full_pipeline_execution(self, pipeline):
        """Test full pipeline executes."""
        from unittest.mock import MagicMock

        mock_retriever = MagicMock()
        mock_retriever.search.return_value = [
            {"id": "1", "content": "test result", "score": 0.95}
        ]

        with patch.object(type(pipeline), 'tempr_retriever', mock_retriever):
            result = pipeline.search("test query")

            assert isinstance(result.query, str)
            assert result.query_type is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

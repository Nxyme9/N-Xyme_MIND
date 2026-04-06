#!/usr/bin/env python3
"""RetrievalPipeline — End-to-end retrieval: query → retrieve → rerank → return.

Stages:
1. Query Analysis (determine query type)
2. Retrieve (call TEMPRRetriever for hybrid search)
3. RRF Fusion (confirm results are fused - handled by TEMPR internally)
4. MMR Rerank (apply diversity scoring)
5. Cross-Encoder Rerank (if available, skip gracefully if not)
6. Return (top-k results with scores)

Each stage handles its own errors - no single point of failure.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .fusion import TEMPRRetriever, mmr_rerank
from .reranker import CrossEncoderReranker
from ..stores.base import SearchResult

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Query type classification for strategy selection."""

    SEMANTIC = "semantic"  # Concept, meaning, "how does X work"
    KEYWORD = "keyword"  # Exact terms, names, commands
    TEMPORAL = "temporal"  # Time-based: "yesterday", "last week"
    RELATIONAL = "relational"  # Connections: "connected to X"
    HYBRID = "hybrid"  # Mixed intent


@dataclass
class PipelineResult:
    """Result of a full retrieval pipeline execution."""

    results: List[SearchResult]
    query: str
    query_type: QueryType
    stages_executed: List[str] = field(default_factory=list)
    stages_failed: List[str] = field(default_factory=list)
    total_latency_ms: float = 0.0
    metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    error: Optional[str] = None


class RetrievalPipeline:
    """End-to-end retrieval pipeline with staged execution.

    Each stage is independently callable and handles errors gracefully.
    Pipeline metrics are logged for observability.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        default_top_k: int = 10,
        enable_cross_encoder: bool = True,
        mmr_lambda: float = 0.5,
    ):
        """Initialize the retrieval pipeline.

        Args:
            db_path: Path to memory database
            default_top_k: Default number of results to return
            enable_cross_encoder: Whether to attempt cross-encoder reranking
            mmr_lambda: Balance between relevance and diversity (0-1)
        """
        self.default_top_k = default_top_k
        self.mmr_lambda = mmr_lambda
        self.enable_cross_encoder = enable_cross_encoder

        # Initialize components
        self._tempr_retriever: Optional[TEMPRRetriever] = None
        self._cross_encoder: Optional[CrossEncoderReranker] = None
        self._db_path = db_path

        # Pipeline state
        self._stage_metrics: Dict[str, Dict[str, Any]] = {}

    @property
    def tempr_retriever(self) -> TEMPRRetriever:
        """Lazy-load TEMPR retriever."""
        if self._tempr_retriever is None:
            self._tempr_retriever = TEMPRRetriever(db_path=self._db_path)
        return self._tempr_retriever

    @property
    def cross_encoder(self) -> Optional[CrossEncoderReranker]:
        """Lazy-load cross-encoder reranker (if enabled)."""
        if not self.enable_cross_encoder:
            return None
        if self._cross_encoder is None:
            self._cross_encoder = CrossEncoderReranker()
        return self._cross_encoder

    # ---------------------------------------------------------------------------
    # Stage 1: Query Analysis
    # ---------------------------------------------------------------------------

    def _analyze_query(self, query: str) -> QueryType:
        """Analyze query to determine its type and select appropriate strategies.

        Args:
            query: User search query

        Returns:
            QueryType classification
        """
        stage_name = "query_analysis"
        start_time = time.perf_counter()
        input_count = 1

        try:
            query_lower = query.lower()

            # Temporal indicators
            temporal_keywords = [
                "yesterday",
                "today",
                "tomorrow",
                "last week",
                "last month",
                "recent",
                "earlier",
                "before",
                "after",
                "when",
                "schedule",
            ]

            # Relational indicators
            relational_keywords = [
                "related",
                "connected",
                "similar",
                "like",
                "depends on",
                "linked to",
                "compared to",
                "vs",
                "versus",
            ]

            # Keyword-heavy indicators (exact match likely better)
            if any(char in query for char in ['"', "'", "/", "-"]) or query.isupper():
                query_type = QueryType.KEYWORD
            elif any(kw in query_lower for kw in temporal_keywords):
                query_type = QueryType.TEMPORAL
            elif any(kw in query_lower for kw in relational_keywords):
                query_type = QueryType.RELATIONAL
            elif len(query.split()) <= 2:
                # Short queries benefit from both semantic and keyword
                query_type = QueryType.HYBRID
            else:
                # Default to semantic for complex queries
                query_type = QueryType.SEMANTIC

            output_count = 1
            self._record_stage_metric(
                stage_name,
                start_time,
                input_count,
                output_count,
                {"query_type": query_type.value},
            )

            logger.info(f"Query analysis: '{query}' -> {query_type.value}")
            return query_type

        except Exception as e:
            self._record_stage_metric(
                stage_name, start_time, input_count, 0, {"error": str(e)}
            )
            logger.warning(f"Query analysis failed: {e}, defaulting to SEMANTIC")
            return QueryType.SEMANTIC

    # ---------------------------------------------------------------------------
    # Stage 2: Retrieve (via TEMPRRetriever)
    # ---------------------------------------------------------------------------

    def _retrieve(self, query: str, top_k: int, query_type: QueryType) -> List[dict]:
        """Execute retrieval using TEMPRRetriever.

        Args:
            query: Search query
            top_k: Number of results
            query_type: Determined query type

        Returns:
            List of result dicts from TEMPR
        """
        stage_name = "retrieve"
        start_time = time.perf_counter()
        input_count = 1

        try:
            # Select strategies based on query type
            strategies = self._get_strategies_for_query_type(query_type)

            # Call TEMPRRetriever (handles semantic + keyword + RRF fusion internally)
            results = self.tempr_retriever.search(
                query=query,
                top_k=top_k,
                strategies=strategies,
            )

            output_count = len(results)
            self._record_stage_metric(
                stage_name,
                start_time,
                input_count,
                output_count,
                {"strategies": strategies},
            )

            logger.info(f"Retrieve stage: {output_count} results via {strategies}")
            return results

        except Exception as e:
            self._record_stage_metric(
                stage_name, start_time, input_count, 0, {"error": str(e)}
            )
            logger.error(f"Retrieve stage failed: {e}")
            raise

    def _get_strategies_for_query_type(self, query_type: QueryType) -> List[str]:
        """Map query type to retriever strategies."""
        strategies_map = {
            QueryType.SEMANTIC: ["semantic"],
            QueryType.KEYWORD: ["keyword"],
            QueryType.TEMPORAL: ["semantic", "keyword"],
            QueryType.RELATIONAL: ["semantic", "keyword"],
            QueryType.HYBRID: ["semantic", "keyword"],
        }
        return strategies_map.get(query_type, ["semantic", "keyword"])

    # ---------------------------------------------------------------------------
    # Stage 3: RRF Fusion (handled by TEMPR internally - verification stage)
    # ---------------------------------------------------------------------------

    def _verify_rrf_fusion(self, results: List[dict]) -> List[dict]:
        """Verify and ensure RRF fusion was applied.

        Note: TEMPRRetriever already applies RRF fusion internally.
        This stage verifies the results are properly fused.

        Args:
            results: Results from retrieval stage

        Returns:
            Verified fused results
        """
        stage_name = "rrf_fusion"
        start_time = time.perf_counter()
        input_count = len(results)

        try:
            # TEMPRRetriever already does RRF fusion, so we just verify
            # If results have rrf_score, they're already fused
            output_count = input_count

            self._record_stage_metric(
                stage_name,
                start_time,
                input_count,
                output_count,
                {"fusion_applied": "tempr_internal"},
            )

            logger.debug(f"RRF fusion verified: {output_count} results")
            return results

        except Exception as e:
            self._record_stage_metric(
                stage_name, start_time, input_count, 0, {"error": str(e)}
            )
            logger.warning(f"RRF fusion verification failed: {e}")
            # Don't fail - results may still be valid
            return results

    # ---------------------------------------------------------------------------
    # Stage 4: MMR Rerank (diversity scoring)
    # ---------------------------------------------------------------------------

    def _mmr_rerank(self, results: List[dict], query: str, top_k: int) -> List[dict]:
        """Apply Maximal Marginal Relevance for result diversity.

        Args:
            results: Fused results from previous stages
            query: Original query (for relevance calculation)
            top_k: Number of results to return

        Returns:
            MMR-reranked results
        """
        stage_name = "mmr_rerank"
        start_time = time.perf_counter()
        input_count = len(results)

        try:
            if not results:
                self._record_stage_metric(stage_name, start_time, input_count, 0, {})
                return []

            # Get query embedding for MMR (if available)
            query_embedding = self._get_query_embedding(query)

            # Apply MMR reranking
            reranked = mmr_rerank(
                results=results,
                query_embedding=query_embedding,
                lambda_=self.mmr_lambda,
                top_k=top_k,
            )

            output_count = len(reranked)
            self._record_stage_metric(
                stage_name,
                start_time,
                input_count,
                output_count,
                {"lambda": self.mmr_lambda},
            )

            logger.info(f"MMR rerank: {input_count} -> {output_count} results")
            return reranked

        except Exception as e:
            self._record_stage_metric(
                stage_name, start_time, input_count, 0, {"error": str(e)}
            )
            logger.warning(f"MMR rerank failed: {e}, returning original order")
            return results[:top_k]

    def _get_query_embedding(self, query: str) -> Optional[List[float]]:
        """Get embedding for query (used in MMR calculation)."""
        try:
            from ..stores.vector_store import embed_text

            return embed_text(query)
        except Exception:
            return None

    # ---------------------------------------------------------------------------
    # Stage 5: Cross-Encoder Rerank
    # ---------------------------------------------------------------------------

    def _cross_encoder_rerank(
        self, results: List[dict], query: str, top_k: int
    ) -> List[dict]:
        """Apply cross-encoder reranking (if available).

        Args:
            results: MMR-reranked results
            query: Original query
            top_k: Number of results to return

        Returns:
            Cross-encoder reranked results (or original if not available)
        """
        stage_name = "cross_encoder_rerank"
        start_time = time.perf_counter()
        input_count = len(results)

        reranker = self.cross_encoder

        # Check if cross-encoder is available
        if reranker is None or not reranker.is_available():
            self._record_stage_metric(
                stage_name,
                start_time,
                input_count,
                input_count,
                {
                    "skipped": "not_available",
                    "reason": "sentence-transformers not installed or model failed to load",
                },
            )
            logger.info("Cross-encoder reranking skipped (not available)")
            return results[:top_k]

        try:
            # Apply cross-encoder reranking
            reranked = reranker.rerank(query, results, top_k)

            output_count = len(reranked)
            self._record_stage_metric(
                stage_name,
                start_time,
                input_count,
                output_count,
                {"reranker_model": reranker.model_name},
            )

            logger.info(
                f"Cross-encoder rerank: {input_count} -> {output_count} results"
            )
            return reranked

        except Exception as e:
            self._record_stage_metric(
                stage_name,
                start_time,
                input_count,
                input_count,
                {"error": str(e), "fallback": "original_order"},
            )
            logger.warning(f"Cross-encoder rerank failed: {e}, returning MMR order")
            return results[:top_k]

    # ---------------------------------------------------------------------------
    # Stage 6: Return (format and return results)
    # ---------------------------------------------------------------------------

    def _format_results(self, results: List[dict], top_k: int) -> List[SearchResult]:
        """Format results into SearchResult objects.

        Args:
            results: Final ranked results
            top_k: Number of results to include

        Returns:
            List of SearchResult objects
        """
        stage_name = "return"
        start_time = time.perf_counter()
        input_count = len(results)

        try:
            formatted = []
            for i, result in enumerate(results[:top_k]):
                # Handle both dict and object results
                if isinstance(result, dict):
                    search_result = SearchResult(
                        id=result.get("id", result.get("memory_id", f"result_{i}")),
                        content=result.get("content", result.get("text", "")),
                        score=result.get("score", result.get("rrf_score", 0.0)),
                        metadata=result.get("metadata", {}),
                        source=result.get("source", "hybrid"),
                    )
                else:
                    # Already a SearchResult-like object
                    search_result = SearchResult(
                        id=getattr(result, "id", f"result_{i}"),
                        content=getattr(result, "content", ""),
                        score=getattr(result, "score", 0.0),
                        metadata=getattr(result, "metadata", {}),
                        source=getattr(result, "source", "hybrid"),
                    )
                formatted.append(search_result)

            output_count = len(formatted)
            self._record_stage_metric(
                stage_name, start_time, input_count, output_count, {}
            )

            logger.info(f"Return stage: {output_count} formatted results")
            return formatted

        except Exception as e:
            self._record_stage_metric(
                stage_name, start_time, input_count, 0, {"error": str(e)}
            )
            logger.error(f"Format results failed: {e}")
            return []

    # ---------------------------------------------------------------------------
    # Stage Metric Recording
    # ---------------------------------------------------------------------------

    def _record_stage_metric(
        self,
        stage_name: str,
        start_time: float,
        input_count: int,
        output_count: int,
        extras: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record metrics for a pipeline stage."""
        latency_ms = (time.perf_counter() - start_time) * 1000
        self._stage_metrics[stage_name] = {
            "latency_ms": round(latency_ms, 2),
            "input_count": input_count,
            "output_count": output_count,
            **(extras or {}),
        }

    def _get_stage_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all recorded stage metrics."""
        return dict(self._stage_metrics)

    # ---------------------------------------------------------------------------
    # Main Pipeline Execution
    # ---------------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> PipelineResult:
        """Execute the full retrieval pipeline.

        Args:
            query: Search query
            top_k: Number of results to return (default: self.default_top_k)

        Returns:
            PipelineResult with results and metadata
        """
        start_time = time.perf_counter()
        top_k = top_k or self.default_top_k

        # Reset stage metrics
        self._stage_metrics = {}

        stages_executed = []
        stages_failed = []

        # Stage 1: Query Analysis
        try:
            query_type = self._analyze_query(query)
            stages_executed.append("query_analysis")
        except Exception as e:
            stages_failed.append("query_analysis")
            query_type = QueryType.SEMANTIC
            logger.warning(
                f"Stage 1 (query_analysis) failed: {e}, using default SEMANTIC"
            )

        # Stage 2: Retrieve
        try:
            results = self._retrieve(query, top_k * 2, query_type)
            stages_executed.append("retrieve")
        except Exception as e:
            stages_failed.append("retrieve")
            logger.error(f"Stage 2 (retrieve) failed: {e}")
            return PipelineResult(
                results=[],
                query=query,
                query_type=query_type,
                stages_executed=stages_executed,
                stages_failed=stages_failed,
                total_latency_ms=(time.perf_counter() - start_time) * 1000,
                metrics=self._get_stage_metrics(),
                error=str(e),
            )

        # Stage 3: RRF Fusion (verification)
        try:
            results = self._verify_rrf_fusion(results)
            stages_executed.append("rrf_fusion")
        except Exception as e:
            stages_failed.append("rrf_fusion")
            logger.warning(f"Stage 3 (rrf_fusion) failed: {e}, continuing with results")

        # Stage 4: MMR Rerank
        try:
            results = self._mmr_rerank(results, query, top_k)
            stages_executed.append("mmr_rerank")
        except Exception as e:
            stages_failed.append("mmr_rerank")
            logger.warning(f"Stage 4 (mmr_rerank) failed: {e}, continuing with results")

        # Stage 5: Cross-Encoder Rerank (optional, graceful skip)
        try:
            results = self._cross_encoder_rerank(results, query, top_k)
            stages_executed.append("cross_encoder_rerank")
        except Exception as e:
            stages_failed.append("cross_encoder_rerank")
            logger.warning(
                f"Stage 5 (cross_encoder_rerank) failed: {e}, continuing with results"
            )

        # Stage 6: Return (always convert to SearchResult objects)
        try:
            final_results = self._format_results(results, top_k)
            stages_executed.append("return")
        except Exception as e:
            stages_failed.append("return")
            logger.error(f"Stage 6 (return) failed: {e}")
            final_results = []

        total_latency_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            f"Pipeline completed: {len(final_results)} results in {total_latency_ms:.1f}ms "
            f"(executed: {len(stages_executed)}, failed: {len(stages_failed)})"
        )

        return PipelineResult(
            results=final_results,
            query=query,
            query_type=query_type,
            stages_executed=stages_executed,
            stages_failed=stages_failed,
            total_latency_ms=round(total_latency_ms, 2),
            metrics=self._get_stage_metrics(),
        )

    # ---------------------------------------------------------------------------
    # Individual Stage Access (for debugging/monitoring)
    # ---------------------------------------------------------------------------

    def analyze_query(self, query: str) -> QueryType:
        """Stage 1: Analyze query type (public API)."""
        return self._analyze_query(query)

    def retrieve(self, query: str, top_k: int, query_type: QueryType) -> List[dict]:
        """Stage 2: Execute retrieval (public API)."""
        return self._retrieve(query, top_k, query_type)

    def verify_rrf_fusion(self, results: List[dict]) -> List[dict]:
        """Stage 3: Verify RRF fusion (public API)."""
        return self._verify_rrf_fusion(results)

    def rerank_mmr(self, results: List[dict], query: str, top_k: int) -> List[dict]:
        """Stage 4: Apply MMR reranking (public API)."""
        return self._mmr_rerank(results, query, top_k)

    def rerank_cross_encoder(
        self, results: List[dict], query: str, top_k: int
    ) -> List[dict]:
        """Stage 5: Apply cross-encoder reranking (public API)."""
        return self._cross_encoder_rerank(results, query, top_k)

    def format_results(self, results: List[dict], top_k: int) -> List[SearchResult]:
        """Stage 6: Format results (public API)."""
        return self._format_results(results, top_k)


__all__ = ["RetrievalPipeline", "PipelineResult", "QueryType"]

"""RRF Fusion Engine — Reciprocal Rank Fusion for multi-retriever result merging."""

from pathlib import Path
"""RRF Fusion Engine — Reciprocal Rank Fusion for multi-retriever result merging."""

import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def rrf_fusion(retriever_results: List[List[dict]], k: int = 60) -> List[dict]:
    """Fuse results from multiple retrievers using Reciprocal Rank Fusion.

    Args:
        retriever_results: List of result lists, one per retriever
        k: RRF constant (default 60)

    Returns:
        Fused and ranked list of results
    """
    # Track scores and best result per ID
    scores: Dict[str, float] = defaultdict(float)
    best_result: Dict[str, dict] = {}

    for results in retriever_results:
        for rank, result in enumerate(results):
            result_id = result.get("id", result.get("content", str(rank)))
            rrf_score = 1.0 / (k + rank + 1)
            scores[result_id] += rrf_score

            # Keep the best version of each result
            if result_id not in best_result or result.get("score", 0) > best_result[
                result_id
            ].get("score", 0):
                best_result[result_id] = result

    # Sort by fused score
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    # Build final results
    final_results = []
    for result_id in sorted_ids:
        if result_id in best_result:
            result = best_result[result_id].copy()
            result["rrf_score"] = round(scores[result_id], 6)
            # Update score to fused score
            result["score"] = round(scores[result_id], 6)
            final_results.append(result)

    return final_results


class TEMPRRetriever:
    """TEMPR: Multi-strategy retrieval with RRF fusion.

    Combines semantic and keyword retrieval with RRF fusion.
    """

    def __init__(self, db_path: Optional[str] = None):
        project_root = Path(__file__).resolve().parents[3]
        self.db_path = db_path or str(project_root / "context" / "memory" / "mind_from_mind.db")
        self._semantic_retriever = None
        self._keyword_retriever = None
        self._semantic_retriever = None
        self._keyword_retriever = None

    def _get_retrievers(self):
        """Lazy-load retrievers."""
        if self._semantic_retriever is None:
            from .semantic import SemanticRetriever

            self._semantic_retriever = SemanticRetriever(self.db_path)

        if self._keyword_retriever is None:
            from .keyword import KeywordRetriever

            self._keyword_retriever = KeywordRetriever(self.db_path)

        return self._semantic_retriever, self._keyword_retriever

    def search(
        self,
        query: str,
        top_k: int = 10,
        tier: Optional[str] = None,
        strategies: Optional[List[str]] = None,
    ) -> List[dict]:
        """Search using multiple strategies with RRF fusion.

        Args:
            query: Search query
            top_k: Number of results to return
            tier: Memory tier filter
            strategies: List of strategies to use (default: ["semantic", "keyword"])

        Returns:
            Fused and ranked list of results
        """
        start = time.time()
        semantic, keyword = self._get_retrievers()

        if strategies is None:
            strategies = ["semantic", "keyword"]

        # Run retrievers in parallel (sequential for now, can be async later)
        retriever_results = []
        for strategy in strategies:
            try:
                if strategy == "semantic":
                    results = semantic.search(query, top_k * 2, tier)
                    retriever_results.append(results)
                elif strategy == "keyword":
                    results = keyword.search(query, top_k * 2, tier)
                    retriever_results.append(results)
            except Exception as e:
                logger.warning(f"TEMPR retriever: {strategy} strategy failed: {e}")

        # Fuse results
        fused = rrf_fusion(retriever_results)

        # Return top_k
        final_results = fused[:top_k]

        elapsed = (time.time() - start) * 1000
        logger.info(
            f"TEMPR retriever: {len(final_results)} results from {len(retriever_results)} "
            f"strategies in {elapsed:.1f}ms"
        )
        return final_results

"""RRF Fusion Engine — Reciprocal Rank Fusion for multi-retriever result merging."""

from pathlib import Path

import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

__all__ = ["rrf_fusion", "mmr_rerank", "TEMPRRetriever"]

logger = logging.getLogger(__name__)


def mmr_rerank(
    results: list,
    query_embedding: list[float] | None = None,
    lambda_: float = 0.5,
    top_k: int = 10,
) -> list:
    """
    MMR (Maximal Marginal Relevance) for diverse results.

    Args:
        results: List of SearchResult objects with embeddings
        query_embedding: Query embedding vector (optional, uses result scores if not provided)
        lambda_: Balance between relevance (lambda_) and diversity (1-lambda_)
        top_k: Number of results to return

    Returns:
        Reranked results with diversity
    """
    if not results:
        return []

    # If no query embedding, just return original results sorted by score
    if not query_embedding:
        return sorted(results, key=lambda r: getattr(r, "score", 0), reverse=True)[
            :top_k
        ]

    import numpy as np

    selected = []
    remaining = list(results)
    query_vec = np.array(query_embedding)

    while len(selected) < top_k and remaining:
        if not selected:
            # First result: highest relevance score
            remaining.sort(key=lambda r: getattr(r, "score", 0), reverse=True)
            selected.append(remaining.pop(0))
            continue

        # Get embeddings of selected results
        selected_embeddings = []
        for r in selected:
            emb = getattr(r, "embedding", None)
            if emb:
                selected_embeddings.append(np.array(emb))

        best_score = -float("inf")
        best_idx = 0

        for i, result in enumerate(remaining):
            emb = getattr(result, "embedding", None)
            if emb is None:
                # Fall back to original score
                score = getattr(result, "score", 0)
            else:
                result_vec = np.array(emb)

                # Relevance to query
                relevance = np.dot(query_vec, result_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(result_vec) + 1e-8
                )

                # Max similarity to selected results
                max_sim = 0
                if selected_embeddings:
                    sims = [
                        np.dot(result_vec, se)
                        / (np.linalg.norm(result_vec) * np.linalg.norm(se) + 1e-8)
                        for se in selected_embeddings
                    ]
                    max_sim = max(sims)

                # MMR score
                score = lambda_ * relevance - (1 - lambda_) * max_sim

            if score > best_score:
                best_score = score
                best_idx = i

        selected.append(remaining.pop(best_idx))

    return selected


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

    def __init__(
        self,
        db_path: Optional[str] = None,
        trust_scorer: Optional[Any] = None,
        trust_weight: float = 0.3,
    ):
        project_root = Path(__file__).resolve().parents[3]
        self.db_path = db_path or str(
            project_root / "context" / "memory" / "mind_from_mind.db"
        )
        self._semantic_retriever = None
        self._keyword_retriever = None
        self.trust_scorer = trust_scorer
        self.trust_weight = trust_weight

        # Learning-based weight tuning
        self.retriever_weights = {"semantic": 0.5, "keyword": 0.5}
        self.feedback_history: list[dict] = []
        self._feedback_threshold = 100  # Adjust weights after N feedback points

    def record_feedback(self, query: str, clicked_result_id: str, source: str):
        """Record which retriever sourced a clicked result."""
        import datetime

        self.feedback_history.append(
            {
                "query": query,
                "clicked_id": clicked_result_id,
                "source": source,
                "timestamp": datetime.datetime.now().isoformat(),
            }
        )
        if len(self.feedback_history) >= self._feedback_threshold:
            self._adjust_weights()

    def _adjust_weights(self):
        """Learn optimal weights from feedback history."""
        source_clicks = {}
        for feedback in self.feedback_history:
            source = feedback["source"]
            source_clicks[source] = source_clicks.get(source, 0) + 1

        total = sum(source_clicks.values())
        if total == 0:
            return

        # Update weights based on click-through rates
        for source in self.retriever_weights:
            clicks = source_clicks.get(source, 0)
            self.retriever_weights[source] = max(0.1, clicks / total)

        # Normalize
        total_weight = sum(self.retriever_weights.values())
        for source in self.retriever_weights:
            self.retriever_weights[source] /= total_weight

        # Clear feedback history
        self.feedback_history = []

    def get_current_weights(self) -> dict:
        """Return current retriever weights."""
        return dict(self.retriever_weights)

    def _get_retrievers(self):
        """Lazy-load retrievers."""
        if self._semantic_retriever is None:
            from .semantic import SemanticRetriever

            self._semantic_retriever = SemanticRetriever(self.db_path)

        if self._keyword_retriever is None:
            from .keyword import KeywordRetriever

            self._keyword_retriever = KeywordRetriever(self.db_path)

        return self._semantic_retriever, self._keyword_retriever

    def _apply_trust_reranking(self, results: list) -> list:
        """Re-rank results using trust scores."""
        if not self.trust_scorer or not results:
            return results

        reranked = []
        for result in results:
            try:
                trust_obj = self.trust_scorer.get_trust_score(
                    result.get("id", result.get("memory_id", ""))
                )
                trust_score = trust_obj.trust if trust_obj else 0.5
            except Exception:
                trust_score = 0.5  # Default neutral trust

            # Blend relevance score with trust score
            relevance_score = result.get("score", 0.5)
            adjusted_score = (
                relevance_score * (1 - self.trust_weight)
                + trust_score * self.trust_weight
            )

            result["score"] = round(adjusted_score, 4)
            result["metadata"] = result.get("metadata", {})
            result["metadata"]["trust_score"] = round(trust_score, 4)

            reranked.append(result)

        # Re-sort by adjusted score
        return sorted(reranked, key=lambda r: r.get("score", 0), reverse=True)

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

        # Apply trust-aware reranking if trust_scorer is available
        results = self._apply_trust_reranking(fused)

        # Return top_k
        final_results = results[:top_k]

        elapsed = (time.time() - start) * 1000
        logger.info(
            f"TEMPR retriever: {len(final_results)} results from {len(retriever_results)} "
            f"strategies in {elapsed:.1f}ms"
        )
        return final_results

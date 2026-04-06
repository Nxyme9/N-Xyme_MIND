"""Unified Memory Router — Aggregates results from all memory sources."""

import logging
from typing import Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from datetime import datetime

from .connectors import MemoryResult, HealthStatus
from .registry import get_registry, get_enabled_connectors
from .embeddings import get_engine, VectorStore
from .learning_config import get_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Unified Memory Models
# ---------------------------------------------------------------------------

@dataclass
class UnifiedMemoryQuery:
    """Query for unified memory search."""
    query: str
    max_results_per_source: int = 5
    enabled_sources: Optional[List[str]] = None  # None = all enabled
    use_semantic: bool = False  # Use embeddings for semantic search
    timeout_ms: int = 5000


@dataclass
class UnifiedMemoryResult:
    """Aggregated result from unified memory search."""
    results: List[MemoryResult]
    sources_queried: List[str]
    sources_failed: List[str]
    total_results: int
    query_time_ms: float
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Router Implementation
# ---------------------------------------------------------------------------

class MemoryRouter:
    """Router that aggregates memory from multiple sources."""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._semantic_enabled = True
        self._vector_store: Optional[VectorStore] = None
        self._learning_adapter: Optional[Any] = None

    @property
    def learning_adapter(self) -> Optional[Any]:
        """Get the learning adapter for re-ranking."""
        return self._learning_adapter

    def set_learning_adapter(self, adapter: Optional[Any]) -> None:
        """Set the learning adapter for re-ranking."""
        self._learning_adapter = adapter
    
    @property
    def vector_store(self) -> VectorStore:
        """Get or create vector store for semantic search."""
        if self._vector_store is None:
            self._vector_store = VectorStore(get_engine())
        return self._vector_store
    
    def search(self, query: UnifiedMemoryQuery) -> UnifiedMemoryResult:
        """Execute unified memory search across all sources."""
        import time
        start_time = time.time()
        
        # Get enabled connectors
        connectors = get_enabled_connectors()
        if query.enabled_sources:
            from .registry import get_registry
            registry = get_registry()
            connectors = [
                registry.get(name) for name in query.enabled_sources
                if registry.get(name)
            ]
        
        # Filter out None (missing connectors)
        connectors = [c for c in connectors if c]
        
        if not connectors:
            return UnifiedMemoryResult(
                results=[],
                sources_queried=[],
                sources_failed=[],
                total_results=0,
                query_time_ms=0,
                metadata={"error": "No connectors available"},
            )
        
        # Parallel search across all connectors
        all_results: List[MemoryResult] = []
        sources_queried: List[str] = []
        sources_failed: List[str] = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._search_connector,
                    connector,
                    query.query,
                    query.max_results_per_source,
                ): connector.name
                for connector in connectors
            }
            
            per_connector_timeout = max(2.0, query.timeout_ms / 1000 / len(connectors))
            for future in as_completed(futures):
                connector_name = futures[future]
                try:
                    results = future.result(timeout=per_connector_timeout)
                    all_results.extend(results)
                    sources_queried.append(connector_name)
                except FuturesTimeoutError:
                    logger.warning(f"Connector {connector_name} timed out after {per_connector_timeout:.1f}s")
                    sources_failed.append(connector_name)
                except Exception as e:
                    logger.warning(f"Connector {connector_name} failed: {e}")
                    sources_failed.append(connector_name)
        
        # Sort by score (highest first)
        all_results.sort(key=lambda r: r.score, reverse=True)

        # Apply learned re-ranking if enabled
        if self._learning_adapter and get_config('rerank_enabled'):
            # Convert MemoryResult to dict for reranking
            result_dicts = [
                {
                    'type': r.metadata.get('result_type', 'other'),
                    'score': r.score,
                    '_result': r,
                }
                for r in all_results
            ]
            # Re-rank based on preferences
            reranked_dicts = self._learning_adapter.rerank_results(result_dicts)
            # Extract re-ranked MemoryResults
            all_results = [d['_result'] for d in reranked_dicts]

        
        # Deduplicate by content
        seen = set()
        deduped = []
        for r in all_results:
            key = r.content[:100].lower()
            if key not in seen:
                seen.add(key)
                deduped.append(r)
        
        query_time_ms = (time.time() - start_time) * 1000
        
        return UnifiedMemoryResult(
            results=deduped,
            sources_queried=sources_queried,
            sources_failed=sources_failed,
            total_results=len(deduped),
            query_time_ms=query_time_ms,
            metadata={"semantic": query.use_semantic},
        )
    
    def _search_connector(self, connector, query: str, max_results: int) -> List[MemoryResult]:
        """Search a single connector."""
        try:
            return connector.search(query, max_results)
        except Exception as e:
            logger.warning(f"Error searching {connector.name}: {e}")
            return []
    
    def set_semantic_enabled(self, enabled: bool):
        """Enable semantic search via embeddings."""
        self._semantic_enabled = enabled
    
    def semantic_search(self, query: str, top_k: int = 5) -> List[dict]:
        """Semantic search using embeddings."""
        return self.vector_store.search(query, top_k)
    
    def index_results(self, results: List[MemoryResult]):
        """Index memory results in vector store for semantic search."""
        for r in results:
            self.vector_store.add(r.content, {"source": r.source, "id": r.id})

    def tempr_search(
        self,
        query: str,
        top_k: int = 10,
        tier: Optional[str] = None,
        strategies: Optional[List[str]] = None,
    ) -> List[dict]:
        """TEMPR multi-strategy retrieval with RRF fusion.

        Args:
            query: Search query
            top_k: Number of results to return
            tier: Memory tier filter (short_term, long_term, reasoning)
            strategies: List of strategies (default: ["semantic", "keyword"])

        Returns:
            Fused and ranked list of result dicts
        """
        from .retrievers.fusion import TEMPRRetriever
        retriever = TEMPRRetriever()
        return retriever.search(query, top_k, tier, strategies)

# Global router instance
_router: Optional[MemoryRouter] = None


def get_router() -> MemoryRouter:
    """Get the global memory router."""
    global _router
    if _router is None:
        _router = MemoryRouter()
    return _router


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

def get_unified_memory(
    query: str,
    max_results: int = 10,
    enabled_sources: Optional[List[str]] = None,
    timeout_ms: int = 5000,
) -> UnifiedMemoryResult:
    """
    Convenience function to get unified memory results.
    
    Args:
        query: Search query string
        max_results: Maximum results per source
        enabled_sources: List of sources to query (None = all)
        timeout_ms: Timeout in milliseconds
    
    Returns:
        UnifiedMemoryResult with aggregated results
    """
    um_query = UnifiedMemoryQuery(
        query=query,
        max_results_per_source=max_results,
        enabled_sources=enabled_sources,
        timeout_ms=timeout_ms,
    )
    return get_router().search(um_query)


def search_memory(query: str, top_k: int = 5) -> List[MemoryResult]:
    """Simple search interface returning top results."""
    result = get_unified_memory(query, max_results=top_k)
    return result.results
def tempr_search(
    query: str,
    top_k: int = 10,
    tier: Optional[str] = None,
    strategies: Optional[List[str]] = None,
) -> List[dict]:
    """TEMPR multi-strategy retrieval with RRF fusion.

    Args:
        query: Search query
        top_k: Number of results to return
        tier: Memory tier filter
        strategies: List of strategies (default: ["semantic", "keyword"])

    Returns:
        Fused and ranked list of result dicts
    """
    return get_router().tempr_search(query, top_k, tier, strategies)


# ---------------------------------------------------------------------------
# Package Exports
# ---------------------------------------------------------------------------

__all__ = [
    "MemoryRouter",
    "UnifiedMemoryQuery",
    "UnifiedMemoryResult",
    "get_router",
    "get_unified_memory",
    "search_memory",
    "tempr_search",
    "MemoryResult",
    "HealthStatus",
]

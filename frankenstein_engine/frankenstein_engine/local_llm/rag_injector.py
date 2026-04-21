#!/usr/bin/env python3
"""RAG Context Injector — Injects relevant context from memory into LLM prompts.

Flow:
    1. Embed query via direct GGUF (nomic-embed-text)
    2. Retrieve top-K relevant docs from memory
    3. Build context string
    4. Return enhanced prompt

NO OLLAMA - uses direct llama-cpp-python.

Caching:
    - Caches RAG results using query hash as key
    - TTL: 1 hour for general / 24 hours for factual
    - Controlled by enable_rag_cache config option
"""

import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional

from packages.memory_store.router import (
    MemoryRouter,
    UnifiedMemoryQuery,
    SearchResults,
)
from packages.memory_store.stores.vector_store import embed_text

logger = logging.getLogger("local_llm.rag")

# Default cache settings
DEFAULT_CACHE_TTL = 3600  # 1 hour
DEFAULT_CACHE_SIZE = 1000  # Max entries


@dataclass
class RAGCacheEntry:
    """A cached RAG result."""

    query_hash: str
    query: str
    context: str
    timestamp: float = field(default_factory=time.time)
    ttl: int = DEFAULT_CACHE_TTL

    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl


class RAGQueryCache:
    """Simple in-memory cache for RAG query results."""

    def __init__(self, max_size: int = DEFAULT_CACHE_SIZE, ttl: int = DEFAULT_CACHE_TTL):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: dict[str, RAGCacheEntry] = {}
        self._lock = threading.Lock()

    def _hash_query(self, query: str) -> str:
        """Create hash of query."""
        return hashlib.sha256(query.encode()).hexdigest()[:16]

    def get(self, query: str) -> Optional[str]:
        """Get cached context for query."""
        query_hash = self._hash_query(query)
        with self._lock:
            entry = self._cache.get(query_hash)
            if entry and not entry.is_expired():
                logger.debug(f"RAG cache HIT: {query[:50]}...")
                return entry.context
            elif entry:
                logger.debug(f"RAG cache EXPIRED: {query[:50]}...")
                del self._cache[query_hash]
            return None

    def set(self, query: str, context: str, ttl: Optional[int] = None) -> None:
        """Cache context for query."""
        query_hash = self._hash_query(query)
        with self._lock:
            # Simple LRU: remove oldest if at capacity
            if len(self._cache) >= self.max_size:
                oldest = min(self._cache.items(), key=lambda x: x[1].timestamp)
                del self._cache[oldest[0]]
                logger.debug(f"RAG cache EVICT: {oldest[0]}")

            self._cache[query_hash] = RAGCacheEntry(
                query_hash=query_hash, query=query, context=context, ttl=ttl or self.ttl
            )
            logger.debug(f"RAG cache SET: {query_hash}")


class RAGContextInjector:
    """Thread-safe RAG context injection for local LLM queries.

    Supports optional caching of RAG results for repeated queries.
    """

    DEFAULT_TOP_K = 5
    CONTEXT_FORMAT = "Context:\n{context}\n\nUser: {query}"

    def __init__(
        self,
        top_k: int = DEFAULT_TOP_K,
        router: Optional[MemoryRouter] = None,
        enable_cache: bool = True,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        cache_size: int = DEFAULT_CACHE_SIZE,
    ):
        self.top_k = top_k
        self._router = router
        self._lock = threading.RLock()
        self._cache = RAGQueryCache(max_size=cache_size, ttl=cache_ttl) if enable_cache else None

        logger.info(f"RAGContextInjector initialized: top_k={top_k}, cache={enable_cache}")

    @property
    def router(self) -> MemoryRouter:
        """Lazy-load default router."""
        if self._router is None:
            self._router = MemoryRouter()
        return self._router

    def _embed_query(self, query: str) -> List[float]:
        """Embed query using direct GGUF (no Ollama).

        Args:
            query: User query string

        Returns:
            Query embedding vector (list of floats)
        """
        # Use direct GGUF embedding from vector_store module
        embedding = embed_text(query)
        return embedding

    def _retrieve_docs(self, query: str, top_k: int) -> SearchResults:
        """Retrieve top-K relevant documents from memory.

        Args:
            query: User query string
            top_k: Number of documents to retrieve

        Returns:
            SearchResults with retrieved documents
        """
        memory_query = UnifiedMemoryQuery(
            query=query,
            max_results_per_source=top_k,
            use_semantic=True,
        )
        return self.router.search(memory_query)

    def _build_context(self, results: SearchResults) -> str:
        """Build context string from retrieved documents.

        Args:
            results: SearchResults from memory retrieval

        Returns:
            Formatted context string
        """
        if not results.results:
            return ""

        context_parts = []
        for i, result in enumerate(results.results, start=1):
            content = result.content
            if content:
                # Truncate long content
                if len(content) > 2000:
                    content = content[:2000] + "..."
                context_parts.append(f"[{i}] {content}")

        return "\n\n".join(context_parts)

    def inject_context(self, query: str, top_k: Optional[int] = None) -> str:
        """Inject relevant context from memory into query.

        This method is thread-safe and can be called concurrently.
        Uses caching for repeated queries.

        Args:
            query: User query string
            top_k: Override default top-K (optional)

        Returns:
            Enhanced prompt with context: "Context:\n{context}\n\nUser: {query}"
            If no relevant docs found, returns just "User: {query}"
        """
        k = top_k if top_k is not None else self.top_k

        with self._lock:
            try:
                # Step 0: Check cache first
                if self._cache:
                    cached = self._cache.get(query)
                    if cached:
                        logger.info(f"RAG cache HIT for: {query[:50]}...")
                        return self.CONTEXT_FORMAT.format(context=cached, query=query)

                # Step 1: Embed query for semantic search
                self._embed_query(query)

                # Step 2: Retrieve top-K relevant docs from memory
                results = self._retrieve_docs(query, k)
                logger.info(
                    f"RAG retrieved {len(results.results)} docs in {results.query_time_ms:.1f}ms"
                )

                # Step 3: Build context string
                context = self._build_context(results)

                # Step 4: Cache the result if caching enabled
                if self._cache and context:
                    self._cache.set(query, context)

                # Step 5: Return enhanced prompt
                if context:
                    return self.CONTEXT_FORMAT.format(context=context, query=query)
                else:
                    return f"User: {query}"

            except Exception as e:
                logger.warning(f"RAG injection failed: {e}, returning original query")
                return f"User: {query}"


# Module-level convenience function
def create_rag_injector(**kwargs) -> RAGContextInjector:
    """Create a RAGContextInjector instance."""
    return RAGContextInjector(**kwargs)


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)

    injector = RAGContextInjector()

    # Test with sample query
    query = "How do I implement authentication in the local LLM?"
    result = injector.inject_context(query)

    print("=== RAG Context Injection Test ===")
    print(f"Original query: {query}")
    print(f"\nEnhanced prompt:\n{result}")

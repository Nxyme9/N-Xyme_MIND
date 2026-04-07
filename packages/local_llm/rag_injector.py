#!/usr/bin/env python3
"""RAG Context Injector — Injects relevant context from memory into LLM prompts."""

import logging
import threading
from typing import List, Optional

from packages.memory_core.router import (
    MemoryRouter,
    UnifiedMemoryQuery,
    SearchResults,
)

logger = logging.getLogger("local_llm.rag")


class RAGContextInjector:
    """Thread-safe RAG context injection for local LLM queries.

    Flow:
    1. Embed query via Ollama (nomic-embed-text)
    2. Retrieve top-K relevant docs from memory
    3. Build context string
    4. Return enhanced prompt
    """

    DEFAULT_EMBED_MODEL = "nomic-embed-text"
    DEFAULT_TOP_K = 5
    OLLAMA_BASE_URL = "http://localhost:11434"
    CONTEXT_FORMAT = "Context:\n{context}\n\nUser: {query}"

    def __init__(
        self,
        embed_model: str = DEFAULT_EMBED_MODEL,
        top_k: int = DEFAULT_TOP_K,
        base_url: str = OLLAMA_BASE_URL,
        router: Optional[MemoryRouter] = None,
    ):
        self.embed_model = embed_model
        self.top_k = top_k
        self.base_url = base_url.rstrip("/")
        self._router = router
        self._lock = threading.RLock()

        logger.info(
            f"RAGContextInjector initialized: model={embed_model}, "
            f"top_k={top_k}, url={base_url}"
        )

    @property
    def router(self) -> MemoryRouter:
        """Lazy-load default router."""
        if self._router is None:
            self._router = MemoryRouter()
        return self._router

    def _embed_query(self, query: str) -> List[float]:
        """Embed query using Ollama embedding API.

        Args:
            query: User query string

        Returns:
            Query embedding vector (list of floats)
        """
        import requests

        url = f"{self.base_url}/v1/embeddings"
        payload = {"model": self.embed_model, "prompt": query}

        try:
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("embedding", [])
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise

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
                # Step 1: Embed query via Ollama
                self._embed_query(query)
                # Note: We embed to enable semantic search, but the router
                # handles embedding internally via its retrievers

                # Step 2: Retrieve top-K relevant docs from memory
                results = self._retrieve_docs(query, k)
                logger.info(
                    f"RAG retrieved {len(results.results)} docs in {results.query_time_ms:.1f}ms"
                )

                # Step 3: Build context string
                context = self._build_context(results)

                # Step 4: Return enhanced prompt
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

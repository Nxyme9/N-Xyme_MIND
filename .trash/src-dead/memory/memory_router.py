#!/usr/bin/env python3
"""Memory Router - Routes queries to appropriate memory backends."""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class MemoryRouter:
    """Routes memory queries to appropriate backend based on query intent."""
    
    TYPE_KEYWORDS = {
        "episodic": ["what happened", "earlier", "before", "when", "session", "ran", "executed"],
        "semantic": ["who is", "what is", "concept", "definition", "learned", "know", "entity"],
        "session": ["my last", "previous", "earlier in this", "current session"],
    }
    
    def __init__(self):
        self.backends = {}
        self._init_backends()
    
    def _init_backends(self):
        """Initialize available memory backends."""
        # Try to import each backend, skip if unavailable
        try:
            from src.memory.connectors import MemoryMCPConnector
            self.backends["memory_mcp"] = MemoryMCPConnector()
            logger.info("✅ Memory MCP backend initialized")
        except Exception as e:
            logger.warning(f"❌ Memory MCP backend unavailable: {e}")
        
        try:
            from src.memory.connectors import SessionConnector
            self.backends["session"] = SessionConnector()
            logger.info("✅ Session backend initialized")
        except Exception as e:
            logger.warning(f"❌ Session backend unavailable: {e}")
        
        try:
            from src.memory.file_connector import FileConnector
            self.backends["file_embeddings"] = FileConnector()
            logger.info("✅ File embeddings backend initialized")
        except Exception as e:
            logger.warning(f"❌ File embeddings backend unavailable: {e}")
    
    def route(self, query: str) -> List[str]:
        """Return list of backends to query based on query intent."""
        query_lower = query.lower()
        
        # Semantic gets priority (facts over events)
        if any(kw in query_lower for kw in self.TYPE_KEYWORDS["semantic"]):
            return ["memory_mcp"]
        
        # Episodic for event sequences
        if any(kw in query_lower for kw in self.TYPE_KEYWORDS["episodic"]):
            return ["session"]
        
        # Session for recent context
        if any(kw in query_lower for kw in self.TYPE_KEYWORDS["session"]):
            return ["session"]
        
        # Default: query all available backends
        return list(self.backends.keys())
    
    def search(self, query: str, max_results: int = 10) -> List[dict]:
        """Search memory using intelligent routing."""
        backends = self.route(query)
        results = []
        
        for backend_name in backends:
            backend = self.backends.get(backend_name)
            if not backend:
                continue
            
            try:
                backend_results = backend.search(query, max_results=max_results)
                for result in backend_results:
                    results.append({
                        "content": result.content,
                        "source": result.source,
                        "score": result.score,
                        "metadata": result.metadata,
                    })
            except Exception as e:
                logger.warning(f"❌ {backend_name} search failed: {e}")
        
        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:max_results]
    
    def get_status(self) -> dict:
        """Get status of all backends."""
        status = {}
        for name, backend in self.backends.items():
            try:
                health = backend.health_check()
                status[name] = {
                    "healthy": health.healthy,
                    "error": health.error,
                    "latency_ms": health.latency_ms,
                }
            except Exception as e:
                status[name] = {
                    "healthy": False,
                    "message": str(e),
                    "latency_ms": 0,
                }
        return status


# Global router instance
_router = None


def get_router() -> MemoryRouter:
    """Get or create the global memory router."""
    global _router
    if _router is None:
        _router = MemoryRouter()
    return _router


def memory_search_unified(query: str, max_results: int = 10) -> dict:
    """Unified memory search using intelligent routing."""
    router = get_router()
    results = router.search(query, max_results=max_results)
    return {
        "status": "ok",
        "query": query,
        "results": results,
        "total_found": len(results),
        "backends_queried": list(set(r["source"] for r in results)),
    }


def memory_status() -> dict:
    """Get status of all memory backends."""
    router = get_router()
    return {
        "status": "ok",
        "backends": router.get_status(),
    }

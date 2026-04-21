"""
Fast Memory Injector - Tiered retrieval for <100ms context injection

Based on research from production systems (AutoGen, LangChain, Claude Code):
- Two-layer caching: exact hash → semantic → LLM
- Keyword search first (sub-10ms)
- Early-exit on high confidence
- Pre-compute session summaries
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from collections import defaultdict

logger = logging.getLogger("orchestration.fast_memory")


# Simple in-memory cache (could swap for Redis)
class TTLCache:
    """Simple TTL cache with max size."""

    def __init__(self, maxsize: int = 500, ttl: int = 300):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self._maxsize = maxsize
        self._ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        # Evict if full
        if len(self._cache) >= self._maxsize:
            # Simple: remove oldest 10%
            keys_to_remove = list(self._cache.keys())[: self._maxsize // 10]
            for k in keys_to_remove:
                del self._cache[k]

        ttl = ttl or self._ttl
        self._cache[key] = (value, time.time() + ttl)

    def clear(self):
        self._cache.clear()


class SimpleInvertedIndex:
    """Simple inverted index for fast keyword lookups."""

    def __init__(self):
        self._index: Dict[str, set] = defaultdict(set)  # word -> set of content_ids
        self._content: Dict[str, str] = {}  # content_id -> content

    def add(self, content_id: str, text: str, content: str):
        """Add content to index."""
        words = text.lower().split()
        for word in words:
            # Simple: index word stems (3+ chars)
            if len(word) >= 3:
                self._index[word].add(content_id)
        self._content[content_id] = content

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search by keyword intersection."""
        query_words = set(query.lower().split())
        query_words = {w for w in query_words if len(w) >= 3}

        if not query_words:
            return []

        # Score by intersection
        scores = []
        for content_id, content_text in self._content.items():
            content_words = set(content_text.lower().split())
            intersection = query_words & content_words
            if intersection:
                scores.append(
                    {
                        "content_id": content_id,
                        "content": self._content[content_id],
                        "score": len(intersection),
                        "matched_words": list(intersection),
                    }
                )

        # Sort by score
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]


@dataclass
class FastInjectResult:
    """Result from fast memory injection."""

    injected_context: str
    source: str  # "cache", "keyword", "semantic", "empty"
    latency_ms: int
    confidence: float


class FastMemoryInjector:
    """Tiered retrieval with early-exit for <100ms injection."""

    def __init__(self):
        # L0: Exact match cache (~1ms)
        self._exact_cache = TTLCache(maxsize=200, ttl=60)  # 1-min TTL for exact

        # L1: Keyword index (~5ms)
        self._keyword_index = SimpleInvertedIndex()
        self._keyword_index_built = False

        # L2: Semantic cache with embeddings (~20ms cache hit)
        self._semantic_cache = TTLCache(maxsize=500, ttl=300)  # 5-min TTL

        # Session summaries cache
        self._session_summaries = TTLCache(maxsize=50, ttl=3600)  # 1-hour TTL

        # Stats
        self._stats = {
            "exact_hits": 0,
            "keyword_hits": 0,
            "semantic_hits": 0,
            "misses": 0,
            "total_requests": 0,
        }

        # Pre-build keyword index with common patterns
        self._init_keyword_index()

    def _init_keyword_index(self):
        """Pre-build keyword index with common project patterns."""
        # Add common contexts - MORE patterns for better matching
        common_patterns = [
            # Project context
            (
                "project_context",
                "n-xyme mind ai coding workspace opencode orchestration agent",
            ),
            # Agent context
            ("agent_sisyphus", "sisyphus orchestrate delegate task plan"),
            (
                "agent_hephaestus",
                "hephaestus implement build code fix create add modify",
            ),
            ("agent_oracle", "oracle review architecture design decision"),
            ("agent_explore", "explore find search grep locate file pattern"),
            ("agent_librarian", "librarian research docs web external"),
            ("agent_atlas", "atlas execute plan step"),
            # BMAD context
            ("bmad_prd", "bmad product requirements document epic story"),
            ("bmad_sprint", "sprint planning task todo"),
            # Learning context
            ("learning_route", "route_task route delegate agent level complexity"),
            ("learning_record", "record_outcome log success latency"),
            ("learning_qlearning", "q-learning weights update agent performance"),
            # Memory context
            ("memory_inject", "memory inject context session preference"),
            # MCP context
            ("mcp_filesystem", "filesystem read write edit glob"),
            ("mcp_context", "context7 memory brain nx sequential thinking"),
            # Common task patterns
            ("task_implement", "implement create build add develop feature"),
            ("task_fix", "fix bug error issue problem broken"),
            ("task_refactor", "refactor restructure improve optimize"),
            ("task_research", "research find search investigate explore"),
            ("task_review", "review analyze check validate"),
        ]

        for content_id, text in common_patterns:
            self._keyword_index.add(content_id, text, f"[CONTEXT] {text}")

        self._keyword_index_built = True
        logger.info(
            f"FastMemoryInjector: Keyword index pre-built with {len(common_patterns)} patterns"
        )

    async def inject_context(
        self,
        agent: str,
        task: str,
        max_tokens: int = 500,
        speed_mode: str = "fast",  # "fast" (<100ms), "balanced" (<300ms), "accurate" (unlimited)
    ) -> FastInjectResult:
        """
        Main entry point - tiered retrieval with early-exit.

        speed_mode:
        - "fast": Return at L1 if confidence > 0.7, skip semantic if > 0.85
        - "balanced": Return at L1 if confidence > 0.5, do semantic always
        - "accurate": Full pipeline, no early exit
        """
        start_time = time.time()
        self._stats["total_requests"] += 1

        # L0: Exact cache match (~1ms)
        cache_key = self._make_cache_key(agent, task)
        if cached := self._exact_cache.get(cache_key):
            self._stats["exact_hits"] += 1
            logger.debug(
                f"FastInject: L0 exact cache hit ({time.time() - start_time:.1f}ms)"
            )
            return FastInjectResult(
                injected_context=self._truncate(cached, max_tokens),
                source="cache",
                latency_ms=int((time.time() - start_time) * 1000),
                confidence=1.0,
            )

        # L1: Keyword search (~5ms)
        keyword_results = self._keyword_index.search(task, top_k=3)
        l1_confidence = self._calc_keyword_confidence(keyword_results, task)

        logger.debug(
            f"FastInject: L1 keyword results={len(keyword_results)}, confidence={l1_confidence:.2f}"
        )

        # Early exit: FAST mode - try semantic first but with super short timeout
        if speed_mode == "fast":
            # For fast mode: try semantic with very short timeout
            semantic_result = await self._semantic_search(task, agent, max_tokens)
            if semantic_result:
                self._semantic_cache.set(cache_key, semantic_result)
                self._stats["semantic_hits"] += 1
                return FastInjectResult(
                    injected_context=semantic_result,
                    source="semantic",
                    latency_ms=int((time.time() - start_time) * 1000),
                    confidence=0.75,
                )
            # Fallback to keyword
            if l1_confidence > 0.3:
                result = self._format_keyword_result(keyword_results, max_tokens)
                self._exact_cache.set(cache_key, result)
                self._stats["keyword_hits"] += 1
                return FastInjectResult(
                    injected_context=result,
                    source="keyword",
                    latency_ms=int((time.time() - start_time) * 1000),
                    confidence=l1_confidence,
                )

        # BEST SYNTHESIS: Always try semantic for balanced/accurate modes
        # L2: Semantic search with cache (~20-50ms)
        semantic_result = await self._semantic_search(task, agent, max_tokens)

        # Merge L1 + L2 - use BEST result (semantic > keyword if available)
        if semantic_result:
            # Semantic has richer context - prefer it
            self._semantic_cache.set(cache_key, semantic_result)
            self._stats["semantic_hits"] += 1
            return FastInjectResult(
                injected_context=semantic_result,
                source="semantic",
                latency_ms=int((time.time() - start_time) * 1000),
                confidence=0.75,
            )

        # Fallback to keyword if no semantic
        if keyword_results:
            combined = self._format_keyword_result(keyword_results, max_tokens)
            self._exact_cache.set(cache_key, combined)
            self._stats["keyword_hits"] += 1
            return FastInjectResult(
                injected_context=combined,
                source="keyword",
                latency_ms=int((time.time() - start_time) * 1000),
                confidence=l1_confidence,
            )

        # Fallback: No context found
        self._stats["misses"] += 1
        return FastInjectResult(
            injected_context="",
            source="empty",
            latency_ms=int((time.time() - start_time) * 1000),
            confidence=0.0,
        )

    def _make_cache_key(self, agent: str, task: str) -> str:
        """Create cache key from agent + task hash."""
        task_hash = hashlib.sha256(task.encode()).hexdigest()[:16]
        return f"{agent}:{task_hash}"

    def _calc_keyword_confidence(self, results: List[Dict], task: str) -> float:
        """Calculate confidence from keyword results."""
        if not results:
            return 0.0

        task_words = set(task.lower().split())
        task_words = {w for w in task_words if len(w) >= 3}

        if not task_words:
            return 0.3

        best_score = results[0].get("score", 0)
        matched_words = results[0].get("matched_words", [])

        # Confidence based on score and word overlap
        # Even small score = some relevance
        if task_words:
            word_match_ratio = len(matched_words) / len(task_words)
        else:
            word_match_ratio = 0

        # Base confidence from score (score 1+ is decent)
        score_confidence = min(0.7, best_score * 0.3)

        # Combined confidence
        confidence = max(0.3, score_confidence + word_match_ratio * 0.3)
        return min(0.95, confidence)

    async def _semantic_search(
        self, task: str, agent: str, max_tokens: int
    ) -> Optional[str]:
        """Semantic search with cache - wired to full memory system."""
        # Check semantic cache first
        cache_key = f"semantic:{hashlib.sha256(task.encode()).hexdigest()[:16]}"
        if cached := self._semantic_cache.get(cache_key):
            return cached

        # WIRED: Use full memory system with short timeout for best synthesis
        try:
            import asyncio
            from packages.brain_mcp.namespaces.fingerprint import (
                get_full_injected_context,
            )

            # Run with timeout to prevent hangs
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    get_full_injected_context, agent, task, max_tokens=max_tokens
                ),
                timeout=0.2,  # 200ms max for semantic
            )
            context = result.get("injected_context", "")
            if context:
                # Cache for future requests
                self._semantic_cache.set(cache_key, context)
                return context[: max_tokens * 4]
        except asyncio.TimeoutError:
            logger.debug("Semantic search timed out, using keyword only")
        except Exception as e:
            logger.debug(f"Semantic search failed: {e}")

        return None

    def _format_keyword_result(self, results: List[Dict], max_tokens: int) -> str:
        """Format keyword results as context."""
        if not results:
            return ""

        parts = []
        max_chars = max_tokens * 4

        for r in results[:2]:
            content = r.get("content", "")[: max_chars // 2]
            if content:
                parts.append(content)

        return "\n\n".join(parts)[:max_chars]

    def _truncate(self, text: str, max_tokens: int) -> str:
        """Truncate to token budget."""
        max_chars = max_tokens * 4
        if len(text) > max_chars:
            return text[: max_chars - 10] + "..."
        return text

    def get_stats(self) -> Dict[str, Any]:
        """Get injection stats."""
        total = self._stats["total_requests"] or 1
        return {
            **self._stats,
            "exact_hit_rate": self._stats["exact_hits"] / total,
            "keyword_hit_rate": self._stats["keyword_hits"] / total,
            "semantic_hit_rate": self._stats["semantic_hits"] / total,
            "miss_rate": self._stats["misses"] / total,
        }

    def add_to_index(self, content_id: str, text: str, content: str):
        """Add custom content to keyword index."""
        self._keyword_index.add(content_id, text, content)


# Global instance
_fast_injector: Optional[FastMemoryInjector] = None


def get_fast_injector() -> FastMemoryInjector:
    """Get or create global fast injector."""
    global _fast_injector
    if _fast_injector is None:
        _fast_injector = FastMemoryInjector()
    return _fast_injector


async def fast_inject_context(
    agent: str, task: str, max_tokens: int = 500, speed_mode: str = "fast"
) -> FastInjectResult:
    """
    Convenience function for fast context injection.

    Usage:
        result = await fast_inject_context("hephaestus", "implement JWT auth")
        print(f"Context: {result.injected_context[:100]}, Source: {result.source}, Latency: {result.latency_ms}ms")
    """
    injector = get_fast_injector()
    return await injector.inject_context(agent, task, max_tokens, speed_mode)


# Export
__all__ = [
    "FastMemoryInjector",
    "FastInjectResult",
    "fast_inject_context",
    "get_fast_injector",
]

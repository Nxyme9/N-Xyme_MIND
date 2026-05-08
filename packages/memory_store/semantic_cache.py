#!/usr/bin/env python3
"""Semantic caching layer for reducing LLM costs."""

from __future__ import annotations
import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached response with metadata."""

    request_hash: str
    response: Any
    created_at: float
    last_accessed: float
    access_count: int = 1
    ttl: float = 3600  # 1 hour default


class SemanticCache:
    """Semantic caching layer - detects similar queries and returns cached responses.

    Unlike exact-match caching, semantic caching uses embeddings to find
    queries that are semantically equivalent despite surface differences.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.95,
        max_size: int = 1000,
        ttl: float = 3600,
    ):
        """Initialize semantic cache.

        Args:
            similarity_threshold: Minimum similarity to consider a match (0-1)
            max_size: Maximum number of entries to cache
            ttl: Default time-to-live in seconds
        """
        self.similarity_threshold = similarity_threshold
        self.max_size = max_size
        self.ttl = ttl
        self._cache: dict[str, CacheEntry] = {}
        self._request_history: list[tuple[str, str]] = []  # (hash, embedding_approx)

    def _get_request_hash(self, request: str) -> str:
        """Get hash of request for exact matching."""
        return hashlib.sha256(request.encode()).hexdigest()[:32]

    def _get_embedding_approx(self, text: str) -> tuple[str, int]:
        """Get approximate embedding for similarity matching.

        Simple hash-based approximation for now.
        In production, use actual embeddings.
        """
        # Normalize text
        normalized = " ".join(text.lower().split())

        # Simple hash approximation
        h = hashlib.md5(normalized.encode()).hexdigest()[:8]

        # Word count as additional feature
        word_count = len(normalized.split())

        return (h, word_count)

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts."""
        # Simple word overlap similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    def get(self, request: str) -> Optional[Any]:
        """Get cached response if exists.

        Args:
            request: The request string

        Returns:
            Cached response or None if not found
        """
        # Exact hash match first
        request_hash = self._get_request_hash(request)
        entry = self._cache.get(request_hash)

        if entry and self._is_valid(entry):
            entry.last_accessed = time.time()
            entry.access_count += 1
            logger.debug(f"Cache hit (exact): {request_hash[:8]}")
            return entry.response

        # Semantic similarity search
        best_match = None
        best_similarity = 0.0

        current_embedding = self._get_embedding_approx(request)

        for hash_key, cached_entry in self._cache.items():
            if not self._is_valid(cached_entry):
                continue

            # Quick filter by embedding approximation
            cached_embedding = self._get_embedding_approx(
                cached_entry.response.get("request", "")
                if isinstance(cached_entry.response, dict)
                else ""
            )

            if current_embedding[1] != cached_embedding[1]:
                continue  # Different word count - unlikely similar

            # Calculate full similarity
            sim = self._calculate_similarity(
                request,
                cached_entry.response.get("request", "")
                if isinstance(cached_entry.response, dict)
                else "",
            )

            if sim > best_similarity and sim >= self.similarity_threshold:
                best_similarity = sim
                best_match = cached_entry

        if best_match:
            best_match.last_accessed = time.time()
            best_match.access_count += 1
            logger.info(f"Cache hit (semantic): similarity={best_similarity:.2f}")
            return best_match.response

        return None

    def put(self, request: str, response: Any, ttl: Optional[float] = None) -> None:
        """Store response in cache.

        Args:
            request: The request string
            response: The response to cache
            ttl: Optional custom TTL in seconds
        """
        # Evict if at capacity
        if len(self._cache) >= self.max_size:
            self._evict_lru()

        request_hash = self._get_request_hash(request)

        entry = CacheEntry(
            request_hash=request_hash,
            response=response,
            created_at=time.time(),
            last_accessed=time.time(),
            ttl=ttl or self.ttl,
        )

        self._cache[request_hash] = entry
        logger.debug(f"Cached: {request_hash[:8]}, size={len(self._cache)}")

    def _is_valid(self, entry: CacheEntry) -> bool:
        """Check if cache entry is still valid."""
        return (time.time() - entry.created_at) < entry.ttl

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)
        del self._cache[lru_key]
        logger.debug(f"Evicted LRU: {lru_key[:8]}")

    def invalidate(self, request: str = None) -> int:
        """Invalidate cache entries.

        Args:
            request: If provided, invalidate specific entry. Otherwise clear all.

        Returns:
            Number of entries invalidated
        """
        if request is None:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared all {count} cache entries")
            return count

        request_hash = self._get_request_hash(request)
        if request_hash in self._cache:
            del self._cache[request_hash]
            logger.info(f"Invalidated: {request_hash[:8]}")
            return 1

        return 0

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_accesses = sum(e.access_count for e in self._cache.values())

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "total_accesses": total_accesses,
            "avg_accesses": total_accesses / len(self._cache) if self._cache else 0,
            "ttl": self.ttl,
            "similarity_threshold": self.similarity_threshold,
        }

    def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed
        """
        expired = [
            key for key, entry in self._cache.items() if not self._is_valid(entry)
        ]

        for key in expired:
            del self._cache[key]

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired entries")

        return len(expired)


# Global cache instance
_semantic_cache = SemanticCache()


def get_semantic_cache() -> SemanticCache:
    """Get global semantic cache instance."""
    return _semantic_cache

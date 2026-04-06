"""
Multi-tier semantic cache for LLM requests.

Provides exact-match caching with TTL expiration and semantic similarity
caching using n-gram overlap (no external dependencies).

Usage:
    from src.model_router.semantic_cache import SemanticCache

    cache = SemanticCache(exact_ttl=60, semantic_ttl=3600, similarity_threshold=0.85)
    cache.put("hello world", "gpt-4", "Hi there!")
    result = cache.get("hello world", "gpt-4")  # exact match
    result = cache.get("hello there world", "gpt-4")  # semantic match if similarity >= threshold
"""

from __future__ import annotations

import math
import threading
import time
from collections import defaultdict
from typing import Any, Dict, Optional


class _ExactEntry:
    """Single entry in the exact-match cache with TTL."""

    __slots__ = ("response", "model", "expires_at")

    def __init__(self, response: str, model: str, ttl: float) -> None:
        self.response = response
        self.model = model
        self.expires_at = time.time() + ttl

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class _SemanticEntry:
    """Single entry in the semantic cache with TTL."""

    __slots__ = ("query", "model", "response", "ngrams", "expires_at")

    def __init__(self, query: str, model: str, response: str, ttl: float) -> None:
        self.query = query
        self.model = model
        self.response = response
        self.ngrams = _ngrams(query)
        self.expires_at = time.time() + ttl

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


def _ngrams(text: str, n: int = 3) -> set[str]:
    """Generate character-level n-grams from text."""
    text = text.lower().strip()
    if len(text) < n:
        return {text}
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union > 0 else 0.0


class SemanticCache:
    """Multi-tier cache: exact-match (fast) + semantic similarity (flexible).

    Thread-safe via threading.Lock. All public methods are safe to call
    from concurrent threads.

    Args:
        exact_ttl: Seconds before exact-match entries expire (default 60).
        semantic_ttl: Seconds before semantic entries expire (default 3600).
        similarity_threshold: Minimum Jaccard similarity for semantic hit (default 0.85).
    """

    def __init__(
        self,
        exact_ttl: float = 60,
        semantic_ttl: float = 3600,
        similarity_threshold: float = 0.85,
        max_size: int = 10000,
        max_exact_size: int = 5000,
    ) -> None:
        self._exact_ttl = exact_ttl
        self._semantic_ttl = semantic_ttl
        self._similarity_threshold = similarity_threshold
        self._max_size = max_size
        self._max_exact_size = max_exact_size

        self._exact: Dict[str, _ExactEntry] = {}
        self._semantic: list[_SemanticEntry] = []
        self._lock = threading.Lock()

        self._stats: Dict[str, int] = defaultdict(int)
        self._stats: Dict[str, int] = defaultdict(int)

    def get(self, query: str, model: str) -> Optional[str]:
        """Look up a cached response.

        Checks exact-match first (O(1)), then falls back to semantic
        similarity search (O(n) over semantic cache entries).

        Args:
            query: The LLM request query string.
            model: The target model name.

        Returns:
            Cached response string if found, None otherwise.
        """
        with self._lock:
            exact_key = self._exact_key(query, model)
            entry = self._exact.get(exact_key)
            if entry and not entry.is_expired:
                self._stats["exact_hits"] += 1
                return entry.response
            if entry:
                del self._exact[exact_key]

            query_ngrams = _ngrams(query)
            best_score = 0.0
            best_response: Optional[str] = None

            valid_entries: list[_SemanticEntry] = []
            for entry in self._semantic:
                if entry.is_expired or entry.model != model:
                    continue
                valid_entries.append(entry)
                score = _jaccard_similarity(query_ngrams, entry.ngrams)
                if score > best_score:
                    best_score = score
                    best_response = entry.response

            self._semantic = valid_entries

            if best_score >= self._similarity_threshold:
                self._stats["semantic_hits"] += 1
                return best_response

            self._stats["misses"] += 1
            return None

    def put(self, query: str, model: str, response: str) -> None:
        """Store a response in both exact and semantic caches.

        Args:
            query: The LLM request query string.
            model: The target model name.
            response: The LLM response to cache.
        """
        with self._lock:
            exact_key = self._exact_key(query, model)
            self._exact[exact_key] = _ExactEntry(response, model, self._exact_ttl)

            self._semantic.append(
                _SemanticEntry(query, model, response, self._semantic_ttl)
            )

            # Enforce max_size on semantic cache
            if len(self._semantic) > self._max_size:
                self._semantic = self._semantic[-self._max_size:]

            # Enforce max_exact_size on exact cache
            if len(self._exact) > self._max_exact_size:
                keys_to_remove = list(self._exact.keys())[:len(self._exact) - self._max_exact_size]
                for key in keys_to_remove:
                    del self._exact[key]

    def clear(self) -> None:
        """Remove all cached entries and reset statistics."""
        with self._lock:
            self._exact.clear()
            self._semantic.clear()
            self._stats.clear()

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics.

        Returns:
            Dict with hit/miss counts and current cache sizes.
        """
        with self._lock:
            now = time.time()
            valid_exact = sum(1 for e in self._exact.values() if e.expires_at > now)
            valid_semantic = sum(1 for e in self._semantic if e.expires_at > now)
            total = (
                self._stats["exact_hits"]
                + self._stats["semantic_hits"]
                + self._stats["misses"]
            )
            hit_rate = (
                (self._stats["exact_hits"] + self._stats["semantic_hits"]) / total
                if total > 0
                else 0.0
            )
            return {
                "exact_hits": self._stats["exact_hits"],
                "semantic_hits": self._stats["semantic_hits"],
                "misses": self._stats["misses"],
                "hit_rate": round(hit_rate, 4),
                "exact_size": valid_exact,
                "semantic_size": valid_semantic,
                "similarity_threshold": self._similarity_threshold,
            }

    @staticmethod
    def _exact_key(query: str, model: str) -> str:
        return f"{model}::{query}"

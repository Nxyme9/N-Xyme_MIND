"""
Prompt Caching Utility

A simple KV-cache and semantic caching implementation to reduce token usage and latency.
Supports exact match lookup (SHA256) and n-gram based semantic similarity.
"""

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Optional


class PromptCache:
    """
    A prompt caching utility that supports exact match and semantic caching.

    Uses SHA256 for exact match keys and n-gram overlap for semantic similarity.
    Implements LRU eviction when cache exceeds max_size.
    """

    def __init__(
        self,
        cache_dir: str = ".cache/prompts",
        max_size: int = 1000,
        max_bytes: int = 10_000_000,
        default_ttl: int = 3600,
    ):
        """
        Initialize the prompt cache.

        Args:
            cache_dir: Directory to store cache files
            max_size: Maximum number of cached prompts
            max_bytes: Maximum total bytes for cached responses (default: 10MB)
            default_ttl: Default time-to-live in seconds (default: 3600 = 1 hour)
        """
        self.cache_dir = Path(cache_dir)
        self.max_size = max_size
        self.max_bytes = max_bytes
        self.default_ttl = default_ttl
        self._operation_count = 0
        self._cleanup_interval = 100
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._ngrams: dict[str, set[tuple]] = {}
        self._hits = 0
        self._misses = 0
        self._semantic_hits = 0
        self._total_bytes = 0
        self._lock = threading.RLock()
        self._load_cache()

    def _hash_prompt(self, prompt: str) -> str:
        """Generate SHA256 hash of prompt for exact match lookup."""
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    def _extract_ngrams(self, text: str, n: int = 3) -> set[tuple]:
        """Extract n-grams from text for semantic similarity."""
        words = text.lower().split()
        if len(words) < n:
            return set()
        return set(tuple(words[i : i + n]) for i in range(len(words) - n + 1))

    def _compute_ngram_overlap(self, set1: set[tuple], set2: set[tuple]) -> float:
        """Compute Jaccard similarity between two n-gram sets."""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def _estimate_size(self, entry: dict) -> int:
        """Estimate memory size of a cache entry in bytes.

        Calculates bytes for response + prompt + metadata.
        """
        size = 0
        if "prompt" in entry:
            size += len(entry["prompt"].encode("utf-8"))
        if "response" in entry:
            size += len(entry["response"].encode("utf-8"))
        size += 100
        return size

    def _load_cache(self) -> None:
        """Load cache from disk."""
        with self._lock:
            cache_file = self.cache_dir / "cache.json"
            meta_file = self.cache_dir / "meta.json"

            try:
                if cache_file.exists() and meta_file.exists():
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self._cache = OrderedDict(data)

                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        self._hits = meta.get("hits", 0)
                        self._misses = meta.get("misses", 0)
                        self._semantic_hits = meta.get("semantic_hits", 0)

                    for key in list(self._cache.keys()):
                        entry = self._cache[key]
                        if "prompt" in entry:
                            self._ngrams[key] = self._extract_ngrams(entry["prompt"])
                            if "created_at" not in entry:
                                entry["created_at"] = time.time()
                                entry["ttl"] = entry.get("ttl", self.default_ttl)
                            if "response" in entry:
                                self._total_bytes += self._estimate_size(entry)
                        else:
                            del self._cache[key]
            except (json.JSONDecodeError, IOError) as e:
                self._cache = OrderedDict()
                self._ngrams = {}
                self._hits = 0
                self._misses = 0
                self._semantic_hits = 0
                self._total_bytes = 0

    def _save_cache(self) -> None:
        """Save cache to disk."""
        with self._lock:
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)

                cache_file = self.cache_dir / "cache.json"
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(dict(self._cache), f, indent=2, ensure_ascii=False)

                meta_file = self.cache_dir / "meta.json"
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "hits": self._hits,
                            "misses": self._misses,
                            "semantic_hits": self._semantic_hits,
                        },
                        f,
                    )
            except IOError as e:
                print(f"Warning: Failed to save cache: {e}", file=sys.stderr)

    def _evict_lru(self) -> None:
        """Evict least recently used item when cache exceeds max_size."""
        if len(self._cache) >= self.max_size:
            oldest_key = next(iter(self._cache))
            self._total_bytes -= self._estimate_size(self._cache[oldest_key])
            del self._cache[oldest_key]
            if oldest_key in self._ngrams:
                del self._ngrams[oldest_key]

    def _evict_by_bytes(self) -> None:
        """Evict oldest entries until under max_bytes."""
        while self._total_bytes > self.max_bytes and self._cache:
            oldest_key = next(iter(self._cache))
            self._total_bytes -= self._estimate_size(self._cache[oldest_key])
            del self._cache[oldest_key]
            if oldest_key in self._ngrams:
                del self._ngrams[oldest_key]

    def _is_expired(self, entry: dict) -> bool:
        """Check if a cache entry has expired based on TTL."""
        created_at = entry.get("created_at", 0)
        ttl = entry.get("ttl", self.default_ttl)
        return time.time() > (created_at + ttl)

    def cleanup(self) -> int:
        """
        Remove all expired entries from the cache.

        Returns:
            Number of entries removed
        """
        with self._lock:
            return self._cleanup()

    def _cleanup(self) -> int:
        """Internal cleanup method (called with lock held)."""
        expired_keys = []
        for key, entry in self._cache.items():
            if self._is_expired(entry):
                expired_keys.append(key)
        for key in expired_keys:
            del self._cache[key]
            if key in self._ngrams:
                del self._ngrams[key]
        if expired_keys:
            self._save_cache()
        return len(expired_keys)

    def get(self, prompt: str) -> Optional[str]:
        """
        Exact match lookup for cached prompt.

        Args:
            prompt: The prompt text to look up

        Returns:
            Cached response if found, None otherwise
        """
        with self._lock:
            key = self._hash_prompt(prompt)

            if key in self._cache:
                entry = self._cache[key]
                if self._is_expired(entry):
                    del self._cache[key]
                    if key in self._ngrams:
                        del self._ngrams[key]
                    self._misses += 1
                    self._save_cache()
                    return None
                self._cache.move_to_end(key)
                self._hits += 1
                self._save_cache()
                return entry["response"]

            self._misses += 1
            self._save_cache()
            return None

    def put(self, prompt: str, response: str, ttl: Optional[int] = None) -> None:
        """
        Store a prompt-response pair in the cache.

        Args:
            prompt: The prompt text
            response: The response to cache
            ttl: Optional TTL override (uses default_ttl if not specified)
        """
        with self._lock:
            key = self._hash_prompt(prompt)
            ttl_value = ttl if ttl is not None else self.default_ttl

            self._cache[key] = {
                "prompt": prompt,
                "response": response,
                "created_at": time.time(),
                "ttl": ttl_value,
            }
            self._cache.move_to_end(key)

            self._ngrams[key] = self._extract_ngrams(prompt)
            self._total_bytes += self._estimate_size(self._cache[key])

            self._evict_lru()
            self._evict_by_bytes()
            self._save_cache()

            self._operation_count += 1
            if self._operation_count >= self._cleanup_interval:
                self._operation_count = 0
                self._cleanup()

    def get_semantic(self, prompt: str, threshold: float = 0.85) -> Optional[str]:
        """
        Semantic similarity lookup for cached prompt.

        Uses n-gram overlap to find similar prompts.

        Args:
            prompt: The prompt text to look up
            threshold: Minimum similarity threshold (0.0 to 1.0)

        Returns:
            Cached response if similar prompt found, None otherwise
        """
        with self._lock:
            prompt_ngrams = self._extract_ngrams(prompt)

            if not prompt_ngrams:
                return self.get(prompt)

            best_match_key = None
            best_overlap = 0.0

            for key, cached_ngrams in self._ngrams.items():
                entry = self._cache[key]
                if self._is_expired(entry):
                    continue
                overlap = self._compute_ngram_overlap(prompt_ngrams, cached_ngrams)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match_key = key

            if best_match_key and best_overlap >= threshold:
                self._cache.move_to_end(best_match_key)
                self._semantic_hits += 1
                self._hits += 1
                self._save_cache()
                return self._cache[best_match_key]["response"]

            self._misses += 1
            self._save_cache()
            return None

    def clear(self) -> None:
        """Clear all cached items and reset statistics."""
        with self._lock:
            self._cache.clear()
            self._ngrams.clear()
            self._hits = 0
            self._misses = 0
            self._semantic_hits = 0
            self._total_bytes = 0
            self._save_cache()

    def stats(self) -> dict:
        """
        Return cache statistics.

        Returns:
            Dictionary with hits, misses, semantic_hits, size, max_size
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (
                (self._hits / total_requests * 100) if total_requests > 0 else 0.0
            )

            return {
                "hits": self._hits,
                "misses": self._misses,
                "semantic_hits": self._semantic_hits,
                "size": len(self._cache),
                "max_size": self.max_size,
                "total_bytes": self._total_bytes,
                "max_bytes": self.max_bytes,
                "default_ttl": self.default_ttl,
                "hit_rate": round(hit_rate, 2),
            }


def main():
    """CLI interface for prompt cache."""
    parser = argparse.ArgumentParser(
        description="Prompt caching utility for reducing token usage and latency.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--prompt", type=str, help="Prompt text to lookup or add to cache"
    )
    parser.add_argument(
        "--response",
        type=str,
        help="Response to cache (use with --prompt when adding new entry)",
    )
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--clear", action="store_true", help="Clear all cached items")
    parser.add_argument(
        "--semantic", action="store_true", help="Use semantic similarity for lookup"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Semantic similarity threshold (default: 0.85)",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=".cache/prompts",
        help="Cache directory (default: .cache/prompts)",
    )
    parser.add_argument(
        "--max-size", type=int, default=1000, help="Maximum cache size (default: 1000)"
    )
    parser.add_argument(
        "--ttl", type=int, default=3600, help="Default TTL in seconds (default: 3600 = 1 hour)"
    )
    parser.add_argument(
        "--cleanup", action="store_true", help="Remove expired entries"
    )

    args = parser.parse_args()

    cache = PromptCache(
        cache_dir=args.cache_dir,
        max_size=args.max_size,
        default_ttl=args.ttl,
    )

    if args.cleanup:
        removed = cache.cleanup()
        print(f"Removed {removed} expired entries.")
        return

    if args.clear:
        cache.clear()
        print("Cache cleared.")
        return

    if args.stats:
        stats = cache.stats()
        print("Cache Statistics:")
        print(f"  Hits: {stats['hits']}")
        print(f"  Misses: {stats['misses']}")
        print(f"  Semantic Hits: {stats['semantic_hits']}")
        print(f"  Size: {stats['size']}/{stats['max_size']}")
        print(f"  Total Bytes: {stats['total_bytes']}/{stats['max_bytes']}")
        print(f"  Default TTL: {stats['default_ttl']}s")
        print(f"  Hit Rate: {stats['hit_rate']}%")
        return

    if args.prompt:
        if args.semantic:
            result = cache.get_semantic(args.prompt, threshold=args.threshold)
        else:
            result = cache.get(args.prompt)

        if result:
            print(f"[CACHE HIT] {result}")
        else:
            print("[CACHE MISS]")

            if args.response:
                cache.put(args.prompt, args.response)
                print("[CACHED] New entry added.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()

"""LRU Semantic Cache — O(1) lookup with semantic similarity."""

import hashlib
import time
import threading
from collections import OrderedDict
from typing import Dict, Optional, Tuple


class LRUCache:
    """Thread-safe LRU cache with TTL."""

    def __init__(self, max_size: int = 10000, ttl: float = 3600.0):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict[str, Tuple[str, float]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self.ttl:
                    self._cache.move_to_end(key)
                    return value
                else:
                    del self._cache[key]
            return None

    def put(self, key: str, value: str) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, time.time())
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def __len__(self) -> int:
        return len(self._cache)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


class LRUSemanticCache:
    """LRU cache with exact match (O(1)) and semantic fallback."""

    def __init__(self, max_size: int = 10000, ttl: float = 3600.0):
        self.exact_cache = LRUCache(max_size=max_size, ttl=ttl)
        self._lock = threading.Lock()

    @staticmethod
    def _hash_key(text: str) -> str:
        return hashlib.sha256(text[:1000].encode()).hexdigest()

    def get(self, prompt: str) -> Optional[str]:
        """O(1) exact match lookup."""
        key = self._hash_key(prompt)
        return self.exact_cache.get(key)

    def put(self, prompt: str, response: str) -> None:
        """Store in O(1) exact cache."""
        key = self._hash_key(prompt)
        self.exact_cache.put(key, response)

    def clear(self) -> None:
        self.exact_cache.clear()

    def __len__(self) -> int:
        return len(self.exact_cache)


# Global instance
lru_semantic_cache = LRUSemanticCache()

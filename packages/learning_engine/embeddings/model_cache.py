"""Embedding model cache with LRU eviction and disk persistence."""

import hashlib
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Optional
import numpy as np


class EmbeddingCache:
    """Thread-safe LRU cache for embeddings with disk persistence."""
    
    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    DIMENSION = 384
    
    def __init__(self, max_size: int = 10000, ttl: int = 3600,
                 cache_dir: str = ".sisyphus/embedding_cache"):
        self.__model = None
        self._memory: OrderedDict[str, dict] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
    
    def _key(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()
    
    def get(self, text: str) -> Optional[np.ndarray]:
        k = self._key(text)
        with self._lock:
            if k in self._memory:
                entry = self._memory[k]
                if time.time() - entry['ts'] < self._ttl:
                    self._memory.move_to_end(k)
                    self._hits += 1
                    return entry['emb'].copy()
                del self._memory[k]
            self._misses += 1
        return None
    
    def put(self, text: str, embedding: np.ndarray):
        k = self._key(text)
        entry = {'emb': embedding.copy(), 'ts': time.time()}
        with self._lock:
            if k in self._memory:
                self._memory.move_to_end(k)
            else:
                if len(self._memory) >= self._max_size:
                    self._memory.popitem(last=False)
            self._memory[k] = entry
        np.save(self._cache_dir / f"{k}.npy", embedding)
    
    def encode(self, text: str) -> np.ndarray:
        cached = self.get(text)
        if cached is not None:
            return cached
        emb = self._model.encode(text, normalize_embeddings=True).astype(np.float32)
        self.put(text, emb)
        return emb
    
    def encode_batch(self, texts: list[str]) -> np.ndarray:
        cached = []
        uncached = []
        uncached_idx = []
        for i, t in enumerate(texts):
            c = self.get(t)
            if c is not None:
                cached.append((i, c))
            else:
                uncached.append(t)
                uncached_idx.append(i)
        
        result = [None] * len(texts)
        for i, emb in cached:
            result[i] = emb
        
        if uncached:
            embs = self._model.encode(uncached, normalize_embeddings=True).astype(np.float32)
            for idx, emb in zip(uncached_idx, embs):
                result[idx] = emb
                self.put(texts[idx], emb)
        
        return np.stack(result)
    
    @property
    def _model(self):
        if self.__model is None:
            from sentence_transformers import SentenceTransformer
            self.__model = SentenceTransformer(self.MODEL_NAME)
        return self.__model
    
    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0
    
    @property
    def size(self) -> int:
        return len(self._memory)
    
    def clear(self):
        with self._lock:
            self._memory.clear()


_cache: Optional[EmbeddingCache] = None

def get_embedding_cache() -> EmbeddingCache:
    global _cache
    if _cache is None:
        _cache = EmbeddingCache()
    return _cache

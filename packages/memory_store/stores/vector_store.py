#!/usr/bin/env python3
"""
Vector Store — Unified vector storage for memory system.

Combines:
- vector_index.py: Core vector index with similarity search
- embeddings.py: Embedding engine with Ollama/Sentence-Transformers
- embedding_service.py: Async embedding service
- embedding_pipeline.py: Auto-embed pipeline for memory system
- embedding_store.py: Vector storage interface
- drive_embedder.py: Drive-specific embedding

Provides:
- VectorIndex: Core vector storage with add/search/delete (implements VectorStore ABC)
- EmbeddingEngine: Generate embeddings via Ollama/ST/hash
- SimilaritySearch: Cosine/L2/dot product similarity
- auto_embed_on_save: Auto-embed memories
- backfill_missing_embeddings: Scan and embed stale memories
"""

from collections import OrderedDict
import hashlib
import json
import logging
import math
import queue
import sqlite3
import struct
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from packages.memory_store.stores.base import (
    SearchResult,
    VectorStore as VectorStoreABC,
)

logger = logging.getLogger(__name__)

# Check availability
SENTENCE_TRANSFORMERS_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    pass

# GGUF llama-server (direct, no Ollama)
GGUF_SERVER_URL = "http://localhost:8088"
GGUF_EMBED_MODEL = "nomic-embed-text-v1.5-Q4_K_M.gguf"
OLLAMA_URL = "http://localhost:8088"  # Legacy alias - now points to GGUF server
OLLAMA_MODEL = "nomic-embed-text"
EMBED_DIM = 768


# ---------------------------------------------------------------------------
# Vector Math Utilities
# ---------------------------------------------------------------------------


def dot_product(v1: List[float], v2: List[float]) -> float:
    """Compute dot product of two vectors."""
    if len(v1) != len(v2):
        raise ValueError(f"Vector dimension mismatch: {len(v1)} vs {len(v2)}")
    return sum(a * b for a, b in zip(v1, v2))


def l2_distance(v1: List[float], v2: List[float]) -> float:
    """Compute L2 (Euclidean) distance between two vectors."""
    if len(v1) != len(v2):
        raise ValueError(f"Vector dimension mismatch: {len(v1)} vs {len(v2)}")
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(v1) != len(v2):
        raise ValueError(f"Vector dimension mismatch: {len(v1)} vs {len(v2)}")
    dot = dot_product(v1, v2)
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


def normalize_vector(v: List[float]) -> List[float]:
    """Normalize a vector to unit length."""
    norm = math.sqrt(sum(a * a for a in v))
    if norm == 0.0:
        return [0.0] * len(v)
    return [a / norm for a in v]


# ---------------------------------------------------------------------------
# Similarity Search Engine (FAISS-accelerated when available)
# ---------------------------------------------------------------------------

# FAISS availability check
FAISS_AVAILABLE = False
try:
    import faiss
    import numpy as np

    FAISS_AVAILABLE = True
    logger.info("FAISS available - using GPU/CPU-accelerated vector search")
except ImportError:
    import numpy as np

    logger.warning("FAISS not available - falling back to O(n) brute force")


class SimilaritySearch:
    """Core similarity search engine supporting multiple distance metrics."""

    METRICS = {"cosine", "l2", "dot"}

    def __init__(self, metric: str = "cosine", use_faiss: bool = True):
        if metric not in self.METRICS:
            raise ValueError(
                f"Unsupported metric: {metric}. Choose from {self.METRICS}"
            )
        self.metric = metric
        self.use_faiss = use_faiss and FAISS_AVAILABLE
        self._faiss_index = None
        self._numpy_vectors = None

    def compute_similarity(self, query: List[float], vector: List[float]) -> float:
        if self.metric == "cosine":
            return cosine_similarity(query, vector)
        elif self.metric == "l2":
            dist = l2_distance(query, vector)
            return 1.0 / (1.0 + dist)
        elif self.metric == "dot":
            return dot_product(query, vector)
        else:
            raise ValueError(f"Unknown metric: {self.metric}")

    def _build_faiss_index(self, vectors: List[List[float]]) -> None:
        """Build FAISS index from vectors."""
        if not vectors or not self.use_faiss:
            return

        self._numpy_vectors = np.array(vectors, dtype=np.float32)
        dim = self._numpy_vectors.shape[1]

        if self.metric == "cosine":
            # Normalize for cosine similarity
            norms = np.linalg.norm(self._numpy_vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1  # Avoid division by zero
            self._numpy_vectors = self._numpy_vectors / norms
            # Use inner product (equivalent to cosine after normalization)
            self._faiss_index = faiss.IndexFlatIP(dim)
        elif self.metric == "l2":
            self._faiss_index = faiss.IndexFlatL2(dim)
        else:  # dot
            self._faiss_index = faiss.IndexFlatIP(dim)

        self._faiss_index.add(self._numpy_vectors)

    def search(
        self, query: List[float], vectors: List[List[float]], top_k: int = 10
    ) -> List[Tuple[int, float]]:
        if not vectors:
            return []

        # Use FAISS if available and vectors are large enough
        if self.use_faiss and len(vectors) > 100:
            # Rebuild index if vectors changed
            if self._numpy_vectors is None or len(self._numpy_vectors) != len(vectors):
                self._build_faiss_index(vectors)

            if self._faiss_index is not None:
                query_np = np.array([query], dtype=np.float32)
                if self.metric == "cosine":
                    query_norm = np.linalg.norm(query_np)
                    if query_norm > 0:
                        query_np = query_np / query_norm

                distances, indices = self._faiss_index.search(
                    query_np, min(top_k, len(vectors))
                )

                # Convert FAISS results to our format
                results = []
                for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                    if idx >= 0:  # FAISS returns -1 for invalid indices
                        results.append((int(idx), float(dist)))
                return results

        # Fallback to O(n) brute force for small vectors or no FAISS
        scores = []
        for idx, vec in enumerate(vectors):
            try:
                score = self.compute_similarity(query, vec)
                scores.append((idx, score))
            except ValueError as e:
                logger.debug(f"Skipping vector {idx}: {e}")
                continue
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------


@dataclass
class IndexStats:
    """Statistics for a vector index."""

    total_vectors: int
    dimension: int
    metric: str
    created_at: float
    last_updated: float
    memory_bytes: int = 0


# ---------------------------------------------------------------------------
# RRF Fusion Utility
# ---------------------------------------------------------------------------


def rrf_fusion(
    vector_results: list, keyword_results: list, k: int = 60, top_k: int = 10
) -> list:
    """
    Reciprocal Rank Fusion of two result lists.

    Args:
        vector_results: Results from vector similarity search
        keyword_results: Results from keyword/BM25 search
        k: RRF constant (default 60)
        top_k: Number of results to return

    Returns:
        Fused and ranked results
    """
    scores: dict[str, float] = {}

    for rank, result in enumerate(vector_results, 1):
        rid = result.id if hasattr(result, "id") else str(result.get("id", ""))
        scores[rid] = scores.get(rid, 0) + 1.0 / (k + rank)

    for rank, result in enumerate(keyword_results, 1):
        rid = result.id if hasattr(result, "id") else str(result.get("id", ""))
        scores[rid] = scores.get(rid, 0) + 1.0 / (k + rank)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]


# ---------------------------------------------------------------------------
# Vector Index (implements VectorStore ABC)
# ---------------------------------------------------------------------------


class VectorIndex(VectorStoreABC):
    """FAISS-style vector index with pure Python implementation."""

    def __init__(self, metric: str = "cosine", name: str = "default"):
        self.name = name
        self.metric = metric
        self._vectors: List[List[float]] = []
        self._metadata: List[Dict[str, Any]] = []
        self._ids: List[str] = []
        self._dimension: Optional[int] = None
        self._created_at: float = time.time()
        self._last_updated: float = self._created_at
        self._search_engine = SimilaritySearch(metric=metric)

    @property
    def size(self) -> int:
        return len(self._vectors)

    @property
    def dimension(self) -> Optional[int]:
        return self._dimension

    @property
    def is_empty(self) -> bool:
        return self.size == 0

    def add_vector(
        self, vector: List[float], metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Add a raw vector to the index (internal method)."""
        dim = len(vector)
        if self._dimension is None:
            self._dimension = dim
        elif dim != self._dimension:
            raise ValueError(
                f"Vector dimension {dim} doesn't match index dimension {self._dimension}"
            )
        self._vectors.append(vector)
        self._metadata.append(metadata or {})
        self._last_updated = time.time()
        return self.size - 1

    def add_batch(
        self,
        vectors: List[List[float]],
        metadata_list: Optional[List[Dict[str, Any]]] = None,
    ) -> List[int]:
        if metadata_list is None:
            metadata_list = [{}] * len(vectors)
        indices = []
        for vec, meta in zip(vectors, metadata_list):
            idx = self.add_vector(vec, meta)
            indices.append(idx)
        return indices

    def search_by_vector(
        self, query: List[float], top_k: int = 10, filter_fn: Optional[callable] = None
    ) -> List[SearchResult]:
        """Search by raw vector (internal method)."""
        if self.is_empty:
            return []
        if len(query) != self._dimension:
            raise ValueError(
                f"Query dimension {len(query)} doesn't match index dimension {self._dimension}"
            )
        raw_results = self._search_engine.search(
            query, self._vectors, top_k=max(top_k, self.size)
        )
        results = []
        for idx, score in raw_results:
            meta = self._metadata[idx]
            if filter_fn and not filter_fn(idx, meta):
                continue
            results.append(
                SearchResult(
                    id=str(idx),
                    content=meta.get("content", ""),
                    score=score,
                    metadata=meta,
                    source="semantic",
                )
            )
            if len(results) >= top_k:
                break
        return results

    def delete_by_index(self, index: int) -> bool:
        """Delete by index (internal method)."""
        if index < 0 or index >= self.size:
            return False
        self._vectors.pop(index)
        self._metadata.pop(index)
        self._last_updated = time.time()
        if self.is_empty:
            self._dimension = None
        return True

    def get_vector(self, index: int) -> Optional[List[float]]:
        if 0 <= index < self.size:
            return self._vectors[index]
        return None

    def get_metadata(self, index: int) -> Optional[Dict[str, Any]]:
        if 0 <= index < self.size:
            return self._metadata[index]
        return None

    def get_stats(self) -> IndexStats:
        memory_bytes = sum(len(v) * 8 for v in self._vectors)
        return IndexStats(
            total_vectors=self.size,
            dimension=self._dimension or 0,
            metric=self.metric,
            created_at=self._created_at,
            last_updated=self._last_updated,
            memory_bytes=memory_bytes,
        )

    def clear(self) -> None:
        self._vectors.clear()
        self._metadata.clear()
        self._ids.clear()
        self._dimension = None
        self._last_updated = time.time()

    # ---------------------------------------------------------------------------
    # VectorStore ABC Implementation
    # ---------------------------------------------------------------------------

    def add(self, id: str, content: str, vector: list[float]) -> None:
        """Add a vector to the store (ABC implementation)."""
        self._ids.append(id)
        self.add_vector(vector, {"id": id, "content": content})

    def search(self, query: str, top_k: int) -> list[SearchResult]:
        """Search for similar vectors (ABC implementation)."""
        query_vec = embed_text(query)
        raw_results = self._search_engine.search(query_vec, self._vectors, top_k=top_k)
        results = []
        for idx, score in raw_results:
            meta = self._metadata[idx]
            results.append(
                SearchResult(
                    id=self._ids[idx] if idx < len(self._ids) else str(idx),
                    content=meta.get("content", ""),
                    score=score,
                    metadata=meta,
                    source="semantic",
                )
            )
        return results

    def hybrid_search(
        self, query: str, top_k: int = 10, keyword_retriever=None
    ) -> list:
        """
        Combines vector similarity + keyword BM25 using RRF fusion.

        Args:
            query: Search query string
            top_k: Number of results to return
            keyword_retriever: Optional KeywordRetriever instance for BM25 search

        Returns:
            List of SearchResult objects with fused scores
        """
        from packages.memory_store.stores.base import SearchResult

        # 1. Get vector results
        vector_results = self.search(query, top_k * 2)

        # 2. Get keyword results (if retriever provided)
        keyword_results = []
        if keyword_retriever:
            try:
                keyword_results = keyword_retriever.search(query, top_k * 2)
            except Exception:
                keyword_results = []

        # 3. RRF fusion with k=60
        k = 60
        scores: dict[str, tuple[float, dict]] = {}  # id -> (score, metadata)

        # Score vector results
        for rank, result in enumerate(vector_results, 1):
            score = 1.0 / (k + rank)
            if hasattr(result, "id"):
                rid = result.id
                content = getattr(result, "content", "")
                metadata = getattr(result, "metadata", {})
            else:
                rid = str(result.get("id", ""))
                content = result.get("content", "")
                metadata = result.get("metadata", {})

            if rid in scores:
                scores[rid] = (scores[rid][0] + score, metadata)
            else:
                scores[rid] = (score, {"content": content, **metadata})

        # Score keyword results
        for rank, result in enumerate(keyword_results, 1):
            score = 1.0 / (k + rank)
            if hasattr(result, "id"):
                rid = result.id
                content = getattr(result, "content", "")
                metadata = getattr(result, "metadata", {})
            else:
                rid = str(result.get("id", ""))
                content = result.get("content", "")
                metadata = result.get("metadata", {})

            if rid in scores:
                scores[rid] = (scores[rid][0] + score, metadata)
            else:
                scores[rid] = (score, {"content": content, **metadata})

        # Sort by fused score and return top_k
        sorted_results = sorted(scores.items(), key=lambda x: x[1][0], reverse=True)[
            :top_k
        ]

        return [
            SearchResult(
                id=rid,
                content=data[1].get("content", ""),
                score=data[0],
                metadata=data[1],
                source="hybrid",
            )
            for rid, data in sorted_results
        ]

    def delete(self, id: str) -> bool:
        """Delete a vector by ID (ABC implementation)."""
        try:
            idx = self._ids.index(id)
            self._vectors.pop(idx)
            self._metadata.pop(idx)
            self._ids.pop(idx)
            self._last_updated = time.time()
            return True
        except ValueError:
            return False

    def stats(self) -> dict[str, Any]:
        """Get statistics about the store (ABC implementation)."""
        return {
            "total_vectors": self.size,
            "dimension": self._dimension or 0,
            "metric": self.metric,
            "created_at": self._created_at,
            "last_updated": self._last_updated,
            "memory_bytes": sum(len(v) * 8 for v in self._vectors),
        }

    def save(self, path: str) -> None:
        data = {
            "name": self.name,
            "metric": self.metric,
            "dimension": self._dimension,
            "created_at": self._created_at,
            "last_updated": self._last_updated,
            "vectors": self._vectors,
            "metadata": self._metadata,
        }
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info(f"Saved vector index '{self.name}' to {path} ({self.size} vectors)")

    @classmethod
    def load(cls, path: str) -> "VectorIndex":
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Index file not found: {path}")
        data = json.loads(file_path.read_text(encoding="utf-8"))
        index = cls(metric=data["metric"], name=data["name"])
        index._dimension = data["dimension"]
        index._created_at = data["created_at"]
        index._last_updated = data["last_updated"]
        index._vectors = data["vectors"]
        index._metadata = data["metadata"]
        logger.info(
            f"Loaded vector index '{index.name}' from {path} ({index.size} vectors)"
        )
        return index


# ---------------------------------------------------------------------------
# Embedding Engine
# ---------------------------------------------------------------------------


class EmbeddingEngine:
    """Synchronous wrapper for embedding generation with query caching.

    Priority: llama-cpp-python GGUF > Ollama > Sentence-Transformers > hash fallback
    """

    # GGUF embedding model path (local, no Ollama needed)
    NOMIC_GGUF_PATH = "models/nomic-embed-text-v1.5-Q4_K_M.gguf"

    def __init__(
        self,
        ollama_url: str = "http://localhost:8088",  # Direct GGUF, not Ollama
        ollama_model: str = "nomic-embed-text",
        st_model: str = "all-MiniLM-L6-v2",
        cache_size: int = 256,
        use_llama_cpp: bool = True,
    ):
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.st_model = st_model
        self.st_encoder = None
        self._st_loaded = False
        self._llama_cpp_model = None
        self._llama_cpp_loaded = False
        self.use_llama_cpp = use_llama_cpp
        # LRU cache for query embeddings
        self._query_cache: OrderedDict = OrderedDict()
        self._cache_size = cache_size
        # Reusable httpx client (no per-call overhead)
        self._http_client = None

    def embed_text(self, text: str) -> List[float]:
        # Check cache first
        cache_key = text.strip().lower()
        if cache_key in self._query_cache:
            self._query_cache.move_to_end(cache_key)
            return self._query_cache[cache_key]

        embedding = None

        # Try llama-cpp-python GGUF first (fastest, no network)
        if self.use_llama_cpp:
            try:
                embedding = self._embed_llama_cpp(text)
                if embedding:
                    self._query_cache[cache_key] = embedding
                    if len(self._query_cache) > self._cache_size:
                        self._query_cache.popitem(last=False)
                    return embedding
            except Exception as e:
                logger.debug(f"llama-cpp GGUF embedding failed: {e}")

        # Try Ollama
        try:
            embedding = self._embed_ollama_sync(text)
            if embedding:
                self._query_cache[cache_key] = embedding
                if len(self._query_cache) > self._cache_size:
                    self._query_cache.popitem(last=False)
                return embedding
        except Exception as e:
            logger.debug(f"Ollama embedding failed: {e}")

        # Fallback to Sentence-Transformers
        if self.st_encoder:
            try:
                embedding = self._embed_st(text)
                if embedding:
                    self._query_cache[cache_key] = embedding
                    if len(self._query_cache) > self._cache_size:
                        self._query_cache.popitem(last=False)
                    return embedding
            except Exception as e:
                logger.debug(f"ST embedding failed: {e}")

        # Last resort: hash-based pseudo-embedding
        embedding = self._embed_hash(text)
        self._query_cache[cache_key] = embedding
        if len(self._query_cache) > self._cache_size:
            self._query_cache.popitem(last=False)
        return embedding

    def prewarm(self) -> None:
        """Pre-warm the embedding model in the background.

        Call this on startup to avoid cold start latency on first query.
        """
        import threading

        def _prewarm():
            logger.info("EmbeddingEngine: Starting pre-warm...")
            # Force load the model by calling embed with a dummy string
            try:
                self.embed_text("[prewarm]")
                logger.info("EmbeddingEngine: Pre-warm complete")
            except Exception as e:
                logger.warning(f"EmbeddingEngine: Pre-warm failed: {e}")

        thread = threading.Thread(target=_prewarm, daemon=True)
        thread.start()
        logger.info("EmbeddingEngine: Pre-warm thread started (background)")

    def _embed_llama_cpp(self, text: str) -> Optional[List[float]]:
        """Embed using GGUF model directly via llama-cpp-python."""
        if self._llama_cpp_model:
            return self._llama_cpp_model.embed(text)

        from llama_cpp import Llama
        from pathlib import Path

        model_path = Path(__file__).parent.parent.parent.parent / self.NOMIC_GGUF_PATH
        if not model_path.exists():
            logger.warning(f"GGUF embedding model not found: {model_path}")
            return None

        try:
            self._llama_cpp_model = Llama(
                model_path=str(model_path),
                n_gpu_layers=-1,
                n_ctx=2048,  # Must match model training context
                n_threads=4,
                embedding=True,  # Enable embeddings
                verbose=False,
            )
            self._llama_cpp_loaded = True
            logger.info("EmbeddingEngine: GGUF model loaded via llama-cpp-python")
            return self._llama_cpp_model.embed(text)
        except Exception as e:
            logger.warning(f"Failed to load GGUF embedding model: {e}")
            return None

    def _get_http_client(self) -> httpx.Client:
        """Get or create reusable httpx client."""
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=30.0)
        return self._http_client

    def _embed_ollama_sync(self, text: str) -> Optional[List[float]]:

        client = self._get_http_client()
        try:
            resp = client.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.ollama_model, "prompt": text},
            )
            resp.raise_for_status()
            data = resp.json()
            embedding = data.get("embedding")
            if embedding:
                return embedding
        except Exception:
            pass
        return None

    def _embed_st(self, text: str) -> Optional[List[float]]:
        if not self._st_loaded:
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                try:
                    self.st_encoder = SentenceTransformer(self.st_model)
                    logger.info(
                        f"EmbeddingEngine: Sentence-Transformers loaded ({self.st_model})"
                    )
                    self._st_loaded = True
                except Exception as e:
                    logger.warning(f"EmbeddingEngine: Failed to load ST: {e}")
                    return None
            else:
                return None
        if not self.st_encoder:
            return None
        embedding = self.st_encoder.encode(text, convert_to_numpy=True)
        vec = embedding.tolist()
        if len(vec) < 768:
            vec = vec + [0.0] * (768 - len(vec))
        return vec[:768]

    def _embed_hash(self, text: str) -> List[float]:
        hash_bytes = hashlib.sha256(text.encode()).digest()
        embedding = []
        for i in range(768):
            byte_idx = i % len(hash_bytes)
            value = (hash_bytes[byte_idx] / 255.0) * 2 - 1
            embedding.append(value)
        return embedding

    def batch_embed(self, documents: List[str]) -> List[List[float]]:
        return [self.embed_text(doc) for doc in documents]

    def similarity(self, vec1: List[float], vec2: List[float]) -> float:
        if len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(a * a for a in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)


# Global engine instance
_engine: Optional[EmbeddingEngine] = None

# Module-level reusable httpx clients (no per-call overhead)
_http_client_short: Optional[httpx.Client] = None
_http_client_long: Optional[httpx.Client] = None


def _get_short_http_client() -> httpx.Client:
    """Get or create reusable httpx client for quick checks."""
    global _http_client_short
    if _http_client_short is None:
        _http_client_short = httpx.Client(timeout=5.0)
    return _http_client_short


def _get_long_http_client() -> httpx.Client:
    """Get or create reusable httpx client for long requests."""
    global _http_client_long
    if _http_client_long is None:
        _http_client_long = httpx.Client(timeout=30.0)
    return _http_client_long


def get_engine() -> EmbeddingEngine:
    global _engine
    if _engine is None:
        _engine = EmbeddingEngine()
        # Auto-prewarm on first engine creation
        _engine.prewarm()
    return _engine


def embed_text(text: str) -> List[float]:
    return get_engine().embed_text(text)


def batch_embed(documents: List[str]) -> List[List[float]]:
    return get_engine().batch_embed(documents)


def similarity(vec1: List[float], vec2: List[float]) -> float:
    return get_engine().similarity(vec1, vec2)


def prewarm() -> None:
    """Pre-warm the embedding engine in the background."""
    get_engine().prewarm()


# ---------------------------------------------------------------------------
# Vector Store (In-memory)
# ---------------------------------------------------------------------------


class VectorStore:
    """In-memory vector store for memory results."""

    def __init__(self, engine: Optional[EmbeddingEngine] = None):
        self.engine = engine or get_engine()
        self.documents: List[str] = []
        self.vectors: List[List[float]] = []
        self.metadata: List[dict] = []

    def add(self, text: str, metadata: Optional[dict] = None):
        vector = self.engine.embed_text(text)
        self.documents.append(text)
        self.vectors.append(vector)
        self.metadata.append(metadata or {})

    def search(self, query: str, top_k: int = 5) -> List[dict]:
        query_vec = self.engine.embed_text(query)
        results = []
        for idx, vec in enumerate(self.vectors):
            score = self.engine.similarity(query_vec, vec)
            results.append(
                {
                    "index": idx,
                    "text": self.documents[idx],
                    "score": score,
                    "metadata": self.metadata[idx],
                }
            )
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


# ---------------------------------------------------------------------------
# Auto-Embed Pipeline
# ---------------------------------------------------------------------------

_pending_embedding_queue: queue.Queue = queue.Queue()
_embedding_thread: Optional[threading.Thread] = None
_ollama_available: bool = True
_shutdown_event = threading.Event()


def _get_db_connection() -> sqlite3.Connection:
    return sqlite3.connect("context/memory/mind_from_mind.db")


# Global GGUF model for embeddings (lazy-loaded)
_gguf_embed_model = None


def _get_gguf_embed_model():
    """Get or create GGUF embedding model (lazy-loaded)."""
    global _gguf_embed_model
    if _gguf_embed_model is not None:
        return _gguf_embed_model

    from llama_cpp import Llama
    from pathlib import Path

    model_path = Path(__file__).parent.parent.parent / GGUF_EMBED_MODEL
    if not model_path.exists():
        logger.warning(f"GGUF embedding model not found: {model_path}")
        return None

    try:
        _gguf_embed_model = Llama(
            model_path=str(model_path),
            n_gpu_layers=-1,
            n_ctx=2048,
            n_threads=4,
            embedding=True,
            verbose=False,
        )
        logger.info("GGUF embedding model loaded via llama-cpp-python")
        return _gguf_embed_model
    except Exception as e:
        logger.warning(f"Failed to load GGUF embedding model: {e}")
        return None


def _embed_via_gguf(text: str) -> Optional[List[float]]:
    """Embed text using GGUF model directly (zero network overhead)."""
    model = _get_gguf_embed_model()
    if model is None:
        return None
    try:
        truncated = text[:2048]
        embedding = model.embed(truncated)
        if embedding and len(embedding) == EMBED_DIM:
            return embedding
    except Exception as e:
        logger.debug(f"GGUF embedding failed: {e}")
    return None


def _check_llama_server_available() -> bool:
    """Check if GGUF llama-server is running on port 8080."""
    try:
        client = _get_short_http_client()
        resp = client.get(f"{GGUF_SERVER_URL}/v1/models")
        return resp.status_code == 200
    except Exception:
        return False


def _embed_via_llama_server(text: str) -> Optional[List[float]]:
    """Embed text using llama-server HTTP API (fallback to GGUF server)."""
    try:
        truncated = text[:2048]
        client = _get_long_http_client()
        resp = client.post(
            f"{GGUF_SERVER_URL}/v1/embeddings",
            json={"model": "embedding-model", "input": truncated},
        )
        resp.raise_for_status()
        data = resp.json()
        embedding = data.get("data", [{}])[0].get("embedding", [])
        if embedding and len(embedding) == EMBED_DIM:
            return embedding
    except Exception as e:
        logger.debug(f"llama-server embedding failed: {e}")
    return None


def _check_ollama_available() -> bool:
    """Check if GGUF llama-server is available (port 8088)."""
    try:
        client = _get_short_http_client()
        resp = client.get(f"{GGUF_SERVER_URL}/v1/models")
        return resp.status_code == 200
    except Exception:
        return False


def _embed_via_ollama(text: str) -> Optional[List[float]]:
    """Embed via GGUF llama-server (OpenAI-compatible API)."""
    try:
        truncated = text[:2048]
        client = _get_long_http_client()
        resp = client.post(
            f"{GGUF_SERVER_URL}/v1/embeddings",
            json={"model": GGUF_EMBED_MODEL, "input": truncated},
        )
        resp.raise_for_status()
        data = resp.json()
        embedding = data.get("data", [{}])[0].get("embedding")
        if embedding and len(embedding) == EMBED_DIM:
            return embedding
    except Exception as e:
        logger.debug(f"GGUF embedding failed: {e}")
    return None


def _save_embedding_to_db(memory_id: str, embedding: List[float]) -> bool:
    try:
        vec_blob = struct.pack(f"<{EMBED_DIM}f", *embedding)
        conn = _get_db_connection()
        conn.execute(
            "INSERT OR REPLACE INTO memory_embeddings (memory_id, model, dim, vec) VALUES (?, ?, ?, ?)",
            (memory_id, OLLAMA_MODEL, EMBED_DIM, vec_blob),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to save embedding for {memory_id}: {e}")
        return False


def _has_existing_embedding(memory_id: str) -> bool:
    try:
        conn = _get_db_connection()
        cursor = conn.execute(
            "SELECT 1 FROM memory_embeddings WHERE memory_id = ?", (memory_id,)
        )
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except Exception:
        return False


def embed_memory(memory_id: str, content: str) -> bool:
    """Embed memory using GGUF llama-server (direct, no fallback)."""
    # Try GGUF direct first (fastest, no network)
    embedding = _embed_via_gguf(content)
    if embedding is not None:
        success = _save_embedding_to_db(memory_id, embedding)
        if success:
            logger.info(f"Embedded memory {memory_id} via GGUF")
        return success

    # Fallback: try llama-server HTTP (port 8088)
    embedding = _embed_via_llama_server(content)
    if embedding is not None:
        success = _save_embedding_to_db(memory_id, embedding)
        if success:
            logger.info(f"Embedded memory {memory_id} via llama-server")
        return success

    # Last resort: GGUF HTTP API (port 8088)
    embedding = _embed_via_ollama(content)
    if embedding is None:
        logger.warning(f"Failed to generate embedding for {memory_id}")
        _pending_embedding_queue.put((memory_id, content))
        return False

    success = _save_embedding_to_db(memory_id, embedding)
    if success:
        logger.info(f"Embedded memory {memory_id} via GGUF HTTP")
    return success


def embed_batch(
    memory_ids_and_contents: List[Tuple[str, str]], batch_size: int = 10
) -> int:
    """Embed batch of memories using GGUF (primary only)."""
    success_count = 0
    for i in range(0, len(memory_ids_and_contents), batch_size):
        batch = memory_ids_and_contents[i : i + batch_size]
        for memory_id, content in batch:
            # Try GGUF direct first
            embedding = _embed_via_gguf(content)
            if embedding is not None and _save_embedding_to_db(memory_id, embedding):
                success_count += 1
                continue

            # Fallback: llama-server HTTP (port 8088)
            embedding = _embed_via_llama_server(content)
            if embedding is not None and _save_embedding_to_db(memory_id, embedding):
                success_count += 1
                continue

            # Last resort: GGUF HTTP API (port 8088)
            embedding = _embed_via_ollama(content)
            if embedding is not None and _save_embedding_to_db(memory_id, embedding):
                success_count += 1
            else:
                logger.warning(f"Failed to embed memory {memory_id}")
    logger.info(
        f"Batch complete: {success_count}/{len(memory_ids_and_contents)} embedded"
    )
    return success_count


def auto_embed_on_save(memory_id: str, content: str) -> bool:
    if _has_existing_embedding(memory_id):
        logger.debug(f"Memory {memory_id} already has embedding, skipping")
        return True
    return embed_memory(memory_id, content)


def backfill_missing_embeddings(
    batch_size: int = 20, max_memories: Optional[int] = None
) -> dict:
    stats = {"processed": 0, "success": 0, "failed": 0, "remaining": 0}
    start_time = None
    try:
        conn = _get_db_connection()
        cursor = conn.execute(
            "SELECT COUNT(*) FROM memories m LEFT JOIN memory_embeddings e ON m.id = e.memory_id WHERE e.memory_id IS NULL AND m.content IS NOT NULL AND length(m.content) > 10"
        )
        stats["remaining"] = cursor.fetchone()[0]
        conn.close()
        if stats["remaining"] == 0:
            logger.info("No memories need embedding")
            return stats
        logger.info(f"Found {stats['remaining']} memories without embeddings")
        start_time = time.time()
        while True:
            if max_memories and stats["processed"] >= max_memories:
                break
            conn = _get_db_connection()
            cursor = conn.execute(
                "SELECT m.id, m.content FROM memories m LEFT JOIN memory_embeddings e ON m.id = e.memory_id WHERE e.memory_id IS NULL AND m.content IS NOT NULL AND length(m.content) > 10 LIMIT ?",
                (batch_size,),
            )
            rows = cursor.fetchall()
            conn.close()
            if not rows:
                break
            for memory_id, content in rows:
                stats["processed"] += 1
                try:
                    if embed_memory(memory_id, content):
                        stats["success"] += 1
                    else:
                        stats["failed"] += 1
                except Exception as e:
                    logger.error(f"Failed to embed {memory_id}: {e}")
                    stats["failed"] += 1
        elapsed = time.time() - start_time if start_time else 0
        stats["elapsed_seconds"] = round(elapsed, 1)
        conn = _get_db_connection()
        cursor = conn.execute(
            "SELECT COUNT(*) FROM memories m LEFT JOIN memory_embeddings e ON m.id = e.memory_id WHERE e.memory_id IS NULL AND m.content IS NOT NULL AND length(m.content) > 10"
        )
        stats["remaining"] = cursor.fetchone()[0]
        conn.close()
        logger.info(
            f"Backfill complete: {stats['processed']} processed, {stats['success']} success, {stats['failed']} failed, {stats['remaining']} remaining, {elapsed:.1f}s"
        )
        return stats
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        return stats


def _embedding_worker():
    while not _shutdown_event.is_set():
        try:
            memory_id, content = _pending_embedding_queue.get(timeout=5)
            logger.info(f"Processing queued embedding for {memory_id}")
            embed_memory(memory_id, content)
            _pending_embedding_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Embedding worker error: {e}")


def start_background_embedding():
    global _embedding_thread
    if _embedding_thread is None or not _embedding_thread.is_alive():
        _embedding_thread = threading.Thread(target=_embedding_worker, daemon=True)
        _embedding_thread.start()
        logger.info("Background embedding thread started")


def stop_background_embedding():
    global _embedding_thread
    _shutdown_event.set()
    if _embedding_thread and _embedding_thread.is_alive():
        _embedding_thread.join(timeout=10)
        logger.info("Background embedding thread stopped")


def get_pending_count() -> int:
    return _pending_embedding_queue.qsize()


# ---------------------------------------------------------------------------
# Package Exports
# ---------------------------------------------------------------------------

__all__ = [
    "VectorIndex",
    "SearchResult",
    "IndexStats",
    "SimilaritySearch",
    "EmbeddingEngine",
    "VectorStore",
    "rrf_fusion",
    "embed_text",
    "batch_embed",
    "similarity",
    "get_engine",
    "embed_memory",
    "embed_batch",
    "auto_embed_on_save",
    "backfill_missing_embeddings",
    "start_background_embedding",
    "stop_background_embedding",
    "get_pending_count",
]

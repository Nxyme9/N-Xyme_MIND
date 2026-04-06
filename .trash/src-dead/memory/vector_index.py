#!/usr/bin/env python3
"""
Vector Index — FAISS-style vector search foundation.

Provides:
- VectorIndex: Core index with add/search/delete operations
- SimilaritySearch: Cosine similarity and L2 distance search
- IndexManager: Multi-index management with persistence

Pure Python implementation — no external ML dependencies (no FAISS, no sklearn).
Uses math/stdlib only with numpy-style array operations via pure Python.

Supports:
- Cosine similarity (default for semantic search)
- L2/Euclidean distance (default for spatial search)
- Dot product similarity
- Batch indexing and search
- Index persistence (JSON-based)
- Metadata filtering
"""

import json
import logging
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    """Single search result with score and metadata."""

    index: int
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    vector: Optional[List[float]] = field(default=None, repr=False)


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
    """Compute cosine similarity between two vectors.

    Returns value in [-1, 1] where 1 means identical direction.
    """
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


def vector_magnitude(v: List[float]) -> float:
    """Compute magnitude (L2 norm) of a vector."""
    return math.sqrt(sum(a * a for a in v))


# ---------------------------------------------------------------------------
# Similarity Search Engine
# ---------------------------------------------------------------------------


class SimilaritySearch:
    """Core similarity search engine supporting multiple distance metrics."""

    METRICS = {"cosine", "l2", "dot"}

    def __init__(self, metric: str = "cosine"):
        """Initialize similarity search engine.

        Args:
            metric: Distance metric to use. One of 'cosine', 'l2', 'dot'.

        Raises:
            ValueError: If metric is not supported.
        """
        if metric not in self.METRICS:
            raise ValueError(
                f"Unsupported metric: {metric}. Choose from {self.METRICS}"
            )
        self.metric = metric

    def compute_similarity(self, query: List[float], vector: List[float]) -> float:
        """Compute similarity/distance between query and a stored vector.

        For cosine and dot: higher is better.
        For L2: lower is better (converted to similarity score).

        Args:
            query: Query vector.
            vector: Stored vector to compare against.

        Returns:
            Similarity score (higher = more similar for all metrics).
        """
        if self.metric == "cosine":
            return cosine_similarity(query, vector)
        elif self.metric == "l2":
            # Convert distance to similarity (inverse)
            dist = l2_distance(query, vector)
            return 1.0 / (1.0 + dist)
        elif self.metric == "dot":
            return dot_product(query, vector)
        else:
            raise ValueError(f"Unknown metric: {self.metric}")

    def search(
        self,
        query: List[float],
        vectors: List[List[float]],
        top_k: int = 10,
    ) -> List[Tuple[int, float]]:
        """Find most similar vectors to query.

        Args:
            query: Query vector.
            vectors: List of candidate vectors to search.
            top_k: Number of results to return.

        Returns:
            List of (index, score) tuples sorted by similarity (descending).
        """
        if not vectors:
            return []

        scores = []
        for idx, vec in enumerate(vectors):
            try:
                score = self.compute_similarity(query, vec)
                scores.append((idx, score))
            except ValueError as e:
                logger.debug(f"Skipping vector {idx}: {e}")
                continue

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def batch_search(
        self,
        queries: List[List[float]],
        vectors: List[List[float]],
        top_k: int = 10,
    ) -> List[List[Tuple[int, float]]]:
        """Search for multiple queries at once.

        Args:
            queries: List of query vectors.
            vectors: List of candidate vectors.
            top_k: Results per query.

        Returns:
            List of result lists, one per query.
        """
        return [self.search(q, vectors, top_k) for q in queries]


# ---------------------------------------------------------------------------
# Vector Index
# ---------------------------------------------------------------------------


class VectorIndex:
    """FAISS-style vector index with pure Python implementation.

    Provides add, search, delete, and persistence operations.
    Supports cosine similarity, L2 distance, and dot product.

    Example:
        >>> index = VectorIndex(metric="cosine")
        >>> index.add([0.1, 0.2, 0.3], {"text": "hello"})
        >>> index.add([0.4, 0.5, 0.6], {"text": "world"})
        >>> results = index.search([0.15, 0.25, 0.35], top_k=1)
        >>> print(results[0].metadata["text"])
        hello
    """

    def __init__(self, metric: str = "cosine", name: str = "default"):
        """Initialize vector index.

        Args:
            metric: Distance metric ('cosine', 'l2', 'dot').
            name: Human-readable name for this index.
        """
        self.name = name
        self.metric = metric
        self._vectors: List[List[float]] = []
        self._metadata: List[Dict[str, Any]] = []
        self._dimension: Optional[int] = None
        self._created_at: float = time.time()
        self._last_updated: float = self._created_at
        self._search_engine = SimilaritySearch(metric=metric)

    @property
    def size(self) -> int:
        """Number of vectors in the index."""
        return len(self._vectors)

    @property
    def dimension(self) -> Optional[int]:
        """Dimension of vectors in the index."""
        return self._dimension

    @property
    def is_empty(self) -> bool:
        """Check if index has no vectors."""
        return self.size == 0

    def add(
        self, vector: List[float], metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Add a vector to the index.

        Args:
            vector: Vector to add (must match index dimension).
            metadata: Optional metadata to associate with the vector.

        Returns:
            Index position of the added vector.

        Raises:
            ValueError: If vector dimension doesn't match existing vectors.
        """
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
        """Add multiple vectors to the index.

        Args:
            vectors: List of vectors to add.
            metadata_list: Optional list of metadata dicts (one per vector).

        Returns:
            List of index positions for added vectors.
        """
        if metadata_list is None:
            metadata_list = [{}] * len(vectors)

        if len(vectors) != len(metadata_list):
            raise ValueError("vectors and metadata_list must have same length")

        indices = []
        for vec, meta in zip(vectors, metadata_list):
            idx = self.add(vec, meta)
            indices.append(idx)
        return indices

    def search(
        self,
        query: List[float],
        top_k: int = 10,
        filter_fn: Optional[Callable[..., bool]] = None,  # type: ignore[type-arg]
    ) -> List[SearchResult]:
        """Search for most similar vectors.

        Args:
            query: Query vector.
            top_k: Number of results to return.
            filter_fn: Optional function to filter results.
                      Takes (index, metadata) and returns bool.

        Returns:
            List of SearchResult objects sorted by similarity.
        """
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
                    index=idx,
                    score=score,
                    metadata=meta,
                    vector=self._vectors[idx] if len(results) < top_k else None,
                )
            )
            if len(results) >= top_k:
                break

        return results

    def delete(self, index: int) -> bool:
        """Remove a vector from the index.

        Args:
            index: Position of vector to remove.

        Returns:
            True if deleted, False if index was invalid.
        """
        if index < 0 or index >= self.size:
            return False

        self._vectors.pop(index)
        self._metadata.pop(index)
        self._last_updated = time.time()

        # Reset dimension if index is now empty
        if self.is_empty:
            self._dimension = None

        return True

    def get_vector(self, index: int) -> Optional[List[float]]:
        """Get a vector by its index position."""
        if 0 <= index < self.size:
            return self._vectors[index]
        return None

    def get_metadata(self, index: int) -> Optional[Dict[str, Any]]:
        """Get metadata for a vector by its index position."""
        if 0 <= index < self.size:
            return self._metadata[index]
        return None

    def get_stats(self) -> IndexStats:
        """Get index statistics."""
        memory_bytes = sum(len(v) * 8 for v in self._vectors)  # 8 bytes per float
        return IndexStats(
            total_vectors=self.size,
            dimension=self._dimension or 0,
            metric=self.metric,
            created_at=self._created_at,
            last_updated=self._last_updated,
            memory_bytes=memory_bytes,
        )

    def clear(self) -> None:
        """Remove all vectors from the index."""
        self._vectors.clear()
        self._metadata.clear()
        self._dimension = None
        self._last_updated = time.time()

    # ---------------------------------------------------------------------------
    # Persistence
    # ---------------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Save index to disk.

        Args:
            path: File path to save to (JSON format).
        """
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
        file_path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )
        logger.info(f"Saved vector index '{self.name}' to {path} ({self.size} vectors)")

    @classmethod
    def load(cls, path: str) -> "VectorIndex":
        """Load index from disk.

        Args:
            path: File path to load from.

        Returns:
            Loaded VectorIndex instance.
        """
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
# Index Manager
# ---------------------------------------------------------------------------


class IndexManager:
    """Manager for multiple vector indices with persistence.

    Example:
        >>> manager = IndexManager(storage_dir="data/indices")
        >>> manager.create_index("semantic", metric="cosine")
        >>> manager.create_index("spatial", metric="l2")
        >>> manager.get_index("semantic").add([0.1, 0.2], {"text": "hello"})
        >>> results = manager.search("semantic", [0.15, 0.25])
    """

    def __init__(self, storage_dir: str = "data/vector_indices"):
        """Initialize index manager.

        Args:
            storage_dir: Directory for persisting indices.
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._indices: Dict[str, VectorIndex] = {}

    def create_index(
        self,
        name: str,
        metric: str = "cosine",
        load_existing: bool = True,
    ) -> VectorIndex:
        """Create or load a vector index.

        Args:
            name: Unique name for the index.
            metric: Distance metric for the index.
            load_existing: Try to load existing index from disk first.

        Returns:
            VectorIndex instance.
        """
        if name in self._indices:
            return self._indices[name]

        # Try to load existing index
        if load_existing:
            index_path = self.storage_dir / f"{name}.json"
            if index_path.exists():
                try:
                    index = VectorIndex.load(str(index_path))
                    self._indices[name] = index
                    return index
                except Exception as e:
                    logger.warning(f"Failed to load existing index '{name}': {e}")

        # Create new index
        index = VectorIndex(metric=metric, name=name)
        self._indices[name] = index
        return index

    def get_index(self, name: str) -> Optional[VectorIndex]:
        """Get an index by name."""
        return self._indices.get(name)

    def delete_index(self, name: str) -> bool:
        """Delete an index by name.

        Args:
            name: Name of index to delete.

        Returns:
            True if deleted, False if not found.
        """
        if name not in self._indices:
            return False

        del self._indices[name]

        # Also delete from disk
        index_path = self.storage_dir / f"{name}.json"
        if index_path.exists():
            index_path.unlink()

        return True

    def list_indices(self) -> Dict[str, IndexStats]:
        """Get stats for all managed indices."""
        return {name: idx.get_stats() for name, idx in self._indices.items()}

    def save_all(self) -> None:
        """Save all indices to disk."""
        for name, index in self._indices.items():
            index_path = self.storage_dir / f"{name}.json"
            index.save(str(index_path))
        logger.info(f"Saved {len(self._indices)} indices to {self.storage_dir}")

    def load_all(self) -> None:
        """Load all indices from disk."""
        for index_file in self.storage_dir.glob("*.json"):
            name = index_file.stem
            try:
                index = VectorIndex.load(str(index_file))
                self._indices[name] = index
            except Exception as e:
                logger.warning(f"Failed to load index '{name}': {e}")
        logger.info(f"Loaded {len(self._indices)} indices from {self.storage_dir}")

    def search(
        self,
        index_name: str,
        query: List[float],
        top_k: int = 10,
    ) -> List[SearchResult]:
        """Search a specific index by name.

        Args:
            index_name: Name of index to search.
            query: Query vector.
            top_k: Number of results.

        Returns:
            List of SearchResult objects.
        """
        index = self._indices.get(index_name)
        if index is None:
            raise ValueError(f"Index '{index_name}' not found")
        return index.search(query, top_k=top_k)


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------


def create_index(name: str = "default", metric: str = "cosine") -> VectorIndex:
    """Create a new vector index.

    Args:
        name: Index name.
        metric: Distance metric ('cosine', 'l2', 'dot').

    Returns:
        New VectorIndex instance.
    """
    return VectorIndex(name=name, metric=metric)


def compute_similarity(
    v1: List[float],
    v2: List[float],
    metric: str = "cosine",
) -> float:
    """Compute similarity between two vectors.

    Args:
        v1: First vector.
        v2: Second vector.
        metric: Distance metric.

    Returns:
        Similarity score.
    """
    engine = SimilaritySearch(metric=metric)
    return engine.compute_similarity(v1, v2)


def find_similar(
    query: List[float],
    candidates: List[List[float]],
    top_k: int = 10,
    metric: str = "cosine",
) -> List[Tuple[int, float]]:
    """Find most similar vectors from candidates.

    Args:
        query: Query vector.
        candidates: List of candidate vectors.
        top_k: Number of results.
        metric: Distance metric.

    Returns:
        List of (index, score) tuples.
    """
    engine = SimilaritySearch(metric=metric)
    return engine.search(query, candidates, top_k=top_k)

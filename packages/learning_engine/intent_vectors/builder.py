"""Intent Vector Builder - Phase 4.2: Build user intent vectors from history.

This module builds intent vectors from query→agent patterns and provides
FAISS-based similarity search for predictive routing.

Usage:
    builder = IntentVectorBuilder()
    builder.build_from_history()
    results = builder.find_similar("add feature")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np

# Configuration
INDEX_PATH = Path(__file__).parent / "intent_vectors"
INDEX_FILE = INDEX_PATH / "index.faiss"
METADATA_FILE = INDEX_PATH / "metadata.json"

# Fallback if FAISS not available - use simple cosine similarity
FAISS_AVAILABLE = False
try:
    import faiss

    FAISS_AVAILABLE = True
except ImportError:
    pass


@dataclass
class IntentEntry:
    """Single intent vector entry with metadata."""

    query: str
    agent: str
    embedding: np.ndarray
    success_rate: float = 1.0
    avg_latency_ms: float = 1000.0


@dataclass
class IntentIndex:
    """Index metadata for serialization."""

    entries: list[dict[str, Any]] = field(default_factory=list)
    dimension: int = 384
    created_at: str = ""
    updated_at: str = ""


class IntentVectorBuilder:
    """Build and query intent vectors for predictive routing."""

    def __init__(self, dimension: int = 384):
        """Initialize builder.

        Args:
            dimension: Embedding dimension (default 384 for sentence-transformers)
        """
        self.dimension = dimension
        self.index: Optional[Any] = None
        self.metadata: IntentIndex = IntentIndex()
        self._load_index()

    def _load_index(self) -> None:
        """Load existing index from disk if available."""
        if not METADATA_FILE.exists():
            return

        try:
            with open(METADATA_FILE) as f:
                data = json.load(f)
                self.metadata = IntentIndex(**data)

            if FAISS_AVAILABLE and INDEX_FILE.exists():
                self.index = faiss.read_index(str(INDEX_FILE))
        except Exception:
            pass

    def _save_index(self) -> None:
        """Persist index to disk."""
        INDEX_PATH.mkdir(parents=True, exist_ok=True)

        with open(METADATA_FILE, "w") as f:
            json.dump(
                {
                    "entries": self.metadata.entries,
                    "dimension": self.metadata.dimension,
                    "created_at": self.metadata.created_at,
                    "updated_at": self.metadata.updated_at,
                },
                f,
            )

        if FAISS_AVAILABLE and self.index:
            faiss.write_index(self.index, str(INDEX_FILE))

    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text using real sentence-transformers model.

        Uses model_cache.py which provides:
        - LRU caching (10,000 entries)
        - Thread-safe singleton pattern
        - Sentence-transformers/all-MiniLM-L6-v2 (384-dim)
        """
        try:
            from packages.learning_engine.embeddings.model_cache import (
                get_embedding_cache,
            )

            cache = get_embedding_cache()
            embedding = cache.encode(text)
            return embedding
        except Exception:
            # Fallback to hash-based if model unavailable
            import hashlib

            vec = np.zeros(self.dimension, dtype=np.float32)
            # Deterministic seed from text hash
            seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            rng = np.random.RandomState(seed)
            vec = rng.randn(self.dimension).astype(np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            return vec

    def build_from_history(self, max_entries: int = 500) -> dict[str, Any]:
        """Build intent vectors from outcome history.

        Args:
            max_entries: Maximum number of historical patterns to include

        Returns:
            Dict with count and status
        """
        from packages.learning_engine.outcome_logger import OutcomeLogger

        logger = OutcomeLogger()
        outcomes = logger.get_outcomes(limit=max_entries)

        # Build intent entries
        entries = {}
        for outcome in outcomes:
            key = outcome.task_description.lower().strip()
            if not key:
                continue

            if key not in entries:
                entries[key] = {
                    "query": outcome.task_description,
                    "agent": outcome.agent,
                    "count": 0,
                    "successes": 0,
                    "latencies": [],
                }

            entries[key]["count"] += 1
            if outcome.success:
                entries[key]["successes"] += 1
            entries[key]["latencies"].append(outcome.latency_ms)

        # Convert to intent entries
        self.metadata.entries = []
        for key, data in entries.items():
            embedding = self._get_embedding(key)
            success_rate = data["successes"] / data["count"] if data["count"] > 0 else 0
            avg_latency = (
                sum(data["latencies"]) / len(data["latencies"])
                if data["latencies"]
                else 0
            )

            self.metadata.entries.append(
                {
                    "query": data["query"],
                    "agent": data["agent"],
                    "count": data["count"],
                    "success_rate": success_rate,
                    "avg_latency_ms": avg_latency,
                }
            )

        # Build FAISS index
        if FAISS_AVAILABLE and self.metadata.entries:
            vectors = np.array(
                [self._get_embedding(e["query"]) for e in self.metadata.entries]
            ).astype("float32")

            self.index = faiss.IndexFlatIP(self.dimension)  # Inner product = cosine
            self.index.add(vectors)

        self.metadata.dimension = self.dimension
        self.metadata.updated_at = str(np.datetime64("now"))

        self._save_index()

        return {
            "status": "success",
            "entries_count": len(self.metadata.entries),
            "index_ready": self.index is not None,
        }

    def find_similar(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Find similar queries and their agents.

        Args:
            query: Search query
            top_k: Number of results to return
            min_score: Minimum similarity score (0-1)

        Returns:
            List of {query, agent, score, success_rate, avg_latency}
        """
        if not self.metadata.entries:
            return []

        query_embedding = self._get_embedding(query).reshape(1, -1).astype("float32")

        # Search index or fall back to linear scan
        if FAISS_AVAILABLE and self.index:
            scores, indices = self.index.search(
                query_embedding, min(top_k, len(self.metadata.entries))
            )
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and score >= min_score:
                    entry = self.metadata.entries[idx]
                    results.append(
                        {
                            "query": entry["query"],
                            "agent": entry["agent"],
                            "score": float(score),
                            "success_rate": entry.get("success_rate", 0),
                            "avg_latency_ms": entry.get("avg_latency_ms", 0),
                        }
                    )
            return results

        # Fallback: linear scan with cosine similarity
        results = []
        for entry in self.metadata.entries:
            entry_embedding = self._get_embedding(entry["query"])
            score = float(np.dot(query_embedding.flatten(), entry_embedding))
            if score >= min_score:
                results.append(
                    {
                        "query": entry["query"],
                        "agent": entry["agent"],
                        "score": score,
                        "success_rate": entry.get("success_rate", 0),
                        "avg_latency_ms": entry.get("avg_latency_ms", 0),
                    }
                )

        # Sort by score and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def predict_agent(self, query: str) -> list[str]:
        """Predict likely agents for a query (for pre-warming).

        Args:
            query: User query

        Returns:
            List of agent names sorted by likelihood
        """
        results = self.find_similar(query, top_k=3, min_score=0.1)
        return [r["agent"] for r in results]


def get_intent_builder() -> IntentVectorBuilder:
    """Get or create singleton intent builder."""
    global _intent_builder
    if _intent_builder is None:
        _intent_builder = IntentVectorBuilder()
    return _intent_builder


_intent_builder: Optional[IntentVectorBuilder] = None

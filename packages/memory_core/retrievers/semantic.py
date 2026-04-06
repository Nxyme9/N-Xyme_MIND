"""Semantic Retriever — Vector similarity search via embeddings."""

import hashlib
import logging
import sqlite3
import struct
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


class SemanticRetriever:
    """Retrieves memories by vector similarity using stored embeddings."""

    def __init__(self, db_path: Optional[str] = None):
        project_root = Path(__file__).resolve().parents[3]
        self.db_path = db_path or str(project_root / "context" / "memory" / "mind_from_mind.db")
        self._embedding_engine = None
        self._embedding_cache: Optional[tuple] = None  # (memory_ids, embeddings_matrix)
    def _get_embedding_engine(self):
        """Lazy-load embedding engine."""
        if self._embedding_engine is None:
            try:
                from ..stores.vector_store import get_engine

                self._embedding_engine = get_engine()
            except Exception as e:
                logger.warning(
                    f"Semantic retriever: Failed to load embedding engine: {e}"
                )
                return None
        return self._embedding_engine

    def search(
        self, query: str, top_k: int = 10, tier: Optional[str] = None
    ) -> List[dict]:
        """Search memories by semantic similarity.

        Args:
            query: Search query text
            top_k: Number of results to return
            tier: Memory tier filter (short_term, long_term, reasoning)

        Returns:
            List of result dicts with id, content, score, metadata
        """
        start = time.time()
        engine = self._get_embedding_engine()
        if engine is None:
            return []

        # Generate query embedding
        try:
            query_vec = engine.embed_text(query)
        except Exception as e:
            logger.warning(f"Semantic retriever: Failed to embed query: {e}")
            return []

        # Search in SQLite
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Use tier filter to reduce search space when possible
            if tier:
                cursor.execute(
                    "SELECT m.id, e.vec FROM memory_embeddings e "
                    "JOIN memories m ON e.memory_id = m.id WHERE m.tier = ?",
                    (tier,),
                )
            else:
                cursor.execute("SELECT memory_id, vec FROM memory_embeddings")
            rows = cursor.fetchall()

            if not rows:
                return []

            import numpy as np

            dim = len(query_vec)
            # Pre-allocate and unpack efficiently
            embeddings = np.zeros((len(rows), dim), dtype=np.float32)
            memory_ids = []
            for i, (mid, vec_blob) in enumerate(rows):
                memory_ids.append(mid)
                embeddings[i] = np.frombuffer(vec_blob, dtype=np.float32)

            # Vectorized cosine similarity
            query_arr = np.array(query_vec, dtype=np.float32)
            dot_products = embeddings @ query_arr
            query_norm = np.linalg.norm(query_arr)
            embedding_norms = np.linalg.norm(embeddings, axis=1)

            # Avoid division by zero
            norms = query_norm * embedding_norms
            norms[norms == 0] = 1.0
            scores = dot_products / norms

            # Use argpartition for O(n) top-k instead of O(n log n) argsort
            k = min(top_k * 2, len(scores))
            if k < len(scores):
                top_indices = np.argpartition(scores, -k)[-k:]
                top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]
            else:
                top_indices = np.argsort(scores)[::-1]

            # Get content for top results
            top_ids = [memory_ids[i] for i in top_indices]
            if not top_ids:
                return []

            # Use parameterized queries to prevent SQL injection
            placeholders = ",".join("?" * len(top_ids))
            params = list(top_ids)
            if tier:
                cursor.execute(
                    f"SELECT id, content, kind, scope, meta_json, tier FROM memories WHERE id IN ({placeholders}) AND tier = ?",
                    params + [tier],
                )
            else:
                cursor.execute(
                    f"SELECT id, content, kind, scope, meta_json, tier FROM memories WHERE id IN ({placeholders})",
                    params,
                )
            memories = {row[0]: row for row in cursor.fetchall()}

            # Build final results
            final_results = []
            for idx in top_indices:
                memory_id = memory_ids[idx]
                if memory_id in memories and len(final_results) < top_k:
                    row = memories[memory_id]
                    final_results.append(
                        {
                            "id": row[0],
                            "content": row[1][:2000] if row[1] else "",
                            "kind": row[2],
                            "scope": row[3],
                            "metadata": row[4] or "{}",
                            "tier": row[5],
                            "score": round(float(scores[idx]), 4),
                            "source": "semantic",
                        }
                    )

            elapsed = (time.time() - start) * 1000
            logger.info(
                f"Semantic retriever: {len(final_results)} results in {elapsed:.1f}ms"
            )
            return final_results

        except Exception as e:
            logger.error(f"Semantic retriever: Search failed: {e}")
            return []
        finally:
            conn.close()

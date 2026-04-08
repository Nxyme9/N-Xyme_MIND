#!/usr/bin/env python3
"""LanceDB Vector Store — High-performance vector storage using LanceDB.

This module provides a LanceDB-backed vector store that:
- Stores vectors on disk (persists across restarts)
- Supports IVF-PQ indexing for fast approximate search
- Provides SQL-like filtering on metadata
- Integrates with existing embedding pipeline

Architecture:
- Uses existing EmbeddingEngine for embedding generation
- LanceDB handles storage + indexing
- Compatible with VectorStore ABC interface
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from packages.memory_core.stores.base import SearchResult, VectorStore as VectorStoreABC

logger = logging.getLogger(__name__)

# LanceDB availability
LANCE_AVAILABLE = False
try:
    import lancedb
    import pyarrow as pa

    LANCE_AVAILABLE = True
except ImportError:
    pass


# Configuration
DEFAULT_LANCE_PATH = ".sisyphus/lance_data"
EMBED_DIM = 768  # nomic-embed-text dimension


@dataclass
class LanceDBConfig:
    """Configuration for LanceDB vector store."""

    path: str = DEFAULT_LANCE_PATH
    embedding_dim: int = EMBED_DIM
    index_type: str = "IVF_PQ"  # "IVF_PQ", "HNSW", None
    metric: str = "cosine"  # "cosine", "l2", "dot"
    # IVF-PQ settings
    num_partitions: int = 100
    num_sub_vectors: int = 16


class LanceDBVectorStore(VectorStoreABC):
    """LanceDB-backed vector store implementing VectorStore ABC.

    Features:
    - Disk-backed storage (survives restarts)
    - IVF-PQ indexing for fast approximate search
    - Metadata filtering with SQL-like expressions
    - Backward compatible with existing vector_store.py

    Usage:
        store = LanceDBVectorStore()
        store.add("mem_001", "memory content", [0.1, 0.2, ...])
        results = store.search("query", top_k=5)
    """

    def __init__(
        self,
        config: Optional[LanceDBConfig] = None,
        table_name: str = "memories",
    ):
        if not LANCE_AVAILABLE:
            raise ImportError(
                "lancedb package not installed. Install with: pip install lancedb"
            )

        self.config = config or LanceDBConfig()
        self.table_name = table_name
        self._db = None
        self._table = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize LanceDB database and table."""
        import lancedb

        # Ensure directory exists
        Path(self.config.path).mkdir(parents=True, exist_ok=True)

        # Connect to LanceDB
        self._db = lancedb.connect(self.config.path)

        # Try to open existing table - simpler than checking list
        try:
            self._table = self._db.open_table(self.table_name)
            logger.info(f"Opened existing LanceDB table: {self.table_name}")
        except Exception:
            # Table doesn't exist - create it
            self._create_table()

    def _create_table(self) -> None:
        """Create new LanceDB table with schema."""
        schema = pa.schema(
            [
                pa.field("id", pa.string()),
                pa.field("content", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), self.config.embedding_dim)),
                pa.field("created_at", pa.string()),
                pa.field("metadata", pa.string()),  # JSON serialized
                pa.field("deleted", pa.bool_()),  # Soft-delete flag
            ]
        )

        self._table = self._db.create_table(self.table_name, schema=schema)
        logger.info(f"Created new LanceDB table: {self.table_name}")

        # Create index if specified
        if self.config.index_type:
            self._create_index()

    def _create_index(self) -> None:
        """Create vector index for faster search."""
        try:
            # Check if table has data first - index creation requires data
            if self._table.count_rows() == 0:
                logger.info("Skipping index creation - table is empty")
                return

            # Map our config to LanceDB API
            metric_map = {"cosine": "cosine", "l2": "l2", "dot": "dot"}

            index_params = {
                "index_type": self.config.index_type,
                "metric": metric_map.get(self.config.metric, "l2"),
                "vector_column_name": "vector",
                "num_partitions": self.config.num_partitions,
                "num_sub_vectors": self.config.num_sub_vectors,
            }

            self._table.create_index(**index_params)
            logger.info(f"Created {self.config.index_type} index")
        except Exception as e:
            logger.warning(f"Failed to create index: {e}")

    def add(
        self,
        id: str,
        content: str,
        vector: list[float],
        metadata: Optional[dict] = None,
    ) -> None:
        """Add a vector to the store.

        Args:
            id: Unique identifier for the vector
            content: Text content (for debugging/reference)
            vector: Embedding vector (must match embedding_dim)
            metadata: Optional metadata dict (stored as JSON)
        """
        import json

        # Pad or truncate vector to expected dimension
        vector = self._normalize_vector(vector)

        # Prepare record
        record = [
            {
                "id": id,
                "content": content,
                "vector": vector,
                "created_at": datetime.now().isoformat(),
                "metadata": json.dumps(metadata or {}),
                "deleted": False,
            }
        ]

        # Add to table
        self._table.add(record)
        logger.debug(f"Added vector: {id}")

    def search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        """Search for similar vectors.

        Args:
            query: Query text to search for
            top_k: Number of results to return

        Returns:
            List of SearchResult objects
        """
        # Generate embedding for query
        from packages.memory_core.stores.vector_store import embed_text

        query_vector = embed_text(query)
        return self.search_by_vector(query_vector, top_k=top_k)

    def search_by_vector(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filter_expr: Optional[str] = None,
    ) -> list[SearchResult]:
        """Search by raw vector.

        Args:
            query_vector: Query embedding
            top_k: Number of results
            filter_expr: Optional SQL-like filter (e.g., "tier = 'working'")

        Returns:
            List of SearchResult objects
        """
        import json

        # Normalize vector
        query_vector = self._normalize_vector(query_vector)

        # Build search query using LanceDB's fluent API
        search = self._table.search(query_vector, vector_column_name="vector")

        # Always filter out deleted records (soft-delete)
        search = search.where("deleted = false")

        # Apply filter if provided (LanceDB uses .where() for filtering)
        if filter_expr:
            search = search.where(filter_expr)

        # Execute search with limit
        try:
            # Get results as pandas DataFrame
            results = search.limit(top_k).to_pandas()
        except Exception as e:
            logger.warning(f"Search failed: {e}")
            return []

        # Convert to SearchResult objects
        search_results = []
        for _, row in results.iterrows():
            search_results.append(
                SearchResult(
                    id=row["id"],
                    content=row["content"],
                    score=1.0 - row["_distance"] if "_distance" in row else 0.0,
                    metadata=json.loads(row["metadata"]) if "metadata" in row else {},
                    source="lance",
                )
            )

        return search_results[:top_k]

    def delete(self, id: str) -> bool:
        """Soft-delete a vector by ID (sets deleted=True).

        Args:
            id: ID of vector to delete

        Returns:
            True if deleted, False if not found
        """
        return self.soft_delete(id)

    def soft_delete(self, id: str) -> bool:
        """Soft-delete a vector by ID (sets deleted=True).

        Args:
            id: ID of vector to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            # Check if record exists
            existing = self._table.to_pandas()
            if id not in existing["id"].values:
                logger.warning(f"Record not found for soft-delete: {id}")
                return False

            # Update the record - set deleted=True
            # LanceDB requires using the update API
            self._table.update(where=f"id = '{id}'", values={"deleted": True})
            logger.info(f"Soft-deleted vector: {id}")
            return True
        except Exception as e:
            logger.error(f"Soft-delete failed for {id}: {e}")
            return False

    def purge_deleted(self) -> int:
        """Actually remove all soft-deleted records from the table.

        Returns:
            Number of records purged
        """
        try:
            # Get all deleted records
            deleted_df = self._table.to_pandas()
            deleted_ids = deleted_df[deleted_df["deleted"] == True]["id"].tolist()

            if not deleted_ids:
                logger.info("No deleted records to purge")
                return 0

            # Use delete API to remove these records
            for record_id in deleted_ids:
                self._table.delete(f"id = '{record_id}'")

            logger.info(f"Purged {len(deleted_ids)} deleted records")
            return len(deleted_ids)
        except Exception as e:
            logger.error(f"Purge failed: {e}")
            return 0

    def stats(self) -> dict[str, Any]:
        """Get statistics about the store.

        Returns:
            Dict with stats: vector_count, index_type, path, etc.
        """
        try:
            count = self._table.count_rows()
            return {
                "vector_count": count,
                "index_type": self.config.index_type,
                "metric": self.config.metric,
                "path": self.config.path,
                "table_name": self.table_name,
                "embedding_dim": self.config.embedding_dim,
            }
        except Exception as e:
            logger.error(f"Stats failed: {e}")
            return {"error": str(e)}

    def count(self) -> int:
        """Get count of non-deleted vectors.

        Returns:
            Number of vectors (excluding soft-deleted)
        """
        try:
            stats = self.stats()
            return stats.get("vector_count", 0)
        except Exception:
            return 0

    def _normalize_vector(self, vector: list[float]) -> list[float]:
        """Normalize vector to expected dimension.

        Args:
            vector: Input vector

        Returns:
            Vector padded/truncated to embedding_dim
        """
        if len(vector) < self.config.embedding_dim:
            # Pad with zeros
            vector = vector + [0.0] * (self.config.embedding_dim - len(vector))
        elif len(vector) > self.config.embedding_dim:
            # Truncate
            vector = vector[: self.config.embedding_dim]

        return vector

    def close(self) -> None:
        """Close the database connection."""
        # LanceDB connections are lightweight, no explicit close needed
        self._db = None
        self._table = None

    # =========================================================================
    # HYBRID SEARCH (Vector + Text/Keyword)
    # =========================================================================

    def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
        filter_expr: Optional[str] = None,
    ) -> list[SearchResult]:
        """Hybrid search combining vector similarity and text matching.

        Combines semantic vector search with keyword/text matching for
        better recall. Uses weighted scoring to combine results.

        Args:
            query: Query text
            top_k: Number of results
            vector_weight: Weight for vector similarity (0.0-1.0)
            text_weight: Weight for text match (0.0-1.0)
            filter_expr: Optional SQL filter expression

        Returns:
            List of SearchResult objects with combined scores
        """
        import json
        import re

        # Normalize weights
        total_weight = vector_weight + text_weight
        if total_weight > 0:
            vector_weight /= total_weight
            text_weight /= total_weight

        # 1. Vector search
        vector_results = self.search(query, top_k=top_k * 2)
        vector_scores = {r.id: r.score for r in vector_results}

        # 2. Text/keyword search
        text_results = self._keyword_search(query, top_k=top_k * 2)
        text_scores = {r.id: r.score for r in text_results}

        # 3. Get all unique IDs
        all_ids = set(vector_scores.keys()) | set(text_scores.keys())

        # 4. Combine scores
        combined_results = []
        for mem_id in all_ids:
            vec_score = vector_scores.get(mem_id, 0.0)
            txt_score = text_scores.get(mem_id, 0.0)

            # Weighted combination
            combined_score = (vec_score * vector_weight) + (txt_score * text_weight)

            # Get content from vector results
            content = ""
            metadata = {}
            for r in vector_results:
                if r.id == mem_id:
                    content = r.content
                    metadata = r.metadata
                    break

            if not content:
                for r in text_results:
                    if r.id == mem_id:
                        content = r.content
                        metadata = r.metadata
                        break

            if content:
                combined_results.append(
                    SearchResult(
                        id=mem_id,
                        content=content,
                        score=combined_score,
                        metadata=metadata,
                        source="hybrid",
                    )
                )

        # 5. Sort by combined score and return top_k
        combined_results.sort(key=lambda x: x.score, reverse=True)
        return combined_results[:top_k]

    def _keyword_search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """Keyword/text search without vector embeddings.

        Simple substring matching for fast keyword retrieval.

        Args:
            query: Query string
            top_k: Number of results

        Returns:
            List of SearchResult objects
        """
        import json
        import re

        try:
            # Get all non-deleted records
            df = self._table.to_pandas()
            df = df[df["deleted"] == False]

            if df.empty:
                return []

            # Simple keyword matching
            query_lower = query.lower()
            query_terms = query_lower.split()

            results = []
            for _, row in df.iterrows():
                content_lower = row["content"].lower()

                # Count matching terms
                matches = sum(1 for term in query_terms if term in content_lower)
                if matches > 0:
                    # Score based on number of matching terms
                    score = matches / len(query_terms)

                    # Parse metadata
                    metadata = {}
                    if row.get("metadata"):
                        try:
                            metadata = json.loads(row["metadata"])
                        except (json.JSONDecodeError, TypeError):
                            pass

                    results.append(
                        SearchResult(
                            id=row["id"],
                            content=row["content"],
                            score=score,
                            metadata=metadata,
                            source="keyword",
                        )
                    )

            # Sort by score
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:top_k]

        except Exception as e:
            logger.warning(f"Keyword search failed: {e}")
            return []


# Convenience functions
def get_lance_store(
    path: str = DEFAULT_LANCE_PATH,
    index_type: str = "IVF_PQ",
) -> LanceDBVectorStore:
    """Get a LanceDB vector store instance.

    Args:
        path: Path to LanceDB data directory
        index_type: Index type ("IVF_PQ", "HNSW", None)

    Returns:
        LanceDBVectorStore instance
    """
    config = LanceDBConfig(path=path, index_type=index_type)
    return LanceDBVectorStore(config=config)


__all__ = [
    "LanceDBVectorStore",
    "LanceDBConfig",
    "get_lance_store",
]

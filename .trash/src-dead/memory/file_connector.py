#!/usr/bin/env python3
"""File Connector — MemoryConnector for file embedding search."""

import json
import logging
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .connectors import HealthStatus, MemoryConnector, MemoryResult, get_project_root
from .embeddings import get_engine
from .drive_embedder import init_chroma

logger = logging.getLogger(__name__)

SQLITE_TABLE = "file_chunks"
PROJECT_ROOT = get_project_root()


def _get_sqlite_path(db_path: str) -> Path:
    """Get SQLite database path."""
    return PROJECT_ROOT / db_path / "file_chunks.db"


class FileConnector(MemoryConnector):
    """MemoryConnector implementation for file embedding search."""

    def __init__(self, db_path: str = "context/memory/file_chroma"):
        super().__init__(name="file_embeddings", enabled=True)
        self.db_path = db_path
        self.collection = init_chroma(db_path)
        self.embedding_engine = get_engine()
        self.sqlite_path = _get_sqlite_path(db_path)

    def health_check(self) -> HealthStatus:
        """Check if file embeddings are accessible."""
        start = time.time()
        try:
            count = self.collection.count()
            if not os.path.exists(self.sqlite_path):
                return HealthStatus(
                    self.name, True, (time.time() - start) * 1000, "no SQLite DB yet"
                )
            conn = sqlite3.connect(str(self.sqlite_path))
            conn.close()
            latency_ms = (time.time() - start) * 1000
            msg = f"{count} chunks indexed" if count > 0 else "empty collection"
            return HealthStatus(self.name, True, latency_ms, msg)
        except Exception as e:
            return HealthStatus(self.name, False, (time.time() - start) * 1000, str(e))

    def search(self, query: str, max_results: int = 10) -> list[MemoryResult]:
        """Search file embeddings.

        Args:
            query: Search query string.
            limit: Maximum number of results to return.

        Returns:
            List of MemoryResult objects.
        """
        try:
            query_embedding = self.embedding_engine.embed_text(query)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=max_results,
                include=["documents", "metadatas", "distances"],
            )

            memory_results = []
            if results and results.get("ids") and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    doc_id = results["ids"][0][i]
                    content = results["documents"][0][i]
                    metadata = results["metadatas"][0][i]
                    distance = (
                        results["distances"][0][i] if "distances" in results else 0.0
                    )

                    score = 1.0 - distance / 2.0

                    memory_results.append(
                        MemoryResult(
                            source=self.name,
                            id=doc_id,
                            content=content,
                            metadata=metadata,
                            score=score,
                            timestamp=datetime.now(),
                        )
                    )
            return memory_results
        except Exception as e:
            logger.error(f"FileConnector search failed: {e}")
            return []

    def get_file_context(self, file_path: str, chunk_index: int = 0) -> dict | None:
        """Get full file context for a specific chunk.

        Args:
            file_path: Path to the file.
            chunk_index: Index of the chunk (default: 0).

        Returns:
            Dictionary with content and metadata, or None if not found.
        """
        try:
            conn = sqlite3.connect(str(self.sqlite_path))
            cur = conn.cursor()
            cur.execute(
                f"SELECT text, metadata_json FROM {SQLITE_TABLE} WHERE file_path = ? AND chunk_index = ?",
                (file_path, chunk_index),
            )
            row = cur.fetchone()
            conn.close()
            if row:
                text_content, metadata_json = row
                metadata = json.loads(metadata_json) if metadata_json else {}
                return {"content": text_content, "metadata": metadata}
            return None
        except Exception as e:
            logger.error(f"FileConnector get_file_context failed: {e}")
            return None


__all__ = ["FileConnector"]

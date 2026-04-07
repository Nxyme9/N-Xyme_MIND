#!/usr/bin/env python3
"""Caching — Semantic cache by embedding similarity, TTL-based invalidation.

Features:
- Semantic similarity threshold: 0.95
- TTL: 1 hour general / 24 hours factual
- Cache size limit: 10GB
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("local_llm.caching")

# Default configuration
DEFAULT_DB_PATH = "~/.cache/n-xyme-mind/local_llm/cache.db"
DEFAULT_SIMILARITY_THRESHOLD = 0.95
DEFAULT_TTL_GENERAL = 3600  # 1 hour in seconds
DEFAULT_TTL_FACTUAL = 86400  # 24 hours in seconds
DEFAULT_MAX_SIZE_GB = 10


@dataclass
class CacheEntry:
    """A single cache entry."""

    cache_key: str
    request_hash: str
    request_text: str
    response_text: str
    embedding: Optional[bytes] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    ttl_seconds: int = DEFAULT_TTL_GENERAL
    is_factual: bool = False
    size_bytes: int = 0


class SemanticCache:
    """Semantic cache with embedding similarity and TTL.

    Uses embedding-based similarity for semantic matching.
    Supports TTL-based invalidation with separate rules for
    factual vs general content.
    """

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        ttl_general: int = DEFAULT_TTL_GENERAL,
        ttl_factual: int = DEFAULT_TTL_FACTUAL,
        max_size_gb: float = DEFAULT_MAX_SIZE_GB,
    ):
        """Initialize SemanticCache.

        Args:
            db_path: Path to SQLite cache database
            similarity_threshold: Cosine similarity threshold (0.0-1.0)
            ttl_general: TTL for general content in seconds
            ttl_factual: TTL for factual content in seconds
            max_size_gb: Maximum cache size in GB
        """
        self.db_path = str(Path(db_path).expanduser())
        self.similarity_threshold = similarity_threshold
        self.ttl_general = ttl_general
        self.ttl_factual = ttl_factual
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)

        self._lock = threading.Lock()
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Ensure database and tables exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT NOT NULL UNIQUE,
                request_hash TEXT NOT NULL,
                request_text TEXT NOT NULL,
                response_text TEXT NOT NULL,
                embedding BLOB,
                timestamp TEXT NOT NULL,
                ttl_seconds INTEGER NOT NULL,
                is_factual INTEGER NOT NULL DEFAULT 0,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                last_accessed TEXT
            )
        """)

        # Indices
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_key ON cache(cache_key)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cache_timestamp ON cache(timestamp)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_hash ON cache(request_hash)")

        conn.commit()
        conn.close()

    def _hash_request(self, request: str) -> str:
        """Create hash of request for exact match."""
        return hashlib.sha256(request.encode()).hexdigest()[:16]

    def _get_embedding(self, text: str) -> bytes:
        """Generate embedding for text using simple hash-based approach.

        Note: For production, replace with actual embedding model
        (e.g., sentence-transformers, Ollama embeddings).
        """
        # Simple hash-based pseudo-embedding for demonstration
        # In production, use: ollama embeddings or sentence-transformers
        hash_bytes = hashlib.sha256(text.encode()).digest()
        return hash_bytes

    def _cosine_similarity(self, emb1: bytes, emb2: bytes) -> float:
        """Calculate cosine similarity between two embeddings.

        Args:
            emb1: First embedding bytes
            emb2: Second embedding bytes

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Convert to floats for computation
        v1 = [float(b) for b in emb1[:64]]  # Use first 64 bytes
        v2 = [float(b) for b in emb2[:64]]

        # Ensure same length
        min_len = min(len(v1), len(v2))
        v1 = v1[:min_len]
        v2 = v2[:min_len]

        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude1 = sum(a * a for a in v1) ** 0.5
        magnitude2 = sum(b * b for b in v2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired."""
        try:
            created = datetime.fromisoformat(entry.timestamp)
            now = datetime.now()
            age = (now - created).total_seconds()
            return age > entry.ttl_seconds
        except (ValueError, TypeError):
            return True

    def _get_cache_size(self) -> int:
        """Get current cache size in bytes."""
        conn = sqlite3.connect(self.db_path)
        result = conn.execute("SELECT SUM(size_bytes) FROM cache").fetchone()
        conn.close()
        return result[0] if result and result[0] else 0

    def _evict_if_needed(self) -> None:
        """Evict oldest entries if cache exceeds size limit."""
        current_size = self._get_cache_size()

        if current_size > self.max_size_bytes:
            logger.info(f"Cache size {current_size} exceeds limit, evicting...")

            conn = sqlite3.connect(self.db_path)
            try:
                # Delete oldest entries until under limit
                while self._get_cache_size() > self.max_size_bytes * 0.9:
                    # Get oldest entry
                    oldest = conn.execute(
                        "SELECT id FROM cache ORDER BY timestamp ASC LIMIT 1"
                    ).fetchone()

                    if not oldest:
                        break

                    conn.execute("DELETE FROM cache WHERE id = ?", (oldest[0],))

                conn.commit()
            finally:
                conn.close()

    def _clean_expired(self) -> None:
        """Remove expired entries."""
        conn = sqlite3.connect(self.db_path)
        try:
            # Get all entries and check expiration
            rows = conn.execute(
                "SELECT id, timestamp, ttl_seconds FROM cache"
            ).fetchall()

            now = datetime.now()
            to_delete = []

            for row in rows:
                try:
                    created = datetime.fromisoformat(row[1])
                    age = (now - created).total_seconds()
                    if age > row[2]:
                        to_delete.append(row[0])
                except (ValueError, TypeError):
                    to_delete.append(row[0])

            if to_delete:
                conn.execute(
                    f"DELETE FROM cache WHERE id IN ({','.join('?' * len(to_delete))})",
                    to_delete,
                )
                conn.commit()
                logger.info(f"Cleaned {len(to_delete)} expired entries")
        finally:
            conn.close()

    def get(
        self,
        request: str,
        embedding: Optional[bytes] = None,
    ) -> Optional[str]:
        """Get cached response for request.

        Args:
            request: Request text
            embedding: Optional pre-computed embedding

        Returns:
            Cached response text or None if not found
        """
        self._clean_expired()

        request_hash = self._hash_request(request)
        emb = embedding or self._get_embedding(request)

        conn = sqlite3.connect(self.db_path)
        try:
            # Try exact hash match first
            row = conn.execute(
                "SELECT * FROM cache WHERE request_hash = ?",
                (request_hash,),
            ).fetchone()

            if row:
                # Update last accessed
                conn.execute(
                    "UPDATE cache SET last_accessed = ? WHERE id = ?",
                    (datetime.now().isoformat(), row[0]),
                )
                conn.commit()

                entry = CacheEntry(
                    cache_key=row[1],
                    request_hash=row[2],
                    request_text=row[3],
                    response_text=row[4],
                    embedding=row[5],
                    timestamp=row[6],
                    ttl_seconds=row[7],
                    is_factual=bool(row[8]),
                    size_bytes=row[9],
                )

                if not self._is_expired(entry):
                    logger.debug(f"Cache hit (exact): {request_hash}")
                    return entry.response_text

            # Try semantic similarity match
            if emb:
                all_rows = conn.execute(
                    "SELECT * FROM cache WHERE embedding IS NOT NULL"
                ).fetchall()

                for row in all_rows:
                    cached_emb = row[5]
                    if cached_emb:
                        similarity = self._cosine_similarity(emb, cached_emb)

                        if similarity >= self.similarity_threshold:
                            entry = CacheEntry(
                                cache_key=row[1],
                                request_hash=row[2],
                                request_text=row[3],
                                response_text=row[4],
                                embedding=cached_emb,
                                timestamp=row[6],
                                ttl_seconds=row[7],
                                is_factual=bool(row[8]),
                                size_bytes=row[9],
                            )

                            if not self._is_expired(entry):
                                # Update access time
                                conn.execute(
                                    "UPDATE cache SET last_accessed = ? WHERE id = ?",
                                    (datetime.now().isoformat(), row[0]),
                                )
                                conn.commit()

                                logger.debug(
                                    f"Cache hit (semantic): similarity={similarity:.3f}"
                                )
                                return entry.response_text

            return None
        finally:
            conn.close()

    def put(
        self,
        request: str,
        response: str,
        embedding: Optional[bytes] = None,
        is_factual: bool = False,
    ) -> str:
        """Store request/response in cache.

        Args:
            request: Request text
            response: Response text
            embedding: Optional pre-computed embedding
            is_factual: If True, use 24hr TTL instead of 1hr

        Returns:
            Cache key
        """
        self._clean_expired()
        self._evict_if_needed()

        request_hash = self._hash_request(request)
        emb = embedding or self._get_embedding(request)
        cache_key = f"{request_hash}_{int(time.time())}"

        ttl = self.ttl_factual if is_factual else self.ttl_general
        size_bytes = len(request) + len(response)

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO cache
                   (cache_key, request_hash, request_text, response_text, embedding,
                    timestamp, ttl_seconds, is_factual, size_bytes, last_accessed)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    cache_key,
                    request_hash,
                    request,
                    response,
                    emb,
                    datetime.now().isoformat(),
                    ttl,
                    1 if is_factual else 0,
                    size_bytes,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            logger.debug(f"Cached: {request_hash} (factual={is_factual}, ttl={ttl}s)")
            return cache_key
        finally:
            conn.close()

    def invalidate(self, request: str) -> bool:
        """Invalidate specific cache entry.

        Args:
            request: Request text to invalidate

        Returns:
            True if entry was found and removed
        """
        request_hash = self._hash_request(request)

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "DELETE FROM cache WHERE request_hash = ?",
                (request_hash,),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def clear(self) -> int:
        """Clear all cache entries.

        Returns:
            Number of entries removed
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM cache").fetchone()
            count = cursor[0] if cursor else 0

            conn.execute("DELETE FROM cache")
            conn.commit()

            logger.info(f"Cleared {count} cache entries")
            return count
        finally:
            conn.close()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        self._clean_expired()

        conn = sqlite3.connect(self.db_path)
        try:
            # Overall stats
            overall = conn.execute(
                """SELECT 
                    COUNT(*) as entries,
                    SUM(size_bytes) as total_size,
                    SUM(CASE WHEN is_factual = 1 THEN 1 ELSE 0 END) as factual,
                    AVG(ttl_seconds) as avg_ttl
                   FROM cache"""
            ).fetchone()

            # Recent entries
            recent = conn.execute(
                "SELECT COUNT(*) FROM cache WHERE last_accessed IS NOT NULL"
            ).fetchone()

            conn.close()

            total_size = overall[1] if overall and overall[1] else 0

            return {
                "entries": overall[0] if overall else 0,
                "total_size_bytes": total_size,
                "total_size_gb": round(total_size / (1024**3), 2),
                "factual_entries": overall[2] if overall else 0,
                "avg_ttl_seconds": round(overall[3], 2)
                if overall and overall[3]
                else 0,
                "recently_accessed": recent[0] if recent else 0,
                "max_size_gb": self.max_size_bytes / (1024**3),
                "similarity_threshold": self.similarity_threshold,
            }
        except Exception:
            return {}

    def close(self) -> None:
        """Close cache database."""
        pass  # SQLite connection closes automatically

    def __enter__(self) -> "SemanticCache":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


# Global singleton
_cache: Optional[SemanticCache] = None
_cache_lock = threading.Lock()


def get_cache() -> SemanticCache:
    """Get or create the global SemanticCache instance."""
    global _cache
    with _cache_lock:
        if _cache is None:
            _cache = SemanticCache()
        return _cache


def get(
    request: str,
    embedding: Optional[bytes] = None,
) -> Optional[str]:
    """Convenience function to get cached response."""
    return get_cache().get(request, embedding)


def put(
    request: str,
    response: str,
    embedding: Optional[bytes] = None,
    is_factual: bool = False,
) -> str:
    """Convenience function to store in cache."""
    return get_cache().put(request, response, embedding, is_factual)


def invalidate(request: str) -> bool:
    """Convenience function to invalidate cache entry."""
    return get_cache().invalidate(request)


def clear() -> int:
    """Convenience function to clear cache."""
    return get_cache().clear()


def get_stats() -> dict[str, Any]:
    """Convenience function to get cache stats."""
    return get_cache().get_stats()

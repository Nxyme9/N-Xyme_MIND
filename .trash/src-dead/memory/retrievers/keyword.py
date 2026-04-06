"""Keyword Retriever — Full-text search via SQLite FTS5."""

import logging
import sqlite3
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

logger = logging.getLogger(__name__)


class KeywordRetriever:
    """Retrieves memories by keyword matching using SQLite FTS5."""

    def __init__(self, db_path: Optional[str] = None):
        project_root = Path(__file__).resolve().parents[3]
        self.db_path: str = db_path or str(
            project_root / "context" / "memory" / "mind_from_mind.db"
        )

    def search(
        self, query: str, top_k: int = 10, tier: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search memories by keyword matching.

        Args:
            query: Search query text
            top_k: Number of results to return
            tier: Memory tier filter (short_term, long_term, reasoning)

        Returns:
            List of result dicts with id, content, score, metadata
        """
        start = time.time()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Check if FTS5 table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_fts'"
            )
            if not cursor.fetchone():
                logger.warning("Keyword retriever: FTS5 table not found")
                return []

            # Build FTS5 query - escape special characters
            # Replace spaces with AND for multi-word queries
            fts_query = " ".join(f'"{term}"' for term in query.split())

            # Use parameterized queries to prevent SQL injection
            if tier:
                cursor.execute(
                    """
                    SELECT f.rowid, m.id, m.content, m.kind, m.scope, m.meta_json, m.tier,
                           bm25(memory_fts) as rank
                    FROM memory_fts f
                    JOIN memories m ON f.rowid = m.rowid
                    WHERE memory_fts MATCH ? AND m.tier = ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (fts_query, tier, top_k),
                )
            else:
                cursor.execute(
                    """
                    SELECT f.rowid, m.id, m.content, m.kind, m.scope, m.meta_json, m.tier,
                           bm25(memory_fts) as rank
                    FROM memory_fts f
                    JOIN memories m ON f.rowid = m.rowid
                    WHERE memory_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (fts_query, top_k),
                )

            rows = cursor.fetchall()
            results: List[Dict[str, Any]] = []
            for row in rows:
                # BM25 score is negative (lower is better), convert to positive
                bm25_score = -row[7] if row[7] else 0
                # Normalize to 0-1 range
                score = min(1.0, bm25_score / 10.0) if bm25_score > 0 else 0.0

                results.append(
                    {
                        "id": row[1],
                        "content": row[2][:2000] if row[2] else "",
                        "kind": row[3],
                        "scope": row[4],
                        "metadata": row[5] or "{}",
                        "tier": row[6],
                        "score": round(score, 4),
                        "source": "keyword",
                    }
                )

            elapsed = (time.time() - start) * 1000
            logger.info(f"Keyword retriever: {len(results)} results in {elapsed:.1f}ms")
            return results

        except Exception as e:
            logger.error(f"Keyword retriever: Search failed: {e}")
            return []
        finally:
            conn.close()

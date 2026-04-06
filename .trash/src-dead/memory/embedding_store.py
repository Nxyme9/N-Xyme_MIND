"""Semantic Embedding Store for Task Similarity

Enables:
- Task similarity search using embeddings
- Find similar successful past tasks
- Recommend agents based on historical patterns
"""

import sqlite3
import json
import hashlib
from pathlib import Path
import time
from typing import List, Dict, Any, Optional


class EmbeddingStore:
    """Simple embedding store using hash-based similarity for tasks."""

    def __init__(self, db_path: str = "context/memory/embeddings.db"):
        self._db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS task_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_hash TEXT NOT NULL,
                task_text TEXT NOT NULL,
                agent TEXT,
                success INTEGER,
                level INTEGER,
                latency_ms REAL,
                context_json TEXT,
                timestamp REAL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_hash ON task_embeddings(task_hash)
        """)
        conn.commit()
        conn.close()

    def _hash_task(self, text: str) -> str:
        """Create a hash for task text."""
        return hashlib.sha256(text.lower().encode()).hexdigest()[:16]

    def _tokenize(self, text: str) -> set:
        """Simple tokenization."""
        return set(text.lower().split())

    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts."""
        tokens1 = self._tokenize(text1)
        tokens2 = self._tokenize(text2)
        if not tokens1 or not tokens2:
            return 0.0
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        return intersection / union if union > 0 else 0.0

    def store_task(
        self,
        task_text: str,
        agent: str,
        success: bool,
        level: int,
        latency_ms: float,
        context: Optional[Dict] = None,
    ) -> None:
        """Store a task with its outcome."""
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            """
            INSERT INTO task_embeddings 
            (task_hash, task_text, agent, success, level, latency_ms, context_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                self._hash_task(task_text),
                task_text,
                agent,
                1 if success else 0,
                level,
                latency_ms,
                json.dumps(context or {}),
                time.time(),
            ),
        )
        conn.commit()
        conn.close()

    def find_similar(
        self, task_text: str, top_k: int = 5, min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Find similar past tasks."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.execute("""
            SELECT task_text, agent, success, level, latency_ms, timestamp
            FROM task_embeddings
            ORDER BY timestamp DESC
            LIMIT 100
        """)

        results = []
        for row in cur:
            similarity = self._jaccard_similarity(task_text, row["task_text"])
            if similarity >= min_similarity:
                results.append(
                    {
                        "task_text": row["task_text"],
                        "agent": row["agent"],
                        "success": bool(row["success"]),
                        "level": row["level"],
                        "latency_ms": row["latency_ms"],
                        "similarity": similarity,
                        "timestamp": row["timestamp"],
                    }
                )

        conn.close()

        # Sort by similarity and return top_k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def recommend_agent(self, task_text: str) -> Optional[Dict[str, Any]]:
        """Recommend best agent based on similar successful tasks."""
        similar = self.find_similar(task_text, top_k=10, min_similarity=0.2)

        if not similar:
            return None

        # Weight by similarity and success
        agent_scores = {}
        for task in similar:
            if task["success"]:
                agent = task["agent"]
                if agent not in agent_scores:
                    agent_scores[agent] = {"score": 0, "count": 0}
                agent_scores[agent]["score"] += task["similarity"]
                agent_scores[agent]["count"] += 1

        if not agent_scores:
            return None

        # Return best agent
        best_agent = max(agent_scores.items(), key=lambda x: x[1]["score"])
        return {
            "agent": best_agent[0],
            "score": best_agent[1]["score"],
            "similar_tasks": best_agent[1]["count"],
            "sample_tasks": [
                t["task_text"] for t in similar[:3] if t["agent"] == best_agent[0]
            ],
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get embedding store statistics."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT COUNT(*) as total FROM task_embeddings")
        total = cur.fetchone()[0]

        cur = conn.execute("""
            SELECT agent, COUNT(*) as count, 
                   SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as successes,
                   AVG(latency_ms) as avg_latency
            FROM task_embeddings
            GROUP BY agent
        """)

        agent_stats = []
        for row in cur:
            agent_stats.append(
                {
                    "agent": row["agent"],
                    "tasks": row["count"],
                    "success_rate": row["successes"] / row["count"]
                    if row["count"] > 0
                    else 0,
                    "avg_latency": row["avg_latency"] or 0,
                }
            )

        conn.close()

        return {"total_tasks": total, "agent_stats": agent_stats}


# Global instance
_embedding_store: Optional[EmbeddingStore] = None


def get_embedding_store() -> EmbeddingStore:
    global _embedding_store
    if _embedding_store is None:
        _embedding_store = EmbeddingStore()
    return _embedding_store

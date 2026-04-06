"""Relational Store — SQLite-based structured memory storage."""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RelationalStore:
    """SQLite-based relational memory store."""

    def __init__(self, db_path: str = "context/memory/mind_from_mind.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_tables()

    def _ensure_tables(self):
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY, content TEXT, kind TEXT, scope TEXT, tier TEXT, meta_json TEXT, created_at TEXT, updated_at TEXT, archived INTEGER DEFAULT 0)"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS memory_embeddings (memory_id TEXT PRIMARY KEY, model TEXT, dim INTEGER, vec BLOB)"""
            )
            conn.commit()
        finally:
            conn.close()

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                "SELECT id, content, kind, scope, meta_json FROM memories WHERE content LIKE ? AND archived = 0 LIMIT ?",
                (f"%{query}%", limit),
            )
            return [
                {
                    "id": row[0],
                    "content": row[1],
                    "kind": row[2],
                    "scope": row[3],
                    "metadata": row[4],
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def store(
        self,
        id: str,
        content: str,
        kind: str = "episodic",
        scope: str = "session",
        **kwargs,
    ) -> str:
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                "INSERT OR REPLACE INTO memories (id, content, kind, scope, meta_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
                (id, content, kind, scope, json.dumps(kwargs.get("metadata", {}))),
            )
            conn.commit()
            return id
        finally:
            conn.close()

    def delete(self, id: str) -> bool:
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                "UPDATE memories SET archived = 1 WHERE id = ?", (id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get(self, id: str) -> Optional[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                "SELECT id, content, kind, scope, meta_json FROM memories WHERE id = ?",
                (id,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "content": row[1],
                    "kind": row[2],
                    "scope": row[3],
                    "metadata": row[4],
                }
            return None
        finally:
            conn.close()

    def stats(self) -> Dict[str, Any]:
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                "SELECT COUNT(*), COUNT(DISTINCT kind) FROM memories WHERE archived = 0"
            )
            row = cursor.fetchone()
            return {"total_memories": row[0] or 0, "memory_types": row[1] or 0}
        finally:
            conn.close()


__all__ = ["RelationalStore"]

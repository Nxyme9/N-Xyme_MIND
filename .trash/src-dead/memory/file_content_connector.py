"""File content connector for memory router — queries indexed file content."""

import logging
import sqlite3
from pathlib import Path
from typing import List, Optional

from src.memory.connectors import MemoryConnector, MemoryResult, HealthStatus

logger = logging.getLogger(__name__)


class FileContentConnector(MemoryConnector):
    """Connector for searching indexed file content."""

    def __init__(self, db_path: Optional[str] = None):
        super().__init__("file_content")
        self.db_path = db_path or str(
            Path(__file__).parent.parent.parent / "context/memory/mind_from_mind.db"
        )

    def search(self, query: str, max_results: int = 5) -> List[MemoryResult]:
        """Search indexed file content via FTS5 or LIKE fallback."""
        results = []
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Escape LIKE wildcards and use parameterized query
            escaped_query = query.replace("%", "\\%").replace("_", "\\_")
            like_query = f"%{escaped_query}%"
            cursor.execute(
                """
                SELECT id, content, meta_json, created_at
                FROM memories
                WHERE kind = 'file' AND content LIKE ? ESCAPE '\\'
                LIMIT ?
            """,
                (like_query, max_results),
            )
            rows = cursor.fetchall()

            for row in rows:
                chunk_id, content, meta_json, created_at = row
                results.append(
                    MemoryResult(
                        source=self.name,
                        id=chunk_id,
                        content=content[:2000] if content else "",
                        metadata={"meta_json": meta_json, "created_at": created_at},
                        score=0.7,
                    )
                )

            conn.close()
        except Exception as e:
            logger.warning(f"File content search failed: {e}")

        return results

    def health_check(self) -> HealthStatus:
        """Check if file content index is accessible."""
        import time

        start = time.time()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM file_index")
            count = cursor.fetchone()[0]
            conn.close()
            return HealthStatus(
                self.name, True, (time.time() - start) * 1000, f"{count} files indexed"
            )
        except Exception as e:
            return HealthStatus(self.name, False, (time.time() - start) * 1000, str(e))

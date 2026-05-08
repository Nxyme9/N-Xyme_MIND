"""Memory Connectors — Abstract base and concrete connectors for unified memory."""

import logging
import os
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Any, List, Optional
from dataclasses import dataclass
from datetime import datetime


def get_project_root():
    env_root = os.environ.get("NX_MIND_ROOT") or os.environ.get("ATHENA_CONTEXT_ROOT")
    if env_root:
        return Path(env_root)
    return Path(__file__).parent.parent.parent.resolve()


PROJECT_ROOT = get_project_root()


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class MemoryResult:
    """Result from a memory source."""

    source: str
    id: str
    content: str
    metadata: dict
    score: float = 1.0
    timestamp: Optional[datetime] = None


@dataclass
class HealthStatus:
    """Health status of a memory source."""

    source: str
    healthy: bool
    latency_ms: float
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Base Connector
# ---------------------------------------------------------------------------


class MemoryConnector(ABC):
    """Abstract base class for memory connectors."""

    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> List[MemoryResult]:
        """Search memory for query."""
        pass

    @abstractmethod
    def health_check(self) -> HealthStatus:
        """Check if connector is healthy."""
        pass

    def close(self):
        """Clean up resources. Override if needed."""
        pass


# ---------------------------------------------------------------------------
# Athena Context Connector
# ---------------------------------------------------------------------------


class AthenaConnector(MemoryConnector):
    """Connector for Athena context MCP (active/product/user/constraints)."""

    def __init__(self):
        super().__init__("athena")
        self._context_cache: dict = {}

    def search(self, query: str, max_results: int = 5) -> List[MemoryResult]:
        """Search Athena context files."""
        results = []
        try:
            import os

            root = os.environ.get("ATHENA_CONTEXT_ROOT", str(PROJECT_ROOT))

            # Active context
            active_path = os.path.join(root, ".context", "activeContext.md")
            if os.path.exists(active_path):
                with open(active_path) as f:
                    content = f.read()
                    if query.lower() in content.lower():
                        results.append(
                            MemoryResult(
                                source=self.name,
                                id="active_context",
                                content=content[:2000],
                                metadata={"type": "active_context"},
                                score=0.9,
                            )
                        )

            # Product context
            product_path = os.path.join(root, ".context", "productContext.md")
            if os.path.exists(product_path):
                with open(product_path) as f:
                    content = f.read()
                    if query.lower() in content.lower():
                        results.append(
                            MemoryResult(
                                source=self.name,
                                id="product_context",
                                content=content[:2000],
                                metadata={"type": "product_context"},
                                score=0.8,
                            )
                        )

            # User context
            user_path = os.path.join(root, ".context", "userContext.md")
            if os.path.exists(user_path):
                with open(user_path) as f:
                    content = f.read()
                    if query.lower() in content.lower():
                        results.append(
                            MemoryResult(
                                source=self.name,
                                id="user_context",
                                content=content[:2000],
                                metadata={"type": "user_context"},
                                score=0.7,
                            )
                        )

        except Exception as e:
            logger.warning(f"Athena search failed: {e}")

        return results[:max_results]

    def health_check(self) -> HealthStatus:
        """Check Athena context files."""
        import os
        import time

        start = time.time()
        try:
            root = os.environ.get("ATHENA_CONTEXT_ROOT", str(PROJECT_ROOT))
            path = os.path.join(root, ".context", "activeContext.md")
            if os.path.exists(path):
                return HealthStatus(self.name, True, (time.time() - start) * 1000)
            return HealthStatus(
                self.name, False, (time.time() - start) * 1000, "context file missing"
            )
        except Exception as e:
            return HealthStatus(self.name, False, 0, str(e))


# ---------------------------------------------------------------------------
# Memory MCP Connector (Knowledge Graph)
# ---------------------------------------------------------------------------


class MemoryMCPConnector(MemoryConnector):
    """Connector for Memory MCP (knowledge graph entities)."""

    def __init__(self):
        super().__init__("memory_mcp")

    def search(self, query: str, max_results: int = 5) -> List[MemoryResult]:
        """Search knowledge graph via Memory MCP."""
        results = []
        try:
            import os
            import json

            root = os.environ.get("ATHENA_CONTEXT_ROOT", str(PROJECT_ROOT))
            graph_path = os.path.join(root, ".context", "knowledge-graph.json")
            if os.path.exists(graph_path):
                with open(graph_path) as f:
                    graph = json.load(f)
                query_lower = query.lower()
                for entity in graph.get("entities", []):
                    if query_lower in entity.get("name", "").lower():
                        results.append(
                            MemoryResult(
                                source=self.name,
                                id=entity.get("id", ""),
                                content=str(entity.get("observations", [])),
                                metadata={"type": "entity"},
                                score=0.8,
                            )
                        )
        except Exception as e:
            logger.warning(f"Memory MCP search failed: {e}")

        return results[:max_results]

    def health_check(self) -> HealthStatus:
        """Check Memory MCP graph."""
        import os
        import time

        start = time.time()
        try:
            root = os.environ.get("ATHENA_CONTEXT_ROOT", str(PROJECT_ROOT))
            graph_path = os.path.join(root, ".context", "knowledge-graph.json")
            if os.path.exists(graph_path):
                return HealthStatus(self.name, True, (time.time() - start) * 1000)
            return HealthStatus(
                self.name,
                True,
                (time.time() - start) * 1000,
                "no graph file (optional)",
            )
        except Exception as e:
            return HealthStatus(self.name, False, 0, str(e))


# ---------------------------------------------------------------------------
# Session Connector (OpenCode sessions)
# ---------------------------------------------------------------------------


class SessionConnector(MemoryConnector):
    """Connector for OpenCode session history."""

    def __init__(self):
        super().__init__("session")

    def search(self, query: str, max_results: int = 5) -> List[MemoryResult]:
        """Search OpenCode sessions."""
        results = []
        try:
            import os
            import json

            session_dir = os.path.join(
                os.environ.get("ATHENA_CONTEXT_ROOT", str(PROJECT_ROOT)), ".sisyphus"
            )
            if os.path.exists(session_dir):
                for fname in os.listdir(session_dir):
                    if fname.endswith(".json"):
                        fpath = os.path.join(session_dir, fname)
                        with open(fpath) as f:
                            data = json.load(f)
                            content = json.dumps(data)
                            if query.lower() in content.lower():
                                results.append(
                                    MemoryResult(
                                        source=self.name,
                                        id=fname,
                                        content=content[:2000],
                                        metadata={"type": "session"},
                                        score=0.6,
                                    )
                                )
        except Exception as e:
            logger.warning(f"Session search failed: {e}")

        return results[:max_results]

    def health_check(self) -> HealthStatus:
        """Check session directory."""
        import os
        import time

        start = time.time()
        try:
            root = os.environ.get("ATHENA_CONTEXT_ROOT", str(PROJECT_ROOT))
            session_dir = os.path.join(root, ".sisyphus")
            if os.path.exists(session_dir):
                return HealthStatus(self.name, True, (time.time() - start) * 1000)
            return HealthStatus(
                self.name, True, (time.time() - start) * 1000, "no sessions yet"
            )
        except Exception as e:
            return HealthStatus(self.name, False, 0, str(e))


# ---------------------------------------------------------------------------
# SQLite Connector (Generic SQLite sources)
# ---------------------------------------------------------------------------


class SQLiteConnector(MemoryConnector):
    """Connector for generic SQLite memory DBs."""

    def __init__(
        self,
        name: str,
        db_path: str,
        table: str = "memories",
        content_col: str = "content",
    ):
        super().__init__(name)
        self.db_path = db_path
        self.table = table
        self.content_col = content_col

    def search(self, query: str, max_results: int = 5) -> List[MemoryResult]:
        results = []
        try:
            import sqlite3

            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                f"SELECT rowid, {self.content_col} FROM {self.table} "
                f"WHERE {self.content_col} LIKE ? LIMIT ?",
                (f"%{query}%", max_results),
            )
            for row in cur.fetchall():
                results.append(
                    MemoryResult(
                        source=self.name,
                        id=str(row[0]),
                        content=row[1][:2000],
                        metadata={"type": "sqlite"},
                        score=0.7,
                    )
                )
            cur.close()
            conn.close()
        except Exception as e:
            logger.warning(f"SQLite search failed ({self.name}): {e}")
        return results

    def health_check(self) -> HealthStatus:
        import os
        import time
        import sqlite3

        start = time.time()
        try:
            if not os.path.exists(self.db_path):
                return HealthStatus(
                    self.name, False, 0, f"DB not found: {self.db_path}"
                )
            conn = sqlite3.connect(self.db_path)
            conn.close()
            return HealthStatus(self.name, True, (time.time() - start) * 1000)
        except Exception as e:
            return HealthStatus(self.name, False, 0, str(e))


# ---------------------------------------------------------------------------
# Memory DB Connector (SQLite memories table)
# ---------------------------------------------------------------------------


class MemoryDBConnector(MemoryConnector):
    """Connector for mind_from_mind.db memories table."""

    DB_PATH = PROJECT_ROOT / "context" / "memory" / "mind_from_mind.db"
    TABLE = "memories"

    def __init__(self):
        super().__init__("memory_db", enabled=True)

    def search(self, query: str, max_results: int = 5) -> List[MemoryResult]:
        """Search memories by content using LIKE query."""
        results = []
        try:
            import sqlite3
            import json

            db_path = str(self.DB_PATH)
            if not os.path.exists(db_path):
                logger.warning(f"Memory DB not found: {db_path}")
                return results

            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            # Search content column, filter out archived
            cur.execute(
                f"SELECT id, content, kind, scope, thread_id, meta_json, text, tags, score "
                f"FROM {self.TABLE} "
                f"WHERE content LIKE ? AND archived != 1 "
                f"LIMIT ?",
                (f"%{query}%", max_results),
            )
            for row in cur.fetchall():
                meta = {}
                if row[5]:  # meta_json
                    try:
                        meta = json.loads(row[5])
                    except Exception:
                        pass
                results.append(
                    MemoryResult(
                        source=self.name,
                        id=row[0],  # id
                        content=row[1] if row[1] else (row[6] or ""),  # content or text
                        metadata={
                            "kind": row[2],
                            "scope": row[3],
                            "thread_id": row[4],
                            "meta": meta,
                            "tags": row[7],
                        },
                        score=float(row[8]) if row[8] else 0.5,
                    )
                )
            cur.close()
            conn.close()
        except Exception as e:
            logger.warning(f"Memory DB search failed: {e}")
        return results

    def health_check(self) -> HealthStatus:
        """Check if memory DB exists and is accessible."""
        import time
        import sqlite3

        start = time.time()
        try:
            db_path = str(self.DB_PATH)
            if not os.path.exists(db_path):
                return HealthStatus(
                    self.name,
                    False,
                    (time.time() - start) * 1000,
                    f"DB not found: {db_path}",
                )
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {self.TABLE}")
            cur.fetchone()
            cur.close()
            conn.close()
            return HealthStatus(self.name, True, (time.time() - start) * 1000)
        except Exception as e:
            return HealthStatus(self.name, False, 0, str(e))


# ---------------------------------------------------------------------------
# Connectors Export
# ---------------------------------------------------------------------------

CONNECTORS = {
    "athena": AthenaConnector,
    "memory_mcp": MemoryMCPConnector,
    "session": SessionConnector,
}

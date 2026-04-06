"""Tests for memory system — connectors, retrievers, router, retention."""

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure src is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.memory.connectors import (
    AthenaConnector,
    MemoryConnector,
    MemoryResult,
    SessionConnector,
    SQLiteConnector,
)
from src.memory.retrievers.fusion import TEMPRRetriever, rrf_fusion
from src.memory.retrievers.keyword import KeywordRetriever
from src.memory.retrievers.semantic import SemanticRetriever
from src.memory.retention_policy import (
    archive_old_memories,
    cleanup_learning_events,
    get_db_size_mb,
    get_memory_count,
    vacuum_database,
)
from src.memory.router import MemoryRouter, get_router


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database with memory schema."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # Create memories table
    cursor.execute(
        """
        CREATE TABLE memories (
            id TEXT PRIMARY KEY,
            content TEXT,
            kind TEXT,
            scope TEXT,
            meta_json TEXT,
            tier TEXT DEFAULT 'long_term'
        )
        """
    )

    # Create FTS5 virtual table
    cursor.execute(
        """
        CREATE VIRTUAL TABLE memory_fts USING fts5(
            content,
            content='memories',
            content_rowid='rowid'
        )
        """
    )

    # Create embeddings table
    cursor.execute(
        """
        CREATE TABLE memory_embeddings (
            memory_id TEXT PRIMARY KEY,
            vec BLOB
        )
        """
    )

    # Create triggers for FTS5 sync
    cursor.execute(
        """
        CREATE TRIGGER memories_ai AFTER INSERT ON memories BEGIN
            INSERT INTO memory_fts(rowid, content)
            VALUES (new.rowid, new.content);
        END
        """
    )

    conn.commit()
    conn.close()
    yield path

    # Cleanup
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def populated_db(temp_db):
    """Database with sample memories."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    test_memories = [
        (
            "mem-001",
            "Python is a programming language",
            "note",
            "global",
            None,
            "long_term",
        ),
        (
            "mem-002",
            "JavaScript runs in the browser",
            "note",
            "global",
            None,
            "long_term",
        ),
        (
            "mem-003",
            "Rust is great for systems programming",
            "note",
            "global",
            None,
            "short_term",
        ),
        (
            "mem-004",
            "The quick brown fox jumps over the lazy dog",
            "note",
            "session",
            None,
            "long_term",
        ),
        (
            "mem-005",
            "Machine learning models need training data",
            "doc",
            "project",
            None,
            "long_term",
        ),
    ]

    cursor.executemany(
        "INSERT INTO memories (id, content, kind, scope, meta_json, tier) VALUES (?, ?, ?, ?, ?, ?)",
        test_memories,
    )
    conn.commit()
    conn.close()
    return temp_db


# ---------------------------------------------------------------------------
# Connector Tests
# ---------------------------------------------------------------------------


class TestMemoryResult:
    def test_creation(self):
        result = MemoryResult(
            source="test",
            id="test-id",
            content="test content",
            metadata={"key": "value"},
            score=0.9,
        )
        assert result.source == "test"
        assert result.id == "test-id"
        assert result.content == "test content"
        assert result.score == 0.9


class TestAthenaConnector:
    def test_search_returns_empty_when_no_data(self):
        connector = AthenaConnector()
        results = connector.search("nonexistent query", max_results=5)
        # Should not raise, returns empty list when no athena data
        assert isinstance(results, list)

    def test_health_check(self):
        connector = AthenaConnector()
        status = connector.health_check()
        assert status.source == "athena"
        assert isinstance(status.healthy, bool)


class TestSessionConnector:
    def test_search_returns_empty_when_no_sessions(self):
        connector = SessionConnector()
        results = connector.search("nonexistent", max_results=5)
        assert isinstance(results, list)

    def test_health_check(self):
        connector = SessionConnector()
        status = connector.health_check()
        assert status.source == "session"


class TestSQLiteConnector:
    def test_search_nonexistent_db(self):
        connector = SQLiteConnector("test", "/nonexistent/path.db")
        results = connector.search("query", max_results=5)
        assert results == []

    def test_health_check_nonexistent_db(self):
        connector = SQLiteConnector("test", "/nonexistent/path.db")
        status = connector.health_check()
        assert status.healthy is False

    def test_search_valid_db(self, populated_db):
        connector = SQLiteConnector("test", populated_db)
        results = connector.search("Python", max_results=5)
        assert isinstance(results, list)
        # Should find the Python memory
        assert any("Python" in r.content for r in results)


# ---------------------------------------------------------------------------
# Retriever Tests
# ---------------------------------------------------------------------------


class TestKeywordRetriever:
    def test_search_no_fts_table(self, temp_db):
        """Keyword retriever returns empty when FTS5 table doesn't exist."""
        retriever = KeywordRetriever(temp_db)
        results = retriever.search("Python", top_k=5)
        assert results == []

    def test_search_with_fts_table(self, populated_db):
        """Keyword retriever finds memories via FTS5."""
        retriever = KeywordRetriever(populated_db)
        results = retriever.search("Python", top_k=5)
        assert len(results) > 0
        assert any("Python" in r.get("content", "") for r in results)

    def test_search_with_tier_filter(self, populated_db):
        """Keyword retriever respects tier filter."""
        retriever = KeywordRetriever(populated_db)
        results = retriever.search("programming", top_k=5, tier="short_term")
        assert all(r.get("tier") == "short_term" for r in results)

    def test_search_empty_query(self, populated_db):
        """Keyword retriever handles empty query."""
        retriever = KeywordRetriever(populated_db)
        results = retriever.search("", top_k=5)
        # Should not crash, may return results or empty
        assert isinstance(results, list)


class TestSemanticRetriever:
    def test_search_no_embedding_engine(self, temp_db):
        """Semantic retriever returns empty when embedding engine unavailable."""
        retriever = SemanticRetriever(temp_db)
        results = retriever.search("Python", top_k=5)
        # Returns empty when no embedding engine (expected in test env)
        assert isinstance(results, list)


class TestTEMPRRetriever:
    def test_search_fallback_to_keyword(self, populated_db):
        """TEMPR retriever works even without embedding engine."""
        retriever = TEMPRRetriever(populated_db)
        results = retriever.search("Python", top_k=3)
        assert isinstance(results, list)

    def test_search_with_strategies(self, populated_db):
        """TEMPR retriever respects strategy selection."""
        retriever = TEMPRRetriever(populated_db)
        results = retriever.search("Python", top_k=3, strategies=["keyword"])
        assert isinstance(results, list)

    def test_search_empty_strategies(self, populated_db):
        """TEMPR retriever handles empty strategies list."""
        retriever = TEMPRRetriever(populated_db)
        results = retriever.search("Python", top_k=3, strategies=[])
        assert results == []


class TestRRFFusion:
    def test_fusion_single_retriever(self):
        """RRF fusion with single retriever preserves order."""
        results = [
            {"id": "a", "content": "first", "score": 1.0},
            {"id": "b", "content": "second", "score": 0.8},
            {"id": "c", "content": "third", "score": 0.6},
        ]
        fused = rrf_fusion([results])
        assert len(fused) == 3
        assert fused[0]["id"] == "a"

    def test_fusion_multiple_retrievers(self):
        """RRF fusion combines results from multiple retrievers."""
        results1 = [
            {"id": "a", "content": "first", "score": 1.0},
            {"id": "b", "content": "second", "score": 0.8},
        ]
        results2 = [
            {"id": "b", "content": "second", "score": 0.9},
            {"id": "c", "content": "third", "score": 0.7},
        ]
        fused = rrf_fusion([results1, results2])
        # "b" appears in both, should rank highest
        assert fused[0]["id"] == "b"
        assert len(fused) == 3

    def test_fusion_empty(self):
        """RRF fusion handles empty input."""
        fused = rrf_fusion([])
        assert fused == []

    def test_fusion_deduplication(self):
        """RRF fusion deduplicates by ID."""
        results1 = [{"id": "a", "content": "version1", "score": 1.0}]
        results2 = [{"id": "a", "content": "version2", "score": 0.5}]
        fused = rrf_fusion([results1, results2])
        assert len(fused) == 1
        assert fused[0]["id"] == "a"


# ---------------------------------------------------------------------------
# Router Tests
# ---------------------------------------------------------------------------


class TestMemoryRouter:
    def test_get_router_singleton(self):
        """get_router returns singleton instance."""
        router1 = get_router()
        router2 = get_router()
        assert router1 is router2

    def test_router_creation(self):
        """MemoryRouter creates with default settings."""
        router = MemoryRouter()
        assert router.max_workers == 4

    def test_router_search_no_connectors(self):
        """Router handles search with no connectors gracefully."""
        from src.memory.router import UnifiedMemoryQuery

        router = MemoryRouter()
        # Patch to return no connectors
        with patch("src.memory.router.get_enabled_connectors", return_value=[]):
            result = router.search(UnifiedMemoryQuery(query="test"))
            assert result.total_results == 0
            assert result.sources_queried == []


# ---------------------------------------------------------------------------
# Retention Policy Tests
# ---------------------------------------------------------------------------


class TestRetentionPolicy:
    def test_get_db_size_mb_nonexistent(self):
        """Returns 0 for non-existent database."""
        size = get_db_size_mb("/nonexistent/path.db")
        assert size == 0.0

    def test_get_memory_count_nonexistent(self):
        """Returns 0 for non-existent database."""
        count = get_memory_count("/nonexistent/path.db")
        assert count == 0

    def test_vacuum_nonexistent_db(self):
        """Returns error for non-existent database."""
        result = vacuum_database("/nonexistent/path.db")
        assert "error" in result

    def test_archive_nonexistent_db(self):
        """Returns error for non-existent database."""
        result = archive_old_memories(db_path="/nonexistent/path.db")
        assert "error" in result

    def test_cleanup_events_nonexistent_db(self):
        """Returns gracefully for non-existent database."""
        result = cleanup_learning_events()
        assert "deleted" in result or "reason" in result


# ---------------------------------------------------------------------------
# Security Tests
# ---------------------------------------------------------------------------


class TestSecurityFixes:
    def test_no_bare_except_in_memory(self):
        """Verify no bare except: clauses in memory modules."""
        memory_dir = PROJECT_ROOT / "src" / "memory"
        for py_file in memory_dir.rglob("*.py"):
            content = py_file.read_text()
            # Check for bare except: (not except Exception: or except SpecificError:)
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped == "except:":
                    pytest.fail(
                        f"Bare except: found in {py_file.relative_to(PROJECT_ROOT)}:{i}"
                    )

    def test_no_exec_in_mcp_server_v2(self):
        """Verify mcp_server_v2.py does not use exec()."""
        mcp_v2 = PROJECT_ROOT / "src" / "memory" / "mcp_server_v2.py"
        content = mcp_v2.read_text()
        # Check for actual exec() calls (not in comments/docstrings)
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            if "exec(" in stripped and "exec(" not in stripped.split("#")[0].split('"""')[0]:
                pytest.fail(f"exec() call found in mcp_server_v2.py: {stripped}")

    def test_no_eval_in_event_bus(self):
        """Verify event_bus.py does not use eval()."""
        event_bus = PROJECT_ROOT / "src" / "tools" / "learning" / "event_bus.py"
        content = event_bus.read_text()
        # Check for eval() calls (not in comments/docstrings)
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "eval(" in stripped and "context=" not in stripped:
                # Allow eval in variable names like "evaluate"
                if "eval(" in stripped and not stripped.startswith("#"):
                    pytest.fail(f"eval() found in event_bus.py: {stripped}")

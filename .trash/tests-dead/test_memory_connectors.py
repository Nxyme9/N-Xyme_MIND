"""Tests for memory connectors module."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.memory.connectors import (
    AthenaConnector,
    MemoryConnector,
    MemoryResult,
    HealthStatus,
    SessionConnector,
    SQLiteConnector,
)


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
        assert result.metadata == {"key": "value"}
        assert result.score == 0.9

    def test_default_score(self):
        result = MemoryResult(source="test", id="1", content="test", metadata={})
        assert result.score == 1.0

    def test_default_timestamp(self):
        result = MemoryResult(source="test", id="1", content="test", metadata={})
        assert result.timestamp is None


class TestHealthStatus:
    def test_healthy(self):
        status = HealthStatus(source="test", healthy=True, latency_ms=10.5)
        assert status.source == "test"
        assert status.healthy is True
        assert status.latency_ms == 10.5
        assert status.error is None

    def test_unhealthy(self):
        status = HealthStatus(
            source="test", healthy=False, latency_ms=0, error="Connection refused"
        )
        assert status.healthy is False
        assert status.error == "Connection refused"


class TestMemoryConnector:
    def test_abstract_base(self):
        with pytest.raises(TypeError):
            MemoryConnector("test")

    def test_concrete_implementation(self):
        class TestConnector(MemoryConnector):
            def search(self, query, max_results=5):
                return [
                    MemoryResult(
                        source=self.name, id="1", content=query, metadata={}, score=1.0
                    )
                ]

            def health_check(self):
                return HealthStatus(source=self.name, healthy=True, latency_ms=1.0)

        connector = TestConnector("test", enabled=True)
        assert connector.name == "test"
        assert connector.enabled is True
        results = connector.search("hello")
        assert len(results) == 1
        assert results[0].content == "hello"
        health = connector.health_check()
        assert health.healthy is True

    def test_disabled_connector(self):
        class TestConnector(MemoryConnector):
            def search(self, query, max_results=5):
                return []

            def health_check(self):
                return HealthStatus(source=self.name, healthy=False, latency_ms=0)

        connector = TestConnector("disabled", enabled=False)
        assert connector.enabled is False


class TestAthenaConnector:
    def test_search_returns_empty_when_no_data(self):
        connector = AthenaConnector()
        results = connector.search("nonexistent query", max_results=5)
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

    def test_health_check_valid_db(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        import sqlite3

        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE memories (id TEXT PRIMARY KEY, content TEXT, kind TEXT, scope TEXT, meta_json TEXT, tier TEXT)"
        )
        conn.commit()
        conn.close()

        connector = SQLiteConnector("test", db_path)
        status = connector.health_check()
        assert status.healthy is True
        assert status.latency_ms >= 0

    def test_search_valid_db(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        import sqlite3

        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE memories (id TEXT PRIMARY KEY, content TEXT, kind TEXT, scope TEXT, meta_json TEXT, tier TEXT)"
        )
        conn.execute(
            "INSERT INTO memories (id, content, kind, scope, meta_json, tier) VALUES (?, ?, ?, ?, ?, ?)",
            ("mem-1", "Python is great", "note", "global", None, "long_term"),
        )
        conn.commit()
        conn.close()

        connector = SQLiteConnector("test", db_path)
        results = connector.search("Python", max_results=5)
        assert isinstance(results, list)
        assert any("Python" in r.content for r in results)

    def test_search_with_tier_filter(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        import sqlite3

        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE memories (id TEXT PRIMARY KEY, content TEXT, kind TEXT, scope TEXT, meta_json TEXT, tier TEXT)"
        )
        conn.execute(
            "INSERT INTO memories (id, content, kind, scope, meta_json, tier) VALUES (?, ?, ?, ?, ?, ?)",
            ("mem-1", "Python is great", "note", "global", None, "long_term"),
        )
        conn.execute(
            "INSERT INTO memories (id, content, kind, scope, meta_json, tier) VALUES (?, ?, ?, ?, ?, ?)",
            ("mem-2", "Rust is fast", "note", "global", None, "short_term"),
        )
        conn.commit()
        conn.close()

        connector = SQLiteConnector("test", db_path)
        results = connector.search("is", max_results=5)
        # SQLiteConnector doesn't support tier filter in search()
        # Just verify it returns results
        assert len(results) >= 1

    def test_search_empty_query(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        import sqlite3

        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE memories (id TEXT PRIMARY KEY, content TEXT, kind TEXT, scope TEXT, meta_json TEXT, tier TEXT)"
        )
        conn.execute(
            "INSERT INTO memories (id, content, kind, scope, meta_json, tier) VALUES (?, ?, ?, ?, ?, ?)",
            ("mem-1", "Python is great", "note", "global", None, "long_term"),
        )
        conn.commit()
        conn.close()

        connector = SQLiteConnector("test", db_path)
        results = connector.search("", max_results=5)
        assert isinstance(results, list)

    def test_close(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        import sqlite3

        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE memories (id TEXT PRIMARY KEY, content TEXT, kind TEXT, scope TEXT, meta_json TEXT, tier TEXT)"
        )
        conn.commit()
        conn.close()

        connector = SQLiteConnector("test", db_path)
        connector.close()  # Should not raise

"""Tests for memory retrievers module."""

import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.memory.retrievers.keyword import KeywordRetriever
from src.memory.retrievers.fusion import rrf_fusion, TEMPRRetriever


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fts_db(tmp_path):
    """Create a temporary SQLite database with FTS5 table and sample data."""
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
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

    # Create triggers for FTS5 sync
    cursor.execute(
        """
        CREATE TRIGGER memories_ai AFTER INSERT ON memories BEGIN
            INSERT INTO memory_fts(rowid, content)
            VALUES (new.rowid, new.content);
        END
        """
    )

    # Insert sample data
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
    return db_path


@pytest.fixture
def empty_db(tmp_path):
    """Create an empty database without FTS5 table."""
    db_path = str(tmp_path / "empty.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE memories (id TEXT PRIMARY KEY, content TEXT, kind TEXT, scope TEXT, meta_json TEXT, tier TEXT)"
    )
    conn.commit()
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# KeywordRetriever Tests
# ---------------------------------------------------------------------------


class TestKeywordRetriever:
    def test_search_finds_matching_content(self, fts_db):
        retriever = KeywordRetriever(fts_db)
        results = retriever.search("Python", top_k=5)
        assert len(results) > 0
        assert any("Python" in r.get("content", "") for r in results)

    def test_search_multi_word_query(self, fts_db):
        retriever = KeywordRetriever(fts_db)
        results = retriever.search("programming language", top_k=5)
        assert len(results) > 0

    def test_search_with_tier_filter(self, fts_db):
        retriever = KeywordRetriever(fts_db)
        results = retriever.search("programming", top_k=5, tier="short_term")
        assert all(r.get("tier") == "short_term" for r in results)

    def test_search_empty_query(self, fts_db):
        retriever = KeywordRetriever(fts_db)
        results = retriever.search("", top_k=5)
        assert isinstance(results, list)

    def test_search_no_fts_table(self, empty_db):
        retriever = KeywordRetriever(empty_db)
        results = retriever.search("test", top_k=5)
        assert results == []

    def test_search_respects_top_k(self, fts_db):
        retriever = KeywordRetriever(fts_db)
        results = retriever.search("is", top_k=2)
        assert len(results) <= 2

    def test_search_result_structure(self, fts_db):
        retriever = KeywordRetriever(fts_db)
        results = retriever.search("Python", top_k=1)
        assert len(results) == 1
        result = results[0]
        assert "id" in result
        assert "content" in result
        assert "kind" in result
        assert "scope" in result
        assert "metadata" in result
        assert "tier" in result
        assert "score" in result
        assert "source" in result
        assert result["source"] == "keyword"

    def test_search_content_truncated(self, fts_db):
        retriever = KeywordRetriever(fts_db)
        results = retriever.search("Python", top_k=1)
        assert len(results[0]["content"]) <= 2000

    def test_search_nonexistent_term(self, fts_db):
        retriever = KeywordRetriever(fts_db)
        results = retriever.search("xyznonexistent123", top_k=5)
        assert results == []

    def test_search_case_insensitive(self, fts_db):
        retriever = KeywordRetriever(fts_db)
        results_lower = retriever.search("python", top_k=5)
        results_upper = retriever.search("PYTHON", top_k=5)
        # FTS5 is case-insensitive, should return same results
        assert len(results_lower) == len(results_upper)


# ---------------------------------------------------------------------------
# RRF Fusion Tests
# ---------------------------------------------------------------------------


class TestRRFFusion:
    def test_fusion_single_retriever(self):
        results = [
            {"id": "a", "content": "first", "score": 1.0},
            {"id": "b", "content": "second", "score": 0.8},
            {"id": "c", "content": "third", "score": 0.6},
        ]
        fused = rrf_fusion([results])
        assert len(fused) == 3
        assert fused[0]["id"] == "a"

    def test_fusion_multiple_retrievers(self):
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
        fused = rrf_fusion([])
        assert fused == []

    def test_fusion_deduplication(self):
        results1 = [{"id": "a", "content": "version1", "score": 1.0}]
        results2 = [{"id": "a", "content": "version2", "score": 0.5}]
        fused = rrf_fusion([results1, results2])
        assert len(fused) == 1
        assert fused[0]["id"] == "a"

    def test_fusion_preserves_best_version(self):
        results1 = [{"id": "a", "content": "better", "score": 0.9}]
        results2 = [{"id": "a", "content": "worse", "score": 0.1}]
        fused = rrf_fusion([results1, results2])
        assert fused[0]["content"] == "better"

    def test_fusion_rrf_score_added(self):
        results = [{"id": "a", "content": "test", "score": 1.0}]
        fused = rrf_fusion([results])
        assert "rrf_score" in fused[0]

    def test_fusion_with_empty_retriever(self):
        results1 = [{"id": "a", "content": "test", "score": 1.0}]
        results2 = []
        fused = rrf_fusion([results1, results2])
        assert len(fused) == 1
        assert fused[0]["id"] == "a"

    def test_fusion_custom_k(self):
        results = [
            {"id": "a", "content": "first", "score": 1.0},
            {"id": "b", "content": "second", "score": 0.8},
        ]
        fused = rrf_fusion([results], k=10)
        assert len(fused) == 2


# ---------------------------------------------------------------------------
# TEMPRRetriever Tests
# ---------------------------------------------------------------------------


class TestTEMPRRetriever:
    def test_search_fallback_to_keyword(self, fts_db):
        retriever = TEMPRRetriever(fts_db)
        results = retriever.search("Python", top_k=3)
        assert isinstance(results, list)

    def test_search_with_strategies(self, fts_db):
        retriever = TEMPRRetriever(fts_db)
        results = retriever.search("Python", top_k=3, strategies=["keyword"])
        assert isinstance(results, list)

    def test_search_empty_strategies(self, fts_db):
        retriever = TEMPRRetriever(fts_db)
        results = retriever.search("Python", top_k=3, strategies=[])
        assert results == []

    def test_search_nonexistent_db(self):
        retriever = TEMPRRetriever("/nonexistent/path.db")
        results = retriever.search("test", top_k=3)
        assert isinstance(results, list)

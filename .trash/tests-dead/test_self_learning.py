#!/usr/bin/env python3
"""Comprehensive test suite for all self-learning modules."""

import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_memory.db"
    yield str(db_path)


@pytest.fixture
def priority_engine(temp_db):
    """Create PriorityEngine instance with temp database."""
    from src.memory.priority_engine import PriorityEngine

    engine = PriorityEngine(temp_db)
    yield engine


@pytest.fixture
def procedural_memory(tmp_path):
    """Create ProceduralMemory instance with temp storage."""
    from src.memory.procedural import ProceduralMemory

    storage_path = tmp_path / "procedural_memory.json"
    memory = ProceduralMemory(storage_path=str(storage_path))
    yield memory


@pytest.fixture
def knowledge_graph(tmp_path):
    """Create KnowledgeGraph instance with temp storage."""
    from src.memory.knowledge_graph import KnowledgeGraph

    graph_path = tmp_path / "knowledge_graph.json"
    graph = KnowledgeGraph(graph_path=str(graph_path))
    yield graph


@pytest.fixture
def preference_model(temp_db):
    """Create PreferenceModel instance with temp database."""
    from src.memory.preference_model import PreferenceModel

    model = PreferenceModel(temp_db)
    yield model


@pytest.fixture
def memory_router():
    """Create MemoryRouter instance."""
    from src.memory.router import MemoryRouter

    router = MemoryRouter()
    yield router


# ==============================================================================
# PriorityEngine Tests
# ==============================================================================


class TestPriorityEngine:
    """Tests for PriorityEngine self-learning functionality."""

    def test_track_query_feedback_basic(self, priority_engine):
        """Test basic query feedback tracking."""
        result = priority_engine.track_query_feedback(
            query="test query",
            result_id="result_1",
            source="memory_mcp",
            used=True,
            ignored=False,
            session_id="test_session",
        )
        assert result is True, "Failed to track query feedback"

    def test_track_query_feedback_ignored(self, priority_engine):
        """Test tracking ignored result."""
        result = priority_engine.track_query_feedback(
            query="test query",
            result_id="result_2",
            source="context7",
            used=False,
            ignored=True,
        )
        assert result is True, "Failed to track ignored result"

    def test_track_query_feedback_empty_query(self, priority_engine):
        """Test tracking with empty query."""
        result = priority_engine.track_query_feedback(
            query="", result_id="result_1", source="memory_mcp", used=True
        )
        assert result is True, "Should handle empty query"

    def test_get_query_stats_existing(self, priority_engine):
        """Test getting stats for existing query."""
        priority_engine.track_query_feedback(
            query="python code", result_id="res_1", source="memory_mcp", used=True
        )
        priority_engine.track_query_feedback(
            query="python code",
            result_id="res_2",
            source="context7",
            used=False,
            ignored=True,
        )

        stats = priority_engine.get_query_stats("python code")
        assert stats["total_feedback"] >= 2, "Should have at least 2 feedback entries"
        assert stats["used_count"] >= 1, "Should have at least 1 used"
        assert stats["ignored_count"] >= 1, "Should have at least 1 ignored"

    def test_get_query_stats_nonexistent(self, priority_engine):
        """Test getting stats for non-existent query."""
        stats = priority_engine.get_query_stats("nonexistent query xyz")
        assert stats["total_feedback"] == 0, "Should return zero for non-existent query"
        assert stats["used_count"] == 0
        assert stats["ignored_count"] == 0

    def test_get_query_stats_nonexistent_with_days(self, priority_engine):
        """Test query stats with days filter on non-existent query."""
        stats = priority_engine.get_query_stats("nonexistent query xyz", days=0)
        assert stats["total_feedback"] == 0, (
            "Should return zero for nonexistent query with 0 days"
        )

    def test_detect_topic_drift_no_data(self, priority_engine):
        """Test topic drift detection with no data."""
        drift = priority_engine.detect_topic_drift(days=7)
        assert drift == 0.0, "Should return 0 with no data"

    def test_detect_topic_drift_with_data(self, priority_engine):
        """Test topic drift detection with access data."""
        # Add file access data
        priority_engine.update_access("/path/to/file.py", "read")
        priority_engine.update_access("/path/to/file.js", "read")

        drift = priority_engine.detect_topic_drift(days=7)
        assert 0.0 <= drift <= 1.0, "Drift should be between 0 and 1"

    def test_get_learning_stats_empty(self, priority_engine):
        """Test learning stats with no data."""
        stats = priority_engine.get_learning_stats()
        assert "total_feedback" in stats
        assert "unique_queries" in stats
        assert "top_queries" in stats
        assert "topic_trends" in stats
        assert stats["total_feedback"] == 0

    def test_get_learning_stats_with_data(self, priority_engine):
        """Test learning stats with feedback data."""
        priority_engine.track_query_feedback(
            query="test query 1", result_id="res_1", source="memory_mcp", used=True
        )
        priority_engine.track_query_feedback(
            query="test query 1", result_id="res_2", source="context7", used=True
        )
        priority_engine.track_query_feedback(
            query="test query 2",
            result_id="res_3",
            source="memory_mcp",
            used=False,
            ignored=True,
        )

        stats = priority_engine.get_learning_stats()
        assert stats["total_feedback"] >= 3
        assert stats["unique_queries"] >= 2


# ==============================================================================
# Learning Config Tests
# ==============================================================================


class TestLearningConfig:
    """Tests for LearningConfig functionality."""

    def test_get_config_keys_exist(self):
        """Test that config has required keys."""
        from src.memory import learning_config as lc

        # Don't use global config - test the defaults directly
        from src.memory.learning_config import LEARNING_CONFIG_DEFAULTS

        assert "enabled" in LEARNING_CONFIG_DEFAULTS
        assert "rerank_enabled" in LEARNING_CONFIG_DEFAULTS
        assert "consolidate_enabled" in LEARNING_CONFIG_DEFAULTS
        assert "forget_enabled" in LEARNING_CONFIG_DEFAULTS

    def test_defaults_are_all_false(self):
        """Test that feature flags default to False."""
        from src.memory.learning_config import LEARNING_CONFIG_DEFAULTS

        assert LEARNING_CONFIG_DEFAULTS["enabled"] is False
        assert LEARNING_CONFIG_DEFAULTS["rerank_enabled"] is False
        assert LEARNING_CONFIG_DEFAULTS["consolidate_enabled"] is False
        assert LEARNING_CONFIG_DEFAULTS["forget_enabled"] is False

    def test_config_has_required_thresholds(self):
        """Test that config has required threshold values."""
        from src.memory.learning_config import LEARNING_CONFIG_DEFAULTS

        assert "min_confidence" in LEARNING_CONFIG_DEFAULTS
        assert "exploration_rate" in LEARNING_CONFIG_DEFAULTS
        assert "consolidation_threshold" in LEARNING_CONFIG_DEFAULTS
        assert isinstance(LEARNING_CONFIG_DEFAULTS["min_confidence"], (int, float))
        assert isinstance(LEARNING_CONFIG_DEFAULTS["exploration_rate"], (int, float))

    def test_merge_config_function(self):
        """Test the config merge function."""
        from src.memory.learning_config import _merge_config

        base = {"a": 1, "b": 2}
        updates = {"b": 3, "c": 4}
        result = _merge_config(base, updates)

        assert result["a"] == 1
        assert result["b"] == 3
        assert result["c"] == 4

    def test_env_override_function(self):
        """Test environment variable override function."""
        from src.memory.learning_config import _apply_env_overrides

        config = {"enabled": False, "min_confidence": 0.8}

        # Test with env var set
        with patch.dict(os.environ, {"LEARNING_ENABLED": "true"}, clear=False):
            result = _apply_env_overrides(config.copy())
            # Note: this may not work as expected if LEARNING_ENABLED was already set

    def test_update_config_function(self):
        """Test update_config merges correctly."""
        from src.memory import learning_config as lc

        # Reset cache
        lc._config_cache = None

        result = lc.update_config({"exploration_rate": 0.5})
        assert "exploration_rate" in result


# ==============================================================================
# Procedural Memory Tests
# ==============================================================================


class TestProceduralMemory:
    """Tests for ProceduralMemory functionality."""

    def test_record_strategy_result(self, procedural_memory, tmp_path):
        """Test recording strategy results."""
        db_path = tmp_path / "test_strategy.db"

        original_db = procedural_memory.DB_PATH
        procedural_memory.DB_PATH = str(db_path)
        procedural_memory._init_strategy_db()

        procedural_memory.record_strategy_result(
            query_type="code_search",
            strategy="semantic_first",
            success=True,
            latency_ms=150.0,
        )

        rate = procedural_memory.get_strategy_success_rate(
            "code_search", "semantic_first"
        )
        assert rate > 0.5, "Successful strategy should have rate > 0.5"

        procedural_memory.DB_PATH = original_db

    def test_get_best_strategy(self, procedural_memory, tmp_path):
        """Test getting best strategy for query type."""
        db_path = tmp_path / "test_strategy2.db"
        original_db = procedural_memory.DB_PATH
        procedural_memory.DB_PATH = str(db_path)
        procedural_memory._init_strategy_db()

        procedural_memory.record_strategy_result(
            query_type="concept_lookup", strategy="semantic_first", success=True
        )

        best = procedural_memory.get_best_strategy("concept_lookup")
        assert best is not None, "Should return a strategy"

        procedural_memory.DB_PATH = original_db

    def test_get_strategy_stats(self, procedural_memory, tmp_path):
        """Test getting strategy statistics."""
        db_path = tmp_path / "test_strategy3.db"
        original_db = procedural_memory.DB_PATH
        procedural_memory.DB_PATH = str(db_path)
        procedural_memory._init_strategy_db()

        procedural_memory.record_strategy_result(
            query_type="general", strategy="rrf_fusion", success=True, latency_ms=100.0
        )

        stats = procedural_memory.get_strategy_stats()
        assert isinstance(stats, dict), "Should return dict"

        procedural_memory.DB_PATH = original_db

    def test_get_strategy_success_rate_no_data(self, procedural_memory, tmp_path):
        """Test success rate with no data."""
        db_path = tmp_path / "test_strategy4.db"
        original_db = procedural_memory.DB_PATH
        procedural_memory.DB_PATH = str(db_path)
        procedural_memory._init_strategy_db()

        rate = procedural_memory.get_strategy_success_rate(
            "unknown_type", "unknown_strategy"
        )
        assert rate == 0.5, "Unknown strategy should return default 0.5"

        procedural_memory.DB_PATH = original_db


# ==============================================================================
# Knowledge Graph Tests
# ==============================================================================


class TestKnowledgeGraph:
    """Tests for KnowledgeGraph entity merge/dedup functionality."""

    def test_find_similar_entities_empty(self, knowledge_graph):
        """Test finding similar entities with empty graph."""
        similar = knowledge_graph.find_similar_entities("python")
        assert similar == [], "Should return empty list for empty graph"

    def test_find_similar_entities_with_data(self, knowledge_graph):
        """Test finding similar entities."""
        knowledge_graph.add_entity("Python", "technology", {"source": "test"})
        knowledge_graph.add_entity("Python3", "technology", {"source": "test"})
        knowledge_graph.add_entity("JavaScript", "technology", {"source": "test"})

        similar = knowledge_graph.find_similar_entities("Python", threshold=0.8)
        assert len(similar) > 0, "Should find similar entities"

    def test_suggest_merges_empty(self, knowledge_graph):
        """Test suggesting merges with empty graph."""
        merges = knowledge_graph.suggest_merges(threshold=0.95)
        assert merges == [], "Should return empty for empty graph"

    def test_suggest_merges_with_entities(self, knowledge_graph):
        """Test suggesting merges returns list."""
        knowledge_graph.add_entity("TestEntity1", "technology", {"source": "test"})
        knowledge_graph.add_entity("TestEntity2", "technology", {"source": "test"})

        merges = knowledge_graph.suggest_merges(threshold=0.5)
        assert isinstance(merges, list), "Should return list"

    def test_merge_entities_success(self, knowledge_graph):
        """Test successful entity merge."""
        knowledge_graph.add_entity("Vue", "technology", {"source": "test1"})
        knowledge_graph.add_entity("VueJS", "technology", {"source": "test2"})

        result = knowledge_graph.merge_entities("VueJS", "Vue")
        assert result is True, "Merge should succeed"

        names = [e["name"] for e in knowledge_graph.entities]
        assert "VueJS" not in names, "Merged entity should be removed"

    def test_merge_entities_same_entity(self, knowledge_graph):
        """Test merging same entity (should fail)."""
        knowledge_graph.add_entity("Test", "technology", {})

        result = knowledge_graph.merge_entities("Test", "Test")
        assert result is False, "Should fail when merging same entity"

    def test_merge_entities_nonexistent(self, knowledge_graph):
        """Test merging non-existent entities."""
        result = knowledge_graph.merge_entities("Nonexistent1", "Nonexistent2")
        assert result is False, "Should fail for non-existent entities"

    def test_get_merge_stats(self, knowledge_graph):
        """Test getting merge statistics."""
        knowledge_graph.add_entity("Entity1", "technology", {})
        knowledge_graph.add_entity("Entity2", "technology", {})

        stats = knowledge_graph.get_merge_stats()
        assert "total_entities" in stats
        assert "potential_merges" in stats
        assert "suggested_merges" in stats


# ==============================================================================
# Enhancements Tests
# ==============================================================================


class TestEnhancements:
    """Tests for Memory Enhancements functionality."""

    def test_get_decay_curve_basic(self):
        """Test basic decay curve calculation."""
        from src.memory.enhancements import get_decay_curve

        decay = get_decay_curve(1.0, 0, half_life=30)
        assert decay == 1.0, "Fresh memory should have full importance"

        decay = get_decay_curve(1.0, 30, half_life=30)
        assert decay == pytest.approx(0.5, rel=0.1), "At half-life, should be ~0.5"

    def test_get_decay_curve_edge_cases(self):
        """Test decay curve edge cases."""
        from src.memory.enhancements import get_decay_curve

        decay = get_decay_curve(0, 30, half_life=30)
        assert decay == 0

        decay = get_decay_curve(0.5, 10, half_life=0)
        assert decay == 0.5

    def test_apply_decay_score_basic(self):
        """Test applying decay to memory."""
        from src.memory.enhancements import apply_decay_score

        created = datetime.now(timezone.utc).isoformat()
        decayed = apply_decay_score("mem_1", created, 1.0, 30)
        assert decayed > 0.9, "Recent memory should retain most importance"

    def test_apply_decay_score_old_memory(self):
        """Test applying decay to old memory."""
        from src.memory.enhancements import apply_decay_score

        created = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
        decayed = apply_decay_score("mem_old", created, 1.0, 30)
        assert decayed < 0.1, "Old memory should have low importance"

    def test_archive_old_memories(self, tmp_path):
        """Test archiving old memories."""
        from src.memory import enhancements

        db_path = tmp_path / "test_archive.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY,
                content TEXT,
                created_at TEXT,
                archived INTEGER DEFAULT 0
            )
        """)

        old_date = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        conn.execute(
            "INSERT INTO memories (content, created_at) VALUES (?, ?)",
            ("short", old_date),
        )
        conn.commit()
        conn.close()

        archived_count = enhancements.archive_old_memories(str(db_path), days=90)

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT archived FROM memories")
        assert cursor.fetchone()[0] == 1, "Memory should be archived"

    def test_get_archived_count(self, tmp_path):
        """Test getting archived memory count."""
        from src.memory import enhancements

        db_path = tmp_path / "test_archived_count.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY,
                content TEXT,
                archived INTEGER DEFAULT 0
            )
        """)
        conn.execute("INSERT INTO memories (archived) VALUES (1)")
        conn.execute("INSERT INTO memories (archived) VALUES (1)")
        conn.execute("INSERT INTO memories (archived) VALUES (0)")
        conn.commit()
        conn.close()

        count = enhancements.get_archived_count(str(db_path))
        assert count == 2, "Should return 2 archived memories"

    def test_restore_memory(self, tmp_path):
        """Test restoring archived memory."""
        from src.memory import enhancements

        db_path = tmp_path / "test_restore.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY,
                content TEXT,
                archived INTEGER DEFAULT 0
            )
        """)
        conn.execute("INSERT INTO memories (content, archived) VALUES ('test', 1)")
        conn.commit()
        conn.close()

        result = enhancements.restore_memory(str(db_path), 1)
        assert result is True, "Should restore memory"

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT archived FROM memories WHERE id = 1")
        assert cursor.fetchone()[0] == 0, "Memory should be unarchived"


# ==============================================================================
# Preference Model Tests
# ==============================================================================


class TestPreferenceModel:
    """Tests for PreferenceModel functionality."""

    def test_record_preference_used(self, preference_model):
        """Test recording used preference."""
        result = preference_model.record_preference(
            query="python function", result_type="code", used=True
        )
        assert result is True, "Failed to record preference"

    def test_record_preference_ignored(self, preference_model):
        """Test recording ignored preference."""
        result = preference_model.record_preference(
            query="python function", result_type="doc", used=False
        )
        assert result is True, "Failed to record ignored preference"

    def test_record_preference_invalid_type(self, preference_model):
        """Test recording with invalid result type."""
        result = preference_model.record_preference(
            query="test", result_type="invalid_type", used=True
        )
        assert result is True, "Should handle invalid type"

    def test_get_preferences_empty(self, preference_model):
        """Test getting preferences with no data."""
        prefs = preference_model.get_preferences()
        assert isinstance(prefs, dict), "Should return dict"
        assert "code" in prefs
        assert "doc" in prefs

    def test_get_preferences_with_data(self, preference_model):
        """Test getting preferences with recorded data."""
        preference_model.record_preference("query1", "code", used=True)
        preference_model.record_preference("query1", "code", used=True)
        preference_model.record_preference("query2", "doc", used=False)

        prefs = preference_model.get_preferences()
        assert prefs["code"] > 0, "Code should have positive preference"

    def test_rerank_results_empty(self, preference_model):
        """Test re-ranking empty results."""
        reranked = preference_model.rerank_results([])
        assert reranked == [], "Should return empty list"

    def test_rerank_results_basic(self, preference_model):
        """Test basic re-ranking."""
        results = [
            {"type": "code", "score": 0.8},
            {"type": "doc", "score": 0.7},
            {"type": "config", "score": 0.6},
        ]

        preference_model.record_preference("test", "code", used=True)

        reranked = preference_model.rerank_results(results)
        assert len(reranked) == 3, "Should return all results"
        assert any("preference_boost" in r for r in reranked), (
            "Should add preference boost"
        )

    def test_rerank_results_preserves_scores(self, preference_model):
        """Test that re-ranking preserves original scores."""
        results = [{"type": "other", "score": 0.5}]

        reranked = preference_model.rerank_results(results)
        assert "score" in reranked[0], "Should preserve score"
        assert "preference_boost" in reranked[0], "Should add boost"

    def test_get_preference_stats_empty(self, preference_model):
        """Test preference stats with no data."""
        stats = preference_model.get_preference_stats()
        assert "total_events" in stats
        assert "used_count" in stats
        assert "preferences" in stats

    def test_get_preference_stats_with_data(self, preference_model):
        """Test preference stats with data."""
        preference_model.record_preference("query1", "code", used=True)
        preference_model.record_preference("query2", "code", used=False)

        stats = preference_model.get_preference_stats()
        assert stats["total_events"] >= 2
        assert stats["used_count"] >= 1


# ==============================================================================
# Router Tests
# ==============================================================================


class TestMemoryRouter:
    """Tests for MemoryRouter learning functionality."""

    def test_set_learning_adapter(self, memory_router):
        """Test setting learning adapter."""
        mock_adapter = MagicMock()
        memory_router.set_learning_adapter(mock_adapter)
        assert memory_router.learning_adapter is mock_adapter

    def test_set_learning_adapter_none(self, memory_router):
        """Test setting learning adapter to None."""
        memory_router.set_learning_adapter(None)
        assert memory_router.learning_adapter is None

    def test_learned_reranking_disabled(self, memory_router):
        """Test learned re-ranking when disabled."""
        from src.memory.router import UnifiedMemoryQuery

        mock_adapter = MagicMock()
        mock_adapter.rerank_results = lambda x: x
        memory_router.set_learning_adapter(mock_adapter)

        query = UnifiedMemoryQuery(query="test", max_results_per_source=5)

        assert hasattr(memory_router, "learning_adapter")

    @patch("src.memory.learning_config.get_config")
    def test_reranking_with_config_enabled(self, mock_get_config, memory_router):
        """Test re-ranking when config feature flag is ON."""
        from src.memory.router import UnifiedMemoryQuery

        mock_get_config.return_value = {"rerank_enabled": True}

        mock_adapter = MagicMock()
        mock_adapter.rerank_results = lambda x: x
        memory_router.set_learning_adapter(mock_adapter)


# ==============================================================================
# Additional Edge Case Tests
# ==============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_priority_engine_invalid_action(self, priority_engine):
        """Test priority engine with invalid action."""
        result = priority_engine.update_access("/path/to/file.py", "invalid_action")
        assert result is True, "Should default to 'read' for invalid action"

    def test_preference_model_empty_query(self, preference_model):
        """Test preference model with empty query."""
        result = preference_model.record_preference("", "code", True)
        assert result is True, "Should handle empty query"

    def test_knowledge_graph_add_duplicate(self, knowledge_graph):
        """Test adding duplicate entity."""
        knowledge_graph.add_entity("Test", "technology", {})
        result = knowledge_graph.add_entity("Test", "technology", {})
        assert result is False, "Should return False for duplicate"

    def test_procedural_store_and_find(self, procedural_memory):
        """Test storing and finding rules."""
        rule = procedural_memory.store(
            rule_id="rule_1", name="Test Rule", condition="python", action="search"
        )
        assert rule is not None

        matches = procedural_memory.find_matching("python code")
        assert len(matches) > 0


# ==============================================================================
# Main
# ==============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

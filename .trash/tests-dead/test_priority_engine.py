"""Unit tests for memory.priority_engine."""

import os
import pytest
import tempfile
from src.memory.priority_engine import (
    PriorityEngine,
    DEFAULT_WEIGHTS,
    FILE_TYPE_PRIORITY,
    VALID_ACTIONS,
)


class TestConstants:
    def test_default_weights_keys(self):
        assert "recency" in DEFAULT_WEIGHTS
        assert "frequency" in DEFAULT_WEIGHTS
        assert "content" in DEFAULT_WEIGHTS
        assert "type" in DEFAULT_WEIGHTS
        assert "project" in DEFAULT_WEIGHTS

    def test_default_weights_sum(self):
        total = sum(DEFAULT_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01

    def test_file_type_priority_keys(self):
        assert "code" in FILE_TYPE_PRIORITY
        assert "doc" in FILE_TYPE_PRIORITY
        assert "config" in FILE_TYPE_PRIORITY
        assert "data" in FILE_TYPE_PRIORITY

    def test_valid_actions(self):
        assert "read" in VALID_ACTIONS
        assert "edit" in VALID_ACTIONS
        assert "create" in VALID_ACTIONS
        assert "delete" in VALID_ACTIONS
        assert "index" in VALID_ACTIONS


class TestPriorityEngine:
    @pytest.fixture
    def temp_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.remove(db_path)

    def test_priority_engine_init(self, temp_db):
        engine = PriorityEngine(db_path=temp_db)
        assert engine.db_path == temp_db
        assert engine.weights == DEFAULT_WEIGHTS

    def test_weights_are_copied(self, temp_db):
        engine = PriorityEngine(db_path=temp_db)
        engine.weights["recency"] = 0.5
        assert DEFAULT_WEIGHTS["recency"] == 0.30

    def test_file_type_priority_values(self, temp_db):
        engine = PriorityEngine(db_path=temp_db)
        assert engine.weights["recency"] == 0.30
        assert engine.weights["frequency"] == 0.25
        assert engine.weights["content"] == 0.20

    def test_calculate_priority_basic(self, temp_db):
        """Test basic priority calculation."""
        engine = PriorityEngine(db_path=temp_db)
        metadata = {"path": "/test/file.py", "modified": 1000, "size": 1000}
        priority = engine.calculate_priority("/test/file.py", metadata)
        assert isinstance(priority, float)
        assert priority >= 0

    def test_get_top_priorities_empty(self, temp_db):
        """Test getting top priorities from empty DB."""
        engine = PriorityEngine(db_path=temp_db)
        results = engine.get_top_priorities(limit=5)
        assert isinstance(results, list)

    def test_update_access_read(self, temp_db):
        """Test updating access for read action."""
        engine = PriorityEngine(db_path=temp_db)
        engine.update_access("/test/file.py", action="read")
        # Should not raise

    def test_update_access_edit(self, temp_db):
        """Test updating access for edit action."""
        engine = PriorityEngine(db_path=temp_db)
        engine.update_access("/test/file.py", action="edit")
        # Should not raise

    def test_get_active_projects(self, temp_db):
        """Test getting active projects."""
        engine = PriorityEngine(db_path=temp_db)
        projects = engine.get_active_projects()
        assert isinstance(projects, list)

    def test_should_index_now(self, temp_db):
        """Test index decision."""
        engine = PriorityEngine(db_path=temp_db)
        should_index = engine.should_index_now("/test/file.py")
        assert isinstance(should_index, bool)

    def test_track_query_feedback(self, temp_db):
        """Test query feedback tracking."""
        engine = PriorityEngine(db_path=temp_db)
        engine.track_query_feedback(
            query="test query", result_id="result1", source="test", used=True
        )
        # Should not raise

    def test_detect_topic_drift(self, temp_db):
        """Test topic drift detection."""
        engine = PriorityEngine(db_path=temp_db)
        drift = engine.detect_topic_drift(days=7)
        assert isinstance(drift, (float, int))

    def test_get_learning_stats(self, temp_db):
        """Test learning stats retrieval."""
        engine = PriorityEngine(db_path=temp_db)
        stats = engine.get_learning_stats()
        assert isinstance(stats, dict)

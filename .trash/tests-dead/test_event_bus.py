#!/usr/bin/env python3
"""Unit tests for event_bus module."""

import pytest
import sys
import tempfile
import os
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.learning.event_bus import LearningEvent, LearningEventBus


class TestLearningEvent:
    """Tests for LearningEvent dataclass."""

    def test_creation(self):
        """Test creating a learning event."""
        event = LearningEvent(
            source="skill",
            task_id="task1",
            action="execute",
            success=True,
        )

        assert event.source == "skill"
        assert event.task_id == "task1"
        assert event.action == "execute"
        assert event.success is True

    def test_to_dict(self):
        """Test serialization to dictionary."""
        event = LearningEvent(
            source="search",
            task_id="task1",
            action="query",
            success=False,
            context={"query": "test"},
        )
        d = event.to_dict()

        assert isinstance(d, dict)
        assert d["source"] == "search"
        assert d["success"] == 0
        assert d["task_id"] == "task1"


class TestLearningEventBus:
    """Tests for LearningEventBus class."""

    @pytest.fixture
    def mock_db(self, tmp_path):
        """Create a mock database path."""
        db_dir = tmp_path / "memory"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir

    @pytest.fixture
    def event_bus(self, monkeypatch, tmp_path):
        """Create event bus with mocked database."""
        db_dir = tmp_path / "memory"
        db_dir.mkdir(parents=True, exist_ok=True)

        class MockLearningDB:
            def __init__(self):
                self._conn = None

            def get_connection(self, name):
                if self._conn is None:
                    db_path = db_dir / name
                    import sqlite3

                    self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
                    self._conn.row_factory = sqlite3.Row
                    # Create the events table
                    self._conn.execute(
                        "CREATE TABLE IF NOT EXISTS events (source TEXT, task_id TEXT, action TEXT, success INTEGER, context TEXT, timestamp TEXT)"
                    )
                    self._conn.commit()
                return self._conn

        mock_db_instance = MockLearningDB()

        def mock_get_db():
            return mock_db_instance

        monkeypatch.setattr("src.tools.learning.event_bus.get_db", mock_get_db)

        bus = LearningEventBus()
        bus._db = mock_db_instance
        return bus

    def test_publish_event(self, event_bus):
        """Test publishing an event."""
        event_bus._queue.clear()  # Clear any leftover events from other tests
        event = LearningEvent(
            source="test_source",
            task_id="task1",
            action="test_action",
            success=True,
        )
        event_bus.publish(event)

        assert len(event_bus._queue) == 1

    def test_subscribe(self, event_bus):
        """Test subscribing to event source."""
        received = []

        def handler(event):
            received.append(event)

        event_bus.subscribe("test_source", handler)

        event = LearningEvent(
            source="test_source", task_id="task1", action="test", success=True
        )
        event_bus.publish(event)

        assert len(received) == 1

    def test_multiple_subscribers(self, event_bus):
        """Test multiple subscribers for same source."""
        received1 = []
        received2 = []

        def handler1(event):
            received1.append(event)

        def handler2(event):
            received2.append(event)

        event_bus.subscribe("test_source", handler1)
        event_bus.subscribe("test_source", handler2)

        event = LearningEvent(
            source="test_source", task_id="task1", action="test", success=True
        )
        event_bus.publish(event)

        assert len(received1) == 1
        assert len(received2) == 1

    def test_flush(self, event_bus):
        """Test flushing events to database."""
        event_bus.publish(
            LearningEvent(source="s1", task_id="t1", action="a1", success=True)
        )
        event_bus.publish(
            LearningEvent(source="s2", task_id="t2", action="a2", success=False)
        )

        event_bus.flush()

        assert len(event_bus._queue) == 0

    def test_get_events(self, event_bus):
        """Test querying events by task_id."""
        event_bus.publish(
            LearningEvent(source="s1", task_id="task1", action="a1", success=True)
        )
        event_bus.publish(
            LearningEvent(source="s2", task_id="task1", action="a2", success=False)
        )
        event_bus.publish(
            LearningEvent(source="s3", task_id="task2", action="a3", success=True)
        )

        event_bus.flush()

        events = event_bus.get_events("task1")
        assert len(events) == 2

    def test_get_events_limit(self, event_bus):
        """Test limiting events in query."""
        for i in range(15):
            event_bus.publish(
                LearningEvent(source="s", task_id="task1", action=f"a{i}", success=True)
            )

        event_bus.flush()

        events = event_bus.get_events("task1", limit=5)
        assert len(events) == 5

    def test_flush_empty_queue(self, event_bus):
        """Test flushing empty queue does nothing."""
        event_bus.flush()
        assert len(event_bus._queue) == 0

    def test_singleton_pattern(self):
        """Test that LearningEventBus is a singleton."""
        bus1 = LearningEventBus()
        bus2 = LearningEventBus()
        assert bus1 is bus2

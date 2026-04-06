"""Event bus consumer — routes LearningEventBus events to all learning modules.

This is the central nervous system that connects event publishing to learning
consumers. It subscribes to the LearningEventBus and routes events to:
- PriorityEngine (for query feedback and priority adaptation)
- PreferenceModel (for result type preferences)
- SelfLearner (for outcome pattern extraction)
- SignalDetector (for anomaly detection)
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EventBusConsumer:
    """Central consumer that routes events to all learning modules."""

    _instance: Optional["EventBusConsumer"] = None

    def __init__(self):
        self._pe = None  # PriorityEngine
        self._pm = None  # PreferenceModel
        self._sl = None  # SelfLearner
        self._sd = None  # SignalDetector
        self._subscribed = False

    @classmethod
    def get_instance(cls) -> "EventBusConsumer":
        """Get or create the singleton consumer."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self):
        """Initialize all learning module references and subscribe to events."""
        if self._subscribed:
            return

        try:
            from src.memory.priority_engine import PriorityEngine
            from pathlib import Path

            db_path = str(
                Path(__file__).parent.parent.parent / "context/memory/file_registry.db"
            )
            self._pe = PriorityEngine(db_path)
        except Exception as e:
            logger.warning(f"Failed to initialize PriorityEngine: {e}")

        try:
            from src.memory.preference_model import PreferenceModel
            from pathlib import Path

            db_path = str(
                Path(__file__).parent.parent.parent / "context/memory/file_registry.db"
            )
            self._pm = PreferenceModel(db_path)
        except Exception as e:
            logger.warning(f"Failed to initialize PreferenceModel: {e}")

        try:
            from src.learning.self_learning import SelfLearner

            self._sl = SelfLearner()
        except Exception as e:
            logger.warning(f"Failed to initialize SelfLearner: {e}")

        # Subscribe to event bus
        try:
            from src.learning.event_bus import get_event_bus

            bus = get_event_bus()
            # Subscribe to all sources
            bus.subscribe("query", self._on_query)
            bus.subscribe("memory", self._on_memory)
            bus.subscribe("skill", self._on_skill)
            bus.subscribe("delegation", self._on_delegation)
            self._subscribed = True
            logger.info("EventBusConsumer subscribed to LearningEventBus")
        except Exception as e:
            logger.warning(f"Failed to subscribe to event bus: {e}")

    def _on_query(self, event):
        """Handle search/query events."""
        ctx = event.context
        query = event.task_id  # query is stored as task_id
        result_count = ctx.get("results", 0)

        # Record in PriorityEngine
        if self._pe:
            self._pe.track_query_feedback(
                query,
                "search_result",
                "memory_search",
                used=result_count > 0,
                ignored=result_count == 0,
            )

        # Record in SelfLearner
        if self._sl:
            self._sl.record_outcome(
                query, "search", event.success, latency_ms=0, context=ctx
            )

    def _on_memory(self, event):
        """Handle memory create/update/delete events."""
        if self._sl:
            self._sl.record_outcome(
                event.task_id, event.action, event.success, context=event.context
            )

    def _on_skill(self, event):
        """Handle skill outcome events."""
        # Record in PriorityEngine
        if self._pe:
            self._pe.track_query_feedback(
                event.task_id,
                event.action,
                "skill",
                used=event.success,
                ignored=not event.success,
            )

        # Record in SelfLearner
        if self._sl:
            self._sl.record_outcome(
                event.task_id, event.action, event.success, context=event.context
            )

    def _on_delegation(self, event):
        """Handle delegation events."""
        if self._sl:
            self._sl.record_outcome(
                event.task_id, event.action, event.success, context=event.context
            )

    def get_stats(self) -> dict:
        """Get consumer statistics."""
        return {
            "subscribed": self._subscribed,
            "priority_engine": self._pe is not None,
            "preference_model": self._pm is not None,
            "self_learner": self._sl is not None,
        }


# Module-level singleton
_consumer: Optional[EventBusConsumer] = None


def get_consumer() -> EventBusConsumer:
    """Get or create the event bus consumer."""
    global _consumer
    if _consumer is None:
        _consumer = EventBusConsumer()
        _consumer.initialize()
    return _consumer

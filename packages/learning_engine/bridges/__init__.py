"""Bridges — Connect external systems to the Memory system.

This package contains bridge modules that connect various logging and
tracking systems to the unified memory system for context injection.

Available Bridges:
    - outcome_to_memory_bridge: Connects OutcomeLogger to Memory system
"""

from packages.learning_engine.bridges.outcome_to_memory_bridge import (
    bridge_outcome_to_memory,
    bridge_sequences_to_memory,
    trigger_on_task_completion,
    bridge_latest_outcome,
    bridge_all_outcomes,
)

__all__ = [
    "bridge_outcome_to_memory",
    "bridge_sequences_to_memory",
    "trigger_on_task_completion",
    "bridge_latest_outcome",
    "bridge_all_outcomes",
]

#!/usr/bin/env python3
"""Backward compatibility re-export for task_wrapper.

This module re-exports all symbols from memory_bridge.py to maintain
backwards compatibility with existing code that imports from task_wrapper.

MEMORY_BRIDGE Architecture:
- Pre-read: Every task() call searches memory for relevant context BEFORE execution
- Post-write: Every task() completion writes outcome to memory AFTER execution
- Result: All sessions share context like a collective hivemind

Use: from packages.learning_engine.task_wrapper import TaskWrapper, wrap_task
OR:  from packages.learning_engine.memory_bridge import TaskWrapper, wrap_task
"""

# Re-export all public symbols from memory_bridge for backward compatibility
from packages.learning_engine.memory_bridge import (
    TaskWrapper,
    wrap_task,
    get_wrapper,
    DelegationOutcome,
    TaskContext,
)

__all__ = [
    "TaskWrapper",
    "wrap_task",
    "get_wrapper",
    "DelegationOutcome",
    "TaskContext",
]

# For backward compatibility, also expose at module level
globals().update(
    {
        "TaskWrapper": TaskWrapper,
        "wrap_task": wrap_task,
        "get_wrapper": get_wrapper,
        "DelegationOutcome": DelegationOutcome,
        "TaskContext": TaskContext,
    }
)

__all__ = [
    "TaskWrapper",
    "wrap_task",
    "get_wrapper",
    "DelegationOutcome",
    "TaskContext",
]

# For backward compatibility, also expose at module level
globals().update(
    {
        "TaskWrapper": TaskWrapper,
        "wrap_task": wrap_task,
        "get_wrapper": get_wrapper,
        "DelegationOutcome": DelegationOutcome,
        "TaskContext": TaskContext,
    }
)

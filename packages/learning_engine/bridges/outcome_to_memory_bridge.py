#!/usr/bin/env python3
"""Outcome→Memory Bridge — Connects OutcomeLogger to Memory system.

This bridge bridges the gap between the OutcomeLogger (which stores delegation
outcomes in SQLite) and the Memory system (which stores memories for context
injection).

Purpose:
    - Convert delegation outcomes from OutcomeLogger to memory entries
    - Enable PreAgentMemoryInjector to use actual task outcomes
    - Store tool sequences for composite action patterns

Usage:
    from packages.learning_engine.bridges.outcome_to_memory_bridge import (
        bridge_outcome_to_memory,
        bridge_sequences_to_memory,
        trigger_on_task_completion,
    )

    # Single outcome
    outcome = {"task_id": "task_001", "task_description": "add JWT auth",
              "agent": "hephaestus", "success": True, ...}
    bridge_outcome_to_memory(outcome)

    # Batch sequences
    sequences = [{"task_id": "task_001", "sequence": [...], "outcome": "success"}]
    bridge_sequences_to_memory(sequences)

    # Hook for OutcomeLogger callback
    trigger_on_task_completion()
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

# Default memory tier for storing outcomes
DEFAULT_MEMORY_KIND = "episodic"

# Default scope
DEFAULT_MEMORY_SCOPE = "global"

# ============================================================================
# Bridge Functions
# ============================================================================


def bridge_outcome_to_memory(outcome: Dict[str, Any]) -> bool:
    """Convert single outcome to memory entry and store in memory system.

    This function bridges the OutcomeLogger to the Memory system by converting
    a delegation outcome into a memory entry that can be used by the
    PreAgentMemoryInjector for context injection.

    Memory entry format:
        "Task: {task_description}, Tool: {agent}, Outcome: {success/failure}"

    Metadata:
        - success_weight: 1.0 if success, 0.0 if failure
        - recency: current timestamp
        - task_type: from outcome
        - task_id: from outcome

    Args:
        outcome: Dictionary containing outcome fields.
            Required fields: task_description, agent, success
            Optional fields: task_id, task_type, latency_ms, tokens_used

    Returns:
        True if successful, False otherwise.
    """
    try:
        # Extract required fields
        task_description = outcome.get("task_description", "")
        agent = outcome.get("agent", "unknown")
        success = outcome.get("success", False)

        if not task_description:
            logger.warning("Outcome missing task_description, skipping")
            return False

        # Build memory entry content
        outcome_str = "success" if success else "failure"
        content = f"Task: {task_description}, Tool: {agent}, Outcome: {outcome_str}"

        # Build metadata
        metadata = {
            "success_weight": 1.0 if success else 0.0,
            "recency": time.time(),
            "recency_timestamp": datetime.now().isoformat(),
            "task_type": outcome.get("task_type", "unknown"),
            "task_id": outcome.get("task_id", ""),
            "latency_ms": outcome.get("latency_ms", 0),
            "tokens_used": outcome.get("tokens_used", 0),
            "source": "outcome_logger",
            "entry_type": "delegation_outcome",
        }

        # Write to memory system
        success_write = _write_to_memory(
            content=content,
            kind=DEFAULT_MEMORY_KIND,
            scope=DEFAULT_MEMORY_SCOPE,
            metadata=metadata,
        )

        if success_write:
            logger.info(f"Bridged outcome to memory: {task_description[:50]}...")
        else:
            logger.warning(f"Failed to bridge outcome: {task_description[:50]}...")

        return success_write

    except Exception as e:
        logger.error(f"Error bridging outcome to memory: {e}")
        return False


def bridge_sequences_to_memory(sequences: List[Dict[str, Any]]) -> int:
    """Batch convert tool sequences to memory entries.

    This function converts tool sequences (from OutcomeLogger.log_sequence)
    into memory entries for composite action pattern analysis.

    Memory entry format:
        "Task: {task_description}, Sequence: {tool1} → {tool2} → ..., Outcome: {outcome}"

    Metadata:
        - success_weight: 1.0 for "success", 0.0 for "failed"
        - recency: current timestamp
        - task_type: "sequence"
        - tools: list of tools used

    Args:
        sequences: List of sequence dictionaries.
            Required fields: task_description, sequence, outcome
            Optional fields: task_id, duration_ms

    Returns:
        Number of successfully bridged sequences.
    """
    if not sequences:
        return 0

    bridged_count = 0

    for seq in sequences:
        try:
            # Extract required fields
            task_description = seq.get("task_description", "")
            sequence = seq.get("sequence", [])
            outcome = seq.get("outcome", "unknown")

            if not task_description or not sequence:
                continue

            # Extract tool names from sequence
            tools = []
            for item in sequence:
                if isinstance(item, dict):
                    tool = item.get("tool", item.get("name", "unknown"))
                    tools.append(tool)

            # Build memory entry content
            outcome_str = outcome
            tool_chain = " → ".join(tools) if tools else "empty"
            content = f"Task: {task_description}, Sequence: {tool_chain}, Outcome: {outcome_str}"

            # Build metadata
            metadata = {
                "success_weight": 1.0 if outcome == "success" else 0.0,
                "recency": time.time(),
                "recency_timestamp": datetime.now().isoformat(),
                "task_type": "sequence",
                "task_id": seq.get("task_id", ""),
                "duration_ms": seq.get("duration_ms", 0),
                "tools": tools,
                "source": "outcome_logger",
                "entry_type": "tool_sequence",
            }

            # Write to memory system
            success_write = _write_to_memory(
                content=content,
                kind=DEFAULT_MEMORY_KIND,
                scope=DEFAULT_MEMORY_SCOPE,
                metadata=metadata,
            )

            if success_write:
                bridged_count += 1

        except Exception as e:
            logger.error(f"Error bridging sequence to memory: {e}")
            continue

    if bridged_count > 0:
        logger.info(f"Bridged {bridged_count} sequences to memory")

    return bridged_count


def trigger_on_task_completion() -> None:
    """Hook that runs after OutcomeLogger logs.

    This function is designed to be called as a callback after the
    OutcomeLogger records an outcome. It bridges the most recent outcome
    to memory for real-time learning.

    Usage:
        # In OutcomeLogger or calling code:
        outcome_logger.log(outcome)
        trigger_on_task_completion()  # Bridge to memory

    Note:
        This requires the OutcomeLogger to have recorded an outcome first.
        The function reads the most recent outcome from the OutcomeLogger's
        database and bridges it.
    """
    try:
        # Import OutcomeLogger
        from packages.learning_engine.outcome_logger import OutcomeLogger

        logger = OutcomeLogger()

        # Get most recent outcome
        outcomes = logger.get_outcomes(limit=1)

        if not outcomes:
            logger.debug("No outcomes to bridge")
            return

        # Get most recent outcome
        latest = outcomes[0]

        # Convert to dictionary format
        outcome_dict = {
            "task_id": latest.task_id,
            "task_description": latest.task_description,
            "task_type": latest.task_type,
            "agent": latest.agent,
            "success": latest.success,
            "latency_ms": latest.latency_ms,
            "tokens_used": latest.tokens_used,
            "timestamp": latest.timestamp,
        }

        # Bridge to memory
        bridge_outcome_to_memory(outcome_dict)

        # Also check for sequences
        sequences = logger.get_sequences(limit=5)
        if sequences:
            seq_dicts = [
                {
                    "task_id": s.task_id,
                    "task_description": s.task_description,
                    "sequence": s.sequence,
                    "outcome": s.outcome,
                    "duration_ms": s.duration_ms,
                }
                for s in sequences
            ]
            bridge_sequences_to_memory(seq_dicts)

        logger.debug("Task completion hook executed")

    except ImportError as e:
        logger.warning(f"OutcomeLogger not available: {e}")
    except Exception as e:
        logger.error(f"Error in task completion hook: {e}")


# ============================================================================
# Internal Helpers
# ============================================================================


def _write_to_memory(
    content: str,
    kind: str = DEFAULT_MEMORY_KIND,
    scope: str = DEFAULT_MEMORY_SCOPE,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Write a memory entry to the unified memory system.

    Args:
        content: Memory content text.
        kind: Memory tier (episodic, semantic, etc.).
        scope: Memory scope (global, session, etc.).
        metadata: Optional metadata dictionary.

    Returns:
        True if successful, False otherwise.
    """
    try:
        # Try to use the unified-memory MCP if available
        from packages.brain_mcp.namespaces.memory import memory_write

        result = memory_write(
            content=content,
            kind=kind,
            scope=scope,
            metadata=metadata,
        )

        if isinstance(result, dict):
            if result.get("error"):
                logger.warning(f"Memory write error: {result.get('error')}")
                return False
            return True

        return True

    except ImportError:
        logger.warning("Memory MCP not available, trying fallback")
        return _write_to_memory_fallback(content, kind, scope, metadata)
    except Exception as e:
        logger.error(f"Memory write failed: {e}")
        return _write_to_memory_fallback(content, kind, scope, metadata)


def _write_to_memory_fallback(
    content: str,
    kind: str = DEFAULT_MEMORY_KIND,
    scope: str = DEFAULT_MEMORY_SCOPE,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Fallback memory write using direct SQLite.

    This provides a fallback when the MCP is not available by writing
    directly to the memory SQLite database.

    Args:
        content: Memory content text.
        kind: Memory tier (episodic, semantic, etc.).
        scope: Memory scope (global, session, etc.).
        metadata: Optional metadata dictionary.

    Returns:
        True if successful, False otherwise.
    """
    import json
    import sqlite3

    db_path = Path(".sisyphus/memory.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        conn = sqlite3.connect(str(db_path), check_same_thread=False)

        # Create table if not exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                kind TEXT NOT NULL,
                scope TEXT NOT NULL,
                metadata_json TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind)")

        # Insert memory
        conn.execute(
            """INSERT INTO memories (content, kind, scope, metadata_json, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                content,
                kind,
                scope,
                json.dumps(metadata or {}),
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

        logger.debug(f"Fallback memory write: {content[:50]}...")
        return True

    except Exception as e:
        logger.error(f"Fallback memory write failed: {e}")
        return False


# ============================================================================
# Convenience Functions
# ============================================================================


def bridge_latest_outcome() -> bool:
    """Bridge the most recent outcome from OutcomeLogger.

    Convenience function that reads the most recent outcome from
    the database and bridges it to memory.

    Returns:
        True if successful, False otherwise.
    """
    try:
        from packages.learning_engine.outcome_logger import OutcomeLogger

        logger = OutcomeLogger()
        outcomes = logger.get_outcomes(limit=1)

        if not outcomes:
            logger.debug("No outcomes to bridge")
            return False

        latest = outcomes[0]
        outcome_dict = {
            "task_id": latest.task_id,
            "task_description": latest.task_description,
            "task_type": latest.task_type,
            "agent": latest.agent,
            "success": latest.success,
            "latency_ms": latest.latency_ms,
            "tokens_used": latest.tokens_used,
            "timestamp": latest.timestamp,
        }

        return bridge_outcome_to_memory(outcome_dict)

    except Exception as e:
        logger.error(f"Error bridging latest outcome: {e}")
        return False


def bridge_all_outcomes(limit: int = 100) -> int:
    """Bridge all outcomes from OutcomeLogger to memory.

    Batch process all outcomes that haven't been bridged yet.

    Args:
        limit: Maximum number of outcomes to bridge.

    Returns:
        Number of successfully bridged outcomes.
    """
    try:
        from packages.learning_engine.outcome_logger import OutcomeLogger

        logger = OutcomeLogger()
        outcomes = logger.get_outcomes(limit=limit)

        bridged_count = 0
        for outcome in outcomes:
            outcome_dict = {
                "task_id": outcome.task_id,
                "task_description": outcome.task_description,
                "task_type": outcome.task_type,
                "agent": outcome.agent,
                "success": outcome.success,
                "latency_ms": outcome.latency_ms,
                "tokens_used": outcome.tokens_used,
                "timestamp": outcome.timestamp,
            }

            if bridge_outcome_to_memory(outcome_dict):
                bridged_count += 1

        logger.info(f"Bridged {bridged_count} outcomes to memory")
        return bridged_count

    except Exception as e:
        logger.error(f"Error bridging outcomes: {e}")
        return 0


# ============================================================================
# CLI (for testing)
# ============================================================================


if __name__ == "__main__":

    # Test bridging
    print("Testing Outcome→Memory Bridge...")

    # Test single outcome
    test_outcome = {
        "task_id": "test_001",
        "task_description": "test outcome bridging",
        "task_type": "implementation",
        "agent": "hephaestus",
        "success": True,
        "latency_ms": 1500,
        "tokens_used": 12000,
    }

    result = bridge_outcome_to_memory(test_outcome)
    print(f"Single outcome bridge: {'SUCCESS' if result else 'FAILED'}")

    # Test sequence
    test_sequence = {
        "task_id": "test_002",
        "task_description": "test sequence bridging",
        "sequence": [
            {"tool": "grep", "args": {"pattern": "import"}},
            {"tool": "read", "args": {"filePath": "main.py"}},
            {"tool": "edit", "args": {"oldString": "foo", "newString": "bar"}},
        ],
        "outcome": "success",
        "duration_ms": 2000,
    }

    result = bridge_sequences_to_memory([test_sequence])
    print(f"Sequence bridge: {'SUCCESS' if result > 0 else 'FAILED'}")

    print("Bridge test complete")

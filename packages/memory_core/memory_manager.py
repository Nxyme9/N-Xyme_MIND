#!/usr/bin/env python3
"""MemoryManager — Central coordinator for memory operations with auto-triggered cognitive processes."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, List, Optional
from datetime import datetime
from pathlib import Path

from .cognitive.forgetting import (
    AdaptiveDecay,
    record_access as forgetting_record_access,
)
from .cognitive.reconsolidation import MemoryReconsolidation
from .cognitive.trust import TrustAwareRetrieval
from .cognitive.priority import PriorityEngine
from .stores.relational_store import RelationalStore

logger = logging.getLogger(__name__)


@dataclass
class MemoryOperationResult:
    """Result of a memory operation."""

    success: bool
    memory_id: str
    action: str  # "created", "accessed", "updated", "deleted", "archived"
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryManager:
    """Central coordinator that auto-triggers cognitive processes on memory operations.

    This class orchestrates forgetting, reconsolidation, trust, and priority engines
    to provide adaptive memory management with automatic cognitive triggers.
    """

    def __init__(self, db_path: str = None):
        """Initialize MemoryManager with all cognitive engines.

        Args:
            db_path: Path to the memory SQLite database. Defaults to context/memory/mind_from_mind.db.
        """
        # Resolve relative paths against project root
        if db_path is None:
            project_root = Path(__file__).resolve().parents[2]
            db_path = str(project_root / "context" / "memory" / "mind_from_mind.db")
        elif not Path(db_path).is_absolute():
            project_root = Path(__file__).resolve().parents[2]
            db_path = str(project_root / db_path)

        self.db_path = db_path
        self._lock = threading.Lock()
        self.store = RelationalStore(db_path)

        # Initialize cognitive engines
        self.forgetting = AdaptiveDecay(Path(db_path))
        self.reconsolidation = MemoryReconsolidation(Path(db_path))
        self.trust = TrustAwareRetrieval(Path(db_path))
        self.priority = PriorityEngine(db_path)

        logger.info(f"MemoryManager initialized with db_path: {db_path}")

    def on_memory_access(self, memory_id: str) -> MemoryOperationResult:
        """Called when memory is retrieved - check decay, trigger tier changes.

        Args:
            memory_id: The ID of the accessed memory.

        Returns:
            MemoryOperationResult with operation outcome.
        """
        with self._lock:
            try:
                # Record access in forgetting engine
                self.forgetting.record_access(memory_id)

                # Update access frequency for priority (use file_path style)
                # Memory ID as path for consistency
                self.priority.update_access(memory_id, action="read")

                # Initialize or update trust on access (boost trust slightly)
                existing_trust = self.trust.get_trust_score(memory_id)
                if existing_trust is None:
                    self.trust.initialize_trust(memory_id)
                # Access doesn't automatically boost trust - that's for verification

                # Check decay score for potential archiving
                decay_result = self.forgetting.apply_decay_actions()

                return MemoryOperationResult(
                    success=True,
                    memory_id=memory_id,
                    action="accessed",
                    metadata={"decay_actions": decay_result},
                )
            except Exception as e:
                logger.error(f"Error in on_memory_access({memory_id}): {e}")
                return MemoryOperationResult(
                    success=False,
                    memory_id=memory_id,
                    action="accessed",
                    metadata={"error": str(e)},
                )

    def on_memory_write(
        self, memory_id: str, content: str, kind: str = "episodic"
    ) -> MemoryOperationResult:
        """Called when memory is stored - check for conflicts, set initial priority.

        Args:
            memory_id: The ID of the memory being written.
            content: The content of the memory.
            kind: The type of memory (episodic, semantic, etc.).

        Returns:
            MemoryOperationResult with operation outcome.
        """
        with self._lock:
            try:
                # Get existing memories for conflict detection
                existing = self.store.search("", limit=100)
                existing_memories = [
                    (m.id, m.content, m.metadata.get("created_at", ""))
                    for m in existing
                    if m.id != memory_id
                ]

                # Check for conflicts with existing memories
                conflicts = self.reconsolidation.detect_conflicts(
                    memory_id, content, existing_memories
                )

                if conflicts:
                    for conflict in conflicts:
                        self.reconsolidation.resolve_conflict(conflict, "keep_new")

                # Set initial priority
                self.priority.update_access(memory_id, action="create")

                # Set initial trust (new memories start neutral)
                self.trust.initialize_trust(memory_id)

                return MemoryOperationResult(
                    success=True,
                    memory_id=memory_id,
                    action="created",
                    metadata={
                        "conflicts_detected": len(conflicts),
                        "conflict_details": [
                            {
                                "id": c.id,
                                "type": c.conflict_type,
                                "score": c.similarity_score,
                            }
                            for c in conflicts
                        ],
                    },
                )
            except Exception as e:
                logger.error(f"Error in on_memory_write({memory_id}): {e}")
                return MemoryOperationResult(
                    success=False,
                    memory_id=memory_id,
                    action="created",
                    metadata={"error": str(e)},
                )

    def on_memory_update(
        self, memory_id: str, new_content: str
    ) -> MemoryOperationResult:
        """Called when memory is updated - check for conflicts with old content.

        Args:
            memory_id: The ID of the memory being updated.
            new_content: The new content for the memory.

        Returns:
            MemoryOperationResult with operation outcome.
        """
        with self._lock:
            try:
                # Get existing memories for conflict detection
                existing = self.store.search("", limit=100)
                existing_memories = [
                    (m.id, m.content, m.metadata.get("created_at", ""))
                    for m in existing
                    if m.id != memory_id
                ]

                # Check for conflicts
                conflicts = self.reconsolidation.detect_conflicts(
                    memory_id, new_content, existing_memories
                )

                if conflicts:
                    for conflict in conflicts:
                        self.reconsolidation.resolve_conflict(conflict, "keep_new")

                # Reset trust (needs re-verification after update)
                existing_trust = self.trust.get_trust_score(memory_id)
                if existing_trust:
                    # Decrement verification count to signal needs re-verification
                    existing_trust.verification_count = 0
                    self.trust._save_trust_score(existing_trust)
                else:
                    self.trust.initialize_trust(memory_id)

                return MemoryOperationResult(
                    success=True,
                    memory_id=memory_id,
                    action="updated",
                    metadata={
                        "conflicts_detected": len(conflicts),
                        "trust_reset": True,
                    },
                )
            except Exception as e:
                logger.error(f"Error in on_memory_update({memory_id}): {e}")
                return MemoryOperationResult(
                    success=False,
                    memory_id=memory_id,
                    action="updated",
                    metadata={"error": str(e)},
                )

    def on_memory_delete(self, memory_id: str) -> MemoryOperationResult:
        """Called when memory is deleted - clean up cognitive tracking.

        Args:
            memory_id: The ID of the memory being deleted.

        Returns:
            MemoryOperationResult with operation outcome.
        """
        with self._lock:
            try:
                # Delete from store
                deleted = self.store.delete(memory_id)

                return MemoryOperationResult(
                    success=deleted, memory_id=memory_id, action="deleted", metadata={}
                )
            except Exception as e:
                logger.error(f"Error in on_memory_delete({memory_id}): {e}")
                return MemoryOperationResult(
                    success=False,
                    memory_id=memory_id,
                    action="deleted",
                    metadata={"error": str(e)},
                )

    def run_consolidation_cycle(self) -> dict[str, Any]:
        """Run a full consolidation cycle - forgetting, trust decay, priority recalculation.

        This should be called periodically (e.g., hourly or on session start/end)
        to maintain memory hygiene.

        Returns:
            Dict with results from each cognitive process.
        """
        results = {
            "forgetting": {},
            "trust_decay": {},
            "priority_recalc": {},
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # Run forgetting/decay cycle
            results["forgetting"] = self.forgetting.apply_decay_actions()
        except Exception as e:
            logger.error(f"Error in forgetting cycle: {e}")
            results["forgetting_error"] = str(e)

        try:
            # Run trust decay for unverified memories
            decayed = self.trust.decay_unverified(days=1)
            results["trust_decay"] = {
                "memories_decayed": len(decayed),
                "decayed_ids": list(decayed.keys()),
            }
        except Exception as e:
            logger.error(f"Error in trust decay: {e}")
            results["trust_decay_error"] = str(e)

        try:
            # Get priority statistics (recalculate_all not available, get stats instead)
            results["priority_recalc"] = self.priority.get_learning_stats()
        except Exception as e:
            logger.error(f"Error in priority recalc: {e}")
            results["priority_recalc_error"] = str(e)

        return results

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive memory management statistics.

        Returns:
            Dict with stats from all cognitive engines.
        """
        return {
            "store": self.store.stats(),
            "forgetting": self.forgetting.get_decay_stats(),
            "reconsolidation": self.reconsolidation.get_stats(),
            "trust": self.trust.get_stats(),
            "priority": self.priority.get_learning_stats(),
        }


# Module-level convenience function
def get_memory_manager(
    db_path: str = "context/memory/mind_from_mind.db",
) -> MemoryManager:
    """Get a MemoryManager instance.

    Args:
        db_path: Path to the memory database.

    Returns:
        MemoryManager instance.
    """
    return MemoryManager(db_path)


__all__ = ["MemoryManager", "MemoryOperationResult", "get_memory_manager"]

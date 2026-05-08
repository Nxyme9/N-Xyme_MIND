#!/usr/bin/env python3
"""MemoryManager — Central coordinator for memory operations with auto-triggered cognitive processes."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, List, Optional
from datetime import datetime
from pathlib import Path

from .cognitive.forgetting import (
    AdaptiveDecay,
)
from .cognitive.reconsolidation import MemoryReconsolidation
from .cognitive.trust import TrustAwareRetrieval
from .cognitive.priority import PriorityEngine
from .conflict_resolver import MemoryConflictResolver, ConflictResolution
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

        # Initialize AGM conflict resolver (Phase 1.2)
        self.conflict_resolver = MemoryConflictResolver()

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

    def _generate_version_hash(self, content: str) -> str:
        """Generate SHA256 hash for memory content.

        Args:
            content: Memory content to hash

        Returns:
            Hex digest of SHA256 hash
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def on_memory_write(
        self,
        memory_id: str,
        content: str,
        kind: str = "episodic",
        scope: str = "global",
        tags: Optional[list[str]] = None,
    ) -> MemoryOperationResult:
        """Called when memory is stored - check for conflicts, set initial priority, create version.

        Args:
            memory_id: The ID of the memory being written.
            content: The content of the memory.
            kind: The type of memory (episodic, semantic, etc.).
            scope: The scope of memory (global, session, project).
            tags: Optional list of tags for the memory.

        Returns:
            MemoryOperationResult with operation outcome.
        """
        with self._lock:
            try:
                # Build metadata with tags
                metadata = {"tags": tags} if tags else {}

                # Get existing memories for conflict detection
                existing = self.store.search("", limit=100)
                existing_memories = [
                    (m.id, m.content, m.metadata.get("created_at", ""))
                    for m in existing
                    if m.id != memory_id
                ]

                # Check for conflicts with existing memories using reconsolidation
                conflicts = self.reconsolidation.detect_conflicts(
                    memory_id, content, existing_memories
                )

                if conflicts:
                    for conflict in conflicts:
                        self.reconsolidation.resolve_conflict(conflict, "keep_new")

                # ALSO check using AGM resolver (Phase 1.2)
                existing_memories_2tuple = [
                    (m.id, m.content) for m in existing if m.id != memory_id
                ]
                agm_conflicts = self.conflict_resolver.check_conflict(
                    memory_id, content, existing_memories_2tuple
                )

                if agm_conflicts:
                    # Apply AGM revision to resolve
                    logger.info(
                        f"AGM conflict resolution for {memory_id}: {agm_conflicts}"
                    )
                    resolution = self.conflict_resolver.resolve_conflict(
                        memory_id, content, existing_memories_2tuple, "revise"
                    )
                    # Update metadata with resolution info
                    metadata["agm_resolution"] = {
                        "action": resolution.action,
                        "method": resolution.resolution_method,
                        "conflicts": resolution.conflicts_detected,
                    }

                # Get current branch
                active_branch = self.store.get_active_branch()
                branch_id = active_branch["id"] if active_branch else "main"

                # Get parent version (latest version for this memory)
                latest_version = self.store.get_latest_version(memory_id, branch_id)
                parent_version = (
                    latest_version["version_hash"] if latest_version else None
                )

                # Generate version hash
                version_hash = self._generate_version_hash(content)

                # Mark previous version as not latest
                if latest_version:
                    conn = self.store._conn
                    conn.execute(
                        "UPDATE memories SET is_latest = 0 WHERE id = ? AND branch_id = ?",
                        (memory_id, branch_id),
                    )
                    conn.commit()

                # Build memory record and store (with version info)
                from .stores.relational_store import MemoryRecord

                record = MemoryRecord(
                    id=memory_id,
                    content=content,
                    kind=kind,
                    scope=scope,
                    tier="short_term",
                    metadata=metadata,
                )
                # Store with version info - manually insert to include version columns
                conn = self.store._conn
                conn.execute(
                    """INSERT OR REPLACE INTO memories 
                       (id, content, kind, scope, tier, meta_json, created_at, updated_at, 
                        version_hash, parent_version, branch_id, is_latest) 
                       VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), ?, ?, ?, 1)""",
                    (
                        record.id,
                        record.content,
                        record.kind,
                        record.scope,
                        record.tier,
                        json.dumps(record.metadata),
                        version_hash,
                        parent_version,
                        branch_id,
                    ),
                )
                conn.commit()

                # Store version in memory_versions table
                self.store.store_version(
                    memory_id=memory_id,
                    version_hash=version_hash,
                    content=content,
                    parent_version=parent_version,
                    branch_id=branch_id,
                )

                # Set initial priority
                self.priority.update_access(memory_id, action="create")

                # Set initial trust (new memories start neutral)
                self.trust.initialize_trust(memory_id)

                return MemoryOperationResult(
                    success=True,
                    memory_id=memory_id,
                    action="created",
                    metadata={
                        "version_hash": version_hash,
                        "parent_version": parent_version,
                        "branch_id": branch_id,
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

    # ===== Version Control Methods =====

    def get_version_history(self, memory_id: str) -> List[dict[str, Any]]:
        """Get version history for a memory.

        Args:
            memory_id: The memory ID

        Returns:
            List of version records with version_hash, timestamp, branch
        """
        with self._lock:
            return self.store.get_version_history(memory_id)

    def rollback_to_version(
        self, memory_id: str, version_hash: str
    ) -> MemoryOperationResult:
        """Rollback memory to a specific version.

        Args:
            memory_id: The memory ID
            version_hash: The version hash to rollback to

        Returns:
            MemoryOperationResult with operation outcome
        """
        with self._lock:
            try:
                # Get the version to rollback to
                version = self.store.get_version_by_hash(memory_id, version_hash)
                if not version:
                    return MemoryOperationResult(
                        success=False,
                        memory_id=memory_id,
                        action="rollback",
                        metadata={"error": f"Version {version_hash} not found"},
                    )

                # Get current branch
                active_branch = self.store.get_active_branch()
                branch_id = active_branch["id"] if active_branch else "main"

                # Get current version as parent
                current_version = self.store.get_latest_version(memory_id, branch_id)
                parent_version = (
                    current_version["version_hash"] if current_version else None
                )

                # Generate new version hash for the rolled-back content
                new_version_hash = self._generate_version_hash(version["content"])

                # Mark previous as not latest
                conn = self.store._conn
                conn.execute(
                    "UPDATE memories SET is_latest = 0 WHERE id = ? AND branch_id = ?",
                    (memory_id, branch_id),
                )

                # Update memory with rolled-back content
                conn.execute(
                    """UPDATE memories SET 
                       content = ?, version_hash = ?, parent_version = ?, 
                       updated_at = datetime('now'), is_latest = 1 
                       WHERE id = ? AND branch_id = ?""",
                    (
                        version["content"],
                        new_version_hash,
                        parent_version,
                        memory_id,
                        branch_id,
                    ),
                )
                conn.commit()

                # Store new version record
                self.store.store_version(
                    memory_id=memory_id,
                    version_hash=new_version_hash,
                    content=version["content"],
                    parent_version=parent_version,
                    branch_id=branch_id,
                )

                return MemoryOperationResult(
                    success=True,
                    memory_id=memory_id,
                    action="rollback",
                    metadata={
                        "version_hash": new_version_hash,
                        "rolled_back_to": version_hash,
                    },
                )
            except Exception as e:
                logger.error(
                    f"Error in rollback_to_version({memory_id}, {version_hash}): {e}"
                )
                return MemoryOperationResult(
                    success=False,
                    memory_id=memory_id,
                    action="rollback",
                    metadata={"error": str(e)},
                )

    def create_branch(
        self, branch_name: str, parent_branch_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Create a new memory branch.

        Args:
            branch_name: Name for the new branch
            parent_branch_id: Parent branch ID (for branching from existing branch)

        Returns:
            Dict with branch info (id, name, created_at)
        """
        with self._lock:
            # If no parent specified, get current active branch
            if parent_branch_id is None:
                active_branch = self.store.get_active_branch()
                if active_branch:
                    parent_branch_id = active_branch["id"]

            branch_id = self.store.create_branch(branch_name, parent_branch_id)
            branch = self.store.get_branch(branch_id)
            return branch

    def get_current_branch(self) -> Optional[dict[str, Any]]:
        """Get the currently active branch.

        Returns:
            Branch record or None
        """
        with self._lock:
            return self.store.get_active_branch()

    def list_branches(self) -> List[dict[str, Any]]:
        """List all memory branches.

        Returns:
            List of branch records
        """
        with self._lock:
            return self.store.list_branches()

    def switch_branch(self, branch_id: str) -> bool:
        """Switch to a different branch.

        Args:
            branch_id: Branch ID to switch to

        Returns:
            True if successful
        """
        with self._lock:
            return self.store.set_active_branch(branch_id)

    def switch_branch_by_name(self, branch_name: str) -> bool:
        """Switch to a branch by name.

        Args:
            branch_name: Branch name to switch to

        Returns:
            True if successful
        """
        with self._lock:
            branch = self.store.get_branch_by_name(branch_name)
            if branch:
                return self.store.set_active_branch(branch["id"])
            return False

    def merge_branch(
        self, source_branch_id: str, target_branch_id: str = "main"
    ) -> dict[str, Any]:
        """Merge a branch into another branch.

        Args:
            source_branch_id: Source branch ID to merge from
            target_branch_id: Target branch ID to merge into

        Returns:
            Dict with merge results
        """
        with self._lock:
            try:
                # Get all memories from source branch
                conn = self.store._conn
                cursor = conn.execute(
                    """SELECT id, content, kind, scope, tier, meta_json 
                       FROM memories WHERE branch_id = ? AND is_latest = 1""",
                    (source_branch_id,),
                )
                source_memories = cursor.fetchall()

                merged_count = 0
                for row in source_memories:
                    memory_id = row["id"]

                    # Get parent version in target branch
                    target_latest = self.store.get_latest_version(
                        memory_id, target_branch_id
                    )
                    parent_version = (
                        target_latest["version_hash"] if target_latest else None
                    )

                    # Generate version hash
                    version_hash = self._generate_version_hash(row["content"])

                    # Mark previous as not latest in target
                    conn.execute(
                        "UPDATE memories SET is_latest = 0 WHERE id = ? AND branch_id = ?",
                        (memory_id, target_branch_id),
                    )

                    # Insert into target branch
                    conn.execute(
                        """INSERT OR REPLACE INTO memories 
                           (id, content, kind, scope, tier, meta_json, created_at, updated_at,
                            version_hash, parent_version, branch_id, is_latest)
                           VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), ?, ?, ?, 1)""",
                        (
                            memory_id,
                            row["content"],
                            row["kind"],
                            row["scope"],
                            row["tier"],
                            row["meta_json"],
                            version_hash,
                            parent_version,
                            target_branch_id,
                        ),
                    )

                    # Store version
                    self.store.store_version(
                        memory_id=memory_id,
                        version_hash=version_hash,
                        content=row["content"],
                        parent_version=parent_version,
                        branch_id=target_branch_id,
                    )
                    merged_count += 1

                conn.commit()

                return {
                    "success": True,
                    "source_branch": source_branch_id,
                    "target_branch": target_branch_id,
                    "memories_merged": merged_count,
                }
            except Exception as e:
                logger.error(
                    f"Error in merge_branch({source_branch_id}, {target_branch_id}): {e}"
                )
                return {
                    "success": False,
                    "error": str(e),
                }

    def get_memory_versions(self, memory_id: str) -> List[dict[str, Any]]:
        """Get simplified version history (alias for get_version_history).

        Args:
            memory_id: The memory ID

        Returns:
            List of version info (version_hash, created_at, branch_id)
        """
        with self._lock:
            versions = self.store.get_version_history(memory_id)
            return [
                {
                    "version_hash": v["version_hash"],
                    "created_at": v["created_at"],
                    "branch_id": v["branch_id"],
                }
                for v in versions
            ]

    def resolve_conflict(
        self,
        memory_id: str,
        new_content: str,
        strategy: str = "revise",
    ) -> ConflictResolution:
        """Manually resolve conflict for a memory using AGM revision.

        Args:
            memory_id: ID of memory with conflict
            new_content: New content to resolve with
            strategy: Resolution strategy ("revise", "contract", "expand")

        Returns:
            ConflictResolution with resolved beliefs.
        """
        with self._lock:
            try:
                # Get existing memories for comparison
                existing = self.store.search("", limit=100)
                existing_memories = [
                    (m.id, m.content) for m in existing if m.id != memory_id
                ]

                # Run conflict resolution
                result = self.conflict_resolver.resolve_conflict(
                    memory_id, new_content, existing_memories, strategy
                )

                logger.info(
                    f"Resolved conflict for {memory_id}: {result.action} "
                    f"(method: {result.resolution_method})"
                )
                return result

            except Exception as e:
                logger.error(f"Error in resolve_conflict({memory_id}): {e}")
                raise


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

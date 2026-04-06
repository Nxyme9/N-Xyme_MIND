"""Memory Reconsolidation — HiMem-inspired conflict-aware memory revision.

Based on HiMem (Hierarchical Memory with Self-Evolution, arXiv:2601.06377).

Key innovation: When a retrieved memory conflicts with new information,
the system automatically revises it rather than just adding a new memory.
This keeps the memory store clean and consistent.

Architecture:
1. Conflict Detection: Semantic similarity + temporal ordering
2. Conflict Resolution: Determine which memory is more current/accurate
3. Revision: Update the older memory with new information
4. Logging: Track all revisions for auditability
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Conflict detection thresholds
CONFLICT_SIMILARITY_THRESHOLD = 0.6  # Minimum semantic similarity to consider conflict
CONFLICT_TEMPORAL_WINDOW_DAYS = 30  # Only consider conflicts within this window


@dataclass
class ConflictRecord:
    """Record of a detected memory conflict."""

    id: str
    memory_id_old: str
    memory_id_new: str
    conflict_type: str  # contradiction, update, extension
    similarity_score: float
    resolution: str  # keep_old, keep_new, merge, flag
    resolved_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RevisionRecord:
    """Record of a memory revision."""

    id: str
    memory_id: str
    old_content: str
    new_content: str
    reason: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryReconsolidator:
    """HiMem-style memory reconsolidation engine."""

    def __init__(self, db_path: Path | None = None):
        """Initialize reconsolidator.

        Args:
            db_path: Path to the memory database.
        """
        if db_path is None:
            project_root = Path(__file__).resolve().parents[2]
            db_path = project_root / "context" / "memory" / "mind_from_mind.db"
        self.db_path = db_path
        self.conflicts: list[ConflictRecord] = []
        self.revisions: list[RevisionRecord] = []
        self._ensure_tables()
        self._load_records()

    def _ensure_tables(self) -> None:
        """Create reconsolidation tables."""
        if not self.db_path.exists():
            return

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_conflicts (
                    id TEXT PRIMARY KEY,
                    memory_id_old TEXT NOT NULL,
                    memory_id_new TEXT NOT NULL,
                    conflict_type TEXT NOT NULL,
                    similarity_score REAL NOT NULL,
                    resolution TEXT NOT NULL,
                    resolved_at TEXT,
                    metadata TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_revisions (
                    id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    old_content TEXT NOT NULL,
                    new_content TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def detect_conflicts(
        self,
        new_memory_id: str,
        new_content: str,
        existing_memories: list[tuple[str, str, str]],  # (id, content, timestamp)
    ) -> list[ConflictRecord]:
        """Detect conflicts between new memory and existing memories.

        Args:
            new_memory_id: ID of the new memory.
            new_content: Content of the new memory.
            existing_memories: List of (id, content, timestamp) tuples.

        Returns:
            List of detected conflicts.
        """
        import uuid

        conflicts = []
        new_words = set(new_content.lower().split())

        for mem_id, mem_content, mem_timestamp in existing_memories:
            if mem_id == new_memory_id:
                continue

            # Check temporal window
            try:
                mem_time = datetime.fromisoformat(mem_timestamp.replace("Z", "+00:00"))
                days_old = (datetime.now(timezone.utc) - mem_time).days
                if days_old > CONFLICT_TEMPORAL_WINDOW_DAYS:
                    continue
            except (ValueError, TypeError):
                pass

            # Check semantic similarity (keyword overlap)
            mem_words = set(mem_content.lower().split())
            if not mem_words or not new_words:
                continue

            similarity = len(new_words & mem_words) / max(
                len(new_words), len(mem_words)
            )

            if similarity >= CONFLICT_SIMILARITY_THRESHOLD:
                # Determine conflict type
                conflict_type = self._classify_conflict(new_content, mem_content)

                conflict = ConflictRecord(
                    id=str(uuid.uuid4())[:8],
                    memory_id_old=mem_id,
                    memory_id_new=new_memory_id,
                    conflict_type=conflict_type,
                    similarity_score=round(similarity, 4),
                    resolution="pending",
                )
                conflicts.append(conflict)
                self.conflicts.append(conflict)
                self._save_conflict(conflict)

        return conflicts

    def resolve_conflict(
        self,
        conflict: ConflictRecord,
        resolution: str,
        merged_content: str | None = None,
    ) -> RevisionRecord | None:
        """Resolve a detected conflict.

        Args:
            conflict: The conflict to resolve.
            resolution: Resolution strategy (keep_old, keep_new, merge, flag).
            merged_content: Content for merge resolution.

        Returns:
            RevisionRecord if a revision was made, None otherwise.
        """
        import uuid

        conflict.resolution = resolution
        conflict.resolved_at = datetime.now(timezone.utc).isoformat()
        self._save_conflict(conflict)

        if resolution == "keep_new":
            # Revision will be made by the caller when updating the memory
            return None
        elif resolution == "merge" and merged_content:
            revision = RevisionRecord(
                id=str(uuid.uuid4())[:8],
                memory_id=conflict.memory_id_old,
                old_content="",  # Would be loaded from DB
                new_content=merged_content,
                reason=f"Merged with {conflict.memory_id_new} (similarity: {conflict.similarity_score})",
                metadata={"conflict_id": conflict.id},
            )
            self.revisions.append(revision)
            self._save_revision(revision)
            return revision
        elif resolution == "flag":
            logger.warning(
                f"Flagged conflict between {conflict.memory_id_old} and {conflict.memory_id_new}"
            )
            return None

        return None

    def reconsolidate(
        self,
        memory_id: str,
        new_content: str,
        reason: str = "New information supersedes old",
    ) -> RevisionRecord:
        """Reconsolidate a memory with new information.

        This is the core reconsolidation operation — when new information
        conflicts with existing memory, we revise the existing memory.

        Args:
            memory_id: ID of the memory to revise.
            new_content: New content to replace old content.
            reason: Reason for the revision.

        Returns:
            RevisionRecord documenting the change.
        """
        import uuid

        # In production, would load old_content from DB
        revision = RevisionRecord(
            id=str(uuid.uuid4())[:8],
            memory_id=memory_id,
            old_content="[old content]",  # Would be loaded from DB
            new_content=new_content,
            reason=reason,
            metadata={"reconsolidation": True},
        )
        self.revisions.append(revision)
        self._save_revision(revision)

        logger.info(f"Reconsolidated memory {memory_id}: {reason}")
        return revision

    def _classify_conflict(self, new_content: str, old_content: str) -> str:
        """Classify the type of conflict.

        Args:
            new_content: New memory content.
            old_content: Existing memory content.

        Returns:
            Conflict type: contradiction, update, or extension.
        """
        new_lower = new_content.lower()
        old_lower = old_content.lower()

        # Check for contradiction (negation patterns)
        contradiction_patterns = [
            "not",
            "no longer",
            "changed",
            "wrong",
            "incorrect",
            "instead",
        ]
        if any(p in new_lower for p in contradiction_patterns):
            return "contradiction"

        # Check for update (similar content with new details)
        new_words = set(new_lower.split())
        old_words = set(old_lower.split())
        overlap = len(new_words & old_words) / max(len(new_words), len(old_words))

        if overlap > 0.7:
            return "update"
        else:
            return "extension"

    def _save_conflict(self, conflict: ConflictRecord) -> None:
        """Save conflict to database."""
        if not self.db_path.exists():
            return

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_conflicts
                (id, memory_id_old, memory_id_new, conflict_type, similarity_score, resolution, resolved_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conflict.id,
                    conflict.memory_id_old,
                    conflict.memory_id_new,
                    conflict.conflict_type,
                    conflict.similarity_score,
                    conflict.resolution,
                    conflict.resolved_at,
                    json.dumps(conflict.metadata),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _save_revision(self, revision: RevisionRecord) -> None:
        """Save revision to database."""
        if not self.db_path.exists():
            return

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_revisions
                (id, memory_id, old_content, new_content, reason, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    revision.id,
                    revision.memory_id,
                    revision.old_content,
                    revision.new_content,
                    revision.reason,
                    revision.timestamp,
                    json.dumps(revision.metadata),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _load_records(self) -> None:
        """Load conflicts and revisions from database."""
        if not self.db_path.exists():
            return

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            # Load conflicts
            cursor = conn.execute("SELECT * FROM memory_conflicts")
            for row in cursor.fetchall():
                conflict = ConflictRecord(
                    id=row["id"],
                    memory_id_old=row["memory_id_old"],
                    memory_id_new=row["memory_id_new"],
                    conflict_type=row["conflict_type"],
                    similarity_score=row["similarity_score"],
                    resolution=row["resolution"],
                    resolved_at=row["resolved_at"] or "",
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
                self.conflicts.append(conflict)

            # Load revisions
            cursor = conn.execute("SELECT * FROM memory_revisions")
            for row in cursor.fetchall():
                revision = RevisionRecord(
                    id=row["id"],
                    memory_id=row["memory_id"],
                    old_content=row["old_content"],
                    new_content=row["new_content"],
                    reason=row["reason"],
                    timestamp=row["timestamp"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
                self.revisions.append(revision)
        finally:
            conn.close()

    def get_stats(self) -> dict[str, Any]:
        """Get reconsolidation statistics."""
        conflict_types: dict[str, int] = {}
        for c in self.conflicts:
            conflict_types[c.conflict_type] = conflict_types.get(c.conflict_type, 0) + 1

        resolutions: dict[str, int] = {}
        for c in self.conflicts:
            resolutions[c.resolution] = resolutions.get(c.resolution, 0) + 1

        return {
            "total_conflicts": len(self.conflicts),
            "total_revisions": len(self.revisions),
            "conflict_types": conflict_types,
            "resolutions": resolutions,
        }


# Global singleton
_reconsolidator = MemoryReconsolidator()


def detect_conflicts(
    new_memory_id: str,
    new_content: str,
    existing_memories: list[tuple[str, str, str]],
) -> list[ConflictRecord]:
    """Convenience function to detect conflicts."""
    return _reconsolidator.detect_conflicts(
        new_memory_id, new_content, existing_memories
    )


def reconsolidate(
    memory_id: str,
    new_content: str,
    reason: str = "New information supersedes old",
) -> RevisionRecord:
    """Convenience function to reconsolidate a memory."""
    return _reconsolidator.reconsolidate(memory_id, new_content, reason)


def get_reconsolidation_stats() -> dict[str, Any]:
    """Convenience function to get stats."""
    return _reconsolidator.get_stats()

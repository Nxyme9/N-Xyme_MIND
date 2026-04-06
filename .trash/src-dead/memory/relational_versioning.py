"""Relational Versioning — Supermemory-inspired relationship types.

Based on Supermemory research (supermemory.ai/research/).

Key innovation: Explicit relationship types that handle knowledge evolution:
- `updates` — handles contradictions ("My favorite color is now Green")
- `extends` — supplements without contradiction (adding job title)
- `derives` — second-order logic inferred from combining memories

Plus dual-layer temporal grounding:
- `documentDate` — when the conversation took place
- `eventDate` — when the event described actually occurred
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


class RelationshipType:
    """Explicit relationship types for knowledge evolution."""

    UPDATES = "updates"  # Contradicts/replaces older memory
    EXTENDS = "extends"  # Supplements without contradiction
    DERIVES = "derives"  # Second-order inference from combining memories
    REFERENCES = "references"  # Points to related memory
    CONTRADICTS = "contradicts"  # Explicit contradiction (flagged)


@dataclass
class VersionedRelationship:
    """A relationship with versioning and temporal grounding."""

    source_id: str
    target_id: str
    relation_type: str
    weight: float = 0.5
    document_date: str = ""  # When the conversation took place
    event_date: str = ""  # When the event described actually occurred
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def is_update(self) -> bool:
        return self.relation_type == RelationshipType.UPDATES

    @property
    def is_extension(self) -> bool:
        return self.relation_type == RelationshipType.EXTENDS

    @property
    def is_derived(self) -> bool:
        return self.relation_type == RelationshipType.DERIVES


class RelationalVersioning:
    """Supermemory-style relational versioning system."""

    def __init__(self, db_path: Path | None = None):
        """Initialize relational versioning.

        Args:
            db_path: Path to the database.
        """
        if db_path is None:
            project_root = Path(__file__).resolve().parents[2]
            db_path = project_root / "context" / "memory" / "mind_from_mind.db"
        self.db_path = db_path
        self.relationships: list[VersionedRelationship] = []
        self._ensure_tables()
        self._load_relationships()

    def _ensure_tables(self) -> None:
        """Create versioning tables."""
        if not self.db_path.exists():
            return

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS versioned_relationships (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    weight REAL DEFAULT 0.5,
                    document_date TEXT,
                    event_date TEXT,
                    metadata TEXT,
                    created_at TEXT,
                    PRIMARY KEY (source_id, target_id, relation_type)
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        weight: float = 0.5,
        document_date: str = "",
        event_date: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> VersionedRelationship:
        """Add a versioned relationship.

        Args:
            source_id: Source memory ID.
            target_id: Target memory ID.
            relation_type: Type of relationship (updates, extends, derives, etc.)
            weight: Relationship strength (0-1).
            document_date: When the conversation took place.
            event_date: When the event described actually occurred.
            metadata: Additional metadata.

        Returns:
            Created VersionedRelationship.
        """
        rel = VersionedRelationship(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight,
            document_date=document_date,
            event_date=event_date,
            metadata=metadata or {},
        )
        self.relationships.append(rel)
        self._save_relationship(rel)
        return rel

    def get_updates(self, memory_id: str) -> list[VersionedRelationship]:
        """Get all updates for a memory (newer versions)."""
        return [
            r for r in self.relationships if r.target_id == memory_id and r.is_update
        ]

    def get_extensions(self, memory_id: str) -> list[VersionedRelationship]:
        """Get all extensions for a memory (supplementary info)."""
        return [
            r for r in self.relationships if r.source_id == memory_id and r.is_extension
        ]

    def get_derived(self, memory_id: str) -> list[VersionedRelationship]:
        """Get all derived relationships for a memory."""
        return [
            r for r in self.relationships if r.source_id == memory_id and r.is_derived
        ]

    def get_current_version(self, memory_id: str) -> str:
        """Get the current (most recent) version of a memory.

        Follows the update chain to find the latest version.

        Args:
            memory_id: Starting memory ID.

        Returns:
            ID of the current version.
        """
        current = memory_id
        visited = set()

        while current not in visited:
            visited.add(current)
            updates = self.get_updates(current)
            if not updates:
                break
            # Follow the most recent update
            updates.sort(key=lambda r: r.created_at, reverse=True)
            current = updates[0].source_id

        return current

    def get_memory_timeline(self, memory_id: str) -> list[VersionedRelationship]:
        """Get the complete timeline of a memory (all versions).

        Args:
            memory_id: Memory ID.

        Returns:
            List of relationships in chronological order.
        """
        timeline = []
        current = memory_id
        visited = set()

        while current not in visited:
            visited.add(current)
            updates = self.get_updates(current)
            timeline.extend(updates)
            if not updates:
                break
            updates.sort(key=lambda r: r.created_at, reverse=True)
            current = updates[0].source_id

        timeline.sort(key=lambda r: r.created_at)
        return timeline

    def detect_contradictions(
        self,
        memory_id: str,
        content: str,
    ) -> list[VersionedRelationship]:
        """Detect contradictions with existing memories.

        Args:
            memory_id: New memory ID.
            content: New memory content.

        Returns:
            List of contradictory relationships.
        """
        contradictions = []
        new_words = set(content.lower().split())

        for rel in self.relationships:
            if rel.relation_type == RelationshipType.CONTRADICTS:
                if rel.source_id == memory_id or rel.target_id == memory_id:
                    contradictions.append(rel)

        return contradictions

    def _save_relationship(self, rel: VersionedRelationship) -> None:
        """Save relationship to database."""
        if not self.db_path.exists():
            return

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO versioned_relationships
                (source_id, target_id, relation_type, weight, document_date, event_date, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rel.source_id,
                    rel.target_id,
                    rel.relation_type,
                    rel.weight,
                    rel.document_date,
                    rel.event_date,
                    json.dumps(rel.metadata),
                    rel.created_at,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _load_relationships(self) -> None:
        """Load relationships from database."""
        if not self.db_path.exists():
            return

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute("SELECT * FROM versioned_relationships")
            for row in cursor.fetchall():
                rel = VersionedRelationship(
                    source_id=row["source_id"],
                    target_id=row["target_id"],
                    relation_type=row["relation_type"],
                    weight=row["weight"],
                    document_date=row["document_date"] or "",
                    event_date=row["event_date"] or "",
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    created_at=row["created_at"] or "",
                )
                self.relationships.append(rel)
        finally:
            conn.close()

    def get_stats(self) -> dict[str, Any]:
        """Get versioning statistics."""
        by_type: dict[str, int] = {}
        for rel in self.relationships:
            by_type[rel.relation_type] = by_type.get(rel.relation_type, 0) + 1

        return {
            "total_relationships": len(self.relationships),
            "by_type": by_type,
        }


# Global singleton
_versioning = RelationalVersioning()


def add_relationship(
    source_id: str,
    target_id: str,
    relation_type: str,
    weight: float = 0.5,
    document_date: str = "",
    event_date: str = "",
    metadata: dict[str, Any] | None = None,
) -> VersionedRelationship:
    """Convenience function to add a relationship."""
    return _versioning.add_relationship(
        source_id,
        target_id,
        relation_type,
        weight,
        document_date,
        event_date,
        metadata,
    )


def get_current_version(memory_id: str) -> str:
    """Convenience function to get current version."""
    return _versioning.get_current_version(memory_id)


def get_memory_timeline(memory_id: str) -> list[VersionedRelationship]:
    """Convenience function to get memory timeline."""
    return _versioning.get_memory_timeline(memory_id)

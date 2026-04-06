"""Cross-Session Transfer — Learn from past sessions.

Implements:
- Extract decisions and outcomes from completed sessions
- Generalize to principles applicable to future sessions
- Store as global-scoped memories for all agents
- Transferability scoring based on generalizability, outcome, repetition
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TransferableKnowledge:
    """Knowledge extracted from a session for transfer."""

    id: str
    source_session: str
    content: str
    knowledge_type: str  # decision, lesson, pattern, principle
    confidence: float
    transferability_score: float
    occurrence_count: int = 1
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)


class CrossSessionTransfer:
    """Transfers learnings across sessions."""

    def __init__(self, storage_path: Path | None = None):
        """Initialize cross-session transfer.

        Args:
            storage_path: Path to store transferred knowledge.
        """
        self.storage_path = storage_path or Path(".sisyphus/cross_session")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.knowledge: list[TransferableKnowledge] = []
        self._load_knowledge()

    def extract_decisions(
        self,
        session_id: str,
        decisions: list[dict[str, Any]],
    ) -> list[TransferableKnowledge]:
        """Extract decisions from a session for transfer.

        Args:
            session_id: Source session ID.
            decisions: List of decision dicts with content, outcome, etc.

        Returns:
            List of TransferableKnowledge objects.
        """
        import uuid

        transferred = []

        for decision in decisions:
            content = decision.get("content", "")
            outcome = decision.get("outcome", "unknown")
            success = outcome in ("success", "positive", "confirmed")

            # Calculate transferability score
            transferability = self._transferability_score(
                content=content,
                success=success,
                occurrence_count=decision.get("occurrence_count", 1),
            )

            if transferability > 0.6:  # Only transfer high-quality knowledge
                knowledge = TransferableKnowledge(
                    id=str(uuid.uuid4())[:8],
                    source_session=session_id,
                    content=content,
                    knowledge_type="decision",
                    confidence=0.8 if success else 0.3,
                    transferability_score=transferability,
                    occurrence_count=decision.get("occurrence_count", 1),
                    metadata={"outcome": outcome},
                )
                transferred.append(knowledge)
                self.knowledge.append(knowledge)

        self._save_knowledge()
        return transferred

    def extract_lessons(
        self,
        session_id: str,
        lessons: list[dict[str, Any]],
    ) -> list[TransferableKnowledge]:
        """Extract lessons learned from a session.

        Args:
            session_id: Source session ID.
            lessons: List of lesson dicts.

        Returns:
            List of TransferableKnowledge objects.
        """
        import uuid

        transferred = []

        for lesson in lessons:
            content = lesson.get("content", "")
            success = lesson.get("outcome", "unknown") == "success"

            transferability = self._transferability_score(
                content=content,
                success=success,
                occurrence_count=lesson.get("occurrence_count", 1),
            )

            if transferability > 0.5:
                knowledge = TransferableKnowledge(
                    id=str(uuid.uuid4())[:8],
                    source_session=session_id,
                    content=content,
                    knowledge_type="lesson",
                    confidence=0.7 if success else 0.4,
                    transferability_score=transferability,
                    occurrence_count=lesson.get("occurrence_count", 1),
                    metadata=lesson.get("metadata", {}),
                )
                transferred.append(knowledge)
                self.knowledge.append(knowledge)

        self._save_knowledge()
        return transferred

    def get_transferable_knowledge(
        self,
        query: str,
        min_score: float = 0.6,
        limit: int = 10,
    ) -> list[TransferableKnowledge]:
        """Get transferable knowledge relevant to a query.

        Args:
            query: Search query.
            min_score: Minimum transferability score.
            limit: Maximum results.

        Returns:
            List of relevant TransferableKnowledge objects.
        """
        query_words = set(query.lower().split())
        results = []

        for knowledge in self.knowledge:
            if knowledge.transferability_score < min_score:
                continue

            # Score by keyword overlap
            content_words = set(knowledge.content.lower().split())
            overlap = len(query_words & content_words) / max(1, len(query_words))

            if overlap > 0.1:
                results.append((knowledge, overlap))

        # Sort by combined score
        results.sort(
            key=lambda x: x[0].transferability_score * 0.6 + x[1] * 0.4,
            reverse=True,
        )

        return [k for k, _ in results[:limit]]

    def _transferability_score(
        self,
        content: str,
        success: bool,
        occurrence_count: int,
    ) -> float:
        """Calculate how transferable a piece of knowledge is.

        Args:
            content: Knowledge content.
            success: Whether the outcome was successful.
            occurrence_count: How many times this has occurred.

        Returns:
            Transferability score (0-1).
        """
        # Generalizability: less specific = more transferable
        specific_indicators = ["file:", "line:", "function:", "class:", "/"]
        specificity = sum(1 for ind in specific_indicators if ind in content.lower())
        generalizability = max(0.0, 1.0 - specificity * 0.2)

        # Outcome weight
        outcome_weight = 1.0 if success else 0.2

        # Repetition weight
        repetition = min(1.0, occurrence_count / 3.0)

        return generalizability * 0.4 + outcome_weight * 0.4 + repetition * 0.2

    def _save_knowledge(self) -> None:
        """Save knowledge to storage."""
        data = [
            {
                "id": k.id,
                "source_session": k.source_session,
                "content": k.content,
                "knowledge_type": k.knowledge_type,
                "confidence": k.confidence,
                "transferability_score": k.transferability_score,
                "occurrence_count": k.occurrence_count,
                "created_at": k.created_at,
                "metadata": k.metadata,
            }
            for k in self.knowledge
        ]
        (self.storage_path / "knowledge.json").write_text(json.dumps(data, indent=2))

    def _load_knowledge(self) -> None:
        """Load knowledge from storage."""
        knowledge_file = self.storage_path / "knowledge.json"
        if not knowledge_file.exists():
            return

        try:
            data = json.loads(knowledge_file.read_text())
            for d in data:
                self.knowledge.append(
                    TransferableKnowledge(
                        id=d["id"],
                        source_session=d["source_session"],
                        content=d["content"],
                        knowledge_type=d["knowledge_type"],
                        confidence=d["confidence"],
                        transferability_score=d["transferability_score"],
                        occurrence_count=d.get("occurrence_count", 1),
                        created_at=d.get("created_at", ""),
                        metadata=d.get("metadata", {}),
                    )
                )
        except Exception as e:
            logger.warning(f"Failed to load cross-session knowledge: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get cross-session transfer statistics."""
        by_type: dict[str, int] = {}
        for k in self.knowledge:
            by_type[k.knowledge_type] = by_type.get(k.knowledge_type, 0) + 1

        return {
            "total_knowledge": len(self.knowledge),
            "by_type": by_type,
            "avg_transferability": round(
                sum(k.transferability_score for k in self.knowledge)
                / max(1, len(self.knowledge)),
                4,
            ),
        }


# Global singleton
_transfer = CrossSessionTransfer()


def extract_decisions(
    session_id: str,
    decisions: list[dict[str, Any]],
) -> list[TransferableKnowledge]:
    """Convenience function to extract decisions."""
    return _transfer.extract_decisions(session_id, decisions)


def extract_lessons(
    session_id: str,
    lessons: list[dict[str, Any]],
) -> list[TransferableKnowledge]:
    """Convenience function to extract lessons."""
    return _transfer.extract_lessons(session_id, lessons)


def get_transferable_knowledge(
    query: str,
    min_score: float = 0.6,
    limit: int = 10,
) -> list[TransferableKnowledge]:
    """Convenience function to get transferable knowledge."""
    return _transfer.get_transferable_knowledge(query, min_score, limit)

"""Cross-Session Transfer — Learn from past sessions.

Implements:
- Extract decisions and outcomes from completed sessions
- Generalize to principles applicable to future sessions
- Store as global-scoped memories for all agents
- Transferability scoring based on embeddings + generalizability + outcome + repetition
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Generalization patterns for semantic scoring
GENERAL_PATTERNS = [
    "best practice", "convention", "pattern", "principle", "guideline",
    "always", "never", "should", "avoid", "recommend", "prefer",
    "learned", "discovered", "found that", "effective", "works well",
    "architecture", "design pattern", "strategy", "approach",
]
SPECIFIC_PATTERNS = [
    "file:", "line:", "function:", "class:", "/src/", ".py:", ".ts:",
]


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
    embedding: list[float] = field(default_factory=list)  # Semantic embedding for similarity


class CrossSessionTransfer:
    """Transfers learnings across sessions."""

    def __init__(self, storage_path: Path | None = None, use_embeddings: bool = True):
        """Initialize cross-session transfer.

        Args:
            storage_path: Path to store transferred knowledge.
            use_embeddings: Whether to use embedding-based scoring.
        """
        self.storage_path = storage_path or Path(".sisyphus/cross_session")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.knowledge: list[TransferableKnowledge] = []
        self.use_embeddings = use_embeddings
        self._embedding_cache = None
        self._load_knowledge()

    @property
    def _cache(self):
        """Lazy-load embedding cache."""
        if self._embedding_cache is None and self.use_embeddings:
            try:
                from .embeddings.model_cache import get_embedding_cache
                self._embedding_cache = get_embedding_cache()
            except ImportError:
                logger.warning("Embedding cache unavailable, falling back to keyword scoring")
                self.use_embeddings = False
        return self._embedding_cache

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
                embedding = self._get_embedding(content)

                knowledge = TransferableKnowledge(
                    id=str(uuid.uuid4())[:8],
                    source_session=session_id,
                    content=content,
                    knowledge_type="decision",
                    confidence=0.8 if success else 0.3,
                    transferability_score=transferability,
                    occurrence_count=decision.get("occurrence_count", 1),
                    metadata={"outcome": outcome},
                    embedding=embedding,
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
                embedding = self._get_embedding(content)

                knowledge = TransferableKnowledge(
                    id=str(uuid.uuid4())[:8],
                    source_session=session_id,
                    content=content,
                    knowledge_type="lesson",
                    confidence=0.7 if success else 0.4,
                    transferability_score=transferability,
                    occurrence_count=lesson.get("occurrence_count", 1),
                    metadata=lesson.get("metadata", {}),
                    embedding=embedding,
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
        generalizability = self._semantic_generalizability(content)

        outcome_weight = 1.0 if success else 0.2

        repetition = min(1.0, occurrence_count / 3.0)

        return generalizability * 0.4 + outcome_weight * 0.4 + repetition * 0.2

    def _semantic_generalizability(self, content: str) -> float:
        """Score semantic generalizability using embeddings and pattern matching.

        Args:
            content: Knowledge content to score.

        Returns:
            Generalizability score (0-1).
        """
        content_lower = content.lower()

        general_score = sum(
            0.08 for pattern in GENERAL_PATTERNS
            if pattern in content_lower
        )

        specific_score = sum(
            0.15 for pattern in SPECIFIC_PATTERNS
            if pattern in content_lower
        )

        base_score = 0.5 + general_score - specific_score
        base_score = max(0.0, min(1.0, base_score))

        if self.use_embeddings and self._cache is not None:
            try:
                general_embedding = self._cache.encode("general principle best practice learned")
                content_embedding = self._cache.encode(content)

                from numpy import dot
                from numpy.linalg import norm
                similarity = dot(general_embedding, content_embedding) / (
                    norm(general_embedding) * norm(content_embedding) + 1e-8
                )

                semantic_weight = 0.3
                return base_score * (1 - semantic_weight) + (similarity + 1) / 2 * semantic_weight
            except Exception as e:
                logger.debug(f"Embedding similarity failed: {e}")

        return base_score

    def _get_embedding(self, content: str) -> list[float]:
        """Get embedding for content using cache.

        Args:
            content: Content to embed.

        Returns:
            List of embedding dimensions.
        """
        if self.use_embeddings and self._cache is not None:
            try:
                emb = self._cache.encode(content)
                return emb.tolist()
            except Exception as e:
                logger.debug(f"Failed to encode content: {e}")
        return []

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
                "embedding": k.embedding,
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
                        embedding=d.get("embedding", []),
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

    def activate_for_session(
        self,
        task_context: str,
        min_score: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Activate cross-session transfer at session start.

        Loads relevant knowledge based on current task context and prepares
        it for injection into routing context.

        Args:
            task_context: Current task/session description.
            min_score: Minimum transferability threshold.

        Returns:
            List of knowledge dicts ready for context injection.
        """
        relevant = self.get_transferable_knowledge(
            query=task_context,
            min_score=min_score,
            limit=5,
        )

        if not relevant:
            return []

        activated = []
        for knowledge in relevant:
            activated.append({
                "content": knowledge.content,
                "knowledge_type": knowledge.knowledge_type,
                "confidence": knowledge.confidence,
                "transferability_score": knowledge.transferability_score,
                "source_session": knowledge.source_session,
                "metadata": knowledge.metadata,
            })

        logger.info(f"Activated {len(activated)} transferable knowledge items for session")
        return activated


# Global singleton
_transfer = CrossSessionTransfer()


def activate_for_session(
    task_context: str,
    min_score: float = 0.5,
) -> list[dict[str, Any]]:
    """Convenience function to activate transfer for a session."""
    return _transfer.activate_for_session(task_context, min_score)


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

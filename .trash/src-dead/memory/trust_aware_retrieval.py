"""Trust-Aware Retrieval — Membrane-inspired trust scoring.

Based on Membrane (selective learning substrate with trust-aware retrieval).

Key innovation: Score memories by competence/trust, not just relevance.
- Track memory source reliability
- Decay trust for unverified memories
- Boost trust for user-confirmed memories
- Competence-based retrieval (prefer memories from reliable sources)
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Trust scoring constants
TRUST_INITIAL = 0.5  # Initial trust for new memories
TRUST_CONFIRMED_BOOST = 0.3  # Boost for user-confirmed memories
TRUST_UNVERIFIED_DECAY = 0.05  # Decay per day for unverified memories
TRUST_CONTRADICTION_PENALTY = 0.2  # Penalty for contradicted memories
TRUST_MIN = 0.0
TRUST_MAX = 1.0


@dataclass
class TrustScore:
    """Trust score for a memory."""

    memory_id: str
    trust: float
    source_reliability: float
    verification_count: int
    contradiction_count: int
    last_verified: str = ""
    last_updated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class TrustAwareRetrieval:
    """Membrane-style trust-aware memory retrieval."""

    def __init__(self, db_path: Path | None = None):
        """Initialize trust-aware retrieval.

        Args:
            db_path: Path to the memory database.
        """
        if db_path is None:
            project_root = Path(__file__).resolve().parents[2]
            db_path = project_root / "context" / "memory" / "mind_from_mind.db"
        self.db_path = db_path
        self.trust_scores: dict[str, TrustScore] = {}
        self._ensure_table()
        self._load_trust_scores()

    def _ensure_table(self) -> None:
        """Create trust scores table."""
        if not self.db_path.exists():
            return

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_trust (
                    memory_id TEXT PRIMARY KEY,
                    trust REAL DEFAULT 0.5,
                    source_reliability REAL DEFAULT 0.5,
                    verification_count INTEGER DEFAULT 0,
                    contradiction_count INTEGER DEFAULT 0,
                    last_verified TEXT,
                    last_updated TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def initialize_trust(
        self,
        memory_id: str,
        source_reliability: float = 0.5,
    ) -> TrustScore:
        """Initialize trust score for a new memory.

        Args:
            memory_id: Memory identifier.
            source_reliability: Initial source reliability (0-1).

        Returns:
            Initialized TrustScore.
        """
        score = TrustScore(
            memory_id=memory_id,
            trust=TRUST_INITIAL,
            source_reliability=source_reliability,
            verification_count=0,
            contradiction_count=0,
        )
        self.trust_scores[memory_id] = score
        self._save_trust_score(score)
        return score

    def confirm_memory(self, memory_id: str) -> TrustScore:
        """Confirm a memory (user verification).

        Args:
            memory_id: Memory to confirm.

        Returns:
            Updated TrustScore.
        """
        score = self.trust_scores.get(memory_id)
        if not score:
            score = self.initialize_trust(memory_id)

        score.trust = min(TRUST_MAX, score.trust + TRUST_CONFIRMED_BOOST)
        score.verification_count += 1
        score.last_verified = datetime.now(timezone.utc).isoformat()
        score.last_updated = datetime.now(timezone.utc).isoformat()
        self._save_trust_score(score)

        return score

    def contradict_memory(self, memory_id: str) -> TrustScore:
        """Record a contradiction for a memory.

        Args:
            memory_id: Memory that was contradicted.

        Returns:
            Updated TrustScore.
        """
        score = self.trust_scores.get(memory_id)
        if not score:
            score = self.initialize_trust(memory_id)

        score.trust = max(TRUST_MIN, score.trust - TRUST_CONTRADICTION_PENALTY)
        score.contradiction_count += 1
        score.last_updated = datetime.now(timezone.utc).isoformat()
        self._save_trust_score(score)

        return score

    def decay_unverified(self, days: int = 1) -> dict[str, TrustScore]:
        """Decay trust for unverified memories.

        Args:
            days: Number of days to decay.

        Returns:
            Dict of decayed scores.
        """
        decayed = {}
        for memory_id, score in self.trust_scores.items():
            if score.verification_count == 0:
                score.trust = max(
                    TRUST_MIN, score.trust - (TRUST_UNVERIFIED_DECAY * days)
                )
                score.last_updated = datetime.now(timezone.utc).isoformat()
                self._save_trust_score(score)
                decayed[memory_id] = score

        return decayed

    def get_trust_score(self, memory_id: str) -> TrustScore | None:
        """Get trust score for a memory."""
        return self.trust_scores.get(memory_id)

    def rank_by_trust(
        self,
        memory_ids: list[str],
        min_trust: float = 0.0,
    ) -> list[tuple[str, float]]:
        """Rank memories by trust score.

        Args:
            memory_ids: List of memory IDs to rank.
            min_trust: Minimum trust threshold.

        Returns:
            List of (memory_id, trust_score) tuples, sorted by trust.
        """
        ranked = []
        for memory_id in memory_ids:
            score = self.trust_scores.get(memory_id)
            if score and score.trust >= min_trust:
                ranked.append((memory_id, score.trust))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def get_trust_aware_results(
        self,
        search_results: list[dict[str, Any]],
        trust_weight: float = 0.3,
        relevance_weight: float = 0.7,
    ) -> list[dict[str, Any]]:
        """Re-rank search results by combining trust and relevance.

        Args:
            search_results: List of search result dicts with 'id' and 'score'.
            trust_weight: Weight for trust score (0-1).
            relevance_weight: Weight for relevance score (0-1).

        Returns:
            Re-ranked results with combined scores.
        """
        ranked_results = []
        for result in search_results:
            memory_id = result.get("id", result.get("memory_id", ""))
            relevance_score = result.get("score", 0.5)

            trust_score = self.trust_scores.get(memory_id)
            trust = trust_score.trust if trust_score else TRUST_INITIAL

            # Combined score
            combined = relevance_weight * relevance_score + trust_weight * trust

            ranked_results.append(
                {
                    **result,
                    "trust_score": trust,
                    "combined_score": round(combined, 4),
                }
            )

        # Sort by combined score
        ranked_results.sort(key=lambda r: r["combined_score"], reverse=True)
        return ranked_results

    def _save_trust_score(self, score: TrustScore) -> None:
        """Save trust score to database."""
        if not self.db_path.exists():
            return

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_trust
                (memory_id, trust, source_reliability, verification_count, contradiction_count, last_verified, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    score.memory_id,
                    score.trust,
                    score.source_reliability,
                    score.verification_count,
                    score.contradiction_count,
                    score.last_verified,
                    score.last_updated,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _load_trust_scores(self) -> None:
        """Load trust scores from database."""
        if not self.db_path.exists():
            return

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute("SELECT * FROM memory_trust")
            for row in cursor.fetchall():
                score = TrustScore(
                    memory_id=row["memory_id"],
                    trust=row["trust"],
                    source_reliability=row["source_reliability"],
                    verification_count=row["verification_count"],
                    contradiction_count=row["contradiction_count"],
                    last_verified=row["last_verified"] or "",
                    last_updated=row["last_updated"] or "",
                )
                self.trust_scores[score.memory_id] = score
        finally:
            conn.close()

    def get_stats(self) -> dict[str, Any]:
        """Get trust statistics."""
        if not self.trust_scores:
            return {"total_tracked": 0}

        trusts = [s.trust for s in self.trust_scores.values()]
        verified = sum(
            1 for s in self.trust_scores.values() if s.verification_count > 0
        )
        contradicted = sum(
            1 for s in self.trust_scores.values() if s.contradiction_count > 0
        )

        return {
            "total_tracked": len(self.trust_scores),
            "avg_trust": round(sum(trusts) / len(trusts), 4),
            "min_trust": round(min(trusts), 4),
            "max_trust": round(max(trusts), 4),
            "verified_count": verified,
            "contradicted_count": contradicted,
        }


# Global singleton
_trust = TrustAwareRetrieval()


def initialize_trust(memory_id: str, source_reliability: float = 0.5) -> TrustScore:
    """Convenience function to initialize trust."""
    return _trust.initialize_trust(memory_id, source_reliability)


def confirm_memory(memory_id: str) -> TrustScore:
    """Convenience function to confirm a memory."""
    return _trust.confirm_memory(memory_id)


def contradict_memory(memory_id: str) -> TrustScore:
    """Convenience function to contradict a memory."""
    return _trust.contradict_memory(memory_id)


def rank_by_trust(
    memory_ids: list[str], min_trust: float = 0.0
) -> list[tuple[str, float]]:
    """Convenience function to rank by trust."""
    return _trust.rank_by_trust(memory_ids, min_trust)


def get_trust_aware_results(
    search_results: list[dict[str, Any]],
    trust_weight: float = 0.3,
    relevance_weight: float = 0.7,
) -> list[dict[str, Any]]:
    """Convenience function to get trust-aware results."""
    return _trust.get_trust_aware_results(
        search_results, trust_weight, relevance_weight
    )

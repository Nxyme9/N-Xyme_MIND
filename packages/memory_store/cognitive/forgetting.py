"""Adaptive forgetting — FadeMem-inspired memory decay.

Based on FadeMem (Alibaba + Peking University, arXiv:2601.18642).
Achieves 45% storage reduction while improving multi-hop reasoning.

Architecture: Dual-layer memory hierarchy with differential decay rates.
Adaptive exponential decay modulated by:
1. Semantic relevance (how related to current context)
2. Access frequency (how often retrieved)
3. Temporal patterns (age-based Ebbinghaus curve)

Decay actions by threshold:
| Score | Action |
|-------|--------|
| > 0.6 | Active — always returned in search |
| 0.3-0.6 | Dormant — returned only on strong semantic match |
| 0.1-0.3 | Archived — excluded from default search |
| < 0.1 | Scheduled for consolidation → delete sources |
"""

from __future__ import annotations

import logging
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Decay constants (from FadeMem paper)
BASE_DECAY_RATE = 0.1  # Base exponential decay rate
SEMANTIC_RELEVANCE_WEIGHT = 0.35  # Weight for semantic relevance
ACCESS_FREQUENCY_WEIGHT = 0.35  # Weight for access frequency
TEMPORAL_WEIGHT = 0.30  # Weight for temporal age

# Thresholds - Made less aggressive to prevent premature deletion
THRESHOLD_ACTIVE = 0.4  # Was 0.6 - Active memories
THRESHOLD_DORMANT = 0.2  # Was 0.3 - Dormant memories
THRESHOLD_ARCHIVED = 0.05  # Was 0.1 - Archived memories

# Ebbinghaus forgetting curve parameters
EBBINGHAUS_STABILITY_INITIAL = 1.0  # Initial memory stability
EBBINGHAUS_RETRIEVABILITY_THRESHOLD = 0.9  # When to trigger review


@dataclass
class DecayScore:
    """Complete decay score with components."""

    overall: float
    temporal: float
    semantic_relevance: float
    access_frequency: float
    graph_centrality: float
    cross_session_utility: float
    action: str  # active, dormant, archived, consolidate


class AdaptiveDecay:
    """FadeMem-style adaptive memory decay."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize adaptive decay.

        Args:
            db_path: Path to the memory database.
        """
        if db_path is None:
            project_root = Path(__file__).resolve().parents[3]
            db_path = project_root / "context" / "memory" / "mind_from_mind.db"
        self.db_path = db_path
        self._ensure_decay_table()

    def _ensure_decay_table(self) -> None:
        """Create decay tracking table if it doesn't exist."""
        if not self.db_path.exists():
            return

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS memory_decay (
                    memory_id TEXT PRIMARY KEY,
                    stability REAL DEFAULT 1.0,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    semantic_relevance REAL DEFAULT 0.5,
                    graph_centrality REAL DEFAULT 0.0,
                    cross_session_count INTEGER DEFAULT 0,
                    total_sessions INTEGER DEFAULT 1,
                    decay_score REAL DEFAULT 0.5,
                    last_updated TEXT
                )"""
            )
            conn.commit()
        finally:
            conn.close()

    def compute_decay_score(
        self,
        memory_id: str,
        age_days: float,
        access_count: int = 0,
        last_accessed: Optional[str] = None,
        semantic_relevance: float = 0.5,
        graph_centrality: float = 0.0,
        cross_session_count: int = 0,
        total_sessions: int = 1,
    ) -> DecayScore:
        """Compute comprehensive decay score for a memory.

        Formula:
        decay = temporal * (1 + usage_boost + recency_boost) * quality *
                (0.5 + 0.5 * centrality) * (0.7 + 0.3 * cross_session)

        Args:
            memory_id: Memory identifier.
            age_days: Age of memory in days.
            access_count: Number of times accessed.
            last_accessed: ISO timestamp of last access.
            semantic_relevance: Semantic relevance score (0-1).
            graph_centrality: Graph centrality score (0-1).
            cross_session_count: Number of sessions this memory was useful in.
            total_sessions: Total number of sessions.

        Returns:
            DecayScore with all components.
        """
        # 1. Temporal decay (Ebbinghaus forgetting curve)
        stability = EBBINGHAUS_STABILITY_INITIAL + math.log(1 + access_count) * 0.5
        temporal = math.exp(-age_days / max(1, stability * 10))

        # 2. Access frequency score (0-1)
        access_freq_score = min(1.0, access_count / 10.0)

        # 3. Recency score (0-1)
        recency_score = 0.5
        if last_accessed:
            try:
                last_access = datetime.fromisoformat(
                    last_accessed.replace("Z", "+00:00")
                )
                days_since_access = (
                    datetime.now(timezone.utc) - last_access
                ).total_seconds() / 86400
                recency_score = max(0.0, 1.0 - days_since_access / 90.0)
            except (ValueError, TypeError):
                pass

        # 4. Quality factor (semantic relevance)
        quality = semantic_relevance

        # 5. Graph centrality score
        centrality_score = graph_centrality

        # 6. Cross-session utility
        cross_session = min(1.0, cross_session_count / max(1, total_sessions))

        # Weighted combination (FadeMem-style)
        overall = (
            TEMPORAL_WEIGHT * temporal
            + SEMANTIC_RELEVANCE_WEIGHT * quality
            + ACCESS_FREQUENCY_WEIGHT * ((access_freq_score + recency_score) / 2)
            + 0.15 * centrality_score
            + 0.10 * cross_session
        )

        # Normalize to 0-1 range
        overall = min(1.0, max(0.0, overall))

        # Determine action
        if overall >= THRESHOLD_ACTIVE:
            action = "active"
        elif overall >= THRESHOLD_DORMANT:
            action = "dormant"
        elif overall >= THRESHOLD_ARCHIVED:
            action = "archived"
        else:
            action = "consolidate"

        score = DecayScore(
            overall=round(overall, 4),
            temporal=round(temporal, 4),
            semantic_relevance=round(semantic_relevance, 4),
            access_frequency=round((access_freq_score + recency_score) / 2, 4),
            graph_centrality=round(graph_centrality, 4),
            cross_session_utility=round(cross_session, 4),
            action=action,
        )

        # Persist score
        self._save_decay_score(memory_id, score, stability)

        return score

    def _save_decay_score(
        self,
        memory_id: str,
        score: DecayScore,
        stability: float,
    ) -> None:
        """Save decay score to database."""
        if not self.db_path.exists():
            return

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """INSERT OR REPLACE INTO memory_decay
                (memory_id, stability, decay_score, last_updated)
                VALUES (?, ?, ?, ?)""",
                (
                    memory_id,
                    stability,
                    score.overall,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def record_access(self, memory_id: str) -> None:
        """Record a memory access (increments access count)."""
        if not self.db_path.exists():
            return

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """INSERT INTO memory_decay (memory_id, access_count, last_accessed, last_updated)
                VALUES (?, 1, ?, ?)
                ON CONFLICT(memory_id) DO UPDATE SET
                    access_count = access_count + 1,
                    last_accessed = excluded.last_accessed,
                    last_updated = excluded.last_updated""",
                (
                    memory_id,
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def apply_decay_actions(self) -> dict[str, int]:
        """Apply decay actions to all memories based on their scores.

        Returns:
            Dict with counts of actions taken.
        """
        if not self.db_path.exists():
            return {"active": 0, "dormant": 0, "archived": 0, "consolidated": 0}

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute("SELECT memory_id, decay_score FROM memory_decay")
            rows = cursor.fetchall()

            actions = {"active": 0, "dormant": 0, "archived": 0, "consolidated": 0}

            for memory_id, score in rows:
                if score >= THRESHOLD_ACTIVE:
                    conn.execute(
                        "UPDATE memories SET tier = 'long_term' WHERE id = ? AND tier = 'archived'",
                        (memory_id,),
                    )
                    actions["active"] += 1
                elif score >= THRESHOLD_DORMANT:
                    actions["dormant"] += 1
                elif score >= THRESHOLD_ARCHIVED:
                    conn.execute(
                        "UPDATE memories SET tier = 'dormant' WHERE id = ?",
                        (memory_id,),
                    )
                    actions["archived"] += 1
                else:
                    conn.execute(
                        "UPDATE memories SET tier = 'archived' WHERE id = ?",
                        (memory_id,),
                    )
                    actions["consolidated"] += 1

            conn.commit()
            return actions

        finally:
            conn.close()

    def get_decay_stats(self) -> dict[str, Any]:
        """Get decay statistics."""
        if not self.db_path.exists():
            return {"total_tracked": 0}

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                """SELECT
                    COUNT(*) as total,
                    AVG(decay_score) as avg_score,
                    MIN(decay_score) as min_score,
                    MAX(decay_score) as max_score,
                    SUM(CASE WHEN decay_score >= ? THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN decay_score >= ? AND decay_score < ? THEN 1 ELSE 0 END) as dormant,
                    SUM(CASE WHEN decay_score >= ? AND decay_score < ? THEN 1 ELSE 0 END) as archived,
                    SUM(CASE WHEN decay_score < ? THEN 1 ELSE 0 END) as consolidate
                FROM memory_decay""",
                (
                    THRESHOLD_ACTIVE,
                    THRESHOLD_DORMANT,
                    THRESHOLD_ACTIVE,
                    THRESHOLD_ARCHIVED,
                    THRESHOLD_DORMANT,
                    THRESHOLD_ARCHIVED,
                ),
            )
            row = cursor.fetchone()

            return {
                "total_tracked": row[0],
                "avg_score": round(row[1], 4) if row[1] else 0,
                "min_score": round(row[2], 4) if row[2] else 0,
                "max_score": round(row[3], 4) if row[3] else 0,
                "active": row[4],
                "dormant": row[5],
                "archived": row[6],
                "consolidate": row[7],
            }
        finally:
            conn.close()


# Global singleton
_decay = AdaptiveDecay()


def compute_decay_score(
    memory_id: str,
    age_days: float,
    access_count: int = 0,
    last_accessed: Optional[str] = None,
    semantic_relevance: float = 0.5,
    graph_centrality: float = 0.0,
    cross_session_count: int = 0,
    total_sessions: int = 1,
) -> DecayScore:
    """Convenience function to compute decay score."""
    return _decay.compute_decay_score(
        memory_id,
        age_days,
        access_count,
        last_accessed,
        semantic_relevance,
        graph_centrality,
        cross_session_count,
        total_sessions,
    )


def record_access(memory_id: str) -> None:
    """Convenience function to record memory access."""
    _decay.record_access(memory_id)


def apply_decay_actions() -> dict[str, int]:
    """Convenience function to apply decay actions."""
    return _decay.apply_decay_actions()

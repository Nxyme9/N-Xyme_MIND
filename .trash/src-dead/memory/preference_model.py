"""Preference model for learning user result type preferences.

This module tracks which result types (code, docs, configs, data) the user
interacts with most and provides preference scores for re-ranking results.
"""

import logging
import math
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from src.memory.learning_config import get_config

logger = logging.getLogger(__name__)

# Result types tracked by the preference model
RESULT_TYPES = ["code", "doc", "config", "data", "text", "other"]

# Half-life for preference decay (30 days)
PREFERENCE_HALF_LIFE_DAYS = 30.0


class PreferenceModel:
    """Learns user preferences for result types based on usage patterns."""

    def __init__(self, db_path: str):
        """Initialize preference model with registry DB path.

        Args:
            db_path: Path to the SQLite file registry database.
        """
        self.db_path = db_path
        self._init_preferences_table()
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration for preference model."""
        try:
            config = get_config()
            self.exploration_rate = config.get("exploration_rate", 0.2)
            self.min_confidence = config.get("min_confidence", 0.8)
            self.feedback_ttl_days = config.get("feedback_ttl_days", 90)
        except Exception:
            # Fallback to defaults if config fails
            self.exploration_rate = 0.2
            self.min_confidence = 0.8
            self.feedback_ttl_days = 90

    def _get_connection(self) -> sqlite3.Connection:
        """Get SQLite connection with proper settings."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _init_preferences_table(self) -> None:
        """Initialize user_preferences table if not exists."""
        try:
            conn = self._get_connection()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    result_type TEXT NOT NULL,
                    used INTEGER DEFAULT 0,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_preferences_type
                ON user_preferences(result_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_preferences_timestamp
                ON user_preferences(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_preferences_query
                ON user_preferences(query)
            """)
            conn.commit()
            conn.close()
            logger.debug("Initialized user_preferences table")
        except Exception as e:
            logger.error(f"Failed to init preferences table: {e}")

    def _calculate_decay_factor(self, timestamp: str) -> float:
        """Calculate decay factor for a timestamp using exponential decay.

        Uses 30-day half-life: decay_factor = 0.5^(days/30)

        Args:
            timestamp: ISO format timestamp string.

        Returns:
            Decay factor between 0.0 and 1.0.
        """
        try:
            if isinstance(timestamp, str):
                ts_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            else:
                ts_dt = timestamp

            now = datetime.now(ts_dt.tzinfo) if ts_dt.tzinfo else datetime.now()
            days_since = (now - ts_dt).total_seconds() / 86400

            # Exponential decay with 30-day half-life
            decay_factor = math.pow(0.5, days_since / PREFERENCE_HALF_LIFE_DAYS)
            return max(0.0, min(1.0, decay_factor))
        except Exception:
            return 0.5  # Neutral if parsing fails

    def record_preference(self, query: str, result_type: str, used: bool) -> bool:
        """Record a preference event.

        Args:
            query: The query string that led to this result.
            result_type: The type of result (code, doc, config, data, text, other).
            used: Whether the user used this result (True) or ignored it (False).

        Returns:
            True if successful, False otherwise.
        """
        if result_type not in RESULT_TYPES:
            logger.warning(f"Unknown result type: {result_type}")
            result_type = "other"

        try:
            conn = self._get_connection()
            timestamp = datetime.now().isoformat()
            conn.execute(
                """INSERT INTO user_preferences (query, result_type, used, timestamp)
                   VALUES (?, ?, ?, ?)""",
                (query, result_type, 1 if used else 0, timestamp),
            )
            conn.commit()
            conn.close()
            logger.debug(
                f"Recorded preference: {query[:30]} -> {result_type} (used={used})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to record preference: {e}")
            return False

    def get_preferences(self) -> dict[str, float]:
        """Get current preference scores per result type.

        Calculates weighted average of usage frequency and recency,
        with exponential decay for older preferences.

        Returns:
            Dict mapping result_type to preference score (0.0-1.0).
        """
        preferences = {result_type: 0.0 for result_type in RESULT_TYPES}

        try:
            conn = self._get_connection()
            cursor = conn.execute(
                """
                SELECT result_type, used, timestamp
                FROM user_preferences
                WHERE timestamp > datetime('now', '-' || ? || ' days')
            """,
                (self.feedback_ttl_days,),
            )

            type_scores: dict[str, list[float]] = {t: [] for t in RESULT_TYPES}

            for row in cursor.fetchall():
                result_type, used, timestamp = row
                if result_type not in RESULT_TYPES:
                    continue

                # Weight: used=1.0, ignored=0.2
                weight = 1.0 if used else 0.2
                decay = self._calculate_decay_factor(timestamp)
                score = weight * decay

                type_scores[result_type].append(score)

            conn.close()

            # Calculate average score per type, normalize to 0-1
            for result_type, scores in type_scores.items():
                if scores:
                    avg_score = sum(scores) / len(scores)
                    # Normalize: cap at 1.0
                    preferences[result_type] = min(1.0, avg_score)

            return preferences
        except Exception as e:
            logger.error(f"Failed to get preferences: {e}")
            return preferences

    def get_preference_for_type(self, result_type: str) -> float:
        """Get preference score for a specific result type.

        Args:
            result_type: The result type to get preference for.

        Returns:
            Preference score between 0.0 and 1.0.
        """
        if result_type not in RESULT_TYPES:
            result_type = "other"

        preferences = self.get_preferences()
        return preferences.get(result_type, 0.0)

    def rerank_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Re-rank results based on learned preferences.

        Boosts results matching preferred types by:
        new_score = original_score + (preference_score * exploration_rate)

        Args:
            results: List of result dicts with 'type' and 'score' keys.

        Returns:
            Re-ranked list of results (sorted by score descending).
        """
        if not results:
            return results

        preferences = self.get_preferences()

        # Apply preference boost to each result
        for result in results:
            result_type = result.get("type", "other")
            if result_type not in RESULT_TYPES:
                result_type = "other"

            pref_score = preferences.get(result_type, 0.0)
            boost = pref_score * self.exploration_rate
            original_score = result.get("score", 0.5)
            result["score"] = original_score + boost
            result["preference_boost"] = boost

        # Sort by boosted score descending
        reranked = sorted(results, key=lambda r: r.get("score", 0), reverse=True)
        return reranked

    def get_preference_stats(self) -> dict[str, Any]:
        """Return statistics about learned preferences.

        Returns:
            Dict with preference stats including counts, top types, etc.
        """
        stats = {
            "total_events": 0,
            "used_count": 0,
            "ignored_count": 0,
            "type_counts": {t: 0 for t in RESULT_TYPES},
            "preferences": self.get_preferences(),
            "top_types": [],
        }

        try:
            conn = self._get_connection()

            # Total events
            cursor = conn.execute("SELECT COUNT(*) FROM user_preferences")
            stats["total_events"] = cursor.fetchone()[0] or 0

            # Used vs ignored
            cursor = conn.execute("""
                SELECT SUM(used) as used, SUM(1 - used) as ignored
                FROM user_preferences
            """)
            row = cursor.fetchone()
            stats["used_count"] = row[0] or 0 if row[0] is not None else 0
            stats["ignored_count"] = row[1] or 0 if row[1] is not None else 0

            # Type counts
            cursor = conn.execute("""
                SELECT result_type, COUNT(*) as cnt
                FROM user_preferences
                GROUP BY result_type
            """)
            for row in cursor.fetchall():
                result_type, count = row
                if result_type in RESULT_TYPES:
                    stats["type_counts"][result_type] = count

            # Top types by preference score
            prefs = stats["preferences"]
            sorted_types = sorted(prefs.items(), key=lambda x: x[1], reverse=True)
            stats["top_types"] = [
                {"type": t, "score": s} for t, s in sorted_types if s > 0
            ]

            conn.close()
            return stats
        except Exception as e:
            logger.error(f"Failed to get preference stats: {e}")
            return stats

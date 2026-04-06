"""
Pattern Learning — Ported from N-Xyme LIVE

Learns user action patterns over time and suggests automations.

Usage:
    learner = PatternLearner()
    learner.record("run_tests")
    learner.record("commit")
    learner.record("push")
    patterns = learner.get_patterns()
"""

import logging
import os
import re
import sqlite3
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Default DB path
DEFAULT_DB_PATH = "context/memory/file_registry.db"


@dataclass
class ActionRecord:
    """A recorded user action."""

    action_type: str
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Pattern:
    """A learned pattern."""

    id: str
    name: str
    trigger_action: str
    suggested_actions: List[str] = field(default_factory=list)
    confidence: float = 0.0
    frequency: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class QueryRecord:
    """A recorded user query."""

    query: str
    results_count: int
    source: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class QueryPattern:
    """A learned query pattern."""

    id: str
    template: str
    normalized_template: str
    confidence: float = 0.0
    frequency: int = 0
    examples: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class PatternLearner:
    """Learns user action patterns over time."""

    def __init__(
        self,
        min_occurrences: int = 3,
        sequence_window: float = 30.0,
        db_path: Optional[str] = None,
    ):
        self.min_occurrences = min_occurrences
        self.sequence_window = sequence_window
        self._history: List[ActionRecord] = []
        self._sequences: Dict[str, List[str]] = defaultdict(
            list
        )  # action -> next actions
        self._patterns: Dict[str, Pattern] = {}

        # Query pattern tracking
        self._query_history: List[QueryRecord] = []
        self._query_patterns: Dict[str, QueryPattern] = {}
        self._query_templates: Dict[str, List[str]] = defaultdict(
            list
        )  # normalized -> raw queries

        # SQLite persistence
        self.db_path = db_path or DEFAULT_DB_PATH
        self._init_db()
        self._load_patterns()

        logger.info(
            f"PatternLearner: Initialized (min={min_occurrences}, db={self.db_path})"
        )

    def _init_db(self) -> None:
        """Initialize SQLite database with learned_patterns table."""
        try:
            # Ensure directory exists
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            conn = self._get_connection()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learned_patterns (
                    id TEXT PRIMARY KEY,
                    pattern_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    trigger_action TEXT,
                    suggested_actions TEXT,
                    confidence REAL NOT NULL,
                    frequency INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    extra_data TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_patterns (
                    id TEXT PRIMARY KEY,
                    template TEXT NOT NULL,
                    normalized_template TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    frequency INTEGER NOT NULL,
                    examples TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    results_count INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()
            conn.close()
            logger.debug("Initialized learned_patterns and query_patterns tables")
        except Exception as e:
            logger.error(f"Failed to init database: {e}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get SQLite connection with proper settings."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _save_action_pattern(self, pattern: Pattern) -> None:
        """Save an action pattern to SQLite."""
        try:
            conn = self._get_connection()
            conn.execute(
                """
                INSERT OR REPLACE INTO learned_patterns
                (id, pattern_type, name, trigger_action, suggested_actions, confidence, frequency, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    pattern.id,
                    "action",
                    pattern.name,
                    pattern.trigger_action,
                    "|".join(pattern.suggested_actions),
                    pattern.confidence,
                    pattern.frequency,
                    pattern.created_at.isoformat(),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save action pattern: {e}")

    def _save_query_pattern(self, pattern: QueryPattern) -> None:
        """Save a query pattern to SQLite."""
        try:
            conn = self._get_connection()
            conn.execute(
                """
                INSERT OR REPLACE INTO query_patterns
                (id, template, normalized_template, confidence, frequency, examples, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    pattern.id,
                    pattern.template,
                    pattern.normalized_template,
                    pattern.confidence,
                    pattern.frequency,
                    "|".join(pattern.examples),
                    pattern.created_at.isoformat(),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save query pattern: {e}")

    def _load_patterns(self) -> None:
        """Load patterns from SQLite on initialization."""
        try:
            conn = self._get_connection()

            # Load action patterns
            cursor = conn.execute("""
                SELECT id, name, trigger_action, suggested_actions, confidence, frequency, created_at
                FROM learned_patterns WHERE pattern_type = 'action'
            """)
            for row in cursor.fetchall():
                pattern = Pattern(
                    id=row[0],
                    name=row[1],
                    trigger_action=row[2],
                    suggested_actions=row[3].split("|") if row[3] else [],
                    confidence=row[4],
                    frequency=row[5],
                    created_at=datetime.fromisoformat(row[6]),
                )
                self._patterns[pattern.id] = pattern

            # Load query patterns
            cursor = conn.execute("""
                SELECT id, template, normalized_template, confidence, frequency, examples, created_at
                FROM query_patterns
            """)
            for row in cursor.fetchall():
                pattern = QueryPattern(
                    id=row[0],
                    template=row[1],
                    normalized_template=row[2],
                    confidence=row[3],
                    frequency=row[4],
                    examples=row[5].split("|") if row[5] else [],
                    created_at=datetime.fromisoformat(row[6]),
                )
                self._query_patterns[pattern.id] = pattern

            conn.close()
            logger.info(
                f"Loaded {len(self._patterns)} action patterns and {len(self._query_patterns)} query patterns from DB"
            )
        except Exception as e:
            logger.error(f"Failed to load patterns: {e}")

    def _normalize_query(self, query: str) -> str:
        """Normalize a query to a template by replacing variable parts."""
        normalized = query.lower().strip()
        # Replace numbers
        normalized = re.sub(r"\d+", "*", normalized)
        # Replace common patterns
        normalized = re.sub(r"\bhow\s+to\b", "how to", normalized)
        normalized = re.sub(r"\bwhat\'?s?\s+the\b", "what's the", normalized)
        normalized = re.sub(r"\bway\s+to\b", "way to", normalized)
        return normalized

    def _calculate_keyword_overlap(self, query1: str, query2: str) -> float:
        """Calculate keyword overlap between two queries."""
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)

    def record(
        self, action_type: str, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a user action."""
        record = ActionRecord(action_type=action_type, context=context or {})
        self._history.append(record)

        # Detect sequences
        if len(self._history) >= 2:
            prev = self._history[-2]
            time_diff = record.timestamp - prev.timestamp

            if time_diff <= self.sequence_window:
                self._sequences[prev.action_type].append(action_type)

        # Keep only last 1000 actions
        if len(self._history) > 1000:
            self._history = self._history[-1000:]

        # Check if pattern detected
        self._check_patterns()

    def _check_patterns(self) -> None:
        """Check for new patterns."""
        for trigger, next_actions in self._sequences.items():
            if len(next_actions) < self.min_occurrences:
                continue

            # Count occurrences
            counter = Counter(next_actions)
            most_common = counter.most_common(3)

            if most_common:
                top_action, count = most_common[0]
                if count >= self.min_occurrences:
                    pattern_id = f"{trigger}->{top_action}"
                    if pattern_id not in self._patterns:
                        confidence = count / len(next_actions)
                        pattern = Pattern(
                            id=pattern_id,
                            name=f"After {trigger}, usually do {top_action}",
                            trigger_action=trigger,
                            suggested_actions=[top_action],
                            confidence=confidence,
                            frequency=count,
                        )
                        self._patterns[pattern_id] = pattern
                        self._save_action_pattern(pattern)
                        logger.info(
                            f"PatternLearner: Detected '{pattern.name}' (confidence={confidence:.2f})"
                        )

    def track_query(self, query: str, results_count: int, source: str) -> None:
        """Record a user query event.

        Args:
            query: The user's query string.
            results_count: Number of results returned.
            source: Source of the query (e.g., 'memory_mcp', 'athena', 'user').
        """
        record = QueryRecord(query=query, results_count=results_count, source=source)
        self._query_history.append(record)

        # Normalize query to template
        normalized = self._normalize_query(query)
        self._query_templates[normalized].append(query)

        # Check for query patterns
        self._check_query_patterns()

        # Keep only last 500 queries
        if len(self._query_history) > 500:
            self._query_history = self._query_history[-500:]

    def _check_query_patterns(self) -> None:
        """Check for new query patterns."""
        for normalized, queries in self._query_templates.items():
            if len(queries) < self.min_occurrences:
                continue

            # Count frequency
            counter = Counter(queries)
            most_common = counter.most_common()

            if most_common:
                top_query, count = most_common[0]
                if count >= self.min_occurrences:
                    pattern_id = f"query_{normalized[:50]}"
                    if pattern_id not in self._query_patterns:
                        confidence = count / len(queries)
                        pattern = QueryPattern(
                            id=pattern_id,
                            template=top_query,
                            normalized_template=normalized,
                            confidence=confidence,
                            frequency=count,
                            examples=[q for q, _ in most_common[:5]],
                        )
                        self._query_patterns[pattern_id] = pattern
                        self._save_query_pattern(pattern)
                        logger.info(
                            f"PatternLearner: Detected query pattern '{normalized}' (confidence={confidence:.2f})"
                        )
                    else:
                        # Update existing pattern
                        pattern = self._query_patterns[pattern_id]
                        pattern.frequency += 1
                        pattern.confidence = pattern.frequency / len(queries)
                        if top_query not in pattern.examples:
                            pattern.examples.append(top_query)
                            pattern.examples = pattern.examples[:10]
                        self._save_query_pattern(pattern)

    def get_query_patterns(self, limit: int = 50) -> List[QueryPattern]:
        """Get most common query patterns.

        Args:
            limit: Maximum number of patterns to return.

        Returns:
            List of QueryPattern sorted by frequency.
        """
        sorted_patterns = sorted(
            self._query_patterns.values(), key=lambda p: p.frequency, reverse=True
        )
        return sorted_patterns[:limit]

    def find_similar_queries(
        self, query: str, threshold: float = 0.6
    ) -> List[Tuple[str, float]]:
        """Find queries similar to the given query.

        Args:
            query: The query to find similar queries for.
            threshold: Minimum similarity threshold (0.0 to 1.0).

        Returns:
            List of (query, similarity) tuples.
        """
        similar = []
        for record in self._query_history:
            similarity = self._calculate_keyword_overlap(query, record.query)
            if similarity >= threshold:
                similar.append((record.query, similarity))

        # Sort by similarity descending and remove duplicates
        similar.sort(key=lambda x: x[1], reverse=True)
        seen = set()
        result = []
        for q, s in similar:
            if q not in seen:
                seen.add(q)
                result.append((q, s))

        return result

    def get_pattern_stats(self) -> Dict[str, Any]:
        """Return statistics about learned patterns.

        Returns:
            Dict with statistics about action and query patterns.
        """
        return {
            "action_patterns": {
                "total": len(self._patterns),
                "high_confidence": sum(
                    1 for p in self._patterns.values() if p.confidence >= 0.7
                ),
            },
            "query_patterns": {
                "total": len(self._query_patterns),
                "total_queries": len(self._query_history),
                "unique_templates": len(self._query_templates),
                "high_confidence": sum(
                    1 for p in self._query_patterns.values() if p.confidence >= 0.7
                ),
            },
            "top_query_patterns": [
                {
                    "template": p.template,
                    "normalized": p.normalized_template,
                    "confidence": p.confidence,
                    "frequency": p.frequency,
                }
                for p in sorted(
                    self._query_patterns.values(),
                    key=lambda p: p.frequency,
                    reverse=True,
                )[:10]
            ],
        }

    def get_patterns(self, min_confidence: float = 0.5) -> List[Pattern]:
        """Get learned patterns above confidence threshold."""
        return [p for p in self._patterns.values() if p.confidence >= min_confidence]

    def suggest_next(self, current_action: str) -> Optional[Pattern]:
        """Suggest next action based on current action."""
        matching = [
            p for p in self._patterns.values() if p.trigger_action == current_action
        ]
        if matching:
            return max(matching, key=lambda p: p.confidence)
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get pattern learning statistics."""
        return {
            "total_actions": len(self._history),
            "sequences_tracked": len(self._sequences),
            "patterns_detected": len(self._patterns),
            "top_patterns": [
                {"name": p.name, "confidence": p.confidence, "frequency": p.frequency}
                for p in sorted(
                    self._patterns.values(), key=lambda p: p.confidence, reverse=True
                )[:5]
            ],
        }

"""Skill Registry — Hybrid routing and performance tracking for skills.

Provides intelligent skill routing based on:
  - Semantic similarity between query and skill triggers
  - Trigger keyword matching
  - Historical performance metrics

Routes queries to the best-matching skills using weighted scoring:
  score = semantic_similarity * w_sem + trigger_match * w_trig + performance * w_perf
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from .db import LearningDB
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from typing import Any


from .db import LearningDB

logger = logging.getLogger(__name__)

# Default weights for hybrid routing
DEFAULT_WEIGHTS = {
    "w_sem": 0.4,
    "w_trig": 0.3,
    "w_perf": 0.3,
}

# Default performance values for skills without history
DEFAULT_SUCCESS_RATE = 0.5
DEFAULT_AVG_LATENCY_MS = 1000.0


@dataclass
class SkillInfo:
    """Information about a registered skill."""

    skill_id: str
    name: str
    description: str
    triggers: list[str]
    trigger_type: str  # "semantic", "keyword", "exact"
    dependencies: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    success_rate: float = DEFAULT_SUCCESS_RATE
    avg_latency_ms: float = DEFAULT_AVG_LATENCY_MS
    invocation_count: int = 0


class SkillRegistry:
    """Registry for skill routing with hybrid scoring and performance tracking.

    Usage::

        reg = SkillRegistry()
        reg.register_skill('memory_search', 'Search memories', ['search', 'find'], 'semantic')
        reg.register_skill('create_memory', 'Create memory', ['create', 'add'], 'semantic')

        routes = reg.route_query('search for memories about learning')
        for r in routes:
            print(f"  - {r['skill_id']}: score={r['score']:.2f}")

        # Record outcomes
        reg.update_performance('memory_search', success=True, latency_ms=50.0)
    """

    def __init__(
        self,
        db_name: str = "skill_registry.db",
        weights: dict[str, float] | None = None,
    ) -> None:
        self._db_name: str = db_name
        self._weights: dict[str, float] = weights or DEFAULT_WEIGHTS.copy()
        self._skills: dict[str, SkillInfo] = {}
        self._lock: threading.Lock = threading.Lock()
        self._weights = weights or DEFAULT_WEIGHTS.copy()
        self._skills: dict[str, SkillInfo] = {}
        self._lock = threading.Lock()
        self._init_db()
        self._load_from_db()

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------

    def _init_db(self) -> None:
        """Create tables if they do not exist."""
        db = LearningDB()
        conn = db.get_connection(self._db_name)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS skills (
                skill_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                triggers_json TEXT NOT NULL DEFAULT '[]',
                trigger_type TEXT NOT NULL DEFAULT 'semantic',
                dependencies_json TEXT NOT NULL DEFAULT '[]',
                created_at REAL NOT NULL,
                success_rate REAL NOT NULL DEFAULT 0.5,
                avg_latency_ms REAL NOT NULL DEFAULT 1000.0,
                invocation_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id TEXT NOT NULL,
                success INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                timestamp REAL NOT NULL,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
            );
        """)

    def _load_from_db(self) -> None:
        """Hydrate in-memory skill objects from the database."""
        db = LearningDB()
        conn = db.get_connection(self._db_name)
        rows = conn.execute("SELECT * FROM skills").fetchall()
        for row in rows:
            self._skills[row["skill_id"]] = SkillInfo(
                skill_id=row["skill_id"],
                name=row["name"],
                description=row["description"],
                triggers=json.loads(row["triggers_json"]),
                trigger_type=row["trigger_type"],
                dependencies=json.loads(row["dependencies_json"]),
                created_at=row["created_at"],
                success_rate=row["success_rate"],
                avg_latency_ms=row["avg_latency_ms"],
                invocation_count=row["invocation_count"],
            )

    def _persist_skill(self, skill: SkillInfo) -> None:
        """Upsert a single skill row."""
        db = LearningDB()
        conn = db.get_connection(self._db_name)
        conn.execute(
            """
            INSERT INTO skills (
                skill_id, name, description, triggers_json, trigger_type,
                dependencies_json, created_at, success_rate, avg_latency_ms, invocation_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(skill_id) DO UPDATE SET
                name=excluded.name,
                description=excluded.description,
                triggers_json=excluded.triggers_json,
                trigger_type=excluded.trigger_type,
                dependencies_json=excluded.dependencies_json,
                success_rate=excluded.success_rate,
                avg_latency_ms=excluded.avg_latency_ms,
                invocation_count=excluded.invocation_count
            """,
            (
                skill.skill_id,
                skill.name,
                skill.description,
                json.dumps(skill.triggers),
                skill.trigger_type,
                json.dumps(skill.dependencies),
                skill.created_at,
                skill.success_rate,
                skill.avg_latency_ms,
                skill.invocation_count,
            ),
        )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def register_skill(
        self,
        skill_id: str,
        name: str,
        triggers: list[str],
        trigger_type: str = "semantic",
        description: str = "",
        dependencies: list[str] | None = None,
    ) -> SkillInfo:
        """Register a new skill in the registry.

        Args:
            skill_id: Unique identifier for the skill
            name: Human-readable name
            triggers: List of trigger keywords/phrases
            trigger_type: Type of matching ("semantic", "keyword", "exact")
            description: Optional description
            dependencies: Optional list of skill_ids this depends on

        Returns:
            The registered SkillInfo
        """
        with self._lock:
            if skill_id in self._skills:
                logger.warning(
                    "Skill '%s' already exists, skipping registration", skill_id
                )
                return self._skills[skill_id]

            skill = SkillInfo(
                skill_id=skill_id,
                name=name,
                description=description,
                triggers=triggers,
                trigger_type=trigger_type,
                dependencies=dependencies or [],
            )
            self._skills[skill_id] = skill
        self._persist_skill(skill)
        logger.info("Registered skill '%s' with triggers %s", skill_id, triggers)
        return skill

    def get_skill(self, skill_id: str) -> dict[str, Any] | None:
        """Get skill details as a dictionary.

        Args:
            skill_id: The skill identifier

        Returns:
            Dictionary with skill details, or None if not found
        """
        skill = self._skills.get(skill_id)
        if skill is None:
            return None
        return {
            "skill_id": skill.skill_id,
            "name": skill.name,
            "description": skill.description,
            "triggers": skill.triggers,
            "trigger_type": skill.trigger_type,
            "dependencies": skill.dependencies,
            "success_rate": skill.success_rate,
            "avg_latency_ms": skill.avg_latency_ms,
            "invocation_count": skill.invocation_count,
        }

    def list_skills(self) -> list[dict[str, Any]]:
        """List all registered skills.

        Returns:
            List of skill dictionaries
        """
        with self._lock:
            return [
                {
                    "skill_id": s.skill_id,
                    "name": s.name,
                    "description": s.description,
                    "triggers": s.triggers,
                    "trigger_type": s.trigger_type,
                    "dependencies": s.dependencies,
                    "success_rate": s.success_rate,
                    "avg_latency_ms": s.avg_latency_ms,
                    "invocation_count": s.invocation_count,
                }
                for s in self._skills.values()
            ]

    def route_query(
        self, query: str, context: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Route a query to the best-matching skills using hybrid scoring.

        Score = semantic_similarity * w_sem + trigger_match * w_trig + performance * w_perf

        Args:
            query: The user query string
            context: Optional context dictionary (not currently used)

        Returns:
            List of skill routes sorted by score (highest first), each with:
                - skill_id: The skill identifier
                - score: The hybrid routing score (0-1)
                - match_type: Primary match type ("semantic", "trigger", "performance")
        """
        if not self._skills:
            return []

        query_lower = query.lower()
        query_words = set(query_lower.split())
        results = []

        w_sem = self._weights["w_sem"]
        w_trig = self._weights["w_trig"]
        w_perf = self._weights["w_perf"]

        for skill in self._skills.values():
            # 1. Trigger match score (keyword/phrase matching)
            trigger_score = 0.0
            matched_triggers: list[str] = []
            for trigger in skill.triggers:
                trigger_lower = trigger.lower()
                if trigger_lower in query_lower:
                    # Exact match in query
                    trigger_score = 1.0
                    matched_triggers.append(trigger)
                elif any(
                    word.startswith(trigger_lower) or trigger_lower in word
                    for word in query_words
                ):
                    # Partial match
                    trigger_score = max(trigger_score, 0.5)
                    matched_triggers.append(trigger)

            # 2. Semantic similarity (simple word overlap for now)
            skill_words = set(t.lower() for t in skill.triggers)
            if skill_words:
                overlap = query_words & skill_words
                sem_score = len(overlap) / len(skill_words)
            else:
                sem_score = 0.0

            # 3. Performance score (normalized)
            perf_score = skill.success_rate

            # Combine scores
            total_score = (
                sem_score * w_sem + trigger_score * w_trig + perf_score * w_perf
            )

            # Determine primary match type
            if trigger_score > sem_score and trigger_score > perf_score:
                match_type = "trigger"
            elif sem_score > trigger_score and sem_score > perf_score:
                match_type = "semantic"
            else:
                match_type = "performance"

            results.append(
                {
                    "skill_id": skill.skill_id,
                    "score": round(total_score, 4),
                    "match_type": match_type,
                    "sem_score": round(sem_score, 4),
                    "trigger_score": round(trigger_score, 4),
                    "perf_score": round(perf_score, 4),
                    "matched_triggers": matched_triggers,
                }
            )

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def update_performance(
        self, skill_id: str, success: bool, latency_ms: float
    ) -> None:
        """Update performance metrics for a skill.

        Args:
            skill_id: The skill identifier
            success: Whether the invocation was successful
            latency_ms: Latency in milliseconds
        """
        with self._lock:
            if skill_id not in self._skills:
                logger.warning(
                    "Skill '%s' not found, cannot update performance", skill_id
                )
                return

            skill = self._skills[skill_id]

            # Record performance event
            db = LearningDB()
            conn = db.get_connection(self._db_name)
            conn.execute(
                "INSERT INTO performance (skill_id, success, latency_ms, timestamp) VALUES (?, ?, ?, ?)",
                (skill_id, 1 if success else 0, latency_ms, time.time()),
            )

            # Update skill metrics (running average)
            n = skill.invocation_count + 1
            skill.success_rate = (
                skill.success_rate * skill.invocation_count + (1.0 if success else 0.0)
            ) / n
            skill.avg_latency_ms = (
                (skill.avg_latency_ms * skill.invocation_count) + latency_ms
            ) / n
            skill.invocation_count = n

        # Persist updated metrics
        self._persist_skill(skill)
        logger.debug(
            "Updated performance for '%s': success_rate=%.2f, latency=%.2fms",
            skill_id,
            skill.success_rate,
            skill.avg_latency_ms,
        )


# Singleton instance
_registry: SkillRegistry | None = None
_registry_lock = threading.Lock()


def get_registry() -> SkillRegistry:
    """Get or create the module-level SkillRegistry singleton."""
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = SkillRegistry()
    return _registry

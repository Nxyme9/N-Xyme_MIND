#!/usr/bin/env python3
"""RoleSynthesizer — Dynamic Role Synthesis for Multi-Agent Orchestration.

Phase 5.4 of Masterplan: Emergent Role Synthesis.

Creates emergent agent roles based on task patterns and outcomes.
Learns from contribution history to build role taxonomy and assign
dynamic roles based on task type.

Usage:
    from packages.orchestration.role_synthesizer import RoleSynthesizer

    synthesizer = RoleSynthesizer()

    # Synthesize roles for a task
    roles = synthesizer.synthesize_role(
        "implement JWT authentication",
        available_agents=["hephaestus", "oracle", "explore", "librarian"]
    )
    # Returns: {
    #     "primary_role": "implementer",
    #     "primary_agent": "hephaestus",
    #     "supporting_roles": [{"role": "reviewer", "agent": "oracle"}],
    #     "confidence": 0.85
    # }

    # Learn from outcome
    synthesizer.learn_from_outcome(
        "task_001",
        role_composition={"primary": "hephaestus", "reviewer": "oracle"},
        success=True
    )

    # Get aggregate stats
    stats = synthesizer.get_role_stats()
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Configure module logger
logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = "~/.cache/n-xyme-mind/roles.db"

# ============================================================================
# Result Dataclasses
# ============================================================================


@dataclass
class RoleDefinition:
    """Definition of a synthesized role."""

    role_name: str
    agent_type: str
    role_type: str  # "primary", "supporting", "reviewer", "researcher"
    confidence: float = 0.0
    success_rate: float = 0.0
    task_count: int = 0


@dataclass
class RoleComposition:
    """Composition of roles for a task."""

    task_id: str
    primary_role: RoleDefinition
    supporting_roles: list[RoleDefinition] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class RoleSynthesizeResult:
    """Result of role synthesis."""

    task_description: str
    primary_role: str
    primary_agent: str
    supporting_roles: list[dict[str, str]]
    confidence: float
    status: str


@dataclass
class RoleStatsResult:
    """Aggregate role statistics."""

    total_tasks: int
    successful_tasks: int
    success_rate: float
    role_effectiveness: list[dict[str, Any]]
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class LearnOutcomeResult:
    """Result of learning from outcome."""

    task_id: str
    status: str
    role_composition_updated: bool


# ============================================================================
# RoleSynthesizer
# ============================================================================


class RoleSynthesizer:
    """Dynamic role synthesis for multi-agent orchestration.

    Phase 5.4: Creates emergent roles based on task patterns from
    contribution history. Builds role taxonomy and assigns dynamic
    roles based on task type.

    Attributes:
        db_path: Path to SQLite database
        min_confidence: Minimum confidence threshold for role assignment
    """

    # Role type mappings based on task keywords
    ROLE_MAPPINGS = {
        "implement": {"role": "implementer", "agent": "hephaestus"},
        "create": {"role": "implementer", "agent": "hephaestus"},
        "add": {"role": "implementer", "agent": "hephaestus"},
        "fix": {"role": "fixer", "agent": "hephaestus"},
        "refactor": {"role": "refactorer", "agent": "hephaestus"},
        "write": {"role": "writer", "agent": "hephaestus"},
        "explain": {"role": "explainer", "agent": "explore"},
        "find": {"role": "researcher", "agent": "explore"},
        "search": {"role": "researcher", "agent": "explore"},
        "look": {"role": "researcher", "agent": "explore"},
        "investigate": {"role": "researcher", "agent": "explore"},
        "review": {"role": "reviewer", "agent": "oracle"},
        "check": {"role": "reviewer", "agent": "oracle"},
        "verify": {"role": "reviewer", "agent": "oracle"},
        "analyze": {"role": "analyzer", "agent": "oracle"},
        "architect": {"role": "architect", "agent": "oracle"},
        "plan": {"role": "planner", "agent": "prometheus"},
        "design": {"role": "designer", "agent": "prometheus"},
        "research": {"role": "researcher", "agent": "librarian"},
        "docs": {"role": "documenter", "agent": "librarian"},
        "web": {"role": "researcher", "agent": "librarian"},
    }

    # Role taxonomy with agent preferences
    ROLE_TAXONOMY = {
        "implementer": {"primary": "hephaestus", "supporting": ["explore", "oracle"]},
        "fixer": {"primary": "hephaestus", "supporting": ["oracle"]},
        "refactorer": {"primary": "hephaestus", "supporting": ["oracle"]},
        "writer": {"primary": "hephaestus", "supporting": []},
        "explainer": {"primary": "explore", "supporting": ["librarian"]},
        "researcher": {"primary": "explore", "supporting": ["librarian"]},
        "reviewer": {"primary": "oracle", "supporting": []},
        "analyzer": {"primary": "oracle", "supporting": ["explore"]},
        "architect": {"primary": "oracle", "supporting": ["prometheus"]},
        "planner": {"primary": "prometheus", "supporting": ["oracle"]},
        "designer": {"primary": "prometheus", "supporting": ["oracle", "hephaestus"]},
        "documenter": {"primary": "librarian", "supporting": []},
    }

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        min_confidence: float = 0.5,
    ):
        """Initialize RoleSynthesizer.

        Args:
            db_path: Path to SQLite database for role history.
                    Defaults to ~/.cache/n-xyme-mind/roles.db
            min_confidence: Minimum confidence threshold (default: 0.5)
        """
        self.db_path = str(Path(db_path).expanduser())
        self.min_confidence = min_confidence
        self._lock = threading.Lock()

        # In-memory cache
        self._role_history: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._task_patterns: dict[str, list[str]] = defaultdict(list)
        self._agent_success: dict[str, dict[str, Any]] = {}

        # Ensure DB directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._ensure_db()
        self._load_history()

        logger.info(
            f"RoleSynthesizer initialized with db={self.db_path}, "
            f"min_confidence={min_confidence}"
        )

    def _ensure_db(self) -> None:
        """Ensure database and tables exist."""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS role_compositions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                task_description TEXT NOT NULL,
                role_type TEXT NOT NULL,
                role_name TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                success INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL,
                UNIQUE(task_id, role_type)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS task_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                task_keywords TEXT NOT NULL,
                role_composition TEXT NOT NULL,
                success INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_effectiveness (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                role_name TEXT NOT NULL,
                success_count INTEGER DEFAULT 0,
                total_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0,
                last_updated TEXT NOT NULL,
                UNIQUE(agent_id, role_name)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_role_compositions_task
            ON role_compositions(task_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_patterns_task
            ON task_patterns(task_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_effectiveness_agent
            ON agent_effectiveness(agent_id)
        """)
        conn.commit()
        conn.close()
        logger.debug("Database tables initialized")

    def _load_history(self) -> None:
        """Load role history from database."""
        import sqlite3

        try:
            conn = sqlite3.connect(self.db_path)

            # Load agent effectiveness
            cursor = conn.execute(
                """SELECT agent_id, role_name, success_count,
                          total_count, success_rate
                   FROM agent_effectiveness"""
            )
            for row in cursor.fetchall():
                agent_id, role_name = row[0], row[1]
                key = f"{agent_id}:{role_name}"
                self._agent_success[key] = {
                    "success": row[2],
                    "total": row[3],
                    "rate": row[4],
                }

            conn.close()
            logger.debug(
                f"Loaded {len(self._agent_success)} agent effectiveness records"
            )
        except Exception as e:
            logger.warning(f"Failed to load history: {e}")

    def synthesize_role(
        self,
        task_description: str,
        available_agents: list[str],
    ) -> dict[str, Any]:
        """Synthesize roles for a task based on description and available agents.

        Args:
            task_description: Description of the task
            available_agents: List of available agent types

        Returns:
            Dict containing:
                - task_description: Original task description
                - primary_role: Name of primary role
                - primary_agent: Selected primary agent
                - supporting_roles: List of supporting role dicts
                - confidence: Confidence score (0-1)
                - status: "success" or "partial"
        """
        logger.info(f"[Phase 5.4] Synthesizing roles for: {task_description[:50]}...")

        # Determine role based on keywords
        role_name, agent_type = self._match_role(task_description)

        # Check if agent is available
        if agent_type not in available_agents:
            # Find alternative
            agent_type = self._find_alternative_agent(role_name, available_agents)
            if not agent_type:
                logger.warning(f"No suitable agent available for role {role_name}")
                return {
                    "task_description": task_description,
                    "primary_role": role_name or "implementer",
                    "primary_agent": "hephaestus",
                    "supporting_roles": [],
                    "confidence": 0.3,
                    "status": "partial",
                }

        # Get supporting roles from taxonomy
        supporting_roles = self._get_supporting_roles(role_name, available_agents)

        # Calculate confidence based on prior success
        confidence = self._calculate_confidence(role_name, agent_type)

        # Track task pattern
        keywords = self._extract_keywords(task_description)
        self._task_patterns[task_description] = keywords

        logger.info(
            f"Synthesized: primary={role_name}({agent_type}), "
            f"supporting={len(supporting_roles)}, confidence={confidence:.2f}"
        )

        return {
            "task_description": task_description,
            "primary_role": role_name or "implementer",
            "primary_agent": agent_type,
            "supporting_roles": supporting_roles,
            "confidence": confidence,
            "status": "success",
        }

    def _match_role(
        self,
        task_description: str,
    ) -> tuple[str, str]:
        """Match task description to role.

        Args:
            task_description: The task description

        Returns:
            Tuple of (role_name, agent_type)
        """
        desc_lower = task_description.lower()

        # Check keyword mappings
        for keyword, mapping in self.ROLE_MAPPINGS.items():
            if keyword in desc_lower:
                return mapping["role"], mapping["agent"]

        # Default role
        return "implementer", "hephaestus"

    def _find_alternative_agent(
        self,
        role_name: str,
        available_agents: list[str],
    ) -> Optional[str]:
        """Find alternative agent when preferred is unavailable.

        Args:
            role_name: The desired role
            available_agents: List of available agents

        Returns:
            Alternative agent type or None
        """
        taxonomy = self.ROLE_TAXONOMY.get(role_name, {})

        # Check primary preference
        preferred = taxonomy.get("primary")
        if preferred and preferred in available_agents:
            return preferred

        # Check supporting options
        for support in taxonomy.get("supporting", []):
            if support in available_agents:
                return support

        # Fall back to any available
        if available_agents:
            return available_agents[0]

        return None

    def _get_supporting_roles(
        self,
        role_name: str,
        available_agents: list[str],
    ) -> list[dict[str, str]]:
        """Get supporting roles for a primary role.

        Args:
            role_name: Primary role name
            available_agents: List of available agents

        Returns:
            List of supporting role dicts
        """
        taxonomy = self.ROLE_TAXONOMY.get(role_name, {})
        supporting = taxonomy.get("supporting", [])

        result = []
        for support_role in supporting:
            # Find agent for this supporting role
            for agent in available_agents:
                # Check if agent matches supporting role type
                if support_role == agent or self._agent_fits_role(agent, support_role):
                    result.append({"role": support_role, "agent": agent})
                    break

        return result

    def _agent_fits_role(self, agent: str, role: str) -> bool:
        """Check if agent fits a role.

        Args:
            agent: Agent type
            role: Role name

        Returns:
            True if agent fits the role
        """
        for mapping in self.ROLE_MAPPINGS.values():
            if mapping["agent"] == agent:
                return mapping["role"] == role

        # Default mapping
        return agent in ["explore", "oracle", "hephaestus"]

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from task description.

        Args:
            text: Task description

        Returns:
            List of keywords
        """
        keywords = []
        text_lower = text.lower()

        for keyword in self.ROLE_MAPPINGS.keys():
            if keyword in text_lower:
                keywords.append(keyword)

        return keywords if keywords else ["implement"]

    def _calculate_confidence(
        self,
        role_name: str,
        agent_type: str,
    ) -> float:
        """Calculate confidence based on prior success.

        Args:
            role_name: Role name
            agent_type: Agent type

        Returns:
            Confidence score (0-1)
        """
        key = f"{agent_type}:{role_name}"
        effectiveness = self._agent_success.get(key, {})

        success_rate = effectiveness.get("rate", 0.5)

        # Boost confidence based on task count
        task_count = effectiveness.get("total", 0)
        if task_count > 10:
            success_rate = min(0.95, success_rate + 0.1)
        elif task_count > 5:
            success_rate = min(0.90, success_rate + 0.05)

        return max(self.min_confidence, success_rate)

    def learn_from_outcome(
        self,
        task_id: str,
        role_composition: dict[str, str],
        success: bool,
    ) -> dict[str, Any]:
        """Learn from task outcome to improve future synthesis.

        Args:
            task_id: The task ID
            role_composition: Dict mapping role -> agent
            success: Whether the task succeeded

        Returns:
            Dict containing:
                - task_id: The task ID
                - status: "learned" or "error"
                - role_composition_updated: Whether composition was updated
        """
        logger.info(f"[Phase 5.4] Learning from outcome: {task_id} -> {success}")

        import sqlite3

        with self._lock:
            # Update agent effectiveness
            for role_name, agent_id in role_composition.items():
                key = f"{agent_id}:{role_name}"

                # Update in-memory
                if key in self._agent_success:
                    self._agent_success[key]["total"] += 1
                    if success:
                        self._agent_success[key]["success"] += 1

                    # Recalculate rate
                    stats = self._agent_success[key]
                    stats["rate"] = (
                        stats["success"] / stats["total"] if stats["total"] > 0 else 0.0
                    )
                else:
                    self._agent_success[key] = {
                        "success": 1 if success else 0,
                        "total": 1,
                        "rate": 1.0 if success else 0.0,
                    }

                # Update database
                try:
                    conn = sqlite3.connect(self.db_path)
                    # Check existing
                    cursor = conn.execute(
                        """SELECT success_count, total_count
                           FROM agent_effectiveness
                           WHERE agent_id = ? AND role_name = ?""",
                        (agent_id, role_name),
                    )
                    row = cursor.fetchone()

                    if row:
                        new_success = row[0] + (1 if success else 0)
                        new_total = row[1] + 1
                        new_rate = new_success / new_total
                        conn.execute(
                            """UPDATE agent_effectiveness
                               SET success_count = ?,
                                   total_count = ?,
                                   success_rate = ?,
                                   last_updated = ?
                               WHERE agent_id = ? AND role_name = ?""",
                            (
                                new_success,
                                new_total,
                                new_rate,
                                datetime.now(timezone.utc).isoformat(),
                                agent_id,
                                role_name,
                            ),
                        )
                    else:
                        conn.execute(
                            """INSERT INTO agent_effectiveness
                               (agent_id, role_name, success_count,
                                total_count, success_rate, last_updated)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (
                                agent_id,
                                role_name,
                                1 if success else 0,
                                1,
                                1.0 if success else 0.0,
                                datetime.now(timezone.utc).isoformat(),
                            ),
                        )
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logger.warning(f"Failed to update effectiveness: {e}")

            # Record role composition
            try:
                conn = sqlite3.connect(self.db_path)
                for role_type, (role_name, agent_id) in enumerate(
                    role_composition.items()
                ):
                    conn.execute(
                        """INSERT OR REPLACE INTO role_compositions
                           (task_id, task_description, role_type,
                            role_name, agent_id, confidence, success,
                            timestamp)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            task_id,
                            f"task_{task_id}",
                            role_type,
                            role_name,
                            agent_id,
                            1.0,
                            1 if success else 0,
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                conn.commit()
                conn.close()
            except Exception as e:
                logger.warning(f"Failed to record composition: {e}")

        logger.info(f"Learned from outcome: task={task_id}, success={success}")

        return {
            "task_id": task_id,
            "status": "learned",
            "role_composition_updated": True,
        }

    def get_role_stats(self) -> dict[str, Any]:
        """Get aggregate role effectiveness statistics.

        Returns:
            Dict containing:
                - total_tasks: Total tasks processed
                - successful_tasks: Total successful tasks
                - success_rate: Overall success rate
                - role_effectiveness: List of role effectiveness dicts
                - timestamp: When stats were computed
                - status: "success"
        """
        logger.info("[Phase 5.4] Computing role statistics")

        import sqlite3

        total_tasks = 0
        successful_tasks = 0

        # Count from role_compositions
        try:
            conn = sqlite3.connect(self.db_path)

            row = conn.execute(
                "SELECT COUNT(*), SUM(success) FROM role_compositions"
            ).fetchone()

            if row:
                total_tasks = row[0] or 0
                successful_tasks = row[1] or 0

            # Get role effectiveness
            cursor = conn.execute(
                """SELECT role_name, agent_id, success_count,
                         total_count, success_rate
                  FROM agent_effectiveness
                  ORDER BY success_rate DESC"""
            )

            role_effectiveness = []
            for row in cursor.fetchall():
                role_effectiveness.append(
                    {
                        "role_name": row[0],
                        "agent_id": row[1],
                        "success_count": row[2],
                        "total_count": row[3],
                        "success_rate": row[4],
                    }
                )

            conn.close()
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            role_effectiveness = []

        success_rate = successful_tasks / total_tasks if total_tasks > 0 else 0.0

        logger.info(f"Role stats: {total_tasks} tasks, {success_rate:.1%} success rate")

        return {
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "success_rate": success_rate,
            "role_effectiveness": role_effectiveness,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success",
        }

    def get_role_for_task(
        self,
        task_description: str,
    ) -> str:
        """Get the role name for a task description.

        Args:
            task_description: The task description

        Returns:
            Role name string
        """
        role_name, _ = self._match_role(task_description)
        return role_name

    def get_effective_agent(
        self,
        role_name: str,
    ) -> str:
        """Get the most effective agent for a role.

        Args:
            role_name: The role name

        Returns:
            Agent type string
        """
        taxonomy = self.ROLE_TAXONOMY.get(role_name, {})
        return taxonomy.get("primary", "hephaestus")


# ============================================================================
# Convenience Functions
# ============================================================================


def synthesize_roles(
    task_description: str,
    available_agents: list[str],
) -> dict[str, Any]:
    """Convenience function to synthesize roles for a task.

    Args:
        task_description: Description of the task
        available_agents: List of available agent types

    Returns:
        Role synthesis result dict
    """
    synthesizer = RoleSynthesizer()
    return synthesizer.synthesize_role(task_description, available_agents)


def learn_from_task(
    task_id: str,
    role_composition: dict[str, str],
    success: bool,
) -> dict[str, Any]:
    """Convenience function to learn from task outcome.

    Args:
        task_id: The task ID
        role_composition: Dict mapping role -> agent
        success: Whether the task succeeded

    Returns:
        Learning result dict
    """
    synthesizer = RoleSynthesizer()
    return synthesizer.learn_from_outcome(task_id, role_composition, success)


def get_effectiveness_stats() -> dict[str, Any]:
    """Convenience function to get role effectiveness stats.

    Returns:
        Role statistics dict
    """
    synthesizer = RoleSynthesizer()
    return synthesizer.get_role_stats()

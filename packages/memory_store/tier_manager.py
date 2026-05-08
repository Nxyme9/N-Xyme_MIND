#!/usr/bin/env python3
"""Memory Tier Manager — 3-tier memory system (working/recent/archive).

This module implements a tiered memory system:
- Working: Last 24 hours, high trust, frequently accessed
- Recent: Last 7 days, medium trust
- Archive: Older than 7 days, lower trust, rarely accessed

The tier manager handles:
- Automatic tier assignment based on age
- Trust score updates based on access patterns
- Promotion/demotion between tiers
- Archival and retrieval from archive
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from packages.memory_store.stores.base import SearchResult

logger = logging.getLogger(__name__)

# Tier configuration
WORKING_TTL_HOURS = 24
RECENT_TTL_DAYS = 7

# Trust thresholds
TRUST_WORKING_MIN = 0.7  # Min trust for working tier
TRUST_RECENT_MIN = 0.4  # Min trust for recent tier

# Circuit breaker configuration for fallback paths
FALLBACK_FAILURE_THRESHOLD = 5  # Switch to degraded mode after 5 consecutive failures
FALLBACK_RECOVERY_INTERVAL = 60  # Seconds to wait before retrying failed backends


class FallbackCircuitBreaker:
    """Circuit breaker for fallback paths to prevent infinite retries.

    Tracks consecutive failures per backend and switches to degraded mode
    after threshold is reached, preventing cascade failures.
    """

    def __init__(self, name: str, threshold: int = FALLBACK_FAILURE_THRESHOLD):
        self.name = name
        self.threshold = threshold
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.degraded = False

    def record_failure(self) -> bool:
        """Record a failure and return True if should degrade."""
        import time

        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.threshold:
            self.degraded = True
            logger.warning(
                f"Circuit breaker '{self.name}' triggered - degraded mode activated after {self.failure_count} failures"
            )
            return True
        return False

    def record_success(self) -> bool:
        """Record success and return True if recovered from degraded mode."""
        was_degraded = self.degraded
        self.failure_count = 0
        self.degraded = False

        if was_degraded:
            logger.info(
                f"Circuit breaker '{self.name}' recovered - degraded mode deactivated"
            )
        return was_degraded

    def should_try(self) -> bool:
        """Check if should attempt the fallback."""
        import time

        if not self.degraded:
            return True

        # Check if recovery interval has passed
        if (
            self.last_failure_time
            and (time.time() - self.last_failure_time) > FALLBACK_RECOVERY_INTERVAL
        ):
            logger.info(
                f"Circuit breaker '{self.name}' attempting recovery after timeout"
            )
            self.degraded = False
            self.failure_count = 0
            return True

        return False


# Global circuit breakers for memory backends
_lance_circuit_breaker = FallbackCircuitBreaker(
    "lance_store", FALLBACK_FAILURE_THRESHOLD
)
_relational_circuit_breaker = FallbackCircuitBreaker(
    "relational_store", FALLBACK_FAILURE_THRESHOLD
)

# Default paths
DEFAULT_DB_PATH = ".sisyphus/memory_tiers.db"


@dataclass
class MemoryTier:
    """Represents a memory in the tier system."""

    id: str
    content: str
    created_at: datetime
    last_accessed: datetime
    tier: str  # "working", "recent", "archive"
    trust_score: float = 0.5  # 0.0 to 1.0
    access_count: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class TierConfig:
    """Configuration for tier behavior."""

    working_ttl_hours: int = WORKING_TTL_HOURS
    recent_ttl_days: int = RECENT_TTL_DAYS
    trust_working_min: float = TRUST_WORKING_MIN
    trust_recent_min: float = TRUST_RECENT_MIN

    # Trust decay rates
    trust_decay_per_access: float = 0.05  # Decay each access
    trust_decay_per_day: float = 0.01  # Decay per day not accessed

    # Archival thresholds
    archive_access_count_threshold: int = 3  # Archive if accessed < this in TTL

    # Database path
    db_path: str = DEFAULT_DB_PATH


# Session-aware tier weighting configuration
SESSION_CONTEXT_WEIGHT = 0.3  # Weight for session-based boosting
BRANCH_MEMORY_BOOST = 1.2  # Boost for memories from current session branch
AGENT_SUCCESS_BOOST = 1.1  # Boost for memories from successful agent delegations


class TierManager:
    """Manages 3-tier memory system.

    Tiers:
    - working: Last 24h, high trust (>= 0.7), frequently accessed
    - recent: Last 7 days, medium trust (>= 0.4)
    - archive: Older than 7 days, lower trust, optimized for storage

    Session-Aware Weighting:
    - Detects similar task patterns from session history
    - Boosts branch memories (same session)
    - Boosts successful agent delegation memories

    Usage:
        manager = TierManager()
        manager.add_memory("mem_001", "Important info", metadata={"project": "athena"})

        # Search respects tier weights + session context
        results = manager.search("important info", top_k=5, session_context={"agent": "hephaestus"})

        # Get tier stats
        stats = manager.get_stats()
    """

    def __init__(self, config: Optional[TierConfig] = None):
        self.config = config or TierConfig()
        self._db = None
        self._init_db()
        # Session context cache for session-aware weighting
        self._session_context_cache: Optional[dict] = None
        self._session_history: list[dict] = []

    def _init_db(self) -> None:
        """Initialize tier management database."""
        Path(self.config.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._db = sqlite3.connect(self.config.db_path)
        self._db.row_factory = sqlite3.Row

        # Create tables
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memory_tiers (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                tier TEXT NOT NULL DEFAULT 'working',
                trust_score REAL DEFAULT 0.5,
                access_count INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            )
        """)

        self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at ON memory_tiers(created_at)
        """)

        self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tier ON memory_tiers(tier)
        """)

        # Memory versioning table
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memory_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                change_type TEXT NOT NULL DEFAULT 'update',
                UNIQUE(memory_id, version)
            )
        """)

        self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_version ON memory_versions(memory_id, version)
        """)

        self._db.commit()
        logger.info(f"Tier manager initialized at {self.config.db_path}")

    def add_memory(
        self,
        id: str,
        content: str,
        metadata: Optional[dict] = None,
        tier: str = "working",
    ) -> None:
        """Add a memory to the tier system.

        Args:
            id: Unique memory ID
            content: Memory content
            metadata: Optional metadata dict
            tier: Initial tier (default: working)
        """
        now = datetime.now()

        self._db.execute(
            """
            INSERT OR REPLACE INTO memory_tiers
            (id, content, created_at, last_accessed, tier, trust_score, access_count, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                id,
                content,
                now.isoformat(),
                now.isoformat(),
                tier,
                0.5,  # Default trust
                0,
                json.dumps(metadata or {}),
            ),
        )

        # Store initial version
        self._db.execute(
            """
            INSERT INTO memory_versions (memory_id, version, content, created_at, change_type)
            VALUES (?, 1, ?, ?, 'create')
            """,
            (id, content, now.isoformat()),
        )

        self._db.commit()
        logger.debug(f"Added memory {id} to {tier} tier")

    def update_memory(self, id: str, content: str) -> bool:
        """Update memory content and store delta.

        Args:
            id: Memory ID
            content: New content

        Returns:
            True if updated, False if not found
        """
        now = datetime.now()

        # Get current version number
        cursor = self._db.execute(
            "SELECT MAX(version) as max_ver FROM memory_versions WHERE memory_id = ?",
            (id,),
        )
        row = cursor.fetchone()
        new_version = (row["max_ver"] or 0) + 1

        # Update memory
        self._db.execute(
            "UPDATE memory_tiers SET content = ?, last_accessed = ? WHERE id = ?",
            (content, now.isoformat(), id),
        )

        # Store version delta
        self._db.execute(
            """
            INSERT INTO memory_versions (memory_id, version, content, created_at, change_type)
            VALUES (?, ?, ?, ?, 'update')
            """,
            (id, new_version, content, now.isoformat()),
        )

        self._db.commit()
        logger.debug(f"Updated memory {id} to version {new_version}")
        return True

    def get_version_history(self, memory_id: str) -> list[dict[str, Any]]:
        """Get version history for a memory.

        Args:
            memory_id: Memory ID

        Returns:
            List of version records with version, content, created_at, change_type
        """
        cursor = self._db.execute(
            """
            SELECT version, content, created_at, change_type
            FROM memory_versions
            WHERE memory_id = ?
            ORDER BY version ASC
            """,
            (memory_id,),
        )

        return [
            {
                "version": row["version"],
                "content": row["content"],
                "created_at": row["created_at"],
                "change_type": row["change_type"],
            }
            for row in cursor
        ]

    def get_memory_at_version(self, memory_id: str, version: int) -> Optional[str]:
        """Get memory content at a specific version.

        Args:
            memory_id: Memory ID
            version: Version number

        Returns:
            Content at that version, or None if not found
        """
        cursor = self._db.execute(
            "SELECT content FROM memory_versions WHERE memory_id = ? AND version = ?",
            (memory_id, version),
        )
        row = cursor.fetchone()
        return row["content"] if row else None

    def revert_to_version(self, memory_id: str, version: int) -> bool:
        """Revert memory to a specific version.

        Args:
            memory_id: Memory ID
            version: Version to revert to

        Returns:
            True if successful, False if version not found
        """
        content = self.get_memory_at_version(memory_id, version)
        if content is None:
            return False

        self.update_memory(memory_id, content)
        logger.debug(f"Reverted memory {memory_id} to version {version}")
        return True

    def get_memory(self, id: str) -> Optional[MemoryTier]:
        """Get a memory by ID.

        Args:
            id: Memory ID

        Returns:
            MemoryTier object or None if not found
        """
        cursor = self._db.execute("SELECT * FROM memory_tiers WHERE id = ?", (id,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_tier(row)

    def access_memory(self, id: str) -> Optional[MemoryTier]:
        """Record a memory access and update trust.

        Args:
            id: Memory ID

        Returns:
            Updated MemoryTier or None if not found
        """
        memory = self.get_memory(id)
        if not memory:
            return None

        # Update access count and last accessed
        now = datetime.now()

        # Calculate new trust: boost for access, decay for time
        days_not_accessed = (now - memory.last_accessed).days
        trust_boost = self.config.trust_decay_per_access * 0.5  # Small boost per access
        trust_decay = self.config.trust_decay_per_day * days_not_accessed

        new_trust = min(1.0, max(0.0, memory.trust_score + trust_boost - trust_decay))

        # Determine new tier based on age and trust
        new_tier = self._calculate_tier(memory.created_at, new_trust)

        self._db.execute(
            """
            UPDATE memory_tiers
            SET last_accessed = ?, tier = ?, trust_score = ?, access_count = access_count + 1
            WHERE id = ?
        """,
            (now.isoformat(), new_tier, new_trust, id),
        )

        self._db.commit()

        return self.get_memory(id)

    def _calculate_tier(self, created_at: datetime, trust: float) -> str:
        """Calculate which tier a memory belongs to.

        Args:
            created_at: When memory was created
            trust: Current trust score

        Returns:
            Tier name ("working", "recent", "archive")
        """
        now = datetime.now()
        age_hours = (now - created_at).total_seconds() / 3600

        # Working: < 24h old, high trust
        if (
            age_hours < self.config.working_ttl_hours
            and trust >= self.config.trust_working_min
        ):
            return "working"

        # Recent: < 7 days old, medium trust
        if (
            age_hours < (self.config.recent_ttl_days * 24)
            and trust >= self.config.trust_recent_min
        ):
            return "recent"

        # Archive: everything else
        return "archive"

    def search(
        self,
        query: str,
        top_k: int = 10,
        tiers: Optional[list[str]] = None,
        session_context: Optional[dict] = None,
    ) -> list[SearchResult]:
        """Search memories with tier-weighted scoring + session-aware boost.

        Args:
            query: Search query
            top_k: Max results
            tiers: Optional list of tiers to search (default: all)
            session_context: Optional dict with session metadata for boosting:
                - agent: Current agent name
                - task_type: Type of task
                - branch: Session branch identifier

        Returns:
            List of SearchResult with tier-boosted + session-boosted scores
        """
        # Cache session context for session-aware weighting
        if session_context:
            self._session_context_cache = session_context
            self._session_history.append(session_context)

        # Try LanceDB first, fallback to RelationalStore on failure
        store = None
        use_vector_search = True

        # Check circuit breaker before trying LanceDB
        if not _lance_circuit_breaker.should_try():
            logger.info(
                "LanceDB circuit breaker active - skipping LanceDB, using RelationalStore"
            )
            store = None
            use_vector_search = False
        else:
            try:
                from packages.memory_store.stores.lance_store import get_lance_store

                store = get_lance_store()
                _lance_circuit_breaker.record_success()
            except Exception as e:
                logger.warning(
                    f"LanceDB not available: {e}, falling back to RelationalStore"
                )
                _lance_circuit_breaker.record_failure()
                use_vector_search = False

        if tiers is None:
            tiers = ["working", "recent", "archive"]

        # FIX: Fallback to RelationalStore when LanceDB fails
        if store is None or not use_vector_search:
            # Check circuit breaker before trying relational store
            if not _relational_circuit_breaker.should_try():
                logger.error(
                    "RelationalStore circuit breaker active - no backends available"
                )
                return []

            from packages.memory_store.stores.relational_store import (
                get_relational_store,
            )

            rs = get_relational_store()
            if rs:
                _relational_circuit_breaker.record_success()
                records = rs.search(query, limit=top_k)
                return [
                    SearchResult(
                        id=r.id,
                        content=r.content,
                        score=0.5,  # Default score for non-vector search
                        tier=r.tier,
                        metadata=r.metadata,
                    )
                    for r in records
                ]
            else:
                _relational_circuit_breaker.record_failure()
            logger.error("Neither LanceDB nor RelationalStore available")
            return []

        # Build filter for tiers
        tier_filter = " OR ".join([f"tier = '{t}'" for t in tiers])

        # FIX: Generate embedding from query string first
        try:
            from packages.memory_store.stores.vector_store import embed_text

            query_vector = embed_text(query)
        except Exception as e:
            logger.warning(
                f"Failed to embed query: {e}, falling back to RelationalStore"
            )
            # Record embedding failure for circuit breaker
            if "lance" in str(e).lower() or "connection" in str(e).lower():
                _lance_circuit_breaker.record_failure()

            from packages.memory_store.stores.relational_store import (
                get_relational_store,
            )

            rs = get_relational_store()
            if rs:
                records = rs.search(query, limit=top_k)
                return [
                    SearchResult(
                        id=r.id,
                        content=r.content,
                        score=0.5,
                        tier=r.tier,
                        metadata=r.metadata,
                    )
                    for r in records
                ]
            return []

        # Search LanceDB - get all results first, then filter by tier
        # Note: LanceDB doesn't have tier field, we filter post-retrieval
        results = store.search_by_vector(
            query_vector,
            top_k=top_k * 3,  # Get more for reranking
        )

        # Boost scores based on tier (from tier manager SQLite)
        # Plus session-aware boosting from session context
        tier_boosts = {
            "working": 1.5,
            "recent": 1.0,
            "archive": 0.5,
        }

        boosted_results = []
        session_ctx = self._session_context_cache or {}

        for r in results:
            memory = self.get_memory(r.id)
            if memory:
                # Filter by requested tiers
                if tiers and memory.tier not in tiers:
                    continue

                boost = tier_boosts.get(memory.tier, 1.0)

                # SESSION-AWARE BOOSTING
                # 1. Branch memory boost (same session branch)
                if session_ctx.get("branch") and memory.metadata.get(
                    "branch"
                ) == session_ctx.get("branch"):
                    boost *= BRANCH_MEMORY_BOOST

                # 2. Agent success boost (memories from successful delegations to same agent)
                if session_ctx.get("agent") and memory.metadata.get(
                    "agent"
                ) == session_ctx.get("agent"):
                    if memory.metadata.get("outcome") == "success":
                        boost *= AGENT_SUCCESS_BOOST

                # 3. Task type boost (similar task patterns)
                if session_ctx.get("task_type") and memory.metadata.get(
                    "task_type"
                ) == session_ctx.get("task_type"):
                    boost *= SESSION_CONTEXT_WEIGHT

                boosted_results.append(
                    SearchResult(
                        id=r.id,
                        content=r.content,
                        score=r.score * boost,
                        metadata={
                            **r.metadata,
                            "tier": memory.tier,
                            "trust": memory.trust_score,
                        },
                        source=f"lance:{memory.tier}",
                    )
                )
            else:
                # Unknown memory - still include but without tier boost
                if not tiers or "working" in tiers:  # Default to including unknown
                    boosted_results.append(r)

        # Sort by boosted score and return top_k
        boosted_results.sort(key=lambda x: x.score, reverse=True)
        return boosted_results[:top_k]

    def get_stats(self) -> dict[str, Any]:
        """Get tier statistics.

        Returns:
            Dict with tier counts, trust distributions, etc.
        """
        cursor = self._db.execute("""
            SELECT tier, 
                   COUNT(*) as count,
                   AVG(trust_score) as avg_trust,
                   AVG(access_count) as avg_access
            FROM memory_tiers
            GROUP BY tier
        """)

        stats = {"tiers": {}, "total": 0}

        for row in cursor:
            tier = row["tier"]
            stats["tiers"][tier] = {
                "count": row["count"],
                "avg_trust": row["avg_trust"] or 0.0,
                "avg_access": row["avg_access"] or 0.0,
            }
            stats["total"] += row["count"]

        return stats

    def get_tier_memories(self, tier: str, limit: int = 100) -> list[MemoryTier]:
        """Get all memories in a specific tier.

        Args:
            tier: Tier name
            limit: Max memories to return

        Returns:
            List of MemoryTier objects
        """
        cursor = self._db.execute(
            """
            SELECT * FROM memory_tiers
            WHERE tier = ?
            ORDER BY trust_score DESC, last_accessed DESC
            LIMIT ?
        """,
            (tier, limit),
        )

        return [self._row_to_tier(row) for row in cursor]

    def _row_to_tier(self, row: sqlite3.Row) -> MemoryTier:
        """Convert database row to MemoryTier."""
        return MemoryTier(
            id=row["id"],
            content=row["content"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_accessed=datetime.fromisoformat(row["last_accessed"]),
            tier=row["tier"],
            trust_score=row["trust_score"],
            access_count=row["access_count"],
            metadata=json.loads(row["metadata"]),
        )

    def close(self) -> None:
        """Close database connection."""
        if self._db:
            self._db.close()
            self._db = None


# Convenience function
def get_tier_manager() -> TierManager:
    """Get a TierManager instance."""
    return TierManager()


__all__ = [
    "TierManager",
    "TierConfig",
    "MemoryTier",
    "get_tier_manager",
]

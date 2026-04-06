"""Sleep engine — Memory consolidation during sleep cycles.

Implements the 3-tier consolidation pipeline:
- Journal (every session end): Group episodic memories by topic → generate cluster summaries
- Consolidate (daemon, every 6h): Cross-cluster synthesis → merge overlapping summaries into principles
- Prune (daemon, daily): Mark source memories as archived after consolidation

Based on research from:
- HiMem (arXiv:2601.06377) — hierarchical memory with self-evolution
- FadeMem (arXiv:2601.18642) — biologically-inspired forgetting
"""

from __future__ import annotations

import json
import logging
import time
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConsolidatedMemory:
    """A consolidated/summarized memory."""

    id: str
    kind: str  # summary, principle, insight
    content: str
    source_ids: list[str]  # Original memory IDs
    compression_ratio: float  # len(sources) / 1
    abstraction_level: int  # 1=summary, 2=principle, 3=insight
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_accessed: float = 0.0
    access_count: int = 0


class SleepEngine:
    """Memory consolidation engine that runs during 'sleep' cycles.

    Consolidates raw memories into summaries, principles, and insights.
    Implements the 3-tier pipeline:
    1. Journal: Group by topic → summarize clusters
    2. Consolidate: Cross-cluster synthesis → merge into principles
    3. Prune: Archive source memories after consolidation
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize sleep engine.

        Args:
            db_path: Path to the memory database.
        """
        if db_path is None:
            project_root = Path(__file__).resolve().parents[3]
            db_path = project_root / "context" / "memory" / "mind_from_mind.db"
        self.db_path = db_path
        self._ensure_consolidation_table()

    def _ensure_consolidation_table(self) -> None:
        """Create consolidation tables if they don't exist."""
        if not self.db_path.exists():
            return

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS consolidated_memories (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_ids TEXT NOT NULL,
                    compression_ratio REAL NOT NULL,
                    abstraction_level INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_accessed REAL DEFAULT 0,
                    access_count INTEGER DEFAULT 0
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS consolidation_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phase TEXT NOT NULL,
                    memories_consolidated INTEGER NOT NULL,
                    memories_archived INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    duration_ms REAL NOT NULL
                )"""
            )
            conn.commit()
        finally:
            conn.close()

    def journal_phase(self, hours: int = 24) -> dict[str, Any]:
        """Phase 1: Journal — group recent memories by topic and summarize.

        Args:
            hours: Look back this many hours for memories to consolidate.

        Returns:
            Dict with consolidation stats.
        """
        start = time.time() * 1000

        if not self.db_path.exists():
            return {"phase": "journal", "clusters_found": 0, "summaries_created": 0}

        conn = sqlite3.connect(str(self.db_path))
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

            cursor = conn.execute(
                "SELECT id, content, kind, scope FROM memories WHERE created_at > ? ORDER BY kind",
                (cutoff,),
            )
            rows = cursor.fetchall()

            # Group by kind (topic cluster)
            clusters: dict[str, list[tuple[str, str, str]]] = {}
            for mem_id, content, kind, scope in rows:
                cluster_key = kind or "uncategorized"
                if cluster_key not in clusters:
                    clusters[cluster_key] = []
                clusters[cluster_key].append((mem_id, content, scope))

            # Create summaries for clusters with ≥3 memories
            summaries_created = 0
            for cluster_key, memories in clusters.items():
                if len(memories) < 3:
                    continue

                source_ids = [m[0] for m in memories]
                contents = [m[1] for m in memories]
                summary = (
                    f"[Summary of {len(memories)} {cluster_key} memories]\n"
                    + "\n".join(f"- {c[:100]}" for c in contents[:10])
                )

                summary_id = f"summary_{cluster_key}_{int(time.time())}"
                conn.execute(
                    """INSERT OR REPLACE INTO consolidated_memories
                    (id, kind, content, source_ids, compression_ratio, abstraction_level, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        summary_id,
                        "summary",
                        summary,
                        json.dumps(source_ids),
                        len(memories),
                        1,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                summaries_created += 1

            elapsed = time.time() * 1000 - start

            conn.execute(
                """INSERT INTO consolidation_log
                (phase, memories_consolidated, memories_archived, started_at, completed_at, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    "journal",
                    len(rows),
                    0,
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                    elapsed,
                ),
            )
            conn.commit()

            return {
                "phase": "journal",
                "clusters_found": len(clusters),
                "summaries_created": summaries_created,
                "total_memories_processed": len(rows),
                "duration_ms": elapsed,
            }

        finally:
            conn.close()

    def consolidate_phase(self) -> dict[str, Any]:
        """Phase 2: Consolidate — merge overlapping summaries into principles.

        Returns:
            Dict with consolidation stats.
        """
        start = time.time() * 1000

        if not self.db_path.exists():
            return {"phase": "consolidate", "principles_created": 0}

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                "SELECT id, content, source_ids FROM consolidated_memories WHERE kind = 'summary'"
            )
            summaries = cursor.fetchall()

            principles_created = 0
            processed = set()

            for i, (sum_id, content, source_ids) in enumerate(summaries):
                if sum_id in processed:
                    continue

                overlapping = []
                for j, (other_id, other_content, other_sources) in enumerate(summaries):
                    if i == j or other_id in processed:
                        continue

                    words1 = set(content.lower().split())
                    words2 = set(other_content.lower().split())
                    overlap = len(words1 & words2) / max(len(words1), len(words2))

                    if overlap > 0.3:
                        overlapping.append((other_id, other_content, other_sources))

                if overlapping:
                    all_sources = json.loads(source_ids)
                    for _, _, other_sources in overlapping:
                        all_sources.extend(json.loads(other_sources))

                    principle_content = (
                        f"[Principle derived from {len(all_sources)} memories]\n"
                    )
                    principle_content += content[:200] + "\n"
                    for _, other_content, _ in overlapping:
                        principle_content += other_content[:200] + "\n"

                    principle_id = f"principle_{int(time.time())}_{principles_created}"
                    conn.execute(
                        """INSERT OR REPLACE INTO consolidated_memories
                        (id, kind, content, source_ids, compression_ratio, abstraction_level, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            principle_id,
                            "principle",
                            principle_content,
                            json.dumps(all_sources),
                            len(all_sources),
                            2,
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                    principles_created += 1
                    processed.add(sum_id)
                    for oid, _, _ in overlapping:
                        processed.add(oid)

            elapsed = time.time() * 1000 - start

            conn.execute(
                """INSERT INTO consolidation_log
                (phase, memories_consolidated, memories_archived, started_at, completed_at, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    "consolidate",
                    len(processed),
                    0,
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                    elapsed,
                ),
            )
            conn.commit()

            return {
                "phase": "consolidate",
                "principles_created": principles_created,
                "summaries_processed": len(processed),
                "duration_ms": elapsed,
            }

        finally:
            conn.close()

    def prune_phase(self, days_old: int = 7) -> dict[str, Any]:
        """Phase 3: Prune — archive source memories after consolidation.

        Args:
            days_old: Only archive consolidations older than this.

        Returns:
            Dict with pruning stats.
        """
        start = time.time() * 1000

        if not self.db_path.exists():
            return {"phase": "prune", "memories_archived": 0}

        conn = sqlite3.connect(str(self.db_path))
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days_old)).isoformat()

            cursor = conn.execute(
                "SELECT source_ids FROM consolidated_memories WHERE created_at < ?",
                (cutoff,),
            )
            rows = cursor.fetchall()

            archived = 0
            for (source_ids_json,) in rows:
                source_ids = json.loads(source_ids_json)
                for source_id in source_ids:
                    cursor = conn.execute(
                        "UPDATE memories SET tier = 'archived' WHERE id = ?",
                        (source_id,),
                    )
                    archived += cursor.rowcount

            conn.commit()

            elapsed = time.time() * 1000 - start

            conn.execute(
                """INSERT INTO consolidation_log
                (phase, memories_consolidated, memories_archived, started_at, completed_at, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    "prune",
                    0,
                    archived,
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                    elapsed,
                ),
            )
            conn.commit()

            return {
                "phase": "prune",
                "memories_archived": archived,
                "duration_ms": elapsed,
            }

        finally:
            conn.close()

    def run_full_cycle(self) -> dict[str, Any]:
        """Run all 3 phases of the consolidation cycle."""
        return {
            "journal": self.journal_phase(),
            "consolidate": self.consolidate_phase(),
            "prune": self.prune_phase(),
        }

    def get_consolidation_stats(self) -> dict[str, Any]:
        """Get consolidation statistics."""
        if not self.db_path.exists():
            return {"total_consolidated": 0, "total_archived": 0}

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                "SELECT kind, COUNT(*) FROM consolidated_memories GROUP BY kind"
            )
            by_kind = dict(cursor.fetchall())

            cursor = conn.execute("SELECT SUM(memories_archived) FROM consolidation_log")
            total_archived = cursor.fetchone()[0] or 0

            cursor = conn.execute("SELECT COUNT(*) FROM consolidation_log")
            total_cycles = cursor.fetchone()[0]

            return {
                "total_consolidated": sum(by_kind.values()),
                "by_kind": by_kind,
                "total_archived": total_archived,
                "total_cycles": total_cycles,
            }
        finally:
            conn.close()


# Global singleton
_sleep_engine = SleepEngine()


def consolidate_memories() -> dict[str, Any]:
    """Convenience function to run full consolidation cycle."""
    return _sleep_engine.run_full_cycle()
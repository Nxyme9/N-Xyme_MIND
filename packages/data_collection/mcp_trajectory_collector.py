#!/usr/bin/env python3
"""MCP Trajectory Collector — TOUCAN-Style Data Collection.

Collects MCP tool call trajectories for training data generation and pattern analysis.
Tracks: tool_name, args, result, timestamp, duration_ms per task.
Aggregates patterns and extracts common tool sequences.

Features:
- Real-time trajectory collection during agent execution
- Pattern aggregation across tasks
- Common sequence extraction (e.g., [grep → read → edit] = "code modification")
- SQLite storage for training data generation
- Integration with packages.nx_brain_mcp.log_tool_sequence when available
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class ToolCall:
    """Single tool call within a trajectory."""

    tool_name: str
    args: dict[str, Any] = field(default_factory=dict)
    result: Optional[dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class Trajectory:
    """Complete trajectory for a single task."""

    task_id: str
    task_description: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    outcome: str = "pending"  # "pending", "success", "failed", "partial"
    total_duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_sequence(self) -> list[dict[str, Any]]:
        """Convert to sequence format for pattern analysis."""
        return [
            {
                "tool": tc.tool_name,
                "args": tc.args,
                "duration_ms": tc.duration_ms,
            }
            for tc in self.tool_calls
        ]


class MCPTrajectoryCollector:
    """Collects and analyzes MCP tool call trajectories."""

    def __init__(self, db_path: str = ".sisyphus/trajectories.db"):
        self.db_path = db_path
        self._current_trajectories: dict[str, Trajectory] = {}
        self._nx_brain_available = self._check_nx_brain()
        self._ensure_db()

    def _check_nx_brain(self) -> bool:
        """Check if nx_brain_mcp is available."""
        try:
            from packages.brain_mcp.namespaces.fingerprint import log_tool_sequence

            return True
        except ImportError:
            return False

    def _ensure_db(self):
        """Ensure database and tables exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS trajectories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL UNIQUE,
                task_description TEXT,
                sequence_json TEXT NOT NULL,
                outcome TEXT NOT NULL,
                total_duration_ms REAL DEFAULT 0.0,
                tool_count INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS tool_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trajectory_id INTEGER NOT NULL,
                tool_name TEXT NOT NULL,
                args_json TEXT DEFAULT '{}',
                result_json TEXT,
                duration_ms REAL DEFAULT 0.0,
                error TEXT,
                call_order INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (trajectory_id) REFERENCES trajectories(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS sequence_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_hash TEXT NOT NULL UNIQUE,
                tool_sequence TEXT NOT NULL,
                pattern_label TEXT,
                occurrence_count INTEGER DEFAULT 1,
                avg_duration_ms REAL DEFAULT 0.0,
                success_rate REAL DEFAULT 0.0,
                last_updated TEXT NOT NULL
            )
        """)

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_trajectories_task ON trajectories(task_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_trajectories_outcome ON trajectories(outcome)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tool_calls_trajectory ON tool_calls(trajectory_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tool_calls_name ON tool_calls(tool_name)"
        )

        conn.commit()
        conn.close()

    def start_trajectory(self, task_id: str, task_description: str) -> None:
        """Start tracking a new trajectory."""
        self._current_trajectories[task_id] = Trajectory(
            task_id=task_id,
            task_description=task_description,
        )

    def record_tool_call(
        self,
        task_id: str,
        tool_name: str,
        args: dict[str, Any],
        result: Optional[dict[str, Any]] = None,
        duration_ms: float = 0.0,
        error: Optional[str] = None,
    ) -> None:
        """Record a tool call within a trajectory."""
        if task_id not in self._current_trajectories:
            self.start_trajectory(task_id, "unknown")

        tc = ToolCall(
            tool_name=tool_name,
            args=args,
            result=result,
            duration_ms=duration_ms,
            error=error,
        )
        self._current_trajectories[task_id].tool_calls.append(tc)

    def end_trajectory(self, task_id: str, outcome: str) -> str:
        """End and persist a trajectory."""
        if task_id not in self._current_trajectories:
            return ""

        traj = self._current_trajectories[task_id]
        traj.outcome = outcome
        traj.total_duration_ms = sum(tc.duration_ms for tc in traj.tool_calls)

        self._persist_trajectory(traj)
        self._extract_patterns(traj)

        if self._nx_brain_available:
            self._sync_to_nx_brain(traj)

        del self._current_trajectories[task_id]
        return traj.task_id

    def _persist_trajectory(self, traj: Trajectory) -> None:
        """Persist trajectory to SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """INSERT OR REPLACE INTO trajectories
               (task_id, task_description, sequence_json, outcome, total_duration_ms, tool_count, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                traj.task_id,
                traj.task_description,
                json.dumps(traj.to_sequence()),
                traj.outcome,
                traj.total_duration_ms,
                len(traj.tool_calls),
                traj.timestamp,
            ),
        )
        trajectory_id = cursor.lastrowid

        for i, tc in enumerate(traj.tool_calls):
            cursor.execute(
                """INSERT INTO tool_calls
                   (trajectory_id, tool_name, args_json, result_json, duration_ms, error, call_order, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    trajectory_id,
                    tc.tool_name,
                    json.dumps(tc.args),
                    json.dumps(tc.result) if tc.result else None,
                    tc.duration_ms,
                    tc.error,
                    i,
                    tc.timestamp,
                ),
            )

        conn.commit()
        conn.close()

    def _extract_patterns(self, traj: Trajectory) -> None:
        """Extract and store common sequence patterns."""
        if len(traj.tool_calls) < 2:
            return

        tool_names = [tc.tool_name for tc in traj.tool_calls]
        sequence_str = " → ".join(tool_names)
        pattern_hash = str(hash(sequence_str))

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT occurrence_count, success_rate, avg_duration_ms FROM sequence_patterns WHERE pattern_hash = ?",
            (pattern_hash,),
        )
        existing = cursor.fetchone()

        if existing:
            occ, success_rate, avg_dur = existing
            new_occ = occ + 1
            success = 1.0 if traj.outcome == "success" else 0.0
            new_success = (success_rate * occ + success) / new_occ
            new_dur = (avg_dur * occ + traj.total_duration_ms) / new_occ

            cursor.execute(
                """UPDATE sequence_patterns
                   SET occurrence_count = ?, success_rate = ?, avg_duration_ms = ?, last_updated = ?
                   WHERE pattern_hash = ?""",
                (
                    new_occ,
                    new_success,
                    new_dur,
                    datetime.now().isoformat(),
                    pattern_hash,
                ),
            )
        else:
            label = self._label_pattern(tool_names)
            cursor.execute(
                """INSERT INTO sequence_patterns
                   (pattern_hash, tool_sequence, pattern_label, occurrence_count, success_rate, avg_duration_ms, last_updated)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    pattern_hash,
                    sequence_str,
                    label,
                    1,
                    1.0 if traj.outcome == "success" else 0.0,
                    traj.total_duration_ms,
                    datetime.now().isoformat(),
                ),
            )

        conn.commit()
        conn.close()

    def _label_pattern(self, tool_names: list[str]) -> str:
        """Assign human-readable label to common patterns."""
        seq = tuple(tool_names)

        common_labels = {
            ("grep", "read", "edit", "lsp_diagnostics"): "code modification",
            ("grep", "read", "grep"): "research and verify",
            ("explore", "read"): "code exploration",
            ("glob", "read"): "file discovery",
            ("write", "bash"): "file creation with execution",
            ("read", "edit", "read"): "read-verify-edit cycle",
            ("lsp_diagnostics", "lsp_goto_definition"): "error investigation",
            ("grep", "lsp_find_references"): "symbol analysis",
            ("bash", "read"): "command output analysis",
            ("websearch", "webfetch"): "web research",
        }

        for pattern, label in common_labels.items():
            if seq[: len(pattern)] == pattern:
                return label

        return f"custom ({len(tool_names)}-step)"

    def _sync_to_nx_brain(self, traj: Trajectory) -> None:
        """Sync trajectory to nx_brain_mcp if available."""
        try:
            from packages.brain_mcp.namespaces.fingerprint import log_tool_sequence

            log_tool_sequence(
                task=traj.task_description,
                sequence=traj.to_sequence(),
                outcome=traj.outcome,
                duration_ms=traj.total_duration_ms,
            )
        except Exception:
            pass

    def get_trajectory(self, task_id: str) -> Optional[Trajectory]:
        """Get current active trajectory."""
        return self._current_trajectories.get(task_id)

    def get_patterns(
        self,
        min_occurrences: int = 2,
        sort_by: str = "occurrence_count",
    ) -> list[dict[str, Any]]:
        """Get aggregated sequence patterns."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        valid_sort = ["occurrence_count", "success_rate", "avg_duration_ms"]
        sort_col = sort_by if sort_by in valid_sort else "occurrence_count"

        cursor.execute(
            f"""SELECT * FROM sequence_patterns
                WHERE occurrence_count >= ?
                ORDER BY {sort_col} DESC""",
            (min_occurrences,),
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_tool_statistics(self) -> dict[str, Any]:
        """Get aggregate statistics across all trajectories."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM trajectories")
        total_trajectories = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tool_calls")
        total_calls = cursor.fetchone()[0]

        cursor.execute(
            "SELECT tool_name, COUNT(*) as count FROM tool_calls GROUP BY tool_name ORDER BY count DESC"
        )
        tool_counts = {r[0]: r[1] for r in cursor.fetchall()}

        cursor.execute(
            """SELECT outcome, COUNT(*) as count FROM trajectories
               GROUP BY outcome"""
        )
        outcome_counts = {r[0]: r[1] for r in cursor.fetchall()}

        cursor.execute(
            "SELECT AVG(total_duration_ms) FROM trajectories WHERE outcome = 'success'"
        )
        avg_success_duration = cursor.fetchone()[0] or 0.0

        conn.close()

        return {
            "total_trajectories": total_trajectories,
            "total_tool_calls": total_calls,
            "tool_counts": tool_counts,
            "outcome_counts": outcome_counts,
            "avg_success_duration_ms": round(avg_success_duration, 2),
        }

    def get_sequences_for_training(
        self,
        outcome_filter: Optional[str] = None,
        min_tools: int = 2,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get sequences formatted for training data generation."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM trajectories WHERE tool_count >= ?"
        params = [min_tools]

        if outcome_filter:
            query += " AND outcome = ?"
            params.append(outcome_filter)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        sequences = []
        for row in rows:
            seq = json.loads(row["sequence_json"])
            sequences.append(
                {
                    "task_id": row["task_id"],
                    "task_description": row["task_description"],
                    "sequence": seq,
                    "outcome": row["outcome"],
                    "duration_ms": row["total_duration_ms"],
                    "tool_count": row["tool_count"],
                }
            )

        return sequences


_global_collector: Optional[MCPTrajectoryCollector] = None


def get_collector() -> MCPTrajectoryCollector:
    """Get or create the global trajectory collector."""
    global _global_collector
    if _global_collector is None:
        _global_collector = MCPTrajectoryCollector()
    return _global_collector


# Convenience functions for easy integration


def start_task(task_id: str, task_description: str) -> None:
    """Start tracking a task trajectory."""
    get_collector().start_trajectory(task_id, task_description)


def record_call(
    task_id: str,
    tool_name: str,
    args: dict[str, Any],
    result: Optional[dict[str, Any]] = None,
    duration_ms: float = 0.0,
    error: Optional[str] = None,
) -> None:
    """Record a tool call."""
    get_collector().record_tool_call(
        task_id, tool_name, args, result, duration_ms, error
    )


def end_task(task_id: str, outcome: str) -> str:
    """End and persist a task trajectory."""
    return get_collector().end_trajectory(task_id, outcome)


def get_patterns(min_occurrences: int = 2) -> list[dict[str, Any]]:
    """Get common tool sequence patterns."""
    return get_collector().get_patterns(min_occurrences)


def get_stats() -> dict[str, Any]:
    """Get aggregate statistics."""
    return get_collector().get_tool_statistics()


def get_training_data(
    outcome: Optional[str] = None,
    min_tools: int = 2,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get sequences formatted for training."""
    return get_collector().get_sequences_for_training(outcome, min_tools, limit)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MCP Trajectory Collector")
    parser.add_argument(
        "--db", default=".sisyphus/trajectories.db", help="Database path"
    )
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--patterns", action="store_true", help="Show patterns")
    parser.add_argument(
        "--training-data", action="store_true", help="Show training data sample"
    )
    args = parser.parse_args()

    collector = MCPTrajectoryCollector(db_path=args.db)

    if args.stats:
        stats = collector.get_tool_statistics()
        print(json.dumps(stats, indent=2))
    elif args.patterns:
        patterns = collector.get_patterns()
        print(json.dumps(patterns, indent=2))
    elif args.training_data:
        data = collector.get_sequences_for_training()
        print(json.dumps(data[:5], indent=2))

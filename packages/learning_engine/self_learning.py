"""Self-Learning Engine — Track outcomes, extract patterns, adapt behavior.

Implements a closed-loop learning system that:
  1. Tracks task outcomes with rich metadata
  2. Extracts recurring patterns from success/failure data
  3. Adapts future behavior based on learned patterns
  4. Persists everything to SQLite for cross-session continuity
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

MAX_OUTCOMES = 10000
MAX_PATTERNS = 1000


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class OutcomeStatus(str, Enum):
    """High-level status derived from outcome patterns."""

    LEARNING = "learning"
    STABLE = "stable"
    REGRESSING = "regressing"
    OPTIMIZED = "optimized"


@dataclass
class LearningOutcome:
    """A single recorded outcome from a task execution."""

    task_id: str
    action: str
    success: bool
    reward: float = 0.0
    latency_ms: float = 0.0
    cost: float = 0.0
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict (for JSON / debugging)."""
        return asdict(self)


@dataclass
class ExtractedPattern:
    """A pattern discovered from aggregated outcomes."""

    pattern_id: str
    task: str
    action: str
    success_count: int = 0
    failure_count: int = 0
    avg_reward: float = 0.0
    avg_latency_ms: float = 0.0
    avg_cost: float = 0.0
    context_signatures: list[str] = field(default_factory=list)
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    @property
    def total_trials(self) -> int:
        return self.success_count + self.failure_count

    @property
    def success_rate(self) -> float:
        if self.total_trials == 0:
            return 0.0
        return self.success_count / self.total_trials

    def update(self, outcome: LearningOutcome) -> None:
        """Incorporate a new outcome into this pattern's statistics."""
        n = self.total_trials + 1
        if outcome.success:
            self.success_count += 1
        else:
            self.failure_count += 1
        self.avg_reward = ((self.avg_reward * (n - 1)) + outcome.reward) / n
        self.avg_latency_ms = ((self.avg_latency_ms * (n - 1)) + outcome.latency_ms) / n
        self.avg_cost = ((self.avg_cost * (n - 1)) + outcome.cost) / n
        self.last_seen = time.time()

        sig = _context_signature(outcome.context)
        if sig not in self.context_signatures:
            self.context_signatures.append(sig)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Adaptation:
    """A behavioural change triggered by the learning engine."""

    task_id: str
    old_action: str
    new_action: str
    reason: str
    expected_improvement: float = 0.0
    timestamp: float = field(default_factory=time.time)
    applied: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _context_signature(ctx: dict[str, Any]) -> str:
    """Create a short deterministic signature from a context dict."""
    if not ctx:
        return "empty"
    keys = sorted(ctx.keys())
    return "|".join(f"{k}={_coerce(ctx[k])}" for k in keys)


def _coerce(v: Any) -> str:
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        return v
    return str(type(v).__name__)


# ---------------------------------------------------------------------------
# SelfLearner
# ---------------------------------------------------------------------------


class SelfLearner:
    """Outcome-driven self-learning engine with SQLite persistence.

    Usage::

        learner = SelfLearner(db_path="learning.db")
        learner.record_outcome(
            task_id="code_review",
            action="static_analysis",
            success=True,
            latency_ms=150.0,
            cost=0.02,
        )
        patterns = learner.extract_patterns()
        adaptation = learner.adapt("code_review")
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or ":memory:"
        self._local = threading.local()
        self._shared_conn: sqlite3.Connection | None = None  # For :memory: databases
        self._outcomes: list[LearningOutcome] = []
        self._patterns: dict[str, ExtractedPattern] = {}
        self._adaptations: list[Adaptation] = []
        self._lock = threading.Lock()
        self._init_db()
        self._load_from_db()
        self._db_path = db_path or ":memory:"
        self._local = threading.local()
        self._outcomes: list[LearningOutcome] = []
        self._patterns: dict[str, ExtractedPattern] = {}
        self._adaptations: list[Adaptation] = []
        self._lock = threading.Lock()
        self._init_db()
        self._load_from_db()

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    reward REAL NOT NULL DEFAULT 0.0,
                    latency_ms REAL NOT NULL DEFAULT 0.0,
                    cost REAL NOT NULL DEFAULT 0.0,
                    context_json TEXT NOT NULL DEFAULT '{}',
                    timestamp REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS patterns (
                    pattern_id TEXT PRIMARY KEY,
                    task TEXT NOT NULL,
                    action TEXT NOT NULL,
                    success_count INTEGER NOT NULL DEFAULT 0,
                    failure_count INTEGER NOT NULL DEFAULT 0,
                    avg_reward REAL NOT NULL DEFAULT 0.0,
                    avg_latency_ms REAL NOT NULL DEFAULT 0.0,
                    avg_cost REAL NOT NULL DEFAULT 0.0,
                    context_signatures_json TEXT NOT NULL DEFAULT '[]',
                    first_seen REAL NOT NULL,
                    last_seen REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS adaptations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    old_action TEXT NOT NULL,
                    new_action TEXT NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    expected_improvement REAL NOT NULL DEFAULT 0.0,
                    timestamp REAL NOT NULL,
                    applied INTEGER NOT NULL DEFAULT 1
                );
            """)

    def _connect(self) -> sqlite3.Connection:
        """Get thread-local connection, except for :memory: which uses shared connection."""
        # For in-memory databases, use a shared connection with check_same_thread=False
        if self._db_path == ":memory:":
            if self._shared_conn is None:
                self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._shared_conn.row_factory = sqlite3.Row
            return self._shared_conn
        # For file-based databases, use thread-local connections
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self._db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
        return self._local.conn
        """Get thread-local connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self._db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            if self._db_path != ":memory:":
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
        return self._local.conn

    def _load_from_db(self) -> None:
        """Load persisted data from database into memory."""
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM outcomes ORDER BY timestamp"
                ).fetchall()
                for r in rows:
                    self._outcomes.append(
                        LearningOutcome(
                            task_id=r["task_id"],
                            action=r["action"],
                            success=bool(r["success"]),
                            reward=r["reward"],
                            latency_ms=r["latency_ms"],
                            cost=r["cost"],
                            context=json.loads(r["context_json"]),
                            timestamp=r["timestamp"],
                        )
                    )

                rows = conn.execute("SELECT * FROM patterns").fetchall()
                for r in rows:
                    self._patterns[r["pattern_id"]] = ExtractedPattern(
                        pattern_id=r["pattern_id"],
                        task=r["task"],
                        action=r["action"],
                        success_count=r["success_count"],
                        failure_count=r["failure_count"],
                        avg_reward=r["avg_reward"],
                        avg_latency_ms=r["avg_latency_ms"],
                        avg_cost=r["avg_cost"],
                        context_signatures=json.loads(r["context_signatures_json"]),
                        first_seen=r["first_seen"],
                        last_seen=r["last_seen"],
                    )

                rows = conn.execute(
                    "SELECT * FROM adaptations ORDER BY timestamp"
                ).fetchall()
                for r in rows:
                    self._adaptations.append(
                        Adaptation(
                            task_id=r["task_id"],
                            old_action=r["old_action"],
                            new_action=r["new_action"],
                            reason=r["reason"],
                            expected_improvement=r["expected_improvement"],
                            timestamp=r["timestamp"],
                            applied=bool(r["applied"]),
                        )
                    )

    def _persist_outcome(self, o: LearningOutcome) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO outcomes
                    (task_id, action, success, reward, latency_ms, cost,
                     context_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    o.task_id,
                    o.action,
                    int(o.success),
                    o.reward,
                    o.latency_ms,
                    o.cost,
                    json.dumps(o.context),
                    o.timestamp,
                ),
            )

    def _persist_pattern(self, p: ExtractedPattern) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO patterns
                    (pattern_id, task, action, success_count, failure_count,
                     avg_reward, avg_latency_ms, avg_cost,
                     context_signatures_json, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pattern_id) DO UPDATE SET
                    success_count=excluded.success_count,
                    failure_count=excluded.failure_count,
                    avg_reward=excluded.avg_reward,
                    avg_latency_ms=excluded.avg_latency_ms,
                    avg_cost=excluded.avg_cost,
                    context_signatures_json=excluded.context_signatures_json,
                    last_seen=excluded.last_seen
                """,
                (
                    p.pattern_id,
                    p.task,
                    p.action,
                    p.success_count,
                    p.failure_count,
                    p.avg_reward,
                    p.avg_latency_ms,
                    p.avg_cost,
                    json.dumps(p.context_signatures),
                    p.first_seen,
                    p.last_seen,
                ),
            )

    def _persist_adaptation(self, a: Adaptation) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO adaptations
                    (task_id, old_action, new_action, reason,
                     expected_improvement, timestamp, applied)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    a.task_id,
                    a.old_action,
                    a.new_action,
                    a.reason,
                    a.expected_improvement,
                    a.timestamp,
                    int(a.applied),
                ),
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_outcome(
        self,
        task_id: str,
        action: str,
        success: bool,
        reward: float = 0.0,
        latency_ms: float = 0.0,
        cost: float = 0.0,
        context: dict[str, Any] | None = None,
    ) -> LearningOutcome:
        """Record a single task outcome and update patterns."""
        outcome = LearningOutcome(
            task_id=task_id,
            action=action,
            success=success,
            reward=reward,
            latency_ms=latency_ms,
            cost=cost,
            context=context or {},
        )
        with self._lock:
            self._outcomes.append(outcome)
            if len(self._outcomes) > MAX_OUTCOMES:
                self._outcomes = self._outcomes[-MAX_OUTCOMES:]
        self._persist_outcome(outcome)
        self._update_pattern(outcome)
        logger.debug(
            "Recorded outcome: task=%s action=%s success=%s",
            task_id,
            action,
            success,
        )
        return outcome

    def get_outcomes(
        self,
        task_id: str | None = None,
        success: bool | None = None,
        limit: int = 100,
    ) -> list[LearningOutcome]:
        """Return outcomes, optionally filtered."""
        with self._lock:
            results = list(self._outcomes)
        if task_id is not None:
            results = [o for o in results if o.task_id == task_id]
        if success is not None:
            results = [o for o in results if o.success == success]
        return results[-limit:]

    def outcome_count(
        self,
        task_id: str | None = None,
        success: bool | None = None,
    ) -> int:
        """Return total outcome count, optionally filtered."""
        with self._lock:
            results = list(self._outcomes)
        if task_id is not None:
            results = [o for o in results if o.task_id == task_id]
        if success is not None:
            results = [o for o in results if o.success == success]
        return len(results)

    # ------------------------------------------------------------------
    # Pattern extraction
    # ------------------------------------------------------------------

    def _update_pattern(self, outcome: LearningOutcome) -> None:
        pid = f"{outcome.task_id}:{outcome.action}"
        with self._lock:
            if pid not in self._patterns:
                self._patterns[pid] = ExtractedPattern(
                    pattern_id=pid,
                    task=outcome.task_id,
                    action=outcome.action,
                )
                if len(self._patterns) > MAX_PATTERNS:
                    oldest = min(self._patterns.values(), key=lambda p: p.first_seen)
                    del self._patterns[oldest.pattern_id]
            self._patterns[pid].update(outcome)
        self._persist_pattern(self._patterns[pid])

    def extract_patterns(
        self,
        min_occurrences: int = 1,
        task_id: str | None = None,
    ) -> list[ExtractedPattern]:
        """Return patterns that meet the minimum occurrence threshold."""
        with self._lock:
            patterns = list(self._patterns.values())
        if task_id is not None:
            patterns = [p for p in patterns if p.task == task_id]
        return [p for p in patterns if p.total_trials >= min_occurrences]

    def get_pattern(self, task_id: str, action: str) -> ExtractedPattern | None:
        """Return a specific pattern, or None."""
        with self._lock:
            return self._patterns.get(f"{task_id}:{action}")

    def get_best_action(self, task_id: str) -> str | None:
        """Return the action with the highest success rate for a task."""
        with self._lock:
            task_patterns = [p for p in self._patterns.values() if p.task == task_id]
        if not task_patterns:
            return None
        best = max(task_patterns, key=lambda p: (p.success_rate, p.avg_reward))
        return best.action if best.success_rate > 0 else None

    def get_worst_action(self, task_id: str) -> str | None:
        """Return the action with the lowest success rate for a task."""
        with self._lock:
            task_patterns = [
                p
                for p in self._patterns.values()
                if p.task == task_id and p.total_trials >= 2
            ]
        if not task_patterns:
            return None
        worst = min(task_patterns, key=lambda p: p.success_rate)
        return worst.action

    # ------------------------------------------------------------------
    # Adaptation
    # ------------------------------------------------------------------

    def adapt(
        self,
        task_id: str,
        current_action: str | None = None,
    ) -> Adaptation | None:
        """Determine and record an adaptation for a task."""
        with self._lock:
            task_patterns = [
                p
                for p in self._patterns.values()
                if p.task == task_id and p.total_trials >= 2
            ]
        if not task_patterns:
            logger.info("No patterns to adapt for task '%s'", task_id)
            return None

        best = max(task_patterns, key=lambda p: (p.success_rate, p.avg_reward))

        if current_action is not None:
            current_patterns = [p for p in task_patterns if p.action == current_action]
            current_rate = current_patterns[0].success_rate if current_patterns else 0.0
            if best.success_rate - current_rate < 0.15:
                return None
            old_action = current_action
        else:
            with self._lock:
                old_action = self._last_action(task_id) or ""

        adaptation = Adaptation(
            task_id=task_id,
            old_action=old_action,
            new_action=best.action,
            reason=f"Action '{best.action}' has success_rate={best.success_rate:.2f}",
            expected_improvement=best.success_rate,
        )
        with self._lock:
            self._adaptations.append(adaptation)
        self._persist_adaptation(adaptation)
        return adaptation

    def get_adaptations(
        self, task_id: str | None = None, limit: int = 50
    ) -> list[Adaptation]:
        """Return recorded adaptations, optionally filtered."""
        with self._lock:
            results = list(self._adaptations)
        if task_id is not None:
            results = [a for a in results if a.task_id == task_id]
        return results[-limit:]

    # ------------------------------------------------------------------
    # Status / diagnostics
    # ------------------------------------------------------------------

    def task_status(self, task_id: str) -> dict[str, Any]:
        """Return a status summary for a task."""
        with self._lock:
            outcomes = [o for o in self._outcomes if o.task_id == task_id]
        if not outcomes:
            return {"task_id": task_id, "status": OutcomeStatus.LEARNING.value}

        total = len(outcomes)
        successes = sum(1 for o in outcomes if o.success)
        rate = successes / total

        recent = outcomes[-10:]
        recent_successes = sum(1 for o in recent if o.success)
        recent_rate = recent_successes / len(recent)

        if total < 5:
            status = OutcomeStatus.LEARNING
        elif recent_rate >= rate + 0.1:
            status = OutcomeStatus.OPTIMIZED
        elif recent_rate <= rate - 0.1:
            status = OutcomeStatus.REGRESSING
        else:
            status = OutcomeStatus.STABLE

        return {
            "task_id": task_id,
            "status": status.value,
            "total_outcomes": total,
            "success_rate": round(rate, 4),
            "recent_success_rate": round(recent_rate, 4),
            "avg_latency_ms": round(sum(o.latency_ms for o in outcomes) / total, 2),
            "avg_cost": round(sum(o.cost for o in outcomes) / total, 4),
        }

    def all_task_statuses(self) -> dict[str, dict[str, Any]]:
        """Return status summaries for every tracked task."""
        with self._lock:
            task_ids = {o.task_id for o in self._outcomes}
        return {tid: self.task_status(tid) for tid in sorted(task_ids)}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _last_action(self, task_id: str) -> str | None:
        with self._lock:
            for o in reversed(self._outcomes):
                if o.task_id == task_id:
                    return o.action
        return None

    def clear_outcomes(self, task_id: str | None = None) -> int:
        """Remove outcomes, optionally for a single task. Returns count removed."""
        with self._lock:
            if task_id is None:
                count = len(self._outcomes)
                self._outcomes.clear()
                with self._connect() as conn:
                    conn.execute("DELETE FROM outcomes")
                return count
            before = len(self._outcomes)
            self._outcomes = [o for o in self._outcomes if o.task_id != task_id]
            removed = before - len(self._outcomes)
        with self._connect() as conn:
            conn.execute("DELETE FROM outcomes WHERE task_id = ?", (task_id,))
        return removed

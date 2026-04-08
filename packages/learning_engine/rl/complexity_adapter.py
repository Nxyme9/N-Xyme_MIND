#!/usr/bin/env python3
"""
Task Complexity Extension for Q-Learning

Adds task complexity classification and historical success tracking to Q-Learning:
- Task complexity: simple/medium/complex based on query analysis
- Historical success: weighted success rate based on past agent performance
- Combined score for better routing decisions
"""

import re
from enum import Enum
from typing import Optional


class TaskComplexity(Enum):
    """Task complexity levels."""

    SIMPLE = 1
    MEDIUM = 2
    COMPLEX = 3


class TaskComplexityClassifier:
    """Classifier for determining task complexity."""

    # Simple keywords
    SIMPLE_KEYWORDS = {
        "what is",
        "how to",
        "list",
        "show",
        "get",
        "find",
        "explain",
        "describe",
        "simple",
        "basic",
        "create",
        "count",
        "sum",
        "total",
        "check",
        "verify",
    }

    # Complex patterns
    COMPLEX_PATTERNS = [
        r"\bimplement\b",
        r"\barchitect\b",
        r"\brefactor\b",
        r"\boptimize\b",
        r"\bdebug\b",
        r"\bfix.*bug\b",
        r"\bdesign\b",
        r"\balgorithm\b",
        r"\bperformance\b",
        r"\bmemory\b",
        r"\bconcurrent\b",
        r"\basync\b",
        r"\bdatabase\b",
        r"\bapi\b.*design",
        r"\bsecurity\b",
        r"\brefacto",
        r"\bmigrat",
        r"\bupgrade\b",
    ]

    @classmethod
    def classify(cls, task: str) -> TaskComplexity:
        """Classify task complexity."""
        task_lower = task.lower().strip()
        length = len(task)

        # Simple: short with basic keywords
        if length < 80:
            if any(kw in task_lower for kw in cls.SIMPLE_KEYWORDS):
                return TaskComplexity.SIMPLE

        # Complex: long or complex patterns
        if length > 200:
            return TaskComplexity.COMPLEX

        for pattern in cls.COMPLEX_PATTERNS:
            if re.search(pattern, task_lower):
                return TaskComplexity.COMPLEX

        return TaskComplexity.MEDIUM

    @classmethod
    def get_complexity_score(cls, task: str) -> float:
        """Get numerical complexity score (0.0 to 1.0)."""
        complexity = cls.classify(task)
        return complexity.value / 3.0  # Normalize to 0-1


class HistoricalSuccessTracker:
    """Tracks historical success rates per agent for routing decisions."""

    def __init__(self, db_path: str = ".sisyphus/agent_success.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite for tracking."""
        import sqlite3
        from pathlib import Path

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_success (
                agent TEXT,
                task_complexity TEXT,
                success_count INTEGER,
                failure_count INTEGER,
                avg_latency_ms REAL,
                last_updated TEXT,
                PRIMARY KEY (agent, task_complexity)
            )
        """)
        conn.commit()
        conn.close()

    def record_outcome(
        self, agent: str, complexity: TaskComplexity, success: bool, latency_ms: float
    ):
        """Record agent outcome."""
        import sqlite3
        from datetime import datetime

        conn = sqlite3.connect(self.db_path)
        complexity_str = complexity.name

        # Get current counts
        cur = conn.execute(
            "SELECT success_count, failure_count FROM agent_success "
            "WHERE agent = ? AND task_complexity = ?",
            (agent, complexity_str),
        )
        row = cur.fetchone()

        if row:
            success_count = row[0] + (1 if success else 0)
            failure_count = row[1] + (0 if success else 1)
        else:
            success_count = 1 if success else 0
            failure_count = 0 if success else 1

        conn.execute(
            """
            INSERT OR REPLACE INTO agent_success
            (agent, task_complexity, success_count, failure_count, avg_latency_ms, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                agent,
                complexity_str,
                success_count,
                failure_count,
                latency_ms,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def get_success_rate(self, agent: str, complexity: TaskComplexity) -> float:
        """Get success rate for agent on complexity level."""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        cur = conn.execute(
            "SELECT success_count, failure_count FROM agent_success "
            "WHERE agent = ? AND task_complexity = ?",
            (agent, complexity.name),
        )
        row = cur.fetchone()
        conn.close()

        if not row or (row[0] + row[1]) == 0:
            return 0.5  # Default: neutral

        return row[0] / (row[0] + row[1])

    def get_weighted_success(self, agent: str, task: str) -> float:
        """Get weighted success rate based on task complexity."""
        complexity = TaskComplexityClassifier.classify(task)

        # Base success rate
        base_rate = self.get_success_rate(agent, complexity)

        # Complexity penalty/bonus
        complexity_bonus = (
            complexity.value - 2
        ) * 0.1  # -0.1 for simple, +0.1 for complex

        return max(0.0, min(1.0, base_rate + complexity_bonus))


class ExtendedQLearningAdapter:
    """Adapter that extends Q-Learning with complexity + historical success."""

    def __init__(self):
        self.complexity_classifier = TaskComplexityClassifier()
        self.success_tracker = HistoricalSuccessTracker()

    def get_state_features(self, task: str, context: dict) -> dict:
        """Get extended state features for Q-Learning."""
        complexity = self.complexity_classifier.classify(task)
        complexity_score = self.complexity_classifier.get_complexity_score(task)

        # Estimate tokens from task length
        estimated_tokens = len(task) // 4

        return {
            "task": task,
            "complexity": complexity.name,
            "complexity_score": complexity_score,
            "estimated_tokens": estimated_tokens,
            "has_code": bool(
                re.search(r"(def|class|import|from|const|let|var|func|fn)", task)
            ),
            "has_regex": bool(re.search(r"(regex|pattern|match|search)", task.lower())),
        }

    def get_agent_weight(self, agent: str, task: str) -> float:
        """Get agent weight based on historical success."""
        return self.success_tracker.get_weighted_success(agent, task)

    def record_agent_result(
        self, agent: str, task: str, success: bool, latency_ms: float
    ):
        """Record agent result for future weighting."""
        complexity = self.complexity_classifier.classify(task)
        self.success_tracker.record_outcome(agent, complexity, success, latency_ms)


# Singleton
_adapter: Optional[ExtendedQLearningAdapter] = None


def get_complexity_adapter() -> ExtendedQLearningAdapter:
    """Get singleton adapter."""
    global _adapter
    if _adapter is None:
        _adapter = ExtendedQLearningAdapter()
    return _adapter


def get_task_complexity(task: str) -> TaskComplexity:
    """Quick complexity check."""
    return TaskComplexityClassifier.classify(task)


def get_agent_success_rate(agent: str, task: str) -> float:
    """Get agent success rate for task."""
    adapter = get_complexity_adapter()
    return adapter.get_agent_weight(agent, task)


if __name__ == "__main__":
    # Test
    test_tasks = [
        "what is Python",
        "implement a binary search algorithm",
        "fix the authentication bug in login.py",
        "design a REST API for task management",
    ]

    print("Task Complexity Classification:")
    for task in test_tasks:
        complexity = get_task_complexity(task)
        score = TaskComplexityClassifier.get_complexity_score(task)
        print(f"  {task[:40]}... -> {complexity.name} ({score:.2f})")

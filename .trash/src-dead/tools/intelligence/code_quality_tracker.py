"""Code Quality Tracker — Uses learning system to track and mitigate vibecoding pitfalls.

This module extends the existing learning system to track code quality metrics,
detect anti-patterns, and warn about degradation over time.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class CodeQualityEvent:
    """Represents a code quality event."""

    file_path: str
    issue_type: str  # "duplicate_code", "dead_code", "syntax_error", "anti_pattern"
    severity: str  # "low", "medium", "high", "critical"
    description: str
    timestamp: float = field(default_factory=time.time)
    fixed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "issue_type": self.issue_type,
            "severity": self.severity,
            "description": self.description,
            "timestamp": self.timestamp,
            "fixed": self.fixed,
        }


# Known anti-patterns from vibecoding
ANTI_PATTERNS = {
    "duplicate_init": {
        "pattern": re.compile(r"def __init__.*?\n.*?def __init__", re.DOTALL),
        "description": "Duplicate __init__ method",
        "severity": "high",
    },
    "dead_code_after_return": {
        "pattern": re.compile(r"return\s+.*?\n\s+\S+", re.DOTALL),
        "description": "Code after return statement",
        "severity": "medium",
    },
    "unused_import": {
        "pattern": re.compile(r"^import\s+\w+", re.MULTILINE),
        "description": "Import statement found (manual review needed)",
        "severity": "low",
    },
    "global_state": {
        "pattern": re.compile(r"^\w+\s*=\s*[^#\n]+$", re.MULTILINE),
        "description": "Global variable assignment",
        "severity": "medium",
    },
    "bare_except": {
        "pattern": re.compile(r"except\s*:"),
        "description": "Bare except clause",
        "severity": "high",
    },
    "magic_number": {
        "pattern": re.compile(r"if\s+\w+\s*[<>]=?\s*\d{3,}"),
        "description": "Magic number in comparison",
        "severity": "low",
    },
}


class CodeQualityTracker:
    """Tracks code quality metrics and uses learning system to mitigate issues."""

    def __init__(self):
        self._events: list[CodeQualityEvent] = []
        self._self_learner = None
        self._priority_engine = None

    def _get_learner(self):
        """Lazy-load SelfLearner."""
        if self._self_learner is None:
            try:
                from src.learning.self_learning import SelfLearner

                self._self_learner = SelfLearner()
            except Exception:
                pass
        return self._self_learner

    def _get_priority_engine(self):
        """Lazy-load PriorityEngine."""
        if self._priority_engine is None:
            try:
                from src.memory.priority_engine import PriorityEngine
                from pathlib import Path

                db_path = str(
                    Path(__file__).parent.parent.parent
                    / "context/memory/file_registry.db"
                )
                self._priority_engine = PriorityEngine(db_path)
            except Exception:
                pass
        return self._priority_engine

    def scan_file(self, file_path: str) -> list[CodeQualityEvent]:
        """Scan a file for code quality issues.

        Args:
            file_path: Path to the file to scan

        Returns:
            List of code quality events found
        """
        events = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            for pattern_name, pattern_info in ANTI_PATTERNS.items():
                if pattern_info["pattern"].search(content):
                    event = CodeQualityEvent(
                        file_path=file_path,
                        issue_type=pattern_name,
                        severity=pattern_info["severity"],
                        description=pattern_info["description"],
                    )
                    events.append(event)
                    self._record_event(event)

        except Exception:
            pass

        return events

    def scan_directory(
        self, dir_path: str, max_files: int = 100
    ) -> list[CodeQualityEvent]:
        """Scan a directory for code quality issues.

        Args:
            dir_path: Path to the directory to scan
            max_files: Maximum number of files to scan

        Returns:
            List of code quality events found
        """
        events = []
        count = 0
        for root, _, files in os.walk(dir_path):
            for f in files:
                if f.endswith(".py"):
                    file_path = os.path.join(root, f)
                    events.extend(self.scan_file(file_path))
                    count += 1
                    if count >= max_files:
                        return events
        return events

    def _record_event(self, event: CodeQualityEvent) -> None:
        """Record a code quality event in the learning system."""
        self._events.append(event)

        # Record in SelfLearner
        learner = self._get_learner()
        if learner:
            learner.record_outcome(
                task_id="code_quality",
                action=event.issue_type,
                success=False,  # Issue found = not successful
                latency_ms=0,
                context={
                    "file": event.file_path,
                    "severity": event.severity,
                    "description": event.description,
                },
            )

        # Record in PriorityEngine
        pe = self._get_priority_engine()
        if pe:
            pe.track_query_feedback(
                query=f"code_quality:{event.issue_type}",
                result_id=event.file_path,
                source="code_quality_tracker",
                used=False,
                ignored=False,
            )

    def get_quality_stats(self) -> dict[str, Any]:
        """Get code quality statistics.

        Returns:
            Dictionary with quality statistics
        """
        severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        type_counts: dict[str, int] = {}

        for event in self._events:
            severity_counts[event.severity] = severity_counts.get(event.severity, 0) + 1
            type_counts[event.issue_type] = type_counts.get(event.issue_type, 0) + 1

        return {
            "total_events": len(self._events),
            "severity_counts": severity_counts,
            "type_counts": type_counts,
            "recent_events": [e.to_dict() for e in self._events[-10:]],
        }

    def mark_fixed(self, file_path: str, issue_type: str) -> bool:
        """Mark an issue as fixed.

        Args:
            file_path: File path
            issue_type: Issue type

        Returns:
            True if event was found and marked
        """
        for event in self._events:
            if event.file_path == file_path and event.issue_type == issue_type:
                event.fixed = True
                # Record success in learning system
                learner = self._get_learner()
                if learner:
                    learner.record_outcome(
                        task_id="code_quality",
                        action=f"fix_{issue_type}",
                        success=True,
                        latency_ms=0,
                        context={"file": file_path},
                    )
                return True
        return False


# Global tracker
_tracker = CodeQualityTracker()


def get_code_quality_tracker() -> CodeQualityTracker:
    """Get the global code quality tracker.

    Returns:
        Global code quality tracker instance
    """
    return _tracker

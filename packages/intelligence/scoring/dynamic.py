"""Dynamic complexity scoring — adjust L1-L5 scoring based on historical data."""

from __future__ import annotations

import json
import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from packages.intelligence.db import SQLiteStore
    HAS_STATE_DB = True
except ImportError:
    HAS_STATE_DB = False
    SQLiteStore = None

try:
    from packages.intelligence.router.keyword import score_complexity, ScoreResult
    HAS_SCORER = True
except ImportError:
    HAS_SCORER = False

logger = logging.getLogger(__name__)


@dataclass
class DynamicScoreResult:
    """Result from dynamic complexity scoring."""

    level: int
    base_level: int
    adjusted_level: int
    confidence: float
    historical_confidence: float
    reason: str
    adjustment_reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "base_level": self.base_level,
            "adjusted_level": self.adjusted_level,
            "confidence": self.confidence,
            "historical_confidence": self.historical_confidence,
            "reason": self.reason,
            "adjustment_reason": self.adjustment_reason,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class MisclassificationRecord:
    """Record of a complexity misclassification."""

    task_description: str
    predicted_level: int
    actual_level: int
    timestamp: str
    agent_feedback: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_description": self.task_description,
            "predicted_level": self.predicted_level,
            "actual_level": self.actual_level,
            "timestamp": self.timestamp,
            "agent_feedback": self.agent_feedback,
        }


class DynamicComplexityScorer:
    """Adjusts L1-L5 complexity scoring based on historical data and feedback."""

    def __init__(self, db: SQLiteStore | None = None, root_dir: Path | None = None):
        if db is not None:
            self._db = db
        elif HAS_STATE_DB:
            db_path = (root_dir or Path(__file__).parent.parent.parent) / ".sisyphus" / "state.db"
            self._db = SQLiteStore(db_path)
        else:
            self._db = None

        self._lock = threading.Lock()
        self._misclassifications: list[MisclassificationRecord] = []
        self._level_adjustments: dict[str, dict[str, Any]] = {}
        self._keyword_adjustments: dict[str, int] = {}
        self._total_predictions = 0
        self._correct_predictions = 0

    def score(self, task: str) -> DynamicScoreResult:
        """Score task complexity with historical adjustments."""
        if not HAS_SCORER:
            return DynamicScoreResult(
                level=2, base_level=2, adjusted_level=2,
                confidence=0.5, historical_confidence=0.5,
                reason="base scorer unavailable", adjustment_reason="no adjustment",
            )

        base_result = score_complexity(task)
        base_level = base_result.level
        adjustment = self._calculate_adjustment(task, base_level)
        adjusted_level = max(1, min(5, base_level + adjustment))

        historical_confidence = self._get_historical_confidence(adjusted_level)
        combined_confidence = (base_result.confidence * 0.6) + (historical_confidence * 0.4)

        adjustment_reason = (
            f"adjusted by {adjustment:+.1f} based on historical patterns"
            if adjustment != 0
            else "no historical adjustment needed"
        )

        result = DynamicScoreResult(
            level=adjusted_level,
            base_level=base_level,
            adjusted_level=adjusted_level,
            confidence=round(combined_confidence, 2),
            historical_confidence=round(historical_confidence, 2),
            reason=base_result.reason,
            adjustment_reason=adjustment_reason,
            metadata={
                "total_predictions": self._total_predictions,
                "correct_predictions": self._correct_predictions,
                "accuracy": self._get_overall_accuracy(),
            },
        )

        self._total_predictions += 1
        return result

    def record_misclassification(
        self,
        task_description: str,
        predicted_level: int,
        actual_level: int,
        agent_feedback: str = "",
    ) -> None:
        """Record a misclassification for future adjustments."""
        record = MisclassificationRecord(
            task_description=task_description,
            predicted_level=predicted_level,
            actual_level=actual_level,
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent_feedback=agent_feedback,
        )

        with self._lock:
            self._misclassifications.append(record)
            self._update_keyword_adjustments(task_description, predicted_level, actual_level)
            self._update_level_adjustments(predicted_level, actual_level)

        logger.info(
            f"Recorded misclassification: predicted L{predicted_level}, actual L{actual_level}",
            extra={"context": {"task": task_description[:50]}},
        )

    def get_confidence_for_level(self, level: int) -> float:
        """Get confidence score for a specific complexity level based on historical accuracy."""
        return self._get_historical_confidence(level)

    def get_adjustment_history(self) -> list[dict[str, Any]]:
        """Get history of level adjustments."""
        return [m.to_dict() for m in self._misclassifications]

    def get_keyword_adjustments(self) -> dict[str, int]:
        """Get current keyword-based level adjustments."""
        with self._lock:
            return dict(self._keyword_adjustments)

    def get_level_accuracy(self) -> dict[str, float]:
        """Get accuracy per level."""
        if not self._misclassifications:
            return {str(i): 1.0 for i in range(1, 6)}

        level_correct: dict[int, int] = defaultdict(int)
        level_total: dict[int, int] = defaultdict(int)

        for m in self._misclassifications:
            level_total[m.predicted_level] += 1
            if m.predicted_level == m.actual_level:
                level_correct[m.predicted_level] += 1

        return {
            str(level): (level_correct[level] / level_total[level])
            if level_total[level] > 0 else 1.0
            for level in range(1, 6)
        }

    def _calculate_adjustment(self, task: str, base_level: int) -> int:
        """Calculate level adjustment based on historical patterns."""
        adjustment = 0

        with self._lock:
            task_lower = task.lower()
            for keyword, adj in self._keyword_adjustments.items():
                if keyword in task_lower:
                    adjustment += adj

            level_data = self._level_adjustments.get(str(base_level), {})
            if level_data:
                avg_offset = level_data.get("avg_offset", 0)
                if abs(avg_offset) >= 0.5:
                    adjustment += int(round(avg_offset))

        return max(-2, min(2, adjustment))

    def _get_historical_confidence(self, level: int) -> float:
        """Get confidence based on historical accuracy for a level."""
        if not self._misclassifications:
            return 0.5

        relevant = [m for m in self._misclassifications if m.predicted_level == level]
        if not relevant:
            return 0.6

        correct = sum(1 for m in relevant if m.predicted_level == m.actual_level)
        return correct / len(relevant)

    def _get_overall_accuracy(self) -> float:
        """Get overall prediction accuracy."""
        if self._total_predictions == 0:
            return 0.0
        return self._correct_predictions / self._total_predictions

    def _update_keyword_adjustments(
        self, task: str, predicted: int, actual: int
    ) -> None:
        """Update keyword adjustments based on misclassification."""
        offset = actual - predicted
        if offset == 0:
            return

        task_lower = task.lower()
        words = set(task_lower.split())

        for word in words:
            if len(word) < 3:
                continue
            current = self._keyword_adjustments.get(word, 0)
            self._keyword_adjustments[word] = current + (offset * 0.1)

    def _update_level_adjustments(self, predicted: int, actual: int) -> None:
        """Update level adjustment statistics."""
        key = str(predicted)
        offset = actual - predicted

        if key not in self._level_adjustments:
            self._level_adjustments[key] = {
                "count": 0,
                "total_offset": 0,
                "avg_offset": 0,
            }

        data = self._level_adjustments[key]
        data["count"] += 1
        data["total_offset"] += offset
        data["avg_offset"] = data["total_offset"] / data["count"]

    def get_training_stats(self) -> dict[str, Any]:
        """Get statistics about the scorer's training data."""
        with self._lock:
            return {
                "total_misclassifications": len(self._misclassifications),
                "total_predictions": self._total_predictions,
                "correct_predictions": self._correct_predictions,
                "overall_accuracy": self._get_overall_accuracy(),
                "keyword_adjustments_count": len(self._keyword_adjustments),
                "level_adjustments": dict(self._level_adjustments),
                "level_accuracy": self.get_level_accuracy(),
            }

    def reset(self) -> None:
        """Reset all learned adjustments."""
        with self._lock:
            self._misclassifications.clear()
            self._level_adjustments.clear()
            self._keyword_adjustments.clear()
            self._total_predictions = 0
            self._correct_predictions = 0


def score_dynamic(task: str, scorer: DynamicComplexityScorer | None = None) -> DynamicScoreResult:
    """Convenience function for dynamic complexity scoring."""
    if scorer is None:
        scorer = DynamicComplexityScorer()
    return scorer.score(task)


def create_scorer(db: SQLiteStore | None = None) -> DynamicComplexityScorer:
    """Create a new dynamic complexity scorer."""
    return DynamicComplexityScorer(db=db)

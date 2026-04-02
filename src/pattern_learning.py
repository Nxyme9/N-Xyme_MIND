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
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


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


class PatternLearner:
    """Learns user action patterns over time."""

    def __init__(
        self,
        min_occurrences: int = 3,
        sequence_window: float = 30.0,
    ):
        self.min_occurrences = min_occurrences
        self.sequence_window = sequence_window
        self._history: List[ActionRecord] = []
        self._sequences: Dict[str, List[str]] = defaultdict(list)  # action -> next actions
        self._patterns: Dict[str, Pattern] = {}
        logger.info(f"PatternLearner: Initialized (min={min_occurrences})")

    def record(self, action_type: str, context: Optional[Dict[str, Any]] = None) -> None:
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
                        logger.info(
                            f"PatternLearner: Detected '{pattern.name}' (confidence={confidence:.2f})"
                        )

    def get_patterns(self, min_confidence: float = 0.5) -> List[Pattern]:
        """Get learned patterns above confidence threshold."""
        return [p for p in self._patterns.values() if p.confidence >= min_confidence]

    def suggest_next(self, current_action: str) -> Optional[Pattern]:
        """Suggest next action based on current action."""
        matching = [p for p in self._patterns.values() if p.trigger_action == current_action]
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
                for p in sorted(self._patterns.values(), key=lambda p: p.confidence, reverse=True)[
                    :5
                ]
            ],
        }

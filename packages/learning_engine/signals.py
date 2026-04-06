"""N-Xyme MIND — Implicit Feedback Signals Module.

Based on arXiv 2604.00356: Signals taxonomy for implicit feedback learning.
Replaces garbage position-based feedback with real implicit signals.

Signal Categories (3):
- INTERACTION: misalignment, stagnation, disengagement, satisfaction
- EXECUTION: failure, loop
- ENVIRONMENT: exhaustion
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class SignalCategory(Enum):
    """High-level signal category from arXiv 2604.00356."""

    INTERACTION = "interaction"
    EXECUTION = "execution"
    ENVIRONMENT = "environment"


class SignalType(Enum):
    """Specific signal types within each category."""

    MISALIGNMENT = "misalignment"
    STAGNATION = "stagnation"
    DISENGAGEMENT = "disengagement"
    SATISFACTION = "satisfaction"
    FAILURE = "failure"
    LOOP = "loop"
    EXHAUSTION = "exhaustion"


@dataclass
class Signal:
    """Represents a single implicit feedback signal."""

    category: SignalCategory
    type: SignalType
    confidence: float
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0-1, got {self.confidence}")


class SignalDetector:
    """Detects implicit feedback signals from user interactions."""

    def __init__(self, config_path: str | None = None):
        self._config: dict[str, Any] = self._load_config(config_path)

    def _load_config(self, config_path: str | None) -> dict[str, Any]:
        if config_path is None:
            config_path = "src/learning/signals_config.json"

        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file) as f:
                return json.load(f)
        return {
            "categories": {
                "interaction": {
                    "signals": [
                        "misalignment",
                        "stagnation",
                        "disengagement",
                        "satisfaction",
                    ],
                    "weights": {
                        "misalignment": 0.8,
                        "stagnation": 0.6,
                        "disengagement": 0.7,
                        "satisfaction": 0.9,
                    },
                },
                "execution": {
                    "signals": ["failure", "loop"],
                    "weights": {"failure": 0.9, "loop": 0.7},
                },
                "environment": {
                    "signals": ["exhaustion"],
                    "weights": {"exhaustion": 0.8},
                },
            }
        }

    def detect_interaction_signals(
        self, query: str, results: list[dict[str, Any]], response: str
    ) -> list[Signal]:
        signals = []

        if not query or len(query.strip()) < 3:
            signals.append(
                Signal(
                    category=SignalCategory.INTERACTION,
                    type=SignalType.DISENGAGEMENT,
                    confidence=0.9,
                    context={"query": query, "reason": "query_too_short"},
                )
            )

        query_len = len(query.strip()) if query else 0
        response_len = len(response.strip()) if response else 0

        if query_len > 50 and response_len < 20:
            signals.append(
                Signal(
                    category=SignalCategory.INTERACTION,
                    type=SignalType.MISALIGNMENT,
                    confidence=0.8,
                    context={"query_len": query_len, "response_len": response_len},
                )
            )
        elif not results or len(results) == 0:
            signals.append(
                Signal(
                    category=SignalCategory.INTERACTION,
                    type=SignalType.MISALIGNMENT,
                    confidence=0.7,
                    context={"results_count": 0},
                )
            )

        if results and len(results) > 0:
            result_types = set()
            for r in results:
                if "type" in r:
                    result_types.add(r["type"])

            if len(result_types) == 1 and len(results) > 3:
                signals.append(
                    Signal(
                        category=SignalCategory.INTERACTION,
                        type=SignalType.STAGNATION,
                        confidence=0.6,
                        context={
                            "result_types": list(result_types),
                            "count": len(results),
                        },
                    )
                )

        if response_len > 100 and len(results) > 0:
            signals.append(
                Signal(
                    category=SignalCategory.INTERACTION,
                    type=SignalType.SATISFACTION,
                    confidence=0.9,
                    context={
                        "response_len": response_len,
                        "results_count": len(results),
                    },
                )
            )

        return signals

    def detect_execution_signals(
        self, tool_calls: list[dict[str, Any]], errors: list[str]
    ) -> list[Signal]:
        signals = []

        if errors and len(errors) > 0:
            error_count = len(errors)
            confidence = min(0.9, 0.5 + (error_count * 0.2))
            signals.append(
                Signal(
                    category=SignalCategory.EXECUTION,
                    type=SignalType.FAILURE,
                    confidence=confidence,
                    context={"error_count": error_count, "errors": errors[:3]},
                )
            )

        if tool_calls and len(tool_calls) > 2:
            tool_names = [
                tc.get("name", tc.get("tool", "unknown")) for tc in tool_calls
            ]
            if len(set(tool_names)) < len(tool_names) / 2:
                signals.append(
                    Signal(
                        category=SignalCategory.EXECUTION,
                        type=SignalType.LOOP,
                        confidence=0.7,
                        context={
                            "tool_calls": tool_names[-10:],
                            "repetition": len(tool_names) - len(set(tool_names)),
                        },
                    )
                )

        return signals

    def detect_environment_signals(
        self, rate_limits: list[dict[str, Any]], resources: dict[str, Any]
    ) -> list[Signal]:
        signals = []

        if rate_limits and len(rate_limits) > 0:
            for rl in rate_limits:
                remaining = rl.get(
                    "remaining", rl.get("remaining_requests", float("inf"))
                )
                limit = rl.get("limit", rl.get("max_requests", 100))

                if limit > 0 and remaining / limit < 0.1:
                    signals.append(
                        Signal(
                            category=SignalCategory.ENVIRONMENT,
                            type=SignalType.EXHAUSTION,
                            confidence=0.8,
                            context={"rate_limit": rl},
                        )
                    )

        if resources:
            cpu_percent = resources.get("cpu_percent", 0)
            if cpu_percent > 90:
                signals.append(
                    Signal(
                        category=SignalCategory.ENVIRONMENT,
                        type=SignalType.EXHAUSTION,
                        confidence=0.9,
                        context={"resource": "cpu", "usage": cpu_percent},
                    )
                )

            memory_percent = resources.get("memory_percent", 0)
            if memory_percent > 90:
                signals.append(
                    Signal(
                        category=SignalCategory.ENVIRONMENT,
                        type=SignalType.EXHAUSTION,
                        confidence=0.9,
                        context={"resource": "memory", "usage": memory_percent},
                    )
                )

        return signals

    def compute_signal_score(self, signals: list[Signal]) -> float:
        if not signals:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for signal in signals:
            category_name = signal.category.value
            category_config = self._config.get("categories", {}).get(category_name, {})
            category_weights = category_config.get("weights", {})
            weight = category_weights.get(signal.type.value, 0.5)

            weighted_sum += signal.confidence * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return min(1.0, weighted_sum / total_weight)


def get_signal_config() -> dict[str, Any]:
    return {
        "categories": {
            "interaction": {
                "signals": [
                    "misalignment",
                    "stagnation",
                    "disengagement",
                    "satisfaction",
                ],
                "description": "Signals from user-query-response interaction",
            },
            "execution": {
                "signals": ["failure", "loop"],
                "description": "Signals from tool execution and errors",
            },
            "environment": {
                "signals": ["exhaustion"],
                "description": "Signals from resource constraints",
            },
        }
    }


__all__ = [
    "SignalCategory",
    "SignalType",
    "Signal",
    "SignalDetector",
    "get_signal_config",
]

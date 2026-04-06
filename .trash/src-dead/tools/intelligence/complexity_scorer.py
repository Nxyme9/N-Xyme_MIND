"""Complexity Scorer — L1-L5 task complexity estimation.

Ported from bin/complexity-score.sh.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from typing import Any


@dataclass
class ScoreResult:
    """Result of complexity scoring."""

    level: int
    confidence: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "confidence": self.confidence,
            "reason": self.reason,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


LEVEL_KEYWORDS: dict[int, list[str]] = {
    1: [
        "typo",
        "fix.*comma",
        "update.*version",
        "rename.*variable",
        "add.*import",
        "remove.*unused",
    ],
    2: [
        "fix.*bug",
        "add.*feature",
        "create.*file",
        "edit.*config",
        "update.*dependency",
    ],
    3: ["refactor", "multi.file", "middleware", "auth", "endpoint", "route", "handler"],
    4: [
        "architecture",
        "system.*design",
        "build.*from.*scratch",
        "new.*module",
        "new.*service",
    ],
    5: ["rewrite", "migrate", "redesign.*entire", "overhaul", "restructure"],
}

GLOBAL_SCOPE_PATTERN = re.compile(
    r"\b(all|every|entire.*codebase|whole.*system|global)\b", re.IGNORECASE
)


def _extract_first_number(text: str) -> int:
    """Extract the first number from text, or 0 if none found."""
    match = re.search(r"\d+", text)
    return int(match.group()) if match else 0


def _match_keywords(text: str, patterns: list[str]) -> bool:
    """Check if any pattern matches the text."""
    text_lower = text.lower()
    for pattern in patterns:
        if re.search(pattern, text_lower):
            return True
    return False


def score_complexity(task: str) -> ScoreResult:
    """Score task complexity on L1-L5 scale (highest-wins logic).

    Args:
        task: Task description string.

    Returns:
        ScoreResult with level, confidence, and reason.
    """
    if not task:
        return ScoreResult(
            level=2, confidence=0.5, reason="empty input, defaulting to L2"
        )

    levels: list[int] = []
    reasons: list[str] = []

    for level, patterns in LEVEL_KEYWORDS.items():
        if _match_keywords(task, patterns):
            levels.append(level)
            reason_map = {
                1: "trivial keywords",
                2: "single-file change",
                3: "multi-file change",
                4: "system design",
                5: "major refactor",
            }
            reasons.append(reason_map[level])

    file_count = _extract_first_number(task)

    def max_level() -> int:
        return max(levels) if levels else 0

    if file_count > 20:
        if max_level() < 4:
            levels.append(4)
            reasons.append(f"large file count: {file_count} files → L4")
    elif file_count > 10:
        if max_level() < 3:
            levels.append(3)
            reasons.append(f"file count: {file_count} files → L3")
    elif file_count > 5:
        if max_level() < 2:
            levels.append(2)
            reasons.append(f"file count: {file_count} files → L2")

    if GLOBAL_SCOPE_PATTERN.search(task):
        if max_level() < 4:
            levels.append(4)
            reasons.append("global scope")

    if not levels:
        score = 2
        reasons.append("ambiguous input, defaulting to L2")
    else:
        score = max_level()

    if len(reasons) == 1:
        confidence = 0.7
        reason = reasons[0]
    else:
        confidence = 0.9
        reason = ", ".join(reasons)

    return ScoreResult(level=score, confidence=confidence, reason=reason)


class ComplexityScorer:
    """Stateless complexity scorer wrapper."""

    @staticmethod
    def score(task: str) -> ScoreResult:
        return score_complexity(task)


def main() -> None:
    parser = argparse.ArgumentParser(description="L1-L5 task complexity estimation")
    parser.add_argument("task", nargs="?", default="", help="Task description")
    args = parser.parse_args()

    result = score_complexity(args.task)
    print(result.to_json())


if __name__ == "__main__":
    main()

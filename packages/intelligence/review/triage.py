"""Review Triage Override — Security-sensitive path detection.

Ported from bin/review-triage.sh.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any


SENSITIVE_KEYWORDS = [
    "auth",
    "security",
    "crypto",
    "encrypt",
    "decrypt",
    "password",
    "secret",
    "token",
    "payment",
    "billing",
    "credential",
    "api.key",
    "private.key",
]

SENSITIVE_PATH_KEYWORDS = [
    "auth",
    "security",
    "crypto",
    "payments",
    "env",
    "secret",
    "credential",
    "token",
    "password",
    "api_key",
    "private_key",
]


def _check_task_keywords(task: str) -> list[str]:
    """Check task description for sensitive keywords with word boundary matching."""
    reasons: list[str] = []
    for keyword in SENSITIVE_KEYWORDS:
        escaped_pattern = re.escape(keyword.replace(".", r"\."))
        pattern = rf"\b{escaped_pattern}\b"
        if re.search(pattern, task, re.IGNORECASE):
            reasons.append(f"sensitive keyword: {keyword}")
    return reasons


def _check_file_paths(file_paths: list[str]) -> list[str]:
    """Check file paths for sensitive segments."""
    reasons: list[str] = []
    for path in file_paths:
        segments = path.replace("/", " ").replace(".", " ").split()
        for segment in segments:
            segment_lower = segment.lower()
            for keyword in SENSITIVE_PATH_KEYWORDS:
                keyword_clean = keyword.lower().replace(".", "")
                if "_" in keyword_clean:
                    parts = keyword_clean.split("_")
                    if all(part in segment_lower for part in parts):
                        reasons.append(f"sensitive path: {path}")
                        break
                elif re.search(rf"\b{re.escape(keyword_clean)}\b", segment_lower):
                    reasons.append(f"sensitive path: {path}")
                    break
    return reasons


def triage_review(task: str, file_paths: list[str] | None = None) -> dict[str, Any]:
    """Check if task requires Oracle review due to security sensitivity.

    Args:
        task: Task description.
        file_paths: Optional list of file paths the task touches.

    Returns:
        Dict with override decision and reasons.
    """
    if file_paths is None:
        file_paths = []

    reasons: list[str] = []

    reasons.extend(_check_task_keywords(task))
    reasons.extend(_check_file_paths(file_paths))

    override = len(reasons) > 0

    if override:
        reason = ", ".join(reasons)
        return {
            "level": 3,
            "override": True,
            "reason": reason,
            "force_oracle": True,
        }
    return {
        "level": 0,
        "override": False,
        "reason": "no sensitive paths detected",
        "force_oracle": False,
    }


class ReviewTriage:
    """Stateless review triage wrapper."""

    @staticmethod
    def triage(task: str, file_paths: list[str] | None = None) -> dict[str, Any]:
        return triage_review(task, file_paths)


def main() -> None:
    parser = argparse.ArgumentParser(description="Security-sensitive path detection")
    parser.add_argument("task", help="Task description")
    parser.add_argument("file_paths", nargs="*", default=[], help="File paths to check")
    args = parser.parse_args()

    result = triage_review(args.task, args.file_paths)
    print(json.dumps(result))


if __name__ == "__main__":
    main()

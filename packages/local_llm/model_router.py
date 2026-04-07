#!/usr/bin/env python3
"""Model Router - Task-based routing to optimal local LLM models."""

import threading
from typing import Dict, Optional


# Task to Model mapping
TASK_MODEL_MAP: Dict[str, str] = {
    "code_generation": "qwen2.5-coder:7b",
    "reasoning": "qwen2.5:14b",
    "fast_simple": "llama3.2:1b",
    "general": "llama3.2:3b",
}

# Keyword mappings for task classification
TASK_KEYWORDS: Dict[str, list] = {
    "code_generation": [
        "code",
        "function",
        "class",
        "def ",
        "async ",
        "implement",
        "debug",
        "fix bug",
        "refactor",
        "api",
        "endpoint",
        "database",
        "sql",
        "test",
        "bug",
        "error",
        "import",
        "export",
        "module",
        "type",
        "interface",
        "return",
        "void",
    ],
    "reasoning": [
        "why",
        "how does",
        "explain",
        "analyze",
        "compare",
        "evaluate",
        "architecture",
        "design",
        "logic",
        "implications",
        "reason",
        "思考",
        "分析",
        "reasoning",
        "step by step",
        "chain of thought",
    ],
    "fast_simple": [
        "quick",
        "simple",
        "fast",
        "brief",
        "one line",
        "short",
        "list",
        "convert",
        "translate",
        "print",
        "echo",
        "hello",
        "hi ",
        "hey",
    ],
}


class ModelRouter:
    """Thread-safe model router for local LLM selection.

    Routes task descriptions to optimal local models based on
    keyword-based task classification.

    Usage:
        router = ModelRouter()
        model = router.route("implement a function to sort a list")
        # Returns: "qwen2.5-coder:7b"
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._route_count = 0

    def route(self, task_description: str) -> str:
        """Route a task description to the optimal model.

        Args:
            task_description: The task/prompt to route

        Returns:
            Model name string (e.g., "qwen2.5-coder:7b")
        """
        with self._lock:
            task_type = self._classify_task(task_description)
            model = TASK_MODEL_MAP.get(task_type, TASK_MODEL_MAP["general"])
            self._route_count += 1
            return model

    def _classify_task(self, task_description: str) -> str:
        """Classify task type based on keywords.

        Args:
            task_description: The task/prompt to classify

        Returns:
            Task type string: "code_generation", "reasoning", "fast_simple", or "general"
        """
        desc_lower = task_description.lower()

        # Check code_generation keywords first (highest priority for this router)
        code_keywords = TASK_KEYWORDS["code_generation"]
        code_matches = sum(1 for kw in code_keywords if kw in desc_lower)

        # Check reasoning keywords
        reasoning_keywords = TASK_KEYWORDS["reasoning"]
        reasoning_matches = sum(1 for kw in reasoning_keywords if kw in desc_lower)

        # Check fast_simple keywords
        fast_keywords = TASK_KEYWORDS["fast_simple"]
        fast_matches = sum(1 for kw in fast_keywords if kw in desc_lower)

        # Decision logic: highest match wins
        if code_matches >= 2:
            return "code_generation"
        if reasoning_matches >= 2:
            return "reasoning"
        if fast_matches >= 2:
            return "fast_simple"

        # Single keyword matches - check which has higher score
        if code_matches > 0 or reasoning_matches > 0 or fast_matches > 0:
            if code_matches >= reasoning_matches and code_matches >= fast_matches:
                return "code_generation"
            if reasoning_matches >= code_matches and reasoning_matches >= fast_matches:
                return "reasoning"
            if fast_matches > 0:
                return "fast_simple"

        # Default to general
        return "general"

    def get_stats(self) -> Dict:
        """Get router statistics.

        Returns:
            Dict with route count and task type distribution
        """
        with self._lock:
            return {
                "total_routes": self._route_count,
            }

    def get_model_for_task(self, task_type: str) -> Optional[str]:
        """Get model for a specific task type.

        Args:
            task_type: One of "code_generation", "reasoning", "fast_simple", "general"

        Returns:
            Model name or None if invalid task type
        """
        return TASK_MODEL_MAP.get(task_type)


# Module-level convenience instance
_default_router: Optional[ModelRouter] = None


def get_router() -> ModelRouter:
    """Get the default ModelRouter instance (singleton pattern)."""
    global _default_router
    if _default_router is None:
        _default_router = ModelRouter()
    return _default_router


def route(task_description: str) -> str:
    """Convenience function to route a task.

    Args:
        task_description: The task/prompt to route

    Returns:
        Model name string
    """
    return get_router().route(task_description)


if __name__ == "__main__":
    # Test the router
    router = ModelRouter()

    test_tasks = [
        "implement a function to sort a list",
        "why is the system slow",
        "hello world",
        "fix the bug in the API endpoint",
        "analyze the architecture",
        "convert this to JSON",
        "explain how this works",
        "write a quick test",
    ]

    print("=== Model Router Tests ===\n")
    for task in test_tasks:
        model = router.route(task)
        print(f"Task: {task[:40]:<40} -> Model: {model}")

    print(f"\nTotal routes: {router.get_stats()['total_routes']}")

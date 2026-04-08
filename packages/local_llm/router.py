#!/usr/bin/env python3
"""
Multi-Model Router - Classifier-based routing between GGUF models

Routes tasks to optimal model based on complexity:
- Simple/fast: llama3.2:3b (fast, low VRAM)
- Complex: qwen2.5-coder:7b (smart, high VRAM)

Directly integrated with llama-cpp-python (no Ollama HTTP overhead)
"""

import re
from enum import Enum
from typing import Optional


# Model configs for GGUF
class ModelConfig:
    """Model configuration for GGUF inference."""

    def __init__(
        self,
        name: str,
        gguf_path: str,
        n_gpu_layers: int = 35,
        n_ctx: int = 131072,
        n_threads: int = 8,
        description: str = "",
    ):
        self.name = name
        self.gguf_path = gguf_path
        self.n_gpu_layers = n_gpu_layers
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.description = description


# Model registry
MODELS = {
    "fast": ModelConfig(
        name="llama3.2:3b",
        gguf_path="models/nomic-embed-text-v1.5-Q4_K_M.gguf",  # Placeholder - update with actual 3B GGUF
        n_gpu_layers=19,
        n_ctx=131072,
        n_threads=8,
        description="Fast, low VRAM - for simple tasks",
    ),
    "smart": ModelConfig(
        name="qwen2.5-coder:7b",
        gguf_path="models/qwen2.5-coder-7b-q4_k_m.gguf",
        n_gpu_layers=35,
        n_ctx=131072,
        n_threads=8,
        description="Smart, high VRAM - for complex tasks",
    ),
}


class TaskComplexity(Enum):
    """Task complexity classification."""

    SIMPLE = "simple"  # < 80 chars, basic keywords
    MEDIUM = "medium"  # 80-200 chars, some complexity
    COMPLEX = "complex"  # > 200 chars, high complexity


class MultiModelRouter:
    """Classifier-based multi-model router for GGUF inference."""

    # Simple keywords that indicate basic tasks
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
    }

    # Complex indicators
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
    ]

    def __init__(self):
        self._llama_client = None
        self._current_model = None

    def classify(self, query: str) -> TaskComplexity:
        """Classify task complexity based on query content.

        Args:
            query: User query/task description

        Returns:
            TaskComplexity enum
        """
        query_lower = query.lower().strip()
        query_length = len(query)

        # Simple: short queries with basic keywords
        if query_length < 80:
            if any(kw in query_lower for kw in self.SIMPLE_KEYWORDS):
                return TaskComplexity.SIMPLE

        # Complex: long queries or complex patterns
        if query_length > 200:
            return TaskComplexity.COMPLEX

        # Check for complex patterns
        for pattern in self.COMPLEX_PATTERNS:
            if re.search(pattern, query_lower):
                return TaskComplexity.COMPLEX

        # Medium by default
        return TaskComplexity.MEDIUM

    def route(self, query: str) -> ModelConfig:
        """Route query to optimal model.

        Args:
            query: User query/task description

        Returns:
            ModelConfig for the optimal model
        """
        complexity = self.classify(query)

        if complexity == TaskComplexity.SIMPLE:
            return MODELS["fast"]
        elif complexity == TaskComplexity.COMPLEX:
            return MODELS["smart"]
        else:
            # Medium: use smart model for better quality
            return MODELS["smart"]

    def get_model_name(self, query: str) -> str:
        """Get model name for query."""
        return self.route(query).name

    def get_gguf_path(self, query: str) -> str:
        """Get GGUF path for query."""
        return self.route(query).gguf_path

    def get_config(self, query: str) -> ModelConfig:
        """Get full model config for query."""
        return self.route(query)


# Singleton instance
_router: Optional[MultiModelRouter] = None


def get_router() -> MultiModelRouter:
    """Get singleton router instance."""
    global _router
    if _router is None:
        _router = MultiModelRouter()
    return _router


def route_query(query: str) -> str:
    """Quick route function - returns model name."""
    return get_router().get_model_name(query)


# CLI for testing
if __name__ == "__main__":
    import sys

    router = MultiModelRouter()

    test_queries = [
        "what is Python",
        "implement a binary search algorithm with O(log n) complexity",
        "fix the bug in auth.py",
        "explain how lists work",
        "design a REST API for a task management system",
    ]

    print("Multi-Model Router - Query Classification Results")
    print("=" * 60)

    for query in test_queries:
        complexity = router.classify(query)
        model = router.route(query)
        print(f"\nQuery: {query[:50]}...")
        print(f"  Complexity: {complexity.value}")
        print(f"  Model: {model.name}")
        print(f"  GGUF: {model.gguf_path}")

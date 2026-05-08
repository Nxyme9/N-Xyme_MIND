#!/usr/bin/env python3
"""Two-Stage Router - Fast tool calling via complexity-based routing.

This module implements a 2-stage routing system for faster tool calling:
- Stage 1: Small model (~100ms) or keyword rules → tool selection
- Stage 2: Big model (~300ms) → reasoning only
- Stage 3: Rosetta (~200ms) → format execution

Target latency: 300-400ms (vs current 1228ms)

Usage:
    router = TwoStageRouter()
    result = router.route("Find all Python files in src/")

    if result.route_path == "direct":
        # Bypass big model - use tool directly
        pass
    elif result.route_path == "full":
        # Full pipeline: big model → Rosetta
        pass
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

# Import tool categories for tool selection
try:
    from packages.orchestration.tool_categories import (
        TOOL_CATEGORIES,
        CATEGORY_KEYWORDS,
        get_relevant_categories,
    )
except ImportError:
    # Fallback if not available
    TOOL_CATEGORIES = {}
    CATEGORY_KEYWORDS = {}

logger = logging.getLogger("two_stage_router")

# =============================================================================
# Complexity Classification Keywords
# =============================================================================

SIMPLE_KEYWORDS: List[str] = [
    "read",
    "list",
    "find",
    "search",
    "grep",
    "glob",
    "show",
    "get",
    "display",
    "view",
    "check",
    "status",
]

COMPLEX_KEYWORDS: List[str] = [
    "create",
    "implement",
    "build",
    "refactor",
    "design",
    "architect",
    "develop",
    "construct",
    "establish",
    "compose",
    "author",
    "generate",
    "modify",
    "transform",
    "restructure",
    "reorganize",
    "plan",
    "configure",
    "setup",
    "initialize",
]


# =============================================================================
# Route Result Dataclass
# =============================================================================


@dataclass
class RouteResult:
    """Result from the two-stage router.

    Attributes:
        complexity: "simple" or "complex"
        selected_tool: Tool name if determined, None otherwise
        needs_big_model: Whether the big model is needed for reasoning
        route_path: "direct" (simple+clear tool), "full" (big model → Rosetta),
                   or "rosetta_only" (direct to Rosetta)
        confidence: Confidence score (0.0-1.0) for the routing decision
        reasoning: Human-readable explanation of the routing decision
    """

    complexity: str
    selected_tool: Optional[str] = None
    needs_big_model: bool = False
    route_path: str = "full"
    confidence: float = 0.0
    reasoning: str = ""


# =============================================================================
# Two-Stage Router Class
# =============================================================================


class TwoStageRouter:
    """Two-stage router for fast tool calling.

    Implements:
    - Stage 1: Complexity classification (simple vs complex)
    - Stage 2: Tool selection based on category matching
    - Stage 3: Route path determination (direct, full, or rosetta_only)

    Example:
        >>> router = TwoStageRouter()
        >>> result = router.route("Read file config.json")
        >>> print(result.complexity)  # "simple"
        >>> print(result.route_path)  # "direct"
    """

    # L1 Cache for routing decisions (ROI #1.14)
    _route_cache: dict = {}
    _cache_max_size = 200
    _cache_hits = 0
    _cache_misses = 0

    def __init__(self, confidence_threshold: float = 0.7):
        """Initialize the two-stage router.

        Args:
            confidence_threshold: Minimum confidence to consider tool selection
                                   as "clear" for direct routing.
        """
        self._confidence_threshold = confidence_threshold
        logger.info(f"TwoStageRouter initialized (threshold={confidence_threshold})")

    def classify_complexity(self, user_message: str) -> str:
        """Classify message complexity as "simple" or "complex".

        Uses keyword matching to determine complexity:
        - Simple: read, list, find, search, grep, glob, show, get, display
        - Complex: create, implement, build, refactor, design, architect

        Args:
            user_message: The user's input message to classify.

        Returns:
            "simple" or "complex" based on keyword analysis.
        """
        message_lower = user_message.lower()

        # Count matches for each category
        simple_count = sum(1 for kw in SIMPLE_KEYWORDS if kw in message_lower)
        complex_count = sum(1 for kw in COMPLEX_KEYWORDS if kw in message_lower)

        # Decision logic: complex keywords have priority when mixed
        # because they indicate intentional action vs passive retrieval
        if complex_count > simple_count:
            return "complex"
        elif simple_count > 0:
            # Also check for question marks - questions seeking info are simple
            if "?" in message_lower and simple_count > 0:
                return "simple"
            return "simple"
        else:
            # Default to complex if unclear (safer - gives more reasoning)
            return "complex"

    def select_tool(self, user_message: str) -> Optional[str]:
        """Select appropriate tool based on user message.

        Uses the category system from tool_categories.py to map
        user intent to the most appropriate tool.

        Args:
            user_message: The user's input message.

        Returns:
            Tool name string if selection is confident, None otherwise.
        """
        if not CATEGORY_KEYWORDS:
            logger.warning("No CATEGORY_KEYWORDS available, returning None")
            return None

        message_lower = user_message.lower()

        # Get relevant categories using the existing function
        try:
            relevant_categories = get_relevant_categories(user_message)
        except Exception as e:
            logger.warning(f"get_relevant_categories failed: {e}")
            relevant_categories = []

        if not relevant_categories:
            return None

        # Score each category based on keyword matches
        category_scores: dict = {}
        for category in relevant_categories:
            if category not in CATEGORY_KEYWORDS:
                continue

            rules = CATEGORY_KEYWORDS[category]
            positive_matches = sum(
                1 for kw in rules.get("positive", []) if kw in message_lower
            )
            negative_matches = sum(
                1 for kw in rules.get("negative", []) if kw in message_lower
            )

            # Calculate score with negative penalty
            score = positive_matches - (negative_matches * 0.5)
            category_scores[category] = score

        if not category_scores:
            return None

        # Get highest scoring category
        best_category = max(category_scores.items(), key=lambda x: x[1])
        category_name, score = best_category

        # Get tools for this category
        tools = TOOL_CATEGORIES.get(category_name, [])

        if not tools:
            return None

        # Return the first tool in the category (most common/default)
        # Could be enhanced with more sophisticated selection
        selected = tools[0]

        # Calculate confidence based on score
        max_possible_score = len(CATEGORY_KEYWORDS[category_name].get("positive", []))
        confidence = (
            min(1.0, score / max_possible_score) if max_possible_score > 0 else 0.5
        )

        logger.debug(
            f"Selected tool: {selected} (category={category_name}, confidence={confidence:.2f})"
        )

        return selected

    def route(self, user_message: str) -> RouteResult:
        """Perform full routing decision.

        Combines complexity classification and tool selection to determine
        the optimal routing path:

        - "direct": Simple request with clear tool → bypass big model (~100ms)
        - "full": Complex request → full pipeline (~600ms)
        - "rosetta_only": Simple but needs formatting → Rosetta only

        Args:
            user_message: The user's input message.

        Returns:
            RouteResult with routing decision details.
        """
        # ROI #1.14: L1 Cache for routing decisions
        cache_key = user_message.lower().strip()
        if cache_key in TwoStageRouter._route_cache:
            TwoStageRouter._cache_hits += 1
            return TwoStageRouter._route_cache[cache_key]

        TwoStageRouter._cache_misses += 1

        # Stage 1: Classify complexity
        complexity = self.classify_complexity(user_message)
        logger.info(f"Complexity classified: {complexity}")

        # Stage 2: Select tool
        selected_tool = self.select_tool(user_message)

        # Stage 3: Determine route path
        if complexity == "simple" and selected_tool:
            # Simple + clear tool = direct routing (bypass big model)
            route_path = "direct"
            needs_big_model = False
            confidence = 0.9
            reasoning = f"Simple request ({user_message[:30]}...) with clear tool ({selected_tool}) - bypass big model"
        elif complexity == "simple" and not selected_tool:
            # Simple but no clear tool = Rosetta only
            route_path = "rosetta_only"
            needs_big_model = False
            confidence = 0.6
            reasoning = (
                "Simple request but no clear tool identified - use Rosetta only"
            )
        else:
            # Complex = full pipeline
            route_path = "full"
            needs_big_model = True
            confidence = 0.8
            reasoning = (
                f"Complex request ({user_message[:30]}...) - full pipeline required"
            )

        result = RouteResult(
            complexity=complexity,
            selected_tool=selected_tool,
            needs_big_model=needs_big_model,
            route_path=route_path,
            confidence=confidence,
            reasoning=reasoning,
        )

        # Cache the result
        if len(TwoStageRouter._route_cache) < TwoStageRouter._cache_max_size:
            TwoStageRouter._route_cache[cache_key] = result

        logger.info(
            f"Route decision: path={route_path}, complexity={complexity}, "
            f"tool={selected_tool}, needs_big_model={needs_big_model}"
        )

        return result

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": len(self._route_cache),
            "max_size": self._cache_max_size,
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": self._cache_hits / (self._cache_hits + self._cache_misses)
            if (self._cache_hits + self._cache_misses) > 0
            else 0,
        }

    def should_bypass_big_model(self, user_message: str) -> bool:
        """Quick check if request can bypass big model.

        Convenience method for fast path determination.

        Args:
            user_message: The user's input message.

        Returns:
            True if big model can be bypassed, False otherwise.
        """
        result = self.route(user_message)
        return result.route_path in ("direct", "rosetta_only")


# =============================================================================
# Module-Level Convenience Functions
# =============================================================================


def route(user_message: str) -> RouteResult:
    """Convenience function for routing.

    Args:
        user_message: The user's input message.

    Returns:
        RouteResult with routing decision.
    """
    router = TwoStageRouter()
    return router.route(user_message)


def classify_complexity(user_message: str) -> str:
    """Convenience function for complexity classification.

    Args:
        user_message: The user's input message.

    Returns:
        "simple" or "complex".
    """
    router = TwoStageRouter()
    return router.classify_complexity(user_message)


def select_tool(user_message: str) -> Optional[str]:
    """Convenience function for tool selection.

    Args:
        user_message: The user's input message.

    Returns:
        Tool name or None.
    """
    router = TwoStageRouter()
    return router.select_tool(user_message)


# =============================================================================
# Main / Tests
# =============================================================================


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s: %(message)s",
    )

    print("=== Two-Stage Router Test ===\n")

    router = TwoStageRouter()

    # Test cases
    test_messages = [
        # Simple requests
        ("Read the config file", "simple"),
        ("Find all Python files", "simple"),
        ("List the directory contents", "simple"),
        ("Search for function definitions", "simple"),
        ("Show me the git status", "simple"),
        ("What's in this file?", "simple"),
        ("Check the current branch", "simple"),
        # Complex requests
        ("Create a new API endpoint", "complex"),
        ("Implement user authentication", "complex"),
        ("Build a new feature", "complex"),
        ("Refactor the codebase", "complex"),
        ("Design the architecture", "complex"),
        ("Develop a new module", "complex"),
        ("Configure the CI pipeline", "complex"),
    ]

    print("--- Complexity Classification ---")
    passed = 0
    failed = 0
    for msg, expected in test_messages:
        result = router.classify_complexity(msg)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} '{msg}' -> {result} (expected: {expected})")

    print(f"\nComplexity results: {passed} passed, {failed} failed")

    print("\n--- Full Routing ---")
    routing_tests = [
        "Read config.json",
        "Find all test files",
        "Create a new component",
        "Implement auth system",
    ]

    for msg in routing_tests:
        result = router.route(msg)
        print(f"\nMessage: '{msg}'")
        print(f"  Complexity: {result.complexity}")
        print(f"  Selected tool: {result.selected_tool}")
        print(f"  Route path: {result.route_path}")
        print(f"  Needs big model: {result.needs_big_model}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Reasoning: {result.reasoning}")

    print("\n--- Quick Bypass Check ---")
    bypass_tests = [
        "Read file",
        "Find code",
        "Create something",
        "Build feature",
    ]
    for msg in bypass_tests:
        bypass = router.should_bypass_big_model(msg)
        print(f"'{msg}' -> bypass={bypass}")

    print("\n=== Tests Complete ===")
    sys.exit(0 if failed == 0 else 1)

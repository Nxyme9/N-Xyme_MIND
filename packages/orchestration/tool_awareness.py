#!/usr/bin/env python3
"""Tool Awareness System - Hybrid proactive + on-demand tool discovery.

This module implements a hybrid tool awareness system that combines:
- Proactive mode: Automatic tool suggestions when confidence > 80%
- On-demand mode: Model can request tool suggestions when beneficial

Research: "Tool awareness = WHEN not WHAT" - timing is critical.

Usage:
    awareness = ToolAwarenessSystem({"high_confidence_threshold": 0.8})

    # Proactive - called before LLM
    suggestions = awareness.get_suggestions(user_message, context)

    # On-demand - called during reasoning when model needs help
    tools = awareness.on_demand_discover("I need to find files matching pattern")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

# Import existing modules
try:
    from packages.orchestration.tool_categories import (
        TOOL_CATEGORIES,
        CATEGORY_KEYWORDS,
        CATEGORY_DESCRIPTIONS,
        get_relevant_categories,
        get_tools_for_category,
        get_tool_description,
    )
    from packages.orchestration.two_stage_router import TwoStageRouter, RouteResult
except ImportError as e:
    logging.warning(f"Could not import tool_categories/two_stage_router: {e}")
    TOOL_CATEGORIES = {}
    CATEGORY_KEYWORDS = {}
    CATEGORY_DESCRIPTIONS = {}

    def get_relevant_categories(msg: str) -> List[str]:
        return []

    def get_tools_for_category(cat: str) -> List[str]:
        return []

    def get_tool_description(cat: str, tool: str) -> Optional[str]:
        return None

    # Fallback RouteResult for when two_stage_router unavailable
    @dataclass
    class RouteResult:
        complexity: str = "complex"
        selected_tool: Optional[str] = None
        needs_big_model: bool = True
        route_path: str = "full"
        confidence: float = 0.5
        reasoning: str = "Router unavailable"

    class TwoStageRouter:
        def __init__(self, confidence_threshold: float = 0.7):
            pass

        def route(self, msg: str) -> RouteResult:
            return RouteResult()

    from packages.orchestration.two_stage_router import TwoStageRouter, RouteResult
except ImportError as e:
    logging.warning(f"Could not import tool_categories/two_stage_router: {e}")
    TOOL_CATEGORIES = {}
    CATEGORY_KEYWORDS = {}
    CATEGORY_DESCRIPTIONS = {}

    def get_relevant_categories(msg: str) -> List[str]:
        return []

    def get_tools_for_category(cat: str) -> List[str]:
        return []

    def get_tool_description(cat: str, tool: str) -> Optional[str]:
        return None

    class TwoStageRouter:
        def __init__(self, confidence_threshold: float = 0.7):
            pass

        def route(self, msg: str) -> RouteResult:
            return RouteResult(
                complexity="complex",
                selected_tool=None,
                needs_big_model=True,
                route_path="full",
                confidence=0.5,
                reasoning="Router not available",
            )


# Style learner integration (lazy import to avoid circular dependencies)
_style_learner_context = None


def _get_style_context() -> Dict[str, Any]:
    """Get style context from style_learner for tool suggestions."""
    global _style_learner_context
    if _style_learner_context is not None:
        return _style_learner_context

    try:
        from packages.orchestration.style_learner_integration import get_style_context

        _style_learner_context = get_style_context()
        return _style_learner_context
    except ImportError:
        return {"available": False, "style_profile": {}, "recommendations": {}}


logger = logging.getLogger("tool_awareness")

# =============================================================================
# Configuration Constants
# =============================================================================

HIGH_CONFIDENCE = 0.8  # 80% - threshold for proactive injection
DEFAULT_CONFIDENCE = 0.7  # Default threshold for tool selection
MIN_CONFIDENCE = 0.3  # Minimum confidence to include in suggestions

# Default configuration
DEFAULT_CONFIG: Dict[str, Any] = {
    "high_confidence_threshold": HIGH_CONFIDENCE,
    "default_threshold": DEFAULT_CONFIDENCE,
    "max_suggestions": 5,
    "enable_proactive": True,
    "enable_on_demand": True,
    "min_confidence": MIN_CONFIDENCE,
    "include_descriptions": True,
    "reasoning_depth": "brief",  # "brief" or "detailed"
}

# =============================================================================
# Tool Suggestion Dataclass
# =============================================================================


@dataclass
class ToolSuggestion:
    """Represents a tool suggestion with metadata.

    Attributes:
        tool_name: Name of the suggested tool
        category: Category the tool belongs to
        confidence: Confidence score (0.0-1.0)
        reason: Human-readable reason for suggestion
        mode: "proactive" or "on_demand"
    """

    tool_name: str
    category: str
    confidence: float
    reason: str
    mode: str = "proactive"

    def __post_init__(self):
        """Validate and clamp values."""
        self.confidence = max(0.0, min(1.0, self.confidence))
        if self.mode not in ("proactive", "on_demand"):
            self.mode = "on_demand"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tool_name": self.tool_name,
            "category": self.category,
            "confidence": self.confidence,
            "reason": self.reason,
            "mode": self.mode,
        }

    def __str__(self) -> str:
        """Human-readable string."""
        conf_pct = int(self.confidence * 100)
        return f"[{conf_pct}% {self.category}] {self.tool_name}: {self.reason}"


# =============================================================================
# Tool Awareness System Class
# =============================================================================


class ToolAwarenessSystem:
    """Hybrid tool awareness system with proactive + on-demand modes.

    This system determines WHEN to inject tool suggestions based on:
    - Message complexity (via TwoStageRouter)
    - Category relevance (via tool_categories)
    - Confidence scoring

    Proactive Mode:
        - Triggered when confidence > 80%
        - Automatically injects suggestions before LLM call
        - Uses context from TwoStageRouter

    On-Demand Mode:
        - Available for model to call during reasoning
        - Triggered when model detects it might need tools
        - Returns relevant tools based on task description

    Example:
        >>> awareness = ToolAwarenessSystem({"high_confidence_threshold": 0.8})
        >>>
        >>> # Proactive - before LLM call
        >>> suggestions = awareness.get_suggestions(
        ...     "Find all Python files in src/",
        ...     {"task_type": "search"}
        ... )
        >>> for s in suggestions:
        ...     print(s)
        >>>
        >>> # On-demand - during reasoning
        >>> tools = awareness.on_demand_discover(
        ...     "I need to check git status before committing"
        ... )
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the tool awareness system.

        Args:
            config: Configuration dictionary with keys:
                - high_confidence_threshold: Threshold for proactive mode (default: 0.8)
                - default_threshold: Default threshold (default: 0.7)
                - max_suggestions: Maximum suggestions to return (default: 5)
                - enable_proactive: Enable proactive mode (default: True)
                - enable_on_demand: Enable on-demand mode (default: True)
                - min_confidence: Minimum confidence for inclusion (default: 0.3)
                - include_descriptions: Include tool descriptions (default: True)
                - reasoning_depth: "brief" or "detailed" (default: "brief")
        """
        self._config = {**DEFAULT_CONFIG, **(config or {})}
        self._router = TwoStageRouter(
            confidence_threshold=self._config["default_threshold"]
        )

        logger.info(
            f"ToolAwarenessSystem initialized with threshold="
            f"{self._config['high_confidence_threshold']}"
        )

    @property
    def config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self._config.copy()

    def _calculate_category_confidence(self, user_message: str, category: str) -> float:
        """Calculate confidence score for a category based on keywords.

        Args:
            user_message: The user's message.
            category: Category to score.

        Returns:
            Confidence score (0.0-1.0).
        """
        if category not in CATEGORY_KEYWORDS:
            return 0.0

        message_lower = user_message.lower()
        rules = CATEGORY_KEYWORDS[category]

        positive = rules.get("positive", [])
        negative = rules.get("negative", [])

        positive_matches = sum(1 for kw in positive if kw in message_lower)
        negative_matches = sum(1 for kw in negative if kw in message_lower)

        # Score calculation: positive matches with negative penalty
        # Use a more generous calculation for proactive mode
        if not positive:
            return 0.5  # Default if no keywords defined

        if positive_matches > 0:
            # Base confidence on ratio of matched keywords
            max_possible = len(positive)
            normalized = positive_matches / max_possible
            # Boost for having positive matches
            confidence = max(0.5, min(1.0, normalized + 0.2))
            # Reduce slightly for negative matches
            confidence -= negative_matches * 0.1
        else:
            confidence = 0.0

        return max(0.0, min(1.0, confidence))

    def _get_complexity_for_message(self, user_message: str) -> RouteResult:
        """Get complexity information from TwoStageRouter.

        Args:
            user_message: User message to analyze.

        Returns:
            RouteResult from router.
        """
        try:
            return self._router.route(user_message)
        except Exception as e:
            logger.warning(f"Router failed: {e}")
            return RouteResult(
                complexity="complex",
                selected_tool=None,
                needs_big_model=True,
                route_path="full",
                confidence=0.5,
                reasoning="Router unavailable",
            )

    def _build_reason(
        self,
        category: str,
        confidence: float,
        complexity: str,
        tool_name: Optional[str] = None,
    ) -> str:
        """Build human-readable reason for suggestion.

        Args:
            category: Category name.
            confidence: Confidence score.
            complexity: Message complexity.
            tool_name: Optional specific tool.

        Returns:
            Formatted reason string.
        """
        depth = self._config.get("reasoning_depth", "brief")

        if depth == "brief":
            conf_level = "high" if confidence > 0.8 else "medium"
            return f"{conf_level} confidence ({complexity} task)"
        else:
            # Detailed reasoning
            category_desc = CATEGORY_DESCRIPTIONS.get(category, "Unknown")
            conf_pct = int(confidence * 100)

            parts = [
                f"{conf_pct}% confidence",
                f"{complexity} task",
                f"category: {category}",
            ]

            if tool_name:
                parts.append(f"tool: {tool_name}")

            return " | ".join(parts)

    def get_suggestions(
        self, user_message: str, context: Optional[Dict[str, Any]] = None
    ) -> List[ToolSuggestion]:
        """Get proactive tool suggestions based on user message.

        This is the main entry point for proactive mode. Called before
        LLM to inject relevant tool suggestions into context.

        Args:
            user_message: The user's input message.
            context: Optional context dictionary with keys:
                - task_type: Type of task (search, execute, etc.)
                - current_tools: Currently active tools
                - session_state: Current session state

        Returns:
            List of ToolSuggestion objects (filtered by confidence threshold).
        """
        if not self._config.get("enable_proactive", True):
            logger.debug("Proactive mode disabled")
            return []

        context = context or {}
        suggestions: List[ToolSuggestion] = []

        # Step 1: Get complexity from TwoStageRouter
        route_result = self._get_complexity_for_message(user_message)

        # Step 2: Get relevant categories from tool_categories
        try:
            relevant_categories = get_relevant_categories(user_message)
        except Exception as e:
            logger.warning(f"get_relevant_categories failed: {e}")
            relevant_categories = []

        if not relevant_categories:
            logger.debug("No relevant categories found")
            return []

        # Step 3: Get style context from style_learner for personalized suggestions
        style_context = _get_style_context()

        # Step 4: Score each category and create suggestions
        high_confidence_threshold = self._config["high_confidence_threshold"]
        min_confidence = self._config["min_confidence"]
        max_suggestions = self._config["max_suggestions"]

        # Extract user's preferred agents from style context
        preferred_agents = []
        if style_context.get("available"):
            style_profile = style_context.get("style_profile", {})
            preferred_agents = style_profile.get("preferred_agents", [])

        for category in relevant_categories:
            if len(suggestions) >= max_suggestions:
                break

            # Calculate category confidence
            confidence = self._calculate_category_confidence(user_message, category)

            # Apply style-based boost: if user prefers certain agents, boost confidence
            # for orchestration-related tool categories
            if style_context.get("available") and preferred_agents:
                if category in ("orchestration", "agent", "delegation"):
                    # User prefers delegation - boost orchestration tools
                    confidence = min(1.0, confidence + 0.15)
                    logger.debug(f"Style boost applied for {category}: +0.15")

            # Skip if below minimum threshold
            if confidence < min_confidence:
                continue

            # Get tools for this category
            tools = get_tools_for_category(category)
            if not tools:
                continue

            # Create suggestion for top tool in category
            tool_name = tools[0]

            # Determine mode based on confidence
            mode = (
                "proactive" if confidence >= high_confidence_threshold else "on_demand"
            )

            # Build reason
            reason = self._build_reason(
                category=category,
                confidence=confidence,
                complexity=route_result.complexity,
                tool_name=tool_name,
            )

            # Add style note if user has strong preferences
            if style_context.get("available") and preferred_agents:
                if category in ("orchestration", "agent", "delegation"):
                    reason = f"{reason} (style: prefers {preferred_agents[0]})"

            suggestion = ToolSuggestion(
                tool_name=tool_name,
                category=category,
                confidence=confidence,
                reason=reason,
                mode=mode,
            )

            suggestions.append(suggestion)

        # Sort by confidence descending
        suggestions.sort(key=lambda s: s.confidence, reverse=True)

        # Log results
        proactive_count = sum(1 for s in suggestions if s.mode == "proactive")
        logger.info(
            f"Generated {len(suggestions)} suggestions "
            f"({proactive_count} proactive) for: {user_message[:50]}..."
        )

        return suggestions

    def on_demand_discover(self, task_description: str) -> List[ToolSuggestion]:
        """On-demand tool discovery - model requests tools during reasoning.

        This method is called when the model detects it might benefit
        from tool assistance but isn't certain which tools to use.

        Args:
            task_description: Description of what the model is trying to do.

        Returns:
            List of ToolSuggestion objects relevant to the task.
        """
        if not self._config.get("enable_on_demand", True):
            logger.debug("On-demand mode disabled")
            return []

        suggestions: List[ToolSuggestion] = []

        # Get relevant categories for the task
        try:
            relevant_categories = get_relevant_categories(task_description)
        except Exception as e:
            logger.warning(f"get_relevant_categories failed: {e}")
            relevant_categories = []

        if not relevant_categories:
            # Fallback: return all categories with neutral confidence
            relevant_categories = list(TOOL_CATEGORIES.keys())

        max_suggestions = self._config["max_suggestions"]

        for category in relevant_categories:
            if len(suggestions) >= max_suggestions:
                break

            # Calculate confidence for this task
            confidence = self._calculate_category_confidence(task_description, category)

            # Boost confidence for on-demand (model explicitly asking)
            confidence = min(1.0, confidence + 0.1)

            # Get tools
            tools = get_tools_for_category(category)
            if not tools:
                continue

            # Add suggestions for multiple tools in category (up to 2)
            for tool_name in tools[:2]:
                # Check max
                if len(suggestions) >= max_suggestions:
                    break

                reason = self._build_reason(
                    category=category,
                    confidence=confidence,
                    complexity="on_demand",
                    tool_name=tool_name,
                )

                # Add tool description if configured
                if self._config.get("include_descriptions", True):
                    desc = get_tool_description(category, tool_name)
                    if desc:
                        # Truncate to first sentence
                        short_desc = desc.split(".")[0] + "."
                        reason = f"{reason} - {short_desc}"

                suggestion = ToolSuggestion(
                    tool_name=tool_name,
                    category=category,
                    confidence=confidence,
                    reason=reason,
                    mode="on_demand",
                )

                suggestions.append(suggestion)

        # Sort by confidence
        suggestions.sort(key=lambda s: s.confidence, reverse=True)

        logger.info(
            f"On-demand discovery returned {len(suggestions)} tools "
            f"for: {task_description[:50]}..."
        )

        return suggestions

    def should_inject_proactively(self, suggestions: List[ToolSuggestion]) -> bool:
        """Determine if suggestions should be injected proactively.

        Args:
            suggestions: List of tool suggestions.

        Returns:
            True if high-confidence suggestions should be injected.
        """
        if not suggestions:
            return False

        high_threshold = self._config["high_confidence_threshold"]

        # Check if any suggestion meets high confidence threshold
        return any(s.confidence >= high_threshold for s in suggestions)

    def build_injection_prompt(
        self, suggestions: List[ToolSuggestion], include_all: bool = False
    ) -> str:
        """Build prompt section for tool injection.

        Args:
            suggestions: List of ToolSuggestion to inject.
            include_all: Include all suggestions (not just high confidence).

        Returns:
            Formatted string for prompt injection.
        """
        if not suggestions:
            return ""

        high_threshold = self._config["high_confidence_threshold"]

        # Filter based on mode
        if include_all:
            filtered = suggestions
        else:
            filtered = [s for s in suggestions if s.confidence >= high_threshold]

        if not filtered:
            return ""

        lines = [
            "",
            "## Relevant Tools",
            "",
            "The following tools may be useful for your task:",
            "",
        ]

        # Group by category
        by_category: Dict[str, List[ToolSuggestion]] = {}
        for s in filtered:
            if s.category not in by_category:
                by_category[s.category] = []
            by_category[s.category].append(s)

        for category, category_suggestions in by_category.items():
            lines.append(f"### {category}")

            for s in category_suggestions:
                conf_pct = int(s.confidence * 100)
                lines.append(
                    f"- **{s.tool_name}** ({conf_pct}% confidence): {s.reason}"
                )

            lines.append("")

        return "\n".join(lines)

    def get_system_prompt_addition(
        self, user_message: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get the system prompt addition for tool awareness.

        Convenience method that combines get_suggestions and build_injection_prompt.

        Args:
            user_message: Current user message.
            context: Optional context.

        Returns:
            String to add to system prompt, or empty string.
        """
        suggestions = self.get_suggestions(user_message, context)

        if not self.should_inject_proactively(suggestions):
            return ""

        return self.build_injection_prompt(suggestions, include_all=False)


# =============================================================================
# Module-Level Convenience Functions
# =============================================================================


# Global instance (lazy initialization)
_global_instance: Optional[ToolAwarenessSystem] = None


def get_instance(config: Optional[Dict[str, Any]] = None) -> ToolAwarenessSystem:
    """Get or create global ToolAwarenessSystem instance.

    Args:
        config: Optional configuration.

    Returns:
        Global ToolAwarenessSystem instance.
    """
    global _global_instance
    if _global_instance is None:
        _global_instance = ToolAwarenessSystem(config)
    return _global_instance


def get_suggestions(
    user_message: str, context: Optional[Dict[str, Any]] = None
) -> List[ToolSuggestion]:
    """Convenience function for getting suggestions.

    Args:
        user_message: User message.
        context: Optional context.

    Returns:
        List of ToolSuggestion.
    """
    return get_instance().get_suggestions(user_message, context)


def on_demand_discover(task_description: str) -> List[ToolSuggestion]:
    """Convenience function for on-demand discovery.

    Args:
        task_description: Task description.

    Returns:
        List of ToolSuggestion.
    """
    return get_instance().on_demand_discover(task_description)


# =============================================================================
# Main / Tests
# =============================================================================


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s: %(message)s",
    )

    print("=== Tool Awareness System Test ===\n")

    # Initialize system
    config = {
        "high_confidence_threshold": 0.8,
        "max_suggestions": 5,
        "reasoning_depth": "brief",
    }
    awareness = ToolAwarenessSystem(config)

    # Test messages
    test_messages = [
        ("Find all Python files in the project", {"task_type": "search"}),
        ("Create a new file called test.py", {"task_type": "execute"}),
        ("Check git status and commit changes", {"task_type": "git"}),
        ("Remember that the user prefers dark mode", {"task_type": "memory"}),
        ("Run the linter and type checker", {"task_type": "quality"}),
        ("Create a new issue on GitHub", {"task_type": "integration"}),
        ("Spawn an agent to handle this", {"task_type": "orchestration"}),
    ]

    print("--- Proactive Mode (get_suggestions) ---\n")
    for msg, ctx in test_messages:
        suggestions = awareness.get_suggestions(msg, ctx)

        print(f"Message: '{msg}'")
        print(f"  Context: {ctx}")

        if suggestions:
            should_inject = awareness.should_inject_proactively(suggestions)
            print(f"  Should inject: {should_inject}")

            for s in suggestions:
                print(f"  {s}")
        else:
            print("  (no suggestions)")
        print()

    print("--- On-Demand Mode (on_demand_discover) ---\n")

    on_demand_tasks = [
        "I need to find files matching a pattern",
        "I want to create a new file",
        "I should check git status before pushing",
        "Let me run the tests to verify",
    ]

    for task in on_demand_tasks:
        tools = awareness.on_demand_discover(task)

        print(f"Task: '{task}'")

        if tools:
            for t in tools:
                print(f"  {t}")
        else:
            print("  (no tools)")
        print()

    print("--- System Prompt Addition ---\n")

    test_msg = "Find all Python files in the project"
    addition = awareness.get_system_prompt_addition(test_msg, {"task_type": "search"})

    if addition:
        print(f"Message: '{test_msg}'")
        print("Addition:")
        print(addition)
    else:
        print("No addition generated")

    print("\n=== Test Complete ===")
    sys.exit(0)

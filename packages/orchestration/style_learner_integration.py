"""Style Learner Integration — Hooks style_learner into orchestration flow.

This module provides the bridge between the orchestration system and the
style_learner for recording delegation patterns during sessions.

Usage:
    from packages.orchestration.style_learner_integration import (
        record_delegation,
        get_style_context,
        init_style_learner,
    )

    # Record a delegation
    record_delegation(agent="hephaestus", task_type="implementation", success=True, latency_ms=1500)

    # Get style context for tool suggestions
    context = get_style_context()
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("style_learner_integration")

# Add packages to path if needed for imports
_project_root = Path(__file__).resolve().parent.parent.parent
_packages_path = _project_root / "packages"
if str(_packages_path) not in sys.path:
    sys.path.insert(0, str(_packages_path))

# Lazy import to avoid circular dependencies
_style_learner = None


def _get_style_learner():
    """Lazy load style_learner to avoid import issues."""
    global _style_learner
    if _style_learner is None:
        try:
            from context_store.style_learner import get_learner

            _style_learner = get_learner()
            logger.info("StyleLearner initialized for orchestration")
        except ImportError as e:
            logger.warning(f"style_learner not available: {e}")
            return None
    return _style_learner


def init_style_learner(db_path: Optional[str] = None) -> bool:
    """Initialize the style learner.

    Args:
        db_path: Optional path to SQLite database

    Returns:
        True if initialization successful, False otherwise
    """
    try:
        learner = _get_style_learner()
        if learner:
            logger.info("Style learner integration initialized")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to init style learner: {e}")
        return False


def record_task(
    task_type: str,
    task_description: str = "",
    level: int = 1,
) -> bool:
    """Record a user task for style learning.

    Args:
        task_type: Type of task (implementation, research, review, fix)
        task_description: Description of the task
        level: Complexity level (1-5)

    Returns:
        True if recorded successfully, False otherwise
    """
    learner = _get_style_learner()
    if not learner:
        return False

    try:
        learner.record_task(
            task_type=task_type,
            task_description=task_description,
            level=level,
        )
        logger.debug(f"Recorded task: {task_type} - {task_description[:50]}")
        return True
    except Exception as e:
        logger.error(f"Failed to record task: {e}")
        return False


def record_delegation(
    agent: str,
    task_type: str = "unknown",
    success: bool = True,
    latency_ms: float = 0.0,
    tokens_used: int = 0,
) -> bool:
    """Record a delegation event for style learning.

    This is the main integration point - call this during agent routing
    to track which agents are used and how well they perform.

    Args:
        agent: Agent name that handled the task
        task_type: Type of task delegated
        success: Whether the task succeeded
        latency_ms: Time taken to complete
        tokens_used: Tokens consumed

    Returns:
        True if recorded successfully, False otherwise
    """
    learner = _get_style_learner()
    if not learner:
        return False

    try:
        learner.record_delegation(
            agent=agent,
            task_type=task_type,
            success=success,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
        )
        logger.debug(
            f"Recorded delegation: agent={agent}, task={task_type}, success={success}"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to record delegation: {e}")
        return False


def record_style(
    is_verbose: bool,
    is_direct: bool,
    message_length: int = 0,
) -> bool:
    """Record communication style.

    Args:
        is_verbose: Whether message is verbose
        is_direct: Whether message is direct
        message_length: Character count of message

    Returns:
        True if recorded successfully, False otherwise
    """
    learner = _get_style_learner()
    if not learner:
        return False

    try:
        learner.record_style(
            is_verbose=is_verbose,
            is_direct=is_direct,
            message_length=message_length,
        )
        logger.debug(f"Recorded style: verbose={is_verbose}, direct={is_direct}")
        return True
    except Exception as e:
        logger.error(f"Failed to record style: {e}")
        return False


def get_style_context() -> Dict[str, Any]:
    """Get learned style context for injection into orchestration.

    This context can be used to influence tool suggestions and
    agent selection based on learned patterns.

    Returns:
        Dict with style profile, recommendations, and timestamp
    """
    learner = _get_style_learner()
    if not learner:
        return {
            "style_profile": {},
            "recommendations": {},
            "timestamp": None,
            "available": False,
        }

    try:
        context = learner.get_style_context()
        context["available"] = True
        return context
    except Exception as e:
        logger.error(f"Failed to get style context: {e}")
        return {
            "style_profile": {},
            "recommendations": {},
            "timestamp": None,
            "available": False,
            "error": str(e),
        }


def get_suggested_agents() -> list[str]:
    """Get suggested agents based on learned preferences.

    Returns:
        List of agent names in order of preference
    """
    context = get_style_context()
    recommendations = context.get("recommendations", {})
    return recommendations.get("suggested_agents", [])


def get_communication_tip() -> str:
    """Get communication tip based on learned style.

    Returns:
        Communication tip string or empty string
    """
    context = get_style_context()
    recommendations = context.get("recommendations", {})
    return recommendations.get("communication_tip", "")


# =============================================================================
# Integration Hooks for Task Router
# =============================================================================


def create_delegation_callback():
    """Create a callback function for task routing to record delegations.

    Returns:
        Callable that can be used to record delegation outcomes
    """

    def record(agent: str, task_type: str, success: bool, latency_ms: float = 0.0):
        record_delegation(
            agent=agent,
            task_type=task_type,
            success=success,
            latency_ms=latency_ms,
        )

    return record


# =============================================================================
# Convenience wrapper for orchestrator integration
# =============================================================================


class StyleLearnerBridge:
    """Bridge class for integrating style_learner with orchestrator.

    Usage:
        bridge = StyleLearnerBridge()

        # On task start
        bridge.on_task_start(task_type="implementation", description="add feature")

        # On delegation
        bridge.on_delegate(agent="hephaestus", task_type="implementation")

        # On task complete
        bridge.on_task_complete(agent="hephaestus", success=True, latency_ms=1500)

        # Get context for next routing decision
        context = bridge.get_context()
    """

    def __init__(self):
        self._current_task: Optional[Dict[str, Any]] = None
        self._initialized = init_style_learner()

    def on_task_start(
        self,
        task_type: str,
        description: str = "",
        level: int = 1,
    ) -> None:
        """Called when a new task starts."""
        if not self._initialized:
            return

        self._current_task = {
            "type": task_type,
            "description": description,
            "level": level,
        }
        record_task(task_type, description, level)

    def on_delegate(
        self,
        agent: str,
        task_type: str = "unknown",
    ) -> None:
        """Called when a task is delegated to an agent."""
        if not self._initialized:
            return

        self._current_task["delegate_agent"] = agent
        self._current_task["delegate_time"] = None  # Will track in on_task_complete

    def on_task_complete(
        self,
        agent: str,
        success: bool = True,
        latency_ms: float = 0.0,
        tokens_used: int = 0,
    ) -> None:
        """Called when a delegated task completes."""
        if not self._initialized:
            return

        task_type = (
            self._current_task.get("type", "unknown")
            if self._current_task
            else "unknown"
        )
        record_delegation(
            agent=agent,
            task_type=task_type,
            success=success,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
        )
        self._current_task = None

    def get_context(self) -> Dict[str, Any]:
        """Get style context for influencing next routing decision."""
        return get_style_context()

    def get_suggested_agents(self) -> list[str]:
        """Get suggested agents based on learned preferences."""
        return get_suggested_agents()


# Global bridge instance
_bridge: Optional[StyleLearnerBridge] = None


def get_bridge() -> StyleLearnerBridge:
    """Get singleton StyleLearnerBridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = StyleLearnerBridge()
    return _bridge


# =============================================================================
# Main - Quick Test
# =============================================================================


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s: %(message)s",
    )

    print("=== Style Learner Integration Test ===\n")

    # Test 1: Initialize
    print("--- Test 1: Initialization ---")
    result = init_style_learner()
    print(f"Init result: {result}")

    # Test 2: Record task
    print("\n--- Test 2: Record Task ---")
    result = record_task("implementation", "add JWT auth middleware", 2)
    print(f"Record task: {result}")

    # Test 3: Record delegation
    print("\n--- Test 3: Record Delegation ---")
    result = record_delegation("hephaestus", "implementation", True, 1500, 12000)
    print(f"Record delegation: {result}")

    # Test 4: Get style context
    print("\n--- Test 4: Get Style Context ---")
    context = get_style_context()
    print(f"Available: {context.get('available')}")
    print(f"Profile: {context.get('style_profile')}")
    print(f"Recommendations: {context.get('recommendations')}")

    # Test 5: Bridge
    print("\n--- Test 5: Bridge Class ---")
    bridge = StyleLearnerBridge()
    bridge.on_task_start("research", "find auth patterns", 1)
    bridge.on_delegate("explore", "research")
    bridge.on_task_complete("explore", True, 800, 5000)
    context = bridge.get_context()
    print(f"Suggested agents: {bridge.get_suggested_agents()}")

    print("\n=== All Tests Passed ===")
    sys.exit(0)

"""
Fingerprint Activator — Phase 1.5 + 2.3: Session Fingerprinting Integration.

This module connects existing fingerprint tools to the orchestration flow:
- BEFORE TASK: Get relevant context from past sessions
- AFTER TASK: Record pattern for learning
- WARM POOL: Pre-warm session pool based on user's preferred agents

Usage:
    from packages.orchestration.fingerprint_activator import FingerprintActivator

    activator = FingerprintActivator()

    # Before agent dispatch
    context = activator.before_task("implement JWT auth")

    # After task completion
    activator.after_task("implement JWT auth", "success")

    # Pre-warm pool based on fingerprint
    activator.warm_pool_based_on_fingerprint(context)
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Thread pool for parallel MCP calls
_executor = ThreadPoolExecutor(max_workers=4)

# ============================================================================
# Result Dataclasses
# ============================================================================


@dataclass
class FingerprintContext:
    """Context from past sessions for current task."""

    current_task: str
    session_context: str
    user_preferences: Dict[str, Any]
    sessions_found: int
    status: str = "success"


@dataclass
class FingerprintResult:
    """Result of fingerprint activation."""

    session_context: str
    user_preferences: Dict[str, Any]
    sessions_found: int
    status: str


@dataclass
class PatternRecordResult:
    """Result of pattern recording."""

    status: str
    action: str
    outcome: str


@dataclass
class WarmPoolResult:
    """Result of pool warming operation."""

    status: str
    agents_warmed: List[str] = field(default_factory=list)
    reason: Optional[str] = None


# ============================================================================
# FingerprintActivator
# ============================================================================


class FingerprintActivator:
    """Connects fingerprint tools to orchestration flow.

    Implements Phase 1.5 + 2.3 of the masterplan:
    - Phase 1.5: Get relevant context BEFORE agent dispatch
    - Phase 2.3: Record patterns AFTER task completion
    - Pool warming based on user fingerprint

    Attributes:
        _max_sessions: Maximum sessions to retrieve for context
    """

    def __init__(self, max_sessions: int = 3) -> None:
        """Initialize fingerprint activator.

        Args:
            max_sessions: Maximum number of past sessions to retrieve (default: 3)
        """
        self._max_sessions = max_sessions
        logger.debug(
            f"FingerprintActivator initialized with max_sessions={max_sessions}"
        )

    def before_task(self, current_task: str) -> Dict[str, Any]:
        """Get relevant context from past sessions before agent dispatch.

        This is Phase 1.5 - retrieves session context and user preferences
        to inject into the agent's prompt before execution.

        Args:
            current_task: The task description to find context for

        Returns:
            Dict containing:
                - session_context: Relevant context from past sessions
                - user_preferences: User's learned preferences
                - sessions_found: Number of sessions that matched
                - status: "success" or "error"
        """
        logger.info(
            f"[Phase 1.5] Getting fingerprint context for task: {current_task[:50]}..."
        )

        session_context = ""
        user_preferences: Dict[str, Any] = {}
        sessions_found = 0

        def get_session_context() -> Dict[str, Any]:
            """Get session context - runs in thread pool."""
            try:
                from packages.brain_mcp.namespaces.fingerprint import (
                    fingerprint_get_session_context,
                )

                return fingerprint_get_session_context(
                    current_task=current_task,
                    max_sessions=self._max_sessions,
                )
            except Exception as e:
                logger.warning(f"Failed to get session context: {e}")
                return {"status": "error", "error": str(e)}

        def get_user_preferences() -> Dict[str, Any]:
            """Get user preferences - runs in thread pool."""
            try:
                from packages.brain_mcp.namespaces.fingerprint import (
                    fingerprint_get_user_preferences,
                )

                return fingerprint_get_user_preferences()
            except Exception as e:
                logger.warning(f"Failed to get user preferences: {e}")
                return {"status": "error", "error": str(e)}

        # Run both MCP calls in parallel
        futures = [
            _executor.submit(get_session_context),
            _executor.submit(get_user_preferences),
        ]

        # Wait for both to complete
        ctx_result, prefs_result = [f.result() for f in futures]

        # Process session context
        if ctx_result.get("status") == "success":
            session_context = ctx_result.get("context", "")
            sessions_found = ctx_result.get("sessions_found", 0)
            logger.debug(f"Found {sessions_found} relevant sessions")
        else:
            logger.warning(f"Session context error: {ctx_result.get('error')}")

        # Process user preferences
        if prefs_result.get("status") == "success":
            user_preferences = {
                "style": prefs_result.get("style", {}),
                "profile": prefs_result.get("profile", {}),
            }
            logger.debug("Retrieved user preferences")
        else:
            logger.warning(f"User preferences error: {prefs_result.get('error')}")

        return {
            "session_context": session_context,
            "user_preferences": user_preferences,
            "sessions_found": sessions_found,
            "status": "success" if session_context or user_preferences else "partial",
        }

    def after_task(self, task: str, outcome: str) -> Dict[str, Any]:
        """Record pattern for learning after task completion.

        This is Phase 2.3 - records the task outcome for pattern extraction
        and predictive routing.

        Args:
            task: The task that was executed
            outcome: Result of the task ("success", "failed", "completed", etc.)

        Returns:
            Dict containing:
                - status: "recorded" or "error"
                - action: The task that was recorded
                - outcome: The outcome that was recorded
        """
        logger.info(f"[Phase 2.3] Recording pattern: {task[:50]}... -> {outcome}")

        try:
            from packages.brain_mcp.namespaces.fingerprint import (
                fingerprint_record_pattern,
            )

            result = fingerprint_record_pattern(
                action_type=task,
                outcome=outcome,
                context={"task": task, "outcome": outcome},
            )

            if result.get("status") == "recorded":
                logger.debug(f"Pattern recorded successfully: {task[:30]}")
            else:
                logger.warning(f"Pattern recording failed: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"Failed to record pattern: {e}")
            return {
                "status": "error",
                "error": str(e),
                "action": task,
                "outcome": outcome,
            }

    def warm_pool_based_on_fingerprint(
        self, fingerprint: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Pre-warm session pool based on user's preferred agents.

        Uses user preferences from fingerprint to determine which agents
        to pre-warm in the session pool.

        Args:
            fingerprint: Output from before_task() containing user_preferences

        Returns:
            Dict containing:
                - status: "warmed", "skipped", or "error"
                - agents_warmed: List of agent types that were warmed
                - reason: Optional reason if skipped
        """
        logger.info("[Phase 2.3] Warming pool based on fingerprint")

        user_prefs = fingerprint.get("user_preferences", {})
        preferred_agents: List[str] = []

        # Extract preferred agents from user profile
        profile = user_prefs.get("profile", {})
        if profile:
            # Look for preferred agent types in profile
            preferred_agents = profile.get("preferred_agents", [])

            # Also check style preferences for agent hints
            style = user_prefs.get("style", {})
            if not preferred_agents:
                preferred_agents = style.get("preferred_agents", [])

        if not preferred_agents:
            logger.debug("No preferred agents found in fingerprint, skipping warm")
            return {
                "status": "skipped",
                "agents_warmed": [],
                "reason": "no_preferred_agents",
            }

        logger.info(f"Warming pool with preferred agents: {preferred_agents}")

        try:
            from packages.brain_mcp.namespaces.session import session_warm_pool

            result = session_warm_pool(agents=preferred_agents)

            if result.get("status") == "success" or "warmed" in result.get(
                "status", ""
            ):
                logger.debug(f"Pool warmed with agents: {preferred_agents}")
                return {
                    "status": "warmed",
                    "agents_warmed": preferred_agents,
                }
            else:
                logger.warning(f"Pool warm failed: {result.get('error')}")
                return {
                    "status": "error",
                    "agents_warmed": [],
                    "reason": result.get("error", "unknown"),
                }

        except Exception as e:
            logger.error(f"Failed to warm pool: {e}")
            return {
                "status": "error",
                "agents_warmed": [],
                "reason": str(e),
            }

    def full_activation(self, task: str) -> Dict[str, Any]:
        """Execute full fingerprint activation cycle.

        Convenience method that runs before_task, returns context for agent,
        and sets up for after_task to be called later.

        Args:
            task: The task to get context for

        Returns:
            Dict with all fingerprint context ready for agent injection
        """
        logger.info(f"[Phase 1.5+2.3] Full fingerprint activation for: {task[:50]}...")

        # Phase 1.5: Get context before task
        fingerprint = self.before_task(task)

        # Try to warm pool based on fingerprint
        warm_result = self.warm_pool_based_on_fingerprint(fingerprint)

        return {
            "task": task,
            "fingerprint": fingerprint,
            "warm_result": warm_result,
            "ready_for_execution": True,
        }


# ============================================================================
# Convenience Functions
# ============================================================================


def get_fingerprint_context(task: str) -> Dict[str, Any]:
    """Convenience function to get fingerprint context before task.

    Args:
        task: Task description

    Returns:
        Fingerprint context dict
    """
    activator = FingerprintActivator()
    return activator.before_task(task)


def record_task_outcome(task: str, outcome: str) -> Dict[str, Any]:
    """Convenience function to record task outcome.

    Args:
        task: Task that was executed
        outcome: Result ("success", "failed", etc.)

    Returns:
        Recording result dict
    """
    activator = FingerprintActivator()
    return activator.after_task(task, outcome)


def warm_pool_from_fingerprint(fingerprint: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to warm pool from fingerprint.

    Args:
        fingerprint: Output from before_task()

    Returns:
        Warm pool result dict
    """
    activator = FingerprintActivator()
    return activator.warm_pool_based_on_fingerprint(fingerprint)

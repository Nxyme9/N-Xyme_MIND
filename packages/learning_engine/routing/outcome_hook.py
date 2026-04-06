#!/usr/bin/env python3
"""TaskOutcomeHook — Auto-logs outcomes when tasks complete.

Wraps task execution to automatically record outcomes to the learning system.
Uses threading.local() for per-task state and integrates with OutcomeLogger
and AdaptiveRouter.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from threading import local
from typing import Any, Optional

from ..outcome_logger import DelegationOutcome, OutcomeLogger

logger = logging.getLogger(__name__)

# Thread-local storage for per-task state
_task_state = local()


@dataclass
class TaskState:
    """State for a single task execution."""

    task_id: str
    description: str
    start_time: float
    agent: str = "unknown"
    level: int = 3
    task_type: str = "implementation"
    context: dict[str, Any] = field(default_factory=dict)


class TaskOutcomeHook:
    """Hooks into task lifecycle to auto-log outcomes.

    Usage:
        hook = TaskOutcomeHook()

        # Before task starts
        hook.before_task("task-123", "Fix the bug in auth")

        # After task completes (success)
        hook.after_task("task-123", success=True)

        # After task fails
        hook.after_task("task-123", success=False, error="Connection refused")

        # Or use as context manager
        with hook.task("task-123", "Implement feature") as t:
            # do work
            pass  # auto-logs on exit
    """

    def __init__(
        self,
        outcome_logger: Optional[OutcomeLogger] = None,
        auto_detect_agent: bool = True,
    ):
        self._outcome_logger = outcome_logger or OutcomeLogger()
        self._auto_detect_agent = auto_detect_agent

    def before_task(
        self,
        task_id: str,
        description: str,
        agent: Optional[str] = None,
        level: Optional[int] = None,
        task_type: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record start of task execution.

        Args:
            task_id: Unique identifier for the task
            description: Human-readable task description
            agent: Agent name (auto-detected if not provided)
            level: L1-L5 complexity level (auto-detected if not provided)
            task_type: Type of task (implementation, research, review, fix)
            context: Additional context dict
        """
        # Auto-detect agent from description if not provided
        if agent is None and self._auto_detect_agent:
            agent = self._detect_agent(description)
        agent = agent or "unknown"

        # Auto-detect level if not provided
        if level is None:
            level = self._detect_level(description)
        level = level or 3

        # Auto-detect task_type if not provided
        if task_type is None:
            task_type = self._detect_task_type(description)
        task_type = task_type or "implementation"

        context = context or {}

        # Store task state in thread-local storage
        setattr(
            _task_state,
            task_id,
            TaskState(
                task_id=task_id,
                description=description,
                start_time=time.time(),
                agent=agent,
                level=level,
                task_type=task_type,
                context=context,
            ),
        )

        logger.debug(f"Task started: {task_id} ({agent}, L{level}, {task_type})")

    def after_task(
        self,
        task_id: str,
        success: bool,
        error: Optional[str] = None,
        tokens_used: int = 0,
        quality_score: Optional[float] = None,
        additional_context: Optional[dict[str, Any]] = None,
    ) -> Optional[int]:
        """Record completion of task execution.

        Args:
            task_id: Unique identifier for the task
            success: Whether the task completed successfully
            error: Error message if task failed
            tokens_used: Number of tokens used (for cost tracking)
            quality_score: User-provided quality score (0-1)
            additional_context: Additional context to merge

        Returns:
            Outcome ID if logged successfully, None otherwise
        """
        # Get task state from thread-local storage
        task_state = getattr(_task_state, task_id, None)

        if task_state is None:
            logger.warning(
                f"No task state found for {task_id}, creating minimal outcome"
            )
            # Create minimal outcome if state not found
            task_state = TaskState(
                task_id=task_id,
                description="unknown",
                start_time=time.time(),
            )

        # Calculate latency
        end_time = time.time()
        latency_ms = (end_time - task_state.start_time) * 1000

        # Build context from stored + additional
        context = task_state.context.copy()
        if additional_context:
            context.update(additional_context)
        if error:
            context["error"] = error

        # Determine success (override if exception caught)
        final_success = success
        if error:
            final_success = False

        # Create DelegationOutcome
        outcome = DelegationOutcome(
            task_id=task_id,
            task_description=task_state.description,
            task_type=task_state.task_type,
            agent=task_state.agent,
            level=task_state.level,
            success=final_success,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            quality_score=quality_score,
            context=context,
            timestamp=datetime.now().isoformat(),
        )

        # Log to database
        try:
            outcome_id = self._outcome_logger.log(outcome)
            logger.info(
                f"Task outcome logged: {task_id} -> "
                f"{'SUCCESS' if final_success else 'FAILED'} "
                f"(latency: {latency_ms:.0f}ms, agent: {task_state.agent})"
            )
            return outcome_id
        except Exception as e:
            logger.error(f"Failed to log outcome: {e}")
            return None
        finally:
            # Clean up thread-local state
            try:
                delattr(_task_state, task_id)
            except AttributeError:
                pass

    def _detect_agent(self, description: str) -> str:
        """Auto-detect agent from task description.

        Args:
            description: Task description text

        Returns:
            Agent name (explore, hephaestus, oracle, librarian, etc.)
        """
        desc_lower = description.lower()

        # Research/exploration tasks
        if any(
            word in desc_lower
            for word in ["find", "search", "locate", "explore", "look for"]
        ):
            return "explore"

        # External research/library tasks
        if any(
            word in desc_lower
            for word in ["documentation", "docs", "external", "web", "search online"]
        ):
            return "librarian"

        # Review/architecture tasks
        if any(
            word in desc_lower
            for word in [
                "review",
                "architecture",
                "design",
                "analyze",
                "evaluate",
                "assess",
            ]
        ):
            return "oracle"

        # Implementation tasks (default)
        return "hephaestus"

    def _detect_level(self, description: str) -> int:
        """Auto-detect complexity level from task description.

        Args:
            description: Task description text

        Returns:
            L1-L5 complexity level
        """
        desc_lower = description.lower()

        # L1: Trivial (typo, version bump)
        if any(word in desc_lower for word in ["typo", "fix spelling", "bump version"]):
            return 1

        # L2: Simple (single file fix)
        if any(word in desc_lower for word in ["fix", "simple", "single", "one file"]):
            return 2

        # L4: Complex (new feature, architecture)
        if any(
            word in desc_lower
            for word in ["new feature", "architecture", "redesign", "system"]
        ):
            return 4

        # L5: Architect (major redesign)
        if any(
            word in desc_lower
            for word in ["redesign", "rearchitecture", "migration", "overhaul"]
        ):
            return 5

        # L3: Default (moderate complexity)
        return 3

    def _detect_task_type(self, description: str) -> str:
        """Auto-detect task type from description.

        Args:
            description: Task description text

        Returns:
            Task type (implementation, research, review, fix)
        """
        desc_lower = description.lower()

        if any(word in desc_lower for word in ["fix", "bug", "error", "issue"]):
            return "fix"
        if any(
            word in desc_lower for word in ["review", "analyze", "evaluate", "assess"]
        ):
            return "review"
        if any(
            word in desc_lower
            for word in ["find", "search", "explore", "research", "lookup"]
        ):
            return "research"

        return "implementation"

    def task(
        self,
        task_id: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs,
    ) -> "TaskContext":
        """Create a context manager for automatic outcome logging.

        Args:
            task_id: Task ID (auto-generated if not provided)
            description: Task description (auto-generated if not provided)
            **kwargs: Additional arguments passed to before_task

        Usage:
            with hook.task("task-123", "Implement feature") as t:
                # do work
                pass  # auto-logs on exit
        """
        task_id = task_id or str(uuid.uuid4())
        description = description or "auto-generated task"

        return TaskContext(self, task_id, description, **kwargs)


class TaskContext:
    """Context manager for automatic outcome logging."""

    def __init__(
        self,
        hook: TaskOutcomeHook,
        task_id: str,
        description: str,
        **kwargs,
    ):
        self._hook = hook
        self._task_id = task_id
        self._description = description
        self._kwargs = kwargs
        self._success = True
        self._error: Optional[str] = None
        self._tokens_used = 0
        self._quality_score: Optional[float] = None

    def __enter__(self) -> "TaskContext":
        self._hook.before_task(self._task_id, self._description, **self._kwargs)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            self._success = False
            self._error = str(exc_val) if exc_val else "Unknown error"

        self._hook.after_task(
            task_id=self._task_id,
            success=self._success,
            error=self._error,
            tokens_used=self._tokens_used,
            quality_score=self._quality_score,
        )
        return False  # Don't suppress exceptions

    def set_success(self, success: bool) -> None:
        """Set success status manually."""
        self._success = success

    def set_error(self, error: Optional[str]) -> None:
        """Set error message."""
        self._error = error

    def set_tokens(self, tokens: int) -> None:
        """Set tokens used."""
        self._tokens_used = tokens

    def set_quality(self, quality: float) -> None:
        """Set quality score."""
        self._quality_score = quality


# Global instance for convenience
_default_hook: Optional[TaskOutcomeHook] = None


def get_hook() -> TaskOutcomeHook:
    """Get the default global TaskOutcomeHook instance."""
    global _default_hook
    if _default_hook is None:
        _default_hook = TaskOutcomeHook()
    return _default_hook


__all__ = [
    "TaskOutcomeHook",
    "TaskContext",
    "TaskState",
    "get_hook",
]

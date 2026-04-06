#!/usr/bin/env python3
"""task_wrapper — Wires learning into task() delegation calls.

This module provides a drop-in wrapper for task() calls that automatically:
1. Before task: calls route_task() to get optimal agent via AdaptiveRouter
2. After task: calls log_outcome() with success/failure, latency, tokens

Works as both decorator and context manager. Thread-safe with threading.local().
"""

from __future__ import annotations

import functools
import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from threading import local
from typing import Any, Callable, Generator, Optional, TypeVar

from .outcome_logger import DelegationOutcome, OutcomeLogger
from .routing.adaptive_router import AdaptiveRouter

logger = logging.getLogger(__name__)

# Thread-local storage for per-task execution state
_task_context = local()

# Type variable for generic function wrapping
F = TypeVar("F", bound=Callable[..., Any])

# Default paths
DEFAULT_OUTCOMES_DB = ".sisyphus/outcomes.db"
DEFAULT_ROUTING_DB = ".sisyphus/routing_learning.db"


@dataclass
class TaskContext:
    """Context for a single wrapped task execution."""

    task_id: str
    description: str
    start_time: float
    agent: str = "unknown"
    level: int = 3
    task_type: str = "implementation"
    tokens_used: int = 0
    context: dict[str, Any] = field(default_factory=dict)


class TaskWrapper:
    """Wraps task() calls with learning integration.

    This class provides:
    - Decorator mode: @wrap_task
    - Context manager mode: with wrapped_task(): ...
    - Manual mode: wrapper.before_task(), wrapper.after_task()

    Usage:
        # As decorator
        @wrap_task
        def my_task(param):
            return do_work(param)

        # As context manager
        with wrapped_task("task-id", "description") as ctx:
            result = do_work()
            ctx.tokens_used = estimate_tokens(result)

        # Manual
        wrapper = TaskWrapper()
        wrapper.before_task("id", "description")
        try:
            result = task()
            wrapper.after_task("id", success=True)
        except Exception as e:
            wrapper.after_task("id", success=False, error=str(e))
    """

    def __init__(
        self,
        outcome_logger: Optional[OutcomeLogger] = None,
        adaptive_router: Optional[AdaptiveRouter] = None,
        outcomes_db: str = DEFAULT_OUTCOMES_DB,
        routing_db: str = DEFAULT_ROUTING_DB,
        auto_route: bool = True,
        auto_log: bool = True,
    ):
        """Initialize the task wrapper.

        Args:
            outcome_logger: Optional OutcomeLogger instance (created if not provided)
            adaptive_router: Optional AdaptiveRouter instance (created if not provided)
            outcomes_db: Path to outcomes database
            routing_db: Path to routing/learning database
            auto_route: Whether to call route_task() before task execution
            auto_log: Whether to log outcome after task completes
        """
        self._outcome_logger = outcome_logger or OutcomeLogger(db_path=outcomes_db)
        self._adaptive_router = adaptive_router or AdaptiveRouter(
            db_path=routing_db,
            outcome_logger=self._outcome_logger,
        )
        self._auto_route = auto_route
        self._auto_log = auto_log

    def before_task(
        self,
        task_id: str,
        description: str,
        agent: Optional[str] = None,
        level: Optional[int] = None,
        task_type: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Record start of task and optionally route to optimal agent.

        Args:
            task_id: Unique identifier for the task
            description: Human-readable task description
            agent: Agent name (auto-detected or from routing if auto_route=True)
            level: L1-L5 complexity level (auto-detected if not provided)
            task_type: Type of task (implementation, research, review, fix)
            context: Additional context dict

        Returns:
            Dict with routing decision (if auto_route=True) or empty dict
        """
        # Auto-detect task_type from description if not provided
        if task_type is None:
            task_type = self._detect_task_type(description)
        task_type = task_type or "implementation"

        # Auto-detect level from description if not provided
        if level is None:
            level = self._detect_level(description)
        level = level or 3

        context = context or {}
        routing_decision: dict[str, Any] = {}

        # Route to optimal agent if enabled
        if self._auto_route:
            try:
                routing_decision = self._adaptive_router.route(description)
                agent = routing_decision.get("agent", agent or "hephaestus")
                level = routing_decision.get("level", level)
                context["routing"] = routing_decision
                logger.debug(f"Routed '{description[:50]}...' -> {agent} (L{level})")
            except Exception as e:
                logger.warning(f"Routing failed, using fallback: {e}")
                agent = agent or self._detect_agent(description)

        # Auto-detect agent if still not provided
        if agent is None:
            agent = self._detect_agent(description)
        agent = agent or "hephaestus"

        # Store task context in thread-local storage
        setattr(
            _task_context,
            task_id,
            TaskContext(
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
        return routing_decision

    def after_task(
        self,
        task_id: str,
        success: bool,
        error: Optional[str] = None,
        tokens_used: int = 0,
        quality_score: Optional[float] = None,
        additional_context: Optional[dict[str, Any]] = None,
    ) -> Optional[int]:
        """Record completion of task execution to learning system.

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
        # Get task context from thread-local storage
        task_ctx: Optional[TaskContext] = getattr(_task_context, task_id, None)

        if task_ctx is None:
            logger.warning(
                f"No task context found for {task_id}, creating minimal outcome"
            )
            # Create minimal context if not found
            task_ctx = TaskContext(
                task_id=task_id,
                description="unknown",
                start_time=time.time(),
            )

        # Calculate latency
        end_time = time.time()
        latency_ms = (end_time - task_ctx.start_time) * 1000

        # Build context from stored + additional
        context = task_ctx.context.copy()
        if additional_context:
            context.update(additional_context)
        if error:
            context["error"] = error

        # Override success if error present
        final_success = success and error is None

        # Create DelegationOutcome
        outcome = DelegationOutcome(
            task_id=task_id,
            task_description=task_ctx.description,
            task_type=task_ctx.task_type,
            agent=task_ctx.agent,
            level=task_ctx.level,
            success=final_success,
            latency_ms=latency_ms,
            tokens_used=tokens_used or task_ctx.tokens_used,
            quality_score=quality_score,
            context=context,
            timestamp=datetime.now().isoformat(),
        )

        # Log to database if enabled
        outcome_id = None
        if self._auto_log:
            try:
                outcome_id = self._outcome_logger.log(outcome)
                logger.info(
                    f"Task outcome logged: {task_id} -> "
                    f"{'SUCCESS' if final_success else 'FAILED'} "
                    f"(latency: {latency_ms:.0f}ms, agent: {task_ctx.agent})"
                )
            except Exception as e:
                logger.error(f"Failed to log outcome: {e}")

        # Clean up thread-local state
        try:
            delattr(_task_context, task_id)
        except AttributeError:
            pass

        return outcome_id

    @contextmanager
    def task(
        self,
        task_id: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs,
    ) -> Generator[TaskContext, None, None]:
        """Context manager for automatic task wrapping.

        Args:
            task_id: Task ID (auto-generated if not provided)
            description: Task description (auto-generated if not provided)
            **kwargs: Additional arguments passed to before_task

        Yields:
            TaskContext that can be modified (e.g., set tokens_used)

        Usage:
            with wrapper.task("task-123", "Implement feature") as ctx:
                result = do_work()
                ctx.tokens_used = estimate_tokens(result)
            # Automatically logs outcome on exit
        """
        task_id = task_id or str(uuid.uuid4())
        description = description or "auto-generated task"

        # Start task and get routing decision
        self.before_task(task_id, description, **kwargs)

        # Get the context for external modification
        task_ctx: Optional[TaskContext] = getattr(_task_context, task_id, None)

        success = True
        error: Optional[str] = None

        try:
            yield task_ctx
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            # Always log outcome
            self.after_task(
                task_id=task_id,
                success=success,
                error=error,
                tokens_used=task_ctx.tokens_used if task_ctx else 0,
            )

    def _detect_agent(self, description: str) -> str:
        """Auto-detect agent from task description."""
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
        """Auto-detect complexity level from task description."""
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
        """Auto-detect task type from description."""
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


# Global default wrapper instance
_default_wrapper: Optional[TaskWrapper] = None


def get_wrapper() -> TaskWrapper:
    """Get the default global TaskWrapper instance."""
    global _default_wrapper
    if _default_wrapper is None:
        _default_wrapper = TaskWrapper()
    return _default_wrapper


def wrap_task(
    func: Optional[F] = None,
    *,
    task_id: Optional[Callable[[], str]] = None,
    description: Optional[Callable[[F], str]] = None,
    auto_route: bool = True,
    auto_log: bool = True,
    wrapper: Optional[TaskWrapper] = None,
) -> Callable[[F], F]:
    """Decorator that wraps a task function with learning integration.

    This is the main entry point for wrapping task() calls.

    Args:
        func: The function to wrap (when used without parentheses)
        task_id: Optional callable that returns task_id (default: auto-generate UUID)
        description: Optional callable that extracts description from func args
        auto_route: Whether to route to optimal agent before execution
        auto_log: Whether to log outcome after execution
        wrapper: Optional TaskWrapper instance (uses global if not provided)

    Returns:
        Wrapped function that logs outcomes to learning system

    Usage:
        # Simple usage (auto-detects description from function name)
        @wrap_task
        def implement_feature(x):
            return do_work(x)

        # With custom description
        @wrap_task(description=lambda f: f"Implement {f.__name__}")
        def my_task():
            pass

        # With options
        @wrap_task(auto_route=True, auto_log=True)
        def tracked_task():
            pass

        # With parentheses (no args)
        @wrap_task()
        def another_task():
            pass
    """

    def decorator(fn: F) -> F:
        # Create wrapper for this specific decorated function
        # Use provided wrapper or get global one
        w = wrapper or get_wrapper()

        @functools.wraps(fn)
        def wrapper_fn(*args, **kwargs):
            # Generate task_id
            tid = task_id() if task_id else str(uuid.uuid4())

            # Extract description from args or use function name
            if description:
                desc = description(fn)
            else:
                # Try to extract from args (first positional arg if it has __name__)
                if args and hasattr(args[0], "__name__"):
                    desc = f"{fn.__name__}({args[0].__name__})"
                else:
                    desc = fn.__name__

            # Before task: route if enabled
            routing_decision = {}
            if auto_route:
                try:
                    routing_decision = w.before_task(tid, desc)
                except Exception as e:
                    logger.warning(f"Pre-task routing failed: {e}")

            # Execute the actual task
            success = True
            error: Optional[str] = None
            result = None

            try:
                result = fn(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                # After task: log outcome if enabled
                if auto_log:
                    try:
                        w.after_task(tid, success=success, error=error)
                    except Exception as e:
                        logger.error(f"Post-task logging failed: {e}")

        return wrapper_fn  # type: ignore[return-value]

    # Handle both @wrap_task and @wrap_task() patterns
    if func is not None:
        # Called as @wrap_task (no parentheses)
        return decorator(func)
    else:
        # Called as @wrap_task(...) with options
        return decorator


# Backwards compatibility: also expose as TaskWrapper for direct usage
__all__ = [
    "TaskWrapper",
    "TaskContext",
    "wrap_task",
    "get_wrapper",
]

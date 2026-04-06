#!/usr/bin/env python3
"""MEMORY_BRIDGE — N-Xyme Collective Memory System.

This module provides a drop-in wrapper for task() calls that automatically:
1. Before task: calls route_task() to get optimal agent via AdaptiveRouter
2. Before task: queries memory for relevant context (MEMORY_BRIDGE PRE-READ)
3. After task: calls log_outcome() with success/failure, latency, tokens
4. After task: writes task outcome to memory (MEMORY_BRIDGE POST-WRITE)

Works as both decorator and context manager. Thread-safe with threading.local().

MEMORY_BRIDGE Architecture:
- Pre-read: Every task() call searches memory for relevant context BEFORE execution
- Post-write: Every task() completion writes outcome to memory AFTER execution
- Result: All sessions share context like a collective hivemind
"""

from __future__ import annotations

import functools
import json
import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
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
        auto_memory: bool = True,
        memory_path: str = ".sisyphus/cross_session/knowledge.json",
    ):
        """Initialize the task wrapper.

        Args:
            outcome_logger: Optional OutcomeLogger instance (created if not provided)
            adaptive_router: Optional AdaptiveRouter instance (created if not provided)
            outcomes_db: Path to outcomes database
            routing_db: Path to routing/learning database
            auto_route: Whether to call route_task() before task execution
            auto_log: Whether to log outcome after task completes
            auto_memory: Whether to enable MEMORY_BRIDGE memory (pre-read + post-write)
            memory_path: Path to cross-session knowledge file
        """
        self._outcome_logger = outcome_logger or OutcomeLogger(db_path=outcomes_db)
        self._adaptive_router = adaptive_router or AdaptiveRouter(
            db_path=routing_db,
            outcome_logger=self._outcome_logger,
        )
        self._auto_route = auto_route
        self._auto_log = auto_log
        self._auto_memory = auto_memory
        self._memory_path = Path(memory_path)
        self._memory_cache: list[dict[str, Any]] = []
        self._load_memory()

    # =========================================================================
    # MEMORY_BRIDGE MEMORY METHODS
    # =========================================================================

    def _load_memory(self) -> None:
        """Load cross-session knowledge from JSON file."""
        if not self._auto_memory:
            return
        try:
            if self._memory_path.exists():
                with open(self._memory_path) as f:
                    self._memory_cache = json.load(f)
                logger.info(f"MEMORY_BRIDGE loaded {len(self._memory_cache)} memories")
        except Exception as e:
            logger.warning(f"Failed to load memory: {e}")
            self._memory_cache = []

    def _save_memory(self) -> None:
        """Save cross-session knowledge to JSON file."""
        if not self._auto_memory:
            return
        try:
            self._memory_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._memory_path, "w") as f:
                json.dump(self._memory_cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    def pre_read_memory(self, query: str, top_k: int = 5) -> str:
        """MEMORY_BRIDGE PRE-READ: Search memory for relevant context.

        Called BEFORE task execution to inject relevant context.
        Uses the FULL unified-memory system with TEMPR hybrid search.

        Args:
            query: The task description to search for
            top_k: Number of top memories to retrieve

        Returns:
            Formatted memory context string to prepend to prompt
        """
        if not self._auto_memory:
            return ""

        # === BLEEDING EDGE: Use actual unified-memory router ===
        try:
            from packages.memory_core.router import MemoryRouter, UnifiedMemoryQuery
            from packages.memory_core.retrievers.fusion import TEMPRRetriever

            router = MemoryRouter()
            uq = UnifiedMemoryQuery(query=query, max_results_per_source=top_k)
            results = router.search(uq)

            if not results.results:
                return ""

            # Format as memory context
            lines = [
                "[MEMORY_BRIDGE MEMORY - Relevant context from previous sessions]:\n"
            ]
            for r in results.results:
                lines.append(
                    f"- {r.content[:300]} "
                    f"(source: {r.source}, score: {r.relevance_score:.2f})"
                )
            lines.append("")

            logger.info(
                f"MEMORY_BRIDGE pre-read: found {len(results.results)} "
                f"memories from {results.sources_queried}"
            )
            return "\n".join(lines)

        except Exception as e:
            logger.warning(f"Unified memory search failed: {e}, falling back to cache")
            # Fallback to simple keyword search from cache
            return self._pre_read_fallback(query, top_k)

    def _pre_read_fallback(self, query: str, top_k: int = 5) -> str:
        """Simple keyword-based fallback search."""
        if not self._memory_cache:
            return ""

        # Simple keyword-based search (no embeddings needed)
        query_lower = query.lower()
        scored = []
        for mem in self._memory_cache:
            content_lower = mem.get("content", "").lower()
            # Score: exact matches > partial matches > any overlap
            score = 0
            query_words = set(query_lower.split())
            content_words = set(content_lower.split())

            # Exact query in content
            if query_lower in content_lower:
                score = 1.0
            # Word overlap
            elif query_words & content_words:
                score = len(query_words & content_words) / max(
                    len(query_words), len(content_words)
                )
            # Any query word in content
            elif any(w in content_lower for w in query_words if len(w) > 3):
                score = 0.3

            if score > 0:
                scored.append((score, mem))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        top_memories = scored[:top_k]

        if not top_memories:
            return ""

        # Format as memory context
        lines = ["[MEMORY_BRIDGE MEMORY - Relevant context from previous sessions]:\n"]
        for score, mem in top_memories:
            lines.append(
                f"- {mem.get('content', '')} (source: {mem.get('source_session', 'unknown')})"
            )
        lines.append("")

        return "\n".join(lines)

    def post_write_memory(
        self,
        task_id: str,
        description: str,
        outcome: str,
        success: bool,
    ) -> None:
        """MEMORY_BRIDGE POST-WRITE: Store task outcome in memory with vector embedding.

        Called AFTER task execution to persist knowledge.
        BLEEDING EDGE: Writes to vector store + SQLite for semantic search.

        Args:
            task_id: The task ID
            description: What was attempted
            outcome: What happened/was learned
            success: Whether it succeeded
        """
        if not self._auto_memory:
            return

        content = f"{description}: {outcome}"

        # === BLEEDING EDGE: Write to vector store for semantic search ===
        try:
            # Try to write to vector store with embedding
            self._write_to_vector_store(task_id, content)
        except Exception as e:
            logger.warning(f"Vector store write failed: {e}")

        # Always write to JSON cache as fallback
        knowledge_entry = {
            "id": task_id[:8],
            "source_session": "hivemind-active",
            "content": content,
            "knowledge_type": "outcome",
            "confidence": 0.9 if success else 0.5,
            "transferability_score": 0.8,
            "occurrence_count": 1,
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "outcome": "success" if success else "failed",
                "task_id": task_id,
            },
        }

        self._memory_cache.append(knowledge_entry)
        self._save_memory()
        logger.info(
            f"MEMORY_BRIDGE stored memory: {task_id[:8]} - {description[:30]}..."
        )

    def _write_to_vector_store(self, task_id: str, content: str) -> None:
        """Write memory to vector store with Ollama embeddings."""
        try:
            import requests

            # Generate embedding with Ollama
            resp = requests.post(
                "http://localhost:11434/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": content},
                timeout=10,
            )
            if resp.status_code != 200:
                logger.warning(f"Ollama embedding failed: {resp.status_code}")
                return

            embedding = resp.json().get("embedding", [])
            if not embedding:
                return

            # Write to SQLite with vector
            from packages.memory_core.stores.vector_store import VectorIndex

            db_path = ".sisyphus/hivemind_vectors.db"
            idx = VectorIndex(db_path=db_path)
            idx.add(
                ids=[task_id[:8]],
                embeddings=[embedding],
                texts=[content],
                metadata=[{"source": "hivemind", "task_id": task_id}],
            )
            logger.info(f"MEMORY_BRIDGE vector stored: {task_id[:8]}")

        except Exception as e:
            logger.debug(f"Vector store write skipped: {e}")

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

        # === MEMORY_BRIDGE PRE-READ: Inject relevant memory context ===
        if self._auto_memory:
            try:
                memory_context = self.pre_read_memory(description, top_k=5)
                if memory_context:
                    context["hivemind_memory"] = memory_context
                    logger.info(
                        f"MEMORY_BRIDGE pre-read injected for: {description[:50]}"
                    )
            except Exception as e:
                logger.debug(f"MEMORY_BRIDGE pre-read skipped: {e}")

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

        # === MEMORY_BRIDGE POST-WRITE: Store outcome in memory ===
        if self._auto_memory:
            try:
                outcome_text = (
                    f"SUCCESS" if final_success else f"FAILED: {error or 'unknown'}"
                )
                self.post_write_memory(
                    task_id=task_id,
                    description=task_ctx.description,
                    outcome=outcome_text,
                    success=final_success,
                )
            except Exception as e:
                logger.debug(f"MEMORY_BRIDGE post-write skipped: {e}")

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

"""Agent Context Middleware — Auto-inject cross-session context into agent executions.

This middleware aggregates context from multiple cross-session sources and provides
methods to inject this context into agent prompts or agent loop initialization.

Usage:
    from packages.orchestration.agent_context_middleware import AgentContextMiddleware

    middleware = AgentContextMiddleware()

    # Get formatted context for a task
    context_block = middleware.get_context_for_task("implement JWT auth")

    # Inject into agent loop initial context
    enhanced_context = middleware.inject_into_agent_loop([
        {"role": "system", "content": "You are a coding assistant"}
    ])

Sources:
    - ContextSharing: recent sessions, shared context
    - CrossSessionTransfer: transferable knowledge from past sessions
    - BMAD ContextInjector: Athena memory bank context
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Cache TTL in seconds (5 minutes)
CONTEXT_CACHE_TTL = 300


class AgentContextMiddleware:
    """Middleware for injecting cross-session context into agent executions.

    Aggregates context from:
    - ContextSharing: recent sessions and shared global knowledge
    - CrossSessionTransfer: transferable knowledge from past sessions
    - BMAD ContextInjector: Athena memory bank context

    Provides caching to avoid repeated expensive context lookups.
    """

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the middleware.

        Args:
            project_root: Path to project root. Defaults to standard location.
        """
        self.project_root = project_root or Path(__file__).parent.parent.parent

        # Lazy-loaded sources
        self._context_sharing = None
        self._cross_session_transfer = None
        self._bmad_injector = None
        self._nx_brain_injector = None  # Phase 2.3: N-Xyme brain memory injection

        # Cache for context blocks
        self._context_cache: Dict[str, tuple[float, str]] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    @property
    def context_sharing(self):
        """Lazy-load ContextSharing."""
        if self._context_sharing is None:
            try:
                from packages.intelligence.delegation.context_sharing import (
                    ContextSharing,
                    get_context_sharing,
                )

                self._context_sharing = get_context_sharing()
            except ImportError as e:
                logger.debug(f"ContextSharing not available: {e}")
                self._context_sharing = None
        return self._context_sharing

    @property
    def cross_session_transfer(self):
        """Lazy-load CrossSessionTransfer."""
        if self._cross_session_transfer is None:
            try:
                from packages.learning_engine.cross_session_transfer import (
                    CrossSessionTransfer,
                    activate_for_session,
                )

                self._cross_session_transfer = activate_for_session
            except ImportError as e:
                logger.debug(f"CrossSessionTransfer not available: {e}")
                self._cross_session_transfer = None
        return self._cross_session_transfer

    @property
    def bmad_injector(self):
        """Lazy-load BMAD ContextInjector."""
        if self._bmad_injector is None:
            try:
                from packages.orchestration.bmad.context_injector import (
                    ContextInjector,
                    get_injector,
                )

                self._bmad_injector = get_injector()
            except ImportError as e:
                logger.debug(f"BMAD ContextInjector not available: {e}")
                self._bmad_injector = None
        return self._bmad_injector

    @property
    def nx_brain_injector(self):
        """Lazy-load N-Xyme brain memory injector (Phase 2.3)."""
        if self._nx_brain_injector is None:
            try:
                from packages.brain_mcp.namespaces.fingerprint import (
                    get_full_injected_context as orchestration_get_injected_context,
                )

                self._nx_brain_injector = orchestration_get_injected_context
            except ImportError as e:
                logger.debug(f"N-Xyme brain injector not available: {e}")
                self._nx_brain_injector = None
        return self._nx_brain_injector

    def _get_cached_context(self, task_description: str) -> Optional[str]:
        """Get cached context if not expired.

        Args:
            task_description: Task description used as cache key.

        Returns:
            Cached context string if valid, None if expired/missing.
        """
        cache_key = task_description[:100]  # Truncate long keys

        if cache_key in self._context_cache:
            timestamp, context = self._context_cache[cache_key]
            if time.time() - timestamp < CONTEXT_CACHE_TTL:
                self._cache_hits += 1
                logger.debug(f"Context cache hit for: {cache_key[:50]}")
                return context
            else:
                # Expired
                del self._context_cache[cache_key]

        self._cache_misses += 1
        return None

    def _set_cached_context(self, task_description: str, context: str) -> None:
        """Set cached context with current timestamp.

        Args:
            task_description: Task description used as cache key.
            context: Context string to cache.
        """
        cache_key = task_description[:100]
        self._context_cache[cache_key] = (time.time(), context)
        logger.debug(f"Cached context for: {cache_key[:50]}")

    def _fetch_from_context_sharing(self) -> List[str]:
        """Fetch context from ContextSharing source.

        Returns:
            List of formatted context strings.
        """
        if self.context_sharing is None:
            return []

        contexts = []

        try:
            # Get recent sessions
            recent = self.context_sharing.get_recent_sessions(limit=3)
            if recent:
                contexts.append("## Recent Sessions")
                for session in recent:
                    session_id = session.get("session_id", "unknown")
                    summary = session.get("summary", "")
                    active_tasks = session.get("active_tasks", [])

                    block = f"- {session_id}: {summary}"
                    if active_tasks:
                        block += f" (tasks: {', '.join(active_tasks[:3])})"
                    contexts.append(block)
                contexts.append("")
        except Exception as e:
            logger.warning(f"Failed to get recent sessions: {e}")

        try:
            # Get shared context
            shared = self.context_sharing.get_shared_context()
            if shared and any(shared.values()):
                contexts.append("## Shared Knowledge")

                if shared.get("global_knowledge"):
                    contexts.append("### Global Knowledge")
                    for key, value in list(shared["global_knowledge"].items())[:5]:
                        contexts.append(f"- {key}: {value}")

                if shared.get("best_practices"):
                    contexts.append("### Best Practices")
                    for practice in shared["best_practices"][:3]:
                        contexts.append(f"- {practice}")

                if shared.get("common_patterns"):
                    contexts.append("### Common Patterns")
                    for pattern in shared["common_patterns"][:3]:
                        contexts.append(f"- {pattern}")

                contexts.append("")
        except Exception as e:
            logger.warning(f"Failed to get shared context: {e}")

        return contexts

    def _fetch_from_cross_session_transfer(self, task_description: str) -> List[str]:
        """Fetch context from CrossSessionTransfer source.

        Args:
            task_description: Current task for relevance scoring.

        Returns:
            List of formatted context strings.
        """
        if self.cross_session_transfer is None:
            return []

        contexts = []

        try:
            # Activate transfer for current task
            activated = self.cross_session_transfer(task_description, min_score=0.5)

            if activated:
                contexts.append("## Transferable Knowledge")
                contexts.append("*From past sessions:*")

                for item in activated[:5]:
                    content = item.get("content", "")
                    knowledge_type = item.get("knowledge_type", "unknown")
                    confidence = item.get("confidence", 0)

                    contexts.append(
                        f"- [{knowledge_type} conf:{confidence:.2f}] {content}"
                    )

                contexts.append("")
        except Exception as e:
            logger.warning(f"Failed to activate cross-session transfer: {e}")

        return contexts

    def _fetch_from_bmad_injector(self) -> List[str]:
        """Fetch context from BMAD ContextInjector.

        Returns:
            List of formatted context strings.
        """
        if self.bmad_injector is None:
            return []

        contexts = []

        try:
            # Get injected context block
            block = self.bmad_injector.get_injected_context_block(context_type="all")

            if block and block != "# No context available":
                contexts.append(block)
                contexts.append("")
        except Exception as e:
            logger.warning(f"Failed to get BMAD injected context: {e}")

        return contexts

    def _fetch_from_nx_brain_injector(self, task_description: str) -> List[str]:
        """Fetch context from N-Xyme brain memory injector (Phase 2.3).

        Args:
            task_description: Current task for context matching.

        Returns:
            List of formatted context strings.
        """
        if self.nx_brain_injector is None:
            return []

        contexts = []

        try:
            # Get injected context from N-Xyme brain
            result = self.nx_brain_injector(agent="agent_loop", task=task_description)

            injected = (
                result.get("injected_context", "") if isinstance(result, dict) else ""
            )

            if injected:
                contexts.append("[N-Xyme Brain Memory]")
                contexts.append(injected)
                contexts.append("")
        except Exception as e:
            logger.warning(f"Failed to get N-Xyme brain injected context: {e}")

        return contexts

    def get_context_for_task(self, task_description: str) -> str:
        """Get formatted cross-session context for a task.

        Aggregates context from all sources and returns a formatted block
        suitable for prepending to an agent prompt.

        Args:
            task_description: Description of current task/message.

        Returns:
            Formatted context block string. Empty string if no context available.
        """
        # Check cache first
        cached = self._get_cached_context(task_description)
        if cached is not None:
            return cached

        logger.info(f"Building context for task: {task_description[:50]}")

        all_contexts: List[str] = []

        # Fetch from all sources in parallel (conceptually)
        # Phase 2.3: Added N-Xyme brain memory injection
        all_contexts.extend(self._fetch_from_context_sharing())
        all_contexts.extend(self._fetch_from_cross_session_transfer(task_description))
        all_contexts.extend(self._fetch_from_bmad_injector())
        all_contexts.extend(self._fetch_from_nx_brain_injector(task_description))

        # Build final context block
        if not all_contexts:
            logger.debug("No cross-session context available")
            result = ""
        else:
            result_lines = [
                "# Cross-Session Context",
                f"# Task: {task_description[:80]}",
                f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                "",
            ]
            result_lines.extend(all_contexts)
            result = "\n".join(result_lines)

        # Cache the result
        self._set_cached_context(task_description, result)

        return result

    def inject_into_agent_loop(
        self, initial_context: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Inject cross-session context into agent loop initial context.

        Takes an existing initial_context list (e.g., from agent configuration)
        and returns an enhanced list with cross-session context prepended.

        Args:
            initial_context: List of message dicts with role/content keys.

        Returns:
            Enhanced context list with cross-session context added.
        """
        if not initial_context:
            logger.warning("Empty initial_context passed to inject_into_agent_loop")
            return initial_context

        # Try to extract task description from context
        task_description = ""

        # Look for task in system message or first user message
        for msg in initial_context:
            content = msg.get("content", "")
            if isinstance(content, str):
                # Use first substantial content as task description
                if len(content) > 10 and not task_description:
                    task_description = content[:200]

        if not task_description:
            task_description = "general agent execution"

        # Get context block
        context_block = self.get_context_for_task(task_description)

        if not context_block:
            logger.debug("No context block to inject")
            return initial_context

        # Build enhanced context
        # Insert as second message (after any system prompt if present)
        enhanced: List[Dict[str, Any]] = []

        # Keep first message as-is (usually system)
        enhanced.append(initial_context[0])

        # Add cross-session context as context message
        enhanced.append(
            {
                "role": "system",
                "content": context_block,
                "source": "cross_session_context",
            }
        )

        # Add remaining original messages
        enhanced.extend(initial_context[1:])

        logger.info(
            f"Injected cross-session context into agent loop ({len(enhanced)} messages)"
        )
        return enhanced

    def clear_cache(self) -> None:
        """Clear the context cache."""
        self._context_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info("Context cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get middleware statistics.

        Returns:
            Dict with cache stats and source availability.
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0

        return {
            "cache": {
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "hit_rate": round(hit_rate, 3),
                "ttl_seconds": CONTEXT_CACHE_TTL,
            },
            "sources": {
                "context_sharing": self.context_sharing is not None,
                "cross_session_transfer": self.cross_session_transfer is not None,
                "bmad_injector": self.bmad_injector is not None,
            },
        }

    def invalidate_cache_for_task(self, task_description: str) -> None:
        """Invalidate cached context for a specific task.

        Args:
            task_description: Task description to invalidate.
        """
        cache_key = task_description[:100]
        if cache_key in self._context_cache:
            del self._context_cache[cache_key]
            logger.debug(f"Invalidated cache for: {cache_key[:50]}")


# Module-level convenience instance
_middleware: Optional[AgentContextMiddleware] = None


def get_middleware() -> AgentContextMiddleware:
    """Get the default middleware instance."""
    global _middleware
    if _middleware is None:
        _middleware = AgentContextMiddleware()
    return _middleware


def get_context_for_task(task_description: str) -> str:
    """Convenience function to get context for a task."""
    return get_middleware().get_context_for_task(task_description)


def inject_into_agent_loop(
    initial_context: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Convenience function to inject context into agent loop."""
    return get_middleware().inject_into_agent_loop(initial_context)


def clear_context_cache() -> None:
    """Convenience function to clear context cache."""
    get_middleware().clear_cache()


def get_middleware_stats() -> Dict[str, Any]:
    """Convenience function to get middleware stats."""
    return get_middleware().get_stats()

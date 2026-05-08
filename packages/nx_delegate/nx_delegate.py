"""N-Xyme Delegate MCP — Reliable task delegation wrapper.

This MCP wraps the UnifiedDelegationRouter to provide reliable task delegation
as a replacement for OMO's broken task() function (bug #16303).

Public API:
    nx_delegate(task_description) -> dict
    nx_delegate_record_outcome(task_id, task_description, level, agent, success) -> None
"""

__version__ = "1.0.0"

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger("nx_delegate_mcp")


def get_unified_router(container: Optional[Any] = None) -> Any:
    """Get or create the unified router via DI container."""
    try:
        from packages.core.di_container import get_container
    except ImportError:
        get_container = None

    if get_container is not None:
        c = container or get_container()
        if c.has("unified_router"):
            return c.get("unified_router")

    try:
        from packages.intelligence.router.unified import get_unified_router

        router = get_unified_router()
        if get_container is not None and container is None:
            c = get_container()
            c.register("unified_router", instance=router, singleton=True)
        return router
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to import UnifiedDelegationRouter: {e}")
        raise


def set_unified_router(router: Any, container: Optional[Any] = None) -> None:
    """Set router explicitly (for testing/mocking)."""
    try:
        from packages.core.di_container import get_container
    except ImportError:
        get_container = None

    if get_container is not None:
        c = container or get_container()
        c.register("unified_router", instance=router, singleton=True)


async def _route_task_async(
    task_description: str,
) -> Dict[str, Any]:
    """Route a task using the unified router (async version).

    Args:
        task_description: Description of the task to route.

    Returns:
        Dict with agent, level, confidence, strategy_used, reason, latency_ms
    """
    start_time = time.time()

    try:
        router = get_unified_router()
        decision = await router.route_task(task_description)

        latency_ms = (time.time() - start_time) * 1000

        result = {
            "agent": decision.agent,
            "level": decision.level,
            "confidence": decision.confidence,
            "strategy_used": decision.strategy_used,
            "reason": decision.reason,
            "latency_ms": latency_ms,
            "task_description": decision.task_description,
        }

        # Add optional fields if present
        if decision.subtasks:
            result["subtasks"] = decision.subtasks
        if decision.prompt:
            result["prompt"] = decision.prompt


        logger.info(
            f"Route decision: {decision.agent} (L{decision.level}, "
            f"conf={decision.confidence:.2f}, strategy={decision.strategy_used})"
        )

        return result

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error(f"Routing failed: {e}")

        # Fallback response
        return {
            "agent": "hephaestus",
            "level": 2,
            "confidence": 0.3,
            "strategy_used": "fallback",
            "reason": f"Routing failed: {str(e)}",
            "latency_ms": latency_ms,
            "task_description": task_description,
            "error": str(e),
        }


def nx_delegate(
    task_description: str,
) -> Dict[str, Any]:
    """Delegate a task to the optimal agent.

    This is the main MCP entry point. It wraps UnifiedDelegationRouter.route_task()
    and provides a synchronous interface while using async routing internally.

    Args:
        task_description: Required. Description of the task to delegate.

    Returns:
        Dict with:
            - agent: Selected agent name (e.g., "hephaestus", "explore")
            - level: Complexity level (1-5)
            - confidence: Confidence score (0.0-1.0)
            - strategy_used: Routing strategy used
            - reason: Human-readable reason for the decision
            - latency_ms: Routing time in milliseconds
            - task_description: Original task description
            - subtasks: Decomposed subtasks for complex tasks (if any)
            - prompt: Generated prompt template (if any)
            - context: Cross-session context for injection (if any)

    Example:
        >>> result = nx_delegate("fix the bug in auth.py")
        >>> print(result["agent"])  # "sisyphus-junior"
        >>> print(result["level"])  # 1
    """
    # Run async routing in sync context
    # FIX: Use existing event loop instead of creating new one with asyncio.run()
    try:
        # Try to get the running loop
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context - schedule the coroutine
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                # FIX: Proper async in thread - create new event loop instead of asyncio.run()
                def run_in_new_loop():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            _route_task_async(task_description)
                        )
                    finally:
                        new_loop.close()

                future = pool.submit(run_in_new_loop)
                return future.result(timeout=30)  # 30s timeout
        except RuntimeError:
            # No running loop - use get_event_loop() which may return existing or create new
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Loop exists but not in this thread - use ThreadPoolExecutor
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    # FIX: Proper async in thread - create new event loop instead of asyncio.run()
                    def run_in_new_loop():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(
                                _route_task_async(task_description)
                            )
                        finally:
                            new_loop.close()

                    future = pool.submit(run_in_new_loop)
                    return future.result(timeout=30)
            else:
                # Loop exists and is not running - safe to use run_until_complete
                return loop.run_until_complete(
                    _route_task_async(task_description)
                )
    except Exception:
        # Final fallback: always use ThreadPoolExecutor - works in ALL contexts (async or not)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            def run_in_new_loop():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(_route_task_async(task_description))
                finally:
                    new_loop.close()
            future = pool.submit(run_in_new_loop)
            return future.result(timeout=30)


async def _record_outcome_async(
    task_id: str,
    task_description: str,
    level: int,
    agent: str,
    success: bool,
    error: Optional[str] = None,
    latency_ms: float = 0,
    tokens_used: int = 0,
) -> None:
    """Record delegation outcome for learning (async version)."""
    try:
        router = get_unified_router()
        await router.record_outcome(
            task_id=task_id,
            task_description=task_description,
            level=level,
            agent=agent,
            success=success,
            error=error,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
        )
        logger.info(
            f"Recorded outcome: {agent} -> {'success' if success else 'failed'}"
        )
    except Exception as e:
        logger.warning(f"Failed to record outcome: {e}")


def nx_delegate_record_outcome(
    task_id: str,
    task_description: str,
    level: int,
    agent: str,
    success: bool,
    error: Optional[str] = None,
    latency_ms: float = 0,
    tokens_used: int = 0,
) -> Dict[str, Any]:
    """Record the outcome of a delegation for learning.

    Call this after task completion to record the result and improve future routing.

    Args:
        task_id: Task ID from nx_delegate() response.
        task_description: Original task description.
        level: Complexity level (1-5).
        agent: Agent that handled the task.
        success: Whether the task completed successfully.
        error: Optional error message if failed.
        latency_ms: Execution time in milliseconds.
        tokens_used: Tokens consumed (optional).

    Returns:
        Dict with status and message.

    Example:
        >>> result = nx_delegate("fix typo in config.py")
        >>> # ... execute task ...
        >>> nx_delegate_record_outcome(
        ...     task_id="delegate_abc123",
        ...     task_description="fix typo in config.py",
        ...     level=1,
        ...     agent="sisyphus-junior",
        ...     success=True
        ... )
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                # FIX: Proper async in thread - create new event loop instead of asyncio.run()
                def run_in_new_loop():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            _record_outcome_async(
                                task_id,
                                task_description,
                                level,
                                agent,
                                success,
                                error,
                                latency_ms,
                                tokens_used,
                            )
                        )
                    finally:
                        new_loop.close()

                future = pool.submit(run_in_new_loop)
                future.result(timeout=30)  # 30s timeout
        else:
            loop.run_until_complete(
                _record_outcome_async(
                    task_id,
                    task_description,
                    level,
                    agent,
                    success,
                    error,
                    latency_ms,
                    tokens_used,
                )
            )
    except RuntimeError:
        # FIX: Use get_event_loop() instead of asyncio.run() to avoid nested event loop issues
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Loop is running in another thread - use ThreadPoolExecutor
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    # FIX: Proper async in thread - create new event loop instead of asyncio.run()
                    def run_in_new_loop():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(
                                _record_outcome_async(
                                    task_id,
                                    task_description,
                                    level,
                                    agent,
                                    success,
                                    error,
                                    latency_ms,
                                    tokens_used,
                                )
                            )
                        finally:
                            new_loop.close()

                    future = pool.submit(run_in_new_loop)
                    future.result(timeout=10)  # 10s timeout for record
            else:
                loop.run_until_complete(
                    _record_outcome_async(
                        task_id,
                        task_description,
                        level,
                        agent,
                        success,
                        error,
                        latency_ms,
                        tokens_used,
                    )
                )
        except Exception:
            # Final fallback: always use ThreadPoolExecutor - works in ALL contexts
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                def run_in_new_loop():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            _record_outcome_async(
                                task_id,
                                task_description,
                                level,
                                agent,
                                success,
                                error,
                                latency_ms,
                                tokens_used,
                            )
                        )
                    finally:
                        new_loop.close()
                future = pool.submit(run_in_new_loop)
                future.result(timeout=10)

    return {
        "status": "recorded",
        "task_id": task_id,
        "agent": agent,
        "success": success,
    }


def nx_delegate_with_id(
    task_description: str,
) -> Dict[str, Any]:
    """Delegate a task and return with a generated task_id.

    Convenience wrapper that adds a task_id to the response.

    Args:
        task_description: Required. Description of the task to delegate.

    Returns:
        Same as nx_delegate() plus:
            - task_id: Generated unique task ID
    """
    result = nx_delegate(task_description)
    result["task_id"] = f"delegate_{uuid.uuid4().hex[:12]}"
    return result


# Convenience exports
__all__ = [
    "__version__",
    "nx_delegate",
    "nx_delegate_record_outcome",
    "nx_delegate_with_id",
    "get_unified_router",
]


# Health check for MCP server
def health_check() -> Dict[str, Any]:
    """Health check for nx_delegate MCP."""
    try:
        router = get_unified_router()
        return {
            "status": "healthy",
            "message": "nx_delegate MCP operational",
            "router": "UnifiedDelegationRouter loaded",
        }
    except Exception as e:
        return {
            "status": "degraded",
            "message": f"nx_delegate MCP error: {e}",
            "router": "failed to load",
        }


# Standalone MCP server entry point
if __name__ == "__main__":
    import sys

    print("nx_delegate MCP v{}".format(__version__), file=sys.stderr)
    print("This module should be run as an MCP server.", file=sys.stderr)

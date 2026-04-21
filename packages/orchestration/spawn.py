"""
Spawn - Unified agent spawning with learning/memory integration

This module provides the canonical entry point for spawning agent tasks.
It ensures: route (from learning) → inject (memory) → execute → log (outcome)

Usage:
    from packages.orchestration.spawn import spawn

    result = await spawn(task="fix the login bug", context={})
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger("orchestration.spawn")


@dataclass
class SpawnResult:
    """Result from spawn"""

    success: bool
    agent: str
    output: Any
    duration_ms: int
    task_id: Optional[str] = None


async def spawn(
    task: str,
    context: Optional[Dict[str, Any]] = None,
    force_agent: Optional[str] = None,
) -> SpawnResult:
    """
    Unified spawn function with learning/memory integration.

    Flow:
    1. Get routing from learning system (route_task)
    2. Inject memory context (get_full_injected_context)
    3. Execute with agent
    4. Log outcome for Q-Learning (record_outcome)

    Args:
        task: Task description
        context: Optional context dict
        force_agent: Force specific agent (skip routing)

    Returns:
        SpawnResult with success, agent, output, duration
    """
    start_time = time.time()
    task_id = f"task_{int(start_time * 1000)}"

    # STEP 1: Get routing from learning system (NOT keyword matching)
    selected_agent = force_agent
    routing_level = 3

    if not force_agent:
        try:
            from packages.nx_routing import route_task

            routing_result = route_task(task_description=task)
            if routing_result:
                suggested = routing_result.agent
                level = routing_result.level
                if suggested in [
                    "hephaestus",
                    "sisyphus",
                    "oracle",
                    "explore",
                    "librarian",
                    "atlas",
                ]:
                    selected_agent = suggested
                    routing_level = level
                    logger.info(
                        f"Learning routing: {selected_agent} (L{routing_level})"
                    )
        except Exception as e:
            logger.warning(f"Learning routing failed, using fallback: {e}")

    # Fallback if still no agent
    if not selected_agent:
        selected_agent = _fallback_route(task)

    # STEP 2: Pre-dispatch memory injection (FAST PATH with fallback)
    # NOTE: fast_inject_context now wires to FULL brain in semantic layer
    # No need for redundant slow path - fast mode includes semantic with timeout
    memory_context = ""
    memory_source = "none"
    memory_latency = 0

    try:
        # Fast injector now includes L2 semantic with full brain wiring
        from packages.orchestration.fast_memory_injector import fast_inject_context

        fast_result = await asyncio.wait_for(
            fast_inject_context(
                agent=selected_agent,
                task=task,
                max_tokens=500,  # Full budget now that semantic is integrated
                speed_mode="balanced",  # balanced = tries semantic first
            ),
            timeout=0.4,  # 400ms - enough for semantic
        )

        if fast_result.injected_context:
            memory_context = fast_result.injected_context
            memory_source = fast_result.source
            memory_latency = fast_result.latency_ms
            logger.info(f"Memory: {memory_source} ({memory_latency}ms)")

    except asyncio.TimeoutError:
        logger.debug("Memory injection timeout, continuing without")
    except Exception as e:
        logger.debug(f"Memory injection failed: {e}")

    # Merge memory into context
    enhanced_context = {
        **(context or {}),
        "memory_injection": memory_context,
        "memory_source": memory_source,
        "memory_latency_ms": memory_latency,
    }

    # P0: Pre-task injection from learned patterns (task_hooks)
    task_hooks_context = ""
    try:
        from packages.orchestration.task_hooks import inject_before_task

        task_hooks_context = inject_before_task(task, selected_agent)
        if task_hooks_context:
            enhanced_context["task_hooks_injection"] = task_hooks_context
            logger.debug(f"Task hooks injected: {len(task_hooks_context)} chars")
    except Exception as e:
        logger.debug(f"Task hooks injection failed: {e}")

    # STEP 3: Execute with agent using WorkerPool
    try:
        from packages.orchestration.agents.pool import WorkerPool

        # Get or create pool instance
        if not hasattr(spawn, "_pool"):
            spawn._pool = WorkerPool(pool_sizes={selected_agent: 1})
            spawn._pool.start_pool()

        # Submit task to pool and wait for result
        task_id = spawn._pool.submit_task(
            task={
                "id": task_id,
                "agent_type": selected_agent,
                "payload": {
                    "task": task,
                    "context": enhanced_context,
                },
            },
            agent_type=selected_agent,
        )

        # Get result via future (synchronous wait)
        with spawn._pool._lock:
            future = spawn._pool._worker_futures.get(task_id)
        if future:
            result = future.result(timeout=120)
            output = result.to_dict() if hasattr(result, "to_dict") else result
            success = result.success if hasattr(result, "success") else True
        else:
            # Fallback: get from pool status
            status = spawn._pool.get_pool_status()
            output = {"status": "completed", "pool_status": status.to_dict()}
            success = True
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        output = {"error": str(e)}
        success = False

    duration_ms = int((time.time() - start_time) * 1000)

    # STEP 4: Log outcome for Q-Learning (MANDATORY)
    try:
        from packages.nx_routing import record_outcome as _record_outcome

        # nx_routing.record_outcome is synchronous
        _record_outcome(
            task_description=task[:200],
            agent=selected_agent,
            level=routing_level,
            success=success,
            latency_ms=duration_ms,
            tokens_used=0,
        )
        logger.info(
            f"Outcome logged: {selected_agent} -> {'success' if success else 'failed'}"
        )

        # P0: Auto-trigger training when threshold met (50+ sequences)
        try:
            from packages.training.training_trigger import check_and_trigger_training

            training_result = check_and_trigger_training()
            if training_result.get("status") == "success":
                logger.info(
                    f"Auto-training triggered: {training_result.get('examples_generated')} examples"
                )
            elif training_result.get("status") == "waiting":
                logger.debug(
                    f"Training waiting: {training_result.get('pending')}/{training_result.get('threshold')}"
                )
        except Exception as e:
            logger.debug(f"Training trigger check failed: {e}")

    except Exception as e:
        logger.error(f"Failed to log outcome: {e}")

    return SpawnResult(
        success=success,
        agent=selected_agent,
        output=output,
        duration_ms=duration_ms,
        task_id=task_id,
    )


def _fallback_route(task: str) -> str:
    """Keyword matching fallback - used only if learning fails"""
    task_lower = task.lower()
    if "typo" in task_lower or "fix" in task_lower and len(task.split()) < 5:
        return "sisyphus-junior"
    elif "implement" in task_lower or "create" in task_lower or "add" in task_lower:
        return "hephaestus"
    elif "fix" in task_lower or "bug" in task_lower or "error" in task_lower:
        return "hephaestus"
    elif "explain" in task_lower or "how" in task_lower or "what" in task_lower:
        return "explore"
    elif "research" in task_lower or "find" in task_lower or "search" in task_lower:
        return "explore"
    elif "review" in task_lower or "analyze" in task_lower:
        return "oracle"
    else:
        return "hephaestus"


# Export
__all__ = ["spawn", "SpawnResult"]

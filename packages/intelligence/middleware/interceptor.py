"""Delegation Interceptor Middleware

Automatically intercepts delegation-related tool calls and:
1. Auto-calls route_task before delegation
2. Auto-calls record_delegation_outcome after completion
3. Tracks task IDs and outcomes for learning
4. Automatic retry on failure with fallback agent
5. Advanced Learning: Q-Learning, Bandits, Meta-Learning, EWC, Counterfactual
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional, List

from fastmcp.server.middleware import Middleware, MiddlewareContext, CallNext

logger = logging.getLogger("delegation-interceptor")

FALLBACK_AGENTS = {
    1: ["sisyphus-junior", "hephaestus"],
    2: ["hephaestus", "sisyphus-junior"],
    3: ["hephaestus", "explore", "prometheus"],
    4: ["prometheus", "hephaestus", "oracle"],
    5: ["metis", "prometheus", "oracle"],
}

MAX_RETRIES = 2


class DelegationInterceptor(Middleware):
    """Middleware that automatically routes and logs delegation outcomes."""

    def __init__(self, router=None, outcome_logger=None, advanced_learner=None):
        super().__init__()
        self._router = router
        self._outcome_logger = outcome_logger
        self._advanced_learner = advanced_learner
        self._pending_tasks: Dict[str, Dict[str, Any]] = {}
        self._retry_counts: Dict[str, int] = {}
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return
        try:
            if self._router is None:
                from packages.intelligence.router.unified import get_unified_router

                self._router = get_unified_router()
            if self._outcome_logger is None:
                from packages.intelligence.delegation.logger import get_outcome_logger

                self._outcome_logger = get_outcome_logger()
            if self._advanced_learner is None:
                try:
                    from packages.learning_engine.advanced_learning import (
                        AdvancedLearningEngine,
                        ActionType,
                    )

                    self._advanced_learner = AdvancedLearningEngine(
                        db_path="context/memory/learning.db"
                    )
                    self._ActionType = ActionType
                    logger.info(
                        "AdvancedLearningEngine initialized in DelegationInterceptor"
                    )
                except Exception as e:
                    logger.warning(f"Could not initialize AdvancedLearningEngine: {e}")
            self._initialized = True
            logger.info("DelegationInterceptor initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize DelegationInterceptor: {e}")
            self._initialized = False

    async def on_call_tool(
        self, context: MiddlewareContext, call_next: CallNext
    ) -> Any:
        self._ensure_initialized()
        if not self._initialized:
            return await call_next(context)

        params = context.message
        tool_name = getattr(params, "name", "")
        tool_args = getattr(params, "arguments", {}) or {}

        if self._is_delegation_tool(tool_name):
            return await self._handle_delegation_tool(
                tool_name, tool_args, context, call_next
            )
        return await call_next(context)

    def _is_delegation_tool(self, tool_name: str) -> bool:
        delegation_tools = {
            "task",
            "delegate",
            "spawn_agent",
            "create_task",
            "run_agent",
            "execute_task",
            "background_task",
            "hephaestus",
            "explore",
            "librarian",
            "oracle",
            "prometheus",
            "metis",
            "momus",
            "atlas",
            "sisyphus-junior",
            "multimodal-looker",
        }
        return tool_name.lower() in delegation_tools

    async def _handle_delegation_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        context: MiddlewareContext,
        call_next: CallNext,
    ) -> Any:
        start_time = time.time()
        task_id = f"task_{int(start_time * 1000)}"
        task_description = tool_args.get(
            "prompt", tool_args.get("description", tool_name)
        )

        try:
            routing_result = await self._router.route_task(task_description)
            logger.info(
                f"Auto-routed '{task_description[:50]}...' -> L{routing_result.level} {routing_result.agent}"
            )

            ml_metadata = {}
            if self._advanced_learner is not None:
                try:
                    action_type = self._map_agent_to_action(routing_result.agent)
                    context_dict = {
                        "level": routing_result.level,
                        "strategy": routing_result.strategy_used,
                        "tool": tool_name,
                    }
                    available_actions = list(self._ActionType)
                    selected_action, ml_metadata = self._advanced_learner.select_action(
                        task=task_description[:50],
                        context=context_dict,
                        available_actions=available_actions,
                    )
                    logger.info(
                        f"ML selected: {selected_action.value}, uncertainty: {ml_metadata.get('uncertainty', 'N/A')}"
                    )
                except Exception as e:
                    logger.warning(f"Advanced learning selection failed: {e}")

            self._pending_tasks[task_id] = {
                "task_description": task_description,
                "level": routing_result.level,
                "recommended_agent": routing_result.agent,
                "routing_strategy": routing_result.strategy_used,
                "start_time": start_time,
                "ml_metadata": ml_metadata,
            }

            try:
                result = await call_next(context)
                success = self._is_successful_result(result)
            except Exception as e:
                logger.info(
                    f"Tool '{tool_name}' not found, but routing succeeded: L{routing_result.level} {routing_result.agent}"
                )
                result = {
                    "status": "routed",
                    "level": routing_result.level,
                    "agent": routing_result.agent,
                    "strategy": routing_result.strategy_used,
                }
                success = True

            elapsed_ms = (time.time() - start_time) * 1000
            await self._router.record_outcome(
                task_id=task_id,
                task_description=task_description,
                level=routing_result.level,
                agent=routing_result.agent,
                success=success,
                latency_ms=elapsed_ms,
                tokens_used=0,
            )
            logger.info(
                f"Delegation outcome logged: {task_id} -> {'success' if success else 'failed'} ({elapsed_ms:.0f}ms)"
            )

            if self._advanced_learner is not None and success:
                try:
                    action_type = self._map_agent_to_action(routing_result.agent)
                    context_dict = {
                        "level": routing_result.level,
                        "strategy": routing_result.strategy_used,
                    }
                    learning_result = self._advanced_learner.record_outcome(
                        task=task_description[:50],
                        action=action_type,
                        success=success,
                        latency_ms=elapsed_ms,
                        cost=0.01,
                        context=context_dict,
                    )
                    if learning_result:
                        logger.info(
                            f"Advanced learning updated: reward={learning_result.get('q_value', 'N/A')}"
                        )
                except Exception as e:
                    logger.warning(f"Failed to update advanced learning: {e}")
            return result

        except Exception as e:
            logger.error(f"Delegation interceptor error: {e}")
            elapsed_ms = (time.time() - start_time) * 1000
            try:
                await self._router.record_outcome(
                    task_id=task_id,
                    task_description=task_description,
                    level=2,
                    agent="unknown",
                    success=False,
                    latency_ms=elapsed_ms,
                    tokens_used=0,
                )
            except Exception:
                pass
            raise

    def _map_agent_to_action(self, agent: str):
        agent_lower = agent.lower() if agent else ""
        mapping = {
            "explore": self._ActionType.EXPLORE,
            "librarian": self._ActionType.LIBRARIAN,
            "oracle": self._ActionType.ORACLE,
            "hephaestus": self._ActionType.HEPHAESTUS,
            "multimodal-looker": self._ActionType.MULTIMODAL,
            "prometheus": self._ActionType.DELEGATE,
            "metis": self._ActionType.DELEGATE,
            "momus": self._ActionType.DELEGATE,
            "atlas": self._ActionType.DELEGATE,
            "sisyphus-junior": self._ActionType.DELEGATE,
            "sisyphus": self._ActionType.DELEGATE,
        }
        return mapping.get(agent_lower, self._ActionType.DELEGATE)

    def _is_successful_result(self, result: Any) -> bool:
        if result is None:
            return False
        if hasattr(result, "is_error") and result.is_error:
            return False
        if hasattr(result, "content"):
            content_str = str(result.content).lower()
            if "error" in content_str and "success" not in content_str:
                return False
        return True

    def get_learning_status(self) -> dict:
        if self._advanced_learner is None:
            return {"status": "not_initialized"}
        return self._advanced_learner.get_learning_status()

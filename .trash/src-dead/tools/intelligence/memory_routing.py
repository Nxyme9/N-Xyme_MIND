"""Memory-Augmented Routing — Uses past task outcomes to influence routing decisions."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("memory-routing")


@dataclass
class SimilarTask:
    """A similar past task."""
    task_description: str
    level: int
    agent: str
    success: bool
    error: Optional[str] = None
    timestamp: str = ""
    similarity: float = 0.0


@dataclass
class RoutingRecommendation:
    """Memory-influenced routing recommendation."""
    original_level: int
    recommended_level: int
    confidence: float
    reason: str
    similar_tasks: List[SimilarTask] = field(default_factory=list)
    fallback_to_keyword: bool = False


class MemoryAugmentedRouter:
    """Routes tasks using memory of past similar tasks."""

    def __init__(self, memory_search_fn=None, memory_record_fn=None):
        self._memory_search_fn = memory_search_fn
        self._memory_record_fn = memory_record_fn
        self._outcome_cache: Dict[str, List[SimilarTask]] = {}

        # Auto-wire to outcome logger if no functions provided
        if memory_search_fn is None or memory_record_fn is None:
            try:
                from src.tools.intelligence.outcome_logger import get_outcome_logger
                outcome_logger = get_outcome_logger()
                if memory_search_fn is None:
                    self._memory_search_fn = lambda query, limit=5: outcome_logger.get_outcomes(limit=limit * 2)
                if memory_record_fn is None:
                    async def _record_wrapper(task_id, task_description, level, agent, success, error=None, latency_ms=0, tokens_used=0):
                        return await outcome_logger.log_outcome(
                            task_id=task_id,
                            task_description=task_description,
                            level=level,
                            agent=agent,
                            success=success,
                            error=error,
                            latency_ms=latency_ms,
                            tokens_used=tokens_used
                        )
                    self._memory_record_fn = _record_wrapper
            except Exception as e:
                logger.warning(f"Failed to wire outcome logger to memory router: {e}")

    async def query_similar_tasks(self, task_description: str, limit: int = 5) -> List[SimilarTask]:
        """Find similar past tasks from memory."""
        cache_key = task_description.lower()[:50]
        if cache_key in self._outcome_cache:
            return self._outcome_cache[cache_key]

        try:
            if self._memory_search_fn:
                search_result = self._memory_search_fn(query=f"delegation task: {task_description}", limit=limit * 2)
                if asyncio.iscoroutine(search_result):
                    results = await search_result
                else:
                    results = search_result
                
                # Handle both dict and list return types
                if isinstance(results, dict):
                    outcome_list = results.get("results", [])
                elif isinstance(results, list):
                    outcome_list = results
                else:
                    outcome_list = []
                
                similar_tasks = []
                for result in outcome_list:
                    task = self._parse_task_outcome(result)
                    if task:
                        similar_tasks.append(task)
                self._outcome_cache[cache_key] = similar_tasks[:limit]
                return similar_tasks[:limit]
            return []
        except Exception as e:
            logger.warning(f"Memory search failed: {e}")
            return []

    async def get_routing_recommendation(self, task_description: str, current_level: int) -> RoutingRecommendation:
        """Get memory-influenced routing recommendation."""
        try:
            similar_tasks = await self.query_similar_tasks(task_description)
            if not similar_tasks:
                return RoutingRecommendation(
                    original_level=current_level, recommended_level=current_level,
                    confidence=0.5, reason="No similar tasks found in memory", fallback_to_keyword=True
                )

            success_rate = sum(1 for t in similar_tasks if t.success) / len(similar_tasks)
            if success_rate < 0.5:
                recommended_level = min(current_level + 1, 5)
                reason = f"Low success rate ({success_rate:.0%}) for similar tasks"
            elif success_rate > 0.8:
                recommended_level = max(current_level - 1, 1)
                reason = f"High success rate ({success_rate:.0%}) for similar tasks"
            else:
                recommended_level = current_level
                reason = f"Moderate success rate ({success_rate:.0%})"

            return RoutingRecommendation(
                original_level=current_level, recommended_level=recommended_level,
                confidence=min(success_rate + 0.2, 1.0), reason=reason, similar_tasks=similar_tasks[:5]
            )
        except Exception as e:
            logger.warning(f"Routing recommendation failed: {e}")
            return RoutingRecommendation(
                original_level=current_level, recommended_level=current_level,
                confidence=0.3, reason=f"Memory routing failed: {e}", fallback_to_keyword=True
            )

    async def record_delegation_outcome(self, task_id: str, task_description: str, level: int, agent: str, success: bool, error: Optional[str] = None, latency_ms: float = 0, tokens_used: int = 0) -> bool:
        """Record delegation outcome to memory for future learning."""
        try:
            if self._memory_record_fn:
                await self._memory_record_fn(
                    task_id=task_id, task_description=task_description, level=level,
                    agent=agent, success=success, error=error, latency_ms=latency_ms, tokens_used=tokens_used
                )
                self._outcome_cache.clear()
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to record outcome: {e}")
            return False

    def _parse_task_outcome(self, memory_result: Dict[str, Any]) -> Optional[SimilarTask]:
        """Parse a memory result into a SimilarTask."""
        try:
            metadata = memory_result.get("metadata", {})
            return SimilarTask(
                task_description=metadata.get("task_description", memory_result.get("content", "")),
                level=metadata.get("level", 2), agent=metadata.get("agent", "unknown"),
                success=metadata.get("success", False), error=metadata.get("error"),
                timestamp=metadata.get("timestamp", ""), similarity=memory_result.get("score", 0.0)
            )
        except Exception as e:
            logger.warning(f"Failed to parse task outcome: {e}")
            return None


_memory_router: Optional[MemoryAugmentedRouter] = None

def get_memory_router() -> MemoryAugmentedRouter:
    """Get or create the global memory router."""
    global _memory_router
    if _memory_router is None:
        _memory_router = MemoryAugmentedRouter()
    return _memory_router

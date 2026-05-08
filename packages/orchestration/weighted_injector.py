"""
Weighted Memory Context Injection (WeightedInjector).

Memory-Weighted Context Injection with circuit breaker resilience.
Uses importance = success*1.0 + recency*0.5 + similarity*0.3.
Max 500 tokens.

Usage:
    from packages.orchestration.weighted_injector import WeightedInjector

    injector = WeightedInjector()
    context = injector.inject(agent="hephaestus", task="implement JWT auth")
    print(context)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

MAX_TOKENS = 500
TOKENS_PER_CHAR = 0.25
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 3
CIRCUIT_BREAKER_RECOVERY_SECONDS = 60


# ============================================================================
# Circuit Breaker State
# ============================================================================


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker for resilience."""

    failure_count: int = 0
    state: CircuitState = CircuitState.CLOSED
    last_failure_time: float = 0.0
    lock: Lock = field(default_factory=Lock)

    def record_success(self) -> None:
        with self.lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED
            logger.debug("Circuit breaker reset to CLOSED")

    def record_failure(self) -> None:
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= CIRCUIT_BREAKER_FAILURE_THRESHOLD:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker OPEN after {self.failure_count} failures"
                )
            else:
                logger.debug(f"Circuit failure count: {self.failure_count}")

    def can_execute(self) -> bool:
        with self.lock:
            if self.state == CircuitState.CLOSED:
                return True
            if self.state == CircuitState.OPEN:
                if (
                    time.time() - self.last_failure_time
                    > CIRCUIT_BREAKER_RECOVERY_SECONDS
                ):
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker HALF_OPEN")
                    return True
                return False
            return True


# ============================================================================
# Result Dataclass
# ============================================================================


@dataclass
class WeightedInjectionResult:
    """Result of weighted memory injection."""

    context_block: str
    memories_injected: int
    tokens_used: int
    within_budget: bool
    circuit_open: bool = False
    error: Optional[str] = None


# ============================================================================
# WeightedInjector
# ============================================================================


class WeightedInjector:
    """Memory-weighted context injection with circuit breaker.

    Features:
    - Importance scoring: success*1.0 + recency*0.5 + similarity*0.3
    - Max 500 tokens budget
    - Circuit breaker for resilience
    - Caching for repeated queries

    Attributes:
        MAX_TOKENS: Maximum tokens for injected context.
    """

    MAX_TOKENS = MAX_TOKENS

    _cache: Dict[str, str] = {}
    _cache_lock = Lock()
    _circuit_breaker: CircuitBreaker = CircuitBreaker()

    def __init__(
        self,
        max_tokens: int = MAX_TOKENS,
        memory_search_fn: Optional[Callable] = None,
    ) -> None:
        """Initialize weighted injector.

        Args:
            max_tokens: Maximum tokens for injected context (default: 500).
            memory_search_fn: Optional custom memory search function.
        """
        self.max_tokens = max_tokens
        self._memory_search_fn = memory_search_fn

    def _get_memory_search(self) -> Callable:
        """Get memory search function."""
        if self._memory_search_fn:
            return self._memory_search_fn

        try:
            from packages.brain_mcp.namespaces.memory import memory_search_memories

            return memory_search_memories
        except ImportError as e:
            logger.warning(f"Memory tools not available: {e}")
            raise

    def inject(self, agent: str, task: str) -> str:
        """Inject weighted context BEFORE agent dispatch.

        Performs:
        1. Check circuit breaker
        2. Search memory for relevant context
        3. Rank by importance (success*1.0 + recency*0.5 + similarity*0.3)
        4. Compress to 500 token budget
        5. Format context block

        Args:
            agent: Target agent name (e.g., "hephaestus", "oracle").
            task: Task description.

        Returns:
            Formatted context block for injection, or empty string if failure.
        """
        cache_key = f"{agent}:{task}"
        with WeightedInjector._cache_lock:
            if cache_key in WeightedInjector._cache:
                return WeightedInjector._cache[cache_key]

        if not WeightedInjector._circuit_breaker.can_execute():
            logger.debug("Circuit breaker OPEN, returning empty context")
            return ""

        try:
            result = self._do_inject(agent, task, cache_key)

            if result.error:
                WeightedInjector._circuit_breaker.record_failure()
                return ""
            else:
                WeightedInjector._circuit_breaker.record_success()

            return result.context_block

        except Exception as e:
            logger.error(f"Weighted injection failed: {e}")
            WeightedInjector._circuit_breaker.record_failure()
            return ""

    def _do_inject(
        self, agent: str, task: str, cache_key: str
    ) -> WeightedInjectionResult:
        """Execute injection logic."""
        search_fn = self._get_memory_search()

        try:
            search_result = search_fn(query=task, limit=10, strict=False, rerank=False)
        except Exception as e:
            return WeightedInjectionResult(
                context_block="",
                memories_injected=0,
                tokens_used=0,
                within_budget=True,
                error=str(e),
            )

        if isinstance(search_result, dict) and "error" in search_result:
            return WeightedInjectionResult(
                context_block="",
                memories_injected=0,
                tokens_used=0,
                within_budget=True,
                error=search_result.get("error"),
            )

        memories = (
            search_result.get("results", []) if isinstance(search_result, dict) else []
        )

        if not memories:
            return WeightedInjectionResult(
                context_block="",
                memories_injected=0,
                tokens_used=0,
                within_budget=True,
            )

        ranked = self._rank_by_importance(memories)
        compressed = self._compress_to_budget(ranked)

        formatted = self._format_context_block(agent, task, compressed)

        with WeightedInjector._cache_lock:
            WeightedInjector._cache[cache_key] = formatted
            if len(WeightedInjector._cache) > 100:
                for _ in range(20):
                    WeightedInjector._cache.pop(
                        next(iter(WeightedInjector._cache)), None
                    )

        return WeightedInjectionResult(
            context_block=formatted,
            memories_injected=compressed.memories_injected,
            tokens_used=compressed.tokens_used,
            within_budget=compressed.within_budget,
        )

    def _rank_by_importance(
        self, memories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rank memories by importance scoring.

        Formula: success * 1.0 + recency * 0.5 + similarity * 0.3

        Args:
            memories: List of memory dictionaries.

        Returns:
            Sorted list by importance descending.
        """
        ranked = []

        for mem in memories:
            metadata = mem.get("metadata", {})
            success = metadata.get("success", False)
            recency = metadata.get("recency_score", 0.5)
            similarity = metadata.get("similarity_score", 0.5)

            importance = (
                (1.0 if success else 0.0) * 1.0 + recency * 0.5 + similarity * 0.3
            )

            ranked.append(
                {
                    "id": mem.get("id"),
                    "content": mem.get("content", ""),
                    "importance": importance,
                    "timestamp": mem.get("created_at"),
                }
            )

        ranked.sort(key=lambda x: x["importance"], reverse=True)
        return ranked

    def _compress_to_budget(
        self, memories: List[Dict[str, Any]]
    ) -> WeightedInjectionResult:
        """Compress memories to fit 500 token budget."""
        context_parts: List[str] = []
        total_chars = 0

        for mem in memories:
            content = mem.get("content", "")
            if not content:
                continue

            new_chars = total_chars + len(content) + 50
            estimated_tokens = int(new_chars * TOKENS_PER_CHAR)

            if estimated_tokens > self.max_tokens:
                remaining = self.max_tokens - total_chars
                if remaining < 100:
                    break
                max_chars = int(remaining / TOKENS_PER_CHAR) - 50
                if max_chars > 50:
                    content = content[:max_chars] + "..."
                    new_chars = total_chars + len(content)
                    estimated_tokens = int(new_chars * TOKENS_PER_CHAR)
                else:
                    break

            context_parts.append(content)
            total_chars = new_chars

            if estimated_tokens > self.max_tokens:
                break

        context = "\n\n".join(context_parts)
        tokens_used = int(total_chars * TOKENS_PER_CHAR)

        return WeightedInjectionResult(
            context_block=context,
            memories_injected=len(context_parts),
            tokens_used=tokens_used,
            within_budget=tokens_used <= self.max_tokens,
        )

    def _format_context_block(
        self, agent: str, task: str, result: WeightedInjectionResult
    ) -> str:
        """Format context block for injection."""
        if not result.context_block:
            return ""

        lines = [
            "<!-- WEIGHTED CONTEXT -->",
            f"Agent: {agent}",
            f"Task: {task}",
            f"Memories: {result.memories_injected} | Tokens: {result.tokens_used}/{self.max_tokens}",
            "",
            result.context_block,
        ]

        return "\n".join(lines)

    def get_circuit_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return WeightedInjector._circuit_breaker.state

    def reset_circuit(self) -> None:
        """Manually reset circuit breaker."""
        WeightedInjector._circuit_breaker.record_success()
        logger.info("Circuit breaker manually reset")


# ============================================================================
# Convenience Functions
# ============================================================================


def inject_weighted(agent: str, task: str) -> str:
    """Convenience function for weighted injection.

    Args:
        agent: Target agent name.
        task: Task description.

    Returns:
        Formatted context block.
    """
    injector = WeightedInjector()
    return injector.inject(agent=agent, task=task)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys

    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "implement authentication"

    injector = WeightedInjector()
    result = injector.inject(agent="hephaestus", task=task)

    print(f"Task: {task}")
    print(f"Circuit: {injector.get_circuit_state().value}")
    print(f"Context:\n{result}")

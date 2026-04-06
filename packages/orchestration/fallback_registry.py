"""Fallback Registry — Tool and context fallback chains."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class FallbackStrategy(Enum):
    """Fallback execution strategies."""

    SEQUENTIAL = "sequential"  # Try each fallback in order
    PARALLEL = "parallel"  # Try all fallbacks in parallel, take first success


@dataclass
class FallbackEntry:
    """A single fallback entry."""

    name: str
    handler: Callable
    priority: int = 0
    timeout: float = 5.0
    enabled: bool = True


class FallbackChain:
    """Fallback chain for a single tool or context source."""

    def __init__(
        self, name: str, strategy: FallbackStrategy = FallbackStrategy.SEQUENTIAL
    ):
        self.name = name
        self.strategy = strategy
        self._fallbacks: list[FallbackEntry] = []

    def add(
        self, name: str, handler: Callable, priority: int = 0, timeout: float = 5.0
    ):
        """Add a fallback handler.

        Args:
            name: Fallback name.
            handler: Callable to execute.
            priority: Higher priority = tried first.
            timeout: Timeout in seconds.
        """
        self._fallbacks.append(
            FallbackEntry(
                name=name,
                handler=handler,
                priority=priority,
                timeout=timeout,
            )
        )
        # Sort by priority (highest first)
        self._fallbacks.sort(key=lambda f: f.priority, reverse=True)

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Execute fallback chain.

        Args:
            *args: Arguments to pass to handlers.
            **kwargs: Keyword arguments to pass to handlers.

        Returns:
            Result from first successful handler.

        Raises:
            Exception: If all handlers fail.
        """
        enabled = [f for f in self._fallbacks if f.enabled]
        if not enabled:
            raise RuntimeError(f"No enabled fallbacks for '{self.name}'")

        last_error = None
        for fallback in enabled:
            try:
                logger.debug(f"Fallback '{self.name}': Trying '{fallback.name}'")
                result = fallback.handler(*args, **kwargs)
                logger.debug(f"Fallback '{self.name}': '{fallback.name}' succeeded")
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"Fallback '{self.name}': '{fallback.name}' failed: {e}")

        raise RuntimeError(f"All fallbacks failed for '{self.name}': {last_error}")

    def get_status(self) -> dict:
        """Get fallback chain status."""
        return {
            "name": self.name,
            "strategy": self.strategy.value,
            "fallbacks": [
                {
                    "name": f.name,
                    "priority": f.priority,
                    "enabled": f.enabled,
                    "timeout": f.timeout,
                }
                for f in self._fallbacks
            ],
        }


class FallbackRegistry:
    """Registry for managing fallback chains."""

    def __init__(self):
        self._chains: dict[str, FallbackChain] = {}

    def get_or_create(
        self, name: str, strategy: FallbackStrategy = FallbackStrategy.SEQUENTIAL
    ) -> FallbackChain:
        """Get or create a fallback chain.

        Args:
            name: Chain name.
            strategy: Fallback strategy.

        Returns:
            FallbackChain for the name.
        """
        if name not in self._chains:
            self._chains[name] = FallbackChain(name, strategy)
        return self._chains[name]

    def get_all_status(self) -> dict[str, dict]:
        """Get status of all fallback chains."""
        return {name: chain.get_status() for name, chain in self._chains.items()}


# Global registry
_global_registry = FallbackRegistry()


def get_fallback_chain(name: str, **kwargs) -> FallbackChain:
    """Get or create a fallback chain from global registry."""
    return _global_registry.get_or_create(name, **kwargs)

"""Self-Healing — Automatic error recovery and prevention.

Based on docs Layer4-Self-Healing-Implementation.md.

Implements:
- Detect recurring errors and apply fixes
- Learn from past fixes to prevent future errors
- Circuit breaker patterns for failing components
- Automatic recovery strategies
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ErrorRecord:
    """Record of an error occurrence."""

    error_type: str
    error_message: str
    component: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    context: dict[str, Any] = field(default_factory=dict)
    fix_applied: str = ""
    fix_successful: bool = False


@dataclass
class HealingStrategy:
    """A strategy for healing a specific error."""

    error_pattern: str
    strategy_name: str
    action: Callable[[], bool]
    success_count: int = 0
    failure_count: int = 0
    last_used: str = ""

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / max(1, total)


class CircuitBreaker:
    """Circuit breaker pattern for failing components."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 60.0,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit.
            recovery_timeout_seconds: Time before attempting recovery.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self._failures: dict[str, int] = defaultdict(int)
        self._last_failure: dict[str, datetime] = {}
        self._state: dict[str, str] = defaultdict(
            lambda: "closed"
        )  # closed, open, half-open

    def can_execute(self, component: str) -> bool:
        """Check if a component can execute.

        Args:
            component: Component name.

        Returns:
            True if circuit is closed or half-open.
        """
        state = self._state[component]

        if state == "closed":
            return True

        if state == "open":
            last_failure = self._last_failure.get(component)
            if last_failure:
                elapsed = (datetime.now(timezone.utc) - last_failure).total_seconds()
                if elapsed >= self.recovery_timeout_seconds:
                    self._state[component] = "half-open"
                    return True
            return False

        # half-open
        return True

    def record_success(self, component: str) -> None:
        """Record a successful execution.

        Args:
            component: Component name.
        """
        self._failures[component] = 0
        self._state[component] = "closed"

    def record_failure(self, component: str) -> None:
        """Record a failed execution.

        Args:
            component: Component name.
        """
        self._failures[component] += 1
        self._last_failure[component] = datetime.now(timezone.utc)

        if self._failures[component] >= self.failure_threshold:
            self._state[component] = "open"
            logger.warning(
                f"Circuit breaker OPEN for {component} "
                f"({self._failures[component]} failures)"
            )

    def get_state(self, component: str) -> str:
        """Get circuit breaker state for a component."""
        return self._state[component]

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "components": {
                component: {
                    "state": self._state[component],
                    "failures": self._failures[component],
                }
                for component in set(
                    list(self._state.keys()) + list(self._failures.keys())
                )
            }
        }


class SelfHealing:
    """Self-healing system with automatic error recovery."""

    def __init__(self, storage_path: Path | None = None):
        """Initialize self-healing system.

        Args:
            storage_path: Path to store healing data.
        """
        self.storage_path = storage_path or Path(".sisyphus/self_healing")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.circuit_breaker = CircuitBreaker()
        self.error_history: list[ErrorRecord] = []
        self.strategies: list[HealingStrategy] = []
        self._load_data()

    def register_strategy(
        self,
        error_pattern: str,
        strategy_name: str,
        action: Callable[[], bool],
    ) -> HealingStrategy:
        """Register a healing strategy.

        Args:
            error_pattern: Error pattern to match.
            strategy_name: Strategy name.
            action: Action to execute for healing.

        Returns:
            Registered HealingStrategy.
        """
        strategy = HealingStrategy(
            error_pattern=error_pattern,
            strategy_name=strategy_name,
            action=action,
        )
        self.strategies.append(strategy)
        return strategy

    def handle_error(
        self,
        error_type: str,
        error_message: str,
        component: str,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Handle an error with automatic healing.

        Args:
            error_type: Type of error.
            error_message: Error message.
            component: Component that failed.
            context: Additional context.

        Returns:
            True if healing was successful.
        """
        # Record error
        record = ErrorRecord(
            error_type=error_type,
            error_message=error_message,
            component=component,
            context=context or {},
        )
        self.error_history.append(record)

        # Check circuit breaker
        if not self.circuit_breaker.can_execute(component):
            logger.warning(f"Circuit breaker open for {component}, skipping healing")
            return False

        # Find matching strategy
        strategy = self._find_strategy(error_type, error_message)
        if strategy:
            try:
                success = strategy.action()
                strategy.success_count += 1 if success else 0
                strategy.failure_count += 0 if success else 1
                strategy.last_used = datetime.now(timezone.utc).isoformat()

                record.fix_applied = strategy.strategy_name
                record.fix_successful = success

                if success:
                    self.circuit_breaker.record_success(component)
                    logger.info(f"Healed {component}: {strategy.strategy_name}")
                else:
                    self.circuit_breaker.record_failure(component)
                    logger.warning(
                        f"Healing failed for {component}: {strategy.strategy_name}"
                    )

                return success
            except Exception as e:
                strategy.failure_count += 1
                self.circuit_breaker.record_failure(component)
                logger.error(f"Healing strategy error: {e}")
                return False

        # No strategy found, record failure
        self.circuit_breaker.record_failure(component)
        return False

    def get_recurring_errors(
        self, window_hours: int = 24, min_count: int = 3
    ) -> list[dict[str, Any]]:
        """Get recurring errors within a time window.

        Args:
            window_hours: Time window in hours.
            min_count: Minimum occurrence count.

        Returns:
            List of recurring error dicts.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        error_counts: dict[str, int] = defaultdict(int)

        for record in self.error_history:
            try:
                record_time = datetime.fromisoformat(
                    record.timestamp.replace("Z", "+00:00")
                )
                if record_time >= cutoff:
                    key = f"{record.error_type}:{record.component}"
                    error_counts[key] += 1
            except (ValueError, TypeError):
                pass

        recurring = []
        for key, count in error_counts.items():
            if count >= min_count:
                error_type, component = key.split(":", 1)
                recurring.append(
                    {
                        "error_type": error_type,
                        "component": component,
                        "count": count,
                        "window_hours": window_hours,
                    }
                )

        return sorted(recurring, key=lambda x: x["count"], reverse=True)

    def _find_strategy(
        self,
        error_type: str,
        error_message: str,
    ) -> HealingStrategy | None:
        """Find a matching healing strategy.

        Args:
            error_type: Error type.
            error_message: Error message.

        Returns:
            Matching HealingStrategy or None.
        """
        for strategy in self.strategies:
            if strategy.error_pattern.lower() in error_type.lower():
                return strategy
            if strategy.error_pattern.lower() in error_message.lower():
                return strategy
        return None

    def _load_data(self) -> None:
        """Load healing data from storage."""
        history_file = self.storage_path / "error_history.json"
        if history_file.exists():
            try:
                data = json.loads(history_file.read_text())
                for d in data:
                    self.error_history.append(
                        ErrorRecord(
                            error_type=d["error_type"],
                            error_message=d["error_message"],
                            component=d["component"],
                            timestamp=d.get("timestamp", ""),
                            context=d.get("context", {}),
                            fix_applied=d.get("fix_applied", ""),
                            fix_successful=d.get("fix_successful", False),
                        )
                    )
            except Exception as e:
                logger.warning(f"Failed to load error history: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get self-healing statistics."""
        total_errors = len(self.error_history)
        fixed_errors = sum(1 for e in self.error_history if e.fix_successful)

        return {
            "total_errors": total_errors,
            "fixed_errors": fixed_errors,
            "fix_rate": round(fixed_errors / max(1, total_errors), 4),
            "strategies_registered": len(self.strategies),
            "circuit_breaker": self.circuit_breaker.get_stats(),
            "recurring_errors": len(self.get_recurring_errors()),
        }


# Global singleton
_self_healing = SelfHealing()


def handle_error(
    error_type: str,
    error_message: str,
    component: str,
    context: dict[str, Any] | None = None,
) -> bool:
    """Convenience function to handle an error."""
    return _self_healing.handle_error(error_type, error_message, component, context)


def register_strategy(
    error_pattern: str,
    strategy_name: str,
    action: Callable[[], bool],
) -> HealingStrategy:
    """Convenience function to register a strategy."""
    return _self_healing.register_strategy(error_pattern, strategy_name, action)

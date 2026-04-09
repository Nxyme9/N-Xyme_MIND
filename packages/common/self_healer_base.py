"""
SelfHealer Base — Common interface for all SelfHealer implementations.

Provides:
- Abstract base for service healing and memory healing
- Common report structure (issues_found, issues_fixed, errors, actions_taken)
- Type definitions for healing operations

Usage:
    from packages.common.self_healer_base import SelfHealerBase, HealingReport

    class MyHealer(SelfHealerBase):
        def heal_all(self) -> dict:
            ...
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class HealingReport:
    """Common report structure for all healing operations."""

    issues_found: int = 0
    issues_fixed: int = 0
    errors: List[str] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "issues_found": self.issues_found,
            "issues_fixed": self.issues_fixed,
            "errors": self.errors,
            "actions_taken": self.actions_taken,
        }

    def reset(self) -> None:
        """Reset report to initial state."""
        self.issues_found = 0
        self.issues_fixed = 0
        self.errors.clear()
        self.actions_taken.clear()

    def merge(self, other: "HealingReport") -> None:
        """Merge another report into this one."""
        self.issues_found += other.issues_found
        self.issues_fixed += other.issues_fixed
        self.errors.extend(other.errors)
        self.actions_taken.extend(other.actions_taken)


class SelfHealerBase(ABC):
    """
    Abstract base class for SelfHealer implementations.

    Subclasses must implement:
    - heal_all(): Run all healing operations
    - get_healing_report(): Get detailed healing report
    """

    def __init__(self) -> None:
        """Initialize base healer."""
        self._report = HealingReport()
        self._enabled = True

    @abstractmethod
    def heal_all(self) -> Dict[str, Any]:
        """
        Run all healing operations.

        Returns:
            Dictionary with healing report
        """
        pass

    @abstractmethod
    def get_healing_report(self) -> Dict[str, Any]:
        """
        Get detailed healing report.

        Returns:
            Dictionary with full healing report
        """
        pass

    def is_enabled(self) -> bool:
        """Check if healing is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable healing operations."""
        self._enabled = True

    def disable(self) -> None:
        """Disable healing operations."""
        self._enabled = False

    def _update_report(
        self,
        issues_found: int = 0,
        issues_fixed: int = 0,
        errors: Optional[List[str]] = None,
        actions: Optional[List[str]] = None,
    ) -> None:
        """Update internal report with new values."""
        self._report.issues_found += issues_found
        self._report.issues_fixed += issues_fixed
        if errors:
            self._report.errors.extend(errors)
        if actions:
            self._report.actions_taken.extend(actions)

    def _reset_report(self) -> None:
        """Reset internal report."""
        self._report.reset()


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "HealingReport",
    "SelfHealerBase",
]

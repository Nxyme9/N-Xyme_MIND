"""N-Xyme Module Interfaces — Core abstractions for plug-and-play modules."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ModuleState(Enum):
    """Lifecycle states for N-Xyme modules."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    SHUTDOWN = "shutdown"


class ModuleStatus(Enum):
    """Module health status indicators."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ModuleMetadata:
    """Metadata for a module."""

    name: str
    version: str
    description: str
    author: Optional[str] = None
    dependencies: Optional[Dict[str, str]] = None
    tags: Optional[list] = None


@dataclass
class HealthCheckResult:
    """Result of a module health check."""

    status: ModuleStatus
    message: str
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "status": self.status.value,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


class NXymeModule(ABC):
    """Abstract base class for all N-Xyme modules."""

    @property
    @abstractmethod
    def metadata(self) -> ModuleMetadata:
        """Return module metadata."""
        ...

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Perform health check.

        Returns:
            Dict with status, message, and optional details
        """
        ...

    def shutdown(self) -> None:
        """Clean shutdown of the module.

        Override to implement cleanup logic.
        """
        logger.info(f"Shutting down module: {self.metadata.name}")

    def initialize(self) -> None:
        """Initialize the module.

        Override to implement initialization logic.
        """
        logger.info(f"Initializing module: {self.metadata.name}")


# Re-export for convenience
__all__ = [
    "NXymeModule",
    "ModuleMetadata",
    "ModuleState",
    "ModuleStatus",
    "HealthCheckResult",
]

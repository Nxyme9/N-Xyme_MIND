"""
Simple Dependency Injection Container for N-Xyme.

Replaces singleton patterns with proper DI for:
- Testability (can mock services)
- No state leakage between tests
- Thread-safe under high concurrency
- Clearer dependency graph
"""

from typing import Optional, TypeVar, Dict, Any, Callable
from dataclasses import dataclass
from threading import Lock
import logging

logger = logging.getLogger("di_container")

T = TypeVar("T")


@dataclass
class ServiceDescriptor:
    """Descriptor for a registered service."""

    instance: Any = None
    factory: Optional[Callable] = None
    singleton: bool = True


class DIContainer:
    """Simple dependency injection container."""

    def __init__(self):
        self._services: Dict[str, ServiceDescriptor] = {}
        self._lock = Lock()

    def register(
        self,
        name: str,
        factory: Optional[Callable] = None,
        instance: Any = None,
        singleton: bool = True,
    ) -> None:
        """Register a service."""
        with self._lock:
            if instance is not None:
                self._services[name] = ServiceDescriptor(
                    instance=instance,
                    singleton=singleton,
                )
            elif factory is not None:
                self._services[name] = ServiceDescriptor(
                    factory=factory,
                    singleton=singleton,
                )
            else:
                raise ValueError("Must provide either instance or factory")

    def get(self, name: str) -> Any:
        """Get a service by name."""
        with self._lock:
            if name not in self._services:
                raise KeyError(f"Service not registered: {name}")

            desc = self._services[name]

            if desc.singleton:
                if desc.instance is None:
                    if desc.factory:
                        desc.instance = desc.factory()
                return desc.instance
            else:
                if desc.factory:
                    return desc.factory()
                raise ValueError(f"No factory for non-singleton: {name}")

    def clear(self) -> None:
        """Clear all registered services (for testing)."""
        with self._lock:
            self._services.clear()

    def has(self, name: str) -> bool:
        """Check if service is registered."""
        return name in self._services

    def unregister(self, name: str) -> None:
        """Unregister a service."""
        with self._lock:
            self._services.pop(name, None)


_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Get the global DI container."""
    global _container
    if _container is None:
        _container = DIContainer()
    return _container


def reset_container() -> None:
    """Reset the global container (for testing)."""
    global _container
    _container = None

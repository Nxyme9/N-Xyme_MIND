"""N-Xyme Module Registry — Plug-and-play discovery and lazy loading."""

import logging
from typing import Dict, Optional, Type, List, Any

from .interfaces import NXymeModule, ModuleState

logger = logging.getLogger(__name__)


class NXymeRegistry:
    """Registry for discovering and managing N-Xyme modules."""

    def __init__(self):
        self._modules: Dict[str, NXymeModule] = {}
        self._module_classes: Dict[str, Type[NXymeModule]] = {}
        self._states: Dict[str, str] = {}

    def register(self, name: str, module_class: Type[NXymeModule]) -> None:
        """Register a module class (not instance) for lazy loading.

        Args:
            name: Module name (e.g., "memory", "orchestration")
            module_class: Class implementing NXymeModule
        """
        self._module_classes[name] = module_class
        self._states[name] = ModuleState.UNINITIALIZED
        logger.info(f"Registered module: {name} ({module_class.__name__})")

    def register_instance(self, name: str, instance: NXymeModule) -> None:
        """Register a module instance directly.

        Args:
            name: Module name
            instance: NXymeModule instance
        """
        self._modules[name] = instance
        self._states[name] = ModuleState.HEALTHY
        logger.info(f"Registered instance: {name}")

    def get(self, name: str) -> Optional[NXymeModule]:
        """Get a module instance, loading if necessary.

        Args:
            name: Module name

        Returns:
            NXymeModule instance or None if not found
        """
        # Already loaded
        if name in self._modules:
            return self._modules[name]

        # Lazy load
        if name in self._module_classes:
            try:
                instance = self._module_classes[name]()
                self._modules[name] = instance
                self._states[name] = ModuleState.HEALTHY
                return instance
            except Exception as e:
                logger.error(f"Failed to load module {name}: {e}")
                self._states[name] = ModuleState.UNHEALTHY
                return None

        return None

    def get_state(self, name: str) -> str:
        """Get current state of a module."""
        return self._states.get(name, ModuleState.UNINITIALIZED)

    def list_modules(self) -> List[str]:
        """List all registered module names."""
        return list(self._module_classes.keys())

    def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Run health check on all modules.

        Returns:
            Dict mapping module names to health check results
        """
        results = {}
        for name in self._module_classes:
            module = self.get(name)
            if module:
                try:
                    results[name] = module.health_check()
                except Exception as e:
                    results[name] = {"status": "unhealthy", "error": str(e)}
            else:
                results[name] = {"status": "unhealthy", "error": "not loaded"}
        return results

    def shutdown_all(self) -> None:
        """Shutdown all modules cleanly."""
        for name, module in self._modules.items():
            try:
                module.shutdown()
                self._states[name] = ModuleState.SHUTDOWN
            except Exception as e:
                logger.error(f"Error shutting down {name}: {e}")


# Global registry instance
_global_registry: Optional[NXymeRegistry] = None


def get_registry() -> NXymeRegistry:
    """Get the global registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = NXymeRegistry()
    return _global_registry


# Re-export for convenience
__all__ = [
    "NXymeRegistry",
    "get_registry",
]

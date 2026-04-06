# Dynamic Panel Registry
"""Dynamic panel registration and management for self-evolving menus.

This system:
1. Automatically registers panels from discovered modules
2. Generates panel content functions dynamically
3. Manages panel lifecycle (add, remove, update)
4. Provides panel metadata and descriptions
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DynamicPanelRegistry:
    """Registry for dynamically discovered panels."""

    def __init__(self):
        self._panels: Dict[str, Dict[str, Any]] = {}
        self._panel_functions: Dict[str, Callable] = {}
        self._panel_metadata: Dict[str, Dict[str, str]] = {}

    def discover_and_register_panels(self, directories: List[Path]) -> List[str]:
        """Discover and register panels from directories.

        Args:
            directories: Directories to scan for panels

        Returns:
            List of newly registered panel names
        """
        new_panels = []

        for directory in directories:
            if not directory.exists():
                continue

            for panel_file in directory.glob("*.py"):
                if panel_file.name.startswith("_"):
                    continue

                try:
                    panel_name = panel_file.stem
                    if panel_name in self._panels:
                        continue

                    # Try to import module
                    module_name = f"src.dashboard.panels.{panel_name}"
                    spec = importlib.util.spec_from_file_location(
                        module_name, panel_file
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        # Check for get_content function
                        if hasattr(module, "get_content"):
                            self._panel_functions[panel_name] = module.get_content
                            self._panels[panel_name] = {
                                "module": module_name,
                                "path": str(panel_file),
                                "has_content": True,
                                "has_info": hasattr(module, "get_panel_info"),
                                "has_commands": hasattr(module, "register_commands"),
                            }

                            # Get metadata if available
                            if hasattr(module, "get_panel_info"):
                                try:
                                    info = module.get_panel_info()
                                    self._panel_metadata[panel_name] = info
                                except Exception:
                                    self._panel_metadata[panel_name] = {
                                        "title": panel_name.replace("_", " ").title(),
                                        "description": "",
                                        "icon": "📊",
                                    }
                            else:
                                self._panel_metadata[panel_name] = {
                                    "title": panel_name.replace("_", " ").title(),
                                    "description": "",
                                    "icon": "📊",
                                }

                            new_panels.append(panel_name)
                            logger.info(f"Registered panel: {panel_name}")
                except Exception as e:
                    logger.warning(f"Failed to register panel {panel_file}: {e}")

        return new_panels

    def get_panel_function(self, name: str) -> Optional[Callable]:
        """Get panel content function by name.

        Args:
            name: Panel name

        Returns:
            Content function or None
        """
        return self._panel_functions.get(name)

    def get_panel_metadata(self, name: str) -> Dict[str, str]:
        """Get panel metadata by name.

        Args:
            name: Panel name

        Returns:
            Panel metadata dict
        """
        return self._panel_metadata.get(
            name,
            {"title": name.replace("_", " ").title(), "description": "", "icon": "📊"},
        )

    def list_panels(self) -> List[str]:
        """List all registered panel names.

        Returns:
            List of panel names
        """
        return list(self._panels.keys())

    def has_panel(self, name: str) -> bool:
        """Check if panel is registered.

        Args:
            name: Panel name

        Returns:
            True if panel exists
        """
        return name in self._panels

    def remove_panel(self, name: str) -> bool:
        """Remove a panel from registry.

        Args:
            name: Panel name

        Returns:
            True if panel was removed
        """
        if name in self._panels:
            del self._panels[name]
            self._panel_functions.pop(name, None)
            self._panel_metadata.pop(name, None)
            return True
        return False

    def get_panel_info(self) -> Dict[str, Dict[str, Any]]:
        """Get info for all registered panels.

        Returns:
            Dict of panel name to info
        """
        return {
            name: {**info, "metadata": self._panel_metadata.get(name, {})}
            for name, info in self._panels.items()
        }


# Global dynamic panel registry instance
dynamic_panel_registry = DynamicPanelRegistry()


# Convenience functions
def discover_and_register_panels(directories: List[Path]) -> List[str]:
    """Discover and register panels from directories."""
    return dynamic_panel_registry.discover_and_register_panels(directories)


def get_panel_function(name: str) -> Optional[Callable]:
    """Get panel content function by name."""
    return dynamic_panel_registry.get_panel_function(name)


def get_panel_metadata(name: str) -> Dict[str, str]:
    """Get panel metadata by name."""
    return dynamic_panel_registry.get_panel_metadata(name)


def list_panels() -> List[str]:
    """List all registered panel names."""
    return dynamic_panel_registry.list_panels()

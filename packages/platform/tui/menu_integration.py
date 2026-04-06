#!/usr/bin/env python3
"""Self-Evolving Menu Integration for N-Xyme MIND Dashboard.

This module provides a clean, robust integration of the self-evolving menu
system into the dashboard without breaking existing functionality.

Usage:
    from .menu_integration import integrate_self_evolving_menu
    integrate_self_evolving_menu(dashboard_instance)
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SelfEvolvingMenu:
    """Self-evolving menu system for the dashboard.

    This class:
    1. Scans the codebase for dashboard-compatible modules
    2. Discovers new panels automatically
    3. Updates the dashboard menu dynamically
    4. Notifies users of new discoveries
    """

    def __init__(self, dashboard: Any):
        """Initialize self-evolving menu.

        Args:
            dashboard: Dashboard instance to integrate with
        """
        self.dashboard = dashboard
        self.discovered_panels: Dict[str, Dict[str, Any]] = {}
        self.known_modules: set = set()
        self.scan_directories = [
            Path("src/dashboard/panels"),
            Path("src/health"),
            Path("src/memory"),
            Path("src/intelligence"),
            Path("src/orchestration"),
            Path("src/model_router"),
        ]

    def scan_for_new_modules(self) -> List[str]:
        """Scan for new dashboard-compatible modules.

        Returns:
            List of newly discovered module names
        """
        new_modules = []

        for directory in self.scan_directories:
            if not directory.exists():
                continue

            for module_file in directory.glob("*.py"):
                if module_file.name.startswith("_"):
                    continue

                module_name = module_file.stem
                if module_name in self.known_modules:
                    continue

                # Check if module has dashboard-compatible interface
                try:
                    content = module_file.read_text()
                    if (
                        "def get_content(" in content
                        or "def get_panel_info(" in content
                    ):
                        self.discovered_panels[module_name] = {
                            "path": str(module_file),
                            "directory": str(directory),
                            "has_content": "def get_content(" in content,
                            "has_panel_info": "def get_panel_info(" in content,
                        }
                        self.known_modules.add(module_name)
                        new_modules.append(module_name)
                        logger.info(f"Discovered new panel: {module_name}")
                except Exception as e:
                    logger.warning(f"Failed to scan {module_file}: {e}")

        return new_modules

    def update_dashboard_menu(self) -> None:
        """Update dashboard menu with discovered panels."""
        new_modules = self.scan_for_new_modules()

        if new_modules and hasattr(self.dashboard, "notify"):
            for module_name in new_modules:
                self.dashboard.notify(
                    f"New panel discovered: {module_name}",
                    severity="information",
                    timeout=5,
                )

            # Update sidebar if possible
            self._update_sidebar()

    def _update_sidebar(self) -> None:
        """Update sidebar with discovered panels."""
        try:
            # Try to find the sidebar container
            sidebar = self.dashboard.query_one("#sidebar")
            if not sidebar:
                return

            # Check if discovered panels section exists
            try:
                container = self.dashboard.query_one("#discovered-panels")
            except Exception:
                # Create discovered panels section
                from textual.containers import Container
                from textual.widgets import Label, Button

                # Add section label
                sidebar.mount(Label("Discovered", classes="section-title"))
                container = Container(id="discovered-panels")
                sidebar.mount(container)

            # Clear existing buttons
            for child in list(container.children):
                child.remove()

            # Add buttons for discovered panels
            from textual.widgets import Button

            for panel_name in self.discovered_panels:
                btn = Button(
                    panel_name.replace("_", " ").title(),
                    id=f"btn-discovered-{panel_name}",
                    variant="default",
                )
                container.mount(btn)

        except Exception as e:
            logger.warning(f"Failed to update sidebar: {e}")

    def get_menu_structure(self) -> Dict[str, Any]:
        """Get current menu structure.

        Returns:
            Dict with menu structure
        """
        return {
            "static_panels": [
                "overview",
                "agents",
                "memory",
                "intelligence",
                "proxy",
                "config",
            ],
            "discovered_panels": list(self.discovered_panels.keys()),
            "total_panels": 6 + len(self.discovered_panels),
            "known_modules": list(self.known_modules),
        }

    def get_discovered_panel_content(self, panel_name: str) -> str:
        """Get content for a discovered panel.

        Args:
            panel_name: Panel name

        Returns:
            Panel content string
        """
        if panel_name not in self.discovered_panels:
            return f"Panel '{panel_name}' not found"

        panel_info = self.discovered_panels[panel_name]
        module_path = Path(panel_info["path"])

        try:
            # Try to import and call get_content
            spec = importlib.util.spec_from_file_location(
                f"dynamic_{panel_name}", module_path
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if hasattr(module, "get_content"):
                    return module.get_content(self.dashboard)
                elif hasattr(module, "get_panel_info"):
                    info = module.get_panel_info()
                    return f"Panel: {panel_name}\n\n{info}"
        except Exception as e:
            return f"Failed to load panel '{panel_name}': {e}"

        return f"Panel: {panel_name}\nPath: {panel_info['path']}"


def integrate_self_evolving_menu(dashboard: Any) -> SelfEvolvingMenu:
    """Integrate self-evolving menu into dashboard.

    Args:
        dashboard: Dashboard instance

    Returns:
        SelfEvolvingMenu instance
    """
    menu = SelfEvolvingMenu(dashboard)

    # Initial scan
    menu.update_dashboard_menu()

    # Set up periodic scanning (every 60 seconds)
    if hasattr(dashboard, "set_interval"):
        dashboard.set_interval(60.0, menu.update_dashboard_menu)

    return menu

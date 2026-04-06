#!/usr/bin/env python3
"""Self-Evolving Menu System — Runtime patcher for N-Xyme MIND Dashboard.

This module patches the dashboard at runtime to add self-evolving menu
capabilities WITHOUT modifying the dashboard source file.

Usage:
    # In your dashboard launch script:
    from src.ui.tui.self_evolving_menu import patch_dashboard
    patch_dashboard(dashboard_instance)

Or run standalone:
    python -m src.ui.tui.self_evolving_menu
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class MenuEvolutionRecord:
    """Record of a menu evolution event."""

    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    event_type: str = ""  # added, removed, updated
    item_type: str = ""  # panel, plugin, module
    item_name: str = ""
    item_path: str = ""
    description: str = ""


class SelfEvolvingMenu:
    """Self-evolving menu system that discovers and registers new panels."""

    def __init__(self, dashboard: Any):
        self.dashboard = dashboard
        self.discovered_panels: Dict[str, Dict[str, Any]] = {}
        self.known_modules: Set[str] = set()
        self.evolution_history: List[MenuEvolutionRecord] = []
        self.scan_directories = [
            Path("src/dashboard/panels"),
            Path("src/health"),
            Path("src/memory"),
            Path("src/intelligence"),
            Path("src/orchestration"),
            Path("src/model_router"),
            Path("src/healing"),
        ]
        self._load_history()

    def _load_history(self):
        """Load evolution history from storage."""
        history_file = Path(".sisyphus/menu_evolution.json")
        if history_file.exists():
            try:
                data = json.loads(history_file.read_text())
                self.evolution_history = [
                    MenuEvolutionRecord(**record) for record in data
                ]
                self.known_modules = {
                    record.item_name
                    for record in self.evolution_history
                    if record.event_type == "added"
                }
            except Exception:
                pass

    def _save_history(self):
        """Save evolution history to storage."""
        history_file = Path(".sisyphus/menu_evolution.json")
        try:
            history_file.parent.mkdir(parents=True, exist_ok=True)
            data = [
                {
                    "timestamp": record.timestamp,
                    "event_type": record.event_type,
                    "item_type": record.item_type,
                    "item_name": record.item_name,
                    "item_path": record.item_path,
                    "description": record.description,
                }
                for record in self.evolution_history
            ]
            history_file.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

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

                        # Record evolution
                        record = MenuEvolutionRecord(
                            event_type="added",
                            item_type="panel",
                            item_name=module_name,
                            item_path=str(module_file),
                            description=f"Discovered in {directory.name}",
                        )
                        self.evolution_history.append(record)

                        logger.info(f"Discovered new panel: {module_name}")
                except Exception as e:
                    logger.warning(f"Failed to scan {module_file}: {e}")

        if new_modules:
            self._save_history()

        return new_modules

    def update_dashboard_menu(self) -> List[str]:
        """Update dashboard menu with discovered panels.

        Returns:
            List of newly discovered module names
        """
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

        return new_modules

    def _update_sidebar(self) -> None:
        """Update sidebar with discovered panels."""
        try:
            # Try to find the sidebar
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
            "evolution_events": len(self.evolution_history),
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
                    return f"Panel: {panel_name}\n\n{json.dumps(info, indent=2)}"
        except Exception as e:
            return f"Failed to load panel '{panel_name}': {e}"

        return f"Panel: {panel_name}\nPath: {panel_info['path']}"


def patch_dashboard(dashboard: Any) -> SelfEvolvingMenu:
    """Patch a dashboard instance with self-evolving menu capabilities.

    Args:
        dashboard: Dashboard instance to patch

    Returns:
        SelfEvolvingMenu instance
    """
    menu = SelfEvolvingMenu(dashboard)

    # Initial scan
    new_modules = menu.update_dashboard_menu()

    # Set up periodic scanning (every 60 seconds)
    if hasattr(dashboard, "set_interval"):
        dashboard.set_interval(60.0, menu.update_dashboard_menu)

    # Add menu_system attribute to dashboard
    dashboard.menu_system = menu

    # Add new methods to dashboard
    def get_menu_structure():
        return menu.get_menu_structure()

    def get_discovered_panel_content(panel_name: str):
        return menu.get_discovered_panel_content(panel_name)

    dashboard.get_menu_structure = get_menu_structure
    dashboard.get_discovered_panel_content = get_discovered_panel_content

    return menu


def main():
    """Run self-evolving menu scanner standalone."""
    import sys

    # Create a mock dashboard for scanning
    class MockDashboard:
        def notify(self, message, severity="", timeout=0):
            print(f"[{severity.upper()}] {message}")

    dashboard = MockDashboard()
    menu = SelfEvolvingMenu(dashboard)

    print("=== Self-Evolving Menu Scanner ===\n")
    print("Scanning for dashboard-compatible modules...\n")

    new_modules = menu.update_dashboard_menu()

    if new_modules:
        print(f"Discovered {len(new_modules)} new panels:")
        for name in new_modules:
            info = menu.discovered_panels[name]
            print(f"  - {name}: {info['path']}")
    else:
        print("No new panels discovered.")

    print(f"\n=== Menu Structure ===")
    structure = menu.get_menu_structure()
    print(f"Static panels: {len(structure['static_panels'])}")
    print(f"Discovered panels: {len(structure['discovered_panels'])}")
    print(f"Total panels: {structure['total_panels']}")
    print(f"Evolution events: {structure['evolution_events']}")

    if structure["discovered_panels"]:
        print(f"\nDiscovered panels:")
        for name in structure["discovered_panels"]:
            info = menu.discovered_panels[name]
            print(f"  - {name}: {info['path']}")


if __name__ == "__main__":
    main()

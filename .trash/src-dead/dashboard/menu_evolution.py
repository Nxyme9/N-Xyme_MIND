# Self-Evolving Menu System
"""Auto-discovery and dynamic menu generation for the dashboard.

This system automatically:
1. Discovers new backend modules with dashboard-compatible interfaces
2. Discovers new panel modules in src/dashboard/panels/
3. Discovers new plugins in src/dashboard/plugins/
4. Dynamically generates menu items based on discoveries
5. Tracks menu evolution over time
6. Notifies users of new menu items

Usage:
    from src.dashboard.menu_evolution import MenuEvolution

    evolution = MenuEvolution()
    evolution.scan_for_new_modules()

    # Get current menu structure
    menu = evolution.get_menu_structure()

    # Get evolution history
    history = evolution.get_evolution_history()
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
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MenuEvolutionRecord:
    """Record of a menu evolution event."""

    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    event_type: str = ""  # added, removed, updated
    item_type: str = ""  # panel, plugin, module, command
    item_name: str = ""
    item_path: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModuleScanner:
    """Scans the codebase for dashboard-compatible modules."""

    def __init__(self, base_path: Path = Path("src")):
        self.base_path = base_path
        self._discovered_modules: Dict[str, Dict[str, Any]] = {}
        self._last_scan: Optional[float] = None

    def scan_for_dashboard_modules(self) -> Dict[str, Dict[str, Any]]:
        """Scan for modules with dashboard-compatible interfaces.

        Looks for modules that have:
        - get_content(dashboard) -> str function
        - get_panel_info() -> dict function
        - register_commands(registry) function
        """
        discovered = {}

        # Scan panels directory
        panels_dir = self.base_path / "dashboard" / "panels"
        if panels_dir.exists():
            for panel_file in panels_dir.glob("*.py"):
                if panel_file.name.startswith("_"):
                    continue

                try:
                    module_name = f"src.dashboard.panels.{panel_file.stem}"
                    spec = importlib.util.spec_from_file_location(
                        module_name, panel_file
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        # Check for dashboard-compatible functions
                        if hasattr(module, "get_content"):
                            discovered[panel_file.stem] = {
                                "type": "panel",
                                "module": module_name,
                                "path": str(panel_file),
                                "has_content": True,
                                "has_info": hasattr(module, "get_panel_info"),
                                "has_commands": hasattr(module, "register_commands"),
                                "discovered_at": datetime.now(timezone.utc).isoformat(),
                            }
                except Exception as e:
                    logger.warning(f"Failed to scan panel {panel_file}: {e}")

        # Scan plugins directory
        plugins_dir = self.base_path / "dashboard" / "plugins"
        if plugins_dir.exists():
            for plugin_file in plugins_dir.glob("*.py"):
                if plugin_file.name.startswith("_"):
                    continue

                try:
                    module_name = f"src.dashboard.plugins.{plugin_file.stem}"
                    spec = importlib.util.spec_from_file_location(
                        module_name, plugin_file
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        # Check for DashboardPlugin subclasses
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if (
                                isinstance(attr, type)
                                and hasattr(attr, "__mro__")
                                and any(
                                    "DashboardPlugin" in str(base)
                                    for base in attr.__mro__
                                )
                                and attr_name != "DashboardPlugin"
                            ):
                                discovered[plugin_file.stem] = {
                                    "type": "plugin",
                                    "module": module_name,
                                    "path": str(plugin_file),
                                    "class_name": attr_name,
                                    "name": getattr(attr, "name", plugin_file.stem),
                                    "version": getattr(attr, "version", "0.0.0"),
                                    "description": getattr(attr, "description", ""),
                                    "discovered_at": datetime.now(
                                        timezone.utc
                                    ).isoformat(),
                                }
                except Exception as e:
                    logger.warning(f"Failed to scan plugin {plugin_file}: {e}")

        # Scan backend modules for dashboard-compatible interfaces
        backend_dirs = [
            self.base_path / "health",
            self.base_path / "memory",
            self.base_path / "intelligence",
            self.base_path / "orchestration",
            self.base_path / "model_router",
        ]

        for backend_dir in backend_dirs:
            if backend_dir.exists():
                for module_file in backend_dir.glob("*.py"):
                    if module_file.name.startswith("_"):
                        continue

                    try:
                        # Check if module has dashboard-compatible functions
                        module_name = module_file.stem
                        # Quick check without importing
                        content = module_file.read_text()
                        if (
                            "def get_content(" in content
                            or "def get_panel_info(" in content
                        ):
                            discovered[module_file.stem] = {
                                "type": "backend_module",
                                "path": str(module_file),
                                "has_content": "def get_content(" in content,
                                "has_panel_info": "def get_panel_info(" in content,
                                "discovered_at": datetime.now(timezone.utc).isoformat(),
                            }
                    except Exception as e:
                        logger.warning(
                            f"Failed to scan backend module {module_file}: {e}"
                        )

        self._discovered_modules = discovered
        self._last_scan = time.time()
        return discovered

    def get_discovered_modules(self) -> Dict[str, Dict[str, Any]]:
        """Get all discovered modules."""
        return self._discovered_modules.copy()

    def get_new_modules_since(self, timestamp: float) -> Dict[str, Dict[str, Any]]:
        """Get modules discovered since a timestamp."""
        if not self._last_scan:
            return {}

        return {
            name: info
            for name, info in self._discovered_modules.items()
            if info.get("discovered_at", "")
            > datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
        }


class MenuEvolution:
    """Self-evolving menu system for the dashboard."""

    def __init__(self, storage_path: Path = Path(".sisyphus/menu_evolution")):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.scanner = ModuleScanner()
        self.evolution_history: List[MenuEvolutionRecord] = []
        self.known_items: Set[str] = set()
        self.menu_structure: Dict[str, Any] = {}

        self._load_history()

    def _load_history(self):
        """Load evolution history from storage."""
        history_file = self.storage_path / "evolution_history.json"
        if history_file.exists():
            try:
                data = json.loads(history_file.read_text())
                self.evolution_history = [
                    MenuEvolutionRecord(**record) for record in data
                ]
                self.known_items = {
                    record.item_name
                    for record in self.evolution_history
                    if record.event_type == "added"
                }
            except Exception as e:
                logger.warning(f"Failed to load evolution history: {e}")

    def _save_history(self):
        """Save evolution history to storage."""
        history_file = self.storage_path / "evolution_history.json"
        try:
            data = [
                {
                    "timestamp": record.timestamp,
                    "event_type": record.event_type,
                    "item_type": record.item_type,
                    "item_name": record.item_name,
                    "item_path": record.item_path,
                    "description": record.description,
                    "metadata": record.metadata,
                }
                for record in self.evolution_history
            ]
            history_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save evolution history: {e}")

    def scan_for_new_modules(self) -> List[MenuEvolutionRecord]:
        """Scan for new modules and update menu.

        Returns:
            List of evolution records for new items
        """
        new_records = []
        discovered = self.scanner.scan_for_dashboard_modules()

        for name, info in discovered.items():
            if name not in self.known_items:
                # New item discovered
                record = MenuEvolutionRecord(
                    event_type="added",
                    item_type=info.get("type", "unknown"),
                    item_name=name,
                    item_path=info.get("path", ""),
                    description=info.get("description", ""),
                    metadata=info,
                )
                self.evolution_history.append(record)
                self.known_items.add(name)
                new_records.append(record)

                logger.info(f"New menu item discovered: {name} ({info.get('type')})")

        # Check for removed items
        current_items = set(discovered.keys())
        removed_items = self.known_items - current_items
        for name in removed_items:
            record = MenuEvolutionRecord(
                event_type="removed",
                item_type="unknown",
                item_name=name,
                description="Module no longer found",
            )
            self.evolution_history.append(record)
            self.known_items.discard(name)
            new_records.append(record)

            logger.info(f"Menu item removed: {name}")

        if new_records:
            self._save_history()

        return new_records

    def get_menu_structure(self) -> Dict[str, Any]:
        """Get current menu structure based on discovered modules."""
        discovered = self.scanner.get_discovered_modules()

        menu = {
            "panels": [],
            "plugins": [],
            "backend_modules": [],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        for name, info in discovered.items():
            item_type = info.get("type", "unknown")
            if item_type == "panel":
                menu["panels"].append(
                    {
                        "name": name,
                        "module": info.get("module", ""),
                        "has_content": info.get("has_content", False),
                        "has_info": info.get("has_info", False),
                        "has_commands": info.get("has_commands", False),
                    }
                )
            elif item_type == "plugin":
                menu["plugins"].append(
                    {
                        "name": name,
                        "module": info.get("module", ""),
                        "class_name": info.get("class_name", ""),
                        "version": info.get("version", "0.0.0"),
                        "description": info.get("description", ""),
                    }
                )
            elif item_type == "backend_module":
                menu["backend_modules"].append(
                    {
                        "name": name,
                        "path": info.get("path", ""),
                        "has_content": info.get("has_content", False),
                        "has_panel_info": info.get("has_panel_info", False),
                    }
                )

        self.menu_structure = menu
        return menu

    def get_evolution_history(self, limit: int = 50) -> List[MenuEvolutionRecord]:
        """Get evolution history.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of evolution records
        """
        return self.evolution_history[-limit:]

    def get_new_items_since(self, timestamp: float) -> List[MenuEvolutionRecord]:
        """Get new items discovered since a timestamp.

        Args:
            timestamp: Unix timestamp

        Returns:
            List of new evolution records
        """
        cutoff = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
        return [
            record
            for record in self.evolution_history
            if record.timestamp > cutoff and record.event_type == "added"
        ]

    def auto_update_menu(self, dashboard: Any = None) -> List[MenuEvolutionRecord]:
        """Auto-update menu and notify dashboard of changes.

        Args:
            dashboard: Dashboard instance for notifications

        Returns:
            List of evolution records for new items
        """
        new_items = self.scan_for_new_modules()

        if new_items and dashboard and hasattr(dashboard, "notify"):
            for record in new_items:
                if record.event_type == "added":
                    dashboard.notify(
                        f"New menu item: {record.item_name} ({record.item_type})",
                        severity="information",
                        timeout=5,
                    )
                elif record.event_type == "removed":
                    dashboard.notify(
                        f"Menu item removed: {record.item_name}",
                        severity="warning",
                        timeout=5,
                    )

        return new_items

    def get_menu_stats(self) -> Dict[str, Any]:
        """Get menu evolution statistics.

        Returns:
            Dict with statistics
        """
        total_added = sum(
            1 for record in self.evolution_history if record.event_type == "added"
        )
        total_removed = sum(
            1 for record in self.evolution_history if record.event_type == "removed"
        )
        total_updated = sum(
            1 for record in self.evolution_history if record.event_type == "updated"
        )

        return {
            "total_items_discovered": total_added,
            "total_items_removed": total_removed,
            "total_items_updated": total_updated,
            "current_items": len(self.known_items),
            "evolution_events": len(self.evolution_history),
            "last_scan": self.scanner._last_scan,
            "last_updated": self.menu_structure.get("last_updated", ""),
        }


# Global menu evolution instance
menu_evolution = MenuEvolution()


# Convenience functions
def scan_for_new_modules() -> List[MenuEvolutionRecord]:
    """Scan for new modules and update menu."""
    return menu_evolution.scan_for_new_modules()


def get_menu_structure() -> Dict[str, Any]:
    """Get current menu structure."""
    return menu_evolution.get_menu_structure()


def get_evolution_history(limit: int = 50) -> List[MenuEvolutionRecord]:
    """Get evolution history."""
    return menu_evolution.get_evolution_history(limit)


def auto_update_menu(dashboard: Any = None) -> List[MenuEvolutionRecord]:
    """Auto-update menu and notify dashboard."""
    return menu_evolution.auto_update_menu(dashboard)


def get_menu_stats() -> Dict[str, Any]:
    """Get menu evolution statistics."""
    return menu_evolution.get_menu_stats()

# Hot-Reload System
"""Hot-reload capability for dashboard plugins, themes, and panels.

Monitors file changes and automatically reloads:
- Plugins (src/dashboard/plugins/*.py)
- Themes (src/dashboard/themes/*.py)
- Panels (src/dashboard/panels/*.py)
- Config (src/dashboard/config/*.py)

Usage:
    from src.dashboard.hot_reload import HotReloadManager

    hot_reload = HotReloadManager()
    hot_reload.start()

    # To stop:
    hot_reload.stop()
"""

import time
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime


class FileWatcher:
    """Watches files for changes."""

    def __init__(
        self,
        directories: List[Path],
        callback: Callable[[Path, str], None],
        interval: float = 2.0,
    ):
        """Initialize file watcher.

        Args:
            directories: Directories to watch
            callback: Function to call when file changes (path, event_type)
            interval: Check interval in seconds
        """
        self.directories = directories
        self.callback = callback
        self.interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._file_times: Dict[Path, float] = {}
        self._scan_files()

    def _scan_files(self):
        """Scan all files and record modification times."""
        for directory in self.directories:
            if directory.exists():
                for file_path in directory.rglob("*.py"):
                    if file_path.name.startswith("_"):
                        continue
                    try:
                        self._file_times[file_path] = file_path.stat().st_mtime
                    except Exception:
                        pass

    def _check_changes(self):
        """Check for file changes."""
        current_times: Dict[Path, float] = {}

        for directory in self.directories:
            if directory.exists():
                for file_path in directory.rglob("*.py"):
                    if file_path.name.startswith("_"):
                        continue
                    try:
                        mtime = file_path.stat().st_mtime
                        current_times[file_path] = mtime

                        if file_path in self._file_times:
                            if mtime > self._file_times[file_path]:
                                self.callback(file_path, "modified")
                        else:
                            self.callback(file_path, "created")
                    except Exception:
                        pass

        # Check for deleted files
        for file_path in list(self._file_times.keys()):
            if file_path not in current_times:
                self.callback(file_path, "deleted")

        self._file_times = current_times

    def _watch_loop(self):
        """Main watch loop."""
        while self._running:
            try:
                self._check_changes()
            except Exception as e:
                print(f"File watcher error: {e}")
            time.sleep(self.interval)

    def start(self):
        """Start watching files."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop watching files."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)


class HotReloadManager:
    """Manages hot-reload for dashboard components."""

    def __init__(self, dashboard: Any = None):
        """Initialize hot-reload manager.

        Args:
            dashboard: Dashboard instance (optional, for notifications)
        """
        self.dashboard = dashboard
        self.watcher: Optional[FileWatcher] = None
        self._reload_handlers: Dict[str, List[Callable]] = {
            "plugins": [],
            "themes": [],
            "panels": [],
            "config": [],
        }

    def add_reload_handler(
        self, component_type: str, handler: Callable[[Path, str], None]
    ):
        """Add a reload handler for a component type.

        Args:
            component_type: Component type (plugins, themes, panels, config)
            handler: Function to call when component changes
        """
        if component_type in self._reload_handlers:
            self._reload_handlers[component_type].append(handler)

    def _on_file_change(self, file_path: Path, event_type: str):
        """Handle file change event.

        Args:
            file_path: Changed file path
            event_type: Event type (created, modified, deleted)
        """
        # Determine component type
        component_type = None
        if "plugins" in str(file_path):
            component_type = "plugins"
        elif "themes" in str(file_path):
            component_type = "themes"
        elif "panels" in str(file_path):
            component_type = "panels"
        elif "config" in str(file_path):
            component_type = "config"

        if component_type:
            # Notify handlers
            for handler in self._reload_handlers.get(component_type, []):
                try:
                    handler(file_path, event_type)
                except Exception as e:
                    print(f"Reload handler error: {e}")

            # Notify dashboard
            if self.dashboard and hasattr(self.dashboard, "notify"):
                self.dashboard.notify(
                    f"{component_type.capitalize()} {event_type}: {file_path.name}",
                    severity="information",
                    timeout=3,
                )

    def start(self, directories: Optional[List[Path]] = None, interval: float = 2.0):
        """Start hot-reload monitoring.

        Args:
            directories: Directories to watch (default: all dashboard directories)
            interval: Check interval in seconds
        """
        if directories is None:
            directories = [
                Path("src/dashboard/plugins"),
                Path("src/dashboard/themes"),
                Path("src/dashboard/panels"),
                Path("src/dashboard/config"),
            ]

        self.watcher = FileWatcher(directories, self._on_file_change, interval)
        self.watcher.start()

        if self.dashboard and hasattr(self.dashboard, "notify"):
            self.dashboard.notify(
                "Hot-reload enabled", severity="information", timeout=3
            )

    def stop(self):
        """Stop hot-reload monitoring."""
        if self.watcher:
            self.watcher.stop()
            self.watcher = None

            if self.dashboard and hasattr(self.dashboard, "notify"):
                self.dashboard.notify(
                    "Hot-reload disabled", severity="information", timeout=3
                )


# Global hot-reload manager instance
hot_reload_manager = HotReloadManager()


# Convenience functions
def start_hot_reload(dashboard: Any = None, interval: float = 2.0):
    """Start hot-reload monitoring.

    Args:
        dashboard: Dashboard instance for notifications
        interval: Check interval in seconds
    """
    global hot_reload_manager
    hot_reload_manager = HotReloadManager(dashboard)
    hot_reload_manager.start(interval=interval)


def stop_hot_reload():
    """Stop hot-reload monitoring."""
    global hot_reload_manager
    hot_reload_manager.stop()


def add_reload_handler(component_type: str, handler: Callable[[Path, str], None]):
    """Add a reload handler for a component type.

    Args:
        component_type: Component type (plugins, themes, panels, config)
        handler: Function to call when component changes
    """
    global hot_reload_manager
    hot_reload_manager.add_reload_handler(component_type, handler)

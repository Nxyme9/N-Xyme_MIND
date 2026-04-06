# Dashboard Plugin System
"""Plugin system for extending dashboard functionality.

Plugins can:
- Add new panels
- Add new commands
- Add new themes
- Modify existing behavior
- Add new data sources

Usage:
    # In your plugin file:
    from src.dashboard.plugins import DashboardPlugin, register_plugin

    class MyPlugin(DashboardPlugin):
        name = "my-plugin"
        version = "1.0.0"
        description = "My custom plugin"

        def register_panels(self, registry):
            registry.add_panel("my-panel", self._get_my_panel_content)

        def register_commands(self, registry):
            registry.add_command("my-command", self._run_my_command)

        def _get_my_panel_content(self, dashboard):
            return "My panel content"

        def _run_my_command(self, dashboard):
            dashboard.notify("My command executed")

    # Register the plugin
    register_plugin(MyPlugin)
"""

from typing import Any, Callable, Dict, List, Optional
from pathlib import Path
import json
import importlib
import importlib.util


class PanelRegistry:
    """Registry for dashboard panels."""

    def __init__(self):
        self._panels: Dict[str, Callable] = {}
        self._panel_info: Dict[str, Dict[str, str]] = {}

    def add_panel(
        self, name: str, content_fn: Callable, info: Optional[Dict[str, str]] = None
    ):
        """Add a panel to the registry.

        Args:
            name: Panel name (must be unique)
            content_fn: Function that returns panel content string
            info: Optional panel metadata (title, description, icon)
        """
        self._panels[name] = content_fn
        self._panel_info[name] = info or {
            "title": name,
            "description": "",
            "icon": "📊",
        }

    def get_panel(self, name: str) -> Optional[Callable]:
        """Get panel content function by name."""
        return self._panels.get(name)

    def get_panel_info(self, name: str) -> Dict[str, str]:
        """Get panel metadata by name."""
        return self._panel_info.get(
            name, {"title": name, "description": "", "icon": "📊"}
        )

    def list_panels(self) -> List[str]:
        """List all registered panel names."""
        return list(self._panels.keys())

    def has_panel(self, name: str) -> bool:
        """Check if panel exists."""
        return name in self._panels


class CommandRegistry:
    """Registry for dashboard commands."""

    def __init__(self):
        self._commands: Dict[str, Callable] = {}
        self._command_info: Dict[str, Dict[str, str]] = {}

    def add_command(
        self, name: str, cmd_fn: Callable, info: Optional[Dict[str, str]] = None
    ):
        """Add a command to the registry.

        Args:
            name: Command name (must be unique)
            cmd_fn: Function that executes the command
            info: Optional command metadata (description, shortcut, category)
        """
        self._commands[name] = cmd_fn
        self._command_info[name] = info or {
            "description": "",
            "shortcut": "",
            "category": "Custom",
        }

    def get_command(self, name: str) -> Optional[Callable]:
        """Get command function by name."""
        return self._commands.get(name)

    def get_command_info(self, name: str) -> Dict[str, str]:
        """Get command metadata by name."""
        return self._command_info.get(
            name, {"description": "", "shortcut": "", "category": "Custom"}
        )

    def list_commands(self) -> List[str]:
        """List all registered command names."""
        return list(self._commands.keys())

    def execute(self, name: str, dashboard: Any) -> bool:
        """Execute a command.

        Args:
            name: Command name
            dashboard: Dashboard instance to pass to command

        Returns:
            True if command executed successfully
        """
        cmd = self._commands.get(name)
        if cmd:
            try:
                cmd(dashboard)
                return True
            except Exception as e:
                if hasattr(dashboard, "notify"):
                    dashboard.notify(f"Command '{name}' failed: {e}", severity="error")
                return False
        return False


class ThemeRegistry:
    """Registry for dashboard themes."""

    def __init__(self):
        self._themes: Dict[str, Dict[str, str]] = {}

    def add_theme(self, name: str, css: str, info: Optional[Dict[str, str]] = None):
        """Add a theme to the registry.

        Args:
            name: Theme name (must be unique)
            css: CSS string for the theme
            info: Optional theme metadata (description, author, dark_mode)
        """
        self._themes[name] = {"css": css, "info": info or {}}

    def get_theme(self, name: str) -> Optional[Dict[str, str]]:
        """Get theme by name."""
        return self._themes.get(name)

    def list_themes(self) -> List[str]:
        """List all registered theme names."""
        return list(self._themes.keys())


class DashboardPlugin:
    """Base class for dashboard plugins.

    Subclass this to create a plugin:

    class MyPlugin(DashboardPlugin):
        name = "my-plugin"
        version = "1.0.0"
        description = "My custom plugin"

        def register_panels(self, registry):
            registry.add_panel("my-panel", self._get_my_panel_content)

        def register_commands(self, registry):
            registry.add_command("my-command", self._run_my_command)
    """

    name: str = "unnamed-plugin"
    version: str = "0.0.0"
    description: str = ""
    author: str = ""

    def register_panels(self, registry: PanelRegistry):
        """Register panels with the panel registry.

        Override this method to add custom panels.
        """
        pass

    def register_commands(self, registry: CommandRegistry):
        """Register commands with the command registry.

        Override this method to add custom commands.
        """
        pass

    def register_themes(self, registry: ThemeRegistry):
        """Register themes with the theme registry.

        Override this method to add custom themes.
        """
        pass

    def on_load(self, dashboard: Any):
        """Called when plugin is loaded.

        Override this method to perform initialization.
        """
        pass

    def on_unload(self, dashboard: Any):
        """Called when plugin is unloaded.

        Override this method to perform cleanup.
        """
        pass


class PluginManager:
    """Manages dashboard plugins."""

    def __init__(self):
        self.panel_registry = PanelRegistry()
        self.command_registry = CommandRegistry()
        self.theme_registry = ThemeRegistry()
        self._plugins: Dict[str, DashboardPlugin] = {}
        self._plugin_dir = Path("src/dashboard/plugins")

    def register_plugin(self, plugin_class: type):
        """Register a plugin class.

        Args:
            plugin_class: Plugin class (subclass of DashboardPlugin)
        """
        plugin = plugin_class()
        if plugin.name in self._plugins:
            raise ValueError(f"Plugin '{plugin.name}' already registered")

        self._plugins[plugin.name] = plugin
        plugin.register_panels(self.panel_registry)
        plugin.register_commands(self.command_registry)
        plugin.register_themes(self.theme_registry)

    def load_plugins_from_directory(self, directory: Optional[Path] = None):
        """Load all plugins from a directory.

        Args:
            directory: Directory to load plugins from (default: src/dashboard/plugins)
        """
        plugin_dir = directory or self._plugin_dir
        if not plugin_dir.exists():
            return

        for plugin_file in plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue

            try:
                spec = importlib.util.spec_from_file_location(
                    plugin_file.stem, plugin_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Find plugin classes in module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, DashboardPlugin)
                            and attr != DashboardPlugin
                        ):
                            self.register_plugin(attr)
            except Exception as e:
                print(f"Failed to load plugin {plugin_file}: {e}")

    def load_plugin_from_file(self, file_path: Path):
        """Load a single plugin from a file.

        Args:
            file_path: Path to plugin file
        """
        try:
            spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, DashboardPlugin)
                        and attr != DashboardPlugin
                    ):
                        self.register_plugin(attr)
        except Exception as e:
            print(f"Failed to load plugin {file_path}: {e}")

    def unload_plugin(self, name: str, dashboard: Any = None):
        """Unload a plugin.

        Args:
            name: Plugin name
            dashboard: Dashboard instance for cleanup
        """
        plugin = self._plugins.pop(name, None)
        if plugin:
            plugin.on_unload(dashboard)

    def list_plugins(self) -> List[Dict[str, str]]:
        """List all loaded plugins.

        Returns:
            List of plugin info dicts
        """
        return [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "author": p.author,
            }
            for p in self._plugins.values()
        ]

    def get_plugin(self, name: str) -> Optional[DashboardPlugin]:
        """Get plugin by name."""
        return self._plugins.get(name)

    def notify_plugins(self, event: str, data: Any = None):
        """Notify all plugins of an event.

        Args:
            event: Event name
            data: Event data
        """
        for plugin in self._plugins.values():
            if hasattr(plugin, "on_event"):
                try:
                    plugin.on_event(event, data)
                except Exception:
                    pass


# Global plugin manager instance
plugin_manager = PluginManager()


# Convenience functions
def register_plugin(plugin_class: type):
    """Register a plugin with the global plugin manager."""
    plugin_manager.register_plugin(plugin_class)


def get_panel_registry() -> PanelRegistry:
    """Get the global panel registry."""
    return plugin_manager.panel_registry


def get_command_registry() -> CommandRegistry:
    """Get the global command registry."""
    return plugin_manager.command_registry


def get_theme_registry() -> ThemeRegistry:
    """Get the global theme registry."""
    return plugin_manager.theme_registry

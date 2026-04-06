# Dashboard Plugins Package
"""Plugin system for extending dashboard functionality."""

from src.dashboard.plugins.plugin_system import (
    DashboardPlugin,
    PanelRegistry,
    CommandRegistry,
    ThemeRegistry,
    PluginManager,
    plugin_manager,
    register_plugin,
    get_panel_registry,
    get_command_registry,
    get_theme_registry,
)

__all__ = [
    "DashboardPlugin",
    "PanelRegistry",
    "CommandRegistry",
    "ThemeRegistry",
    "PluginManager",
    "plugin_manager",
    "register_plugin",
    "get_panel_registry",
    "get_command_registry",
    "get_theme_registry",
]

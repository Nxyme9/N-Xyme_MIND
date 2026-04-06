# Example Plugin
"""Example plugin demonstrating the dashboard plugin system.

This plugin adds:
- A custom "Plugins" panel showing loaded plugins
- A "reload-plugins" command
- A custom theme

Usage:
    This plugin is automatically loaded when the dashboard starts.
    To disable, set "example-plugin": false in dashboard-config.json plugins section.
"""

from src.dashboard.plugins import (
    DashboardPlugin,
    PanelRegistry,
    CommandRegistry,
    ThemeRegistry,
)
from src.dashboard.themes import Theme


class ExamplePlugin(DashboardPlugin):
    """Example plugin for the dashboard."""

    name = "example-plugin"
    version = "1.0.0"
    description = "Example plugin demonstrating the plugin system"
    author = "N-Xyme"

    def register_panels(self, registry: PanelRegistry):
        """Register custom panels."""
        registry.add_panel(
            "plugins",
            self._get_plugins_panel_content,
            {"title": "Plugins", "description": "Loaded plugins", "icon": "🔌"},
        )

    def register_commands(self, registry: CommandRegistry):
        """Register custom commands."""
        registry.add_command(
            "reload-plugins",
            self._reload_plugins_command,
            {
                "description": "Reload all plugins",
                "shortcut": "Ctrl+R",
                "category": "Plugins",
            },
        )

    def register_themes(self, registry: ThemeRegistry):
        """Register custom themes."""
        registry.add_theme(
            "example-theme",
            self._get_example_theme_css(),
            {"description": "Example theme", "dark_mode": True},
        )

    def _get_plugins_panel_content(self, dashboard) -> str:
        """Get plugins panel content."""
        from src.dashboard.plugins import plugin_manager

        plugins = plugin_manager.list_plugins()
        content = "LOADED PLUGINS\n\n"
        for plugin in plugins:
            content += f"  {plugin['name']} v{plugin['version']}\n"
            content += f"    {plugin['description']}\n"
            content += f"    Author: {plugin['author']}\n\n"

        if not plugins:
            content += "  No plugins loaded.\n"
            content += "  Add plugins to src/dashboard/plugins/ directory.\n"

        return content

    def _reload_plugins_command(self, dashboard):
        """Reload all plugins command."""
        from src.dashboard.plugins import plugin_manager

        try:
            plugin_manager.load_plugins_from_directory()
            dashboard.notify("Plugins reloaded", severity="information")
        except Exception as e:
            dashboard.notify(f"Failed to reload plugins: {e}", severity="error")

    def _get_example_theme_css(self) -> str:
        """Get example theme CSS."""
        return """
Screen { background: #1a1a2e; }
#sidebar { background: #16213e; border-right: thick #0f3460; }
#sidebar Button { background: #0f3460; }
#content { background: #1a1a2e; }
#status-bar { background: #0f3460; }
.panel-title { color: #e94560; }
.section-header { color: #533483; }
"""


class ExampleTheme(Theme):
    """Example theme for the dashboard."""

    name = "example-theme"
    description = "Example theme with custom colors"
    dark_mode = True
    author = "N-Xyme"
    version = "1.0.0"

    def get_css(self) -> str:
        return """
Screen { background: #1a1a2e; }
#sidebar { background: #16213e; border-right: thick #0f3460; }
#sidebar Button { background: #0f3460; }
#content { background: #1a1a2e; }
#status-bar { background: #0f3460; }
.panel-title { color: #e94560; }
.section-header { color: #533483; }
"""

    def get_color_palette(self) -> dict:
        return {
            "background": "#1a1a2e",
            "sidebar": "#16213e",
            "primary": "#0f3460",
            "accent": "#e94560",
            "secondary": "#533483",
        }

# Dashboard Configuration
"""Configuration-driven panel definitions and dashboard settings.

This module provides:
- Panel definitions (what panels exist, their order, visibility)
- Dashboard settings (refresh rate, theme, layout)
- Plugin configuration (which plugins are enabled)
- User preferences (saved across sessions)

Usage:
    from src.dashboard.config import DashboardConfig

    config = DashboardConfig()
    config.load()

    # Access panel definitions
    panels = config.get_panel_definitions()

    # Access settings
    refresh_rate = config.get_setting("refresh_rate", 10)

    # Update settings
    config.set_setting("refresh_rate", 5)
    config.save()
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import json
from datetime import datetime


class PanelDefinition:
    """Definition of a dashboard panel."""

    def __init__(
        self,
        name: str,
        title: str,
        description: str = "",
        icon: str = "📊",
        enabled: bool = True,
        order: int = 0,
        module: str = "",
        function: str = "",
        requires: List[str] = None,
    ):
        self.name = name
        self.title = title
        self.description = description
        self.icon = icon
        self.enabled = enabled
        self.order = order
        self.module = module
        self.function = function
        self.requires = requires or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "icon": self.icon,
            "enabled": self.enabled,
            "order": self.order,
            "module": self.module,
            "function": self.function,
            "requires": self.requires,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PanelDefinition":
        """Create from dictionary."""
        return cls(
            name=data.get("name", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            icon=data.get("icon", "📊"),
            enabled=data.get("enabled", True),
            order=data.get("order", 0),
            module=data.get("module", ""),
            function=data.get("function", ""),
            requires=data.get("requires", []),
        )


class DashboardConfig:
    """Configuration for the dashboard."""

    def __init__(self, config_path: str = ".sisyphus/dashboard-config.json"):
        self.config_path = Path(config_path)
        self.panels: List[PanelDefinition] = []
        self.settings: Dict[str, Any] = {}
        self.plugins: Dict[str, bool] = {}
        self.preferences: Dict[str, Any] = {}
        self._defaults()

    def _defaults(self):
        """Set default configuration."""
        # Default panels
        self.panels = [
            PanelDefinition("overview", "Overview", "System overview", "🏠", True, 0),
            PanelDefinition("memory", "Memory", "Memory system", "🧠", True, 1),
            PanelDefinition(
                "intelligence", "Intelligence", "Intelligence layer", "🤖", True, 2
            ),
            PanelDefinition(
                "orchestration", "Orchestration", "Agent orchestration", "🎭", True, 3
            ),
            PanelDefinition("proxy", "Proxy/VPN", "Proxy and VPN", "🌐", True, 4),
            PanelDefinition("brain", "Brain", "Brain system", "🧩", True, 5),
            PanelDefinition("learning", "Learning", "Learning system", "📚", True, 6),
            PanelDefinition("security", "Security", "Security layer", "🔒", True, 7),
            PanelDefinition(
                "model-router", "Model Router", "Model routing", "🔄", True, 8
            ),
            PanelDefinition("workers", "Workers", "Worker processes", "⚙️", True, 9),
            PanelDefinition("blocks", "Blocks", "GPU/Blocks", "🧱", True, 10),
        ]

        # Default settings
        self.settings = {
            "refresh_rate": 10,
            "theme": "default",
            "dark_mode": True,
            "show_data_age": True,
            "show_sparklines": True,
            "auto_save_config": True,
            "max_history_entries": 20,
            "log_level": "info",
            "enable_notifications": True,
            "notification_timeout": 5,
        }

        # Default plugins (all enabled)
        self.plugins = {
            "core": True,
            "config-editor": True,
            "settings-screen": True,
            "command-palette": True,
        }

        # Default preferences
        self.preferences = {
            "last_view": "overview",
            "last_theme": "default",
            "last_dark_mode": True,
            "window_size": None,
            "window_position": None,
        }

    def load(self):
        """Load configuration from file."""
        if not self.config_path.exists():
            return

        try:
            data = json.loads(self.config_path.read_text())

            # Load panels
            if "panels" in data:
                self.panels = [PanelDefinition.from_dict(p) for p in data["panels"]]

            # Load settings
            if "settings" in data:
                self.settings.update(data["settings"])

            # Load plugins
            if "plugins" in data:
                self.plugins.update(data["plugins"])

            # Load preferences
            if "preferences" in data:
                self.preferences.update(data["preferences"])
        except Exception as e:
            print(f"Failed to load config: {e}")

    def save(self):
        """Save configuration to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "panels": [p.to_dict() for p in self.panels],
                "settings": self.settings,
                "plugins": self.plugins,
                "preferences": self.preferences,
                "last_updated": datetime.now().isoformat(),
            }
            self.config_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Failed to save config: {e}")

    def get_panel_definitions(self) -> List[PanelDefinition]:
        """Get all panel definitions."""
        return sorted(self.panels, key=lambda p: p.order)

    def get_enabled_panels(self) -> List[PanelDefinition]:
        """Get enabled panel definitions."""
        return sorted([p for p in self.panels if p.enabled], key=lambda p: p.order)

    def get_panel(self, name: str) -> Optional[PanelDefinition]:
        """Get panel definition by name."""
        for panel in self.panels:
            if panel.name == name:
                return panel
        return None

    def add_panel(self, panel: PanelDefinition):
        """Add a panel definition."""
        self.panels.append(panel)

    def remove_panel(self, name: str):
        """Remove a panel definition by name."""
        self.panels = [p for p in self.panels if p.name != name]

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: Any):
        """Set a setting value."""
        self.settings[key] = value

    def get_plugin_enabled(self, name: str) -> bool:
        """Check if plugin is enabled."""
        return self.plugins.get(name, False)

    def set_plugin_enabled(self, name: str, enabled: bool):
        """Enable or disable a plugin."""
        self.plugins[name] = enabled

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a preference value."""
        return self.preferences.get(key, default)

    def set_preference(self, key: str, value: Any):
        """Set a preference value."""
        self.preferences[key] = value

    def reset_to_defaults(self):
        """Reset configuration to defaults."""
        self._defaults()


# Global config instance
config = DashboardConfig()


# Convenience functions
def get_config() -> DashboardConfig:
    """Get the global config instance."""
    return config


def load_config():
    """Load configuration from file."""
    config.load()


def save_config():
    """Save configuration to file."""
    config.save()

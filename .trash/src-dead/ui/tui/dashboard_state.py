"""
Dashboard state management module.

Provides persistent state storage for the TUI dashboard.
"""

from dataclasses import dataclass, field, asdict
import json
from pathlib import Path
from typing import Any


CONFIG_DIR = Path.home() / ".config" / "n-xyme"
CONFIG_FILE = CONFIG_DIR / "dashboard_state.json"


@dataclass
class DashboardState:
    """
    Manages dashboard state persistence.

    Attributes:
        current_tab: Currently active tab identifier.
        auto_refresh: Whether auto-refresh is enabled.
        sparklines_enabled: Whether sparkline charts are enabled.
        notifications_enabled: Whether notifications are enabled.
        preferences: Additional user preferences dictionary.
    """

    current_tab: str = "home"
    auto_refresh: bool = True
    sparklines_enabled: bool = True
    notifications_enabled: bool = True
    preferences: dict[str, Any] = field(default_factory=dict)

    def save(self) -> None:
        """
        Write state to JSON configuration file.

        Creates the config directory if it doesn't exist.
        Handles I/O errors gracefully.
        """
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2)
        except (IOError, OSError) as e:
            # Silently fail on write errors to avoid disrupting the UI
            pass

    def load(self) -> "DashboardState":
        """
        Load state from JSON configuration file.

        Returns:
            DashboardState: The loaded state, or default state if file not found.
        """
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return DashboardState(
                    current_tab=data.get("current_tab", "home"),
                    auto_refresh=data.get("auto_refresh", True),
                    sparklines_enabled=data.get("sparklines_enabled", True),
                    notifications_enabled=data.get("notifications_enabled", True),
                    preferences=data.get("preferences", {}),
                )
        except (IOError, OSError, json.JSONDecodeError):
            pass
        return self._default()

    def reset(self) -> None:
        """
        Reset state to default values.

        Resets all attributes to their default values.
        """
        default_state = self._default()
        self.current_tab = default_state.current_tab
        self.auto_refresh = default_state.auto_refresh
        self.sparklines_enabled = default_state.sparklines_enabled
        self.notifications_enabled = default_state.notifications_enabled
        self.preferences = default_state.preferences

    @staticmethod
    def _default() -> "DashboardState":
        """Create a default state instance."""
        return DashboardState(
            current_tab="home",
            auto_refresh=True,
            sparklines_enabled=True,
            notifications_enabled=True,
            preferences={},
        )

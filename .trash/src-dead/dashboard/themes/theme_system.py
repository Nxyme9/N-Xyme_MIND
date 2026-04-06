# Dashboard Theme System
"""Theme system for customizing dashboard appearance.

Themes can:
- Define custom CSS
- Define color palettes
- Define typography
- Define layout preferences

Usage:
    # In your theme file:
    from src.dashboard.themes import Theme, register_theme

    class MyTheme(Theme):
        name = "my-theme"
        description = "My custom theme"
        dark_mode = True

        def get_css(self) -> str:
            return '''
            Screen { background: #1a1a1a; }
            #sidebar { background: #2a2a2a; }
            '''

    # Register the theme
    register_theme(MyTheme)
"""

from typing import Dict, List, Optional
from pathlib import Path
import json


class Theme:
    """Base class for dashboard themes.

    Subclass this to create a theme:

    class MyTheme(Theme):
        name = "my-theme"
        description = "My custom theme"
        dark_mode = True

        def get_css(self) -> str:
            return '''
            Screen { background: #1a1a1a; }
            #sidebar { background: #2a2a2a; }
            '''
    """

    name: str = "unnamed-theme"
    description: str = ""
    dark_mode: bool = True
    author: str = ""
    version: str = "0.0.0"

    def get_css(self) -> str:
        """Get CSS for this theme.

        Returns:
            CSS string
        """
        return ""

    def get_color_palette(self) -> Dict[str, str]:
        """Get color palette for this theme.

        Returns:
            Dict of color name to color value
        """
        return {}

    def get_font_settings(self) -> Dict[str, str]:
        """Get font settings for this theme.

        Returns:
            Dict of font settings
        """
        return {}


class ThemeManager:
    """Manages dashboard themes."""

    def __init__(self):
        self._themes: Dict[str, Theme] = {}
        self._active_theme: Optional[str] = None
        self._theme_dir = Path("src/dashboard/themes")

    def register_theme(self, theme_class: type):
        """Register a theme class.

        Args:
            theme_class: Theme class (subclass of Theme)
        """
        theme = theme_class()
        if theme.name in self._themes:
            raise ValueError(f"Theme '{theme.name}' already registered")

        self._themes[theme.name] = theme

    def load_themes_from_directory(self, directory: Optional[Path] = None):
        """Load all themes from a directory.

        Args:
            directory: Directory to load themes from (default: src/dashboard/themes)
        """
        theme_dir = directory or self._theme_dir
        if not theme_dir.exists():
            return

        for theme_file in theme_dir.glob("*.py"):
            if theme_file.name.startswith("_"):
                continue

            try:
                import importlib.util

                spec = importlib.util.spec_from_file_location(
                    theme_file.stem, theme_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, Theme)
                            and attr != Theme
                        ):
                            self.register_theme(attr)
            except Exception as e:
                print(f"Failed to load theme {theme_file}: {e}")

    def set_active_theme(self, name: str):
        """Set the active theme.

        Args:
            name: Theme name
        """
        if name not in self._themes:
            raise ValueError(f"Theme '{name}' not found")

        self._active_theme = name

    def get_active_theme(self) -> Optional[Theme]:
        """Get the active theme.

        Returns:
            Active theme instance or None
        """
        if self._active_theme:
            return self._themes.get(self._active_theme)
        return None

    def get_active_theme_css(self) -> str:
        """Get CSS for the active theme.

        Returns:
            CSS string
        """
        theme = self.get_active_theme()
        if theme:
            return theme.get_css()
        return ""

    def list_themes(self) -> List[Dict[str, str]]:
        """List all registered themes.

        Returns:
            List of theme info dicts
        """
        return [
            {
                "name": t.name,
                "description": t.description,
                "dark_mode": t.dark_mode,
                "author": t.author,
                "version": t.version,
            }
            for t in self._themes.values()
        ]

    def get_theme(self, name: str) -> Optional[Theme]:
        """Get theme by name."""
        return self._themes.get(name)


# Global theme manager instance
theme_manager = ThemeManager()


# Convenience functions
def register_theme(theme_class: type):
    """Register a theme with the global theme manager."""
    theme_manager.register_theme(theme_class)


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager."""
    return theme_manager

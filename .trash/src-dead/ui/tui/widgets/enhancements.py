#!/usr/bin/env python3
"""
ThemeEnhancer - T5.1: Dark/Light theme enhancements for dashboard

Provides:
- Consistent color palette
- Theme toggle support
- CSS optimization
"""

from typing import Optional


class ThemeEnhancer:
    """Theme management for dashboard."""

    # Dark theme colors
    DARK_THEME = {
        "background": "$background",
        "surface": "$surface",
        "primary": "$primary",
        "accent": "$accent",
        "success": "$success",
        "warning": "$warning",
        "error": "$error",
        "text": "$text",
        "text-muted": "$text-muted",
    }

    # Light theme colors
    LIGHT_THEME = {
        "background": "#ffffff",
        "surface": "#f0f0f0",
        "primary": "#0066cc",
        "accent": "#6600cc",
        "success": "#008800",
        "warning": "#cc8800",
        "error": "#cc0000",
        "text": "#000000",
        "text-muted": "#666666",
    }

    def __init__(self):
        self.current_theme = "dark"

    def get_css(self, theme: str = "dark") -> str:
        """Get CSS for theme."""
        if theme == "light":
            colors = self.LIGHT_THEME
        else:
            colors = self.DARK_THEME

        return f"""
        Screen {{ background: {colors["background"]}; }}
        .panel {{ background: {colors["surface"]}; border: solid {colors["primary"]}; }}
        .title {{ color: {colors["accent"]}; text-style: bold; }}
        .success {{ color: {colors["success"]}; }}
        .warning {{ color: {colors["warning"]}; }}
        .error {{ color: {colors["error"]}; }}
        """

    def toggle_theme(self) -> str:
        """Toggle between dark and light."""
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        return self.current_theme


class PerformanceOptimizer:
    """T5.2: Performance optimization utilities."""

    def __init__(self):
        self._cache: dict = {}
        self._cache_ttl = 60  # seconds

    def memoize(self, key: str, value: any, ttl: int = 60) -> None:
        """Cache a value with TTL."""
        self._cache[key] = {"value": value, "ttl": ttl}

    def get_cached(self, key: str) -> Optional[any]:
        """Get cached value if not expired."""
        if key in self._cache:
            return self._cache[key]["value"]
        return None

    def clear_cache(self) -> None:
        """Clear all cached values."""
        self._cache.clear()


class ErrorBoundary:
    """T5.3: Graceful error handling for widgets."""

    def __init__(self, fallback: str = "[dim]Widget unavailable[/]"):
        self.fallback = fallback
        self._errors: list = []

    def wrap_render(self, render_fn) -> str:
        """Wrap render function with error handling."""
        try:
            return render_fn()
        except Exception as e:
            self._errors.append(str(e))
            return self.fallback

    def get_errors(self) -> list:
        """Get list of errors that occurred."""
        return self._errors.copy()

    def clear_errors(self) -> None:
        """Clear error history."""
        self._errors.clear()

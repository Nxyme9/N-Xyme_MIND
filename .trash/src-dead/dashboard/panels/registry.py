# Panel Registry Helper
"""Helper to register all built-in panels."""

from typing import Any
from src.dashboard.plugins import PanelRegistry


def register_builtin_panels(registry: PanelRegistry):
    """Register all built-in panels.

    Args:
        registry: Panel registry instance
    """
    # Import panel modules
    from src.dashboard.panels import overview, memory, intelligence

    # Register panels
    registry.add_panel(
        "overview",
        overview.get_content,
        {"title": "Overview", "description": "System overview", "icon": "🏠"},
    )
    registry.add_panel(
        "memory",
        memory.get_content,
        {"title": "Memory", "description": "Memory system", "icon": "🧠"},
    )
    registry.add_panel(
        "intelligence",
        intelligence.get_content,
        {"title": "Intelligence", "description": "Intelligence layer", "icon": "🤖"},
    )

"""
Dashboard constants for N-Xyme MIND TUI.

This module contains all constant definitions used across the TUI dashboard,
including tab identifiers, event types, refresh intervals, and button IDs.
"""


# =============================================================================
# Tab Identifiers
# =============================================================================

TAB_IDS = {
    "OVERVIEW": "tab-overview",
    "AGENTS": "tab-agents",
    "MEMORY": "tab-memory",
    "INTELLIGENCE": "tab-intelligence",
    "PROXY": "tab-proxy",
    "CONFIG": "tab-config",
    "HEALTH": "tab-health",
    "SKILLS": "tab-skills",
    "ROUTING": "tab-routing",
    "SETTINGS": "tab-settings",
    "MCP": "tab-mcp",
    "BENCHMARKS": "tab-benchmarks",
    "TASKS": "tab-tasks",
    "OBSERVATIONS": "tab-observations",
    "K_GRAPH": "tab-k-graph",
    "L_COSTS": "tab-l-costs",
    "M_FEED": "tab-m-feed",
}


# =============================================================================
# Event Types
# =============================================================================

EVENT_TYPES = {
    "TAB_CHANGED": "tab.changed",
    "DATA_REFRESHED": "data.refreshed",
    "DAEMON_STARTED": "daemon.started",
    "DAEMON_STOPPED": "daemon.stopped",
    "CONFIG_SAVED": "config.saved",
    "THEME_CHANGED": "theme.changed",
    "REFRESH_TOGGLED": "refresh.toggled",
}


# =============================================================================
# Refresh Intervals (in seconds)
# =============================================================================

REFRESH_INTERVALS = {
    "DEFAULT_REFRESH": 5,
    "FAST_REFRESH": 1,
    "SLOW_REFRESH": 30,
}


# =============================================================================
# Button IDs for Common Actions
# =============================================================================

BUTTON_IDS = {
    "SAVE_CONFIG": "config-save-btn",
    "REFRESH_DATA": "refresh-data-btn",
    "CLEAR_CACHE": "clear-cache-btn",
    "TOGGLE_DARK": "toggle-dark-btn",
}
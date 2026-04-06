#!/usr/bin/env python3
"""
Command Palette - VSCode-style command quick access

T3.1 from dashboard-v2-plan.md:
- Cmd+K / Ctrl+K activation
- Fuzzy search commands
- Quick actions and navigation
"""

from typing import Callable, Dict, List, Optional

from textual.app import ComposeResult
from textual.widgets import Input, Static, ListView, ListItem


class Command:
    """Represents a command in the palette."""

    def __init__(
        self,
        id: str,
        label: str,
        description: str = "",
        category: str = "General",
        action: Optional[Callable] = None,
        shortcut: str = "",
    ):
        self.id = id
        self.label = label
        self.description = description
        self.category = category
        self.action = action
        self.shortcut = shortcut

    def matches(self, query: str) -> bool:
        """Check if command matches the query (fuzzy)."""
        query = query.lower()
        label = self.label.lower()
        desc = self.description.lower()

        # Direct substring match
        if query in label or query in desc:
            return True

        # Fuzzy: all characters in order
        if all(c in label for c in query):
            return True

        return False


class CommandPaletteCommands:
    """Default commands for the dashboard."""

    # Action method mappings to ultimate_dashboard
    ACTION_MAP = {
        # Navigation
        "nav.overview": "action_tab_overview",
        "nav.agents": "action_tab_agents",
        "nav.memory": "action_tab_memory",
        "nav.intelligence": "action_tab_intelligence",
        "nav.proxy": "action_tab_proxy",
        "nav.config": "action_tab_config",
        "nav.health": "action_tab_health",
        "nav.skills": "action_tab_skills",
        "nav.routing": "action_tab_routing",
        "nav.settings": "action_tab_settings_panel",
        "nav.mcp": "action_tab_mcp",
        "nav.benchmarks": "action_tab_benchmarks",
        "nav.tasks": "action_tab_tasks",
        "nav.observations": "action_tab_observations",
        "nav.knowledge": "action_tab_knowledge",
        "nav.costs": "action_tab_costs",
        "nav.activity": "action_tab_activity",
        # General Actions
        "action.refresh": "action_refresh",
        "action.dark": "action_toggle_dark",
        "action.help": "action_show_help",
        "action.palette": "action_command_palette",
        "action.edit_config": "action_edit_config",
        "action.search": "action_search",
        "action.export": "action_export",
        "action.settings": "action_settings",
        "action.clear_cache": "_action_clear_cache",
        "action.stats": "_action_show_stats",
        # Daemon
        "daemon.start": "_action_start_daemon",
        "daemon.stop": "_action_stop_daemon",
        # Agents
        "agents.start": "_action_start_agents",
        "agents.stop": "_action_stop_agents",
        "agents.restart": "_action_restart_agents",
        "agents.add": "_action_add_agent",
        # Memory
        "memory.clear": "_action_clear_memory",
        "memory.optimize": "_action_optimize_memory",
        "memory.explore": "_action_explore_memory",
        "memory.export": "_action_export_memory",
        "memory.import": "_action_import_memory",
        # Intelligence
        "intelligence.retrain": "_action_retrain_model",
        "intelligence.metrics": "_action_view_metrics",
        "intelligence.benchmark": "_action_run_benchmark",
        # Proxy
        "proxy.start": "_action_start_proxies",
        "proxy.stop": "_action_stop_proxies",
        "proxy.rotate": "_action_rotate_ips",
        "proxy.add_backend": "_action_add_backend",
        # Config
        "config.save": "_action_save_config",
        "config.new": "_action_new_config",
        "config.open": "_action_open_config",
        "config.validate": "_action_validate_config",
        "config.export": "_action_export_config",
        # Health
        "health.check": "_action_run_health_check",
        "health.report": "_action_view_health_report",
        "health.alert": "_action_send_alert",
        # Skills
        "skills.add": "_action_add_skill",
        "skills.reload": "_action_reload_skills",
        "skills.export": "_action_export_skills",
        # Routing
        "routing.refresh": "_action_refresh_routes",
        "routing.stats": "_action_view_routing_stats",
        "routing.add_trigger": "_action_add_trigger",
        # Settings
        "settings.save": "_action_save_settings",
        "settings.load": "_action_load_settings",
        "settings.reset": "_action_reset_settings",
        # MCP
        "mcp.refresh": "_action_refresh_mcp",
        "mcp.add": "_action_add_mcp_server",
        "mcp.test": "_action_test_mcp",
        # Benchmarks
        "benchmarks.run_all": "_action_run_all_benchmarks",
        "benchmarks.compare": "_action_compare_benchmarks",
        "benchmarks.export": "_action_export_benchmarks",
        "benchmarks.run": "_action_run_benchmark",
        # Tasks
        "tasks.new": "_action_new_task",
        "tasks.start": "_action_start_tasks",
        "tasks.stop": "_action_stop_tasks",
        "tasks.clear_done": "_action_clear_done_tasks",
        # Observations
        "observations.refresh": "_action_refresh_observations",
        "observations.export": "_action_export_observations",
        "observations.clear": "_action_clear_observations",
        # Knowledge
        "knowledge.refresh": "_action_refresh_kg",
        "knowledge.load": "_action_load_kg",
        "knowledge.export": "_action_export_kg",
        # Costs
        "costs.refresh": "_action_refresh_costs",
        "costs.detailed": "_action_detailed_costs",
        "costs.export": "_action_export_costs",
        # Activity
        "activity.view": "_action_view_activity_log",
        "activity.refresh": "_action_refresh_feed",
        "activity.pause": "_action_pause_feed",
        "activity.clear": "_action_clear_feed",
    }

    @staticmethod
    def get_commands() -> List[Command]:
        return [
            # Navigation (17 commands)
            Command(
                "nav.overview",
                "Go to Overview",
                "Switch to overview panel",
                "Navigation",
                shortcut="1",
            ),
            Command(
                "nav.agents",
                "Go to Agents",
                "Switch to agents panel",
                "Navigation",
                shortcut="2",
            ),
            Command(
                "nav.memory",
                "Go to Memory",
                "Switch to memory panel",
                "Navigation",
                shortcut="3",
            ),
            Command(
                "nav.intelligence",
                "Go to Intelligence",
                "Switch to intelligence panel",
                "Navigation",
                shortcut="4",
            ),
            Command(
                "nav.proxy",
                "Go to Proxy",
                "Switch to proxy panel",
                "Navigation",
                shortcut="5",
            ),
            Command(
                "nav.config",
                "Go to Config",
                "Switch to config panel",
                "Navigation",
                shortcut="6",
            ),
            Command(
                "nav.health",
                "Go to Health",
                "Switch to health panel",
                "Navigation",
                shortcut="7",
            ),
            Command(
                "nav.skills",
                "Go to Skills",
                "Switch to skills panel",
                "Navigation",
                shortcut="8",
            ),
            Command(
                "nav.routing",
                "Go to Routing",
                "Switch to routing panel",
                "Navigation",
                shortcut="9",
            ),
            Command(
                "nav.settings",
                "Go to Settings",
                "Switch to settings panel",
                "Navigation",
                shortcut="0",
            ),
            Command("nav.mcp", "Go to MCP", "Switch to MCP panel", "Navigation"),
            Command(
                "nav.benchmarks",
                "Go to Benchmarks",
                "Switch to benchmarks panel",
                "Navigation",
            ),
            Command("nav.tasks", "Go to Tasks", "Switch to tasks panel", "Navigation"),
            Command(
                "nav.observations",
                "Go to Observations",
                "Switch to observations panel",
                "Navigation",
            ),
            Command(
                "nav.knowledge",
                "Go to Knowledge",
                "Switch to knowledge panel",
                "Navigation",
            ),
            Command("nav.costs", "Go to Costs", "Switch to costs panel", "Navigation"),
            Command(
                "nav.activity",
                "Go to Activity",
                "Switch to activity panel",
                "Navigation",
            ),
            # System Actions (11 commands)
            Command(
                "action.refresh",
                "Refresh Data",
                "Refresh all dashboard data",
                "System",
                shortcut="R",
            ),
            Command(
                "action.dark",
                "Toggle Dark Mode",
                "Switch between light/dark theme",
                "System",
                shortcut="D",
            ),
            Command(
                "action.help",
                "Show Help",
                "Display keyboard shortcuts",
                "System",
                shortcut="?",
            ),
            Command(
                "action.palette",
                "Command Palette",
                "Open command palette",
                "System",
                shortcut="Ctrl+K",
            ),
            Command(
                "action.clear_cache", "Clear Cache", "Clear dashboard cache", "System"
            ),
            Command(
                "action.stats", "Show Stats", "Display system statistics", "System"
            ),
            Command(
                "action.search",
                "Search",
                "Search across all data",
                "System",
                shortcut="S",
            ),
            Command(
                "action.export",
                "Export Dashboard",
                "Export current view as JSON",
                "System",
                shortcut="E",
            ),
            Command(
                "action.settings", "Settings", "Open settings", "System", shortcut="X"
            ),
            Command(
                "action.edit_config",
                "Edit Config",
                "Edit configuration files",
                "System",
                shortcut="C",
            ),
            # Daemon Actions (2 commands)
            Command(
                "daemon.start", "Start Daemon", "Start the background daemon", "Daemon"
            ),
            Command(
                "daemon.stop", "Stop Daemon", "Stop the background daemon", "Daemon"
            ),
            # Agent Actions (4 commands)
            Command(
                "agents.start",
                "Start All Agents",
                "Start all agent processes",
                "Agents",
            ),
            Command(
                "agents.stop", "Stop All Agents", "Stop all agent processes", "Agents"
            ),
            Command("agents.restart", "Restart Agents", "Restart all agents", "Agents"),
            Command(
                "agents.add", "Add Agent", "Add a new agent configuration", "Agents"
            ),
            # Memory Actions (5 commands)
            Command("memory.clear", "Clear Memory", "Clear all memory data", "Memory"),
            Command(
                "memory.optimize",
                "Optimize Memory",
                "Optimize memory storage",
                "Memory",
            ),
            Command(
                "memory.explore", "Explore Memory", "Open memory explorer", "Memory"
            ),
            Command(
                "memory.export", "Export Memory", "Export memory to file", "Memory"
            ),
            Command(
                "memory.import", "Import Memory", "Import memory from file", "Memory"
            ),
            # Intelligence Actions (3 commands)
            Command(
                "intelligence.retrain",
                "Retrain Model",
                "Retrain the intelligence model",
                "Intelligence",
            ),
            Command(
                "intelligence.metrics",
                "View Metrics",
                "View intelligence metrics",
                "Intelligence",
            ),
            Command(
                "intelligence.benchmark",
                "Run Benchmark",
                "Run a single benchmark",
                "Intelligence",
            ),
            # Proxy Actions (4 commands)
            Command("proxy.start", "Start Proxies", "Start all proxy servers", "Proxy"),
            Command("proxy.stop", "Stop Proxies", "Stop all proxy servers", "Proxy"),
            Command("proxy.rotate", "Rotate IPs", "Rotate proxy IP addresses", "Proxy"),
            Command(
                "proxy.add_backend", "Add Backend", "Add a new proxy backend", "Proxy"
            ),
            # Config Actions (5 commands)
            Command(
                "config.save", "Save Config", "Save current configuration", "Config"
            ),
            Command("config.new", "New Config", "Create new configuration", "Config"),
            Command("config.open", "Open Config", "Open configuration file", "Config"),
            Command(
                "config.validate", "Validate Config", "Validate configuration", "Config"
            ),
            Command("config.export", "Export Config", "Export configuration", "Config"),
            # Health Actions (3 commands)
            Command(
                "health.check", "Run Health Check", "Run system health check", "Health"
            ),
            Command(
                "health.report",
                "View Health Report",
                "View detailed health report",
                "Health",
            ),
            Command("health.alert", "Send Alert", "Send health alert", "Health"),
            # Skill Actions (3 commands)
            Command("skills.add", "Add Skill", "Add a new skill", "Skills"),
            Command("skills.reload", "Reload Skills", "Reload all skills", "Skills"),
            Command(
                "skills.export", "Export Skills", "Export skill definitions", "Skills"
            ),
            # Routing Actions (3 commands)
            Command(
                "routing.refresh", "Refresh Routes", "Refresh routing table", "Routing"
            ),
            Command(
                "routing.stats",
                "View Routing Stats",
                "View routing statistics",
                "Routing",
            ),
            Command(
                "routing.add_trigger", "Add Trigger", "Add a new trigger", "Routing"
            ),
            # Settings Actions (3 commands)
            Command(
                "settings.save", "Save Settings", "Save current settings", "Settings"
            ),
            Command(
                "settings.load", "Load Settings", "Load settings from file", "Settings"
            ),
            Command(
                "settings.reset", "Reset Settings", "Reset to defaults", "Settings"
            ),
            # MCP Actions (3 commands)
            Command("mcp.refresh", "Refresh MCP", "Refresh MCP servers", "MCP"),
            Command("mcp.add", "Add MCP Server", "Add new MCP server", "MCP"),
            Command("mcp.test", "Test MCP", "Test MCP connection", "MCP"),
            # Benchmark Actions (4 commands)
            Command(
                "benchmarks.run_all",
                "Run All Benchmarks",
                "Run all benchmarks",
                "Benchmarks",
            ),
            Command(
                "benchmarks.compare",
                "Compare Benchmarks",
                "Compare benchmark results",
                "Benchmarks",
            ),
            Command(
                "benchmarks.export",
                "Export Benchmarks",
                "Export benchmark results",
                "Benchmarks",
            ),
            Command(
                "benchmarks.run",
                "Run Benchmark",
                "Run a specific benchmark",
                "Benchmarks",
            ),
            # Task Actions (4 commands)
            Command("tasks.new", "New Task", "Create a new scheduled task", "Tasks"),
            Command("tasks.start", "Start Tasks", "Start scheduled tasks", "Tasks"),
            Command("tasks.stop", "Stop Tasks", "Stop scheduled tasks", "Tasks"),
            Command(
                "tasks.clear_done", "Clear Done Tasks", "Clear completed tasks", "Tasks"
            ),
            # Observation Actions (3 commands)
            Command(
                "observations.refresh",
                "Refresh Observations",
                "Refresh observation data",
                "Observations",
            ),
            Command(
                "observations.export",
                "Export Observations",
                "Export observations",
                "Observations",
            ),
            Command(
                "observations.clear",
                "Clear Observations",
                "Clear observation data",
                "Observations",
            ),
            # Knowledge Actions (3 commands)
            Command(
                "knowledge.refresh",
                "Refresh Knowledge",
                "Refresh knowledge graph",
                "Knowledge",
            ),
            Command(
                "knowledge.load", "Load Knowledge", "Load knowledge graph", "Knowledge"
            ),
            Command(
                "knowledge.export",
                "Export Knowledge",
                "Export knowledge graph",
                "Knowledge",
            ),
            # Cost Actions (3 commands)
            Command("costs.refresh", "Refresh Costs", "Refresh cost data", "Costs"),
            Command(
                "costs.detailed",
                "Detailed Costs",
                "View detailed cost breakdown",
                "Costs",
            ),
            Command("costs.export", "Export Costs", "Export cost data", "Costs"),
            # Activity Actions (4 commands)
            Command(
                "activity.view", "View Activity Log", "View activity log", "Activity"
            ),
            Command(
                "activity.refresh", "Refresh Feed", "Refresh activity feed", "Activity"
            ),
            Command("activity.pause", "Pause Feed", "Pause activity feed", "Activity"),
            Command("activity.clear", "Clear Feed", "Clear activity feed", "Activity"),
            # Special
            Command(
                "special.quit", "Quit", "Exit the dashboard", "Special", shortcut="Q"
            ),
        ]

    @staticmethod
    def filter_commands(query: str) -> List[Command]:
        """Filter commands by query."""
        commands = CommandPaletteCommands.get_commands()
        if not query:
            return commands
        return [c for c in commands if c.matches(query)]


def fuzzy_match(query: str, text: str) -> int:
    """
    Calculate fuzzy match score.
    Returns higher score for better matches.
    """
    query = query.lower()
    text = text.lower()

    # Exact substring
    if query in text:
        return 100

    # All characters in order
    qi = 0
    for c in text:
        if qi < len(query) and c == query[qi]:
            qi += 1
    if qi == len(query):
        return 50

    # Partial match
    score = 0
    for c in query:
        if c in text:
            score += 10

    return score

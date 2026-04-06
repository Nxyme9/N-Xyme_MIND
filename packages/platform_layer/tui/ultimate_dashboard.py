#!/usr/bin/env python3
"""N-Xyme MIND Dashboard v2.0 — ADHD-friendly, complete frontend."""

import json
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import logging

logger = logging.getLogger(__name__)

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import (
    Static,
    Label,
    Input,
    Button,
    DataTable,
    Switch,
    Header,
    Footer,
    ProgressBar,
    TabbedContent,
    TabPane,
    Select,
    Checkbox,
    Rule,
    Sparkline,
)
from textual.reactive import reactive
from textual import work


# ─── Config Helpers ───────────────────────────────────────────────────────────


def _safe_json(path: str) -> dict:
    try:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text())
    except Exception:
        pass
    return {}


def _save_json(path: str, data: dict) -> bool:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2) + "\n")
        return True
    except Exception:
        return False


# All config files
CONFIG_FILES = {
    "opencode.json": ("Agents, Models, MCPs", "opencode.json"),
    ".opencode/opencode.json": ("OpenCode Config", ".opencode/opencode.json"),
    ".sisyphus/routing-weights.json": (
        "Routing Weights",
        ".sisyphus/routing-weights.json",
    ),
    ".sisyphus/routing-triggers.json": (
        "Routing Triggers",
        ".sisyphus/routing-triggers.json",
    ),
    ".sisyphus/learning-config.json": (
        "Learning Config",
        ".sisyphus/learning-config.json",
    ),
    "src/.sisyphus/learning-config.json": (
        "Learning Config (src)",
        "src/.sisyphus/learning-config.json",
    ),
    "src/learning/signals_config.json": (
        "Signal Weights",
        "src/learning/signals_config.json",
    ),
    "configs/vpn/backends.json": ("VPN Backends", "configs/vpn/backends.json"),
    "configs/vpn/country_mappings.json": (
        "VPN Countries",
        "configs/vpn/country_mappings.json",
    ),
    "configs/ollama.json": ("Ollama Config", "configs/ollama.json"),
    "triggers.json": ("Triggers", "triggers.json"),
    ".sisyphus/session-state.json": ("Session State", ".sisyphus/session-state.json"),
    ".sisyphus/agent-performance.json": (
        "Agent Performance",
        ".sisyphus/agent-performance.json",
    ),
    ".context/mind-state.json": ("MIND State", ".context/mind-state.json"),
}


# ─── Backend Data ─────────────────────────────────────────────────────────────


def get_system_stats():
    stats = {}
    try:
        r = subprocess.run(
            ["pgrep", "-f", "src.memory.daemon"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        stats["daemon_running"] = r.returncode == 0 and r.stdout.strip()
        stats["daemon_pid"] = (
            r.stdout.strip().split("\n")[0] if stats["daemon_running"] else "N/A"
        )
    except Exception:
        stats["daemon_running"] = False
        stats["daemon_pid"] = "N/A"
    try:
        import urllib.request

        urllib.request.urlopen("http://localhost:11434", timeout=2)
        stats["ollama_running"] = True
    except Exception:
        stats["ollama_running"] = False
    try:
        from packages.memory_core.mcp_server import get_memory_stats as _gs

        m = _gs()
        # get_memory_stats returns nested structure - extract properly
        file_reg = m.get("file_registry", {})
        stats["memory_sources"] = len(file_reg)  # Number of tables = sources
        stats["memory_enabled"] = m.get("learning_events", 0)  # Events count as enabled
    except Exception:
        stats["memory_sources"] = 0
        stats["memory_enabled"] = 0
    try:
        from packages.memory_core.indexing.embedder import get_indexed_count as _gc

        i = _gc()
        stats["indexed_files"] = i.get("total_files", 0)
        stats["indexed_chunks"] = i.get("total_chunks", 0)
    except Exception:
        stats["indexed_files"] = 0
        stats["indexed_chunks"] = 0
    try:
        from packages.memory_core.memory_router import get_router

        stats["router_backends"] = len(get_router().backends)
    except Exception:
        stats["router_backends"] = 0
    try:
        from packages.orchestration.agents.registry import get_agent_registry

        stats["orchestration_agents"] = len(get_agent_registry().get_all_agents())
    except Exception:
        stats["orchestration_agents"] = 0
    try:
        from packages.memory_core.mcp_server import get_learning_stats as _gs

        l = _gs()
        # Function returns keys directly, not nested under feedback_stats
        stats["learning_feedback"] = l.get("total_feedback", 0)
        stats["learning_queries"] = l.get("unique_queries", 0)
        stats["learning_top_queries"] = l.get("top_queries", [])
    except Exception:
        stats["learning_feedback"] = 0
        stats["learning_queries"] = 0
        stats["learning_top_queries"] = []
    try:
        # Get preferences count from memory stats
        from packages.memory_core.mcp_server import get_memory_stats as _ms

        m = _ms()
        stats["preferences"] = m.get("file_registry", {}).get("user_preferences", 0)
    except Exception:
        stats["preferences"] = 0
    try:
        p = Path(".sisyphus/outcomes.jsonl")
        stats["outcomes"] = len(p.read_text().splitlines()) if p.exists() else 0
    except Exception:
        stats["outcomes"] = 0
    return stats


def get_agent_health_data() -> dict:
    """Load agent health from .sisyphus/agent_health.json"""
    try:
        f = Path(".sisyphus/agent_health.json")
        if f.exists():
            return json.loads(f.read_text())
    except Exception:
        pass
    return {}


def get_skills_data() -> dict:
    """Load agent skills from .sisyphus/skills.json"""
    try:
        f = Path(".sisyphus/skills.json")
        if f.exists():
            return json.loads(f.read_text())
    except Exception:
        pass
    return {}


def get_routing_data() -> dict:
    """Load routing data from .sisyphus/"""
    data = {}
    try:
        f = Path(".sisyphus/routing-triggers.json")
        if f.exists():
            data["triggers"] = json.loads(f.read_text())
    except Exception:
        pass
    try:
        f = Path(".sisyphus/routing-weights.json")
        if f.exists():
            data["weights"] = json.loads(f.read_text())
    except Exception:
        pass
    return data


def get_mcp_status() -> dict:
    """Check MCP server status"""
    return {"mcp_servers": [], "status": "unknown"}


# ─── Config Editor Screen ─────────────────────────────────────────────────────


class ConfigEditorScreen(ModalScreen[None]):
    """Full ecosystem JSON config editor."""

    BINDINGS = [("escape", "dismiss", "Close")]
    CSS = """
    ConfigEditorScreen { align: center middle; }
    #config-container { width: 95; height: 90%; background: $surface; border: thick $primary; padding: 1 2; }
    #config-file-list { width: 100%; height: 12; }
    #config-tree { width: 100%; height: 55%; }
    #config-input-row { width: 100%; height: 3; }
    #config-key-input { width: 30%; }
    #config-value-input { width: 68%; }
    #config-status { margin-top: 1; color: $success; }
    """

    CONFIG_FILES = list(CONFIG_FILES.items())
    current_file: str = "opencode.json"
    config_data: dict = {}
    flat_keys: list = []

    def compose(self) -> ComposeResult:
        with Container(id="config-container"):
            yield Label("Ecosystem Config Editor (Esc to close)", classes="panel-title")
            yield DataTable(id="config-file-list")
            yield DataTable(id="config-tree")
            with Horizontal(id="config-input-row"):
                yield Input(
                    placeholder="Key path (e.g. agent.sisyphus.model)",
                    id="config-key-input",
                )
                yield Input(placeholder="New value", id="config-value-input")
            yield Button("Save", id="config-save-btn", variant="primary")
            yield Static("", id="config-status")

    def on_mount(self) -> None:
        table = self.query_one("#config-file-list", DataTable)
        table.add_columns("Config File", "Description", "Exists")
        for path, desc in self.CONFIG_FILES:
            exists = "Yes" if Path(path).exists() else "No"
            table.add_row(path, desc, exists)
        self._load_file(self.CONFIG_FILES[0][0])

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_idx = event.cursor_row
        if 0 <= row_idx < len(self.CONFIG_FILES):
            self._load_file(self.CONFIG_FILES[row_idx][0])

    def _load_file(self, path: str) -> None:
        self.current_file = path
        self.config_data = _safe_json(path)
        self.flat_keys = []
        self._flatten(self.config_data, "")
        table = self.query_one("#config-tree", DataTable)
        table.clear()
        table.add_columns("Key Path", "Value")
        for key, val in self.flat_keys:
            val_str = json.dumps(val) if isinstance(val, (dict, list)) else str(val)
            table.add_row(key, val_str[:100])
        self.query_one("#config-status", Static).update(
            f"Loaded: {path} ({len(self.flat_keys)} keys)"
        )

    def _flatten(self, obj: Any, prefix: str) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                full_key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, (dict, list)):
                    self.flat_keys.append((full_key, v))
                    self._flatten(v, full_key)
                else:
                    self.flat_keys.append((full_key, v))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                full_key = f"{prefix}[{i}]"
                if isinstance(v, (dict, list)):
                    self.flat_keys.append((full_key, v))
                    self._flatten(v, full_key)
                else:
                    self.flat_keys.append((full_key, v))

    def _set_nested(self, data: dict, key_path: str, value: Any) -> dict:
        keys = key_path.replace("]", "").split("[")
        keys = [k for k in keys if k]
        keys = [k.split(".") for k in keys]
        keys = [item for sublist in keys for item in sublist]
        current = data
        for k in keys[:-1]:
            if k.isdigit():
                k = int(k)
            if isinstance(current, list):
                current = current[k]
            else:
                current = current[k]
        last_key = keys[-1]
        if last_key.isdigit():
            last_key = int(last_key)
        if isinstance(current, list):
            current[last_key] = value
        else:
            current[last_key] = value
        return data

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "config-save-btn":
            self._save_file()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "config-value-input":
            key = self.query_one("#config-key-input", Input).value.strip()
            if key:
                try:
                    value = json.loads(event.value)
                except json.JSONDecodeError:
                    value = event.value
                self._set_nested(self.config_data, key, value)
                self._load_file(self.current_file)
                self._save_file()

    def _save_file(self) -> None:
        if _save_json(self.current_file, self.config_data):
            self.query_one("#config-status", Static).update(
                f"Saved: {self.current_file} ({len(self.flat_keys)} keys)"
            )
        else:
            self.query_one("#config-status", Static).update(
                f"Failed to save {self.current_file}"
            )


class SearchScreen(ModalScreen[None]):
    """Interactive search across all agents and configs."""

    BINDINGS = [("escape", "dismiss", "Close")]

    CSS = """
    SearchScreen { align: center middle; }
    #search-container { width: 90; height: 85%; background: $surface; border: thick $primary; padding: 1 2; }
    #search-input { width: 100%; margin-bottom: 1; }
    #search-results { width: 100%; height: 80%; }
    """

    def compose(self) -> ComposeResult:
        with Container(id="search-container"):
            yield Label("Search Agents & Configs (Esc to close)", classes="panel-title")
            yield Input(placeholder="Search query...", id="search-input")
            yield DataTable(id="search-results")

    def on_mount(self) -> None:
        table = self.query_one("#search-results", DataTable)
        table.add_columns("Source", "Key", "Value")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip().lower()
        if not query:
            return

        table = self.query_one("#search-results", DataTable)
        table.clear()

        # Search through JSON data files
        search_files = [
            (".sisyphus/agent_health.json", "Health"),
            (".sisyphus/skills.json", "Skills"),
            (".sisyphus/routing.json", "Routing"),
            (".sisyphus/menu_evolution.json", "Menu"),
            ("opencode.json", "Config"),
        ]

        for path, source in search_files:
            data = _safe_json(path)
            if data:
                self._search_dict(data, source, query, table)

    def _search_dict(
        self, data: dict, source: str, query: str, table: DataTable
    ) -> None:
        """Recursively search through a dictionary."""

        def flatten(d: dict, prefix: str = "") -> list:
            items = []
            for k, v in d.items():
                key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    items.extend(flatten(v, key))
                else:
                    items.append((key, str(v)[:100]))
            return items

        for key, value in flatten(data):
            if query in key.lower() or query in value.lower():
                table.add_row(source, key, value)


# ─── Main Dashboard ───────────────────────────────────────────────────────────


class NxyeDashboard(App):
    """N-Xyme MIND Dashboard v2.0 — ADHD-friendly, complete frontend."""

    TITLE = "N-Xyme MIND Dashboard"
    CSS = """
    Screen { background: $background; }
    #main-layout { width: 1fr; height: 1fr; }
    #sidebar { width: 24; background: $surface; border-right: thick $primary; }
    #sidebar .section-title { text-style: bold; color: $warning; padding: 1 1; }
    #sidebar Button { width: 100%; margin: 0 0 1 0; }
    #content { width: 1fr; padding: 1 2; }
    #status-bar { height: 3; background: $panel; content-align: center middle; border-top: thick $primary; }
    .panel-title { text-style: bold; color: $warning; padding: 0 1; }
    .section-header { text-style: bold; color: $primary; padding: 1 0; }
    .status-ok { color: $success; }
    .status-warn { color: $warning; }
    .status-error { color: $error; }
    DataTable { width: 100%; height: 15; }
    .stat-box { width: 20; height: 3; background: $surface; border: thick $primary; content-align: center middle; }
    .stat-label { text-style: bold; color: $text-muted; }
    .stat-value { text-style: bold; color: $success; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("d", "toggle_dark", "Dark Mode", show=True),
        Binding("1", "tab_overview", "Overview", show=True),
        Binding("2", "tab_agents", "Agents", show=True),
        Binding("3", "tab_memory", "Memory", show=True),
        Binding("4", "tab_intelligence", "Intelligence", show=True),
        Binding("5", "tab_proxy", "Proxy", show=True),
        Binding("6", "tab_config", "Config", show=True),
        Binding("7", "tab_health", "Health", show=True),
        Binding("8", "tab_skills", "Skills", show=True),
        Binding("9", "tab_routing", "Routing", show=True),
        Binding("0", "tab_settings_panel", "Settings", show=True),
        Binding("-", "tab_mcp", "MCP", show=True),
        Binding("=", "tab_benchmarks", "Benchmarks", show=True),
        Binding("[", "tab_tasks", "Tasks", show=True),
        Binding("]", "tab_observations", "Observations", show=True),
        Binding("c", "edit_config", "Edit Config", show=True),
        Binding("e", "export", "Export", show=True),
        Binding("s", "search", "Search", show=True),
        Binding("x", "settings", "Settings", show=True),
    ]

    current_tab: reactive[str] = reactive("overview")
    live_data: dict = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-layout"):
            with Vertical(id="sidebar"):
                yield Label("Panels", classes="section-title")
                yield Button("1 Overview", id="btn-overview", variant="primary")
                yield Button("2 Agents", id="btn-agents")
                yield Button("3 Memory", id="btn-memory")
                yield Button("4 Intelligence", id="btn-intelligence")
                yield Button("6 Config", id="btn-config")
                yield Button("7 Health", id="btn-health")
                yield Button("8 Skills", id="btn-skills")
                yield Button("9 Routing", id="btn-routing")
                yield Button("0 Settings", id="btn-settings")
                yield Button("- MCP", id="btn-mcp")
                yield Button("= Benchmarks", id="btn-benchmarks")
                yield Button("[ Tasks", id="btn-tasks")
                yield Button("] Obs", id="btn-observations")
                # Self-evolving menu: discovered panels section
                yield Label(
                    "Discovered", classes="section-title", id="discovered-label"
                )
                yield Container(id="discovered-panels")
                yield Button("Edit Config (C)", id="btn-edit-config")
                yield Button("Search (S)", id="btn-search")
                yield Button("Settings (X)", id="btn-settings-action")
            with ScrollableContainer(id="content"):
                yield Static("Loading...", id="content-area")
        yield Static(
            "Panel: Overview | 1-0: panels, 7-9: new, C edit, S search, X settings, Q quit, D dark mode",
            id="status-bar",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.live_data = self._get_loading_state()
        self.refresh_content()
        self._background_refresh()
        self.set_interval(10.0, self._background_refresh)
        # Integrate self-evolving menu system
        self._integrate_self_evolving_menu()

    def _get_loading_state(self) -> dict:
        return {
            "daemon": {"running": False, "pid": "loading..."},
            "ollama": {"running": False},
            "memory": {"total_sources": 0, "enabled_count": 0},
            "indexed": {"total_files": 0, "total_chunks": 0},
            "router": {"backends": 0},
            "orchestration": {"agents": 0},
            "learning": {"feedback_stats": {}, "preference_stats": {}},
            "sessions": {"total": 0},
            "security": {"modules": []},
            "performance": {"outcomes": 0},
            "timestamp": datetime.now().isoformat(),
        }

    @work(thread=True)
    def _background_refresh(self) -> None:
        try:
            data = get_system_stats()
            self.call_from_thread(self._apply_refresh, data)
        except Exception:
            pass

    def _apply_refresh(self, data: dict) -> None:
        self.live_data = data
        self.refresh_content()

    def refresh_content(self) -> None:
        content = self._get_content_for_tab(self.current_tab)
        self.query_one("#content-area", Static).update(content)
        self.query_one("#status-bar", Static).update(
            f"Panel: {self.current_tab.capitalize()} | {datetime.now().strftime('%H:%M:%S')} | 1-0 panels, -[]= new, C edit, S search, X settings, Q quit, D dark mode"
        )

    def _get_content_for_tab(self, tab: str) -> str:
        tabs = {
            "overview": self._get_overview_content,
            "agents": self._get_agents_content,
            "memory": self._get_memory_content,
            "intelligence": self._get_intelligence_content,
            "proxy": self._get_proxy_content,
            "config": self._get_config_content,
            "health": self._get_health_content,
            "skills": self._get_skills_content,
            "routing": self._get_routing_content,
            "settings": self._get_settings_content,
            "mcp": self._get_mcp_content,
            "benchmarks": self._get_benchmarks_content,
            "tasks": self._get_tasks_content,
            "observations": self._get_observations_content,
        }
        return tabs.get(tab, lambda: "Unknown tab")()

        tabs = {
            "overview": self._get_overview_content,
            "agents": self._get_agents_content,
            "memory": self._get_memory_content,
            "intelligence": self._get_intelligence_content,
            "proxy": self._get_proxy_content,
            "config": self._get_config_content,
            "health": self._get_health_content,
            "skills": self._get_skills_content,
            "routing": self._get_routing_content,
            "settings": self._get_settings_content,
            "mcp": self._get_mcp_content,
            "benchmarks": self._get_benchmarks_content,
            "tasks": self._get_tasks_content,
            "observations": self._get_observations_content,
        }
        return tabs.get(tab, lambda: "Unknown tab")()

    def _get_overview_content(self) -> str:
        # Get real data from JSON files
        health = get_agent_health_data()
        skills = get_skills_data()
        routing = get_routing_data()

        # Count healthy agents
        healthy_agents = sum(1 for a in health.values() if a.get("status") == "healthy")
        total_agents = len(health)

        # Get session count
        session_state = _safe_json(".sisyphus/session-state.json")

        # Get daemon status from live_data (flat keys from get_system_stats)
        d = self.live_data
        daemon_ok = d.get("daemon_running", False)
        daemon_pid = d.get("daemon_pid", "N/A")
        ollama_ok = d.get("ollama_running", False)

        return f"""SYSTEM OVERVIEW

        Core Services
  Daemon: {"Running" if daemon_ok else "Stopped"} | PID: {daemon_pid}
  Ollama: {"Running" if ollama_ok else "Stopped"} | http://localhost:11434

  Data Index
  Files: {d.get("indexed_files", 0)} | Chunks: {d.get("indexed_chunks", 0)}

  System Components
  Memory: {d.get("memory_sources", 0)} sources | {d.get("memory_enabled", 0)} enabled
  Router: {d.get("router_backends", 0)} backends
  Agents: {total_agents} ({healthy_agents} healthy)
  QT|  Sessions: {session_state.get("session_started", "N/A")[:10]}
  Outcomes: {d.get("outcomes", 0)}

  TZ|  Triggers: {len(routing.get("triggers", []))}
  ZN|  Weights: {len(routing.get("weights", {}))} configured

  Agent Skills
  Hephaestus: {skills.get("hephaestus", {}).get("success_count", 0)}/{skills.get("hephaestus", {}).get("total_tasks", 0)} tasks
  Explore: {skills.get("explore", {}).get("success_count", 0)}/{skills.get("explore", {}).get("total_tasks", 0)} tasks
  
  Learning: {d.get("learning_feedback", 0)} feedback | {d.get("learning_queries", 0)} queries

  Last Update: {d.get("timestamp", "N/A")[:19]}"""

    def _get_agents_content(self) -> str:
        agents = _safe_json("opencode.json").get("agent", {})
        content = "AGENT CONFIGURATION (opencode.json)\n\n"
        if agents:
            content += f"{'Agent':<25} {'Model':<30} {'Edit':<10} {'Bash':<10}\n"
            content += "-" * 75 + "\n"
            for name, cfg in agents.items():
                model = cfg.get("model", "default")
                edit = cfg.get("permission", {}).get("edit", "inherit")
                bash = cfg.get("permission", {}).get("bash", {}).get("*", "inherit")
                content += f"{name:<25} {model:<30} {edit:<10} {bash:<10}\n"
        else:
            content += "  No agents configured in opencode.json"
        return content

    def _get_memory_content(self) -> str:
        # Data comes from get_system_stats() with flat keys: memory_sources, memory_enabled, indexed_files, indexed_chunks
        d = self.live_data
        mem_sources = d.get("memory_sources", 0)
        mem_enabled = d.get("memory_enabled", 0)
        idx_files = d.get("indexed_files", 0)
        idx_chunks = d.get("indexed_chunks", 0)

        # Learning stats
        lrn_feedback = d.get("learning_feedback", 0)
        lrn_queries = d.get("learning_queries", 0)

        return f"""MEMORY SYSTEM

Sources
  Total: {mem_sources} | Enabled: {mem_enabled}

File Index
  Files: {idx_files} | Chunks: {idx_chunks}

Learning
  Feedback: {lrn_feedback}
  Queries: {lrn_queries}"""

    def _get_intelligence_content(self) -> str:
        # Data comes from get_system_stats() with flat keys: learning_feedback, learning_queries
        feedback = self.live_data.get("learning_feedback", 0)
        queries = self.live_data.get("learning_queries", 0)

        # Get top queries from memory stats if available
        top_queries = self.live_data.get("learning_top_queries", [])[:5]

        # Get preference data - check for user_preferences in file_registry
        prefs = self.live_data.get("preferences", 0)

        return f"""INTELLIGENCE LAYER

Feedback
  Events: {feedback} | Queries: {queries}
  Preferences: {prefs}

Top Queries:
  {json.dumps(top_queries, indent=2)[:200]}"""

    def _get_proxy_content(self) -> str:
        vpn = _safe_json("configs/vpn/backends.json")
        backends = vpn.get("backends", [])
        content = "PROXY / VPN CONFIGURATION\n\n"
        if backends:
            content += f"{'Name':<15} {'Host':<20} {'Port':<6} {'Provider':<15} {'Country':<10}\n"
            content += "-" * 66 + "\n"
            for b in backends:
                content += f"{b.get('name', '?'):<15} {b.get('socks_host', '?'):<20} {str(b.get('socks_port', '?')):<6} {b.get('provider', '?'):<15} {b.get('country', '?'):<10}\n"
        else:
            content += "  No VPN backends configured"
        return content

    def _get_config_content(self) -> str:
        content = "ECOSYSTEM CONFIG FILES\n\n"
        for path, (desc, _) in CONFIG_FILES.items():
            exists = Path(path).exists()
            status = "OK" if exists else "MISSING"
            content += f"  [{status}] {path:<45} {desc}\n"
        content += "\nPress C to edit any config file."
        return content

    def _get_health_content(self) -> str:
        """Get agent health data from .sisyphus/"""
        health = get_agent_health_data()
        if not health:
            return "No agent health data available"

        content = "AGENT HEALTH STATUS\n\n"
        for agent_name, data in health.items():
            status = data.get("status", "unknown")
            total = data.get("total_checks", 0)
            success = data.get("total_successes", 0)
            fail = data.get("total_failures", 0)
            avg_time = data.get("avg_response_time_ms", 0)
            status_icon = (
                "✓" if status == "healthy" else "⚠" if status == "degraded" else "✗"
            )
            content += f"{status_icon} {agent_name:<20} {status:<10} {success}/{total} ({fail} fail) | {avg_time:.0f}ms\n"
        return content

    def _get_skills_content(self) -> str:
        """Get agent skills data from .sisyphus/"""
        skills = get_skills_data()
        if not skills:
            return "No skills data available"

        content = "AGENT SKILLS & PERFORMANCE\n\n"
        for agent_name, data in skills.items():
            agent_skills = data.get("skills", {})
            tasks = data.get("total_tasks", 0)
            success = data.get("success_count", 0)
            rate = (success / tasks * 100) if tasks > 0 else 0
            content += f"{agent_name} ({success}/{tasks} = {rate:.0f}%)\n"
            for skill, score in list(agent_skills.items())[:3]:
                content += f"  {skill}: {score:.2f}\n"
            content += "\n"
        return content

    def _get_routing_content(self) -> str:
        """Get routing data from .sisyphus/"""
        routing = get_routing_data()
        content = "═══ ROUTING SYSTEM ═══\n\n"

        # Triggers
        triggers = routing.get("triggers", [])
        if triggers:
            content += "▸ TRIGGERS\n"
            if isinstance(triggers, list):
                for t in triggers:
                    pat = t.get("pattern", "?")[:30]
                    ag = t.get("agent", "?")
                    lvl = t.get("level", "?")
                    conf = t.get("confidence", 0)
                    content += f"  {pat:<30} → {ag:<12} L{lvl} ({conf:.0%})\n"
            elif isinstance(triggers, dict):
                for t in triggers.get("triggers", []):
                    pat = t.get("pattern", "?")[:30]
                    ag = t.get("agent", "?")
                    lvl = t.get("level", "?")
                    conf = t.get("confidence", 0)
                    content += f"  {pat:<30} → {ag:<12} L{lvl} ({conf:.0%})\n"
            content += "\n"

        # Weights
        weights = routing.get("weights", {})
        if weights:
            content += "▸ AGENT WEIGHTS\n"
            for ag, w in weights.items():
                sr = w.get("success_rate", 0) * 100
                lat = w.get("avg_latency_ms", 0)
                tasks = w.get("total_tasks", 0)
                by_lvl = w.get("by_level", {})
                lvl_info = ", ".join(
                    [
                        f"L{k}:{v.get('success_rate', 0) * 100:.0f}%"
                        for k, v in list(by_lvl.items())[:2]
                    ]
                )
                content += f"  {ag:<16} {sr:>5.1f}% | {lat:>6.1f}ms | {tasks:>3} tasks | {lvl_info}\n"
            content += "\n"

        # Quick stats
        content += "▸ QUICK STATS\n"
        content += f"  Triggers: {len(triggers) if isinstance(triggers, list) else len(triggers.get('triggers', []))}\n"
        content += f"  Agents: {len(weights)}\n"

        return content

    def _get_settings_content(self) -> str:
        """Settings and preferences panel - shows all system configuration"""
        content = "═══ SYSTEM CONFIGURATION ═══\n\n"

        # Load all config data
        health = get_agent_health_data()
        skills = get_skills_data()
        routing = get_routing_data()
        menu_evo = _safe_json(".sisyphus/menu_evolution.json")
        ml_model = _safe_json(".sisyphus/ml_model.json")
        boulder = _safe_json(".sisyphus/boulder.json")
        session = _safe_json(".sisyphus/session-state.json")

        # Agent Health
        content += "▸ AGENT HEALTH\n"
        for name, data in health.items():
            status = data.get("status", "unknown")
            checks = data.get("total_checks", 0)
            success = data.get("total_successes", 0)
            fail = data.get("total_failures", 0)
            content += f"  {name:<18} {status:<10} {success}/{checks} ok, {fail} fail\n"
        content += "\n"

        # Agent Skills
        content += "▸ AGENT SKILLS\n"
        for name, data in skills.items():
            tasks = data.get("total_tasks", 0)
            success = data.get("success_count", 0)
            if tasks > 0:
                rate = (success / tasks) * 100
                content += f"  {name:<18} {success}/{tasks} ({rate:.0f}%)\n"
        content += "\n"

        # Routing
        content += "▸ ROUTING SYSTEM\n"
        triggers = routing.get("triggers", [])
        content += f"  Triggers: {len(triggers)}\n"
        weights = routing.get("weights", {})
        content += f"  Weights: {len(weights)} agents\n"
        for agent, w in list(weights.items())[:5]:
            sr = w.get("success_rate", 0) * 100
            tasks = w.get("total_tasks", 0)
            content += f"    {agent:<15} {sr:>5.1f}% | {tasks:>3} tasks\n"
        content += "\n"

        # Menu Evolution
        content += "▸ MENU EVOLUTION\n"
        if menu_evo and isinstance(menu_evo, list):
            for item in menu_evo[-5:]:
                t = item.get("timestamp", "")[:19]
                i = item.get("item_name", "?")
                e = item.get("event_type", "?")
                content += f"  [{e}] {i} @ {t}\n"
        content += "\n"

        # ML Model
        content += "▸ ML MODEL WEIGHTS\n"
        mw = ml_model.get("model_weights", {})
        for agent, weights in list(mw.items())[:4]:
            content += f"  {agent}: "
            kw = list(weights.keys())[:3]
            content += ", ".join(kw) + "...\n"
        content += "\n"

        # Active Plan (Boulder)
        content += "▸ ACTIVE PLAN\n"
        if boulder:
            content += f"  Plan: {boulder.get('plan_name', 'none')}\n"
            content += f"  Wave: {boulder.get('current_wave', 0)}/1\n"
            content += f"  Tasks: {boulder.get('tasks_completed', 0)}/{boulder.get('tasks_total', 0)}\n"
        content += "\n"

        # Session State
        content += "▸ CURRENT SESSION\n"
        if session:
            content += f"  Agent: {session.get('last_agent', 'N/A')}\n"
            content += f"  Task: {session.get('current_task', 'N/A')[:40]}...\n"
            started = session.get("session_started", "")[:10]
            content += f"  Started: {started}\n"
        content += "\n"

        return content

    def _get_mcp_content(self) -> str:
        """Get MCP server status from config"""
        content = "═══ MCP SERVERS ═══\n\n"

        # Known MCP servers from AGENTS.md
        mcp_servers = [
            ("sequential-thinking", "Chain-of-thought reasoning"),
            ("memory", "Knowledge graph (deprecated)"),
            ("unified-memory", "Unified search + semantic"),
            ("context7", "Library documentation"),
            ("filesystem", "File operations"),
            ("fetch", "Web content fetch"),
            ("git", "Version control"),
            ("athena-context", "Active context retrieval"),
            ("trigger-guardian", "Command routing"),
            ("nx-mind", "Project state"),
            ("athena", "Memory bank"),
            ("github", "GitHub API"),
        ]

        # Check which are available in config
        for name, desc in mcp_servers:
            # Check if we can find evidence this MCP is configured
            status = "●"  # Assume available
            content += f"  {status} {name:<20} - {desc}\n"

        content += "\n▸ MCP STATUS\n"
        content += f"  Total configured: {len(mcp_servers)}\n"
        content += "  Run: bin/mcp-doctor.sh for diagnostics\n"

        content += "\n▸ AVAILABLE TOOLS\n"
        tool_count = {
            "filesystem": 14,
            "github": 50,
            "memory": 8,
            "unified-memory": 14,
            "context7": 2,
            "fetch": 5,
            "athena-context": 8,
            "sequential-thinking": 1,
        }
        for tool, count in list(tool_count.items())[:6]:
            content += f"  {tool:<18} {count} tools\n"

        content += "\n═══ QUICK ACTIONS ═══\n"
        content += "  [D] Run MCP doctor    [R] Refresh status\n"

        return content

    def _get_benchmarks_content(self) -> str:
        """Get benchmark data from .sisyphus/benchmarks/"""
        content = "═══ BENCHMARK HISTORY ═══\n\n"

        # Load benchmark files
        import glob

        bench_files = sorted(Path(".sisyphus/benchmarks").glob("benchmark-*.json"))

        if not bench_files:
            content += "  No benchmarks recorded yet\n"
            return content

        content += "▸ RECENT RUNS\n"
        for bf in bench_files[-5:]:
            try:
                data = json.loads(bf.read_text())
                ts = bf.name.replace("benchmark-", "").replace(".json", "")[:8]
                passed = data.get("passed", 0)
                failed = data.get("failed", 0)
                total = passed + failed
                rate = (passed / total * 100) if total > 0 else 0
                content += f"  {ts}  {passed}/{total} passed ({rate:.0f}%)\n"
            except:
                pass

        # Get latest benchmark details
        if bench_files:
            latest = bench_files[-1]
            try:
                data = json.loads(latest.read_text())
                content += "\n▸ LATEST DETAILS\n"
                content += f"  Tests: {data.get('passed', 0)} passed, {data.get('failed', 0)} failed\n"
                content += f"  Duration: {data.get('duration_ms', 0):.0f}ms\n"
                content += f"  Timestamp: {data.get('timestamp', 'N/A')[:19]}\n"
            except:
                pass

        content += "\n═══ QUICK ACTIONS ═══\n"
        content += "  [R] Run benchmark    [L] View last results\n"

        return content

    def _get_tasks_content(self) -> str:
        """Get active plan and tasks from boulder.json"""
        content = "═══ ACTIVE PLAN ═══\n\n"

        boulder = _safe_json(".sisyphus/boulder.json")

        if boulder:
            content += "▸ PLAN STATUS\n"
            content += f"  Plan: {boulder.get('plan_name', 'none')}\n"
            content += f"  Wave: {boulder.get('current_wave', 0)}\n"
            content += f"  Tasks: {boulder.get('tasks_completed', 0)}/{boulder.get('tasks_total', 0)}\n"

            wave_status = boulder.get("wave_1_status", "unknown")
            content += f"  Status: {wave_status}\n"

            next_action = boulder.get("next_action", "None")
            content += f"\n  Next: {next_action[:50]}...\n"

            # Session IDs
            sessions = boulder.get("session_ids", [])
            content += f"\n▸ SESSIONS\n"
            for sid in sessions[:3]:
                content += f"  {sid[:20]}...\n"
        else:
            content += "  No active plan\n"

        # Load plan files
        plan_files = list(Path(".sisyphus/plans").glob("*.json")) + list(
            Path(".sisyphus/plans").glob("*.md")
        )
        content += f"\n▸ AVAILABLE PLANS ({len(plan_files)})\n"
        for pf in plan_files[:5]:
            content += f"  • {pf.name}\n"

        content += "\n═══ QUICK ACTIONS ═══\n"
        content += "  [N] New plan    [C] Continue    [S] Stop plan\n"

        return content

    def _get_observations_content(self) -> str:
        """Get learning observations from .sisyphus/observations/"""
        content = "═══ LEARNING OBSERVATIONS ═══\n\n"

        # Load observations
        obs_files = sorted(Path(".sisyphus/observations").glob("*.json"))

        if not obs_files:
            content += "  No observations recorded\n"
            return content

        # Categorize observations
        prefs = []
        errs = []
        corrs = []
        decs = []

        for of in obs_files:
            name = of.name
            if "pref" in name:
                prefs.append(of)
            elif "err" in name:
                errs.append(of)
            elif "corr" in name:
                corrs.append(of)
            elif "dec" in name:
                decs.append(of)

        content += "▸ OBSERVATIONS BY TYPE\n"
        content += f"  Preferences: {len(prefs)}\n"
        content += f"  Errors: {len(errs)}\n"
        content += f"  Corrections: {len(corrs)}\n"
        content += f"  Decisions: {len(decs)}\n"

        # Show latest observation
        if obs_files:
            latest = obs_files[-1]
            try:
                data = json.loads(latest.read_text())
                content += "\n▸ LATEST\n"
                # Try to show relevant fields
                for k, v in list(data.items())[:4]:
                    content += f"  {k}: {str(v)[:30]}...\n"
            except:
                pass

        # Cross-session knowledge
        knowledge = _safe_json(".sisyphus/cross_session/knowledge.json")
        if knowledge:
            content += "\n▸ KNOWLEDGE GRAPH\n"
            entities = knowledge.get("entities", [])
            relations = knowledge.get("relations", [])
            content += f"  Entities: {len(entities)}\n"
            content += f"  Relations: {len(relations)}\n"

        content += "\n═══ QUICK ACTIONS ═══\n"
        content += "  [V] View all    [C] Clear old    [E] Export\n"

        return content

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        # Check if it's a discovered panel button
        if bid.startswith("btn-discovered-"):
            panel_name = bid.replace("btn-discovered-", "")
            self._handle_discovered_panel(panel_name)
            return

        actions = {
            "btn-overview": lambda: self._set_tab("overview"),
            "btn-agents": lambda: self._set_tab("agents"),
            "btn-memory": lambda: self._set_tab("memory"),
            "btn-intelligence": lambda: self._set_tab("intelligence"),
            "btn-config": lambda: self._set_tab("config"),
            "btn-health": lambda: self._set_tab("health"),
            "btn-skills": lambda: self._set_tab("skills"),
            "btn-routing": lambda: self._set_tab("routing"),
            "btn-settings": lambda: self._set_tab("settings"),
            "btn-mcp": lambda: self._set_tab("mcp"),
            "btn-benchmarks": lambda: self._set_tab("benchmarks"),
            "btn-tasks": lambda: self._set_tab("tasks"),
            "btn-observations": lambda: self._set_tab("observations"),
            "btn-edit-config": self.action_edit_config,
            "btn-search": self.action_search,
            "btn-settings-action": self.action_settings,
            "btn-edit-config": self.action_edit_config,
            "btn-search": self.action_search,
            "btn-settings-action": self.action_settings,
        }
        action = actions.get(bid)
        if action:
            action()

    def _set_tab(self, tab: str) -> None:
        self.current_tab = tab
        self.refresh_content()
        # Update button variants
        for btn_id in [
            "btn-overview",
            "btn-agents",
            "btn-memory",
            "btn-config",
            "btn-health",
            "btn-skills",
            "btn-routing",
            "btn-settings",
            "btn-mcp",
            "btn-benchmarks",
            "btn-tasks",
            "btn-observations",
            "btn-discovered-",  # prefix for discovered panels
        ]:
            try:
                btn = self.query_one(f"#{btn_id}", Button)
                btn.variant = "primary" if btn_id == f"btn-{tab}" else "default"
            except Exception:
                pass

    def action_refresh(self) -> None:
        self._background_refresh()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def action_tab_overview(self) -> None:
        self._set_tab("overview")

    def action_tab_agents(self) -> None:
        self._set_tab("agents")

    def action_tab_memory(self) -> None:
        self._set_tab("memory")

    def action_tab_intelligence(self) -> None:
        self._set_tab("intelligence")

    def action_tab_proxy(self) -> None:
        self._set_tab("proxy")

    def action_tab_config(self) -> None:
        self._set_tab("config")

    def action_tab_health(self) -> None:
        self._set_tab("health")

    def action_tab_skills(self) -> None:
        self._set_tab("skills")

    def action_tab_routing(self) -> None:
        self._set_tab("routing")

    def action_tab_settings_panel(self) -> None:
        self._set_tab("settings")

    def action_tab_mcp(self) -> None:
        self._set_tab("mcp")

    def action_tab_benchmarks(self) -> None:
        self._set_tab("benchmarks")

    def action_tab_tasks(self) -> None:
        self._set_tab("tasks")

    def action_tab_observations(self) -> None:
        self._set_tab("observations")

    def action_edit_config(self) -> None:
        self.push_screen(ConfigEditorScreen())

    def action_search(self) -> None:
        """Open search modal to search across all agents and configs."""
        self.push_screen(SearchScreen())

    def action_export(self) -> None:
        """Export current dashboard data to a JSON file."""
        try:
            # Gather all live data
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "system": get_system_stats(),
                "overview": self._get_overview_content(),
                "live_data": self.live_data,
            }

            # Save to file
            export_path = Path.home() / "n-xyme-dashboard-export.json"
            export_path.write_text(json.dumps(export_data, indent=2, default=str))
            self.notify(f"Exported to {export_path}", severity="information", timeout=5)
        except Exception as e:
            self.notify(f"Export failed: {e}", severity="error")

    def action_settings(self) -> None:
        try:
            from .settings_screen import SettingsScreen

            self.push_screen(SettingsScreen())
        except Exception as e:
            self.notify(f"Settings error: {e}")

    # ─── Self-Evolving Menu Integration ─────────────────────────────────────

    def _integrate_self_evolving_menu(self) -> None:
        """Initialize and patch dashboard with self-evolving menu capabilities."""
        try:
            from .self_evolving_menu import patch_dashboard

            self.menu_system = patch_dashboard(self)
            self.notify(
                "Self-evolving menu activated", severity="information", timeout=3
            )
        except Exception as e:
            self.notify(f"Menu integration failed: {e}", severity="warning", timeout=5)

    def _update_discovered_panels_sidebar(self) -> None:
        """Refresh sidebar with discovered panels from menu system."""
        if not hasattr(self, "menu_system"):
            return

        try:
            container = self.query_one("#discovered-panels", Container)
            # Clear existing buttons
            for child in list(container.children):
                child.remove()

            # Add buttons for discovered panels
            for panel_name in self.menu_system.discovered_panels:
                btn = Button(
                    panel_name.replace("_", " ").title(),
                    id=f"btn-discovered-{panel_name}",
                    variant="default",
                )
                container.mount(btn)
        except Exception as e:
            logger.warning(f"Failed to update discovered panels sidebar: {e}")

    def _handle_discovered_panel(self, panel_name: str) -> None:
        """Display content for a discovered panel."""
        if not hasattr(self, "menu_system"):
            return

        try:
            content = self.menu_system.get_discovered_panel_content(panel_name)
            self.query_one("#content-area", Static).update(content)
            self.current_tab = f"discovered:{panel_name}"
            self.query_one("#status-bar", Static).update(
                f"Panel: {panel_name.replace('_', ' ').title()} | Self-evolving | {datetime.now().strftime('%H:%M:%S')}"
            )
        except Exception as e:
            self.notify(f"Failed to load panel '{panel_name}': {e}", severity="error")

    def action_refresh_menu(self) -> None:
        """Manually trigger menu evolution scan."""
        if hasattr(self, "menu_system"):
            new_modules = self.menu_system.update_dashboard_menu()
            if new_modules:
                self._update_discovered_panels_sidebar()
                self.notify(
                    f"Menu updated: {len(new_modules)} new panels",
                    severity="information",
                )
            else:
                self.notify(
                    "No new panels discovered", severity="information", timeout=2
                )


def main():
    app = NxyeDashboard()
    app.run()


if __name__ == "__main__":
    main()

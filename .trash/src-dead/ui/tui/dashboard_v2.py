#!/usr/bin/env python3
"""N-Xyme MIND Dashboard v2.0 — ADHD-friendly, complete frontend."""

import json
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

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
        from src.memory.mcp_server import get_memory_stats as _gs

        m = _gs()
        stats["memory_sources"] = m.get("total_sources", 0)
        stats["memory_enabled"] = m.get("enabled_count", 0)
    except Exception:
        stats["memory_sources"] = 0
        stats["memory_enabled"] = 0
    try:
        from src.memory.drive_embedder import get_indexed_count as _gc

        i = _gc()
        stats["indexed_files"] = i.get("total_files", 0)
        stats["indexed_chunks"] = i.get("total_chunks", 0)
    except Exception:
        stats["indexed_files"] = 0
        stats["indexed_chunks"] = 0
    try:
        from src.memory.memory_router import get_router

        stats["router_backends"] = len(get_router().backends)
    except Exception:
        stats["router_backends"] = 0
    try:
        from src.orchestration.agent_card_registry import get_agent_registry

        stats["orchestration_agents"] = len(get_agent_registry().get_all_agents())
    except Exception:
        stats["orchestration_agents"] = 0
    try:
        from src.memory.mcp_server import get_learning_stats as _gs

        l = _gs()
        fb = l.get("feedback_stats", {})
        stats["learning_feedback"] = fb.get("total_feedback", 0)
        stats["learning_queries"] = fb.get("unique_queries", 0)
    except Exception:
        stats["learning_feedback"] = 0
        stats["learning_queries"] = 0
    try:
        p = Path(".sisyphus/outcomes.jsonl")
        stats["outcomes"] = len(p.read_text().splitlines()) if p.exists() else 0
    except Exception:
        stats["outcomes"] = 0
    return stats


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
        Binding("5", "tab_proxy", "Proxy/VPN", show=True),
        Binding("6", "tab_config", "Config", show=True),
        Binding("c", "edit_config", "Edit Config", show=True),
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
                yield Button("5 Proxy/VPN", id="btn-proxy")
                yield Button("6 Config", id="btn-config")
                yield Label("Actions", classes="section-title")
                yield Button("Edit Config (C)", id="btn-edit-config")
                yield Button("Search (S)", id="btn-search")
                yield Button("Settings (X)", id="btn-settings")
            with ScrollableContainer(id="content"):
                yield Static("Loading...", id="content-area")
        yield Static(
            "Panel: Overview | 1-6 panels, C edit config, S search, X settings, Q quit, D dark mode",
            id="status-bar",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.live_data = self._get_loading_state()
        self.refresh_content()
        self._background_refresh()
        self.set_interval(10.0, self._background_refresh)

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
            f"Panel: {self.current_tab.capitalize()} | {datetime.now().strftime('%H:%M:%S')} | 1-6 panels, C edit config, S search, X settings, Q quit, D dark mode"
        )

    def _get_content_for_tab(self, tab: str) -> str:
        tabs = {
            "overview": self._get_overview_content,
            "agents": self._get_agents_content,
            "memory": self._get_memory_content,
            "intelligence": self._get_intelligence_content,
            "proxy": self._get_proxy_content,
            "config": self._get_config_content,
        }
        return tabs.get(tab, lambda: "Unknown tab")()

    def _get_overview_content(self) -> str:
        d = self.live_data
        daemon_ok = d.get("daemon", {}).get("running", False)
        ollama_ok = d.get("ollama", {}).get("running", False)
        return f"""SYSTEM OVERVIEW

Core Services
  Daemon: {"Running" if daemon_ok else "Stopped"} | PID: {d.get("daemon", {}).get("pid", "N/A")}
  Ollama: {"Running" if ollama_ok else "Stopped"} | http://localhost:11434

Data Index
  Files: {d.get("indexed", {}).get("total_files", 0)} | Chunks: {d.get("indexed", {}).get("total_chunks", 0)}

System Components
  Memory: {d.get("memory", {}).get("total_sources", 0)} sources | {d.get("memory", {}).get("enabled_count", 0)} enabled
  Router: {d.get("router", {}).get("backends", 0)} backends
  Agents: {d.get("orchestration", {}).get("agents", 0)}
  Sessions: {d.get("sessions", {}).get("total", 0)}
  Outcomes: {d.get("performance", {}).get("outcomes", 0)}

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
        d = self.live_data
        mem = d.get("memory", {})
        idx = d.get("indexed", {})
        return f"""MEMORY SYSTEM

Sources
  Total: {mem.get("total_sources", 0)} | Enabled: {mem.get("enabled_count", 0)}

File Index
  Files: {idx.get("total_files", 0)} | Chunks: {idx.get("total_chunks", 0)}

Learning
  Feedback: {d.get("learning", {}).get("feedback_stats", {}).get("total_feedback", 0)}
  Queries: {d.get("learning", {}).get("feedback_stats", {}).get("unique_queries", 0)}"""

    def _get_intelligence_content(self) -> str:
        learn = self.live_data.get("learning", {})
        fb = learn.get("feedback_stats", {})
        pref = learn.get("preference_stats", {})
        return f"""INTELLIGENCE LAYER

Feedback
  Events: {fb.get("total_feedback", 0)} | Queries: {fb.get("unique_queries", 0)}
  Preferences: {len(pref)}

Top Queries:
  {json.dumps(fb.get("top_queries", [])[:5], indent=2)[:200]}"""

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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        actions = {
            "btn-overview": lambda: self._set_tab("overview"),
            "btn-agents": lambda: self._set_tab("agents"),
            "btn-memory": lambda: self._set_tab("memory"),
            "btn-intelligence": lambda: self._set_tab("intelligence"),
            "btn-proxy": lambda: self._set_tab("proxy"),
            "btn-config": lambda: self._set_tab("config"),
            "btn-edit-config": self.action_edit_config,
            "btn-search": self.action_search,
            "btn-settings": self.action_settings,
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
            "btn-intelligence",
            "btn-proxy",
            "btn-config",
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

    def action_edit_config(self) -> None:
        self.push_screen(ConfigEditorScreen())

    def action_search(self) -> None:
        self.notify("Search: use command input at bottom")

    def action_settings(self) -> None:
        try:
            from src.ui.tui.settings_screen import SettingsScreen

            self.push_screen(SettingsScreen())
        except Exception as e:
            self.notify(f"Settings error: {e}")


def main():
    app = NxyeDashboard()
    app.run()


if __name__ == "__main__":
    main()

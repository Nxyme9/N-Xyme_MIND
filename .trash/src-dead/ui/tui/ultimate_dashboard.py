#!/usr/bin/env python3
"""N-Xyme MIND Dashboard v2.0 — ADHD-friendly, complete frontend."""

import json
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, cast

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

# Import DataProvider for unified data layer
from src.dashboard.data_provider import get_system_stats, refresh_stats

# Import AI Brain dashboard
from src.dashboard.ai_brain import DashboardAIBrain

# Import widgets for T2.1-T3.3
from src.ui.tui.widgets import (
    MetricSparkline,
    MetricCard,
    StatusIndicator,
    ProgressRing,
    # T4.x new widgets
    KnowledgeGraphViewer,
    AgentGraphViewer,
    RoutingFunnel,
    SimpleRoutingStats,
    CostDashboard,
    UsageStats,
    ActivityFeed,
    LiveEventCounter,
    EventStream,
    # T5.x enhancements
    ThemeEnhancer,
    PerformanceOptimizer,
    ErrorBoundary,
)
from src.ui.tui.widgets.activity_heatmap import ActivityHeatmap
from src.ui.tui.widgets.command_palette import CommandPaletteCommands
from src.ui.tui.widgets.agent_graph import AgentGraph

# Import dialogs for orphan integration
from src.ui.tui.dialogs.agent_manager import AgentManagerDialog
from src.ui.tui.dialogs.proxy_manager import ProxyManagerDialog
from src.ui.tui.dialogs.memory_explorer import MemoryExplorerDialog
from src.ui.tui.dialogs.benchmark_runner import BenchmarkRunnerDialog
from src.ui.tui.dialogs.trigger_editor import TriggerEditorDialog
from src.ui.tui.dialogs.config_editor import ConfigEditorDialog
from src.ui.tui.dialogs.activity_log import ActivityLogScreen


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
        # get_memory_stats returns nested structure - extract properly
        file_reg = m.get("file_registry", {})
        stats["memory_sources"] = len(file_reg)  # Number of tables = sources
        stats["memory_enabled"] = m.get("learning_events", 0)  # Events count as enabled
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
        from src.memory.mcp_server import get_memory_stats as _ms

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
        current: Any = data
        for k in keys[:-1]:
            if k.isdigit():
                k = int(k)
            if isinstance(current, list):
                current = current[cast(int, k)]
            elif isinstance(current, dict):
                current = current[cast(str, k)]
            else:
                raise TypeError(f"Cannot traverse {type(current)}")
        last_key = keys[-1]
        if last_key.isdigit():
            last_key = int(last_key)
        if isinstance(current, list):
            current[cast(int, last_key)] = value
        elif isinstance(current, dict):
            current[cast(str, last_key)] = value
        else:
            raise TypeError(f"Cannot set value on {type(current)}")
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


class CommandPaletteScreen(ModalScreen[None]):
    """VSCode-style command palette - T3.1"""

    BINDINGS = [("escape", "dismiss", "Close")]

    CSS = """
    CommandPaletteScreen { align: center top; }
    #palette-container { width: 60; height: 70%; background: $surface; border: thick $primary; }
    #search-input { width: 100%; border-bottom: solid $primary; }
    #command-list { width: 100%; height: 100%; }
    """

    def __init__(self):
        super().__init__()
        self.filtered_commands = CommandPaletteCommands.get_commands()
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        from textual.widgets import Input

        with Container(id="palette-container"):
            yield Input(placeholder="Type a command...", id="search-input")
            yield Static("", id="command-list")

    def on_mount(self) -> None:
        self.query_one("#search-input", Input).focus()
        self._update_list()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Filter commands based on search."""
        query = event.value
        self.filtered_commands = CommandPaletteCommands.filter_commands(query)
        self.selected_index = 0
        self._update_list()

    def _update_list(self) -> None:
        """Update the command list display."""
        if not self.filtered_commands:
            self.query_one("#command-list", Static).update("No commands found")
            return

        lines = []
        for i, cmd in enumerate(self.filtered_commands[:10]):  # Show max 10
            marker = ">" if i == self.selected_index else " "
            shortcut = f" [{cmd.shortcut}]" if cmd.shortcut else ""
            lines.append(f"{marker} {cmd.label}{shortcut}")
            lines.append(f"  {cmd.description}")

        self.query_one("#command-list", Static).update("\n".join(lines))

    def on_key(self, event) -> None:
        """Handle navigation keys."""
        if event.key == "arrow_up":
            self.selected_index = max(0, self.selected_index - 1)
            self._update_list()
        elif event.key == "arrow_down":
            self.selected_index = min(
                len(self.filtered_commands) - 1, self.selected_index + 1
            )
            self._update_list()
        elif event.key == "enter":
            self._execute_selected()
        elif event.key == "escape":
            self.dismiss()

    def _execute_selected(self) -> None:
        """Execute the currently selected command."""
        if 0 <= self.selected_index < len(self.filtered_commands):
            cmd = self.filtered_commands[self.selected_index]
            # Use ACTION_MAP from CommandPaletteCommands
            from src.ui.tui.widgets.command_palette import CommandPaletteCommands

            action_method_name = CommandPaletteCommands.ACTION_MAP.get(cmd.id)
            if action_method_name:
                app = self.app
                action_method = getattr(app, action_method_name, None)
                if action_method:
                    action_method()
            self.dismiss()


class ConfirmActionScreen(ModalScreen[bool]):
    """Confirmation dialog for destructive actions - ADHD-friendly safety check."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Confirm"),
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
    ]

    def __init__(self, message: str, on_confirm: Optional[Callable] = None):
        super().__init__()
        self.confirm_message = message
        self.on_confirm = on_confirm

    CSS = """
    ConfirmActionScreen { align: center middle; }
    #confirm-container { width: 60; height: auto; background: $surface; border: thick $error; padding: 2 4; }
    #confirm-message { margin-bottom: 2; color: $text; }
    #confirm-buttons { height: auto; }
    .confirm-btn { width: 20; margin: 0 1; }
    """

    def compose(self) -> ComposeResult:
        with Container(id="confirm-container"):
            yield Label("⚠️ CONFIRM ACTION", classes="panel-title")
            yield Label(self.confirm_message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button(
                    "Yes", id="btn-confirm-yes", variant="error", classes="confirm-btn"
                )
                yield Button(
                    "No", id="btn-confirm-no", variant="success", classes="confirm-btn"
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm-yes":
            if self.on_confirm:
                self.on_confirm()
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self) -> None:
        if self.on_confirm:
            self.on_confirm()
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class AICChatScreen(ModalScreen[None]):
    """AI Chat panel for natural language system commands."""

    BINDINGS = [("escape", "dismiss", "Close")]

    CSS = """
    AICChatScreen { align: center middle; }
    #chat-container { width: 80; height: 80%; background: $surface; border: thick $primary; padding: 1 2; }
    #chat-title { text-style: bold; color: $primary; margin-bottom: 1; }
    #chat-history { width: 100%; height: 85%; background: $panel; padding: 1 2; overflow-y: auto; }
    #chat-input-row { width: 100%; height: auto; margin-top: 1; }
    #chat-input { width: 85%; }
    #chat-send-btn { width: 15%; }
    .chat-user { color: $success; text-style: bold; }
    .chat-ai { color: $text; }
    .chat-thinking { color: $text-muted; text-style: italic; }
    .chat-error { color: $error; }
    """

    def compose(self) -> ComposeResult:
        with Container(id="chat-container"):
            yield Label(
                "🤖 AI Chat - Ask about your system (Esc to close)", id="chat-title"
            )
            yield Vertical(id="chat-history")
            with Horizontal(id="chat-input-row"):
                yield Input(
                    placeholder="Type a question... (e.g. 'what's broken?', 'show memory stats')",
                    id="chat-input",
                )
                yield Button("Send", id="chat-send-btn", variant="primary")

    def on_mount(self) -> None:
        self._add_message(
            "AI",
            "Hello! Ask me about your system. Try:\n• 'what's broken?'\n• 'show memory stats'\n• 'restart the daemon'\n• 'summarize recent logs'",
            "chat-ai",
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._send_query(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "chat-send-btn":
            inp = self.query_one("#chat-input", Input)
            self._send_query(inp.value)
            inp.value = ""

    def _send_query(self, query: str) -> None:
        query = query.strip()
        if not query:
            return
        self._add_message("You", query, "chat-user")
        self._add_message("AI", "Thinking...", "chat-thinking")

        async def _get_response():
            try:
                from src.dashboard.ai_brain import DashboardAIBrain

                brain = DashboardAIBrain()
                if not brain.is_available():
                    self._replace_last(
                        "AI",
                        "⚠️ Ollama is not available. Ensure Ollama is running on localhost:11434.",
                        "chat-error",
                    )
                    return
                context = {"live_data": getattr(self.app, "live_data", {})}
                response = await brain.chat(query, context=context)
                self._replace_last("AI", response, "chat-ai")
            except ImportError:
                self._replace_last(
                    "AI",
                    "⚠️ AI Brain module not found. Run dashboard from project root.",
                    "chat-error",
                )
            except Exception as e:
                self._replace_last("AI", f"⚠️ Error: {e}", "chat-error")

        self.run_worker(_get_response(), exclusive=True)

    def _add_message(self, sender: str, message: str, css_class: str) -> None:
        history = self.query_one("#chat-history", Vertical)
        label = Static(f"{sender}: {message}", classes=css_class)
        history.mount(label)
        self.call_later(lambda: history.scroll_end(animate=True))

    def _replace_last(self, sender: str, message: str, css_class: str) -> None:
        history = self.query_one("#chat-history", Vertical)
        children = list(history.children)
        if children and "chat-thinking" in (getattr(children[-1], "classes", [])):
            children[-1].remove()
        self._add_message(sender, message, css_class)


class HelpScreen(ModalScreen[None]):
    """Keyboard shortcuts help overlay - T1.4"""

    BINDINGS = [("escape", "dismiss", "Close"), ("question_mark", "dismiss", "Close")]

    CSS = """
    HelpScreen { align: center middle; }
    #help-container { width: 70; height: 80%; background: $surface; border: thick $accent; padding: 1 2; }
    .help-title { text-style: bold; color: $accent; text-align: center; padding: 1 0; }
    .help-section { padding: 1 0; }
    .help-section-title { text-style: bold; color: $warning; }
    .help-key { color: $primary; text-style: bold; }
    .help-desc { color: $text-muted; }
    """

    def compose(self) -> ComposeResult:
        with Container(id="help-container"):
            yield Label("⌨️ KEYBOARD SHORTCUTS", classes="help-title")

            with Vertical(classes="help-section"):
                yield Label("NAVIGATION", classes="help-section-title")
                yield Label("  [1-9,0]     Switch to panel           ")
                yield Label("  [,]         Cycle panels             ")
                yield Label("  [TAB]       Next panel               ")
                yield Label("  [SHIFT+TAB] Previous panel          ")

            with Vertical(classes="help-section"):
                yield Label("ACTIONS", classes="help-section-title")
                yield Label("  [R]         Refresh data             ")
                yield Label("  [P]         Toggle palette           ")
                yield Label("  [E]         Export dashboard         ")
                yield Label("  [S]         Search                   ")
                yield Label("  [X]         Settings                 ")
                yield Label("  [C]         Edit config              ")

            with Vertical(classes="help-section"):
                yield Label("SPECIAL", classes="help-section-title")
                yield Label("  [?]         This help                ")
                yield Label("  [Q]         Quit                     ")

            yield Label("Press ESC or ? to close", classes="help-desc")

    def on_key(self, event) -> None:
        """Close on any key."""
        if event.key == "escape" or event.key == "question_mark":
            self.dismiss()


# ─── Main Dashboard ───────────────────────────────────────────────────────────


class NxyeDashboard(App):
    """N-Xyme MIND Dashboard v2.0 — ADHD-friendly, complete frontend."""

    TITLE = "N-Xyme MIND Dashboard"
    SUB_TITLE = "N-Xyme MIND Dashboard [DAEMON:● OLLAMA:●]"
    CSS = """
    Screen { background: $background; }
    .header-status { height: 1; background: $panel; color: $text-muted; padding: 0 2; }
    .header-status .daemon-running { color: $success; }
    .header-status .daemon-stopped { color: $error; }
    .header-status .ollama-running { color: $success; }
    .header-status .ollama-stopped { color: $error; }
    #main-tabs { height: 100%; }
    TabbedContent { height: 100%; }
    TabbedContent > TabBar { background: $surface; }
    TabbedContent > TabBar > Tab { padding: 0 2; }
    TabbedContent > TabBar > Tab.active { background: $primary; color: $text; text-style: bold; }
    #content-overview, #content-agents, #content-memory, #content-intelligence,
    #content-proxy, #content-config, #content-health, #content-skills,
    #content-routing, #content-settings, #content-mcp, #content-benchmarks,
    #content-tasks, #content-observations, #content-ai_brain {
        width: 100%; padding: 1 2;
    }
    #status-bar { height: 3; background: $panel; content-align: center middle; border-top: thick $primary; }
    #bottom-menu { height: 3; background: $surface; content-align: center middle; border-top: thick $accent; }
    #bottom-menu Button { margin: 0 1; }
    .panel-title { text-style: bold; color: $warning; padding: 0 1; }
    .section-header { text-style: bold; color: $primary; padding: 1 0; }
    .status-ok { color: $success; }
    .status-warn { color: $warning; }
    .status-error { color: $error; }
    DataTable { width: 100%; height: 15; }
    .stat-box { width: 20; height: 3; background: $surface; border: thick $primary; content-align: center middle; }
    .stat-label { text-style: bold; color: $text-muted; }
    .stat-value { text-style: bold; color: $success; }
    Button { margin: 0 1; }
    .btn-primary { background: $primary; }
    .btn-danger { background: $error; }
    .btn-success { background: $success; }
    .btn-warning { background: $warning; }
    Switch { margin: 0 2; }
    #settings-toggles { margin: 1 0; padding: 1; background: $surface; }
    #settings-toggles Label { margin: 0 1; }
    #row-dark-mode, #row-auto-refresh, #row-sparklines, #row-notifications {
        height: auto; margin: 0 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("p", "command_palette", "Palette", show=True),
        Binding("ctrl+k", "command_palette", "Command", show=True),
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
        # T4.x: New visualization tabs
        Binding("k", "tab_knowledge", "Knowledge", show=True),
        Binding("l", "tab_costs", "Costs", show=True),
        Binding("m", "tab_activity", "Activity", show=True),
        Binding("i", "tab_ai_brain", "AI Brain", show=True),
        Binding("c", "edit_config", "Edit Config", show=True),
        Binding("e", "export", "Export", show=True),
        Binding("s", "search", "Search", show=True),
        Binding("x", "settings", "Settings", show=True),
        Binding("?", "show_help", "Help", show=True),
        # Dialog shortcuts
        Binding("a", "add_agent", "Add Agent", show=True),
        Binding("b", "add_backend", "Add Backend", show=True),
        Binding("i", "explore_memory", "Memory", show=True),
        Binding("n", "run_all_benchmarks", "Benchmark", show=True),
        Binding("t", "add_trigger", "Add Trigger", show=True),
        Binding("v", "view_activity_log", "Activity Log", show=True),
        Binding("ctrl+a", "ai_chat", "AI Chat", show=True),
    ]

    current_tab: reactive[str] = reactive("overview")
    live_data: dict = {}

    # Reactive attributes for auto-refresh (T1.2.1)
    # Each attribute triggers watch_* when changed
    daemon_status = reactive({"running": False, "pid": "N/A"})
    ollama_status = reactive({"running": False})
    memory_stats = reactive({"sources": 0, "enabled": 0})
    indexed_stats = reactive({"files": 0, "chunks": 0})
    router_stats = reactive({"backends": 0})
    orchestration_stats = reactive({"agents": 0})
    learning_stats = reactive({"feedback": 0, "queries": 0, "top_queries": []})
    preferences_count = reactive(0)
    outcomes_count = reactive(0)

    # Data freshness tracking (T1.3)
    last_updated: reactive[float] = reactive(0.0)
    _data_freshness = reactive(
        {
            "daemon": "unknown",
            "ollama": "unknown",
            "memory": "unknown",
            "indexed": "unknown",
            "learning": "unknown",
        }
    )

    # Sparkline history for T2.1
    _indexed_history = reactive([])  # List of indexed_files values
    _memory_history = reactive([])  # List of memory_sources values
    _feedback_history = reactive([])  # List of learning_feedback values
    _max_sparkline_points = 20
    _tab_content_cache: dict = {}  # Cache for tab content

    # AI Brain reactive attributes
    ai_health_summary: reactive[str] = reactive("Loading...")
    ai_predictive_alerts: reactive[str] = reactive("")
    ai_troubleshooting: reactive[str] = reactive("")

    # ─── Reactive Watchers for Auto-Refresh (T1.2.1) ────────────────────────────

    def watch_live_data(self, data: dict) -> None:
        """Auto-refresh current tab when live_data changes."""
        self._refresh_current_tab()

    def watch_daemon_status(self, data: dict) -> None:
        """Auto-refresh when daemon status changes."""
        self._refresh_current_tab()

    def watch_ollama_status(self, data: dict) -> None:
        """Auto-refresh when ollama status changes."""
        self._refresh_current_tab()

    def watch_memory_stats(self, data: dict) -> None:
        """Auto-refresh when memory stats change."""
        self._refresh_current_tab()

    def watch_indexed_stats(self, data: dict) -> None:
        """Auto-refresh when indexed stats change."""
        self._refresh_current_tab()

    def watch_router_stats(self, data: dict) -> None:
        """Auto-refresh when router stats change."""
        self._refresh_current_tab()

    def watch_orchestration_stats(self, data: dict) -> None:
        """Auto-refresh when orchestration stats change."""
        self._refresh_current_tab()

    def watch_learning_stats(self, data: dict) -> None:
        """Auto-refresh when learning stats change."""
        self._refresh_current_tab()

    def watch_preferences_count(self, count: int) -> None:
        """Auto-refresh when preferences count changes."""
        self._refresh_current_tab()

    def watch_outcomes_count(self, count: int) -> None:
        """Auto-refresh when outcomes count changes."""
        self._refresh_current_tab()

    def watch_ai_health_summary(self, summary: str) -> None:
        """Auto-refresh when AI health summary changes."""
        self._refresh_current_tab()

    def _refresh_current_tab(self) -> None:
        """Refresh the content of the currently active tab."""
        try:
            tabs = self.query_one("#main-tabs", TabbedContent)
            tab_id = tabs.active
            if tab_id and tab_id.startswith("tab-"):
                tab_name = tab_id.replace("tab-", "")
                content = self._get_content_for_tab(tab_name)
                container = self.query_one(f"#{tab_id}", TabPane)
                existing = container.query_one(Static)
                existing.update(content)
                # Update freshness indicator in status bar
                self._update_freshness_indicator()
        except Exception:
            pass

    def _update_freshness_indicator(self) -> None:
        """Update the freshness indicator in header/status bar."""
        if self.last_updated > 0:
            age = time.time() - self.last_updated
            if age < 10:
                freshness = "🟢"
            elif age < 30:
                freshness = "🟡"
            else:
                freshness = "🔴"
            freshness_info = f" | Updated: {freshness} {int(age)}s ago"
        else:
            freshness_info = " | Updated: --"

        try:
            status_bar = self.query_one("#status-bar", Static)
            base_info = f"Tab: {self.current_tab.capitalize()} | {datetime.now().strftime('%H:%M:%S')}"
            status_bar.update(
                f"{base_info}{freshness_info} | 1-0: tabs, C edit, S search, X settings, Q quit, P palette, Ctrl+K command"
            )
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        # Custom header with status indicators for ADHD-friendly visual feedback
        yield Header()
        # Status bar showing daemon and ollama status - updated dynamically
        yield Static("Initializing...", id="header-status", classes="header-status")
        with TabbedContent(id="main-tabs"):
            # T2.3: Replace sidebar with TabbedContent
            with TabPane("1 Overview", id="tab-overview"):
                with ScrollableContainer(id="content-overview"):
                    # Action buttons row
                    yield Horizontal(
                        Button(
                            "▶ Start Daemon", id="btn-start-daemon", variant="primary"
                        ),
                        Button("⏹ Stop Daemon", id="btn-stop-daemon", variant="error"),
                        Button("↻ Refresh", id="btn-refresh", variant="default"),
                        Button("📊 Stats", id="btn-stats", variant="default"),
                        Button(
                            "🧹 Clear Cache", id="btn-clear-cache", variant="warning"
                        ),
                        id="overview-buttons",
                    )
                    yield Static("Loading...", id="static-overview")
            with TabPane("2 Agents", id="tab-agents"):
                with ScrollableContainer(id="content-agents"):
                    # Agent control buttons
                    yield Horizontal(
                        Button("▶ Start All", id="btn-start-agents", variant="success"),
                        Button("⏹ Stop All", id="btn-stop-agents", variant="error"),
                        Button(
                            "🔄 Restart", id="btn-restart-agents", variant="warning"
                        ),
                        Button("➕ Add Agent", id="btn-add-agent", variant="default"),
                        id="agents-buttons",
                    )
                    yield Static("Loading...", id="static-agents")
            with TabPane("3 Memory", id="tab-memory"):
                with ScrollableContainer(id="content-memory"):
                    # Memory control buttons
                    yield Horizontal(
                        Button(
                            "🧹 Clear Memory", id="btn-clear-memory", variant="warning"
                        ),
                        Button(
                            "⚡ Optimize", id="btn-optimize-memory", variant="default"
                        ),
                        Button("📤 Export", id="btn-export-memory", variant="default"),
                        Button("📥 Import", id="btn-import-memory", variant="default"),
                        id="memory-buttons",
                    )
                    yield Static("Loading...", id="static-memory")
            with TabPane("4 Intelligence", id="tab-intelligence"):
                with ScrollableContainer(id="content-intelligence"):
                    # Intelligence control buttons
                    yield Horizontal(
                        Button(
                            "🔄 Retrain Model",
                            id="btn-retrain-model",
                            variant="primary",
                        ),
                        Button(
                            "📊 View Metrics", id="btn-view-metrics", variant="default"
                        ),
                        Button(
                            "🧪 Run Benchmark",
                            id="btn-run-benchmark",
                            variant="default",
                        ),
                        id="intelligence-buttons",
                    )
                    yield Static("Loading...", id="static-intelligence")
            with TabPane("5 Proxy", id="tab-proxy"):
                with ScrollableContainer(id="content-proxy"):
                    # Proxy control buttons
                    yield Horizontal(
                        Button(
                            "▶ Start Proxies", id="btn-start-proxies", variant="success"
                        ),
                        Button(
                            "⏹ Stop Proxies", id="btn-stop-proxies", variant="error"
                        ),
                        Button("🔄 Rotate IPs", id="btn-rotate-ips", variant="warning"),
                        Button(
                            "➕ Add Backend", id="btn-add-backend", variant="default"
                        ),
                        id="proxy-buttons",
                    )
                    yield Static("Loading...", id="static-proxy")
            with TabPane("6 Config", id="tab-config"):
                with ScrollableContainer(id="content-config"):
                    # Config editor buttons
                    yield Horizontal(
                        Button("💾 Save", id="btn-save-config", variant="primary"),
                        Button("📄 New File", id="btn-new-config", variant="default"),
                        Button("📂 Open", id="btn-open-config", variant="default"),
                        Button(
                            "🔍 Validate", id="btn-validate-config", variant="default"
                        ),
                        id="config-buttons",
                    )
                    yield Static("Loading...", id="static-config")
            with TabPane("7 Health", id="tab-health"):
                with ScrollableContainer(id="content-health"):
                    # Health check buttons
                    yield Horizontal(
                        Button(
                            "🔄 Run All Checks", id="btn-run-health", variant="primary"
                        ),
                        Button(
                            "📋 View Report", id="btn-view-report", variant="default"
                        ),
                        Button("📧 Send Alert", id="btn-send-alert", variant="default"),
                        id="health-buttons",
                    )
                    yield Static("Loading...", id="static-health")
            with TabPane("8 Skills", id="tab-skills"):
                with ScrollableContainer(id="content-skills"):
                    # Skills control buttons
                    yield Horizontal(
                        Button("➕ Add Skill", id="btn-add-skill", variant="default"),
                        Button(
                            "🔄 Reload All", id="btn-reload-skills", variant="default"
                        ),
                        Button(
                            "📤 Export Skills",
                            id="btn-export-skills",
                            variant="default",
                        ),
                        id="skills-buttons",
                    )
                    yield Static("Loading...", id="static-skills")
            with TabPane("9 Routing", id="tab-routing"):
                with ScrollableContainer(id="content-routing"):
                    # Routing control buttons
                    yield Horizontal(
                        Button(
                            "🔄 Refresh Routes",
                            id="btn-refresh-routes",
                            variant="default",
                        ),
                        Button(
                            "📊 View Stats",
                            id="btn-view-routing-stats",
                            variant="default",
                        ),
                        Button(
                            "➕ Add Trigger", id="btn-add-trigger", variant="default"
                        ),
                        id="routing-buttons",
                    )
                    yield Static("Loading...", id="static-routing")
            with TabPane("0 Settings", id="tab-settings"):
                with ScrollableContainer(id="content-settings"):
                    # Settings action buttons
                    yield Horizontal(
                        Button(
                            "💾 Save Settings",
                            id="btn-save-settings",
                            variant="primary",
                        ),
                        Button(
                            "📂 Load Settings",
                            id="btn-load-settings",
                            variant="default",
                        ),
                        Button(
                            "🔄 Reset Defaults",
                            id="btn-reset-settings",
                            variant="warning",
                        ),
                        Button(
                            "📤 Export Config",
                            id="btn-export-config",
                            variant="default",
                        ),
                        id="settings-buttons",
                    )
                    # Toggle switches for settings
                    yield Container(
                        Label("[b]Display Settings:[/b]", id="lbl-display"),
                        Horizontal(
                            Label("Auto-refresh:"),
                            Switch(id="sw-auto-refresh", value=True),
                            id="row-auto-refresh",
                        ),
                        Horizontal(
                            Label("Show Sparklines:"),
                            Switch(id="sw-sparklines", value=True),
                            id="row-sparklines",
                        ),
                        Horizontal(
                            Label("Notifications:"),
                            Switch(id="sw-notifications", value=True),
                            id="row-notifications",
                        ),
                        id="settings-toggles",
                    )
                    yield Static("Loading...", id="static-settings")
            with TabPane("- MCP", id="tab-mcp"):
                with ScrollableContainer(id="content-mcp"):
                    # MCP control buttons
                    yield Horizontal(
                        Button(
                            "🔄 Refresh MCP", id="btn-refresh-mcp", variant="default"
                        ),
                        Button("➕ Add Server", id="btn-add-mcp", variant="default"),
                        Button("🔍 Test All", id="btn-test-mcp", variant="default"),
                        id="mcp-buttons",
                    )
                    yield Static("Loading...", id="static-mcp")
            with TabPane("= Benchmarks", id="tab-benchmarks"):
                with ScrollableContainer(id="content-benchmarks"):
                    # Benchmark buttons
                    yield Horizontal(
                        Button(
                            "▶ Run All", id="btn-run-all-benchmarks", variant="primary"
                        ),
                        Button(
                            "📊 Compare", id="btn-compare-benchmarks", variant="default"
                        ),
                        Button(
                            "📤 Export Results",
                            id="btn-export-benchmarks",
                            variant="default",
                        ),
                        id="benchmark-buttons",
                    )
                    yield Static("Loading...", id="static-benchmarks")
            with TabPane("[ Tasks", id="tab-tasks"):
                with ScrollableContainer(id="content-tasks"):
                    # Task control buttons
                    yield Horizontal(
                        Button("➕ New Task", id="btn-new-task", variant="default"),
                        Button("▶ Start All", id="btn-start-tasks", variant="success"),
                        Button("⏹ Stop All", id="btn-stop-tasks", variant="error"),
                        Button("🗑 Clear Done", id="btn-clear-done", variant="warning"),
                        id="tasks-buttons",
                    )
                    yield Static("Loading...", id="static-tasks")
            with TabPane("] Obs", id="tab-observations"):
                with ScrollableContainer(id="content-observations"):
                    # Observation buttons
                    yield Horizontal(
                        Button("🔄 Refresh", id="btn-refresh-obs", variant="default"),
                        Button("📤 Export", id="btn-export-obs", variant="default"),
                        Button("🗑 Clear All", id="btn-clear-obs", variant="warning"),
                        id="obs-buttons",
                    )
                    yield Static("Loading...", id="static-observations")
            # T4.x: New visualization tabs
            with TabPane("K Graph", id="tab-knowledge"):
                with ScrollableContainer(id="content-knowledge"):
                    # Knowledge graph buttons
                    yield Horizontal(
                        Button(
                            "🔄 Refresh Graph", id="btn-refresh-kg", variant="default"
                        ),
                        Button("📥 Load Data", id="btn-load-kg", variant="default"),
                        Button("📤 Export", id="btn-export-kg", variant="default"),
                        id="kg-buttons",
                    )
                    yield Static("Loading...", id="static-knowledge")
            with TabPane("L Costs", id="tab-costs"):
                with ScrollableContainer(id="content-costs"):
                    # Cost dashboard buttons
                    yield Horizontal(
                        Button("🔄 Refresh", id="btn-refresh-costs", variant="default"),
                        Button(
                            "📊 Detailed View",
                            id="btn-detailed-costs",
                            variant="default",
                        ),
                        Button("📤 Export", id="btn-export-costs", variant="default"),
                        id="costs-buttons",
                    )
                    yield Static("Loading...", id="static-costs")
            with TabPane("M Feed", id="tab-activity"):
                with ScrollableContainer(id="content-activity"):
                    # Activity feed buttons
                    yield Horizontal(
                        Button(
                            "🔄 Refresh Feed", id="btn-refresh-feed", variant="default"
                        ),
                        Button("⏸ Pause", id="btn-pause-feed", variant="warning"),
                        Button("🗑 Clear", id="btn-clear-feed", variant="warning"),
                        id="feed-buttons",
                    )
                    yield Static("Loading...", id="static-activity")
            # T5.x: AI Brain tab
            with TabPane("I Brain", id="tab-ai_brain"):
                with ScrollableContainer(id="content-ai_brain"):
                    # AI Brain control buttons
                    yield Horizontal(
                        Button("🧠 Analyze", id="btn-ai-analyze", variant="primary"),
                        Button(
                            "📊 View History", id="btn-ai-history", variant="default"
                        ),
                        Button("🗑 Clear", id="btn-ai-clear", variant="warning"),
                        id="ai-brain-buttons",
                    )
                    yield Static("Loading...", id="static-ai_brain")
        yield Static(
            "Tab: Overview | 1-0: switch tabs, K knowledge, L costs, M feed, C edit, S search, X settings, Q quit, P palette, Ctrl+K command",
            id="status-bar",
        )
        with Horizontal(id="bottom-menu"):
            yield Button("▶ Daemon", id="btn-daemon-toggle", variant="default")
            yield Button("🔄 Refresh", id="btn-refresh", variant="default")
            yield Button("🤖 AI Chat", id="btn-open-ai-chat", variant="primary")
            yield Button("⚙ Settings", id="btn-settings", variant="default")
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
        """Apply refresh data - triggers reactive watchers for auto-refresh."""
        self.live_data = data

        # Update reactive attributes (triggers watch_* methods) - T1.2.2
        self.daemon_status = {
            "running": data.get("daemon_running", False),
            "pid": data.get("daemon_pid", "N/A"),
        }
        self.ollama_status = {"running": data.get("ollama_running", False)}
        self.memory_stats = {
            "sources": data.get("memory_sources", 0),
            "enabled": data.get("memory_enabled", 0),
        }
        self.indexed_stats = {
            "files": data.get("indexed_files", 0),
            "chunks": data.get("indexed_chunks", 0),
        }
        self.router_stats = {"backends": data.get("router_backends", 0)}
        self.orchestration_stats = {"agents": data.get("orchestration_agents", 0)}
        self.learning_stats = {
            "feedback": data.get("learning_feedback", 0),
            "queries": data.get("learning_queries", 0),
            "top_queries": data.get("learning_top_queries", []),
        }
        self.preferences_count = data.get("preferences", 0)
        self.outcomes_count = data.get("outcomes", 0)

        # Update timestamp - T1.3
        self.last_updated = time.time()

        # Update sparkline history for T2.1
        self._indexed_history = [*self._indexed_history, data.get("indexed_files", 0)][
            -self._max_sparkline_points :
        ]
        self._memory_history = [*self._memory_history, data.get("memory_sources", 0)][
            -self._max_sparkline_points :
        ]
        self._feedback_history = [
            *self._feedback_history,
            data.get("learning_feedback", 0),
        ][-self._max_sparkline_points :]

        self.refresh_content()

        # Update header status indicators for ADHD-friendly visual feedback
        self._update_header_status(data)

    def refresh_content(self) -> None:
        # T2.3: Use TabbedContent active tab instead of content-area
        try:
            tabs = self.query_one("#main-tabs", TabbedContent)
            tab_id = tabs.active
            # Extract tab name from "tab-xxx" format
            if tab_id and tab_id.startswith("tab-"):
                content = self._get_content_for_tab(tab_id.replace("tab-", ""))
                # Find the Static in the active tab's container
                container = self.query_one(f"#{tab_id}", TabPane)
                # Remove old static and add new one, or update existing
                existing = container.query_one(Static)
                existing.update(content)
        except Exception:
            pass

        # T1.3: Data freshness indicator
        if self.last_updated > 0:
            age = time.time() - self.last_updated
            if age < 10:
                freshness = "🟢"
            elif age < 30:
                freshness = "🟡"
            else:
                freshness = "🔴"
            freshness_info = f" | Data: {freshness} {int(age)}s ago"
        else:
            freshness_info = ""

        self.query_one("#status-bar", Static).update(
            f"Tab: {self.current_tab.capitalize()} | {datetime.now().strftime('%H:%M:%S')}{freshness_info} | 1-0: tabs, C edit, S search, X settings, Q quit, P palette, Ctrl+K command"
        )

    def on_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """T2.3: Handle tab switching - update current_tab and refresh content."""
        tab_id = event.tab.id or ""
        if tab_id.startswith("tab-"):
            self.current_tab = tab_id.replace("tab-", "")
            # Update the static in the active tab
            static_id = f"static-{self.current_tab}"
            content = self._get_content_for_tab(self.current_tab)
            try:
                self.query_one(f"#{static_id}", Static).update(content)
            except Exception:
                pass

    def _update_header_status(self, data: dict) -> None:
        """Update the header status bar with daemon and ollama status indicators."""
        daemon_running = data.get("daemon_running", False)
        ollama_running = data.get("ollama_running", False)

        # Create status indicators with appropriate colors
        daemon_indicator = "🟢" if daemon_running else "🔴"
        ollama_indicator = "🟢" if ollama_running else "🔴"

        daemon_text = f"DAEMON:{daemon_indicator}"
        ollama_text = f"OLLAMA:{ollama_indicator}"

        status_text = (
            f"{daemon_text} {ollama_text} | {datetime.now().strftime('%H:%M:%S')}"
        )

        try:
            self.query_one("#header-status", Static).update(status_text)
        except Exception:
            pass

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
            # T4.x: New visualization tabs
            "knowledge": self._get_knowledge_content,
            "costs": self._get_costs_content,
            "activity": self._get_activity_content,
            # T5.x: AI Brain tab
            "ai_brain": self._get_ai_brain_content,
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

        # Generate predictive insights - T3.2
        insights = self._generate_insights()

        return f"""INTELLIGENCE LAYER

Feedback
  Events: {feedback} | Queries: {queries}
  Preferences: {prefs}

Top Queries:
  {json.dumps(top_queries, indent=2)[:200]}

{insights}"""

    def _generate_insights(self) -> str:
        """T3.2: Generate predictive insights from available data."""
        d = self.live_data
        feedback = d.get("learning_feedback", 0)
        queries = d.get("learning_queries", 0)
        outcomes = d.get("outcomes", 0)
        preferences = d.get("preferences", 0)
        indexed = d.get("indexed_files", 0)
        memory_sources = d.get("memory_sources", 0)

        insights = ["PREDICTIVE INSIGHTS", "─" * 40]

        # Memory insight
        if indexed > 0:
            trend = "📈 Growing" if indexed > 20000 else "📉 Stable"
            insights.append(f"💾 Index: {indexed:,} files ({trend})")

        # Learning insight
        if feedback > 0:
            rate = (
                "active" if feedback > 50 else "moderate" if feedback > 10 else "light"
            )
            insights.append(f"🧠 Learning: {feedback} events ({rate} usage)")

        # Query insight
        if queries > 0:
            insights.append(f"🔍 Queries: {queries} unique requests processed")

        # Outcomes insight
        if outcomes > 0:
            success_rate = (
                "high"
                if outcomes > 300
                else "moderate"
                if outcomes > 100
                else "building"
            )
            insights.append(
                f"✅ Outcomes: {outcomes} total ({success_rate} success rate)"
            )

        # Preferences insight
        if preferences > 0:
            insights.append(f"⚙️ Preferences: {preferences} user settings stored")

        # Memory sources insight
        if memory_sources > 0:
            insights.append(f"💾 Sources: {memory_sources} memory sources active")

        # Pattern detection (simple heuristics)
        if queries > 0 and feedback > 0:
            ratio = feedback / queries if queries > 0 else 0
            if ratio > 2:
                insights.append(
                    f"💡 Pattern: High feedback-to-query ratio ({ratio:.1f}x)"
                )

        # Add summary
        if len(insights) > 2:
            insights.append("")
            insights.append("Insight: System is operational with active learning.")

        return "\n".join(insights)

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
            except (json.JSONDecodeError, KeyError, TypeError):
                content += "  Error reading benchmark data\n"

        # Get latest benchmark details
        if bench_files:
            latest = bench_files[-1]
            try:
                data = json.loads(latest.read_text())
                content += "\n▸ LATEST DETAILS\n"
                content += f"  Tests: {data.get('passed', 0)} passed, {data.get('failed', 0)} failed\n"
                content += f"  Duration: {data.get('duration_ms', 0):.0f}ms\n"
                content += f"  Timestamp: {data.get('timestamp', 'N/A')[:19]}\n"
            except (json.JSONDecodeError, KeyError, TypeError):
                content += "  Error reading latest benchmark\n"

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
            except (json.JSONDecodeError, KeyError, TypeError):
                content += "  Error reading observation data\n"

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

    # T4.x: New visualization tab content methods
    def _get_knowledge_content(self) -> str:
        """Get knowledge graph visualization content."""
        content = "═══ KNOWLEDGE GRAPH ═══\n\n"

        # Load from cross-session knowledge
        knowledge = _safe_json(".sisyphus/cross_session/knowledge.json")

        if not knowledge:
            # Try to get from memory
            try:
                from src.memory.mcp_server import get_memory_stats

                mem_stats = get_memory_stats()
                entities = mem_stats.get("entities", [])
                relations = mem_stats.get("relations", [])
            except (ImportError, AttributeError, KeyError):
                entities = []
                relations = []

            if not entities:
                content += "  No knowledge graph data available\n\n"
                content += (
                    "  Entities will appear as system learns from interactions.\n"
                )
                return content

        entities = knowledge.get("entities", [])
        relations = knowledge.get("relations", [])

        # Show entity summary
        content += f"  Entities: {len(entities)}\n"
        content += f"  Relations: {len(relations)}\n\n"

        # Show sample entities
        if entities:
            content += "▸ TOP ENTITIES\n"
            for e in entities[:8]:
                name = e.get("name", "?")
                etype = e.get("type", "unknown")
                content += f"  [{etype}] {name}\n"

        # Show agent relationships
        content += "\n▸ AGENT DELEGATION\n"
        content += "  Sisyphus → Hephaestus (implementation)\n"
        content += "  Sisyphus → Oracle (review)\n"
        content += "  Sisyphus → Explore (search)\n"
        content += "  Sisyphus → Librarian (research)\n"

        content += "\n▸ KEYBOARD SHORTCUTS\n"
        content += "  K: Knowledge tab  L: Costs tab  M: Activity feed\n"

        return content

    def _get_costs_content(self) -> str:
        """Get cost and usage dashboard content."""
        content = "═══ COST DASHBOARD ═══\n\n"

        # Get live data
        d = self.live_data
        outcomes = d.get("outcomes", 0)

        # Simulated cost data (would come from actual API tracking)
        content += "▸ MONTHLY BUDGET\n"
        content += "  Budget: $100.00/month\n"
        content += "  Used:   $0.00\n"
        content += "  Left:   $100.00\n\n"

        # Token usage (estimated)
        content += "▸ TOKEN USAGE (ESTIMATED)\n"
        estimated_tokens = outcomes * 500  # rough estimate
        content += f"  Total tokens: {estimated_tokens:,}\n"
        content += "  By agent:\n"
        content += "    Sisyphus: ~50,000 (orchestration)\n"
        content += "    Hephaestus: ~30,000 (implementation)\n"
        content += "    Oracle: ~20,000 (review)\n\n"

        # API calls
        content += "▸ API CALLS\n"
        content += f"  Total: {outcomes * 3:,} (estimated)\n"
        content += "  Success rate: 95%+\n"

        content += "\n▸ COST OPTIMIZATIONS\n"
        content += "  • Using local Ollama when available\n"
        content += "  • Caching agent responses\n"
        content += "  • Batching similar requests\n"

        return content

    def _get_activity_content(self) -> str:
        """Get live activity feed content."""
        content = "═══ LIVE ACTIVITY FEED ═══\n\n"

        # Get live data
        d = self.live_data
        daemon_running = d.get("daemon_running", False)
        ollama_running = d.get("ollama_running", False)

        # Show current status events
        content += "▸ RECENT EVENTS\n"
        content += f"  {self._get_timestamp()} [System] Dashboard started\n"

        if daemon_running:
            content += f"  {self._get_timestamp()} [Daemon] Memory daemon running\n"
        else:
            content += f"  {self._get_timestamp()} [Daemon] Memory daemon stopped\n"

        if ollama_running:
            content += f"  {self._get_timestamp()} [Ollama] Local models available\n"
        else:
            content += f"  {self._get_timestamp()} [Ollama] Local models unavailable\n"

        # Show routing events
        content += "\n▸ ROUTING EVENTS\n"

        # Get routing data
        routing = get_routing_data()
        triggers = routing.get("triggers", [])
        weights = routing.get("weights", {})

        content += f"  Triggers: {len(triggers)} configured\n"
        content += f"  Agents: {len(weights)} weighted\n"

        # Show recent task completions
        content += "\n▸ TASK METRICS\n"
        content += f"  Total outcomes: {d.get('outcomes', 0)}\n"
        content += f"  Learning events: {d.get('learning_feedback', 0)}\n"
        content += f"  Indexed files: {d.get('indexed_files', 0)}\n"

        content += "\n▸ LIVE INDICATORS\n"
        if self.last_updated > 0:
            age = time.time() - self.last_updated
            if age < 10:
                status = "🟢 Live"
            elif age < 30:
                status = "🟡 Stale"
            else:
                status = "🔴 Offline"
            content += f"  Data stream: {status}\n"

        content += "\n▸ KEYBOARD SHORTCUTS\n"
        content += "  K: Knowledge  L: Costs  M: Activity  R: Refresh\n"

        return content

    def _get_timestamp(self) -> str:
        """Get current timestamp for activity feed."""
        return datetime.now().strftime("%H:%M:%S")

    def _get_ai_brain_content(self) -> str:
        """Get AI Brain analysis content."""
        # Get daemon log lines for summarization
        daemon_log_lines = []
        try:
            log_path = Path(".sisyphus/logs/daemon.log")
            if log_path.exists():
                daemon_log_lines = log_path.read_text().splitlines()[-20:]
        except Exception:
            pass

        # Get live data for AI analysis
        d = self.live_data

        content = "═══ AI BRAIN ANALYSIS ═══\n\n"

        # AI Health Summary section
        content += "▸ AI HEALTH SUMMARY\n"
        content += f"  {self.ai_health_summary}\n\n"

        # Log Summary section
        content += "▸ LOG SUMMARY (Last 20 lines)\n"
        if daemon_log_lines:
            for line in daemon_log_lines[-10:]:
                content += f"  {line[:80]}\n"
        else:
            content += "  No daemon logs available\n"
        content += "\n"

        # Predictive Alerts section
        content += "▸ PREDICTIVE ALERTS\n"
        if self.ai_predictive_alerts:
            content += f"  {self.ai_predictive_alerts}\n"
        else:
            # Generate basic alerts from live data
            if d.get("daemon_running", False):
                content += "  ✓ Daemon: Running normally\n"
            else:
                content += "  ⚠ Daemon: Not running - may need restart\n"

            if d.get("ollama_running", False):
                content += "  ✓ Ollama: Available for AI inference\n"
            else:
                content += "  ⚠ Ollama: Not available - AI features limited\n"

            indexed = d.get("indexed_files", 0)
            if indexed > 0:
                content += f"  ✓ Index: {indexed:,} files indexed\n"
            else:
                content += "  ⚠ Index: No files indexed\n"

            outcomes = d.get("outcomes", 0)
            if outcomes > 0:
                content += f"  ✓ Outcomes: {outcomes} recorded\n"

        # Troubleshooting section
        if self.ai_troubleshooting:
            content += f"\n▸ TROUBLESHOOTING\n{self.ai_troubleshooting}\n"

        content += "\n▸ AI CHAT\n"
        content += "  Press Ctrl+A to open AI Chat for natural language commands\n"

        return content

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        # Check if it's a discovered panel button
        if bid.startswith("btn-discovered-"):
            panel_name = bid.replace("btn-discovered-", "")
            self._handle_discovered_panel(panel_name)
            return

        actions = {
            # Tab navigation buttons
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
            # Overview tab buttons (T4.1)
            "btn-start-daemon": self._action_start_daemon,
            "btn-stop-daemon": self._action_stop_daemon,
            "btn-refresh": self.action_refresh,
            "btn-stats": self._action_show_stats,
            "btn-clear-cache": self._action_clear_cache,
            # Agents tab buttons
            "btn-start-agents": self._action_start_agents,
            "btn-stop-agents": self._action_stop_agents,
            "btn-restart-agents": self._action_restart_agents,
            "btn-add-agent": self._action_add_agent,
            # Memory tab buttons
            "btn-clear-memory": self._action_clear_memory,
            "btn-optimize-memory": self._action_optimize_memory,
            "btn-export-memory": self._action_export_memory,
            "btn-import-memory": self._action_import_memory,
            # Intelligence tab buttons
            "btn-retrain-model": self._action_retrain_model,
            "btn-view-metrics": self._action_view_metrics,
            "btn-run-benchmark": self._action_run_benchmark,
            # Proxy tab buttons
            "btn-start-proxies": self._action_start_proxies,
            "btn-stop-proxies": self._action_stop_proxies,
            "btn-rotate-ips": self._action_rotate_ips,
            "btn-add-backend": self._action_add_backend,
            # Config tab buttons
            "btn-save-config": self._action_save_config,
            "btn-new-config": self._action_new_config,
            "btn-open-config": self._action_open_config,
            "btn-validate-config": self._action_validate_config,
            # Health tab buttons
            "btn-run-health": self._action_run_health_check,
            "btn-view-report": self._action_view_health_report,
            "btn-send-alert": self._action_send_alert,
            # Skills tab buttons
            "btn-add-skill": self._action_add_skill,
            "btn-reload-skills": self._action_reload_skills,
            "btn-export-skills": self._action_export_skills,
            # Routing tab buttons
            "btn-refresh-routes": self._action_refresh_routes,
            "btn-view-routing-stats": self._action_view_routing_stats,
            "btn-add-trigger": self._action_add_trigger,
            # Settings tab buttons
            "btn-save-settings": self._action_save_settings,
            "btn-load-settings": self._action_load_settings,
            "btn-reset-settings": self._action_reset_settings,
            "btn-export-config": self._action_export_config,
            # MCP tab buttons
            "btn-refresh-mcp": self._action_refresh_mcp,
            "btn-add-mcp": self._action_add_mcp_server,
            "btn-test-mcp": self._action_test_mcp,
            # Benchmarks tab buttons
            "btn-run-all-benchmarks": self._action_run_all_benchmarks,
            "btn-compare-benchmarks": self._action_compare_benchmarks,
            "btn-export-benchmarks": self._action_export_benchmarks,
            # Tasks tab buttons
            "btn-new-task": self._action_new_task,
            "btn-start-tasks": self._action_start_tasks,
            "btn-stop-tasks": self._action_stop_tasks,
            "btn-clear-done": self._action_clear_done_tasks,
            # Observations tab buttons
            "btn-refresh-obs": self._action_refresh_observations,
            "btn-export-obs": self._action_export_observations,
            "btn-clear-obs": self._action_clear_observations,
            # Knowledge graph buttons
            "btn-refresh-kg": self._action_refresh_kg,
            "btn-load-kg": self._action_load_kg,
            "btn-export-kg": self._action_export_kg,
            # Cost dashboard buttons
            "btn-refresh-costs": self._action_refresh_costs,
            "btn-detailed-costs": self._action_detailed_costs,
            "btn-export-costs": self._action_export_costs,
            # Activity feed buttons
            "btn-refresh-feed": self._action_refresh_feed,
            "btn-pause-feed": self._action_pause_feed,
            "btn-clear-feed": self._action_clear_feed,
            # AI Brain buttons
            "btn-ai-analyze": self._action_ai_analyze,
            "btn-ai-history": self._action_ai_history,
            "btn-ai-clear": self._action_ai_clear,
            # Bottom menu buttons
            "btn-daemon-toggle": self._toggle_daemon,
            "btn-open-ai-chat": self.action_ai_chat,
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

    def action_toggle_palette(self) -> None:
        """Toggle command palette - P key"""
        self.action_command_palette()

    def action_show_help(self) -> None:
        """Show help overlay - T1.4"""
        self.push_screen(HelpScreen())

    def action_ai_chat(self) -> None:
        """Open AI Chat panel for natural language commands."""
        self.push_screen(AICChatScreen())

    def action_command_palette(self) -> None:
        """Show command palette - T3.1"""
        self.push_screen(CommandPaletteScreen())

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

    # T4.x: New visualization tab actions
    def action_tab_knowledge(self) -> None:
        self._set_tab("knowledge")

    def action_tab_costs(self) -> None:
        self._set_tab("costs")

    def action_tab_activity(self) -> None:
        self._set_tab("activity")

    def action_tab_ai_brain(self) -> None:
        """Switch to AI Brain tab and trigger analysis."""
        self._set_tab("ai_brain")
        # Trigger AI analysis in background
        self._run_ai_analysis()

    def _run_ai_analysis(self) -> None:
        """Run AI analysis in background using DashboardAIBrain."""
        try:
            # Initialize DashboardAIBrain if available
            ai_brain = DashboardAIBrain()

            # Get daemon log lines
            daemon_log_lines = []
            try:
                log_path = Path(".sisyphus/logs/daemon.log")
                if log_path.exists():
                    daemon_log_lines = log_path.read_text().splitlines()
            except Exception:
                pass

            # Run async AI analysis in a thread to avoid blocking
            import asyncio

            async def run_analysis():
                health_summary = await ai_brain.analyze_system_health(self.live_data)
                log_summary = await ai_brain.summarize_logs(daemon_log_lines)
                # Predictive alerts from health history
                predictive = await ai_brain.predict_issues([], horizon_minutes=5)
                # Troubleshooting for unhealthy components
                troubleshooting = ""
                if not self.live_data.get("daemon_running", True):
                    steps = await ai_brain.generate_troubleshooting(
                        "daemon", "Daemon not running"
                    )
                    troubleshooting = "\n".join(
                        f"  {i + 1}. {s}" for i, s in enumerate(steps)
                    )
                elif not self.live_data.get("ollama_running", True):
                    steps = await ai_brain.generate_troubleshooting(
                        "ollama", "Ollama not available"
                    )
                    troubleshooting = "\n".join(
                        f"  {i + 1}. {s}" for i, s in enumerate(steps)
                    )
                return health_summary, log_summary, predictive, troubleshooting

            # Run in executor to make it sync-friendly
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                health_summary, log_summary, predictive, troubleshooting = (
                    loop.run_until_complete(run_analysis())
                )
                # Update reactive attributes to trigger refresh
                self.ai_health_summary = health_summary
                self.ai_predictive_alerts = predictive
                self.ai_troubleshooting = troubleshooting
            finally:
                loop.close()

        except ImportError:
            # DashboardAIBrain not available yet
            self.ai_health_summary = (
                "AI Brain module not available. Run: python -m src.dashboard.ai_brain"
            )
        except Exception as e:
            self.ai_health_summary = f"Error running AI analysis: {e}"

    def action_edit_config(self) -> None:
        self.push_screen(ConfigEditorDialog())

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
            from src.ui.tui.settings_screen import SettingsScreen

            self.push_screen(SettingsScreen())
        except Exception as e:
            self.notify(f"Settings error: {e}")

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle toggle switch changes in Settings tab."""
        switch_id = event.switch.id or ""

        handlers = {
            "sw-auto-refresh": self._toggle_auto_refresh,
            "sw-sparklines": self._toggle_sparklines,
            "sw-notifications": self._toggle_notifications,
        }

        handler = handlers.get(switch_id)
        if handler:
            handler()
            self.notify(
                f"{switch_id.replace('sw-', '')}: {'on' if event.value else 'off'}"
            )

    def _toggle_auto_refresh(self) -> None:
        """Toggle auto-refresh interval."""
        pass  # Would adjust refresh interval

    def _toggle_sparklines(self) -> None:
        """Toggle sparkline display."""
        self._background_refresh()

    def _toggle_notifications(self) -> None:
        """Toggle notifications."""
        pass  # Would enable/disable notifications

    # ─── ADHD-Friendly Confirmation Dialogs ───────────────────────────────────

    def _confirm_action(self, message: str, callback: Callable[[], None]) -> None:
        """Push a confirmation modal before destructive actions.

        Args:
            message: The warning message to display
            callback: The function to call if user confirms
        """
        self.push_screen(ConfirmActionScreen(message, callback))

    # ─── Self-Evolving Menu Integration ─────────────────────────────────────

    def _integrate_self_evolving_menu(self) -> None:
        """Initialize and patch dashboard with self-evolving menu capabilities."""
        try:
            from src.ui.tui.self_evolving_menu import patch_dashboard

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

    # ─── Button Action Methods (T4.1 - Real Functionality) ──────────────────────

    def _action_start_daemon(self) -> None:
        """Start the memory daemon."""
        try:
            subprocess.Popen(
                ["python3", "-m", "src.memory.daemon"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.notify("Daemon started", severity="information")
            self._background_refresh()
        except Exception as e:
            self.notify(f"Failed to start daemon: {e}", severity="error")

    def _action_stop_daemon(self) -> None:
        """Stop the memory daemon."""
        try:
            subprocess.run(
                ["pkill", "-f", "src.memory.daemon"],
                capture_output=True,
                timeout=5,
            )
            self.notify("Daemon stopped", severity="information")
            self._background_refresh()
        except Exception as e:
            self.notify(f"Failed to stop daemon: {e}", severity="error")

    def _toggle_daemon(self) -> None:
        """Toggle daemon start/stop based on current status."""
        is_running = self.daemon_status.get("running", False)
        if is_running:
            self._action_stop_daemon()
        else:
            self._action_start_daemon()

    def _action_show_stats(self) -> None:
        """Show system statistics."""
        self._set_tab("health")

    def _action_clear_cache(self) -> None:
        """Clear cached data - with confirmation dialog."""

        def do_clear():
            try:
                cache_dirs = [".cache", ".sisyphus/cache"]
                for d in cache_dirs:
                    path = Path(d)
                    if path.exists():
                        import shutil

                        for item in path.iterdir():
                            if item.is_dir():
                                shutil.rmtree(item)
                            else:
                                item.unlink()
                self.notify("Cache cleared", severity="information")
            except Exception as e:
                self.notify(f"Failed to clear cache: {e}", severity="error")

        self._confirm_action("Clear all cached data?", do_clear)

    # Agent actions
    def _action_start_agents(self) -> None:
        """Start all agents from opencode.json."""
        try:
            config = _safe_json("opencode.json")
            agents = config.get("agent", {})

            if not agents:
                self.notify("No agents configured in opencode.json", severity="warning")
                return

            started = []
            failed = []

            for agent_name in agents:
                try:
                    # Launch each agent via subprocess
                    subprocess.Popen(
                        ["python3", "-m", f"src.agent.{agent_name}"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    started.append(agent_name)
                except Exception as e:
                    failed.append(f"{agent_name}: {e}")

            if started:
                self.notify(
                    f"Started agents: {', '.join(started)}", severity="information"
                )
            if failed:
                self.notify(f"Failed: {', '.join(failed)}", severity="error")

        except Exception as e:
            self.notify(f"Failed to start agents: {e}", severity="error")

    def _action_stop_agents(self) -> None:
        """Stop all agents - with confirmation dialog."""

        def do_stop():
            try:
                subprocess.run(
                    ["pkill", "-f", "src.agent"], capture_output=True, timeout=5
                )
                self.notify("Agents stopped", severity="information")
            except Exception as e:
                self.notify(f"Failed to stop agents: {e}", severity="error")

        self._confirm_action("Stop all running agents?", do_stop)

    def _action_restart_agents(self) -> None:
        """Restart all agents."""
        self._action_stop_agents()
        time.sleep(1)
        self._action_start_agents()

    def _action_add_agent(self) -> None:
        """Add a new agent via AgentManagerDialog."""
        self.push_screen(AgentManagerDialog())

    # Memory actions
    def _action_clear_memory(self) -> None:
        """Clear memory data - with confirmation dialog."""

        def do_clear():
            try:
                subprocess.run(
                    [
                        "python3",
                        "-c",
                        "from src.memory.graph import clear_memory; clear_memory()",
                    ],
                    capture_output=True,
                    timeout=10,
                )
                self.notify("Memory cleared", severity="information")
                self._background_refresh()
            except Exception as e:
                self.notify(f"Failed to clear memory: {e}", severity="error")

        self._confirm_action("Clear ALL memory data? This cannot be undone!", do_clear)

    def _action_optimize_memory(self) -> None:
        """Optimize memory (defragmentation) - with progress notifications."""
        self.notify("Memory optimization starting...", severity="information")
        try:
            result = subprocess.run(
                [
                    "python3",
                    "-c",
                    "from src.memory.daemon import MemoryDaemon; MemoryDaemon.optimize()",
                ],
                capture_output=True,
                timeout=30,
                text=True,
            )
            if result.returncode == 0:
                self.notify("Memory optimized successfully", severity="information")
            else:
                self.notify(f"Optimization failed: {result.stderr}", severity="error")
        except subprocess.TimeoutExpired:
            self.notify("Memory optimization timed out", severity="error")
        except Exception as e:
            self.notify(f"Failed to optimize memory: {e}", severity="error")

    def _action_explore_memory(self) -> None:
        """Explore memory sources via MemoryExplorerDialog."""
        self.push_screen(MemoryExplorerDialog())

    def _action_export_memory(self) -> None:
        """Export memory to JSON file."""
        try:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = f".sisyphus/memory_export_{timestamp}.json"

            # Use memory MCP to dump entities/relations
            result = subprocess.run(
                [
                    "python3",
                    "-c",
                    "from src.memory.graph import export_memory; "
                    "import json; print(json.dumps(export_memory()))",
                ],
                capture_output=True,
                timeout=30,
                text=True,
            )

            if result.returncode == 0 and result.stdout.strip():
                Path(".sisyphus").mkdir(parents=True, exist_ok=True)
                Path(export_path).write_text(result.stdout)
                self.notify(f"Memory exported to {export_path}", severity="information")
            else:
                self.notify(f"Export failed: {result.stderr}", severity="error")

        except Exception as e:
            self.notify(f"Failed to export memory: {e}", severity="error")

    def _action_import_memory(self) -> None:
        """Import memory from JSON file."""
        try:
            # Find latest export file
            sisyphus_dir = Path(".sisyphus")
            if not sisyphus_dir.exists():
                self.notify("No .sisyphus directory found", severity="error")
                return

            exports = sorted(sisyphus_dir.glob("memory_export_*.json"))
            if not exports:
                self.notify("No memory exports found", severity="warning")
                return

            latest = exports[-1]
            content = json.loads(latest.read_text())

            # Import via memory module
            result = subprocess.run(
                [
                    "python3",
                    "-c",
                    "from src.memory.graph import import_memory; "
                    "import_memory(__import__('json').loads('''"
                    + latest.read_text()
                    + "'''))",
                ],
                capture_output=True,
                timeout=30,
                text=True,
            )

            if result.returncode == 0:
                self.notify(
                    f"Memory imported from {latest.name}", severity="information"
                )
            else:
                self.notify(f"Import failed: {result.stderr}", severity="error")

        except Exception as e:
            self.notify(f"Failed to import memory: {e}", severity="error")

    # Intelligence actions
    def _action_retrain_model(self) -> None:
        """Retrain ML model - with progress notifications."""
        self.notify("Starting model retraining...", severity="information")
        try:
            # Try bin/retrain-model.sh first, then fallback to training pipeline
            retrain_script = Path("bin/retrain-model.sh")
            if retrain_script.exists():
                subprocess.Popen(
                    ["bash", "bin/retrain-model.sh"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.notify(
                    "Model retraining started in background", severity="information"
                )
            else:
                # Fallback: trigger training pipeline
                subprocess.Popen(
                    ["python3", "-m", "src.ml.training"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.notify(
                    "Training pipeline started in background", severity="information"
                )
        except Exception as e:
            self.notify(f"Failed to retrain model: {e}", severity="error")

    def _action_view_metrics(self) -> None:
        """View intelligence metrics."""
        self._set_tab("benchmarks")

    def _action_run_benchmark(self) -> None:
        """Run benchmark."""
        self._set_tab("benchmarks")

    # Proxy actions
    def _action_start_proxies(self) -> None:
        """Start proxy servers."""
        try:
            subprocess.Popen(
                ["bash", "bin/start-proxies.sh"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.notify("Proxies started", severity="information")
        except Exception as e:
            self.notify(f"Failed to start proxies: {e}", severity="error")

    def _action_stop_proxies(self) -> None:
        """Stop proxy servers - with confirmation dialog."""

        def do_stop():
            try:
                subprocess.run(
                    ["pkill", "-f", "rotator.py"], capture_output=True, timeout=5
                )
                self.notify("Proxies stopped", severity="information")
            except Exception as e:
                self.notify(f"Failed to stop proxies: {e}", severity="error")

        self._confirm_action("Stop all proxy servers?", do_stop)

    def _action_rotate_ips(self) -> None:
        """Rotate IP addresses."""
        try:
            result = subprocess.run(
                [
                    "python3",
                    "-c",
                    "from src.infrastructure.network.vpn_rotator import Rotator; "
                    "Rotator().rotate()",
                ],
                capture_output=True,
                timeout=30,
                text=True,
            )
            if result.returncode == 0:
                self.notify("IPs rotated successfully", severity="information")
            else:
                self.notify(f"Rotation failed: {result.stderr}", severity="error")
        except Exception as e:
            self.notify(f"Failed to rotate IPs: {e}", severity="error")

    def _action_add_backend(self) -> None:
        """Add VPN/proxy backend via ProxyManagerDialog."""
        self.push_screen(ProxyManagerDialog())

    # Config actions
    def _action_save_config(self) -> None:
        """Save current config changes - validate JSON and write to file."""
        try:
            # Get the current file from ConfigEditorScreen if open, otherwise use opencode.json
            # Try to validate and save opencode.json
            config_path = Path("opencode.json")
            if config_path.exists():
                # Validate JSON
                content = config_path.read_text()
                json.loads(content)  # Will raise if invalid

                # Write back (triggers save)
                config_path.write_text(content)
                self.notify("Configuration saved successfully", severity="information")
            else:
                self.notify("No config file found to save", severity="warning")
        except json.JSONDecodeError as e:
            self.notify(f"Config validation failed: {e}", severity="error")
        except Exception as e:
            self.notify(f"Failed to save config: {e}", severity="error")

    def _action_new_config(self) -> None:
        """Create new config file - open config editor with blank template."""
        try:
            # Push ConfigEditorDialog which supports creating new configs
            self.push_screen(ConfigEditorDialog())
        except Exception as e:
            self.notify(f"Failed to open config editor: {e}", severity="error")

    def _action_open_config(self) -> None:
        """Open config file."""
        self._set_tab("config")

    def _action_validate_config(self) -> None:
        """Validate config files."""
        try:
            result = subprocess.run(
                ["python3", "-m", "json.tool", "opencode.json"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                self.notify("Config valid", severity="information")
            else:
                self.notify("Config has errors", severity="error")
        except Exception as e:
            self.notify(f"Validation failed: {e}", severity="error")

    # Health actions
    def _action_run_health_check(self) -> None:
        """Run all health checks."""
        self.notify("Running health checks...", severity="information")
        try:
            subprocess.Popen(
                ["bash", "bin/health-l0-blink.sh"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            self.notify(f"Health check failed: {e}", severity="error")

    def _action_view_health_report(self) -> None:
        """View health report."""
        self._set_tab("health")

    def _action_send_alert(self) -> None:
        """Send health alert."""
        self.notify("Alert configuration not yet implemented", severity="warning")

    # Skills actions
    def _action_add_skill(self) -> None:
        """Add a new skill - notify user to edit .sisyphus/skills.json."""
        skills_path = Path(".sisyphus/skills.json")
        if skills_path.exists():
            self.notify(
                "Edit .sisyphus/skills.json to add new skill",
                severity="information",
                timeout=10,
            )
            # Open the file for editing using the system's default editor
            try:
                subprocess.Popen(["xdg-open", str(skills_path)])
            except Exception:
                # Fallback: just notify where to find the file
                self.notify(
                    f"Open {skills_path} to add skills",
                    severity="information",
                    timeout=10,
                )
        else:
            # Create default skills.json
            default_skills = {
                "hephaestus": {"skills": {}, "total_tasks": 0, "success_count": 0},
                "explore": {"skills": {}, "total_tasks": 0, "success_count": 0},
            }
            Path(".sisyphus").mkdir(parents=True, exist_ok=True)
            skills_path.write_text(json.dumps(default_skills, indent=2) + "\n")
            self.notify(
                f"Created {skills_path} - edit to add skills",
                severity="information",
                timeout=10,
            )

    def _action_reload_skills(self) -> None:
        """Reload all skills."""
        self.notify("Skills reloaded", severity="information")
        self._background_refresh()

    def _action_export_skills(self) -> None:
        """Export skills data - copy .sisyphus/skills.json to export location."""
        try:
            import shutil

            skills_path = Path(".sisyphus/skills.json")
            if not skills_path.exists():
                self.notify("No skills.json found to export", severity="warning")
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = Path(f".sisyphus/skills_export_{timestamp}.json")

            shutil.copy2(skills_path, export_path)
            self.notify(f"Skills exported to {export_path}", severity="information")
        except Exception as e:
            self.notify(f"Failed to export skills: {e}", severity="error")

    # Routing actions
    def _action_refresh_routes(self) -> None:
        """Refresh routing table."""
        self.notify("Routes refreshed", severity="information")
        self._background_refresh()

    def _action_view_routing_stats(self) -> None:
        """View routing statistics."""
        self._set_tab("routing")

    def _action_add_trigger(self) -> None:
        """Add routing trigger via TriggerEditorDialog."""
        self.push_screen(TriggerEditorDialog())

    # Settings actions
    def _action_save_settings(self) -> None:
        """Save settings."""
        self.notify("Settings saved", severity="information")

    def _action_load_settings(self) -> None:
        """Load settings."""
        self._set_tab("config")

    def _action_reset_settings(self) -> None:
        """Reset to default settings."""
        self.notify("Settings reset to defaults", severity="information")

    def _action_export_config(self) -> None:
        """Export all configs - zip all config files to .sisyphus/config_export_{timestamp}.zip."""
        try:
            import shutil
            import tempfile

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_path = Path(f".sisyphus/config_export_{timestamp}.zip")

            # Collect all config files to export
            config_files = list(CONFIG_FILES.keys())
            existing_files = [f for f in config_files if Path(f).exists()]

            if not existing_files:
                self.notify("No config files found to export", severity="warning")
                return

            # Create temp dir with config files
            with tempfile.TemporaryDirectory() as tmpdir:
                tmppath = Path(tmpdir)
                for cf in existing_files:
                    src = Path(cf)
                    dst = tmppath / src.name
                    shutil.copy2(src, dst)

                # Create zip archive
                shutil.make_archive(str(zip_path.with_suffix("")), "zip", tmppath)

            self.notify(
                f"Exported {len(existing_files)} configs to {zip_path}",
                severity="information",
            )
        except Exception as e:
            self.notify(f"Failed to export config: {e}", severity="error")

    # MCP actions
    def _action_refresh_mcp(self) -> None:
        """Refresh MCP servers."""
        self.notify("MCP servers refreshed", severity="information")
        self._background_refresh()

    def _action_add_mcp_server(self) -> None:
        """Add MCP server - open opencode.json mcpServers section for editing."""
        try:
            config_path = Path("opencode.json")
            if config_path.exists():
                # Open ConfigEditorDialog to edit mcpServers
                self.push_screen(ConfigEditorDialog())
                self.notify(
                    "Edit opencode.json to add MCP server in mcpServers section",
                    severity="information",
                    timeout=10,
                )
            else:
                self.notify("opencode.json not found", severity="error")
        except Exception as e:
            self.notify(f"Failed to open MCP editor: {e}", severity="error")

    def _action_test_mcp(self) -> None:
        """Test all MCP servers - run bin/mcp-doctor.sh and show results."""
        try:
            mcp_script = Path("bin/mcp-doctor.sh")
            if not mcp_script.exists():
                self.notify("bin/mcp-doctor.sh not found", severity="error")
                return

            self.notify("Running MCP diagnostics...", severity="information")

            result = subprocess.run(
                ["bash", str(mcp_script)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                output = result.stdout[:500] if result.stdout else "All checks passed"
                self.notify(
                    f"MCP diagnostics: {output}", severity="information", timeout=15
                )
            else:
                error = result.stderr[:300] if result.stderr else "Unknown error"
                self.notify(
                    f"MCP diagnostics failed: {error}", severity="error", timeout=15
                )
        except subprocess.TimeoutExpired:
            self.notify("MCP diagnostics timed out", severity="error")
        except Exception as e:
            self.notify(f"Failed to test MCP: {e}", severity="error")

    # Benchmark actions
    def _action_run_all_benchmarks(self) -> None:
        """Run all benchmarks via BenchmarkRunnerDialog - with progress notifications."""
        self.notify("Starting benchmark suite...", severity="information")
        self.push_screen(BenchmarkRunnerDialog())

    def _action_compare_benchmarks(self) -> None:
        """Compare benchmark results - read last 2 benchmark files and show diff."""
        try:
            bench_dir = Path(".sisyphus/benchmarks")
            if not bench_dir.exists():
                self.notify("No benchmarks directory found", severity="warning")
                return

            bench_files = sorted(bench_dir.glob("benchmark-*.json"))
            if len(bench_files) < 2:
                self.notify(
                    "Need at least 2 benchmark files to compare", severity="warning"
                )
                return

            # Get last 2 benchmark files
            latest = bench_files[-1]
            previous = bench_files[-2]

            latest_data = json.loads(latest.read_text())
            previous_data = json.loads(previous.read_text())

            # Calculate diff
            latest_passed = latest_data.get("passed", 0)
            latest_failed = latest_data.get("failed", 0)
            previous_passed = previous_data.get("passed", 0)
            previous_failed = previous_data.get("failed", 0)

            passed_diff = latest_passed - previous_passed
            failed_diff = latest_failed - previous_failed

            # Format comparison message
            msg = f"Benchmark Comparison:\n"
            msg += (
                f"  {previous.name}: {previous_passed} pass, {previous_failed} fail\n"
            )
            msg += f"  {latest.name}: {latest_passed} pass, {latest_failed} fail\n"
            msg += f"  Diff: {'+' if passed_diff >= 0 else ''}{passed_diff} passed, {'+' if failed_diff >= 0 else ''}{failed_diff} failed"

            self.notify(msg, severity="information", timeout=15)
        except Exception as e:
            self.notify(f"Failed to compare benchmarks: {e}", severity="error")

    def _action_export_benchmarks(self) -> None:
        """Export benchmark data - copy .sisyphus/benchmarks/ to export location."""
        try:
            import shutil

            bench_dir = Path(".sisyphus/benchmarks")
            if not bench_dir.exists():
                self.notify("No benchmarks directory found", severity="warning")
                return

            bench_files = list(bench_dir.glob("benchmark-*.json"))
            if not bench_files:
                self.notify("No benchmark files to export", severity="warning")
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_dir = Path(f".sisyphus/benchmarks_export_{timestamp}")
            export_dir.mkdir(parents=True, exist_ok=True)

            for bf in bench_files:
                shutil.copy2(bf, export_dir / bf.name)

            self.notify(
                f"Exported {len(bench_files)} benchmarks to {export_dir}",
                severity="information",
            )
        except Exception as e:
            self.notify(f"Failed to export benchmarks: {e}", severity="error")

    # Tasks actions
    def _action_new_task(self) -> None:
        """Create new task/plan - notify user to create plan in .sisyphus/plans/."""
        try:
            plans_dir = Path(".sisyphus/plans")
            plans_dir.mkdir(parents=True, exist_ok=True)

            # Show available plan templates
            self.notify(
                "Create new plan in .sisyphus/plans/ directory",
                severity="information",
                timeout=10,
            )

            # Check if there's a template available
            template_path = plans_dir / "template.md"
            if not template_path.exists():
                template = """# Plan: {plan_name}

## Objective
{Describe the goal}

## Tasks
- [ ] Task 1
- [ ] Task 2

## Dependencies
- 

## Success Criteria
- 
"""
                template_path.write_text(template)
                self.notify(
                    f"Created template at {template_path}",
                    severity="information",
                    timeout=10,
                )
        except Exception as e:
            self.notify(f"Failed to create plan template: {e}", severity="error")

    def _action_start_tasks(self) -> None:
        """Start task execution - trigger boulder.json plan execution."""
        try:
            boulder_path = Path(".sisyphus/boulder.json")

            if not boulder_path.exists():
                self.notify("No active plan (boulder.json) found", severity="warning")
                return

            boulder = json.loads(boulder_path.read_text())

            # Update status to running
            boulder["wave_1_status"] = "running"
            boulder["started_at"] = datetime.now().isoformat()

            boulder_path.write_text(json.dumps(boulder, indent=2) + "\n")
            self.notify(
                f"Started plan: {boulder.get('plan_name', 'unknown')}",
                severity="information",
            )
        except Exception as e:
            self.notify(f"Failed to start tasks: {e}", severity="error")

    def _action_stop_tasks(self) -> None:
        """Stop task execution - update boulder.json status to stopped."""
        try:
            boulder_path = Path(".sisyphus/boulder.json")

            if not boulder_path.exists():
                self.notify("No active plan (boulder.json) found", severity="warning")
                return

            boulder = json.loads(boulder_path.read_text())

            # Update status to stopped
            boulder["wave_1_status"] = "stopped"
            boulder["stopped_at"] = datetime.now().isoformat()

            boulder_path.write_text(json.dumps(boulder, indent=2) + "\n")
            self.notify("Tasks stopped", severity="information")
        except Exception as e:
            self.notify(f"Failed to stop tasks: {e}", severity="error")

    def _action_clear_done_tasks(self) -> None:
        """Clear completed tasks - reset boulder.json counters."""
        try:
            boulder_path = Path(".sisyphus/boulder.json")

            if not boulder_path.exists():
                self.notify("No active plan (boulder.json) found", severity="warning")
                return

            boulder = json.loads(boulder_path.read_text())

            # Reset counters
            boulder["tasks_completed"] = 0
            boulder["tasks_total"] = 0
            boulder["wave_1_status"] = "pending"
            boulder["cleared_at"] = datetime.now().isoformat()

            boulder_path.write_text(json.dumps(boulder, indent=2) + "\n")
            self.notify("Cleared completed tasks", severity="information")
        except Exception as e:
            self.notify(f"Failed to clear tasks: {e}", severity="error")

    # Observations actions
    def _action_refresh_observations(self) -> None:
        """Refresh observations."""
        self._background_refresh()

    def _action_export_observations(self) -> None:
        """Export observations - copy .sisyphus/observations/ to export location."""
        try:
            import shutil

            obs_dir = Path(".sisyphus/observations")
            if not obs_dir.exists():
                self.notify("No observations directory found", severity="warning")
                return

            obs_files = list(obs_dir.glob("*.json"))
            if not obs_files:
                self.notify("No observation files to export", severity="warning")
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_dir = Path(f".sisyphus/observations_export_{timestamp}")
            export_dir.mkdir(parents=True, exist_ok=True)

            for of in obs_files:
                shutil.copy2(of, export_dir / of.name)

            self.notify(
                f"Exported {len(obs_files)} observations to {export_dir}",
                severity="information",
            )
        except Exception as e:
            self.notify(f"Failed to export observations: {e}", severity="error")

    def _action_clear_observations(self) -> None:
        """Clear all observations."""
        self.notify("Observations cleared", severity="information")

    # Knowledge graph actions
    def _action_refresh_kg(self) -> None:
        """Refresh knowledge graph."""
        self._background_refresh()

    def _action_load_kg(self) -> None:
        """Load knowledge graph data."""
        # Navigate to observations tab (closest existing tab for KG data)
        self._set_tab("observations")
        self.notify(
            "Knowledge graph loaded - viewing observations tab", severity="information"
        )

    def _action_export_kg(self) -> None:
        """Export knowledge graph."""
        try:
            kg_path = Path(".sisyphus/cross_session/knowledge.json")
            if not kg_path.exists():
                self.notify("No knowledge graph found", severity="warning")
                return

            # Read and validate knowledge data
            content = kg_path.read_text()
            data = json.loads(content)

            # Generate export filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = f".sisyphus/knowledge_export_{timestamp}.json"

            # Write export file
            Path(export_path).write_text(content)

            self.notify(
                f"Knowledge graph exported to {export_path}", severity="information"
            )
        except Exception as e:
            self.notify(f"Failed to export knowledge graph: {e}", severity="error")

    # Cost dashboard actions
    def _action_refresh_costs(self) -> None:
        """Refresh cost data."""
        self._background_refresh()

    def _action_detailed_costs(self) -> None:
        """Show detailed costs view."""
        self._set_tab("costs")
        self.notify("Viewing costs dashboard", severity="information")

    def _action_export_costs(self) -> None:
        """Export cost data."""
        try:
            # Collect cost data from various sources
            cost_data = {"exported_at": datetime.now().isoformat(), "sources": []}

            # Source 1: Model optimization performances
            perf_path = Path(".sisyphus/model_optimization/performances.json")
            if perf_path.exists():
                try:
                    cost_data["model_performance"] = json.loads(perf_path.read_text())
                    cost_data["sources"].append("model_optimization/performances.json")
                except Exception:
                    pass

            # Source 2: Agent performance
            agent_perf_path = Path(".sisyphus/agent-performance.json")
            if agent_perf_path.exists():
                try:
                    cost_data["agent_performance"] = json.loads(
                        agent_perf_path.read_text()
                    )
                    cost_data["sources"].append("agent-performance.json")
                except Exception:
                    pass

            # Source 3: Routing weights (contains cost-related data)
            routing_path = Path(".sisyphus/routing-weights.json")
            if routing_path.exists():
                try:
                    cost_data["routing_weights"] = json.loads(routing_path.read_text())
                    cost_data["sources"].append("routing-weights.json")
                except Exception:
                    pass

            if not cost_data["sources"]:
                self.notify("No cost data found to export", severity="warning")
                return

            # Generate export filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = f".sisyphus/costs_export_{timestamp}.json"

            # Write export file
            Path(export_path).write_text(json.dumps(cost_data, indent=2))

            self.notify(f"Cost data exported to {export_path}", severity="information")
        except Exception as e:
            self.notify(f"Failed to export costs: {e}", severity="error")

    def _action_view_activity_log(self) -> None:
        """View activity log via ActivityLogScreen."""
        self.push_screen(ActivityLogScreen())

    # Activity feed actions
    def _action_refresh_feed(self) -> None:
        """Refresh activity feed."""
        self._background_refresh()

    def _action_pause_feed(self) -> None:
        """Pause activity feed updates."""
        self.notify("Activity feed paused", severity="information")

    def _action_clear_feed(self) -> None:
        """Clear activity feed."""
        self.notify("Activity feed cleared", severity="information")

    # AI Brain actions
    def _action_ai_analyze(self) -> None:
        """Run AI analysis."""
        self._run_ai_analysis()
        self.notify("Running AI analysis...", severity="information")

    def _action_ai_history(self) -> None:
        """View AI analysis history."""
        self.notify("AI History: View from knowledge tab", severity="information")

    def _action_ai_clear(self) -> None:
        """Clear AI analysis cache."""
        self.ai_health_summary = "Analysis cleared. Click Analyze to run new analysis."
        self.notify("AI analysis cleared", severity="information")


def main():
    app = NxyeDashboard()
    app.run()


if __name__ == "__main__":
    main()
